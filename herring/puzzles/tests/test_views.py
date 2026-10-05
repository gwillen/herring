import json

from django.contrib.auth import get_user_model
from django.test import TestCase

from puzzles import views
from puzzles.models import ChannelParticipation, Puzzle
from .helpers import make_puzzle, make_round, make_superuser, make_user


class AnonymousTests(TestCase):
    def test_index_redirects_to_login(self):
        response = self.client.get('/')
        self.assertRedirects(response, '/accounts/login/?next=/')

    def test_puzzle_data_requires_login(self):
        self.assertEqual(self.client.get('/puzzles/').status_code, 302)

    def test_login_page_shows_team_name(self):
        response = self.client.get('/accounts/login/')
        self.assertContains(response, 'please log in')

    def test_login_without_next_goes_home(self):
        make_user()
        response = self.client.post('/accounts/login/', {'username': 'solver', 'password': 'pw'})
        self.assertRedirects(response, '/', fetch_redirect_response=False)

    def test_login_with_password(self):
        make_user()
        response = self.client.post('/accounts/login/?next=/', {'username': 'solver', 'password': 'pw'})
        self.assertRedirects(response, '/', fetch_redirect_response=False)


class SignupTests(TestCase):
    def signup(self, magic):
        return self.client.post('/signup/', {
            'username': 'newbie', 'first_name': 'New', 'last_name': 'Bie',
            'email': 'n@example.com', 'password1': 'a-Long-pw-123', 'password2': 'a-Long-pw-123',
            'magic_secret': magic, 'discord_identifier': 'newbie#1234',
        })

    def test_signup_page_renders(self):
        self.assertEqual(self.client.get('/signup/').status_code, 200)

    def test_signup_with_magic_creates_user_and_profile(self):
        response = self.signup('test-magic')
        self.assertContains(response, 'Thanks for joining the team, New')
        user = get_user_model().objects.get(username='newbie')
        self.assertEqual(user.profile.discord_identifier, 'newbie#1234')

    def test_signup_without_magic_creates_nothing(self):
        self.signup('wrong')
        self.assertFalse(get_user_model().objects.filter(username='newbie').exists())


class SolverTests(TestCase):
    def setUp(self):
        views.compute_active_users.cache_clear()
        self.user = make_user(email='solver@example.com')
        self.client.force_login(self.user)
        self.round = make_round(name='Round One')
        self.puzzle = make_puzzle(self.round, name='Anagrams')

    def test_index_loads_bundle(self):
        self.assertContains(self.client.get('/'), 'bundle.js')

    def test_resources_page(self):
        self.assertEqual(self.client.get('/resources/').status_code, 200)

    def test_puzzle_data(self):
        data = self.client.get('/puzzles/').json()
        puzzle = data['rounds'][0]['puzzle_set'][0]
        self.assertEqual(puzzle['slug'], self.puzzle.slug)
        self.assertEqual(puzzle['channel_active'], [])
        self.assertEqual(data['settings']['service_status'], {'discord': None, 'gapps': None})

    def test_one_puzzle_page(self):
        self.assertContains(self.client.get(f'/puzzles/{self.puzzle.id}/'), 'Anagrams')

    def test_update_answer_note_tags(self):
        for field in ['answer', 'note', 'tags']:
            self.post_update({field: f'new {field}'})
        self.puzzle.refresh_from_db()
        self.assertEqual((self.puzzle.answer, self.puzzle.note, self.puzzle.tags),
                         ('new answer', 'new note', 'new tags'))

    def test_spreadsheet_redirect(self):
        Puzzle.objects.filter(id=self.puzzle.id).update(sheet_id='SHEET')
        response = self.client.get(f'/s/{self.puzzle.id}')
        self.assertRedirects(response, 'https://docs.google.com/spreadsheets/d/SHEET/edit',
                             status_code=301, fetch_redirect_response=False)

    def test_edit_profile(self):
        self.assertEqual(self.client.get('/edit_profile/').status_code, 200)
        self.client.post('/edit_profile/', {'first_name': 'Sol', 'last_name': 'Ver',
                                            'discord_identifier': 'solver#1'})
        self.user.refresh_from_db()
        self.assertEqual((self.user.first_name, self.user.profile.discord_identifier), ('Sol', 'solver#1'))

    def test_edit_profile_without_email(self):
        self.user.email = ''
        self.user.save()
        self.client.post('/edit_profile/', {'first_name': 'Sol', 'last_name': 'Ver', 'discord_identifier': 'x#1'})
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Sol')

    def test_active_users_listed(self):
        ChannelParticipation.objects.create(channel_puzzle=self.puzzle, user_id='abc#1', is_member=True,
                                            last_active=self.puzzle.last_active, display_name='')
        data = self.client.get('/puzzles/').json()
        self.assertEqual(data['rounds'][0]['puzzle_set'][0]['channel_active'], ['abc'])

    def test_logout(self):
        self.client.post('/accounts/logout/')
        self.assertEqual(self.client.get('/').status_code, 302)

    def post_update(self, data):
        response = self.client.post(f'/puzzles/{self.puzzle.id}/', json.dumps(data),
                                    content_type='application/json')
        self.assertEqual(response.status_code, 200)
        return response


class AdminTests(TestCase):
    PAGES = ['/admin/', '/admin/puzzles/round/', '/admin/puzzles/round/add/', '/admin/puzzles/puzzle/',
             '/admin/puzzles/puzzle/add/', '/admin/puzzles/userprofile/', '/admin/auth/user/']

    def setUp(self):
        self.admin = make_superuser()
        self.client.force_login(self.admin)
        self.round = make_round()
        self.puzzle = make_puzzle(self.round)

    def test_admin_pages_render(self):
        pages = self.PAGES + [f'/admin/puzzles/round/{self.round.id}/change/',
                              f'/admin/puzzles/puzzle/{self.puzzle.id}/change/',
                              f'/admin/auth/user/{self.admin.id}/change/']
        for page in pages:
            with self.subTest(page=page):
                self.assertEqual(self.client.get(page).status_code, 200)

    def test_add_round_with_inline_puzzle(self):
        response = self.client.post('/admin/puzzles/round/add/', {
            'hunt_id': 0, 'number': 2, 'name': 'Round Two', 'hunt_url': '',
            'puzzle_set-TOTAL_FORMS': 1, 'puzzle_set-INITIAL_FORMS': 0,
            'puzzle_set-0-hunt_id': 0, 'puzzle_set-0-name': 'Inline Puzzle', 'puzzle_set-0-number': 1,
            'puzzle_set-0-hunt_url': '',
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Puzzle.objects.filter(name='Inline Puzzle', parent__name='Round Two').exists())
