#!/bin/sh
set -e

# Wait for DB to be ready
# until python - <<'PY'
# import os
# import sys
# import psycopg2

# try:
#   connection = psycopg2.connect(
#     dbname=os.getenv("POSTGRES_DB", "postgres"),
#     user=os.getenv("POSTGRES_USER", "postgres"),
#     password=os.getenv("POSTGRES_PASSWORD", ""),
#     host=os.getenv("POSTGRES_HOST", "db"),
#     port=os.getenv("POSTGRES_PORT", "5432"),
#   )
#   connection.close()
#   sys.exit(0)
# except Exception:
#   sys.exit(1)
# PY
# do
#   echo "Waiting for database..."
#   sleep 2
# done

echo "➡️ Running database migrations..."
python manage.py migrate --noinput

# Collect static files
# echo "➡️ Collecting static files..."
# python manage.py collectstatic --noinput

# Execute whatever command is passed to the container
echo "➡️ Starting service: $@"
exec "$@"
