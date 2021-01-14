web: gunicorn --pythonpath=herring herring.wsgi --log-file -
# see https://github.com/celery/celery/issues/2839
worker: REMAP_SIGTERM=SIGQUIT celery worker --workdir=herring --app=herring -E --beat
