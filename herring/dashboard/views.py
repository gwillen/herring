from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from herring.log_buffer import LEVEL_NAMES
from herring.version import herring_version
from puzzles.redis_state import discord_connected
from . import logs

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
