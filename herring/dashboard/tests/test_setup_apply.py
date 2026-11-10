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
    def test_unticked_operations_stay_unapplied(self):
        plan, discord = make_plan(), FakeDiscord()
        discord.state['roles'][1]['position'] = 10
        results = apply(plan, [op.key for op in plan.operations.all() if op.default_selected], discord)
        self.assertEqual(results['category.create.30'].status, 'pending')
        self.assertNotIn('Spare', [c['name'] for c in discord.state['channels']])
        self.assertEqual(results['channel.order'].status, 'applied')

    def test_queueing_pulls_in_dependencies(self):
        plan = make_plan()
        queued = setup_apply.queue_operations(plan, ['channel.create.14'])
        self.assertEqual(queued, ['channel.create.14', 'role.create.2'])

    def test_applies_everything_in_order_with_created_ids(self):
        plan, discord = make_plan(), FakeDiscord()
        discord.state['roles'][1]['position'] = 10  # someone dragged the bot's role to the top
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

    def test_bot_role_must_be_on_top_and_numbered_above_the_roles(self):
        results = apply(make_plan(), ['role.order'], FakeDiscord())  # new roles all at 1, like Discord does
        self.assertIn("drag the bot's role to the very top", results['role.order'].error)

    def test_role_order_applies_once_bot_role_is_renumbered(self):
        discord = FakeDiscord()
        discord.state['roles'][1]['position'] = 10
        self.assertEqual(apply(make_plan(), ['role.order'], discord)['role.order'].status, 'applied')

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
        self.assertEqual(len(setup_flow.bot_role_notices(TARGET, BOT_ID, roles_to_arrange=2)), 1)  # bot at position 1
        renumbered = {**TARGET, 'roles': [{**r, 'position': 5} if r['id'] == '101' else r for r in TARGET['roles']]}
        self.assertEqual(setup_flow.bot_role_notices(renumbered, BOT_ID, roles_to_arrange=2), [])


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


class DiscordSessionTests(TestCase):
    def test_sends_a_body_only_when_given(self):
        from dashboard.discord_api import DiscordSession
        session = DiscordSession.__new__(DiscordSession)
        session.client = mock.Mock(**{'http.request': mock.AsyncMock(return_value=[])})
        import asyncio
        session.loop = asyncio.new_event_loop()
        self.addCleanup(session.loop.close)
        session.request('GET', '/guilds/1/roles')
        session.request('POST', '/guilds/1/roles', {'name': 'x'})
        (_, get_kwargs), (_, post_kwargs) = [(c.args, c.kwargs) for c in session.client.http.request.call_args_list]
        self.assertEqual((get_kwargs, post_kwargs), ({}, {'json': {'name': 'x'}}))
