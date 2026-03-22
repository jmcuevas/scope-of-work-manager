#!/bin/bash
set -e
python manage.py migrate --noinput
exec gunicorn scope_manager.wsgi --workers 2 --bind "0.0.0.0:${PORT:-8000}"
