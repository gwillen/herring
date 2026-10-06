from datetime import timedelta

from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from puzzles import views
from puzzles.models import ChannelParticipation, Puzzle
from .helpers import make_puzzle, make_round, make_user


def make_hunt(rounds, puzzles_per_round, members_per_puzzle):
    now = timezone.now()
    for r in range(rounds):
        parent = make_round(name=f'Round {r}', number=r)
        for p in range(puzzles_per_round):
            puzzle = make_puzzle(parent, name=f'Puzzle {r}-{p}', number=p)
            ChannelParticipation.objects.bulk_create(
                ChannelParticipation(channel_puzzle=puzzle, user_id=f'user{m}#1', is_member=True,
                                     last_active=now - timedelta(minutes=m))
                for m in range(members_per_puzzle))


class PuzzleDataQueryTests(TestCase):
    """The main page polls /puzzles/ every 10s; its query count must not grow with the hunt's size."""

    def setUp(self):
        self.client.force_login(make_user())

    def count_queries(self):
        views.compute_active_users.cache_clear()
        with CaptureQueriesContext(connection) as queries:
            self.assertEqual(self.client.get('/puzzles/').status_code, 200)
        return len(queries)

    def test_query_count_independent_of_hunt_size(self):
        make_hunt(rounds=2, puzzles_per_round=2, members_per_puzzle=2)
        small = self.count_queries()
        make_hunt(rounds=8, puzzles_per_round=10, members_per_puzzle=5)
        large = self.count_queries()
        self.assertEqual(small, large, f"{small} queries for a small hunt but {large} for a large one")
