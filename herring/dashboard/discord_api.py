"""
Reading Discord server structure over Discord's HTTP API, with the bot's
token. No gateway connection: safe to use from the web process. Results are
Discord's raw JSON, so snapshots keep everything Discord returned.
"""
import asyncio
import base64
import io
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
TIMEOUT_SECONDS = 60


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
    """
    ({section: raw JSON}, {section: error text}) for every SNAPSHOT_SECTIONS
    entry, plus the emoji and sticker image files ('expression_files'), so a
    snapshot can recreate them even if the originals are deleted later.
    """
    async with bot_http() as client:
        return await read_structure(client, guild_id)


async def read_structure(client, guild_id):
    results = await asyncio.gather(*(fetch_section(client, path, guild_id) for path in SNAPSHOT_SECTIONS.values()))
    sections, errors = split_results(dict(zip(SNAPSHOT_SECTIONS, results)))
    files, file_errors = split_results(await fetch_expression_files(client, sections))
    return {**sections, 'expression_files': files}, {**errors, **file_errors}


async def fetch_setup_inputs(guild_id, message_limit):
    """For planning a server setup: (sections, errors, usage, bot user ID), with one login."""
    async with bot_http() as client:
        sections, errors = await read_structure(client, guild_id)
        usage = await read_usage(client, guild_id, message_limit)
        return sections, errors, usage, str(client.user.id)


def split_results(results):
    """{name: (data, error)} -> ({name: data} for successes, {name: error} for failures)."""
    return ({name: data for name, (data, error) in results.items() if error is None},
            {name: error for name, (data, error) in results.items() if error is not None})


async def fetch_expression_files(client, sections):
    urls = {f"emoji:{e['id']}": emoji_url(e) for e in sections.get('emojis', [])}
    urls |= {f"sticker:{s['id']}": sticker_url(s) for s in sections.get('stickers', [])}
    results = await asyncio.gather(*(fetch_file(client, url) for url in urls.values()))
    return dict(zip(urls, results))


def emoji_url(emoji):
    return f"https://cdn.discordapp.com/emojis/{emoji['id']}.{'gif' if emoji.get('animated') else 'png'}"


# Sticker format_type -> file extension (1 PNG, 2 APNG, 3 Lottie, 4 GIF).
STICKER_EXTENSIONS = {1: 'png', 2: 'png', 3: 'json', 4: 'gif'}


def sticker_url(sticker):
    extension = STICKER_EXTENSIONS.get(sticker.get('format_type'), 'png')
    host = 'media.discordapp.net' if extension == 'gif' else 'cdn.discordapp.com'
    return f"https://{host}/stickers/{sticker['id']}.{extension}"


async def fetch_file(client, url):
    """({'url', 'content_type', 'data_b64'}, None), or (None, error)."""
    try:
        data = await client.http.get_from_cdn(url)
    except discord.HTTPException as e:
        logger.info("Couldn't download %s: %s", url, e)
        return None, f"{e.status} {e.text}"
    content_type = {'gif': 'image/gif', 'json': 'application/json'}.get(url.rsplit('.', 1)[-1], 'image/png')
    return {'url': url, 'content_type': content_type, 'data_b64': base64.b64encode(data).decode()}, None


async def fetch_template(code):
    """A server template's raw JSON (readable without the bot being in the template's server)."""
    async with bot_http() as client:
        return await client.http.request(Route('GET', '/guilds/templates/{code}', code=code))


async def fetch_usage(guild_id, message_limit):
    """
    How used a server looks: {'human_members', 'human_messages'}. Messages are
    counted only up to message_limit + 1 (enough to know it's over the limit).
    Archived threads aren't counted.
    """
    async with bot_http() as client:
        return await read_usage(client, guild_id, message_limit)


async def read_usage(client, guild_id, message_limit):
    members = await fetch_all_members(client, guild_id)
    channels = await client.http.request(Route('GET', '/guilds/{guild_id}/channels', guild_id=guild_id))
    threads = await client.http.request(Route('GET', '/guilds/{guild_id}/threads/active', guild_id=guild_id))
    messages = await count_human_messages(client, channels + threads['threads'], message_limit + 1)
    return {'human_members': sum(1 for m in members if not m['user'].get('bot')), 'human_messages': messages}


async def fetch_all_members(client, guild_id):
    members, after = [], '0'
    while True:
        page = await client.http.request(Route('GET', '/guilds/{guild_id}/members', guild_id=guild_id),
                                         params={'limit': 1000, 'after': after})
        members += page
        if len(page) < 1000:
            return members
        after = page[-1]['user']['id']


# Channel types that hold messages: text, voice (its text chat), announcement, threads, stage.
MESSAGE_CHANNEL_TYPES = {0, 2, 5, 10, 11, 12, 13}


async def count_human_messages(client, channels, stop_at):
    count = 0
    for channel in (c for c in channels if c['type'] in MESSAGE_CHANNEL_TYPES):
        count += await count_channel_human_messages(client, channel['id'], stop_at - count)
        if count >= stop_at:
            break
    return count


async def count_channel_human_messages(client, channel_id, stop_at):
    count, before = 0, None
    while count < stop_at:
        params = {'limit': 100, **({'before': before} if before else {})}
        page = await client.http.request(Route('GET', '/channels/{channel_id}/messages', channel_id=channel_id),
                                         params=params)
        count += sum(1 for message in page if not message['author'].get('bot'))
        if len(page) < 100:
            break
        before = page[-1]['id']
    return count


async def fetch_section(client, path, guild_id):
    try:
        params = {'with_counts': 'true'} if path == SNAPSHOT_SECTIONS['guild'] else None
        return await client.http.request(Route('GET', path, guild_id=guild_id), params=params), None
    except discord.HTTPException as e:
        logger.info("Snapshot of guild %s: couldn't read %s: %s", guild_id, path, e)
        return None, f"{e.status} {e.text}"


class DiscordSession:
    """
    Synchronous access to Discord's HTTP API for a batch of requests (e.g.
    applying a setup plan from a Celery task): one event loop and one login.
    discord.py's client handles Discord's rate limits.
    """

    def __enter__(self):
        self.loop = asyncio.new_event_loop()
        self.client = discord.Client(intents=discord.Intents.none())
        self.loop.run_until_complete(self.client.login(settings.HERRING_SECRETS['discord-bot-token']))
        return self

    def __exit__(self, *exc_info):
        self.loop.run_until_complete(self.client.close())
        self.loop.close()

    def request(self, method, path, body=None, params=None):
        """Discord's JSON response (None for an empty one)."""
        coroutine = self.client.http.request(Route(method, path), json=body, params=params)
        return self.loop.run_until_complete(asyncio.wait_for(coroutine, TIMEOUT_SECONDS))

    def create_sticker(self, guild_id, body, file):
        sticker_file = discord.File(io.BytesIO(base64.b64decode(file['data_b64'])),
                                    filename=f"sticker.{file['url'].rsplit('.', 1)[-1]}")
        coroutine = self.client.http.create_guild_sticker(guild_id, body, sticker_file, reason=None)
        return self.loop.run_until_complete(asyncio.wait_for(coroutine, TIMEOUT_SECONDS))

    @property
    def bot_user_id(self):
        return str(self.client.user.id)
