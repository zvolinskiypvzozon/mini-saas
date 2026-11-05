#!/usr/bin/env bash
# Проверка, что последний дамп действительно восстанавливается:
# разворачиваем его во временную базу, сравниваем таблицы и версию миграций с основной базой, удаляем копию.
set -euo pipefail
source /usr/local/bin/common.sh

check_db="${POSTGRES_DB}_verify"
trap 'dropdb --if-exists --force --maintenance-db=postgres "$check_db"' EXIT

restore.sh latest "$check_db"

tables_sql="SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public' AND table_type = 'BASE TABLE' ORDER BY 1"

query() { psql --dbname="$1" --tuples-only --no-align --command="$2"; }

source_tables="$(query "$POSTGRES_DB" "$tables_sql")"
restored_tables="$(query "$check_db" "$tables_sql")"
if [ "$source_tables" != "$restored_tables" ]; then
  echo "FAIL: table list differs" >&2
  diff <(echo "$source_tables") <(echo "$restored_tables") >&2 || true
  exit 1
fi

source_rev="$(query "$POSTGRES_DB" "SELECT version_num FROM alembic_version")"
restored_rev="$(query "$check_db" "SELECT version_num FROM alembic_version")"
if [ "$source_rev" != "$restored_rev" ]; then
  echo "FAIL: alembic revision ${restored_rev} in backup, ${source_rev} in database" >&2
  exit 1
fi

printf '%-20s %10s %10s\n' table current backup
for table in $source_tables; do
  printf '%-20s %10s %10s\n' "$table" \
    "$(query "$POSTGRES_DB" "SELECT count(*) FROM \"$table\"")" \
    "$(query "$check_db" "SELECT count(*) FROM \"$table\"")"
done

echo "verify ok: backup restores, ${restored_rev} migration, $(echo "$source_tables" | wc -l) tables"
