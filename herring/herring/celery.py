from __future__ import absolute_import
# This boilerplate comes from:
# http://docs.celeryproject.org/en/latest/django/first-steps-with-django.html

import os
from celery import Celery
from celery.signals import setup_logging, worker_process_init

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'herring.settings')
from django.conf import settings

app = Celery('herring')
app.config_from_object('django.conf:settings', namespace='CELERY')


@setup_logging.connect
def config_loggers(*args, **kwargs):
    from logging.config import dictConfig
    dictConfig(settings.LOGGING)


@worker_process_init.connect
def on_worker_process_init(*args, **kwargs):
    app.tasks['puzzles.tasks.check_connection_to_slack'].delay()


app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)


@app.task(bind=True)
def debug_task(self):
    print('Request: {0!r}'.format(self.request))
