from __future__ import absolute_import
# This boilerplate comes from:
# http://docs.celeryproject.org/en/latest/django/first-steps-with-django.html

import os
from celery import Celery

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'herring.settings')
from django.conf import settings

app = Celery('herring')
app.config_from_object('django.conf:settings')
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)


@app.task(bind=True)
def debug_task(self):
    print('Request: {0!r}'.format(self.request))
