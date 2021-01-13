import logging
import os
import environ

from herring.settings import HERRING_ACTIVATE_DISCORD, HERRING_DISCORD_DEBUG_CHANNEL

MAX_DISCORD_EMBED_LEN = 2048

class ChatLogHandler(logging.Handler):
    def emit(self, record):
        if HERRING_ACTIVATE_DISCORD:
            # Can't import this at load time because "django.core.exceptions.AppRegistryNotReady: Apps aren't loaded yet."
            from puzzles.discordbot import DISCORD_ANNOUNCER, do_in_discord
            import discord
            embed = discord.Embed(description=self.format(record)[:MAX_DISCORD_EMBED_LEN])
            do_in_discord(DISCORD_ANNOUNCER.post_message(HERRING_DISCORD_DEBUG_CHANNEL, "", embed=embed))
