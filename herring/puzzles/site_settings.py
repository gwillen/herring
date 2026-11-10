"""
Reading and changing the settings admins control from the dashboard
(puzzles.models.SiteSettings), from any process: web, Celery workers, the
Discord bots. Values are cached for SITE_SETTINGS_CACHE_SECONDS, so a change
reaches every process within that time.
"""
import asyncio
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

from django.conf import settings
from django.db import connection, transaction

logger = logging.getLogger(__name__)

# Django forbids synchronous database access from inside an event loop, so reads
# from async code (the Discord bots) happen on this thread instead.
_reader = ThreadPoolExecutor(max_workers=1, thread_name_prefix='site-settings')
_cache = {'at': None, 'value': None}


@dataclass(frozen=True)
class Current:
    """The settings in effect. discord_enabled/gapps_enabled already include the environment's hard switches."""
    discord_enabled: bool
    gapps_enabled: bool
    discord_guild_id: int = None
    hunt_id: int = None
    protected_category_ids: frozenset = field(default_factory=frozenset)


def current():
    if _cache['at'] is None or time.monotonic() - _cache['at'] >= settings.SITE_SETTINGS_CACHE_SECONDS:
        _cache['value'], _cache['at'] = load(), time.monotonic()
    return _cache['value']


def load():
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return effective(read_row())  # ordinary synchronous code: read on this thread (and inside its transaction)
    return _reader.submit(read_and_disconnect).result(timeout=30)


def read_and_disconnect():
    """For the reader thread: don't keep a database connection open between reads."""
    try:
        return effective(read_row())
    finally:
        connection.close()


def read_row():
    from puzzles.models import SiteSettings
    return SiteSettings.objects.get_or_create(id=1)[0]


def effective(row):
    return Current(discord_enabled=settings.HERRING_ACTIVATE_DISCORD and row.discord_enabled,
                   gapps_enabled=settings.HERRING_ACTIVATE_GAPPS and row.gapps_enabled,
                   discord_guild_id=row.discord_guild_id, hunt_id=row.hunt_id,
                   protected_category_ids=frozenset(row.protected_category_ids))


def clear_cache():
    _cache['at'] = None


def discord_on():
    return current().discord_enabled


def gapps_on():
    return current().gapps_enabled


def guild_id():
    """The current hunt's Discord server ID, or None if none is set."""
    return current().discord_guild_id


def hunt_id():
    """The current hunt's ID, or None if none is set."""
    return current().hunt_id


def default_hunt_id():
    """Default for new rounds and puzzles: the current hunt (0 if none is set, as before)."""
    return hunt_id() or 0


EDITABLE = ('discord_enabled', 'gapps_enabled', 'discord_guild_id', 'hunt_id', 'protected_category_ids')


@transaction.atomic
def update(user, **changes):
    """Saves the given changes, recording each actual change; returns the names of the fields that changed."""
    from puzzles.models import SiteSettingChange
    row = read_row()
    changed = {name: value for name, value in changes.items() if getattr(row, name) != value}
    assert set(changed) <= set(EDITABLE), changed
    for name, value in changed.items():
        SiteSettingChange.objects.create(changed_by=user, field=name, old_value=getattr(row, name), new_value=value)
        setattr(row, name, value)
    row.save()
    clear_cache()
    logger.info("Site settings changed by %s: %s", user, changed or "nothing")
    return sorted(changed)
