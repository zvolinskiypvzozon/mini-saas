#!/usr/bin/env bash
# Выкатить релиз:  ./scripts/deploy.sh v1.2.0
# 1) бэкап БД; 2) если новая версия старше схемы БД — откатить миграции кодом текущей версии;
# 3) перезапустить api, web, backup из образов версии; 4) дождаться /health; 5) записать текущую версию.
set -euo pipefail
cd "$(dirname "$0")/.."

version="${1:?usage: deploy.sh vX.Y.Z}"
state_dir=.deploy
current="$(cat "${state_dir}/current" 2>/dev/null || echo none)"

set -a
source .env
set +a

for service in api web backup; do
  if ! docker image inspect "mini-saas-${service}:${version}" > /dev/null 2>&1; then
    echo "no image mini-saas-${service}:${version} — run ./scripts/release.sh ${version}" >&2
    exit 1
  fi
done

echo "deploy: ${current} -> ${version}"

echo "1/4 backup"
docker compose exec -T backup backup.sh

echo "2/4 database schema"
db_rev="$(docker compose exec -T db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tAc \
  "SELECT version_num FROM alembic_version")"
target_head="$(docker run --rm "mini-saas-api:${version}" alembic heads | awk '{print $1}')"
if docker run --rm "mini-saas-api:${version}" alembic show "$db_rev" > /dev/null 2>&1; then
  echo "    db ${db_rev}, ${version} knows it — upgrade (if any) runs on api start"
else
  # старая версия не знает новых миграций: откатываем их, пока работает код, в котором они есть
  echo "    db ${db_rev} is newer than ${version} (head ${target_head}) — downgrading"
  docker compose exec -T api alembic downgrade "$target_head"
fi

echo "3/4 restart api, web, backup"
APP_VERSION="$version" docker compose up -d --no-build api web backup

echo "4/4 health check"
for _ in $(seq 1 30); do
  if curl -fs localhost:8080/health > /dev/null && curl -fs localhost:8080/ > /dev/null; then
    mkdir -p "$state_dir"
    echo "$version" > "${state_dir}/current"
    echo "$(date -u +%FT%TZ) ${current} -> ${version}" >> "${state_dir}/history"
    echo "deployed ${version}"
    exit 0
  fi
  sleep 2
done

echo "health check FAILED for ${version}. Roll back: ./scripts/rollback.sh 1" >&2
docker compose logs api --tail 20 >&2
exit 1
