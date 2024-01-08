import json
import logging
import re
from collections import defaultdict
from datetime import datetime, timedelta, timezone

import django.contrib.auth
import typing
from cachetools.func import ttl_cache
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Count, F
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt

from puzzles.tasks import add_user_to_puzzle, get_service_status
from .forms import UserProfileForm, UserSignupForm, UserEditForm
from .models import ChannelParticipation, Puzzle, Round, UserProfile, to_json_value

@never_cache
@login_required
def edit_profile(request):
    if request.method == 'POST':
        # XXX: this might let them change someone else's profile or something, don't imitate this if your app is important
        user_form = UserEditForm(request.POST, instance=request.user)
        profile_form = UserProfileForm(request.POST, instance=request.user.profile)
        if user_form.is_valid() and profile_form.is_valid():
            user_form.full_clean()
            user_form.save()
            profile_form.full_clean()
            profile_form.save()
            messages.success(request, 'Profile saved.')
        else:
            messages.error(request, "ERROR: Profile not saved. This is probably not your fault. Contact an admin.")
    else:
        user_form = UserEditForm(instance=request.user)
        profile_form = UserProfileForm(instance=request.user.profile)
    return render(request, 'registration/profile_edit.html', {'user_form': user_form, 'profile_form': profile_form})

@never_cache
def signup(request):
    if request.method == 'POST':
        user_form = UserSignupForm(request.POST)
        profile_form = UserProfileForm(request.POST)
        if user_form.is_valid() and profile_form.is_valid() and user_form.cleaned_data['magic_secret'] == settings.HERRING_SECRETS['magic-secret']:
            user:User = user_form.save(commit=False)
            user.is_active = True  # this was checking if they had the secret, but just block making the account instead
            user.save()
            user.refresh_from_db()  # load the profile instance created by the signal
            profile_form = UserProfileForm(request.POST, instance=user.profile)
            profile_form.full_clean()
            profile_form.save()
            greeting = user.first_name or user.username
            return render(request, 'registration/post_signup.html', {'username': greeting, 'active': user.is_active})
    else:
        user_form = UserSignupForm()
        profile_form = UserProfileForm()
    return render(request, 'registration/signup.html', {'user_form': user_form, 'profile_form': profile_form})


@login_required
def index(request):
    admins = django.contrib.auth.models.User.objects.filter(is_staff=True)
    context = {
        'username': request.user.username,
        'rounds': Round.objects.filter(hunt_id=settings.HERRING_HUNT_ID),
        'channel': 'general_chat',
        'admins': admins,
    }
    return render(request, 'puzzles/index.html', context)


@login_required
def get_resources(request):
    return render(request, 'puzzles/resources.html', {})


@login_required
def get_puzzles(request):
    try:
        profile = UserProfile.objects.get(user_id=request.user.id)
    except UserProfile.DoesNotExist:
        profile = {}
    data = {
        'rounds': Round.objects.filter(hunt_id=settings.HERRING_HUNT_ID),
        'settings': {
            'discord': settings.HERRING_ACTIVATE_DISCORD,
            'gapps': settings.HERRING_ACTIVATE_GAPPS,
            'profile': profile,
            'service_status': get_service_status(),
        },
    }
    logging.debug("Serializing puzzle data.")
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
    return redirect(f'https://docs.google.com/spreadsheets/d/{puzzle.sheet_id}/edit', permanent=True)


class DiscordRedirect(HttpResponseRedirect):
    allowed_schemes = ['https', 'discord']

@login_required
def discord_channel_link(request, puzzle_id, use_app):
    puzzle = get_object_or_404(Puzzle, pk=puzzle_id)
    user = request.user.id
    # intentional non-delayed task, because we don't have a results backend set up and we need to
    # wait until it finishes before redirecting!
    channel_id = add_user_to_puzzle(user, puzzle.slug)
    protocol = 'discord' if use_app else 'https'
    url = f'{protocol}://discordapp.com/channels/{settings.HERRING_DISCORD_GUILD_ID}/{channel_id}'
    logging.info(f'redirecting {request.user} to {url}')
    return DiscordRedirect(url)


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

# Disabled because it was never updated from slack to discord.
"""
@csrf_exempt
def run_scraper(request):
    scrape_activity_log.delay()
    return HttpResponse("ok")
"""

from puzzles.discordbot import DISCORD_ANNOUNCER, do_in_discord_nonblocking

@csrf_exempt
def post_discord(request):
    if request.method == "POST":
        #pm = request.POST.get('pm')
        channel = request.POST.get('channel')
        text = request.POST.get('text')
        do_in_discord_nonblocking(DISCORD_ANNOUNCER.post_message(channel, text))
        return HttpResponse("ok")
    else:
        return HttpResponse("please use POST")


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
            p['channel_active'] = active_users_by_slug.get(p['slug'], [])
    return json


@ttl_cache(ttl=5)
def compute_active_users():
    now = datetime.utcnow().replace(tzinfo=timezone.utc)
    results:typing.Sequence[ChannelParticipation] = ChannelParticipation.objects\
        .filter(is_member=True, last_active__gt=now - timedelta(hours=2))

    # I still don't know a really pythonic way to do this
    channel_users = defaultdict(list)
    for result in results:
        name = result.display_name
        if not name:
            hash_pos = result.user_id.rfind('#')
            if hash_pos >= 0:
                name = result.user_id[:hash_pos]
            else:
                name = result.user_id
        channel_users[result.channel_puzzle.slug].append(name)

    return channel_users
