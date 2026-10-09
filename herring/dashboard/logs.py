"""
Reading the captured logs (written by herring.log_buffer.RedisLogHandler) and
editing the runtime log level settings.
"""
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import cache
from itertools import islice

from django.conf import settings

from herring.log_buffer import LEVEL_NAMES, parse_levels, redis_from_url

logger = logging.getLogger(__name__)

# Stream entries are read in batches of this many, newest first...
SCAN_BATCH = 500
# ...stopping after this many, so a filter that matches nothing can't scan the whole buffer on every poll.
MAX_SCANNED = 20000
LEVEL_VALUES = logging.getLevelNamesMapping()


@cache
def redis():
    return redis_from_url(settings.REDIS_URL)


@dataclass(frozen=True)
class LogFilter:
    min_level: str = 'DEBUG'
    logger: str = ''    # logger name prefix, e.g. 'puzzles' or 'discord.gateway'
    text: str = ''      # case-insensitive substring of the message
    process: str = ''   # substring of the process label, e.g. 'worker' or a pid

    @classmethod
    def from_query(cls, query):
        level = query.get('level', 'DEBUG')
        return cls(min_level=level if level in LEVEL_NAMES else 'DEBUG',
                   logger=query.get('logger', '').strip(), text=query.get('text', '').strip(),
                   process=query.get('process', '').strip())

    def matches(self, entry):
        return (LEVEL_VALUES.get(entry['level'], 0) >= LEVEL_VALUES[self.min_level]
                and (not self.logger or entry['logger'] == self.logger
                     or entry['logger'].startswith(self.logger + '.'))
                and self.text.lower() in entry['message'].lower()
                and self.process in entry['process'])


def read_entries(log_filter, before=None, after=None, limit=200):
    """
    Up to `limit` matching entries, newest first. `before` / `after` are entry
    IDs (exclusive bounds), for loading older entries and for live tailing.
    """
    matching = (entry for entry in scan_newest_first(before, after) if log_filter.matches(entry))
    return list(islice(matching, limit))


def scan_newest_first(before, after):
    upper, lower = f'({before}' if before else '+', f'({after}' if after else '-'
    scanned = 0
    while scanned < MAX_SCANNED:
        rows = redis().xrevrange(settings.HERRING_LOG_STREAM_KEY, max=upper, min=lower, count=SCAN_BATCH)
        if not rows:
            return
        scanned += len(rows)
        yield from (decode_entry(entry_id, fields) for entry_id, fields in rows)
        upper = f'({rows[-1][0].decode()}'


def decode_entry(entry_id, fields):
    entry = {key.decode(): value.decode(errors='replace') for key, value in fields.items()}
    timestamp = datetime.fromtimestamp(float(entry.get('ts', 0)), tz=timezone.utc)
    return {**entry, 'id': entry_id.decode(), 'time': timestamp.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}


def buffer_size():
    return redis().xlen(settings.HERRING_LOG_STREAM_KEY)


def current_levels():
    return parse_levels(redis().get(settings.HERRING_LOG_LEVELS_KEY))


def save_levels(levels):
    """Stores {logger name: level}; '' is the root logger and is always kept. Processes apply it within seconds."""
    cleaned = {name.strip(): level for name, level in levels.items() if level in LEVEL_NAMES}
    cleaned.setdefault('', 'INFO')
    redis().set(settings.HERRING_LOG_LEVELS_KEY, json.dumps(cleaned, sort_keys=True))
    logger.info("dashboard: log levels set to %s", cleaned)
    return cleaned
