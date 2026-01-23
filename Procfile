release: python manage.py migrate
web: bin/start-pgbouncer daphne -b 0.0.0.0 -p $PORT progress_rpg.asgi:application
worker: RUNNING_CHANNEL_WORKER=1 python manage.py runworker default
celery: IS_CELERY_WORKER=1 celery -A progress_rpg worker --concurrency=2 --loglevel=info
