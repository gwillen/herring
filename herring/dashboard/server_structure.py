"""
Readable views of a server snapshot's raw Discord JSON (see models.DiscordServerSnapshot).
"""
import discord


def role_rows(sections):
    """Roles from highest to lowest (Discord's order), with decoded permissions."""
    roles = sorted(sections.get('roles', []), key=lambda role: -role['position'])
    return [{**role, 'color_hex': f"#{role['color']:06x}", 'permission_names': permission_names(role['permissions']),
             'is_everyone': role['id'] == sections.get('guild', {}).get('id')} for role in roles]


def permission_names(permissions):
    allowed = discord.Permissions(int(permissions))
    return ['administrator'] if allowed.administrator else [name for name, value in allowed if value]


def channel_tree(sections):
    """[(category or None, [channels])] in Discord's display order; channels have 'type_name' and decoded overwrites."""
    channels = [with_type_name(channel) for channel in sections.get('channels', [])]
    categories = by_position(c for c in channels if c['type'] == discord.ChannelType.category.value)
    children = lambda parent_id: by_position(c for c in channels if c.get('parent_id') == parent_id
                                             and c['type'] != discord.ChannelType.category.value)
    return [(None, children(None))] + [(category, children(category['id'])) for category in categories]


def with_type_name(channel):
    try:
        type_name = discord.ChannelType(channel['type']).name
    except ValueError:
        type_name = f"type {channel['type']}"
    return {**channel, 'type_name': type_name}


def by_position(channels):
    return sorted(channels, key=lambda channel: (channel.get('position', 0), int(channel['id'])))


def onboarding_summary(sections):
    onboarding = sections.get('onboarding')
    if onboarding is None:
        return None
    names = channel_names(sections)
    return {**onboarding, 'default_channel_names': [names.get(i, i) for i in onboarding.get('default_channel_ids', [])]}


def channel_names(sections):
    return {channel['id']: channel['name'] for channel in sections.get('channels', [])}


def section_counts(sections):
    """{section: number of items} for the list-valued sections, for an overview."""
    return {name.replace('_', ' '): len(data) for name, data in sections.items() if isinstance(data, list)}


def sections_from_template(template):
    """
    Snapshot-style sections from a Discord server template. Templates use small
    integer placeholder IDs (@everyone is role 0, which then also serves as the
    guild ID), give roles in order instead of positions, and have no bot roles,
    member overwrites, Community features, onboarding, emojis or stickers.
    """
    source = template['serialized_source_guild']
    guild = ({k: v for k, v in source.items() if k not in ('roles', 'channels')}
             | {'id': '0', 'features': []} | id_strings(source, ('system_channel_id', 'afk_channel_id')))
    roles = [{**role, 'id': str(role['id']), 'permissions': str(role['permissions']), 'position': i, 'managed': False}
             for i, role in enumerate(source['roles'])]
    channels = [{**channel, **id_strings(channel, ('id', 'parent_id')),
                 'permission_overwrites': [{**o, 'id': str(o['id'])} for o in channel.get('permission_overwrites', [])]}
                for channel in source['channels']]
    return {'guild': guild, 'roles': roles, 'channels': channels,
            'template': {k: v for k, v in template.items() if k != 'serialized_source_guild'}}


def id_strings(obj, keys):
    """The given ID fields as strings (None stays None), like real snapshot IDs."""
    return {k: (str(obj[k]) if obj.get(k) is not None else None) for k in keys if k in obj}


def abbreviated(value, max_length=300):
    """For display: value with long strings (e.g. base64 images) cut short, saying how long they were."""
    if isinstance(value, str) and len(value) > max_length:
        return f"{value[:60]}... ({len(value)} characters in all)"
    if isinstance(value, dict):
        return {k: abbreviated(v, max_length) for k, v in value.items()}
    if isinstance(value, list):
        return [abbreviated(v, max_length) for v in value]
    return value
