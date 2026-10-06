import json
from unittest import mock

from django.test import TestCase, override_settings

from puzzles.models import Puzzle
from .helpers import make_puzzle, make_round, make_user

SECRETS = {'magic-secret': 'test-magic', 'post-discord-token': 'right-token'}


@override_settings(HERRING_SECRETS=SECRETS)
class PostDiscordTests(TestCase):
    def post(self, **fields):
        with mock.patch('puzzles.views.post_discord_message') as post_discord_message:
            response = self.client.post('/post_discord/', {'channel': 'general', 'text': 'hi', **fields})
        return response, post_discord_message.delay

    def test_correct_token_queues_post(self):
        response, queue_post = self.post(token='right-token')
        self.assertEqual(response.status_code, 200)
        queue_post.assert_called_once_with('general', 'hi')

    def test_missing_or_wrong_token_refused(self):
        for fields in [{}, {'token': ''}, {'token': 'wrong'}]:
            with self.subTest(fields=fields):
                response, queue_post = self.post(**fields)
                self.assertEqual(response.status_code, 403)
                queue_post.assert_not_called()

    @override_settings(HERRING_SECRETS={})
    def test_refused_when_token_not_configured(self):
        response, queue_post = self.post(token='')
        self.assertEqual(response.status_code, 403)
        queue_post.assert_not_called()

    def test_get_not_allowed(self):
        self.assertEqual(self.client.get('/post_discord/').status_code, 405)


class UpdatePuzzleTests(TestCase):
    def setUp(self):
        self.client.force_login(make_user())
        self.puzzle = make_puzzle(make_round())

    def post(self, body):
        return self.client.post(f'/puzzles/{self.puzzle.id}/', body, content_type='application/json')

    def assert_rejected(self, body):
        before = Puzzle.objects.values().get(id=self.puzzle.id)
        self.assertEqual(self.post(body).status_code, 400)
        self.assertEqual(Puzzle.objects.values().get(id=self.puzzle.id), before)

    def test_non_editable_fields_rejected(self):
        for field in ['hunt_id', 'sheet_id', 'name', 'is_meta', 'url']:
            with self.subTest(field=field):
                self.assert_rejected(json.dumps({field: 'x', 'note': 'sneaky'}))

    def test_invalid_values_rejected(self):
        for body in ['not json', '["answer"]', json.dumps({'answer': 5}), json.dumps({'note': 'x' * 201})]:
            with self.subTest(body=body):
                self.assert_rejected(body)

    def test_update_saves_only_that_field(self):
        Puzzle.objects.filter(id=self.puzzle.id).update(tags='from elsewhere')
        self.assertEqual(self.post(json.dumps({'note': 'hello'})).status_code, 200)
        self.puzzle.refresh_from_db()
        self.assertEqual((self.puzzle.note, self.puzzle.tags), ('hello', 'from elsewhere'))


class SignupSecretTests(TestCase):
    @override_settings(HERRING_SECRETS={})
    def test_signup_refused_when_magic_secret_not_configured(self):
        response = self.client.post('/signup/', {
            'username': 'newbie', 'password1': 'a-Long-pw-123', 'password2': 'a-Long-pw-123', 'magic_secret': '',
        })
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Thanks for joining')


@override_settings(SECURE_SSL_REDIRECT=True, SESSION_COOKIE_SECURE=True, CSRF_COOKIE_SECURE=True)
class HttpsSettingsTests(TestCase):
    def test_http_redirects_to_https(self):
        response = self.client.get('/accounts/login/')
        self.assertRedirects(response, 'https://testserver/accounts/login/', fetch_redirect_response=False,
                             status_code=301)

    def test_cookies_are_secure_over_https(self):
        make_user()
        response = self.client.post('/accounts/login/?next=/', {'username': 'solver', 'password': 'pw'},
                                    secure=True)
        self.assertTrue(response.cookies['sessionid']['secure'])
