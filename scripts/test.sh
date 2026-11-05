#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

set -a
source .env
set +a

TEST_DB=appdb_test

if ! docker compose exec -T db psql -U "$POSTGRES_USER" -d postgres -tAc \
    "SELECT 1 FROM pg_database WHERE datname='$TEST_DB'" | grep -q 1; then
  docker compose exec -T db createdb -U "$POSTGRES_USER" "$TEST_DB"
  echo "Создана база $TEST_DB"
fi

docker compose run --rm --no-deps \
  -v "$PWD/api:/app" \
  -e DATABASE_URL="postgresql+psycopg://$POSTGRES_USER:$POSTGRES_PASSWORD@db:5432/$TEST_DB" \
  -e PYTHONDONTWRITEBYTECODE=1 \
  api sh -c "pip install -q --root-user-action=ignore -r requirements-dev.txt && pytest -v"
