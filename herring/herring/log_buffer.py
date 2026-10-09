"""
Captures log records from every Herring process (web, Celery workers, the
Discord bot) into a capped Redis stream, for the admin dashboard's log viewer.

Which loggers are captured at which level is a runtime setting, stored in
Redis and edited from the dashboard. A background thread in each process
re-reads it every LEVELS_REFRESH_SECONDS and applies it to that process's
Python loggers, so turning on DEBUG for e.g. 'puzzles' affects all processes
within seconds, without a restart.

This module is loaded by logging configuration (settings.LOGGING) before
Django is set up, so it must not import Django or app code.
"""
import json
import logging
import os
import socket
import sys
import threading
import time
from functools import cache

from redis import Redis

LEVELS_REFRESH_SECONDS = 10
# After a failure to write to Redis, stop trying for this long (and say so on stderr).
FAILURE_BACKOFF_SECONDS = 30
DEFAULT_LEVELS = {'': 'INFO'}  # '' is the root logger
LEVEL_NAMES = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']


def redis_from_url(url):
    # Heroku's Redis uses self-signed certificates (as in puzzles.redis_state).
    ssl_kwargs = {'ssl_cert_reqs': None} if url.startswith('rediss:') else {}
    return Redis.from_url(url, **ssl_kwargs)


@cache
def process_label():
    """Where a record came from: host (or Heroku dyno), role, and pid."""
    host = os.environ.get('DYNO') or socket.gethostname()
    return f"{host} {process_role()} {os.getpid()}"


def process_role():
    args = [os.path.basename(arg) for arg in sys.argv[:3]]
    if any('gunicorn' in arg for arg in args):
        return 'web'
    if any('celery' in arg for arg in args):
        return 'worker'
    if len(args) > 1 and args[0] == 'manage.py':
        return args[1]
    return args[0] if args else 'unknown'


class RedisLogHandler(logging.Handler):
    """Appends records to a capped Redis stream, and applies the runtime log levels."""

    def __init__(self, redis_url, stream_key, levels_key, max_entries):
        super().__init__()
        self.redis_url = redis_url
        self.stream_key = stream_key
        self.levels_key = levels_key
        self.max_entries = max_entries
        self.local = threading.local()  # re-entrancy guard (redis-py can log while we write)
        self.applied_levels = {}
        self.refresher_pid = None
        self.failed_at = 0
        self.setFormatter(logging.Formatter('%(message)s'))  # adds the traceback, if any

    @property
    def redis(self):
        if not hasattr(self, '_redis'):
            self._redis = redis_from_url(self.redis_url)
        return self._redis

    def emit(self, record):
        if getattr(self.local, 'busy', False) or time.time() - self.failed_at < FAILURE_BACKOFF_SECONDS:
            return
        self.local.busy = True
        try:
            self.ensure_level_refresher()
            self.redis.xadd(self.stream_key, self.entry(record), maxlen=self.max_entries, approximate=True)
        except Exception as e:
            self.failed_at = time.time()
            print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} log_buffer: couldn't write to Redis, "
                  f"pausing for {FAILURE_BACKOFF_SECONDS}s: {e!r}", file=sys.stderr)
        finally:
            self.local.busy = False

    def entry(self, record):
        return {'ts': f"{record.created:.3f}", 'level': record.levelname, 'logger': record.name,
                'process': process_label(), 'message': self.format(record)}

    def ensure_level_refresher(self):
        """Starts this process's refresher thread (again after a fork: threads don't survive one)."""
        if self.refresher_pid == os.getpid():
            return
        self.refresher_pid = os.getpid()
        self.refresh_levels()
        threading.Thread(target=self.refresh_levels_forever, name='log-levels', daemon=True).start()

    def refresh_levels_forever(self):
        while True:
            time.sleep(LEVELS_REFRESH_SECONDS)
            try:
                self.refresh_levels()
            except Exception as e:
                print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} log_buffer: couldn't refresh log levels: {e!r}",
                      file=sys.stderr)

    def refresh_levels(self):
        levels = parse_levels(self.redis.get(self.levels_key))
        if levels != self.applied_levels:
            apply_levels(levels, previous=self.applied_levels)
            self.applied_levels = levels


def parse_levels(raw):
    """The stored level settings ({logger name: level name}), or the defaults if unset or unreadable."""
    if raw is None:
        return dict(DEFAULT_LEVELS)
    try:
        levels = json.loads(raw)
        return {str(name): level for name, level in levels.items() if level in LEVEL_NAMES}
    except (ValueError, AttributeError):
        print(f"log_buffer: ignoring unreadable log level settings: {raw!r}", file=sys.stderr)
        return dict(DEFAULT_LEVELS)


def apply_levels(levels, previous):
    """Sets each named logger's level; loggers no longer listed go back to inheriting their parent's."""
    for name in set(previous) - set(levels):
        logging.getLogger(name or None).setLevel(logging.NOTSET if name else logging.INFO)
    for name, level in levels.items():
        logging.getLogger(name or None).setLevel(level)
