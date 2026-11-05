#!/usr/bin/env bash
# Релиз = git-тег vX.Y.Z + образы mini-saas-{api,web,backup}:vX.Y.Z, собранные из этого тега.
#   ./scripts/release.sh v1.2.0           тег на текущий main (рабочая копия должна быть чистой)
#   ./scripts/release.sh v1.0.0 0450581   тег на указанный коммит
#   ./scripts/release.sh v1.1.0           тег уже есть — только пересобрать образы
set -euo pipefail
cd "$(dirname "$0")/.."

version="${1:?usage: release.sh vX.Y.Z [commit]}"
if [[ ! "$version" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  echo "version must look like v1.2.3" >&2
  exit 2
fi

if ! git rev-parse -q --verify "refs/tags/${version}" > /dev/null; then
  commit="${2:-}"
  if [ -z "$commit" ]; then
    if [ "$(git rev-parse --abbrev-ref HEAD)" != "main" ]; then
      echo "releases are made from main" >&2
      exit 1
    fi
    if ! git diff --quiet || ! git diff --cached --quiet; then
      echo "working tree is not clean" >&2
      exit 1
    fi
    latest="$(git tag --list 'v*' --sort=-v:refname | head -1)"
    if [ -n "$latest" ] && [ "$(printf '%s\n%s\n' "$latest" "$version" | sort -V | tail -1)" != "$version" ]; then
      echo "${version} must be greater than the latest release ${latest}" >&2
      exit 1
    fi
    commit=HEAD
  fi
  released="$(git tag --points-at "$commit" --list 'v*' | tr '\n' ' ')"
  if [ -n "$released" ]; then
    echo "commit $(git rev-parse --short "$commit") is already released as ${released}— merge new changes into main first" >&2
    exit 1
  fi
  git tag -a "$version" -m "Release ${version}" "$commit"
  echo "tagged ${version} -> $(git rev-parse --short "${version}^{commit}")"
fi

# собираем ровно то, что лежит в теге, а не текущую рабочую копию
src="$(mktemp -d)"
trap 'rm -rf "$src"' EXIT
git archive "$version" | tar -x -C "$src"

build() {
  local service="$1" dir="$2"
  if [ -d "${src}/${dir}" ]; then
    docker build --quiet --tag "mini-saas-${service}:${version}" "${src}/${dir}" > /dev/null
    echo "built mini-saas-${service}:${version}"
  else
    echo "skip ${service}: no ${dir}/ in ${version}"
  fi
}

build api api
build web frontend
build backup backup
