import hmac
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
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseForbidden, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from puzzles.tasks import add_user_to_puzzle, get_service_status, post_discord_message
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
        if user_form.is_valid() and profile_form.is_valid() and secret_matches('magic-secret', user_form.cleaned_data['magic_secret']):
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
        'rounds': Round.objects.filter(hunt_id=settings.HERRING_HUNT_ID).prefetch_related('puzzle_set'),
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


DISCORD_JOIN_FAILED_HTML = (
    "<p>Herring couldn't add you to this puzzle's Discord channel. Check that your Discord username "
    "in <a href='/edit_profile/'>your profile</a> is right, or ask an admin.</p>")


class DiscordRedirect(HttpResponseRedirect):
    allowed_schemes = ['https', 'discord']

# How long the Discord link waits for a Celery worker to add the user to the channel.
DISCORD_JOIN_TIMEOUT_SECONDS = 20

@login_required
def discord_channel_link(request, puzzle_id, use_app):
    puzzle = get_object_or_404(Puzzle, pk=puzzle_id)
    # A Celery worker (which holds the Discord connection) adds the user to the
    # channel. Wait for it, so the channel is visible once Discord opens it.
    try:
        channel_id = add_user_to_puzzle.delay(request.user.id, puzzle.slug).get(timeout=DISCORD_JOIN_TIMEOUT_SECONDS)
    except Exception:
        logging.error("discord_channel_link: adding %s to %s failed or timed out", request.user, puzzle.slug, exc_info=True)
        return HttpResponse("Herring couldn't reach Discord in time. Try again in a minute, or ask an admin.",
                            status=504, content_type='text/plain')
    if channel_id is None:
        logging.warning("discord_channel_link: couldn't add %s to %s's channel", request.user, puzzle.slug)
        return HttpResponse(DISCORD_JOIN_FAILED_HTML, status=404)
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

# The only fields the puzzle page edits; everything else is admin-only.
EDITABLE_PUZZLE_FIELDS = {'answer', 'note', 'tags'}

def update_puzzle(request, puzzle_id):
    puzzle = get_object_or_404(Puzzle, pk=puzzle_id)
    try:
        updates = parse_puzzle_updates(request.body)
    except ValueError as e:
        logging.warning("update_puzzle: rejected update to %s from %s: %s", puzzle.slug, request.user, e)
        return HttpResponseBadRequest(str(e))
    for key, value in updates.items():
        setattr(puzzle, key, value)
    puzzle.save(update_fields=list(updates))
    return HttpResponse("Updated puzzle " + str(puzzle.slug))

def parse_puzzle_updates(body):
    """Parses and validates a JSON object of puzzle field updates; raises ValueError if invalid."""
    updates = json.loads(body)
    if not isinstance(updates, dict):
        raise ValueError("expected a JSON object")
    unknown = set(updates) - EDITABLE_PUZZLE_FIELDS
    if unknown:
        raise ValueError(f"fields not editable here: {sorted(unknown)}")
    for key, value in updates.items():
        check_puzzle_field_value(key, value)
    return updates

def check_puzzle_field_value(key, value):
    max_length = Puzzle._meta.get_field(key).max_length
    if not isinstance(value, str) or len(value) > max_length:
        raise ValueError(f"{key} must be a string of at most {max_length} characters")

# Disabled because it was never updated from slack to discord.
"""
@csrf_exempt
def run_scraper(request):
    scrape_activity_log.delay()
    return HttpResponse("ok")
"""

@csrf_exempt
@require_POST
def post_discord(request):
    """
    For scripts: posts `text` to the Discord channel named `channel`. The
    `token` field must match the 'post-discord-token' secret (in SECRETS);
    without that secret configured, every request is refused.
    """
    if not secret_matches('post-discord-token', request.POST.get('token')):
        logging.warning("post_discord: refused request with missing or wrong token (from %s, forwarded for %s)",
                        request.META.get('REMOTE_ADDR'), request.META.get('HTTP_X_FORWARDED_FOR'))
        return HttpResponseForbidden("missing or wrong token")
    post_discord_message.delay(request.POST.get('channel'), request.POST.get('text'))
    return HttpResponse("ok")


def secret_matches(name, supplied):
    """Whether `supplied` equals HERRING_SECRETS[name]. Always false if that secret isn't configured."""
    expected = settings.HERRING_SECRETS.get(name)
    if not expected or supplied is None:
        return False
    return hmac.compare_digest(supplied.encode(), expected.encode())


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
    now = datetime.now(timezone.utc)
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
        # channel_puzzle is keyed by slug (to_field), so its _id is the slug, with no extra query.
        channel_users[result.channel_puzzle_id].append(name)

    return channel_users
