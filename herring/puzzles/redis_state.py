"""
Shared Redis state: the client, and Discord connection status, which the
processes that hold Discord connections (Celery workers, the listener bot)
report here so the web process can show it without connecting to Discord.
"""
import logging
from functools import cache
from urllib.parse import urlparse

from django.conf import settings
from redis import Redis

# Each reporter writes its status every HERRING_DISCORD_STATUS_INTERVAL_SECONDS;
# a status expires if it isn't refreshed, so a dead process shows up as "not
# connected".
DISCORD_STATUS_INTERVAL_SECONDS = settings.HERRING_DISCORD_STATUS_INTERVAL_SECONDS
DISCORD_STATUS_TTL_SECONDS = 3 * DISCORD_STATUS_INTERVAL_SECONDS
DISCORD_COMPONENTS = ('announcer', 'listener')


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


def _status_key(component):
    return f'herring:discord-status:{component}'


def set_discord_status(component, connected):
    """Record whether `component` ('announcer' or 'listener') is connected to Discord."""
    assert component in DISCORD_COMPONENTS, component
    redis_client().set(_status_key(component), '1' if connected else '0', ex=DISCORD_STATUS_TTL_SECONDS)


def discord_connected():
    """True if every Discord component reported itself connected recently."""
    values = redis_client().mget([_status_key(c) for c in DISCORD_COMPONENTS])
    logging.debug("discord status from redis: %s", dict(zip(DISCORD_COMPONENTS, values)))
    return all(value == b'1' for value in values)
