"""
Read-only look at the configured Discord server: categories, channels, and
(optionally) recent messages, fetched over Discord's HTTP API with the bot's
token. Changes nothing.

    python herring/manage.py discord_inspect [--messages N]
"""
import asyncio

import discord
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Show the configured Discord server's categories, channels and recent messages (read-only)"

    def add_arguments(self, parser):
        parser.add_argument('--messages', type=int, default=0,
                            help="also show this many recent messages per text channel")

    def handle(self, *args, **options):
        if not settings.HERRING_ACTIVATE_DISCORD:
            raise CommandError("ACTIVATE_DISCORD is off")
        for line in asyncio.run(inspect_guild(options['messages'])):
            self.stdout.write(line)


async def inspect_guild(message_count):
    client = discord.Client(intents=discord.Intents.none())
    await client.login(settings.HERRING_SECRETS['discord-bot-token'])
    try:
        guild = await client.fetch_guild(settings.HERRING_DISCORD_GUILD_ID)
        channels = await guild.fetch_channels()
        lines = [f"Guild: {guild.name} ({guild.id})", f"Bot user: {client.user}"]
        for category, members in group_by_category(channels):
            lines.append(f"[{category.name if category else 'no category'}]")
            for channel in members:
                lines.extend(await describe_channel(channel, message_count))
        return lines
    finally:
        await client.close()


def group_by_category(channels):
    categories = sorted((c for c in channels if isinstance(c, discord.CategoryChannel)), key=lambda c: c.position)
    others = sorted((c for c in channels if not isinstance(c, discord.CategoryChannel)), key=lambda c: c.position)
    groups = [(None, [c for c in others if c.category_id is None])]
    return groups + [(cat, [c for c in others if c.category_id == cat.id]) for cat in categories]


async def describe_channel(channel, message_count):
    topic = getattr(channel, 'topic', None)
    lines = [f"  {channel.type}: #{channel.name} ({channel.id})" + (f" topic: {topic!r}" if topic else "")
             + f" overwrites: {len(channel.overwrites)}"]
    if message_count and isinstance(channel, discord.TextChannel):
        messages = [m async for m in channel.history(limit=message_count)]
        lines.extend(f"      {m.created_at:%Y-%m-%d %H:%M:%S} {m.author}: {m.content[:150]!r}"
                     + (f" [embed: {m.embeds[0].description[:100]!r}]" if m.embeds and m.embeds[0].description else "")
                     for m in reversed(messages))
    return lines
