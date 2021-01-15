import logging
import os
import environ
import time
import datetime
import signal
import threading
import sys

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
        # Some of this is kind of dumb anyway, handlers are not per-thread, they are per logger or something, and may be used in multiple threads.
        ct = threading.current_thread()
        self.thread_info = [HEROKU_APP_NAME, HEROKU_RELEASE_VERSION, HEROKU_DYNO_NAME, ct.name, ct.ident, ct.native_id]

        # This is a weird place to do this, but I really want to be the very first to know that we're exiting.
        """
        # This is currently disabled because gwillen is concerned it's interfering with other stuff.
        def handle_sigterm(_signo, _stackframe):
            # Can't import this at load or init time, because "django.core.exceptions.AppRegistryNotReady: Apps aren't loaded yet."
            from puzzles.discordbot import DISCORD_ANNOUNCER, do_in_discord

            self.shutdown = True
            now = datetime.datetime.now()
            #do_in_discord(DISCORD_ANNOUNCER.post_message(HERRING_DISCORD_DEBUG_CHANNEL, f"`[{now.strftime('%m/%d/%Y, %H:%M:%S')}] ChatLogHandler shutting down, suppressing logs until exit to reduce spam. (You can still find them in the PaperTrail log viewer on Heroku.) Thread info: {self.thread_info}`"))
            self.old_handler(_signo, _stackframe)
            sys.exit(0)

        if (threading.current_thread() == threading.main_thread()) and (self.old_handler != handle_sigterm):
            self.old_handler = signal.signal(signal.SIGTERM, handle_sigterm)
        """

    def emit(self, record):
        if self.shutdown:
            return

        try:
            # Can't import this at load or init time, because "django.core.exceptions.AppRegistryNotReady: Apps aren't loaded yet."
            from puzzles.discordbot import DISCORD_ANNOUNCER, do_in_discord_nonblocking
            import discord

            if self.startup:
                self.startup = False
                start_time = datetime.datetime.fromtimestamp(self.start_time)
                #do_in_discord_nonblocking(DISCORD_ANNOUNCER.post_message(HERRING_DISCORD_DEBUG_CHANNEL, f"`[{start_time.strftime('%m/%d/%Y, %H:%M:%S')}] ChatLogHandler starting up, suppressing logs for the next {SUPPRESS_STARTUP_SECONDS} seconds to reduce spam. (You can still find them in the PaperTrail log viewer on Heroku.) Thread info: {self.thread_info} Signal handler info: {self.old_handler}`"))

            now = time.time()
            if now < self.start_time + SUPPRESS_STARTUP_SECONDS:
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
            do_in_discord_nonblocking(DISCORD_ANNOUNCER.post_message(HERRING_DISCORD_DEBUG_CHANNEL, "", embed=embed))
        except Exception as e:
            self.shutdown = True
            # Safe to call logging.error from here once shutdown is True, since we will not try to do anything from emit().
            logging.error(f"Oh no, exception in ChatLogHandler.emit -- we will stop logging to discord until server restart. Details: {e}")
