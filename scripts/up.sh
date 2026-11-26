#!/usr/bin/env bash
# scripts/up.sh - arranque de Winnie.  Ejecutar desde cualquier sitio.
#   ./scripts/up.sh synthetic   Solo el pipeline con datos sintéticos (sin honeypots). Primera prueba.
#   ./scripts/up.sh full        Honeypots SSH + web + pipeline (todo el sistema).
#   ./scripts/up.sh --help
# Antes de cambiar nada ejecuta scripts/preflight.sh; si falla, no toca el host.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=lib/contract.sh
. "$ROOT/scripts/lib/contract.sh"
MODE="${1:-}"

usage() { sed -n '2,6p' "$0" | sed 's/^# \{0,1\}//'; exit "${1:-0}"; }
[ -n "$MODE" ] || usage 1
[ "$MODE" = "--help" ] || [ "$MODE" = "-h" ] && usage 0
profile_modules "$MODE" >/dev/null 2>&1 || usage 1

bash "$ROOT/scripts/preflight.sh" "$MODE"
bash "$ROOT/scripts/init.sh"

# Los señuelos solo arrancan con la salida de la honeynet ya cerrada (docs/lab-containment.md).
# WINNIE_ALLOW_EGRESS=1 lo salta solo si todos los señuelos escuchan en 127.0.0.1.
if [ "$MODE" = "full" ] && ! bash "$ROOT/scripts/check_egress.sh"; then
  loopback=1
  while read -r _ addr _ _; do case "$addr" in 127.*) ;; *) loopback=0 ;; esac; done \
    < <(published_ports full | grep -v '^pipeline ')
  if [ "${WINNIE_ALLOW_EGRESS:-0}" = 1 ] && [ "$loopback" = 1 ]; then
    echo "[up] AVISO: WINNIE_ALLOW_EGRESS=1 con señuelos en 127.0.0.1: arranco SIN contención de salida." \
         "No uses este modo con participantes ni tráfico externo."
  else
    echo "[up] No arranco los señuelos sin contención de salida." >&2
    exit 1
  fi
fi

# Los puertos de los señuelos escuchan en 127.0.0.1 salvo que el .env del módulo diga otra cosa.
if [ "$MODE" = "synthetic" ]; then
  (cd "$ROOT/modules/pipeline" && python3 tools/generate_sample_data.py)
fi
for m in $(profile_modules "$MODE"); do
  build=(); [ "$m" = "pipeline" ] || build=(--build)
  # shellcheck disable=SC2046
  (cd "$ROOT/modules/$m" && docker compose $(compose_files "$MODE" "$m") up -d ${build[@]+"${build[@]}"})
done

bash "$ROOT/modules/pipeline/scripts/import_dashboards.sh"

echo
echo "Listo. Dashboards:  http://localhost:5601/app/dashboards#/view/hp-dashboard  (rango: últimos 30 días)"
if [ "$MODE" = "synthetic" ]; then
  echo "Verificación extremo a extremo:  bash modules/pipeline/tests/e2e_check.sh"
else
  echo "SSH señuelo: ssh -p 2222 root@127.0.0.1 (pass: root)  ·  Web señuelo: http://localhost:8080"
fi
