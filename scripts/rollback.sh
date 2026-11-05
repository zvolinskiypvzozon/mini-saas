#!/usr/bin/env bash
# Откат на 1 или 2 релиза назад от выкаченной версии:  ./scripts/rollback.sh [1|2]
# Порядок релизов — git-теги vX.Y.Z по номеру версии.
set -euo pipefail
cd "$(dirname "$0")/.."

steps="${1:-1}"
if [[ ! "$steps" =~ ^[12]$ ]]; then
  echo "usage: rollback.sh [1|2]" >&2
  exit 2
fi

current="$(cat .deploy/current 2>/dev/null || true)"
if [ -z "$current" ]; then
  echo "nothing deployed yet (.deploy/current is empty)" >&2
  exit 1
fi

mapfile -t releases < <(git tag --list 'v*' --sort=-v:refname)
for i in "${!releases[@]}"; do
  if [ "${releases[$i]}" = "$current" ]; then
    target="${releases[$((i + steps))]:-}"
    if [ -z "$target" ]; then
      echo "no release ${steps} step(s) before ${current}" >&2
      exit 1
    fi
    echo "rollback ${steps} step(s): ${current} -> ${target}"
    exec ./scripts/deploy.sh "$target"
  fi
done

echo "current version ${current} is not a release tag" >&2
exit 1
