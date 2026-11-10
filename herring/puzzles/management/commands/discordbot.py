import asyncio
import time

from django.conf import settings
from django.core.management.base import BaseCommand

from puzzles import site_settings
from puzzles.discordbot import run_listener_bot

# While the integration is switched off in the dashboard, check this often whether it's back on.
OFF_CHECK_SECONDS = 30

class Command(BaseCommand):
    help = "Runs the discord listener bot (forever)"

    def handle(self, *args, **options):
        if settings.HERRING_ACTIVATE_DISCORD and settings.HERRING_ENABLE_STANDALONE_DISCORD:
            self.stdout.write(self.style.SUCCESS("Launching the discord listener bot..."))
            run_while_switched_on()
        else:
            self.stdout.write(self.style.WARNING("Not launching the discord listener bot, because either ACTIVATE_DISCORD or ENABLE_STANDALONE_DISCORD is not set."))


def run_while_switched_on():
    """Runs the bot whenever the integration is switched on in the dashboard (the bot stops itself when it's switched off)."""
    while True:
        if site_settings.discord_on():
            asyncio.run(run_listener_bot())
        else:
            time.sleep(OFF_CHECK_SECONDS)
