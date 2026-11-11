"""
Planning the setup of a new hunt's Discord server from a snapshot of an old
one: pure functions from (source snapshot, target snapshot) to a list of
operations, each the exact Discord API request to send.

Objects that exist only in the source are referred to with placeholders,
"@ref:<kind>:<source id>", resolved when applying from an ID map: target
objects matched at planning time are in the initial map, and each operation
that creates something adds the new ID. An operation depends on the operations
that create the refs it uses, plus any listed in `after`.
"""
import re
from dataclasses import dataclass, field

import discord

CATEGORY = discord.ChannelType.category.value
THREAD_TYPES = {10, 11, 12}
# The documented guild channel types (text, voice, category, announcement, stage, directory, forum, media).
# Discord has others: its create endpoint also accepts the undocumented 6 and 21, and in 2026-11 an
# experimental "server-hub" channel of a type it can't create showed up. Operations on channels of other
# types are offered, but unticked.
KNOWN_CHANNEL_TYPES = {0, 2, CATEGORY, 5, 13, 14, 15, 16}
# Last year's puzzle channels (r4-anagrams, r2m-final-meta) aren't copied.
PUZZLE_CHANNEL_RE = re.compile(r'^r\d+m?-')
REF_RE = re.compile(r'@ref:[a-z_]+:[0-9]+')
# An unboosted server's limits; higher source values are clamped.
MAX_BITRATE = {2: 96000, 13: 64000}


@dataclass(frozen=True)
class Operation:
    key: str
    stage: str
    description: str
    method: str
    path: str
    body: object = None
    creates: str = None  # the ref whose ID is the created object's 'id'
    preconditions: tuple = ()
    after: tuple = ()  # keys of operations that must be applied first, beyond those creating its refs
    file: dict = None  # for stickers: {'url', 'content_type', 'data_b64'}, sent as multipart
    selected: bool = True  # ticked by default on the plan page
    # An 'arrange' operation: its body is a list of {'id': ref, ...} entries, and entries whose ref doesn't
    # exist when it's applied (not created, or not chosen) are left out. Its refs don't make it depend on
    # the operations creating them; plan order puts it after them.
    partial: bool = False


@dataclass(frozen=True)
class SetupInput:
    source: dict  # snapshot sections
    target: dict
    server_name: str
    bot_id: str
    puzzle_category_ids: frozenset = field(default_factory=frozenset)


def ref(kind, source_id):
    return f"@ref:{kind}:{source_id}"


def refs_in(value):
    """Every ref placeholder inside a JSON-like value or string."""
    if isinstance(value, str):
        return set(REF_RE.findall(value))
    if isinstance(value, dict):
        return set().union(*map(refs_in, value.values())) if value else set()
    if isinstance(value, list):
        return set().union(*map(refs_in, value)) if value else set()
    return set()


def resolve(value, id_map):
    """value with every ref replaced by its ID; None if any ref isn't in id_map (yet)."""
    if any(r not in id_map for r in refs_in(value)):
        return None
    if isinstance(value, str):
        return REF_RE.sub(lambda m: id_map[m.group(0)], value)
    if isinstance(value, dict):
        return {k: resolve(v, id_map) for k, v in value.items()}
    if isinstance(value, list):
        return [resolve(v, id_map) for v in value]
    return value


def dependencies(operations, initial_id_map):
    """{operation key: sorted keys of the operations it depends on}."""
    creators = {op.creates: op.key for op in operations if op.creates}
    hard_refs = lambda op: set() if op.partial else refs_in([op.path, op.body]) - set(initial_id_map)
    return {op.key: sorted({creators[r] for r in hard_refs(op) if r in creators} | set(op.after))
            for op in operations}


def resolve_partial(entries, id_map):
    """An 'arrange' body with the entries whose ref isn't resolvable left out (see Operation.partial)."""
    return [resolved for resolved in (resolve(entry, id_map) for entry in entries) if resolved is not None]


# --- Reading snapshots -------------------------------------------------------

def everyone_role_id(sections):
    return sections['guild']['id']


def copyable_roles(sections):
    """Source roles to copy, lowest first: not @everyone, not managed by a bot or integration."""
    roles = [r for r in sections.get('roles', []) if r['id'] != everyone_role_id(sections) and not r.get('managed')]
    return sorted(roles, key=lambda r: r.get('position', 0))


def is_puzzle_channel(channel):
    return bool(PUZZLE_CHANNEL_RE.match(channel['name']))


def children_of(sections, category_id):
    return [c for c in sections.get('channels', []) if c.get('parent_id') == category_id]


def is_puzzle_category(sections, category, puzzle_category_ids):
    """A category of last year's puzzles: Herring made it for a round, or it has only puzzle channels."""
    children = children_of(sections, category['id'])
    return category['id'] in puzzle_category_ids or (bool(children) and all(map(is_puzzle_channel, children)))


def source_categories(setup):
    return [c for c in setup.source.get('channels', []) if c['type'] == CATEGORY
            and not is_puzzle_category(setup.source, c, setup.puzzle_category_ids)]


def source_channels(setup):
    copied_categories = {c['id'] for c in source_categories(setup)}
    return [c for c in setup.source.get('channels', [])
            if c['type'] not in THREAD_TYPES | {CATEGORY} and not is_puzzle_channel(c)
            and (c.get('parent_id') is None or c['parent_id'] in copied_categories)]


def excluded_categories(setup):
    """Source categories left out as last year's puzzle rounds, for the plan page."""
    return [c for c in setup.source.get('channels', []) if c['type'] == CATEGORY
            and is_puzzle_category(setup.source, c, setup.puzzle_category_ids)]


# --- Matching source objects to what the target already has ----------------

def initial_id_map(setup):
    """{ref: target ID} for every source object that already has a counterpart in the target."""
    roles = match_by_name(copyable_roles(setup.source), unmanaged(setup.target.get('roles', [])))
    categories = match_categories(setup)
    channels = match_channels(setup, categories)
    return ({ref('role', everyone_role_id(setup.source)): everyone_role_id(setup.target)}
            | {ref('role', s): t for s, t in roles.items()}
            | {ref('channel', s): t for s, t in (categories | channels).items()}
            | {ref('emoji', s): t for s, t in match_by_name(setup.source.get('emojis', []),
                                                             setup.target.get('emojis', [])).items()})


def unmanaged(roles):
    return [r for r in roles if not r.get('managed')]


def match_by_name(sources, targets, same=lambda s, t: s['name'] == t['name']):
    """{source id: target id}, each target used at most once, in source order."""
    matches, used = {}, set()
    for source in sources:
        target = next((t for t in targets if t['id'] not in used and same(source, t)), None)
        if target:
            matches[source['id']] = target['id']
            used.add(target['id'])
    return matches


def target_categories(setup):
    return [c for c in setup.target.get('channels', []) if c['type'] == CATEGORY]


def match_categories(setup):
    """By name first; then remaining categories whose channels overlap by name (Text Channels -> General Stuff)."""
    sources, targets = source_categories(setup), target_categories(setup)
    by_name = match_by_name(sources, targets)
    rest_s = [c for c in sources if c['id'] not in by_name]
    rest_t = [c for c in targets if c['id'] not in by_name.values()]
    return by_name | match_by_name(rest_s, rest_t, lambda s, t: shares_channel_names(setup, s, t))


def shares_channel_names(setup, source_category, target_category):
    names = lambda sections, category: {c['name'] for c in children_of(sections, category['id'])}
    return bool(names(setup.source, source_category) & names(setup.target, target_category))


def match_channels(setup, category_matches):
    """By name and type, preferring a target channel already in the matching category."""
    targets = [c for c in setup.target.get('channels', []) if c['type'] not in THREAD_TYPES | {CATEGORY}]
    in_place = lambda s, t: same_channel(s, t) and category_matches.get(s.get('parent_id')) == t.get('parent_id')
    first = match_by_name(source_channels(setup), targets, in_place)
    rest_s = [c for c in source_channels(setup) if c['id'] not in first]
    rest_t = [c for c in targets if c['id'] not in first.values()]
    return first | match_by_name(rest_s, rest_t, same_channel)


def same_channel(source, target):
    return source['name'] == target['name'] and source['type'] == target['type']


# --- Building the operations -------------------------------------------------

@dataclass(frozen=True)
class SetupPlanDraft:
    operations: list
    id_map: dict  # refs already resolved to existing target objects
    notes: list  # things left out or worth knowing, for the plan page


def build_plan(setup):
    id_map = initial_id_map(setup)
    builders = [name_operations, role_operations, emoji_operations, category_operations, channel_operations,
                position_operations, delete_operations, settings_operations, community_operations,
                sticker_operations, automod_operations]
    operations = []
    for builder in builders:
        operations += builder(setup, id_map, operations)
    return SetupPlanDraft(operations, id_map, plan_notes(setup))


def plan_notes(setup):
    excluded = [c['name'] for c in excluded_categories(setup)]
    member_overwrites = sum(1 for c in setup.source.get('channels', []) for o in c.get('permission_overwrites', [])
                            if o['type'] == 1)
    return ([f"Not copied, as last year's puzzle rounds: {len(excluded)} categories ({', '.join(excluded)})"]
            if excluded else []) + ([f"Not copied: {member_overwrites} per-member permission overwrites"]
                                    if member_overwrites else [])


def guild_path(setup, suffix=''):
    return f"/guilds/{everyone_role_id(setup.target)}{suffix}"


def target_object(sections, collection, target_id):
    return next((o for o in sections.get(collection, []) if o['id'] == target_id), {})


def changed_fields(desired, current, id_map):
    """The fields of `desired` whose (resolved) value differs from `current`'s (a missing field counts as empty)."""
    return {k: v for k, v in desired.items()
            if comparable(resolve(v, id_map)) != comparable(current.get(k)) and (k in current or v not in (0, False, None, '', []))}


def comparable(value):
    if isinstance(value, list):
        return sorted(map(repr, map(comparable, value)))
    if isinstance(value, dict):
        return {k: comparable(v) for k, v in value.items()}
    return str(value) if isinstance(value, int) and not isinstance(value, bool) else value


def name_operations(setup, id_map, earlier):
    if setup.target['guild'].get('name') == setup.server_name:
        return []
    return [Operation('server.name', 'Server', f"Rename the server to {setup.server_name!r}", 'PATCH',
                      guild_path(setup), {'name': setup.server_name})]


ROLE_FIELDS = ('name', 'permissions', 'hoist', 'mentionable')


def role_body(role):
    color = {'colors': role['colors']} if role.get('colors') else {'color': role.get('color', 0)}
    return {k: role[k] for k in ROLE_FIELDS if k in role} | color


def role_operations(setup, id_map, earlier):
    everyone = everyone_operations(setup, id_map)
    per_role = [op for role in copyable_roles(setup.source) for op in role_copy_operations(setup, id_map, role)]
    return everyone + per_role + [role_order_operation(setup)]


def everyone_operations(setup, id_map):
    target_id = everyone_role_id(setup.target)
    source = target_object(setup.source, 'roles', everyone_role_id(setup.source))
    changes = changed_fields({'permissions': source.get('permissions')}, target_object(setup.target, 'roles', target_id), id_map)
    return [Operation('role.everyone', 'Roles', "Set @everyone's permissions", 'PATCH',
                      guild_path(setup, f"/roles/{target_id}"), changes)] if changes else []


def role_copy_operations(setup, id_map, role):
    role_ref = ref('role', role['id'])
    if role_ref not in id_map:
        return [Operation(f"role.create.{role['id']}", 'Roles', f"Create role {role['name']!r}", 'POST',
                          guild_path(setup, '/roles'), role_body(role), creates=role_ref,
                          preconditions=({'absent': 'roles', 'name': role['name']},))]
    changes = changed_fields(role_body(role), target_object(setup.target, 'roles', id_map[role_ref]), id_map)
    return [Operation(f"role.update.{role['id']}", 'Roles', f"Update role {role['name']!r}: {', '.join(changes)}",
                      'PATCH', guild_path(setup, f"/roles/{id_map[role_ref]}"), changes,
                      preconditions=({'exists': 'roles', 'id': id_map[role_ref]},))] if changes else []


def role_order_operation(setup):
    """Put the copied roles in last year's order, just above @everyone (and below the bot's role)."""
    roles = copyable_roles(setup.source)
    return Operation('role.order', 'Roles', f"Arrange the roles in last year's order", 'PATCH',
                     guild_path(setup, '/roles'),
                     [{'id': ref('role', role['id']), 'position': i + 1} for i, role in enumerate(roles)],
                     preconditions=({'bot_role_on_top': len(roles)},), partial=True)


def copied_role_ids(setup):
    return {r['id'] for r in copyable_roles(setup.source)} | {everyone_role_id(setup.source)}


def role_refs(setup, role_ids):
    """Refs for those of `role_ids` that are copied (or @everyone); others can't exist in the target."""
    return [ref('role', r) for r in role_ids if r in copied_role_ids(setup)]


def channel_refs(setup, channel_ids):
    copied = {c['id'] for c in source_categories(setup) + source_channels(setup)}
    return [ref('channel', c) for c in channel_ids if c in copied]


def channel_ref(setup, channel_id):
    return next(iter(channel_refs(setup, [channel_id] if channel_id else [])), None)


def emoji_ref(setup, emoji_id):
    """Ref for a custom emoji copied from the source; None for unicode emoji or ones that aren't copied."""
    copied = {e['id'] for e in setup.source.get('emojis', [])}
    return ref('emoji', emoji_id) if emoji_id in copied else None


def data_uri(file):
    return f"data:{file['content_type']};base64,{file['data_b64']}"


def emoji_operations(setup, id_map, earlier):
    files = setup.source.get('expression_files', {})
    return [Operation(f"emoji.create.{e['id']}", 'Emojis', f"Create emoji :{e['name']}:", 'POST',
                      guild_path(setup, '/emojis'),
                      {'name': e['name'], 'image': data_uri(files[f"emoji:{e['id']}"]),
                       'roles': role_refs(setup, e.get('roles', []))},
                      creates=ref('emoji', e['id']), preconditions=({'absent': 'emojis', 'name': e['name']},))
            for e in setup.source.get('emojis', [])
            if ref('emoji', e['id']) not in id_map and f"emoji:{e['id']}" in files]


TEXT_FIELDS = ('topic', 'nsfw', 'rate_limit_per_user', 'default_auto_archive_duration', 'default_thread_rate_limit_per_user')
VOICE_FIELDS = ('nsfw', 'rate_limit_per_user', 'bitrate', 'user_limit', 'rtc_region', 'video_quality_mode')
# Which settable fields apply to which channel types (per Discord's Create Guild Channel docs). Others,
# like the bitrate templates include for every channel, are left out.
CHANNEL_FIELDS = {CATEGORY: (), 0: TEXT_FIELDS, 5: TEXT_FIELDS, 2: VOICE_FIELDS, 13: VOICE_FIELDS,
                  15: TEXT_FIELDS + ('default_sort_order', 'default_forum_layout'), 16: TEXT_FIELDS + ('default_sort_order',)}


def channel_body(setup, channel):
    """Everything about a source channel that can be set on a new one, with refs for roles and its category."""
    fields = ('name', 'type') + CHANNEL_FIELDS.get(channel['type'], ())
    body = {k: channel[k] for k in fields if channel.get(k) is not None}
    if 'bitrate' in body:
        body['bitrate'] = min(body['bitrate'], MAX_BITRATE.get(channel['type'], body['bitrate']))
    if channel['type'] != CATEGORY:
        body['parent_id'] = channel_ref(setup, channel.get('parent_id'))
    return body | {'permission_overwrites': overwrites_body(setup, channel)} | forum_fields(setup, channel)


def overwrites_body(setup, channel):
    """The channel's role overwrites, for copied roles (per-member overwrites are dropped)."""
    copied = copied_role_ids(setup)
    return [{'id': ref('role', o['id']), 'type': 0, 'allow': str(o['allow']), 'deny': str(o['deny'])}
            for o in channel.get('permission_overwrites', []) if o['type'] == 0 and o['id'] in copied]


def forum_fields(setup, channel):
    tags = [{'name': t['name'], 'moderated': t.get('moderated', False), 'emoji_name': t.get('emoji_name'),
             'emoji_id': emoji_ref(setup, t.get('emoji_id'))} for t in channel.get('available_tags', [])]
    return {'available_tags': tags} if tags else {}


def category_operations(setup, id_map, earlier):
    return [op for category in source_categories(setup) for op in channel_copy_operations(setup, id_map, category)]


def channel_operations(setup, id_map, earlier):
    return [op for channel in source_channels(setup) for op in channel_copy_operations(setup, id_map, channel)]


def channel_copy_operations(setup, id_map, channel):
    channel_ref_ = ref('channel', channel['id'])
    if channel_ref_ not in id_map:
        return [channel_create_operation(setup, channel)]
    target = target_object(setup.target, 'channels', id_map[channel_ref_])
    changes = changed_fields({k: v for k, v in channel_body(setup, channel).items() if k != 'type'}, target, id_map)
    return [channel_update_operation(setup, channel, target, changes)] if changes else []


def channel_kind(channel):
    return 'category' if channel['type'] == CATEGORY else 'channel'


def channel_label(channel):
    if channel['type'] in (2, 13):
        return f"voice channel {channel['name']!r}"
    return f"category {channel['name']!r}" if channel['type'] == CATEGORY else f"#{channel['name']}"


def type_doubts(channel):
    """Why an operation on this channel shouldn't be ticked by default, judging by its type."""
    return [] if channel['type'] in KNOWN_CHANNEL_TYPES else [
        f"its type, {channel['type']}, isn't one Herring knows (maybe a new Discord feature), so Discord may refuse it"]


def with_doubts(description, doubts):
    return description + (f" — left unticked: {'; '.join(doubts)}" if doubts else "")


def channel_create_operation(setup, channel):
    kind = channel_kind(channel)
    empty = kind == 'category' and not children_of(setup.source, channel['id'])
    doubts = (["empty last year; maybe an old round"] if empty else []) + type_doubts(channel)
    return Operation(f"{kind}.create.{channel['id']}", stage_for(kind),
                     with_doubts(f"Create {channel_label(channel)}", doubts),
                     'POST', guild_path(setup, '/channels'), channel_body(setup, channel),
                     creates=ref('channel', channel['id']), selected=not doubts,
                     preconditions=({'absent': 'channels', 'name': channel['name'], 'type': channel['type']},))


def channel_update_operation(setup, channel, target, changes):
    kind = channel_kind(channel)
    doubts = type_doubts(target)
    return Operation(f"{kind}.update.{channel['id']}", stage_for(kind),
                     with_doubts(f"Update {channel_label(target)}: "
                                 f"{', '.join(describe_change(k, v) for k, v in changes.items())}", doubts),
                     'PATCH', f"/channels/{target['id']}", changes, selected=not doubts,
                     preconditions=({'exists': 'channels', 'id': target['id']},))


def stage_for(kind):
    return 'Categories' if kind == 'category' else 'Channels'


def describe_change(field_name, value):
    if field_name == 'name':
        return f"rename to {value!r}"
    if field_name == 'parent_id':
        return "move to the matching category"
    return field_name.replace('_', ' ')


def position_operations(setup, id_map, earlier):
    """Last year's order, for whichever categories and channels exist by then (it comes after the creates and moves)."""
    copied = source_categories(setup) + source_channels(setup)
    return [Operation('channel.order', 'Channels', "Arrange the categories and channels in last year's order",
                      'PATCH', guild_path(setup, '/channels'),
                      [{'id': ref('channel', c['id']), 'position': c.get('position', 0)} for c in copied], partial=True)]


def delete_operations(setup, id_map, earlier):
    """Target channels and categories with no counterpart: deleted only if unused (checked again when applied)."""
    matched = set(id_map.values())
    leftovers = [c for c in setup.target.get('channels', []) if c['id'] not in matched and c['type'] not in THREAD_TYPES
                 and not is_target_puzzle_channel(setup, c)]
    channels = [delete_channel_operation(c) for c in leftovers if c['type'] != CATEGORY]
    # Category deletes come after the channel moves and deletes in plan order, and check then that they're empty.
    return channels + [delete_category_operation(c) for c in leftovers if c['type'] == CATEGORY]


def is_target_puzzle_channel(setup, channel):
    """The new server's own puzzle channels and round categories (puzzles added before setup) are never deleted."""
    if channel['type'] == CATEGORY:
        return is_puzzle_category(setup.target, channel, setup.puzzle_category_ids)
    return is_puzzle_channel(channel)


def delete_channel_operation(channel):
    doubts = type_doubts(channel)
    return Operation(f"channel.delete.{channel['id']}", 'Cleanup',
                     with_doubts(f"Delete {channel_label(channel)} (not in last year's server; only if it has no messages)",
                                 doubts),
                     'DELETE', f"/channels/{channel['id']}", selected=not doubts,
                     preconditions=({'exists': 'channels', 'id': channel['id']}, {'no_messages': channel['id']}))


def delete_category_operation(category):
    return Operation(f"category.delete.{category['id']}", 'Cleanup',
                     f"Delete {channel_label(category)} (not in last year's server; only if it's empty by then)",
                     'DELETE', f"/channels/{category['id']}",
                     preconditions=({'exists': 'channels', 'id': category['id']}, {'empty_category': category['id']}))


GUILD_SETTINGS = ('verification_level', 'default_message_notifications', 'explicit_content_filter', 'afk_timeout',
                  'system_channel_flags', 'preferred_locale', 'premium_progress_bar_enabled')
GUILD_CHANNEL_SETTINGS = ('afk_channel_id', 'system_channel_id')


def settings_operations(setup, id_map, earlier):
    source = setup.source['guild']
    desired = ({k: source[k] for k in GUILD_SETTINGS if k in source}
               | {k: channel_ref(setup, source.get(k)) for k in GUILD_CHANNEL_SETTINGS if k in source})
    changes = changed_fields(desired, setup.target['guild'], id_map)
    return [Operation('server.settings', 'Server', f"Server settings: {', '.join(k.replace('_', ' ') for k in changes)}",
                      'PATCH', guild_path(setup), changes)] if changes else []


def community_operations(setup, id_map, earlier):
    """Community (if last year's server had it), then the features that need it: welcome screen, onboarding."""
    if 'COMMUNITY' not in setup.source['guild'].get('features', []):
        return []
    enable = [] if 'COMMUNITY' in setup.target['guild'].get('features', []) else [community_operation(setup)]
    after = tuple(op.key for op in enable)
    return enable + welcome_screen_operations(setup, after) + onboarding_operations(setup, after)


def community_operation(setup):
    source, target = setup.source['guild'], setup.target['guild']
    body = {'features': sorted(set(target.get('features', [])) | {'COMMUNITY'}),
            'verification_level': max(source.get('verification_level', 1), 1),
            'explicit_content_filter': 2,
            **{k: channel_ref(setup, source.get(k)) for k in ('rules_channel_id', 'public_updates_channel_id',
                                                              'safety_alerts_channel_id')}}
    return Operation('server.community', 'Community', "Turn on Community (with last year's rules and updates channels)",
                     'PATCH', guild_path(setup), body)


def welcome_screen_operations(setup, after):
    screen = setup.source.get('welcome_screen')
    if not screen:
        return []
    channels = [{'channel_id': channel_ref(setup, c['channel_id']), 'description': c.get('description', ''),
                 'emoji_id': emoji_ref(setup, c.get('emoji_id')), 'emoji_name': c.get('emoji_name')}
                for c in screen.get('welcome_channels', []) if channel_ref(setup, c['channel_id'])]
    return [Operation('server.welcome', 'Community', "Set up the welcome screen", 'PATCH',
                      guild_path(setup, '/welcome-screen'),
                      {'enabled': True, 'description': screen.get('description'), 'welcome_channels': channels},
                      after=after)]


def onboarding_operations(setup, after):
    onboarding = setup.source.get('onboarding')
    if not onboarding or not (onboarding.get('enabled') or onboarding.get('prompts')):
        return []
    body = {'prompts': [prompt_body(setup, p) for p in onboarding.get('prompts', [])],
            'default_channel_ids': channel_refs(setup, onboarding.get('default_channel_ids', [])),
            'enabled': onboarding.get('enabled', False), 'mode': onboarding.get('mode', 0)}
    return [Operation('server.onboarding', 'Community',
                      f"Set up onboarding ({len(body['prompts'])} questions, {len(body['default_channel_ids'])} default channels)",
                      'PUT', guild_path(setup, '/onboarding'), body, after=after)]


def prompt_body(setup, prompt):
    keys = ('id', 'type', 'title', 'single_select', 'required', 'in_onboarding')
    return {k: prompt[k] for k in keys if k in prompt} | {'options': [option_body(setup, o) for o in prompt['options']]}


def option_body(setup, option):
    emoji = option.get('emoji') or {}
    return {'id': option['id'], 'title': option['title'], 'description': option.get('description'),
            'channel_ids': channel_refs(setup, option.get('channel_ids', [])),
            'role_ids': role_refs(setup, option.get('role_ids', [])),
            'emoji_id': emoji_ref(setup, emoji.get('id')), 'emoji_name': emoji.get('name'),
            'emoji_animated': emoji.get('animated', False)}


def sticker_operations(setup, id_map, earlier):
    files = setup.source.get('expression_files', {})
    existing = {s['name'] for s in setup.target.get('stickers', [])}
    return [Operation(f"sticker.create.{s['id']}", 'Emojis', f"Create sticker {s['name']!r}", 'POST',
                      guild_path(setup, '/stickers'),
                      {'name': s['name'], 'description': s.get('description') or '', 'tags': s.get('tags', '')},
                      file=files[f"sticker:{s['id']}"], preconditions=({'absent': 'stickers', 'name': s['name']},))
            for s in setup.source.get('stickers', []) if s['name'] not in existing and f"sticker:{s['id']}" in files]


AUTOMOD_FIELDS = ('name', 'event_type', 'trigger_type', 'trigger_metadata', 'enabled')


def automod_operations(setup, id_map, earlier):
    existing = {r['name'] for r in setup.target.get('auto_moderation_rules', [])}
    return [Operation(f"automod.create.{r['id']}", 'Moderation', f"Create AutoMod rule {r['name']!r}", 'POST',
                      guild_path(setup, '/auto-moderation/rules'), automod_body(setup, r),
                      preconditions=({'absent': 'auto_moderation_rules', 'name': r['name']},))
            for r in setup.source.get('auto_moderation_rules', []) if r['name'] not in existing]


def automod_body(setup, rule):
    actions = [{**a, 'metadata': {**a['metadata'], 'channel_id': channel_ref(setup, a['metadata']['channel_id'])}}
               if a.get('metadata', {}).get('channel_id') else a for a in rule.get('actions', [])]
    return ({k: rule[k] for k in AUTOMOD_FIELDS if k in rule} | {'actions': actions}
            | {'exempt_roles': role_refs(setup, rule.get('exempt_roles', [])),
               'exempt_channels': channel_refs(setup, rule.get('exempt_channels', []))})
