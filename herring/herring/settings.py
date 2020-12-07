"""
Django settings for herring project.

Generated by 'django-admin startproject' using Django 1.8.2.

For more information on this file, see
https://docs.djangoproject.com/en/1.8/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.8/ref/settings/
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import json
import os

import environ

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

env = environ.Env()
environ.Env.read_env(os.path.join(os.path.dirname(BASE_DIR), '.env'))

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.8/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = '+fn9lj!kwzxqzpxihje!_+o0!y8ork#@+wc19w_mnf7^6gi4d$'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env.get_value('DEBUG', default=False)

ALLOWED_HOSTS = []


# Application definition

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'puzzles',
)

MIDDLEWARE = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.security.SecurityMiddleware',
)

ROOT_URLCONF = 'herring.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'herring.wsgi.application'


# Database
# https://docs.djangoproject.com/en/1.8/ref/settings/#databases

DATABASES = {
    'default': env.db_url(
        default='postgres:///herringdb',
        engine='django.db.backends.postgresql_psycopg2')
}


# Internationalization
# https://docs.djangoproject.com/en/1.8/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Honor the 'X-Forwarded-Proto' header for request.is_secure()
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Allow all host headers
ALLOWED_HOSTS = ['*']

# Static asset configuration
STATIC_ROOT = 'staticfiles'
STATIC_URL = '/static/'
STATICFILES_DIRS = []

REDIS_URL = env.get_value('REDIS_URL', default='redis://localhost:6379/0')

# Celery queue
CELERY_BROKER_URL = env.get_value('BROKER_URL', default=REDIS_URL)
# max_retries here controls Celery's initial attempts to contact Redis, and
# defaults to *infinity*. Using a slightly smaller number is useful, for
# example, in development environments if the developer doesn't want to run a
# whole Redis+Celery stack and is okay with integrations not working.
CELERY_BROKER_TRANSPORT_OPTIONS = dict(max_retries=3)
CELERY_REDBEAT_REDIS_URL = REDIS_URL
CELERY_BEAT_SCHEDULER = 'redbeat.RedBeatScheduler'
CELERY_BEAT_SCHEDULE = {
    # 'read-google-sheets-changes': {
    #     'task': 'puzzles.tasks.process_google_sheets_changes',
    #     'schedule': 15.0,
    # },
    'check-connection-to-messaging': {
        'task': 'puzzles.tasks.check_connection_to_messaging',
        'schedule': 60.0,
    },
}

# This indirectly affects the expiration time of the lock RedBeat sets in
# Redis to ensure that only one scheduler is running. It largely doesn't
# matter unless the worker process with the active RedBeat instance is
# forcefully killed, in which case having a max_loop_interval of 30 seconds
# means that it could be up to 6 minutes before another RedBeat claims the
# lock and starts scheduling tasks again.
CELERY_BEAT_MAX_LOOP_INTERVAL = 30


# Previously in puzzles/tasks.py
HERRING_STATUS_CHANNEL = env.get_value('STATUS_CHANNEL', default='_dev_puzzle_status')
HERRING_HOST = env.get_value('HOST', default='http://localhost:8000')
HERRING_PUZZLE_ACTIVITY_LOG_URL = env.get_value('PUZZLE_ACTIVITY_LOG_URL', default=None)
HERRING_PUZZLE_SITE_SESSION_COOKIE = env.get_value('PUZZLE_SITE_SESSION_COOKIE', default=None)

HERRING_DISCORD_GUILD_ID = int(env.get_value('DISCORD_GUILD', default=750176135224229979))
HERRING_DISCORD_PROTECTED_CATEGORIES = set(json.loads(env.get_value('DISCORD_PROTECTED_CATEGORIES', default="[750176135849050192, 779933113450102834]")))
HERRING_DISCORD_PUZZLE_ANNOUNCEMENTS = env.get_value('DISCORD_ANNOUNCEMENTS', default='puzzle-announcements')

# Previously in herring/secrets.py
HERRING_SECRETS = json.loads(env.get_value('SECRETS', default='{}'))
HERRING_FUCK_OAUTH = json.loads(env.get_value('FUCK_OAUTH', default='{}'))

# This should be more dynamic in the future.
HERRING_HUNT_ID = int(env.get_value('HUNT_ID', default=0))

HERRING_ACTIVATE_GAPPS = env.bool('ACTIVATE_GAPPS', default=True)
HERRING_ACTIVATE_SLACK = env.bool('ACTIVATE_SLACK', default=True)
HERRING_ACTIVATE_DISCORD = env.bool('ACTIVATE_DISCORD', default=True)

HERRING_SOLVERTOOLS_URL = env.get_value('SOLVERTOOLS_URL', default="http://ireproof.org/")

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': env.get_value('LOG_LEVEL', default='INFO'),
    },
    'loggers': {
        'django.db.backends': {
            'handlers': ['console'],
            'level': env.get_value(
                'DJANGO_DB_LOG_LEVEL',
                default='DEBUG' if DEBUG else 'INFO'),
            'propagate': False,
        },
    },
}
