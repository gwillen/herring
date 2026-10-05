from io import StringIO

from django.core.management import call_command
from django.test import TestCase


class MigrationTests(TestCase):
    def test_no_missing_migrations(self):
        """Models (including fields from third-party libraries) must match the migrations."""
        out = StringIO()
        try:
            call_command('makemigrations', '--check', '--dry-run', stdout=out)
        except SystemExit:
            self.fail(f"Models have changes not reflected in migrations:\n{out.getvalue()}")
