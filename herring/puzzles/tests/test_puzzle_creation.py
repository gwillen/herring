from unittest import mock

from django.test import TestCase, override_settings

from puzzles import discordbot, tasks
from puzzles.models import Puzzle
from .helpers import make_puzzle, make_round


@override_settings(HERRING_ACTIVATE_GAPPS=True, HERRING_ACTIVATE_DISCORD=True)
class PuzzleCreationTasksTests(TestCase):
    def setUp(self):
        self.puzzle = make_puzzle(make_round())

    def run_creation(self, make_sheet_results):
        with mock.patch.object(tasks, 'make_sheet', side_effect=make_sheet_results) as make_sheet, \
                mock.patch.object(tasks, 'do_in_discord') as do_in_discord, \
                mock.patch.object(tasks, 'DISCORD_ANNOUNCER'):
            tasks.create_puzzle_sheet_and_channel.delay(self.puzzle.slug)
        self.puzzle.refresh_from_db()
        return make_sheet, do_in_discord

    def test_creates_sheet_and_channels(self):
        make_sheet, do_in_discord = self.run_creation(['SHEET1'])
        self.assertEqual(self.puzzle.sheet_id, 'SHEET1')
        do_in_discord.assert_called_once()

    def test_sheet_failure_retries_sheet_only(self):
        make_sheet, do_in_discord = self.run_creation([RuntimeError('Google is down'), 'SHEET2'])
        self.assertEqual(make_sheet.call_count, 2)
        self.assertEqual(self.puzzle.sheet_id, 'SHEET2')
        do_in_discord.assert_called_once()  # channels created (and announced) once

    @override_settings(HERRING_ACTIVATE_GAPPS=False)
    def test_no_sheet_without_google(self):
        make_sheet, do_in_discord = self.run_creation(['unused'])
        make_sheet.assert_not_called()
        do_in_discord.assert_called_once()


class ChannelTopicTests(TestCase):
    @override_settings(HERRING_HOST='http://192.0.2.1:18000')
    def test_topic_links_to_sheet_page(self):
        puzzle = make_puzzle(make_round(), hunt_url='https://hunt.example/p1')
        self.assertIn(f'Sheet: http://192.0.2.1:18000/s/{puzzle.id} - Puzzle: https://hunt.example/p1',
                      discordbot._build_topic(puzzle))
