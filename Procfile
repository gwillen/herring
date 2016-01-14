web: gunicorn --pythonpath=herring herring.wsgi --log-file -
worker: herring/manage.py celery worker
