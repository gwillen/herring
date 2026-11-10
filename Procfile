# Heroku runs this before each new release goes live; if it fails, the release doesn't.
release: python herring/manage.py migrate --noinput
web: gunicorn --pythonpath=herring herring.wsgi --log-file -
# see https://github.com/celery/celery/issues/2839
worker: REMAP_SIGTERM=SIGQUIT celery --workdir=herring --app=herring worker -E --beat
