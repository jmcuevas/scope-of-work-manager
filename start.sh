#!/bin/bash
set -e
python manage.py migrate --noinput
exec uvicorn scope_manager.asgi:application --workers 2 --host 0.0.0.0 --port "${PORT:-8000}"
