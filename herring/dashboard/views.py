from django.conf import settings
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
import json
import logging

from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from herring.log_buffer import LEVEL_NAMES
from herring.version import herring_version
from puzzles import redis_state, site_settings
from puzzles.models import SiteSettingChange
from puzzles.redis_state import listener_heartbeat
from . import discord_api, logs, server_structure, setup_apply, setup_flow
from .models import DiscordServerSnapshot, SetupPlan

logger = logging.getLogger(__name__)

PAGE_SIZE = 200


@staff_member_required
def home(request):
    context = {
        'version': herring_version(),
        'site': site_settings.current(),
        'heartbeat': listener_heartbeat(),
        'heartbeat_limit': redis_state.DISCORD_STATUS_TTL_SECONDS,
        'log_entries': logs.buffer_size(),
        'log_capacity': settings.HERRING_LOG_BUFFER_ENTRIES,
        'log_levels': sorted(logs.current_levels().items()),
        'unapplied_migrations': unapplied_migrations(),
    }
    return render(request, 'dashboard/home.html', context)


def unapplied_migrations():
    """Names of migrations the database is missing (pages using their tables would fail)."""
    executor = MigrationExecutor(connection)
    return [f"{migration.app_label}.{migration.name}"
            for migration, backwards in executor.migration_plan(executor.loader.graph.leaf_nodes())]


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
    context = {'snapshots': DiscordServerSnapshot.objects.only('guild_id', 'guild_name', 'taken_at', 'taken_by', 'errors', 'origin'),
               'plans': SetupPlan.objects.select_related('source', 'target'),
               'configured_guild_id': str(site_settings.guild_id())}
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
               'raw_json': json.dumps(server_structure.abbreviated(sections), indent=2, sort_keys=True)}
    return render(request, 'dashboard/snapshot.html', context)


@staff_member_required
@require_POST
def import_template(request):
    """Saves a Discord server template (given its discord.new link or code) as a snapshot."""
    code = request.POST['template'].strip().rstrip('/').rsplit('/', 1)[-1]
    try:
        template = discord_api.run(discord_api.fetch_template(code))
    except Exception as e:
        logger.error("Reading server template %r failed", code, exc_info=True)
        messages.error(request, f"Couldn't read template {code!r}: {type(e).__name__}: {e}")
        return redirect('dashboard:discord')
    snapshot = DiscordServerSnapshot.objects.create(
        guild_id=int(template['source_guild_id']), guild_name=f"{template['name']} (template {code})", origin='template',
        taken_by=request.user, herring_version=herring_version(), sections=server_structure.sections_from_template(template))
    logger.info("Saved server template %s as snapshot %s for %s", code, snapshot.id, request.user)
    return redirect('dashboard:snapshot', snapshot_id=snapshot.id)


@staff_member_required
@require_POST
def create_setup_plan(request):
    source = get_object_or_404(DiscordServerSnapshot, id=request.POST['source'])
    target_guild_id, server_name = int(request.POST['target']), request.POST['server_name'].strip()
    if target_guild_id == source.guild_id or not server_name:
        messages.error(request, "Choose a target server other than the source, and a server name.")
        return redirect('dashboard:discord')
    try:
        plan = setup_flow.create_plan(source, target_guild_id, server_name, request.user)
    except Exception as e:
        logger.error("Making a setup plan for server %s failed", target_guild_id, exc_info=True)
        messages.error(request, f"Couldn't make a setup plan: {type(e).__name__}: {e}")
        return redirect('dashboard:discord')
    return redirect('dashboard:setup_plan', plan_id=plan.id)


@staff_member_required
def setup_plan_detail(request, plan_id):
    plan = get_object_or_404(SetupPlan.objects.select_related('source', 'target', 'acknowledged_by'), id=plan_id)
    operations = [with_display_fields(op) for op in plan.operations.all()]
    context = {'plan': plan, 'operations': operations, 'in_progress': any(op.status == 'queued' for op in operations),
               'counts': {s: sum(1 for op in operations if op.status == s) for s in ('applied', 'existing', 'failed', 'skipped')}}
    return render(request, 'dashboard/setup_plan.html', context)


def with_display_fields(operation):
    operation.display_body = server_structure.abbreviated(operation.body)
    operation.display_result = server_structure.abbreviated(operation.result)
    return operation


@staff_member_required
@require_POST
def apply_setup_plan(request, plan_id):
    plan = get_object_or_404(SetupPlan, id=plan_id)
    if plan.operations.filter(status='queued').exists():
        messages.error(request, "This plan is already being applied.")
    elif plan.warnings and not plan.acknowledged_by and request.POST.get('acknowledge') != 'yes':
        messages.error(request, "This server doesn't look new; tick the confirmation to apply anyway.")
    else:
        start_applying(request, plan)
    return redirect('dashboard:setup_plan', plan_id=plan.id)


def start_applying(request, plan):
    if plan.warnings and not plan.acknowledged_by:
        plan.acknowledged_by = request.user
        plan.save(update_fields=['acknowledged_by'])
    queued = setup_apply.queue_operations(plan, request.POST.getlist('operation'))
    logger.info("%s queued %d operations of setup plan %s: %s", request.user, len(queued), plan.id, queued)
    setup_apply.apply_setup_plan.delay(plan.id, request.user.id)
    messages.success(request, f"Applying {len(queued)} operations; this page updates as they finish.")


@staff_member_required
def settings_page(request):
    site = site_settings.current()
    context = {'site': site, 'row': site_settings.read_row(), 'env': settings,
               'changes': SiteSettingChange.objects.select_related('changed_by')[:50]}
    if settings.HERRING_ACTIVATE_DISCORD:
        context |= discord_choices(site.discord_guild_id)
    return render(request, 'dashboard/settings.html', context)


def discord_choices(guild_id):
    """The servers the bot is in, and the current server's categories, for the settings form."""
    try:
        guilds, _ = discord_api.run(discord_api.fetch_bot_guilds())
        categories = discord_api.run(discord_api.fetch_categories(guild_id)) if guild_id else []
    except Exception as e:
        logger.error("Couldn't read servers/categories from Discord for the settings page", exc_info=True)
        return {'discord_error': f"{type(e).__name__}: {e}"}
    return {'guilds': guilds, 'categories': categories,
            'guild_known': guild_id is None or str(guild_id) in {g['id'] for g in guilds}}


@staff_member_required
@require_POST
def save_settings(request):
    try:
        changes = settings_from_form(request.POST)
    except ValueError as e:
        messages.error(request, f"Not saved: {e}")
        return redirect('dashboard:settings')
    changed = site_settings.update(request.user, **changes)
    messages.success(request, f"Saved: {', '.join(changed)}." if changed else "Nothing changed.")
    return redirect('dashboard:settings')


def settings_from_form(form):
    """The site settings the form sets. Switches the environment has turned off aren't on the form, so stay as they are."""
    changes = {'hunt_id': optional_int(form.get('hunt_id', ''), 'hunt ID'),
               'protected_category_ids': sorted(form.getlist('protected_category_ids'))}
    if settings.HERRING_ACTIVATE_DISCORD:
        changes |= {'discord_enabled': 'discord_enabled' in form,
                    'discord_guild_id': optional_int(form.get('discord_guild_id', ''), 'server ID')}
    if settings.HERRING_ACTIVATE_GAPPS:
        changes['gapps_enabled'] = 'gapps_enabled' in form
    return changes


def optional_int(text, label):
    text = text.strip()
    if not text:
        return None
    if not text.isdigit():
        raise ValueError(f"the {label} must be a number")
    return int(text)
