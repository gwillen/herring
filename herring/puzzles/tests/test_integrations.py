"""
The Discord and Google integrations can't be exercised without credentials, so these tests only
check that their code still loads and wires up against the installed library versions.
"""
import asyncio
from unittest import mock

import aiohttp
import discord
from django.conf import settings
from django.test import SimpleTestCase, TestCase

from herring.celery import app as celery_app
from puzzles import discordbot


class CeleryTests(TestCase):
    def test_tasks_registered(self):
        expected = {'puzzles.tasks.post_answer', 'puzzles.tasks.post_update',
                    'puzzles.tasks.create_puzzle_sheet_and_channel', 'puzzles.tasks.create_round_category',
                    'puzzles.tasks.check_connection_to_messaging', 'puzzles.tasks.process_google_sheets_changes',
                    'puzzles.tasks.add_user_to_puzzle'}
        celery_app.loader.import_default_modules()
        self.assertLessEqual(expected, set(celery_app.tasks))

    def test_messaging_task_is_idle_without_celery_listener(self):
        from puzzles.tasks import check_connection_to_messaging
        with mock.patch('puzzles.tasks.REDIS') as redis:
            check_connection_to_messaging.apply()
        redis.lock.assert_not_called()

    def test_post_update_runs_eagerly(self):
        from puzzles.tasks import post_update
        post_update.delay('no-such-slug', 'tags', 'x')  # returns early when the puzzle is missing


class DiscordBotTests(SimpleTestCase):
    def test_listener_bot_registers_cogs_and_commands(self):
        cogs, commands, slash_commands = asyncio.run(self.set_up_listener_bot())
        self.assertEqual(cogs, {'HerringCog', 'SolvertoolsCog', 'CommandErrorHandler'})
        self.assertLessEqual({'join', 'leave', 'answer', 'anagram'}, commands)
        self.assertIn('join', slash_commands)

    async def set_up_listener_bot(self):
        async with aiohttp.ClientSession() as client:
            bot = discordbot.HerringListenerBot(client)
            await bot.setup_hook()
            guild = discord.Object(id=settings.HERRING_DISCORD_GUILD_ID)
            slash_commands = {c.name for c in bot.tree.get_commands(guild=guild)}
            return set(bot.cogs), {c.name for c in bot.commands}, slash_commands

    def test_announcer_bot_constructs(self):
        self.assertFalse(discordbot.HerringAnnouncerBot().intents.message_content)

