"""
The Discord and Google integrations can't be exercised without credentials, so these tests only
check that their code still loads and wires up against the installed library versions.
"""
import asyncio
from unittest import mock

import aiohttp
import discord
from django.conf import settings
from django.test import SimpleTestCase, TestCase, override_settings

from herring.celery import app as celery_app
from puzzles import discordbot, redis_state
from .helpers import make_user


class CeleryTests(TestCase):
    def test_tasks_registered(self):
        expected = {'puzzles.tasks.post_answer', 'puzzles.tasks.post_update',
                    'puzzles.tasks.create_puzzle_sheet_and_channel', 'puzzles.tasks.create_round_category',
                    'puzzles.tasks.check_connection_to_messaging', 'puzzles.tasks.process_google_sheets_changes',
                    'puzzles.tasks.add_user_to_puzzle', 'puzzles.tasks.report_discord_status',
                    'puzzles.tasks.post_discord_message', 'puzzles.tasks.post_debug_message'}
        celery_app.loader.import_default_modules()
        self.assertLessEqual(expected, set(celery_app.tasks))

    def test_messaging_task_is_idle_without_celery_listener(self):
        from puzzles.tasks import check_connection_to_messaging
        with mock.patch('puzzles.tasks.redis_client') as redis_client:
            check_connection_to_messaging.apply()
        redis_client.assert_not_called()

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



class LazyAnnouncerTests(SimpleTestCase):
    def counting_factory(self, result):
        calls = []
        return calls, lambda: calls.append(1) or result

    def test_creates_once_and_forwards_attributes(self):
        calls, factory = self.counting_factory(mock.Mock(name='bot'))
        announcer = discordbot.LazyAnnouncer(factory)
        announcer.post_message('chan', 'hi')
        announcer.post_message('chan', 'again')
        self.assertEqual(len(calls), 1)
        self.assertEqual(announcer.get().post_message.call_count, 2)

    def test_failed_creation_is_not_retried_until_reset(self):
        calls, factory = self.counting_factory(None)
        announcer = discordbot.LazyAnnouncer(factory)
        self.assertIsNone(announcer.get())
        self.assertIsNone(announcer.get())
        announcer.reset()
        announcer.get()
        self.assertEqual(len(calls), 2)

    def test_use_during_creation_raises(self):
        announcer = discordbot.LazyAnnouncer(lambda: announcer.get())
        with self.assertRaises(RuntimeError):
            announcer.get()

    def test_do_in_discord_resets_dead_bot(self):
        dead_bot = mock.Mock(**{'do_in_loop.side_effect': RuntimeError('dead')})
        with mock.patch.object(discordbot, 'DISCORD_ANNOUNCER', discordbot.LazyAnnouncer(lambda: dead_bot)):
            with self.assertRaises(RuntimeError):
                discordbot.do_in_discord(None)
            self.assertIs(discordbot.DISCORD_ANNOUNCER._bot, discordbot.LazyAnnouncer._NOT_CREATED)


class DiscordStatusTests(SimpleTestCase):
    def connected_with(self, values):
        with mock.patch('puzzles.redis_state.redis_client') as redis_client:
            redis_client.return_value.mget.return_value = values
            return redis_state.discord_connected()

    def test_connected_only_if_every_component_reported_connected(self):
        self.assertTrue(self.connected_with([b'1', b'1']))
        self.assertFalse(self.connected_with([b'1', b'0']))
        self.assertFalse(self.connected_with([b'1', None]))  # expired: the process stopped reporting

    def test_report_discord_status_records_announcer(self):
        from puzzles import tasks
        with mock.patch.object(tasks, 'announcer_is_ready', return_value=True), \
                mock.patch.object(tasks, 'set_discord_status') as set_status:
            tasks.report_discord_status()
        set_status.assert_called_once_with('announcer', True)


@override_settings(HERRING_ACTIVATE_DISCORD=True, HERRING_ACTIVATE_GAPPS=False)
class WebProcessDiscordTests(TestCase):
    """The web process must never create a Discord connection of its own."""

    def setUp(self):
        from puzzles.tasks import get_service_status
        get_service_status.cache_clear()
        self.addCleanup(get_service_status.cache_clear)
        self.client.force_login(make_user())

    def test_page_data_reads_status_from_redis_without_announcer(self):
        def no_announcer_here():
            raise AssertionError("web request tried to create the announcer bot")
        with mock.patch.object(discordbot, 'DISCORD_ANNOUNCER', discordbot.LazyAnnouncer(no_announcer_here)), \
                mock.patch('puzzles.tasks.discord_connected', return_value=True):
            data = self.client.get('/puzzles/').json()
        self.assertEqual(data['settings']['service_status']['discord'], True)
