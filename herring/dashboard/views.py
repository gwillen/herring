from django.conf import settings
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
import json
import logging

from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from herring.log_buffer import LEVEL_NAMES
from herring.version import herring_version
from puzzles.redis_state import discord_connected
from . import discord_api, logs, server_structure
from .models import DiscordServerSnapshot

logger = logging.getLogger(__name__)

PAGE_SIZE = 200


@staff_member_required
def home(request):
    context = {
        'version': herring_version(),
        'discord_active': settings.HERRING_ACTIVATE_DISCORD,
        'discord_connected': settings.HERRING_ACTIVATE_DISCORD and discord_connected(),
        'gapps_active': settings.HERRING_ACTIVATE_GAPPS,
        'hunt_id': settings.HERRING_HUNT_ID,
        'log_entries': logs.buffer_size(),
        'log_capacity': settings.HERRING_LOG_BUFFER_ENTRIES,
        'log_levels': sorted(logs.current_levels().items()),
    }
    return render(request, 'dashboard/home.html', context)


@staff_member_required
def logs_page(request):
    log_filter = logs.LogFilter.from_query(request.GET)
    context = {
        'filter': log_filter,
        'entries': logs.read_entries(log_filter, limit=PAGE_SIZE),
        'level_names': LEVEL_NAMES,
        'levels': sorted(logs.current_levels().items()),
        'page_size': PAGE_SIZE,
    }
    return render(request, 'dashboard/logs.html', context)


@staff_member_required
def log_entries(request):
    """JSON for the log page's live tail (?after=<id>) and 'older' button (?before=<id>)."""
    entries = logs.read_entries(logs.LogFilter.from_query(request.GET), before=request.GET.get('before'),
                                after=request.GET.get('after'), limit=PAGE_SIZE)
    # A full page means there may be more: for the live tail, that's a gap the page should point out.
    return JsonResponse({'entries': entries, 'more': len(entries) == PAGE_SIZE})


@staff_member_required
@require_POST
def save_log_levels(request):
    names, levels = request.POST.getlist('logger'), request.POST.getlist('level')
    logs.save_levels(dict(zip(names, levels)))
    return redirect(reverse('dashboard:logs') + '#levels')


@staff_member_required
def discord_servers(request):
    """The servers the bot is in, with snapshot buttons, and the saved snapshots."""
    context = {'snapshots': DiscordServerSnapshot.objects.only('guild_id', 'guild_name', 'taken_at', 'taken_by', 'errors'),
               'configured_guild_id': str(settings.HERRING_DISCORD_GUILD_ID)}
    if not settings.HERRING_ACTIVATE_DISCORD:
        context['guilds_error'] = "the Discord integration is off (ACTIVATE_DISCORD)"
        return render(request, 'dashboard/discord_servers.html', context)
    try:
        context['guilds'], application_id = discord_api.run(discord_api.fetch_bot_guilds())
        context['invite_url'] = (f"https://discord.com/oauth2/authorize?client_id={application_id}"
                                 "&scope=bot+applications.commands&permissions=8")
    except Exception as e:
        logger.error("Couldn't list the bot's Discord servers", exc_info=True)
        context['guilds_error'] = f"{type(e).__name__}: {e}"
    return render(request, 'dashboard/discord_servers.html', context)


@staff_member_required
@require_POST
def take_snapshot(request):
    guild_id = int(request.POST['guild_id'])
    try:
        sections, errors = discord_api.run(discord_api.fetch_server_structure(guild_id))
    except Exception as e:
        logger.error("Snapshot of Discord server %s failed", guild_id, exc_info=True)
        messages.error(request, f"Snapshot of server {guild_id} failed: {type(e).__name__}: {e}")
        return redirect('dashboard:discord')
    snapshot = DiscordServerSnapshot.objects.create(
        guild_id=guild_id, guild_name=sections.get('guild', {}).get('name', '(unknown)'), taken_by=request.user,
        herring_version=herring_version(), sections=sections, errors=errors)
    logger.info("Saved snapshot %s of Discord server %s for %s (unreadable sections: %s)",
                snapshot.id, snapshot, request.user, sorted(errors) or 'none')
    return redirect('dashboard:snapshot', snapshot_id=snapshot.id)


@staff_member_required
def snapshot_detail(request, snapshot_id):
    snapshot = get_object_or_404(DiscordServerSnapshot, id=snapshot_id)
    sections = snapshot.sections
    context = {'snapshot': snapshot, 'guild': sections.get('guild', {}),
               'roles': server_structure.role_rows(sections), 'channel_tree': server_structure.channel_tree(sections),
               'onboarding': server_structure.onboarding_summary(sections),
               'counts': server_structure.section_counts(sections),
               'raw_json': json.dumps(sections, indent=2, sort_keys=True)}
    return render(request, 'dashboard/snapshot.html', context)
