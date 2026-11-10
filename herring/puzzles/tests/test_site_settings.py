import asyncio
from unittest import mock

from django.test import TestCase, override_settings

from puzzles import discordbot, site_settings
from puzzles.models import Round, SiteSettingChange
from .helpers import make_puzzle, make_round, make_superuser, make_user, set_site_settings


class SiteSettingsTests(TestCase):
    def test_starts_empty(self):
        self.assertEqual((site_settings.guild_id(), site_settings.hunt_id()), (None, 0))

    @override_settings(HERRING_ACTIVATE_DISCORD=True, HERRING_ACTIVATE_GAPPS=False)
    def test_environment_switches_are_hard_limits(self):
        self.assertTrue(site_settings.discord_on())
        self.assertFalse(site_settings.gapps_on())
        set_site_settings(discord_enabled=False, gapps_enabled=True)
        self.assertFalse(site_settings.discord_on())
        self.assertFalse(site_settings.gapps_on())  # still off: the environment says so

    def test_changes_are_recorded(self):
        user = make_superuser()
        self.assertEqual(site_settings.update(user, hunt_id=2027, discord_guild_id=None), ['hunt_id'])
        change = SiteSettingChange.objects.get()
        self.assertEqual((change.field, change.old_value, change.new_value, change.changed_by), ('hunt_id', 0, 2027, user))

    def test_new_rounds_belong_to_the_current_hunt(self):
        set_site_settings(hunt_id=2027)
        self.assertEqual(make_round().hunt_id, 2027)

    def test_readable_from_async_code(self):
        async def read():
            return site_settings.current()
        self.assertEqual(asyncio.run(read()).discord_guild_id, None)  # via the reader thread

    def test_puzzle_list_shows_only_the_current_hunt(self):
        self.client.force_login(make_user())
        make_puzzle(make_round(name='This year'))
        Round.objects.create(name='Last year', number=1, hunt_id=2026)
        rounds = self.client.get('/puzzles/').json()['rounds']
        self.assertEqual([r['name'] for r in rounds], ['This year'])


@override_settings(HERRING_ACTIVATE_DISCORD=True)
class DiscordSwitchTests(TestCase):
    def test_commands_say_the_integration_is_off(self):
        set_site_settings(discord_enabled=False)
        with self.assertRaisesMessage(discordbot.commands.CheckFailure, 'switched off'):
            discordbot.integration_is_on(mock.Mock())
        set_site_settings(discord_enabled=True)
        self.assertTrue(discordbot.integration_is_on(mock.Mock()))

    def test_bots_disconnect_when_switched_off(self):
        set_site_settings(discord_enabled=False)
        bot, on_close = mock.Mock(**{'is_closed.side_effect': [False, True], 'close': mock.AsyncMock()}), mock.Mock()
        with mock.patch.object(discordbot, 'DISABLE_CHECK_SECONDS', 0), \
                mock.patch.object(discordbot.site_settings, 'discord_on', return_value=False):
            asyncio.run(discordbot.close_when_disabled(bot, on_close))
        bot.close.assert_awaited_once()
        on_close.assert_called_once()

    def test_discord_link_explains_when_no_server_is_set(self):
        self.client.force_login(make_user())
        puzzle = make_puzzle(make_round())
        self.assertContains(self.client.get(f'/disc/{puzzle.id}/0'), 'no Discord server is set', status_code=503)


@override_settings(HERRING_ACTIVATE_DISCORD=True, HERRING_ACTIVATE_GAPPS=False)
class SettingsPageTests(TestCase):
    def setUp(self):
        self.client.force_login(make_superuser())
        guilds = mock.AsyncMock(return_value=([{'id': '555', 'name': 'Hunt 2027'}], 1))
        categories = mock.AsyncMock(return_value=[{'id': '9', 'name': 'Staff', 'type': 4, 'position': 0}])
        self.enterContext(mock.patch('dashboard.discord_api.fetch_bot_guilds', guilds))
        self.enterContext(mock.patch('dashboard.discord_api.fetch_categories', categories))

    def test_page_shows_choices_and_hard_switches(self):
        set_site_settings(discord_guild_id=555)
        page = self.client.get('/dashboard/settings/')
        self.assertContains(page, 'Hunt 2027 (555)')
        self.assertContains(page, 'Staff')
        self.assertContains(page, 'ACTIVATE_GAPPS')  # Sheets is off for the deployment

    def test_save(self):
        response = self.client.post('/dashboard/settings/save/', {
            'hunt_id': '2027', 'discord_enabled': 'on', 'discord_guild_id': '555', 'protected_category_ids': ['9']})
        self.assertRedirects(response, '/dashboard/settings/', fetch_redirect_response=False)
        current = site_settings.current()
        self.assertEqual((current.hunt_id, current.discord_guild_id, current.protected_category_ids),
                         (2027, 555, frozenset({'9'})))

    def test_bad_hunt_id_is_refused(self):
        self.client.post('/dashboard/settings/save/', {'hunt_id': 'next year'})
        self.assertEqual(site_settings.hunt_id(), 0)

    def test_unchecking_turns_discord_off(self):
        self.client.post('/dashboard/settings/save/', {'hunt_id': '0', 'discord_guild_id': ''})
        self.assertFalse(site_settings.discord_on())
