"""
Settings for running the test suite: `manage.py test --settings=herring.settings_test`.
"""
from .settings import *  # noqa: F401,F403

# Run Celery tasks inline, so tests never need a broker.
CELERY_TASK_ALWAYS_EAGER = True

# External integrations stay off in tests regardless of what .env says.
HERRING_ACTIVATE_DISCORD = False
HERRING_ACTIVATE_GAPPS = False
HERRING_ENABLE_STANDALONE_DISCORD = False
HERRING_SECRETS = {'magic-secret': 'test-magic'}

# Hashing passwords slowly is pointless in tests.
PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']
