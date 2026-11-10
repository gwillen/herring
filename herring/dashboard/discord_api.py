"""
Reading Discord server structure over Discord's HTTP API, with the bot's
token. No gateway connection: safe to use from the web process. Results are
Discord's raw JSON, so snapshots keep everything Discord returned.
"""
import asyncio
import logging
from contextlib import asynccontextmanager

import discord
from discord.http import Route
from django.conf import settings

logger = logging.getLogger(__name__)

# Everything a server snapshot records, as {section name: API path}. Sections
# that fail (e.g. the welcome screen of a server without Community enabled)
# are recorded as errors rather than failing the whole snapshot.
SNAPSHOT_SECTIONS = {
    'guild': '/guilds/{guild_id}',
    'roles': '/guilds/{guild_id}/roles',
    'channels': '/guilds/{guild_id}/channels',
    'onboarding': '/guilds/{guild_id}/onboarding',
    'welcome_screen': '/guilds/{guild_id}/welcome-screen',
    'emojis': '/guilds/{guild_id}/emojis',
    'stickers': '/guilds/{guild_id}/stickers',
    'auto_moderation_rules': '/guilds/{guild_id}/auto-moderation/rules',
}
# An unresponsive Discord shouldn't hold a web request forever.
TIMEOUT_SECONDS = 30


@asynccontextmanager
async def bot_http():
    """The bot's HTTP client, logged in, and closed afterwards."""
    client = discord.Client(intents=discord.Intents.none())
    await client.login(settings.HERRING_SECRETS['discord-bot-token'])
    try:
        yield client
    finally:
        await client.close()


def run(coroutine):
    return asyncio.run(asyncio.wait_for(coroutine, TIMEOUT_SECONDS))


async def fetch_bot_guilds():
    """The servers the bot is in (raw JSON), and the bot's application ID (for invite links)."""
    async with bot_http() as client:
        guilds = await client.http.request(Route('GET', '/users/@me/guilds'))
        return guilds, client.application_id


async def fetch_server_structure(guild_id):
    """({section: raw JSON}, {section: error text}) for every SNAPSHOT_SECTIONS entry."""
    async with bot_http() as client:
        results = await asyncio.gather(*(fetch_section(client, path, guild_id) for path in SNAPSHOT_SECTIONS.values()))
    sections = dict(zip(SNAPSHOT_SECTIONS, results))
    return ({name: data for name, (data, error) in sections.items() if error is None},
            {name: error for name, (data, error) in sections.items() if error is not None})


async def fetch_section(client, path, guild_id):
    try:
        params = {'with_counts': 'true'} if path == SNAPSHOT_SECTIONS['guild'] else None
        return await client.http.request(Route('GET', path, guild_id=guild_id), params=params), None
    except discord.HTTPException as e:
        logger.info("Snapshot of guild %s: couldn't read %s: %s", guild_id, path, e)
        return None, f"{e.status} {e.text}"
