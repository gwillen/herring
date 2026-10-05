from datetime import datetime, timedelta, timezone

from django.test import TestCase

from puzzles.models import Puzzle, UserProfile, to_json_value
from puzzles.slugtools import puzzle_to_slug, title_to_slug
from puzzles.spreadsheets import SheetChange
from .helpers import make_puzzle, make_round, make_user


class SlugToolsTests(TestCase):
    def test_title_to_slug_skips_common_words(self):
        self.assertEqual(title_to_slug('The Art of the Deal'), 'art-deal')

    def test_title_to_slug_stops_at_long_word(self):
        self.assertEqual(title_to_slug('Anagrams and Friends'), 'anagrams')

    def test_title_to_slug_falls_back_to_common_words(self):
        self.assertEqual(title_to_slug('Of The'), 'of-the')

    def test_puzzle_to_slug_includes_round_prefix(self):
        puzzle = make_puzzle(make_round(number=4), name='Anagrams')
        self.assertEqual(puzzle_to_slug(puzzle), 'r4-anagrams')

    def test_meta_puzzle_slug(self):
        puzzle = make_puzzle(make_round(number=2), name='Final Meta', is_meta=True)
        self.assertEqual(puzzle.slug, 'r2m-final')

    def test_duplicate_names_get_unique_slugs(self):
        parent = make_round()
        slugs = {make_puzzle(parent, name='Same').slug for _ in range(3)}
        self.assertEqual(len(slugs), 3)


class ActivityTrackerTests(TestCase):
    def setUp(self):
        self.puzzle = make_puzzle(make_round())
        self.start = self.puzzle.last_active

    def test_later_activity_moves_last_active(self):
        later = self.start + timedelta(minutes=10)
        self.assertTrue(self.puzzle.record_activity(later))
        self.assertEqual(self.puzzle.last_active, later)
        self.assertEqual(self.puzzle.activity_tracker & 1, 1)

    def test_earlier_activity_sets_older_bit(self):
        self.puzzle.record_activity(self.start + timedelta(minutes=10))
        self.puzzle.record_activity(self.start + timedelta(minutes=10) - timedelta(minutes=4))
        self.assertEqual(self.puzzle.activity_tracker & 0b100, 0b100)

    def test_repeated_activity_reports_no_change(self):
        later = self.start + timedelta(minutes=10)
        self.puzzle.record_activity(later)
        self.assertFalse(self.puzzle.record_activity(later))

    def test_batch_save_activity_persists(self):
        self.puzzle.record_activity(self.start + timedelta(hours=1))
        Puzzle.batch_save_activity([self.puzzle])
        self.puzzle.refresh_from_db()
        self.assertEqual(self.puzzle.activity_tracker, 1)

    def test_activity_histo_is_hex(self):
        self.puzzle.activity_tracker = 0xABC
        self.assertEqual(self.puzzle.activity_histo, '000000000000abc')


class JsonTests(TestCase):
    def test_round_json_includes_puzzles(self):
        parent = make_round(name='Round One')
        puzzle = make_puzzle(parent, name='Puzzle One')
        Puzzle.objects.filter(id=puzzle.id).update(answer='ANSWER')
        data = to_json_value(parent)
        self.assertEqual(data['name'], 'Round One')
        self.assertEqual([p['answer'] for p in data['puzzle_set']], ['ANSWER'])

    def test_puzzle_json_has_iso_datetime(self):
        puzzle = make_puzzle(make_round())
        datetime.fromisoformat(to_json_value(puzzle)['last_active'])


class UserProfileTests(TestCase):
    def test_profile_created_with_user(self):
        user = make_user()
        self.assertTrue(UserProfile.objects.filter(user=user).exists())


class SheetChangeTests(TestCase):
    def test_parses_zulu_time(self):
        change = SheetChange({'fileId': 'abc', 'time': '2026-01-16T12:34:56.789Z'})
        self.assertEqual(change.sheet_id, 'abc')
        self.assertEqual(change.datetime.tzinfo, timezone.utc)
