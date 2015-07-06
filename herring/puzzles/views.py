from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, JsonResponse

from .models import Round, Puzzle, to_json_value


def index(request):
    context = {
        'rounds': Round.objects.all(),
    }
    return render(request, 'puzzles/index.html', context)


def get_puzzles(request):
    data = {
        'rounds': Round.objects.all()
    }
    print("Serializing puzzle data.")
    return JsonResponse(to_json_value(data))

def update_puzzle(request, puzzle_id):
    puzzle = get_object_or_404(Puzzle, pk=puzzle_id)
    # TODO: update puzzle with POST body
    return HttpResponse("Updated puzzle " + str(puzzle_id))
