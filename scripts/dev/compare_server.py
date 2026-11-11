#!/usr/bin/env python
"""
Compares a saved server snapshot (e.g. last year's server) with a live Discord server (e.g. the one just set up
from it), by names: non-puzzle channels (category, topic, role overwrites) and their order, Community settings,
onboarding, welcome screen, AutoMod, emojis, stickers, roles. Read-only. Run in the dev container:
    docker compose -p herring-claude exec -T project python scripts/dev/compare_server.py SNAPSHOT_ID GUILD_ID
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'herring'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'herring.settings')
import django; django.setup()
from dashboard import discord_api, server_structure, setup_plan
from dashboard.models import DiscordServerSnapshot

src = DiscordServerSnapshot.objects.get(id=sys.argv[1]).sections
tgt, errors = discord_api.run(discord_api.fetch_server_structure(int(sys.argv[2])))
print('target read errors:', errors or 'none')


def names(sections):
    roles = {r['id']: r['name'] for r in sections['roles']} | {sections['guild']['id']: '@everyone'}
    chans = {c['id']: c['name'] for c in sections['channels']}
    emojis = {e['id']: e['name'] for e in sections.get('emojis', [])}
    return roles, chans, emojis


def layout(sections, skip_puzzles=True):
    roles, chans, _ = names(sections)
    out = {}
    for c in sections['channels']:
        if c['type'] in (10, 11, 12) or (skip_puzzles and (setup_plan.is_puzzle_channel(c) or (c['type'] == 4 and setup_plan.is_puzzle_category(sections, c, frozenset())))):
            continue
        ows = sorted((roles.get(o['id'], '?' + o['id']), o['allow'], o['deny']) for o in c.get('permission_overwrites', []) if o['type'] == 0 and o['id'] in roles)
        out[(c['type'], c['name'])] = (chans.get(c.get('parent_id')), c.get('topic') or None, ows)
    return out


def community(sections):
    roles, chans, emojis = names(sections)
    g, ob, ws = sections['guild'], sections.get('onboarding', {}), sections.get('welcome_screen', {})
    return {'community': 'COMMUNITY' in g['features'], 'rules': chans.get(g.get('rules_channel_id')),
            'updates': chans.get(g.get('public_updates_channel_id')), 'system': chans.get(g.get('system_channel_id')),
            'onboarding': (ob.get('enabled'), sorted(chans.get(i, i) for i in ob.get('default_channel_ids', [])),
                           [(p['title'], [(o['title'], sorted(chans.get(i, i) for i in o['channel_ids']), sorted(roles.get(i, i) for i in o['role_ids']),
                                           o.get('emoji', {}).get('name')) for o in p['options']]) for p in ob.get('prompts', [])]),
            'welcome': (ws.get('description'), [(chans.get(c['channel_id']), c['description'], c.get('emoji_name')) for c in ws.get('welcome_channels', [])]),
            'automod': sorted((r['name'], r['trigger_type'], tuple(sorted(roles.get(i, i) for i in r['exempt_roles'])),
                               tuple(chans.get(a.get('metadata', {}).get('channel_id')) for a in r['actions'])) for r in sections.get('auto_moderation_rules', [])),
            'emojis': sorted(e['name'] for e in sections.get('emojis', [])), 'stickers': sorted(s['name'] for s in sections.get('stickers', []))}


a, b = layout(src), layout(tgt)
print('channels: source', len(a), 'target', len(b))
for key in sorted(set(a) | set(b), key=str):
    if a.get(key) != b.get(key):
        print('  DIFF', key, '\n    source:', a.get(key), '\n    target:', b.get(key))
ca, cb = community(src), community(tgt)
for key in ca:
    print(('  same ' if ca[key] == cb[key] else '  DIFF ') + key, '' if ca[key] == cb[key] else f"\n    source: {ca[key]}\n    target: {cb[key]}")
print('target name:', tgt['guild']['name'])
print('roles: source', sorted(r['name'] for r in src['roles'] if not r.get('managed')) == sorted(r['name'] for r in tgt['roles'] if not r.get('managed')))

# Display order of categories and channels
skip = lambda c, s: setup_plan.is_puzzle_channel(c) or (c['type'] == 4 and setup_plan.is_puzzle_category(s, c, frozenset()))
order = lambda s: [((cat or {}).get('name'), [c['name'] for c in chans if not skip(c, s)])
                   for cat, chans in server_structure.channel_tree(s) if not (cat and skip(cat, s))]
a, b = order(src), order(tgt)
print('channel order: same' if a == b else 'channel order: DIFFERENT')
for x, y in zip(a, b):
    print(('  ' if x == y else '* ') + str(x[0]), '|', x[1][:4], '...' if x != y else '', '' if x == y else f'\n    target: {y}')
