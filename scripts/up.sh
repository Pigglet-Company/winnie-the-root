#!/usr/bin/env bash
# scripts/up.sh - arranque de Winnie.  Ejecutar desde cualquier sitio.
#   ./scripts/up.sh synthetic   Solo el pipeline con datos sintéticos (sin honeypots). Primera prueba.
#   ./scripts/up.sh full        Honeypots SSH + web + pipeline (todo el sistema).
#   ./scripts/up.sh --help
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MODE="${1:-}"

usage() { sed -n '2,6p' "$0"; exit "${1:-0}"; }
[ -n "$MODE" ] || usage 1
[ "$MODE" = "--help" ] && usage 0
case "$MODE" in synthetic|full) ;; *) usage 1;; esac

# Linux: OpenSearch necesita vm.max_map_count >= 262144
if [ "$(uname -s)" = "Linux" ] && [ -r /proc/sys/vm/max_map_count ]; then
  cur="$(cat /proc/sys/vm/max_map_count)"
  if [ "$cur" -lt 262144 ]; then
    echo "AVISO: vm.max_map_count=$cur (< 262144). OpenSearch no arrancará."
    echo "       Ejecuta:  sudo sysctl -w vm.max_map_count=262144"
    exit 1
  fi
fi

"$ROOT/scripts/init.sh"

# Primera ejecución: puertos de los señuelos solo en localhost (cambia a 0.0.0.0 bajo tu responsabilidad)
export HP_BIND_ADDR="${HP_BIND_ADDR:-127.0.0.1}"

if [ "$MODE" = "synthetic" ]; then
  cd "$ROOT/modules/pipeline"
  python3 tools/generate_sample_data.py
  docker compose -f compose.yml -f compose.dev.yml up -d
else
  (cd "$ROOT/modules/ssh-honeypot" && docker compose up -d --build)
  (cd "$ROOT/modules/web-honeypot" && docker compose up -d --build)
  cd "$ROOT/modules/pipeline"
  docker compose up -d
fi

./scripts/import_dashboards.sh

echo
echo "Listo. Dashboards:  http://localhost:5601/app/dashboards#/view/hp-dashboard  (rango: últimos 30 días)"
if [ "$MODE" = "synthetic" ]; then
  echo "Verificación extremo a extremo:  (cd modules/pipeline && ./tests/e2e_check.sh)"
else
  echo "SSH señuelo: ssh -p 2222 root@127.0.0.1 (pass: root)  ·  Web señuelo: http://localhost:8080"
fi
