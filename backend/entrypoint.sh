#!/bin/sh
set -e

python manage.py migrate --noinput
python manage.py collectstatic --noinput 2>/dev/null || true

if [ "$RUN_SEED" = "1" ]; then
  python manage.py seed_demo_data
fi

exec python manage.py runserver 0.0.0.0:8000
