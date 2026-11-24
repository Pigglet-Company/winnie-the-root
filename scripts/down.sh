#!/usr/bin/env bash
# scripts/down.sh - para todo. Conserva los datos. Con --purge borra también volúmenes, red y logs.
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PURGE=0; [ "${1:-}" = "--purge" ] && PURGE=1
V=(); [ "$PURGE" = 1 ] && V=(-v)

(cd "$ROOT/modules/pipeline"      && docker compose -f compose.yml -f compose.dev.yml down "${V[@]}" 2>/dev/null)
(cd "$ROOT/modules/web-honeypot"  && docker compose down "${V[@]}" 2>/dev/null)
(cd "$ROOT/modules/ssh-honeypot"  && docker compose down "${V[@]}" 2>/dev/null)

if [ "$PURGE" = 1 ]; then
  docker volume rm honeylogs 2>/dev/null || true
  docker network rm honeynet 2>/dev/null || true
  echo "Todo borrado (volúmenes, red y logs)."
else
  echo "Parado. Datos conservados (usa --purge para borrarlos)."
fi
