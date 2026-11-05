#!/usr/bin/env bash
# Делает дамп при старте контейнера и дальше каждые BACKUP_INTERVAL_HOURS часов.
set -uo pipefail

interval_hours="${BACKUP_INTERVAL_HOURS:-24}"
echo "backup service: every ${interval_hours}h, keep ${BACKUP_KEEP_DAYS:-7} days"

while true; do
  backup.sh || echo "$(date -u +%FT%TZ) backup FAILED" >&2
  sleep "$((interval_hours * 3600))"
done
