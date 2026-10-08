import logging
from unittest import mock

from django.test import SimpleTestCase

from herring.log_custom import ChatLogHandler


class ChatLogHandlerTests(SimpleTestCase):
    def emitted(self, logger_name, level, message):
        handler = ChatLogHandler()
        handler.start_time = 0  # past the startup quiet period
        record = logging.LogRecord(logger_name, level, __file__, 1, message, None, None)
        with mock.patch('puzzles.tasks.post_debug_message') as post:
            handler.emit(record)
        return post.delay.call_args_list

    def test_app_warning_is_queued_with_process_label(self):
        [call] = self.emitted('root', logging.WARNING, 'something odd')
        self.assertIn('something odd', call.args[1])
        self.assertNotIn('<unknown>', call.args[1])

    def test_discord_library_warnings_are_not_posted(self):
        self.assertEqual(self.emitted('discord.http', logging.WARNING, 'We are being rate limited.'), [])

    def test_discord_library_errors_are_posted(self):
        self.assertEqual(len(self.emitted('discord.client', logging.ERROR, 'Attempting a reconnect')), 1)
