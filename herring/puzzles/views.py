from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse

from .models import Round, Puzzle


def index(request):
    context = {
        'rounds': Round.objects.all(),
    }
    return render(request, 'puzzles/index.html', context)


def get_puzzles(request):
    print("Serializing puzzle data.")
    return HttpResponse("Puzzle data.")


def update_puzzle(request, puzzle_id):
    puzzle = get_object_or_404(Puzzle, pk=puzzle_id)
    return HttpResponse("Updated puzzle " + str(puzzle_id))
