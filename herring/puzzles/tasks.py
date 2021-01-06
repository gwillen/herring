from typing import Optional

from asgiref.sync import sync_to_async
from asyncio import run, sleep, wait, get_event_loop
from cachetools.func import ttl_cache
from celery import shared_task
from datetime import datetime, timezone
from django.conf import settings
from django.db import transaction
import json
import kombu.exceptions
from lazy_object_proxy import Proxy as lazy_object
from puzzles.discordbot import HerringAnnouncerBot, make_announcer_bot, run_listener_bot
from puzzles.models import Puzzle, Round, UserProfile
from puzzles.spreadsheets import check_spreadsheet_service, iterate_changes, make_sheet
from redis import Redis
import slacker
import websockets
import requests
from bs4 import BeautifulSoup
import logging

BULLSHIT_CHANNEL="_herring_experimental"
# XXX specific to the 2020 hunt
HUNT_URL_PREFIX="https://pennypark.fun"

SLACK_USER_ID = None  # will be initialized once SLACK is

@lazy_object
def SLACK():
    global SLACK_USER_ID
    if not settings.HERRING_ACTIVATE_SLACK:
        logging.warning("Running without Slack integration!")
        return None
    try:
        # A token logged in as a legitimate user. Turns out that "bots" can't
        # do the things we want to automate!
        result = slacker.Slacker(settings.HERRING_SECRETS['slack-user-token'])
        SLACK_USER_ID = result.auth.test().body['user_id']
        return result
    except KeyError:
        print(
            "Couldn't find the SECRETS environment variable. This server won't be able "
            "to use Slack and Google Drive integrations."
        )


@lazy_object
def REDIS():
    # Every instance of the Redis object creates its own connection pool,
    # and Redis connections on Heroku are limited! So sharing this Redis
    # instance is possibly important. TBH, I have no idea why we run out of
    # Redis connections so quickly; it's possible this doesn't help at all.
    return Redis.from_url(settings.REDIS_URL, max_connections=1)

@lazy_object
def DISCORD_ANNOUNCER() -> Optional[HerringAnnouncerBot]:
    if not settings.HERRING_ACTIVATE_DISCORD:
        logging.warning("Running without Discord integration!")
        return None
    return make_announcer_bot(settings.HERRING_SECRETS['discord-bot-token'])

_optional_tasks_enabled = None


def do_in_discord(coro):
    try:
        return DISCORD_ANNOUNCER.do_in_loop(coro)
    except RuntimeError:
        # probably the discord bot is busted, try to make it rebuild
        logging.error("Invalidating discord announcer bot!")
        del DISCORD_ANNOUNCER.__target__
        raise


def optional_task(t):
    """
    This decorator replaces the task it decorates with a no-op if, on first
    call, a connection to Redis can't be established.
    """
    def dummy_apply_async(*args, **kwargs):
        logging.warning(
            f"Optional task {t.__name__} has been disabled because a "
            "connection to Redis could not be established. If Redis is "
            "running again, the web server should be restarted.")

    def apply_async(*args, **kwargs):
        global _optional_tasks_enabled
        if _optional_tasks_enabled is None:
            try:
                t.__class__.apply_async(t, *args, **kwargs)
                _optional_tasks_enabled = True
                del t.apply_async
                return
            except kombu.exceptions.OperationalError:
                _optional_tasks_enabled = False

        if _optional_tasks_enabled:
            del t.apply_async
        else:
            t.apply_async = dummy_apply_async

        t.apply_async(*args, **kwargs)

    t.apply_async = apply_async
    return t


def post_local_and_global(local_channel, local_message, global_message):
    logging.warning("tasks: post_local_and_global(%s, %s, %s)", local_channel, local_message, global_message)
    if settings.HERRING_ACTIVATE_SLACK:
        try:
            response = SLACK.channels.join(local_channel)
            channel_id = response.body['channel']['id']
            SLACK.chat.post_message(channel_id, local_message, link_names=True, as_user=True)
        except Exception:
            # Probably the channel's already archived. Don't worry too much about it.
            logging.warning("tasks: failed to post to local channel (probably archived)", exc_info=True)

        response = SLACK.channels.join(settings.HERRING_STATUS_CHANNEL)
        global_channel_id = response.body['channel']['id']
        SLACK.chat.post_message(global_channel_id, global_message, link_names=True, as_user=True)

    if settings.HERRING_ACTIVATE_DISCORD:
        do_in_discord(DISCORD_ANNOUNCER.post_local_and_global(local_channel, local_message, global_message))

@optional_task
@shared_task(rate_limit=0.5)
def post_answer(slug, answer):
    logging.warning("tasks: post_answer(%s, %s)", slug, answer)

    puzzle = Puzzle.objects.get(slug=slug)
    answer = answer.upper()
    local_message = "\N{PARTY POPPER} Confirmed answer: {}".format(answer)
    global_message = '\N{PARTY POPPER} Puzzle "{name}" (#{slug}) was solved! The answer is: {answer}'.format(
        answer=answer,
        slug=slug,
        name=puzzle.name
    )
    post_local_and_global(slug, local_message, global_message)


@optional_task
@shared_task(rate_limit=0.5)
def post_update(slug, updated_field, value):
    logging.warning("tasks: post_update(%s, %s, %s)", slug, updated_field, value)

    try:
        puzzle = Puzzle.objects.get(slug=slug)
    except Puzzle.DoesNotExist:
        return
    local_message = '{} set to: {}'.format(updated_field, value)
    global_message = '"{name}" (#{slug}) now has these {field}: {value}'.format(
        field=updated_field,
        value=value,
        slug=slug,
        name=puzzle.name
    )
    post_local_and_global(slug, local_message, global_message)


@optional_task
@shared_task(bind=True, max_retries=10, default_retry_delay=5, rate_limit=0.25)  # rate_limit is in tasks/sec
def create_puzzle_sheet_and_channel(self, slug):
    logging.warning("tasks: create_puzzle_sheet_and_channel(%s)", slug)

    try:
        puzzle = Puzzle.objects.get(slug=slug)
    except Exception as e:
        logging.error("tasks: Failed to retrieve puzzle when creating sheet and channel (may be retried) - %s", slug, exc_info=True)
        raise self.retry(exc=e)

    if settings.HERRING_ACTIVATE_GAPPS:
        sheet_title = '{} - {}'.format(puzzle.round_prefix(), puzzle.name)
        sheet_id = make_sheet(sheet_title)

        puzzle.sheet_id = sheet_id

    if settings.HERRING_ACTIVATE_SLACK:
        try:
            created = SLACK.channels.create(slug)
        except slacker.Error:
            logging.error("tasks: failed to create channel when creating sheet and channel (joining instead) - %s", slug, exc_info=True)
            created = SLACK.channels.join(slug)

        channel_id = created.body['channel']['id']
        puzzle.slack_channel_id = channel_id

        puzzle_name = puzzle.name
        if len(puzzle_name) >= 30:
            puzzle_name = puzzle_name[:29] + '\N{HORIZONTAL ELLIPSIS}'

        topic = "{name} - Sheet: {host}/s/{id} - Puzzle: {url}".format(
            name=puzzle_name,
            url=puzzle.hunt_url,
            host=settings.HERRING_HOST,
            id=puzzle.id
        )
        SLACK.channels.set_topic(channel_id, topic)

        response = SLACK.channels.join(settings.HERRING_STATUS_CHANNEL)
        status_channel_id = response.body['channel']['id']

        new_channel_msg = 'New puzzle created: "{name}" (#{slug})'.format(
            slug=slug, name=puzzle.name
        )

        SLACK.chat.post_message(status_channel_id, new_channel_msg, link_names=True, as_user=True)

    puzzle.save()

    if settings.HERRING_ACTIVATE_DISCORD:
        try:
            do_in_discord(DISCORD_ANNOUNCER.make_puzzle_channels(puzzle))
        except RuntimeError:
            raise self.retry()



@optional_task
@shared_task(bind=True, max_retries=10, default_retry_delay=5, rate_limit=0.25)
def create_round_category(self, round_id):
    logging.warning("tasks: create_round_category(%d)", round_id)

    if settings.HERRING_ACTIVATE_DISCORD:
        try:
            round = Round.objects.get(id=round_id)
        except Exception as e:
            logging.error("tasks: Couldn't retrieve round %d to create a Discord category", round_id, exc_info=True)
            raise self.retry(exc=e)
        try:
            category = do_in_discord(DISCORD_ANNOUNCER.make_category(round.name))
            if category:
                round.discord_categories = str(category.id)
                round.save()
        except RuntimeError:
            raise self.retry()

@shared_task(rate_limit=0.1)
def scrape_activity_log():
    logging.warning("tasks: scrape_activity_log()")

    log_url = settings.HERRING_PUZZLE_ACTIVITY_LOG_URL
    log_cookies = json.loads(settings.HERRING_PUZZLE_SITE_SESSION_COOKIE)

    flatten = lambda l: [item for sublist in l for item in sublist]
    def extract_link(text, selector):
        return HUNT_URL_PREFIX + BeautifulSoup(text, 'html.parser').select(selector)[0].get('href')
    def extract_text(text, selector):
        return BeautifulSoup(text, 'html.parser').select(selector)[0].get_text()

    s = requests.Session()
    r = s.get(log_url, cookies=log_cookies)
    entries = flatten(reversed([[(x['when'], y) for y in x['htmls']] for x in json.loads(r.content)['log']]))

    rounds = [(t, extract_text(x, 'b')) for (t, x) in entries if ' is now open!' in x]
    unlocks = [(t, extract_link(x, 'a'), extract_text(x, 'span.puzzletitle'), extract_text(x, 'span.landtag')) for (t, x) in entries if ' opened.' in x]
    solves = [(t, extract_link(x, 'a'), extract_text(x, 'span.puzzletitle'), extract_text(x, 'span.landtag')) for (t, x) in entries if ' solved.' in x]

    last_unlock = unlocks[-1]

    new_unlocks = []
    for ul in unlocks:
        p = Puzzle.objects.filter(hunt_url=ul[1])
        if not p:
            new_unlocks.append(ul)

    if settings.HERRING_ACTIVATE_SLACK:
        response = SLACK.channels.join(BULLSHIT_CHANNEL)
        bullshit_channel_id = response.body['channel']['id']

        # XXX hardcoded hunt root URL
        activity_msg = "Last puzzle unlock was '{}' in round '{}' at {} ({})".format(last_unlock[2], last_unlock[3], datetime.fromtimestamp(last_unlock[0]).strftime("%a %-I:%M %p"), last_unlock[1])
        SLACK.chat.post_message(bullshit_channel_id, activity_msg, link_names=True, as_user=True)

        if len(new_unlocks) > 0:
            display_unlocks = ", ".join(["{} in {} ({})".format(x[2], x[3], x[1]) for x in new_unlocks])
            activity_msg = "There are {} unlocks without puzzle pages: {}".format(len(new_unlocks), display_unlocks)
            SLACK.chat.post_message(bullshit_channel_id, activity_msg, link_names=True, as_user=True)


@shared_task(ignore_result=True)
def check_connection_to_messaging():
    # This task is intended to run *indefinitely*. The scheduler will attempt
    # to kick it off regularly, but we only want one running at any given time;
    # more would certainly be a waste of compute and will definitely make the Discord integration work
    # unreliably. To achieve this, we'll use Redis as a mutex.

    mutex = REDIS.lock('puzzles.tasks.check_connection_to_messaging:mutex', timeout=10)

    if not mutex.acquire(blocking=False):
        return

    logging.info("check_connection_to_messaging: Acquired mutex")

    async def keep_mutex():
        while True:
            await sleep(2)
            mutex.reacquire()

    try:
        logging.info("herring secrets: %s", settings.HERRING_SECRETS)
        run(wait([process_slack_messages_forever(), run_discord_listener_bot(), keep_mutex()]))
    finally:
        mutex.release()
        logging.info("check_connection_to_messaging: Released mutex")


async def run_discord_listener_bot():
    if settings.HERRING_ACTIVATE_DISCORD:
        await run_listener_bot(get_event_loop())


async def process_slack_messages_forever():
    logging.info("process_slack_messages_forever: Starting")
    while True:
        if settings.HERRING_ACTIVATE_SLACK:
            try:
                result = SLACK.rtm.connect()
                if result.successful:
                    uri = result.body['url']
                    async with websockets.connect(uri) as ws:
                        while await dispatch_slack_message(json.loads(await ws.recv())):
                            pass
                    continue  # reconnect immediately
                else:
                    logging.error("Couldn't connect to Slack RTM API: %s", result.error)
            except Exception:
                logging.exception("Error processing Slack RTM messages")

        # If we're here, we failed to connect or we recorded an application
        # error. Either way, we'll attempt to reconnect in a minute.
        await sleep(60)


@sync_to_async
def dispatch_slack_message(message):
    logging.debug("dispatch_slack_message: %r", message)
    mtype = message['type']
    if mtype == 'error':
        logging.error("Slack RTM error: %s", message['error']['msg'])
        return False
    if mtype == 'message':
        if not ('subtype' in message or message['user'] == SLACK_USER_ID):
            record_slack_activity(
                channel_id=message['channel'],
                user_id=message['user'],
                timestamp=float(message['ts']))
    elif mtype == 'member_joined_channel' or mtype == 'member_left_channel':
        update_slack_channel_membership.delay(channel_id=message['channel'])
    return True


def record_slack_activity(channel_id, user_id, timestamp):
    slug = channel_name(channel_id)
    if slug is None:
        return

    dt = datetime.fromtimestamp(timestamp, timezone.utc)
    try:
        with transaction.atomic():
            puzzle = Puzzle.objects.select_for_update().get(slug=slug)
            if puzzle.slack_channel_id != channel_id:
                # this shouldn't ever really happen, just a fixup
                puzzle.slack_channel_id = channel_id
                puzzle.save(update_fields=['slack_channel_id'])
            if puzzle.record_activity(dt):
                puzzle.save(update_fields=['last_active', 'activity_tracker'])
    except Puzzle.DoesNotExist:
        return

    with transaction.atomic():
        row, created = puzzle.channelparticipation_set.get_or_create(
            user_id=user_id,
            defaults=dict(last_active=dt, is_member=True))
        if not created and (row.last_active is None or row.last_active < dt):
            row.last_active = dt
            row.is_member = True
            row.save(update_fields=['last_active', 'is_member'])

    logging.info("record_slack_activity: For puzzle %s, user %s, recorded activity at %s", slug, user_id, dt)


@shared_task
def update_slack_channel_membership(channel_id):
    slug = channel_name(channel_id)
    if slug is None:
        return

    try:
        puzzle = Puzzle.objects.get(slug=slug)
    except Puzzle.DoesNotExist:
        return

    if settings.HERRING_ACTIVATE_SLACK:
        result = SLACK.conversations.members(channel_id)
        if not result.successful:
            return

        membership = set(result.body['members'])
        membership.remove(SLACK_USER_ID)
        n = len(membership)

        puzzle.channel_count = n
        puzzle.save(update_fields=['channel_count'])

        puzzle.channelparticipation_set\
            .exclude(user_id__in=membership)\
            .update(is_member=False)

        for row in puzzle.channelparticipation_set.filter(is_member=True):
            membership.remove(row.user_id)

        for user_id in membership:
            puzzle.channelparticipation_set.update_or_create(
                user_id=user_id,
                defaults=dict(is_member=True))

    logging.info("update_slack_channel_membership: For puzzle %s, set channel_count = %d", slug, n)


@ttl_cache(maxsize=512, ttl=3600)
def channel_name(channel_id):
    if not settings.HERRING_ACTIVATE_SLACK:
        return None
    result = SLACK.conversations.info(channel_id)
    if result.successful:
        return result.body['channel']['name']


@shared_task(bind=True, rate_limit=0.5)
@transaction.atomic
def process_google_sheets_changes(self):
    logging.info("process_google_sheets_changes: Starting")

    if settings.HERRING_ACTIVATE_GAPPS:
        puzzles_to_update = set()
        for change in fetch_latest_sheet_changes():
            try:
                puzzle = Puzzle.objects \
                    .select_for_update() \
                    .get(sheet_id=change.sheet_id)
            except Puzzle.DoesNotExist:
                continue

            if puzzle.record_activity(change.datetime):
                puzzles_to_update.add(puzzle)

        Puzzle.batch_save_activity(puzzles_to_update)
        logging.info("process_google_sheets_changes: Finished (%d updated)", len(puzzles_to_update))


def fetch_latest_sheet_changes():
    """
    Wraps puzzles.spreadsheets.iterate_changes with the logic needed to keep
    the last used page token in Redis.
    """
    start_page_token_key = 'puzzles.google_changes.start_page_token'

    page_token = REDIS.get(start_page_token_key)

    if isinstance(page_token, bytes):
        page_token = page_token.decode('utf-8')

    page_token = yield from iterate_changes(page_token)

    REDIS.set(start_page_token_key, page_token)


@shared_task(rate_limit=0.5)
def add_user_to_puzzle(user_id, puzzle_name):
    logging.debug("add_user_to_puzzle: %r, %r", user_id, puzzle_name)
    if not settings.HERRING_ACTIVATE_DISCORD:
        return
    try:
        user = UserProfile.objects.get(user_id=user_id)
    except UserProfile.DoesNotExist:
        # oh well, we tried
        return
    channel = do_in_discord(DISCORD_ANNOUNCER.add_user_to_puzzle(user, puzzle_name))
    if channel is None:
        # not sure what happened here
        return
    return channel.id


@ttl_cache(ttl=10)
def get_service_status():
    slack = None
    discord = None
    gapps = None
    if settings.HERRING_ACTIVATE_SLACK:
        slack = (SLACK.auth.test().body['user_id'] == SLACK_USER_ID)
    if settings.HERRING_ACTIVATE_DISCORD:
        # this has the side effect of reifying DISCORD_ANNOUNCER
        discord = do_in_discord(DISCORD_ANNOUNCER.wait_until_really_ready(5))
    if settings.HERRING_ACTIVATE_GAPPS:
        gapps = check_spreadsheet_service()
    return {
        'slack': slack,
        'discord': discord,
        'gapps': gapps,
    }
