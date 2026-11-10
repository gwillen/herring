from unittest import mock

from django.test import TestCase, override_settings

from dashboard import server_structure
from dashboard.models import DiscordServerSnapshot
from puzzles.tests.helpers import make_superuser, make_user

GUILD_ID = '111'
SECTIONS = {
    'guild': {'id': GUILD_ID, 'name': 'Hunt 2026', 'features': ['COMMUNITY']},
    'roles': [{'id': GUILD_ID, 'name': '@everyone', 'position': 0, 'color': 0, 'permissions': '1024'},
              {'id': '5', 'name': 'Admins', 'position': 2, 'color': 0xff0000, 'permissions': '8', 'hoist': True},
              {'id': '6', 'name': 'Solvers', 'position': 1, 'color': 0, 'permissions': '3072'}],
    'channels': [{'id': '20', 'type': 4, 'name': 'Social', 'position': 1, 'permission_overwrites': []},
                 {'id': '21', 'type': 0, 'name': 'general', 'position': 0, 'parent_id': '20', 'topic': 'chat'},
                 {'id': '22', 'type': 2, 'name': 'Voice 1', 'position': 1, 'parent_id': '20'},
                 {'id': '23', 'type': 0, 'name': 'rules', 'position': 0}],
    'onboarding': {'enabled': True, 'mode': 0, 'prompts': [], 'default_channel_ids': ['21', '23']},
}


class ServerStructureTests(TestCase):
    def test_roles_highest_first_with_permissions(self):
        rows = server_structure.role_rows(SECTIONS)
        self.assertEqual([r['name'] for r in rows], ['Admins', 'Solvers', '@everyone'])
        self.assertEqual(rows[0]['permission_names'], ['administrator'])
        self.assertEqual(rows[1]['permission_names'], ['read_messages', 'send_messages'])
        self.assertTrue(rows[2]['is_everyone'])

    def test_channel_tree(self):
        tree = server_structure.channel_tree(SECTIONS)
        self.assertEqual([(c and c['name'], [ch['name'] for ch in chans]) for c, chans in tree],
                         [(None, ['rules']), ('Social', ['general', 'Voice 1'])])
        self.assertEqual(tree[1][1][1]['type_name'], 'voice')

    def test_onboarding_names_default_channels(self):
        self.assertEqual(server_structure.onboarding_summary(SECTIONS)['default_channel_names'], ['general', 'rules'])


@override_settings(HERRING_ACTIVATE_DISCORD=True)
class DiscordServerViewTests(TestCase):
    def setUp(self):
        self.client.force_login(make_superuser())

    def test_staff_only(self):
        self.client.force_login(make_user())
        self.assertEqual(self.client.get('/dashboard/discord/').status_code, 302)

    @override_settings(HERRING_DISCORD_GUILD_ID=111)
    def test_lists_servers_and_marks_current_one(self):
        async def fake_guilds():
            return [{'id': GUILD_ID, 'name': 'Hunt 2026'}, {'id': '222', 'name': 'Hunt 2027'}], 999
        with mock.patch('dashboard.discord_api.fetch_bot_guilds', fake_guilds):
            response = self.client.get('/dashboard/discord/')
        self.assertContains(response, "current hunt's server", count=1)
        self.assertContains(response, 'client_id=999')

    def test_take_snapshot_saves_raw_sections_and_errors(self):
        async def fake_structure(guild_id):
            return SECTIONS, {'welcome_screen': '404 Unknown Guild Welcome Screen'}
        with mock.patch('dashboard.discord_api.fetch_server_structure', fake_structure):
            response = self.client.post('/dashboard/discord/snapshots/', {'guild_id': GUILD_ID})
        snapshot = DiscordServerSnapshot.objects.get()
        self.assertRedirects(response, f'/dashboard/discord/snapshots/{snapshot.id}/')
        self.assertEqual((snapshot.guild_name, snapshot.sections, list(snapshot.errors)),
                         ('Hunt 2026', SECTIONS, ['welcome_screen']))
        page = self.client.get(response.url)
        self.assertContains(page, 'Solvers')
        self.assertContains(page, 'welcome_screen')

    def test_snapshot_failure_is_reported(self):
        async def broken(guild_id):
            raise RuntimeError('Discord is down')
        with mock.patch('dashboard.discord_api.fetch_server_structure', broken), \
                mock.patch('dashboard.discord_api.fetch_bot_guilds', mock.AsyncMock(return_value=([], 999))):
            response = self.client.post('/dashboard/discord/snapshots/', {'guild_id': GUILD_ID}, follow=True)
        self.assertContains(response, 'Discord is down')
        self.assertFalse(DiscordServerSnapshot.objects.exists())

    @override_settings(HERRING_ACTIVATE_DISCORD=False)
    def test_says_when_discord_is_off(self):
        self.assertContains(self.client.get('/dashboard/discord/'), 'Discord integration is off')
