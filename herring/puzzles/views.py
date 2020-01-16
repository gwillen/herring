import json
import re

from cachetools.func import ttl_cache
from datetime import datetime, timedelta, timezone
from django.db.models import Count, F
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse, JsonResponse
import django.contrib.auth
from django.contrib.auth.decorators import login_required

from puzzles.tasks import scrape_activity_log

from .models import ChannelParticipation, Round, Puzzle, to_json_value

@login_required
def logout(request):
    if request.method == "POST":
        django.contrib.auth.logout(request)
    return redirect('/')

@login_required
def index(request):
    admins = django.contrib.auth.models.User.objects.filter(is_staff=True)
    context = {
        'username': request.user.username,
        'rounds': Round.objects.all(),
        'channel': 'general_chat',
        'admins': admins,
    }
    return render(request, 'puzzles/index.html', context)


@login_required
def get_resources(request):
    return render(request, 'puzzles/resources.html', {})


@login_required
def get_puzzles(request):
    data = {
        'rounds': Round.objects.all()
    }
    print("Serializing puzzle data.")
    return JsonResponse(add_metrics(to_json_value(data)))


@login_required
def one_puzzle(request, puzzle_id):
    if request.method == "POST":
        return update_puzzle(request, puzzle_id)
    else:
        return get_one_puzzle(request, puzzle_id)


@login_required
def puzzle_spreadsheet(request, puzzle_id):
    puzzle = get_object_or_404(Puzzle, pk=puzzle_id)
    return redirect(f'https://docs.google.com/spreadsheets/d/{puzzle.sheet_id}/edit')


def to_channel(title):
    return re.sub(r'\W+', '_', title.lower())

def get_one_puzzle(request, puzzle_id):
    puzzle = get_object_or_404(Puzzle, pk=puzzle_id)
    context = {
        'username': request.user.username,
        'puzzle': puzzle,
        'channel': to_channel(puzzle.name)
    }
    return render(request, 'puzzles/one_puzzle.html', context)

def update_puzzle(request, puzzle_id):
    puzzle = get_object_or_404(Puzzle, pk=puzzle_id)

    data = json.loads(request.body.decode('utf-8'))
    for key in data.keys():
        setattr(puzzle, key, data[key])
    puzzle.save()
    return HttpResponse("Updated puzzle " + str(puzzle.slug))

@csrf_exempt
def update_puzzle_hook(request):
    """
    Take a request from Slack to alter puzzle information.
    """
    puzzle = get_object_or_404(Puzzle, slug=request.POST.get('channel_name'))
    command = request.POST.get('command')
    value = request.POST.get('text')

    if command == '/notes':
        puzzle.note = value
    elif command == '/tag':
        tags = [t.strip() for t in puzzle.tags.split(',') if t.strip()]
        if value not in tags:
            tags.append(value)
        puzzle.tags = ', '.join(tags)
    elif command == '/untag':
        tags = [tag.strip() for tag in puzzle.tags.split(',') if tag.strip() and tag.lower() != value.lower()]
        puzzle.tags = ', '.join(tags)
    elif command == '/answer':
        puzzle.answer = value
    else:
        return HttpResponse("Don't know the command %r" % command)
    puzzle.save()
    return HttpResponse("Updated puzzle " + str(puzzle.slug))

@csrf_exempt
def run_scraper(request):
    scrape_activity_log.delay()
    return HttpResponse("ok")


def add_metrics(json):
    """
    This function exists because I am paranoid about making the big
    fetch-all-the-puzzles query too slow, and also I am too unclever right
    now to figure out how to coax Django into doing the correct join and
    aggregation logic. So instead we do the aggregation in a separate query
    (which we can cache), and manually join it to the JSON here.

    Probably this optimization is premature and unnecessary, and a future me
    or a future someone else is almost certainly more clever, so this may not
    remain in this form for long.
    """
    active_users_by_slug = compute_active_users()
    for r in json['rounds']:
        for p in r['puzzle_set']:
            p['channel_active_count'] = active_users_by_slug.get(p['slug'], 0)
    return json


@ttl_cache(ttl=5)
def compute_active_users():
    now = datetime.utcnow().replace(tzinfo=timezone.utc)
    results = ChannelParticipation.objects\
        .filter(is_member=True, last_active__gt=now - timedelta(hours=2))\
        .values(slug=F('channel_puzzle__slug'))\
        .annotate(active=Count('user_id'))
    return {result['slug']: result['active'] for result in results}
