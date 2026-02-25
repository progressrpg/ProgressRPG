#!/bin/sh
set -e

# Wait for DB to be ready
until python - <<'PY'
import os
import sys
import psycopg2

try:
  connection = psycopg2.connect(
    dbname=os.getenv("POSTGRES_DB", "postgres"),
    user=os.getenv("POSTGRES_USER", "postgres"),
    password=os.getenv("POSTGRES_PASSWORD", ""),
    host=os.getenv("POSTGRES_HOST", "db"),
    port=os.getenv("POSTGRES_PORT", "5432"),
  )
  connection.close()
  sys.exit(0)
except Exception:
  sys.exit(1)
PY
do
  echo "Waiting for database..."
  sleep 2
done

echo "➡️ Running database migrations..."
python manage.py migrate

echo "➡️ Waiting a few seconds for migrations to settle..."
sleep 3

# Optional: load seed data
if [ -f "seed_data.json" ]; then
    echo "➡️ Loading seed data..."
    python manage.py loaddata seed_data.json
fi

# Optional: create superuser if not exists
python manage.py seed_superuser || echo "Superuser already exists"

# Optional: run world setup (your custom script)
# python manage.py setup_world || echo "World setup already done"

# Optional: generate initial character days
# python manage.py generate_character_days || echo "Character days already generated"

# Execute whatever command is passed to the container
exec "$@"
