"""
A synthetic 'last year' server and a freshly created 'new' one, for the setup tests,
plus a fake Discord HTTP session that keeps state.
"""
import copy
import itertools

PNG = {'url': 'https://cdn.discordapp.com/emojis/50.png', 'content_type': 'image/png', 'data_b64': 'iVBORw0KGgo='}

SOURCE = {
    'guild': {'id': '1', 'name': 'Hunt 2026', 'features': ['COMMUNITY'], 'verification_level': 1,
              'explicit_content_filter': 2, 'rules_channel_id': '12', 'public_updates_channel_id': '14',
              'system_channel_id': '11', 'afk_timeout': 300},
    'roles': [{'id': '1', 'name': '@everyone', 'position': 0, 'permissions': '1024', 'color': 0},
              {'id': '3', 'name': 'Solver', 'position': 1, 'permissions': '0', 'color': 0, 'hoist': False},
              {'id': '2', 'name': 'Admin', 'position': 2, 'permissions': '8', 'color': 16711680, 'hoist': True},
              {'id': '4', 'name': 'OldBot', 'position': 3, 'permissions': '8', 'managed': True, 'tags': {'bot_id': '9'}}],
    'channels': [
        {'id': '10', 'type': 4, 'name': 'General Stuff', 'position': 0, 'permission_overwrites': []},
        {'id': '11', 'type': 0, 'name': 'general', 'position': 0, 'parent_id': '10', 'permission_overwrites': []},
        {'id': '12', 'type': 0, 'name': 'rules', 'position': 1, 'parent_id': '10', 'topic': 'Be nice',
         'permission_overwrites': [{'id': '1', 'type': 0, 'allow': '0', 'deny': '2048'}]},
        {'id': '13', 'type': 2, 'name': 'Hangout', 'position': 2, 'parent_id': '10', 'bitrate': 128000,
         'permission_overwrites': []},
        {'id': '14', 'type': 0, 'name': 'announcements', 'position': 3, 'parent_id': '10', 'permission_overwrites': [
            {'id': '2', 'type': 0, 'allow': '2048', 'deny': '0'}, {'id': '999', 'type': 1, 'allow': '2048', 'deny': '0'},
            {'id': '4', 'type': 0, 'allow': '2048', 'deny': '0'}]},
        {'id': '20', 'type': 4, 'name': 'Round A', 'position': 1, 'permission_overwrites': []},
        {'id': '21', 'type': 0, 'name': 'r1-anagrams', 'position': 0, 'parent_id': '20', 'permission_overwrites': []},
        {'id': '30', 'type': 4, 'name': 'Spare', 'position': 2,
         'permission_overwrites': [{'id': '1', 'type': 0, 'allow': '0', 'deny': '1024'}]},
    ],
    'onboarding': {'enabled': True, 'mode': 0, 'default_channel_ids': ['11', '12', '21'], 'prompts': [
        {'id': '80', 'type': 0, 'title': 'Where are you?', 'single_select': True, 'required': False, 'in_onboarding': True,
         'options': [{'id': '81', 'title': 'Solving', 'description': None, 'channel_ids': ['11'], 'role_ids': ['3', '4'],
                      'emoji': {'id': '50', 'name': 'herring', 'animated': False}}]}]},
    'welcome_screen': {'description': 'Welcome!', 'welcome_channels': [
        {'channel_id': '11', 'description': 'Chat', 'emoji_id': None, 'emoji_name': '👋'}]},
    'emojis': [{'id': '50', 'name': 'herring', 'roles': ['2', '4']}],
    'stickers': [{'id': '60', 'name': 'fish', 'description': 'A fish', 'tags': 'fish', 'format_type': 1}],
    'auto_moderation_rules': [{'id': '70', 'guild_id': '1', 'creator_id': '5', 'name': 'No spam', 'event_type': 1,
                               'trigger_type': 3, 'trigger_metadata': {}, 'enabled': True,
                               'actions': [{'type': 2, 'metadata': {'channel_id': '12'}}],
                               'exempt_roles': ['2'], 'exempt_channels': ['13']}],
    'expression_files': {'emoji:50': PNG, 'sticker:60': {**PNG, 'url': 'https://cdn.discordapp.com/stickers/60.png'}},
}

BOT_ID = 'B'
TARGET = {
    'guild': {'id': '100', 'name': 'New server', 'features': [], 'verification_level': 0, 'system_channel_id': '111'},
    'roles': [{'id': '100', 'name': '@everyone', 'position': 0, 'permissions': '1024', 'color': 0},
              {'id': '101', 'name': 'HerringBot', 'position': 1, 'permissions': '8', 'managed': True,
               'tags': {'bot_id': BOT_ID}}],
    'channels': [
        {'id': '110', 'type': 4, 'name': 'Text Channels', 'position': 0, 'permission_overwrites': []},
        {'id': '111', 'type': 0, 'name': 'general', 'position': 0, 'parent_id': '110', 'permission_overwrites': []},
        {'id': '112', 'type': 4, 'name': 'Voice Channels', 'position': 1, 'permission_overwrites': []},
        {'id': '113', 'type': 2, 'name': 'General', 'position': 0, 'parent_id': '112', 'bitrate': 64000,
         'permission_overwrites': []},
    ],
    'emojis': [], 'stickers': [], 'auto_moderation_rules': [],
}


class FakeDiscord:
    """Enough of DiscordSession for the executor: remembers created roles/channels, records every request."""

    def __init__(self, target=TARGET, messages=None, fail=()):
        self.state = copy.deepcopy(target)
        self.messages = messages or {}  # channel id -> messages
        self.fail = set(fail)  # paths whose writes fail
        self.requests, self.ids = [], (str(n) for n in itertools.count(500))
        self.bot_user_id = BOT_ID

    def request(self, method, path, body=None, params=None):
        self.requests.append((method, path, body))
        if method != 'GET' and path in self.fail:
            raise RuntimeError(f"Discord said no to {path}")
        return self.get(path) if method == 'GET' else self.write(method, path, body)

    def get(self, path):
        guild = self.state['guild']['id']
        if path == f"/guilds/{guild}/members/{BOT_ID}":
            return {'roles': ['101']}
        if path.endswith('/messages'):
            return self.messages.get(path.split('/')[2], [])[:1]
        return self.state[{'roles': 'roles', 'channels': 'channels', 'emojis': 'emojis', 'stickers': 'stickers',
                           'rules': 'auto_moderation_rules'}[path.rsplit('/', 1)[-1]]]

    def write(self, method, path, body):
        if method == 'POST':
            created = {'position': 1, **body, 'id': next(self.ids)}  # Discord puts new roles just above @everyone
            collection = {'roles': 'roles', 'channels': 'channels'}.get(path.rsplit('/', 1)[-1])
            if collection:
                self.state[collection].append(created)
            return created
        if method == 'DELETE':
            self.state['channels'] = [c for c in self.state['channels'] if c['id'] != path.rsplit('/', 1)[-1]]
            return None
        return self.update(path, body)

    def update(self, path, body):
        channel = next((c for c in self.state['channels'] if path == f"/channels/{c['id']}"), None)
        if channel is not None and isinstance(body, dict):
            channel.update(body)
        return body

    def create_sticker(self, guild_id, body, file):
        self.requests.append(('POST', f"/guilds/{guild_id}/stickers", body))
        return {**body, 'id': next(self.ids)}
