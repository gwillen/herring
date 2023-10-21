from django.core.management.base import BaseCommand
from puzzles.discordbot import run_listener_bot
from django.conf import settings
import asyncio

class Command(BaseCommand):
    help = "Runs the discord listener bot (forever)"

    def handle(self, *args, **options):
        if settings.HERRING_ACTIVATE_DISCORD and settings.HERRING_ENABLE_STANDALONE_DISCORD:
            self.stdout.write(self.style.SUCCESS("Launching the discord listener bot..."))
            asyncio.run(run_listener_bot())
        else:
            self.stdout.write(self.style.WARNING("Not launching the discord listener bot, because either ACTIVATE_DISCORD or ENABLE_STANDALONE_DISCORD is not set."))
