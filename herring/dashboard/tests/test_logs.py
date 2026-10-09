import logging
from unittest import mock

from django.conf import settings
from django.test import TestCase

from dashboard import logs
from herring import log_buffer
from puzzles.tests.helpers import make_superuser, make_user


def clear_buffer():
    logs.redis().delete(settings.HERRING_LOG_STREAM_KEY, settings.HERRING_LOG_LEVELS_KEY)


def capture(logger_name, level, message, **kwargs):
    """Logs through a fresh buffer handler (configured like the real one) and returns it."""
    handler = log_buffer.RedisLogHandler(settings.REDIS_URL, settings.HERRING_LOG_STREAM_KEY,
                                         settings.HERRING_LOG_LEVELS_KEY, max_entries=1000)
    record = logging.LogRecord(logger_name, level, __file__, 1, message, None, kwargs.get('exc_info'))
    with mock.patch.object(log_buffer.threading, 'Thread'):  # no background refresher in tests
        handler.emit(record)
    return handler


class LogBufferTests(TestCase):
    def setUp(self):
        clear_buffer()
        self.addCleanup(clear_buffer)

    def test_records_are_captured_with_metadata(self):
        capture('puzzles.tasks', logging.WARNING, 'something odd')
        [entry] = logs.read_entries(logs.LogFilter())
        self.assertEqual((entry['level'], entry['logger'], entry['message']), ('WARNING', 'puzzles.tasks', 'something odd'))
        self.assertIn(str(__import__('os').getpid()), entry['process'])

    def test_tracebacks_are_kept(self):
        try:
            raise ValueError('boom')
        except ValueError:
            import sys
            capture('puzzles', logging.ERROR, 'failed', exc_info=sys.exc_info())
        [entry] = logs.read_entries(logs.LogFilter())
        self.assertIn('ValueError: boom', entry['message'])

    def test_filters(self):
        capture('discord.gateway', logging.DEBUG, 'heartbeat')
        capture('puzzles.views', logging.WARNING, 'rejected update')
        capture('puzzlesx', logging.ERROR, 'not a child of puzzles')
        messages = lambda **kw: [e['message'] for e in logs.read_entries(logs.LogFilter(**kw))]
        self.assertEqual(messages(min_level='WARNING'), ['not a child of puzzles', 'rejected update'])
        self.assertEqual(messages(logger='puzzles'), ['rejected update'])
        self.assertEqual(messages(text='HEART'), ['heartbeat'])

    def test_paging_and_tailing(self):
        for i in range(5):
            capture('puzzles', logging.INFO, f'message {i}')
        newest_two = logs.read_entries(logs.LogFilter(), limit=2)
        self.assertEqual([e['message'] for e in newest_two], ['message 4', 'message 3'])
        older = logs.read_entries(logs.LogFilter(), before=newest_two[-1]['id'], limit=10)
        self.assertEqual([e['message'] for e in older], ['message 2', 'message 1', 'message 0'])
        self.assertEqual(logs.read_entries(logs.LogFilter(), after=newest_two[0]['id']), [])

    def test_saved_levels_are_applied_to_loggers(self):
        logs.save_levels({'herring.test.verbose': 'DEBUG', 'ignored': 'NOT-A-LEVEL'})
        self.addCleanup(logging.getLogger('herring.test.verbose').setLevel, logging.NOTSET)
        handler = capture('puzzles', logging.INFO, 'first record starts the refresher')
        self.assertEqual(handler.applied_levels, {'': 'INFO', 'herring.test.verbose': 'DEBUG'})
        self.assertEqual(logging.getLogger('herring.test.verbose').level, logging.DEBUG)

    def test_redis_failure_does_not_raise(self):
        handler = log_buffer.RedisLogHandler('redis://nonexistent-host:6379/0', 'k', 'l', 10)
        with mock.patch('sys.stderr'):
            handler.emit(logging.LogRecord('x', logging.ERROR, __file__, 1, 'm', None, None))
        self.assertGreater(handler.failed_at, 0)


class DashboardViewTests(TestCase):
    def setUp(self):
        clear_buffer()
        self.addCleanup(clear_buffer)

    def test_staff_only(self):
        self.client.force_login(make_user())
        for url in ['/dashboard/', '/dashboard/logs/', '/dashboard/logs/entries.json']:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 302)  # to the admin login

    def test_pages_render_for_staff(self):
        self.client.force_login(make_superuser())
        capture('puzzles', logging.ERROR, '<b>not html</b>')
        self.assertContains(self.client.get('/dashboard/'), 'Herring version')
        self.assertContains(self.client.get('/dashboard/logs/?level=ERROR'), '&lt;b&gt;not html&lt;/b&gt;')
        data = self.client.get('/dashboard/logs/entries.json?level=ERROR').json()
        self.assertEqual([e['message'] for e in data['entries']], ['<b>not html</b>'])

    def test_save_levels(self):
        self.client.force_login(make_superuser())
        response = self.client.post('/dashboard/logs/levels/',
                                    {'logger': ['', 'puzzles', 'discord'], 'level': ['WARNING', 'DEBUG', '']})
        self.assertRedirects(response, '/dashboard/logs/#levels', fetch_redirect_response=False)
        self.assertEqual(logs.current_levels(), {'': 'WARNING', 'puzzles': 'DEBUG'})
