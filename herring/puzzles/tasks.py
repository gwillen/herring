from typing import Optional

from asgiref.sync import sync_to_async
import asyncio
from asyncio import run, sleep, wait, get_event_loop
from cachetools.func import ttl_cache
from celery import shared_task
from datetime import datetime, timezone
from django.conf import settings
from django.contrib.postgres.search import SearchQuery, SearchVector
from django.db import transaction
import json
import kombu.exceptions
from lazy_object_proxy import Proxy as lazy_object
from puzzles.discordbot import run_listener_bot, DISCORD_ANNOUNCER, do_in_discord
from puzzles.models import Puzzle, Round, UserProfile
from puzzles.spreadsheets import check_spreadsheet_service, iterate_changes, make_sheet
from redis import Redis
import websockets
import requests
from bs4 import BeautifulSoup
import logging
from urllib.parse import urlparse

BULLSHIT_CHANNEL="_herring_experimental"
# XXX specific to the 2020 hunt
HUNT_URL_PREFIX="https://pennypark.fun"

@lazy_object
def REDIS():
    # Every instance of the Redis object creates its own connection pool,
    # and Redis connections on Heroku are limited! So sharing this Redis
    # instance is possibly important. TBH, I have no idea why we run out of
    # Redis connections so quickly; it's possible this doesn't help at all.
    ssl_kwargs = {}
    url = urlparse(settings.REDIS_URL)
    if url.scheme == "rediss":
        ssl_kwargs["ssl_cert_reqs"] = None  # allow self-signed certificates
    return Redis.from_url(settings.REDIS_URL, max_connections=1, **ssl_kwargs)

_optional_tasks_enabled = None

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
@shared_task(rate_limit=0.5)
def notify_subscribers(slug: str, keywords: str):
    logging.warning("tasks: notify_subscribers(%s, %r)", slug, keywords)

    try:
        puzzle = Puzzle.objects.get(slug=slug)
    except Puzzle.DoesNotExist:
        return

    try:
        users = UserProfile.objects.annotate(search=SearchVector('subscriptions', config='english')).filter(
            search=SearchQuery(keywords, search_type='raw'),
            discord_identifier__isnull=False,
        )
        users = list(users)
    except Exception as e:
        logging.error("tasks: notify_subscribers failed while searching subscriptions", e)
        return

    if len(users) == 0:
        return

    discord_ids = [u.discord_identifier for u in users]

    message = f"Based on your subscriptions, you might want to join \"{puzzle.name}\" (#{slug})."
    if puzzle.tags:
        message += f" It has tags \"{puzzle.tags}\"."
    if puzzle.note:
        message += f" It has notes \"{puzzle.note}\"."
    if settings.HERRING_ACTIVATE_DISCORD:
        do_in_discord(DISCORD_ANNOUNCER.send_subscription_messages(slug, discord_ids, message))


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
        if not puzzle.sheet_id:
            sheet_title = '{} - {}'.format(puzzle.round_prefix(), puzzle.name)
            sheet_id = make_sheet(sheet_title)

            puzzle.sheet_id = sheet_id

    puzzle.save()

    if settings.HERRING_ACTIVATE_DISCORD:
        try:
            do_in_discord(DISCORD_ANNOUNCER.make_puzzle_channels(puzzle))
        except Exception:
            raise self.retry()



@optional_task
@shared_task(bind=True, max_retries=10, default_retry_delay=5, rate_limit=0.25)
def create_round_category(self, round_id):
    logging.warning("tasks: create_round_category(%d)", round_id)

    if settings.HERRING_ACTIVATE_DISCORD:
        with transaction.atomic():
            try:
                round = Round.objects.select_for_update().get(id=round_id)
            except Exception as e:
                logging.error("tasks: Couldn't retrieve round %d to create a Discord category", round_id, exc_info=True)
                raise self.retry(exc=e)
            try:
                category = do_in_discord(DISCORD_ANNOUNCER.make_category(round.name))
                if category:
                    round.discord_categories = str(category.id)
                    round.save()
            except Exception:
                raise self.retry()

# This is disabled because it was never updated from slack to discord.
"""
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
"""

@shared_task(ignore_result=True)
def check_connection_to_messaging():
    # This task is intended to run *indefinitely*. The scheduler will attempt
    # to kick it off regularly, but we only want one running at any given time;
    # more would certainly be a waste of compute and will definitely make the Discord integration work
    # unreliably. To achieve this, we'll use Redis as a mutex.

    mutex = REDIS.lock('puzzles.tasks.check_connection_to_messaging:mutex', timeout=10)

    if not mutex.acquire(blocking=False):
        logging.info("check_connection_to_messaging: Didn't get mutex, messaging already active")
        return

    logging.info("check_connection_to_messaging: Acquired mutex")

    async def keep_mutex():
        while True:
            await sleep(2)
            mutex.reacquire()

    async def _check_connection_to_messaging():
        awaitables = [
            asyncio.create_task(run_discord_listener_bot(), name="run_discord_listener_bot"),
            asyncio.create_task(keep_mutex(), name="keep_mutex")
        ]
        return await asyncio.gather(*awaitables)

    try:
        run(_check_connection_to_messaging())
    finally:
        mutex.release()
        logging.info("check_connection_to_messaging: Released mutex")

async def run_discord_listener_bot():
    if settings.HERRING_ACTIVATE_DISCORD and not settings.HERRING_ENABLE_STANDALONE_DISCORD:
        await run_listener_bot()

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
    discord = None
    gapps = None
    if settings.HERRING_ACTIVATE_DISCORD:
        # this has the side effect of reifying DISCORD_ANNOUNCER
        discord = do_in_discord(DISCORD_ANNOUNCER.wait_until_really_ready(5))
    if settings.HERRING_ACTIVATE_GAPPS:
        gapps = check_spreadsheet_service()
    return {
        'discord': discord,
        'gapps': gapps,
    }
