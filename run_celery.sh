#!/bin/sh

celery --app=uploader_1 worker --loglevel=DEBUG --concurrency=2 -E --logfile=logs/celery.log

exec "$@"
