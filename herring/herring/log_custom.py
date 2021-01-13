import logging
import os
import environ
import time
import signal
import threading

from herring.settings import HERRING_ACTIVATE_DISCORD, HERRING_DISCORD_DEBUG_CHANNEL, HEROKU_APP_NAME, HEROKU_DYNO_NAME

MAX_DISCORD_EMBED_LEN = 2048
SUPPRESS_STARTUP_SECONDS = 30

class ChatLogHandler(logging.Handler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.start_time = time.time()
        self.startup = True
        self.shutdown = False

        # This is a weird place to do this, but I really want to be the very first to know that we're exiting.
        def handle_sigterm():
            self.shutdown = True
            do_in_discord(DISCORD_ANNOUNCER.post_message(HERRING_DISCORD_DEBUG_CHANNEL, f"`ChatLogHandler shutting down, suppressing logs until exit to reduce spam. (You can still find them in the PaperTrail log viewer on Heroku.) Thread info: {thread_info}`"))
            sys.exit(0)

        if threading.current_thread() == threading.main_thread():
            signal.signal(signal.SIGTERM, handle_sigterm)

    def emit(self, record):
        # Can't import this at load or init time, because "django.core.exceptions.AppRegistryNotReady: Apps aren't loaded yet."
        from puzzles.discordbot import DISCORD_ANNOUNCER, do_in_discord
        import discord

        if self.startup:
            self.startup = False
            ct = threading.current_thread()
            thread_info = [HEROKU_APP_NAME, HEROKU_DYNO_NAME, ct.name, ct.ident, ct.native_id]
            do_in_discord(DISCORD_ANNOUNCER.post_message(HERRING_DISCORD_DEBUG_CHANNEL, f"`ChatLogHandler starting up, suppressing logs for the next {SUPPRESS_STARTUP_SECONDS} seconds to reduce spam. (You can still find them in the PaperTrail log viewer on Heroku.) Thread info: {thread_info}`"))

        now = time.time()
        if self.shutdown or (now < self.start_time + SUPPRESS_STARTUP_SECONDS):
            return

        # We could do this with a Filter, but there's no real need -- it would just be a function with the same code, and
        #   then we'd have to configure things to use it. Easier to just do it right here.

        # Suppress 404s:
        if record.levelname == "WARNING" and record.name == "django.request":
            return

        logging.info(f"About to emit object to discord: {record} of type {type(record)}")
        embed = discord.Embed(description=discord.utils.escape_markdown(self.format(record))[:MAX_DISCORD_EMBED_LEN])
        do_in_discord(DISCORD_ANNOUNCER.post_message(HERRING_DISCORD_DEBUG_CHANNEL, "", embed=embed))
