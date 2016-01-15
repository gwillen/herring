import json
import re

from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse, JsonResponse
import django.contrib.auth
from django.contrib.auth.decorators import login_required

from .models import Round, Puzzle, to_json_value

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
    return JsonResponse(to_json_value(data))


@login_required
def one_puzzle(request, puzzle_id):
    if request.method == "POST":
        return update_puzzle(request, puzzle_id)
    else:
        return get_one_puzzle(request, puzzle_id)

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
        tags = puzzle.tags.split(',')
        if value not in tags:
            tags.append(value)
        puzzle.tags = ','.join(tags)
    elif command == '/untag':
        tags = [tag for tag in puzzle.tags.split(',') if tag.lower() != value.lower()]
        puzzle.tags = ','.join(tags)
    elif command == '/answer':
        puzzle.answer = value
    else:
        return HttpResponse("Don't know the command %r" % command)
    puzzle.save()
    return HttpResponse("Updated puzzle " + str(puzzle.slug))

