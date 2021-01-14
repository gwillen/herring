import logging
import os
import environ
import time
import datetime
import signal
import threading

from herring.settings import HERRING_ACTIVATE_DISCORD, HERRING_DISCORD_DEBUG_CHANNEL, HEROKU_APP_NAME, HEROKU_DYNO_NAME, HEROKU_RELEASE_VERSION

MAX_DISCORD_EMBED_LEN = 2048
SUPPRESS_STARTUP_SECONDS = 150

class ChatLogHandler(logging.Handler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.start_time = time.time()
        self.startup = True
        self.shutdown = False
        self.old_handler = "<none>"  # distinguish temporarily from signal returning None

        # This is a weird place to do this, but I really want to be the very first to know that we're exiting.
        def handle_sigterm(_signo, _stackframe):
            self.shutdown = True
            now = datetime.datetime.now()
            do_in_discord(DISCORD_ANNOUNCER.post_message(HERRING_DISCORD_DEBUG_CHANNEL, f"`[{now.strftime('%m/%d/%Y, %H:%M:%S')}] ChatLogHandler shutting down, suppressing logs until exit to reduce spam. (You can still find them in the PaperTrail log viewer on Heroku.) Thread info: {self.thread_info}`"))
            sys.exit(0)

        if threading.current_thread() == threading.main_thread():
            self.old_handler = signal.signal(signal.SIGTERM, handle_sigterm)

    def emit(self, record):
        # Can't import this at load or init time, because "django.core.exceptions.AppRegistryNotReady: Apps aren't loaded yet."
        from puzzles.discordbot import DISCORD_ANNOUNCER, do_in_discord
        import discord

        if self.startup:
            self.startup = False
            ct = threading.current_thread()
            self.thread_info = [HEROKU_APP_NAME, HEROKU_RELEASE_VERSION, HEROKU_DYNO_NAME, ct.name, ct.ident, ct.native_id]
            start_time = datetime.datetime.fromtimestamp(self.start_time)
            do_in_discord(DISCORD_ANNOUNCER.post_message(HERRING_DISCORD_DEBUG_CHANNEL, f"`[{start_time.strftime('%m/%d/%Y, %H:%M:%S')}] ChatLogHandler starting up, suppressing logs for the next {SUPPRESS_STARTUP_SECONDS} seconds to reduce spam. (You can still find them in the PaperTrail log viewer on Heroku.) Thread info: {self.thread_info} Signal handler info: {self.old_handler}`"))

        now = time.time()
        if self.shutdown or (now < self.start_time + SUPPRESS_STARTUP_SECONDS):
            return

        # We could do this with a Filter, but there's no real need -- it would just be a function with the same code, and
        #   then we'd have to configure things to use it. Easier to just do it right here.

        # Suppress 404s:
        if record.levelname == "WARNING" and record.name == "django.request":
            return

        # Suppress the most frequent cause of asyncio warnings about blocking event loop:
        if record.levelname == "WARNING" and record.name == "asyncio" and "keep_mutex" in record.message:
            return

        logging.info(f"About to emit object to discord: {record} of type {type(record)}")
        formatted_record = self.format(record)
        truncated_record = formatted_record[:MAX_DISCORD_EMBED_LEN - 50]  # leave plenty of space for markdown
        if len(truncated_record) < len(formatted_record):
            truncated_record += " ..."
        truncated_record += f" ({HEROKU_DYNO_NAME}, {HEROKU_RELEASE_VERSION})"
        embed = discord.Embed(description=discord.utils.escape_markdown(truncated_record)[:MAX_DISCORD_EMBED_LEN])
        do_in_discord(DISCORD_ANNOUNCER.post_message(HERRING_DISCORD_DEBUG_CHANNEL, "", embed=embed))
