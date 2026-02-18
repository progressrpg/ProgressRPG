release: python manage.py migrate
web: bin/start-pgbouncer daphne -b 0.0.0.0 -p $PORT progress_rpg.asgi:application
celery: IS_CELERY_WORKER=1 celery -A progress_rpg worker --concurrency=1 --loglevel=info
beat: celery -A progress_rpg beat --loglevel=info
