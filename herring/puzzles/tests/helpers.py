from django.contrib.auth import get_user_model

from puzzles.models import Puzzle, Round


def make_round(name='Test Round', number=1):
    return Round.objects.create(name=name, number=number)


def make_puzzle(parent, name='Test Puzzle', number=1, **fields):
    return Puzzle.objects.create(parent=parent, name=name, number=number, **fields)


def make_user(username='solver', **fields):
    return get_user_model().objects.create_user(username=username, password='pw', **fields)


def make_superuser(username='boss'):
    return get_user_model().objects.create_superuser(username=username, password='pw')
