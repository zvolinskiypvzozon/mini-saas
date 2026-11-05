#!/usr/bin/env bash
# Восстановление дампа в базу:  restore.sh <имя_дампа|latest> <база> [--force]
# Основную базу (POSTGRES_DB) перезаписывает только с --force.
set -euo pipefail
source /usr/local/bin/common.sh

if [ $# -lt 2 ]; then
  echo "usage: restore.sh <dump-name|latest> <target-db> [--force]" >&2
  exit 2
fi

name="$1"
target="$2"

if [ "$name" = "latest" ]; then
  name="$(latest_backup)"
  if [ -z "$name" ]; then
    echo "no backups in ${BACKUP_PREFIX}/" >&2
    exit 1
  fi
fi

if [ "$target" = "$POSTGRES_DB" ] && [ "${3:-}" != "--force" ]; then
  echo "refusing to overwrite main database '${POSTGRES_DB}' without --force" >&2
  exit 1
fi

file="/tmp/restore-${name}"
trap 'rm -f "$file"' EXIT

mc cp --quiet "${BACKUP_PREFIX}/${name}" "$file" > /dev/null
dropdb --if-exists --force --maintenance-db=postgres "$target"
createdb --maintenance-db=postgres "$target"
pg_restore --no-owner --exit-on-error --dbname="$target" "$file"

echo "restored ${name} into ${target}"
