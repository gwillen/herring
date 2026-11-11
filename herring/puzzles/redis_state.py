"""
Shared Redis state: the client, and Discord connection status, which the
processes that hold Discord connections (Celery workers, the listener bot)
report here so the web process can show it without connecting to Discord.
"""
import json
import logging
import time
from functools import cache
from urllib.parse import urlparse

from django.conf import settings
from redis import Redis

logger = logging.getLogger(__name__)

# The Discord listener bot (the one long-lived connection) records a heartbeat
# every HERRING_DISCORD_STATUS_INTERVAL_SECONDS; it expires if not refreshed, so
# a stopped listener shows up as "not connected".
DISCORD_STATUS_INTERVAL_SECONDS = settings.HERRING_DISCORD_STATUS_INTERVAL_SECONDS
DISCORD_STATUS_TTL_SECONDS = 3 * DISCORD_STATUS_INTERVAL_SECONDS
LISTENER_HEARTBEAT_KEY = 'herring:discord-listener-heartbeat'


@cache
def redis_client():
    # Every instance of the Redis object creates its own connection pool,
    # and Redis connections on Heroku are limited! So sharing this Redis
    # instance is possibly important. TBH, I have no idea why we run out of
    # Redis connections so quickly; it's possible this doesn't help at all.
    ssl_kwargs = {}
    url = urlparse(settings.REDIS_URL)
    if url.scheme == "rediss":
        ssl_kwargs["ssl_cert_reqs"] = None  # allow self-signed certificates
    return Redis.from_url(settings.REDIS_URL, max_connections=1, **ssl_kwargs)


def record_listener_heartbeat(connected, process):
    heartbeat = {'at': time.time(), 'connected': connected, 'process': process}
    redis_client().set(LISTENER_HEARTBEAT_KEY, json.dumps(heartbeat), ex=DISCORD_STATUS_TTL_SECONDS)


def listener_heartbeat():
    """The listener's latest heartbeat ({'at', 'connected', 'process', 'seconds_ago'}), or None if it's gone quiet."""
    raw = redis_client().get(LISTENER_HEARTBEAT_KEY)
    if raw is None:
        return None
    heartbeat = json.loads(raw)
    return heartbeat | {'seconds_ago': round(time.time() - heartbeat['at'])}


def discord_connected():
    """True if the listener bot recently reported itself connected."""
    heartbeat = listener_heartbeat()
    logger.debug("Discord listener heartbeat: %s", heartbeat)
    return bool(heartbeat and heartbeat['connected'])
