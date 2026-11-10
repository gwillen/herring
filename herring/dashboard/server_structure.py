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
