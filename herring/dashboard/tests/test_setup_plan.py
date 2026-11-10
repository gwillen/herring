from django.test import SimpleTestCase

from dashboard import setup_plan
from dashboard.setup_plan import ref
from .setup_fixtures import BOT_ID, SOURCE, TARGET


def plan(source=SOURCE, target=TARGET, puzzle_categories=frozenset()):
    return setup_plan.build_plan(setup_plan.SetupInput(source, target, 'You Are Being Rage Limited', BOT_ID,
                                                       puzzle_categories))


def operation(draft, key):
    return next(op for op in draft.operations if op.key == key)


class MatchingTests(SimpleTestCase):
    def test_matches_existing_objects(self):
        id_map = plan().id_map
        self.assertEqual(id_map[ref('role', '1')], '100')  # @everyone
        self.assertEqual(id_map[ref('channel', '10')], '110')  # Text Channels holds #general, like General Stuff
        self.assertEqual(id_map[ref('channel', '11')], '111')  # #general itself
        self.assertNotIn(ref('role', '4'), id_map)  # last year's bot role isn't copied

    def test_renames_matched_category(self):
        self.assertEqual(operation(plan(), 'category.update.10').body, {'name': 'General Stuff'})


class OperationTests(SimpleTestCase):
    def test_keys_are_unique(self):
        keys = [op.key for op in plan().operations]
        self.assertEqual(len(keys), len(set(keys)))

    def test_puzzle_rounds_are_left_out(self):
        draft = plan()
        self.assertFalse(any('Round A' in op.description or 'r1-anagrams' in op.description for op in draft.operations))
        self.assertIn('Round A', ' '.join(draft.notes))

    def test_herring_round_categories_are_left_out_by_id(self):
        draft = plan(puzzle_categories=frozenset({'30'}))
        self.assertFalse(any(op.key == 'category.create.30' for op in draft.operations))

    def test_empty_category_is_created_unticked(self):
        self.assertFalse(operation(plan(), 'category.create.30').selected)

    def test_roles_created_in_order_without_bot_role(self):
        draft = plan()
        self.assertEqual([op.key for op in draft.operations if op.key.startswith('role.create')],
                         ['role.create.3', 'role.create.2'])
        self.assertEqual(operation(draft, 'role.order').body,
                         [{'id': ref('role', '3'), 'position': 1}, {'id': ref('role', '2'), 'position': 2}])

    def test_overwrites_keep_only_copied_roles(self):
        body = operation(plan(), 'channel.create.14').body
        self.assertEqual(body['permission_overwrites'],
                         [{'id': ref('role', '2'), 'type': 0, 'allow': '2048', 'deny': '0'}])
        self.assertEqual(body['parent_id'], ref('channel', '10'))

    def test_voice_bitrate_is_clamped(self):
        self.assertEqual(operation(plan(), 'channel.create.13').body['bitrate'], 96000)

    def test_leftovers_are_deleted_only_if_unused(self):
        draft = plan()
        voice = operation(draft, 'channel.delete.113')
        self.assertIn({'no_messages': '113'}, voice.preconditions)
        category = operation(draft, 'category.delete.112')
        self.assertIn({'empty_category': '112'}, category.preconditions)
        self.assertIn('channel.delete.113', category.after)

    def test_community_onboarding_and_welcome_screen(self):
        draft = plan()
        community = operation(draft, 'server.community').body
        self.assertEqual(community['rules_channel_id'], ref('channel', '12'))
        onboarding = operation(draft, 'server.onboarding')
        self.assertEqual(onboarding.body['default_channel_ids'], [ref('channel', '11'), ref('channel', '12')])
        option = onboarding.body['prompts'][0]['options'][0]
        self.assertEqual((option['role_ids'], option['emoji_id']), ([ref('role', '3')], ref('emoji', '50')))
        self.assertEqual(onboarding.after, ('server.community',))
        self.assertEqual(operation(draft, 'server.welcome').body['welcome_channels'][0]['channel_id'],
                         ref('channel', '11'))

    def test_expressions_and_automod(self):
        draft = plan()
        self.assertEqual(operation(draft, 'emoji.create.50').body['roles'], [ref('role', '2')])
        self.assertTrue(operation(draft, 'emoji.create.50').body['image'].startswith('data:image/png;base64,'))
        self.assertIsNotNone(operation(draft, 'sticker.create.60').file)
        rule = operation(draft, 'automod.create.70').body
        self.assertEqual((rule['exempt_roles'], rule['actions'][0]['metadata']['channel_id']),
                         ([ref('role', '2')], ref('channel', '12')))
        self.assertNotIn('creator_id', rule)

    def test_server_rename(self):
        self.assertEqual(operation(plan(), 'server.name').body, {'name': 'You Are Being Rage Limited'})


class DependencyTests(SimpleTestCase):
    def test_dependencies_follow_refs(self):
        draft = plan()
        deps = setup_plan.dependencies(draft.operations, draft.id_map)
        self.assertEqual(deps['channel.create.14'], ['role.create.2'])  # its category already exists
        self.assertIn('emoji.create.50', deps['server.onboarding'])
        self.assertIn('server.community', deps['server.onboarding'])

    def test_resolve(self):
        id_map = {ref('role', '2'): '502'}
        self.assertEqual(setup_plan.resolve({'ids': [ref('role', '2')]}, id_map), {'ids': ['502']})
        self.assertIsNone(setup_plan.resolve({'ids': [ref('role', '3')]}, id_map))
