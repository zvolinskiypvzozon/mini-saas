#!/usr/bin/env bash
# Дамп БД в S3: backups/<db>/<db>-YYYYmmdd-HHMMSS.dump, удаление дампов старше BACKUP_KEEP_DAYS.
set -euo pipefail
source /usr/local/bin/common.sh

name="${POSTGRES_DB}-$(date -u +%Y%m%d-%H%M%S).dump"
file="/tmp/${name}"
trap 'rm -f "$file"' EXIT

pg_dump --format=custom --dbname="$POSTGRES_DB" --file="$file"
pg_restore --list "$file" > /dev/null

mc mb --ignore-existing "s3/${BACKUP_BUCKET}" > /dev/null
mc cp --quiet "$file" "${BACKUP_PREFIX}/${name}" > /dev/null
mc rm --recursive --force --older-than "${BACKUP_KEEP_DAYS}d" "${BACKUP_PREFIX}/" > /dev/null 2>&1 || true

echo "$(date -u +%FT%TZ) backup ok: ${BACKUP_BUCKET}/${POSTGRES_DB}/${name} ($(du -h "$file" | cut -f1))"
