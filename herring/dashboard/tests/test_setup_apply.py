from unittest import mock

from django.test import TestCase, override_settings

from dashboard import setup_apply, setup_flow, setup_plan
from dashboard.models import DiscordServerSnapshot, SetupPlan
from puzzles.tests.helpers import make_superuser
from .setup_fixtures import BOT_ID, SOURCE, TARGET, FakeDiscord

NEW_SERVER_USAGE = {'age_days': 0, 'human_members': 1, 'human_messages': 0}


def make_plan(usage=NEW_SERVER_USAGE, user=None):
    source = DiscordServerSnapshot.objects.create(guild_id=1, guild_name='Hunt 2026', herring_version='t', sections=SOURCE)
    target = DiscordServerSnapshot.objects.create(guild_id=100, guild_name='New server', herring_version='t', sections=TARGET)
    setup = setup_plan.SetupInput(SOURCE, TARGET, 'You Are Being Rage Limited', BOT_ID)
    return setup_flow.save_plan(source, target, setup, dict(usage), user)


def apply(plan, keys, discord):
    setup_apply.queue_operations(plan, keys)
    with mock.patch('dashboard.discord_api.DiscordSession') as session:
        session.return_value.__enter__.return_value = discord
        setup_apply.apply_setup_plan(plan.id, None)
    return {op.key: op for op in SetupPlan.objects.get(id=plan.id).operations.all()}


class ApplyTests(TestCase):
    def test_queueing_pulls_in_dependencies(self):
        plan = make_plan()
        queued = setup_apply.queue_operations(plan, ['channel.create.14'])
        self.assertEqual(queued, ['channel.create.14', 'role.create.2'])

    def test_applies_everything_in_order_with_created_ids(self):
        plan, discord = make_plan(), FakeDiscord()
        results = apply(plan, [op.key for op in plan.operations.all()], discord)
        self.assertEqual({k for k, op in results.items() if op.status != 'applied'}, set(),
                         {k: op.error for k, op in results.items() if op.error})
        created_admin = SetupPlan.objects.get(id=plan.id).id_map[setup_plan.ref('role', '2')]
        announcements = next(c for c in discord.state['channels'] if c['name'] == 'announcements')
        self.assertEqual(announcements['permission_overwrites'][0]['id'], created_admin)
        self.assertNotIn('Voice Channels', [c['name'] for c in discord.state['channels']])

    def test_failure_skips_dependents_only(self):
        plan = make_plan()
        results = apply(plan, ['channel.create.14', 'channel.create.12'], FakeDiscord(fail={'/guilds/100/roles'}))
        self.assertEqual(results['role.create.2'].status, 'failed')
        self.assertIn('Discord said no', results['role.create.2'].error)
        self.assertEqual(results['channel.create.14'].status, 'skipped')
        self.assertEqual(results['channel.create.12'].status, 'applied')

    def test_preconditions_are_rechecked(self):
        plan = make_plan()
        discord = FakeDiscord(messages={'113': [{'id': '1'}]})
        discord.state['roles'].append({'id': '555', 'name': 'Solver', 'position': 1})
        results = apply(plan, ['role.create.3', 'channel.delete.113'], discord)
        self.assertEqual(results['role.create.3'].error, "Not applied: there's already one named 'Solver'")
        self.assertEqual(results['channel.delete.113'].error, "Not applied: it has messages")

    def test_bot_role_must_be_on_top(self):
        plan = make_plan()
        discord = FakeDiscord()
        discord.state['roles'].append({'id': '102', 'name': 'Owner', 'position': 5})
        results = apply(plan, ['role.order'], discord)
        self.assertIn("bot's role isn't at the top", results['role.order'].error)

    def test_applied_operations_are_not_repeated(self):
        plan, discord = make_plan(), FakeDiscord()
        apply(plan, ['server.name'], discord)
        apply(plan, ['server.name'], discord)
        self.assertEqual(sum(1 for r in discord.requests if r[2] == {'name': 'You Are Being Rage Limited'}), 1)


class SafetyTests(TestCase):
    def test_usage_warnings(self):
        self.assertEqual(setup_flow.usage_warnings(NEW_SERVER_USAGE), [])
        warnings = setup_flow.usage_warnings({'age_days': 400, 'human_members': 40, 'human_messages': 51})
        self.assertEqual(len(warnings), 3)

    def test_bot_role_notice(self):
        self.assertEqual(setup_flow.bot_role_notices(TARGET, BOT_ID), [])
        low_bot = {**TARGET, 'roles': TARGET['roles'] + [{'id': '7', 'name': 'Mods', 'position': 4}]}
        self.assertEqual(len(setup_flow.bot_role_notices(low_bot, BOT_ID)), 1)


@override_settings(HERRING_ACTIVATE_DISCORD=True)
class SetupViewTests(TestCase):
    def setUp(self):
        self.user = make_superuser()
        self.client.force_login(self.user)

    def test_plan_page(self):
        plan = make_plan()
        page = self.client.get(f'/dashboard/discord/setup/{plan.id}/')
        self.assertContains(page, 'Setting up You Are Being Rage Limited')
        self.assertContains(page, 'Create role &#x27;Admin&#x27;')
        self.assertContains(page, '(129 characters in all)', count=0)  # nothing long in this plan

    def test_used_server_needs_confirmation(self):
        plan = make_plan(usage={'age_days': 400, 'human_members': 1, 'human_messages': 0})
        with mock.patch('dashboard.setup_apply.apply_setup_plan.delay') as delay:
            self.client.post(f'/dashboard/discord/setup/{plan.id}/apply/', {'operation': ['server.name']})
            delay.assert_not_called()
            self.client.post(f'/dashboard/discord/setup/{plan.id}/apply/', {'operation': ['server.name'], 'acknowledge': 'yes'})
            delay.assert_called_once_with(plan.id, self.user.id)
        self.assertEqual(SetupPlan.objects.get(id=plan.id).acknowledged_by, self.user)
