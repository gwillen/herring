#!/bin/sh

set -eu

# These are build dependencies for some of the Python packages in
# requirements.txt.
apk add gcc libffi-dev musl-dev openssl-dev postgresql-dev

pip install -r requirements.txt

# Honcho runs the Procfile in the dev environment; it isn't needed in Heroku.
pip install honcho

# If the database doesn't already exist, this initializes it.
herring/manage.py makemigrations
herring/manage.py migrate

# This assembles the staticfiles directory; Heroku performs this step
# automatically when it detects an appropriate Django app, so there is no need
# to commit the directory to Git.
herring/manage.py collectstatic --noinput --clear --link

# An easier way to create an admin user interactively is to call
# `herring/manage.py createsuperuser`, but it throws an error if the user
# already exists.
herring/manage.py shell <<EOF
from django.contrib.auth import get_user_model
users = get_user_model().objects
if not users.filter(username='admin').exists():
    users.create_superuser('admin', password='admin')
EOF

# gunicorn-dev.py configures Gunicorn to watch for file changes and reload
# automatically. It may eventually contain other settings exclusive to the dev
# environment.
#
# PYTHONUNBUFFERED=true keeps the output of the Procfile commands flowing;
# without that, Python buffers stdout when it is connected to a process like
# Honcho.
#
# We don't want Honcho to pull from the .env file, because docker-compose.yml
# already imports it, and Honcho and Compose disagree on how to interpret
# quotation marks and escape sequences. Instead, we point it at /dev/null.
#
# Finally, we run two copies of the worker process, both to ensure that there's
# enough concurrency despite the long-running Slack task that will occupy one
# of the worker subprocesses indefinitely, and to test that Celery Beat is
# configured such that scaling up workers doesn't cause tasks to be
# double-scheduled.
GUNICORN_CMD_ARGS="-c python:gunicorn-dev" \
PYTHONUNBUFFERED=true \
exec honcho -e /dev/null start -c worker=2
