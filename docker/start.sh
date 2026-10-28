#!/bin/sh
# Container init 
set -e

# bring the database schema up to date
python manage.py migrate --noinput

# serve the app
exec gunicorn config.wsgi \
    --bind 0.0.0.0:8000 \
    --workers "${GUNICORN_WORKERS:-3}" \
    --threads 4 \
    --access-logfile - \
    --forwarded-allow-ips "*"
