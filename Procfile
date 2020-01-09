web: gunicorn --pythonpath=herring herring.wsgi --log-file -
worker: celery worker --workdir=herring --app=herring -E
