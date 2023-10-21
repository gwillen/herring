from django.core.management.base import BaseCommand
from puzzles.discordbot import run_listener_bot
import asyncio

class Command(BaseCommand):
    help = "Runs the discord listener bot (forever)"

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Launching the discord listener bot..."))
        asyncio.run(run_listener_bot())
