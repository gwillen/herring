from typing import Optional

from asgiref.sync import sync_to_async
import asyncio
from asyncio import run, sleep, wait, get_event_loop
from cachetools.func import ttl_cache
from celery import shared_task
from datetime import datetime, timezone
from django.conf import settings
from django.db import transaction
import json
import kombu.exceptions
from puzzles.discordbot import run_listener_bot, DISCORD_ANNOUNCER, announcer_is_ready, do_in_discord, LEAVE_EMOJI, TRIUMPH_EMOJI
from puzzles.models import Puzzle, Round, UserProfile
from puzzles.redis_state import discord_connected, redis_client, set_discord_status
from puzzles.spreadsheets import check_spreadsheet_service, iterate_changes, make_sheet
import logging

logger = logging.getLogger(__name__)

BULLSHIT_CHANNEL="_herring_experimental"
# XXX specific to the 2020 hunt
HUNT_URL_PREFIX="https://pennypark.fun"

_optional_tasks_enabled = None

def optional_task(t):
    """
    This decorator replaces the task it decorates with a no-op if, on first
    call, a connection to Redis can't be established.
    """
    def dummy_apply_async(*args, **kwargs):
        logger.warning(
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


def post_local_and_global(local_channel, local_message, global_message, local_reaction=None, global_reaction=None):
    logger.warning("tasks: post_local_and_global(%s, %s, %s, %s, %s)", local_channel, local_message, global_message, local_reaction, global_reaction)
    if settings.HERRING_ACTIVATE_DISCORD:
        do_in_discord(DISCORD_ANNOUNCER.post_local_and_global(local_channel, local_message, global_message, local_reaction, global_reaction))

@optional_task
@shared_task(rate_limit=0.5)
def post_answer(slug, answer):
    logger.warning("tasks: post_answer(%s, %s)", slug, answer)

    puzzle = Puzzle.objects.get(slug=slug)
    answer = answer.upper()
    local_message = f"{TRIUMPH_EMOJI} Confirmed answer: {answer}\nReact with {LEAVE_EMOJI} to leave the puzzle!"
    global_message = f'{TRIUMPH_EMOJI} Puzzle "{puzzle.name}" (#{slug}) from round {puzzle.parent.name} was solved! The answer is: {answer}\nReact with {LEAVE_EMOJI} to leave the puzzle!'
    post_local_and_global(slug, local_message, global_message, LEAVE_EMOJI, LEAVE_EMOJI)


@optional_task
@shared_task(rate_limit=0.5)
def post_update(slug, updated_field, value):
    logger.warning("tasks: post_update(%s, %s, %s)", slug, updated_field, value)

    try:
        puzzle = Puzzle.objects.get(slug=slug)
    except Puzzle.DoesNotExist:
        return
    local_message = f'{updated_field} set to: {value}'
    global_message = f'"{puzzle.name}" (#{slug}) from round {puzzle.parent.name} now has these {updated_field}: {value}'
    post_local_and_global(slug, local_message, global_message)


@optional_task
@shared_task
def create_puzzle_sheet_and_channel(slug):
    """
    Queued when a puzzle is created. Its sheet and its Discord channels are
    created by separate tasks, so a failure (and the retries) of one doesn't
    hold up or repeat the other -- e.g. retrying a failed sheet mustn't redo
    channel creation, which announces the puzzle.
    """
    logger.warning("tasks: create_puzzle_sheet_and_channel(%s)", slug)
    if settings.HERRING_ACTIVATE_GAPPS:
        create_puzzle_sheet.delay(slug)
    if settings.HERRING_ACTIVATE_DISCORD:
        create_puzzle_channels.delay(slug)


def get_puzzle_or_retry(task, slug):
    try:
        return Puzzle.objects.get(slug=slug)
    except Exception as e:
        logger.error("tasks: %s couldn't load puzzle %s (will retry)", task.name, slug, exc_info=True)
        raise task.retry(exc=e)


@shared_task(bind=True, max_retries=10, default_retry_delay=5, rate_limit=0.25)  # rate_limit is in tasks/sec
def create_puzzle_sheet(self, slug):
    puzzle = get_puzzle_or_retry(self, slug)
    if puzzle.sheet_id:
        return
    try:
        sheet_id = make_sheet(f'{puzzle.round_prefix()} - {puzzle.name}')
    except Exception as e:
        logger.error("tasks: creating the sheet for %s failed (will retry)", slug, exc_info=True)
        raise self.retry(exc=e)
    Puzzle.objects.filter(id=puzzle.id).update(sheet_id=sheet_id)


@shared_task(bind=True, max_retries=10, default_retry_delay=5, rate_limit=0.25)
def create_puzzle_channels(self, slug):
    puzzle = get_puzzle_or_retry(self, slug)
    try:
        do_in_discord(DISCORD_ANNOUNCER.make_puzzle_channels(puzzle))
    except Exception as e:
        logger.error("tasks: creating Discord channels for %s failed (will retry)", slug, exc_info=True)
        raise self.retry(exc=e)



@optional_task
@shared_task(bind=True, max_retries=10, default_retry_delay=5, rate_limit=0.25)
def create_round_category(self, round_id):
    logger.warning("tasks: create_round_category(%d)", round_id)

    if settings.HERRING_ACTIVATE_DISCORD:
        with transaction.atomic():
            try:
                round = Round.objects.select_for_update().get(id=round_id)
            except Exception as e:
                logger.error("tasks: Couldn't retrieve round %d to create a Discord category", round_id, exc_info=True)
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
    logger.warning("tasks: scrape_activity_log()")

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

    # Without this check, the task would hold the mutex (and a worker process)
    # forever with nothing to do, and block warm shutdown of its worker.
    if not listener_bot_runs_in_celery():
        logger.info("check_connection_to_messaging: Discord listener doesn't run under Celery; nothing to do")
        return

    mutex = redis_client().lock('puzzles.tasks.check_connection_to_messaging:mutex', timeout=10)

    if not mutex.acquire(blocking=False):
        logger.info("check_connection_to_messaging: Didn't get mutex, messaging already active")
        return

    logger.info("check_connection_to_messaging: Acquired mutex")

    async def keep_mutex():
        while True:
            await sleep(2)
            mutex.reacquire()

    async def _check_connection_to_messaging():
        awaitables = [
            asyncio.create_task(run_listener_bot(), name="run_listener_bot"),
            asyncio.create_task(keep_mutex(), name="keep_mutex")
        ]
        return await asyncio.gather(*awaitables)

    try:
        run(_check_connection_to_messaging())
    finally:
        mutex.release()
        logger.info("check_connection_to_messaging: Released mutex")

def listener_bot_runs_in_celery():
    return settings.HERRING_ACTIVATE_DISCORD and not settings.HERRING_ENABLE_STANDALONE_DISCORD

@shared_task(bind=True, rate_limit=0.5)
@transaction.atomic
def process_google_sheets_changes(self):
    logger.info("process_google_sheets_changes: Starting")

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
        logger.info("process_google_sheets_changes: Finished (%d updated)", len(puzzles_to_update))


def fetch_latest_sheet_changes():
    """
    Wraps puzzles.spreadsheets.iterate_changes with the logic needed to keep
    the last used page token in Redis.
    """
    start_page_token_key = 'puzzles.google_changes.start_page_token'

    page_token = redis_client().get(start_page_token_key)

    if isinstance(page_token, bytes):
        page_token = page_token.decode('utf-8')

    page_token = yield from iterate_changes(page_token)

    redis_client().set(start_page_token_key, page_token)


# Called from the web process (discord_channel_link), which waits for the
# result -- the channel ID to redirect to -- so it stores its result, and has no
# rate limit (a hunt's worth of people clicking Discord links shouldn't queue
# up; discord.py handles Discord's own rate limits).
@shared_task(ignore_result=False)
def add_user_to_puzzle(user_id, puzzle_name):
    logger.debug("add_user_to_puzzle: %r, %r", user_id, puzzle_name)
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
        # Reported to Redis by the processes that hold Discord connections; the
        # web process never connects to Discord itself.
        discord = discord_connected()
    if settings.HERRING_ACTIVATE_GAPPS:
        gapps = check_spreadsheet_service()
    return {
        'discord': discord,
        'gapps': gapps,
    }


@shared_task(ignore_result=True)
def report_discord_status():
    """Periodic (Celery beat): record whether this worker's announcer bot is connected."""
    set_discord_status('announcer', announcer_is_ready())


@shared_task(ignore_result=True)
def post_discord_message(channel_name, text):
    """Post `text` to the Discord channel named `channel_name` (for /post_discord/)."""
    do_in_discord(DISCORD_ANNOUNCER.post_message(channel_name, text))
