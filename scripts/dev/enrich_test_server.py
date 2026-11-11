#!/usr/bin/env python
"""
Gives a test server (one set up with last year's layout, whose channel and role names this uses) Community, a welcome
screen, onboarding, an emoji, a sticker and an AutoMod rule, so it can serve as a full 'last year' source for testing
server setup. Changes that server! Run in the dev container:
    docker compose -p herring-claude exec -T project python scripts/dev/enrich_test_server.py GUILD_ID
"""
import base64, os, struct, sys, zlib
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'herring'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'herring.settings')
import django; django.setup()
from dashboard.discord_api import DiscordSession

G = sys.argv[1]


def png(size, rgb):
    row = b'\x00' + bytes(rgb) * size
    chunk = lambda kind, data: struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data))
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', size, size, 8, 2, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress(row * size)) + chunk(b'IEND', b''))


def step(name, call):
    try:
        result = call()
        print(f"OK   {name}: {str(result)[:200]}")
        return result
    except Exception as e:
        print(f"FAIL {name}: {type(e).__name__}: {e}"[:600])


with DiscordSession() as d:
    channels = {c['name']: c for c in d.request('GET', f'/guilds/{G}/channels')}
    roles = {r['name']: r for r in d.request('GET', f'/guilds/{G}/roles')}
    guild = d.request('GET', f'/guilds/{G}')
    print('features before:', guild['features'])
    step('community', lambda: d.request('PATCH', f'/guilds/{G}', {
        'features': sorted(set(guild['features']) | {'COMMUNITY'}), 'verification_level': 1, 'explicit_content_filter': 2,
        'rules_channel_id': channels['rules']['id'], 'public_updates_channel_id': channels['server-management']['id']})['features'])
    step('welcome screen', lambda: d.request('PATCH', f'/guilds/{G}/welcome-screen', {
        'enabled': True, 'description': 'Welcome to the hunt!',
        'welcome_channels': [{'channel_id': channels['general']['id'], 'description': 'Chat', 'emoji_name': '👋'},
                             {'channel_id': channels['intros']['id'], 'description': 'Say hi', 'emoji_name': None}]}))
    emoji = step('emoji', lambda: d.request('POST', f'/guilds/{G}/emojis', {
        'name': 'herring', 'image': 'data:image/png;base64,' + base64.b64encode(png(64, (200, 30, 30))).decode(), 'roles': []}))
    step('sticker', lambda: d.create_sticker(G, {'name': 'redherring', 'description': 'A red herring', 'tags': 'fish'},
                                             {'url': 'x.png', 'content_type': 'image/png', 'data_b64': base64.b64encode(png(320, (220, 40, 40))).decode()}))
    step('automod', lambda: d.request('POST', f'/guilds/{G}/auto-moderation/rules', {
        'name': 'No red herrings', 'event_type': 1, 'trigger_type': 1, 'trigger_metadata': {'keyword_filter': ['redherring']},
        'actions': [{'type': 1}, {'type': 2, 'metadata': {'channel_id': channels['herringbot-debug']['id']}}],
        'enabled': True, 'exempt_roles': [roles['Discord Mod']['id']], 'exempt_channels': []}))
    defaults = [channels[n]['id'] for n in ('general', 'random', 'food', 'quotes', 'photos', 'intros', 'theme', 'rules')]
    prompt = {'type': 0, 'title': 'How are you solving?', 'single_select': True, 'required': False, 'in_onboarding': True,
              'options': [{'title': 'On campus', 'description': 'In Cambridge', 'channel_ids': [channels['onsite-logistics']['id']],
                           'role_ids': [roles['On-site solver']['id']], 'emoji_id': emoji and emoji['id'], 'emoji_name': emoji and emoji['name'], 'emoji_animated': False},
                          {'title': 'Remote', 'description': None, 'channel_ids': [channels['remote-solvers']['id']],
                           'role_ids': [roles['Remote solver']['id']], 'emoji_name': '🏠'}]}
    body = {'prompts': [prompt], 'default_channel_ids': defaults, 'enabled': True, 'mode': 0}
    if not step('onboarding without ids', lambda: d.request('PUT', f'/guilds/{G}/onboarding', body)):
        fake = lambda n: str(((1700000000000 - 1420070400000) << 22) + n)
        with_ids = {**body, 'prompts': [{**prompt, 'id': fake(1), 'options': [{**o, 'id': fake(2 + i)} for i, o in enumerate(prompt['options'])]}]}
        step('onboarding with made-up ids', lambda: d.request('PUT', f'/guilds/{G}/onboarding', with_ids))
