#!/usr/bin/env bash
# tests/check_public_entry_docker.sh - ensayo de la entrada pública con Docker real (lo usa CI).
#   1) docker compose config por cada modo: binds por defecto en 127.0.0.1 y 9200 sin publicar
#   2) un preflight fallido (puerto ocupado) no cambia el estado de Docker: se registra antes y después
#   3) init.sh dos veces seguidas: segunda ejecución sin errores y recursos etiquetados
# No arranca contenedores de larga duración. Deja creados honeynet y honeylogs-<fuente> (los borra --cleanup).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
# shellcheck source=../scripts/lib/contract.sh
. scripts/lib/contract.sh
unset HP_BIND_ADDR WEB_HOST_PORT SECURITY_MODE

published() {   # imprime host_ip:published de cada puerto publicado del modelo resuelto
  docker compose "$@" config --format json | python3 -c '
import json, sys
for name, svc in json.load(sys.stdin)["services"].items():
    for p in svc.get("ports", []):
        print(name, "%s:%s->%s" % (p.get("host_ip", "0.0.0.0"), p["published"], p["target"]))'
}

echo "== 1. Modelos Compose por modo"
check_model() {   # $1=descripción; resto=args de compose
  local what="$1"; shift
  local out; out="$(published "$@")"
  echo "-- $what"; echo "$out" | sed 's/^/   /'
  if echo "$out" | grep -v ' 127\.0\.0\.1:' | grep -q .; then echo "ERROR: $what publica fuera de 127.0.0.1"; exit 1; fi
  if echo "$out" | grep -q -- '->9200'; then echo "ERROR: $what publica 9200"; exit 1; fi
}
check_model "A ssh-honeypot"      -f modules/ssh-honeypot/compose.yml
check_model "B web-honeypot"      -f modules/web-honeypot/compose.yml
check_model "C pipeline full"     -f modules/pipeline/compose.yml
check_model "C pipeline synthetic" -f modules/pipeline/compose.yml -f modules/pipeline/compose.dev.yml
SECURITY_MODE=prod OPENSEARCH_ADMIN_PASSWORD=ci-only-not-a-secret \
  check_model "C pipeline prod"   -f modules/pipeline/compose.yml
HP_BIND_ADDR=0.0.0.0 published -f modules/web-honeypot/compose.yml | grep -q ' 0\.0\.0\.0:8080->8080' \
  || { echo "ERROR: HP_BIND_ADDR=0.0.0.0 no abre la web"; exit 1; }
echo "-- HP_BIND_ADDR=0.0.0.0 abre la web de forma explícita: ok"

echo "== 2. Preflight fallido no cambia nada"
state() { { docker network ls --format '{{.Name}}'; docker volume ls --format '{{.Name}}'; docker ps -a --format '{{.Names}}'; } | sort; }
python3 -m http.server 18080 --bind 127.0.0.1 >/dev/null 2>&1 &
holder=$!; trap 'kill $holder 2>/dev/null || true' EXIT
sleep 1
before="$(state)"
if out="$(WEB_HOST_PORT=18080 ./scripts/up.sh full 2>&1)"; then echo "ERROR: up.sh arrancó con el puerto ocupado"; exit 1; fi
echo "$out" | sed 's/^/   /'
echo "$out" | grep -q 'web 127.0.0.1:18080 ocupado' || { echo "ERROR: preflight no señaló el puerto ocupado"; exit 1; }
after="$(state)"
echo "-- estado antes:";   echo "$before" | sed 's/^/   /'
echo "-- estado después:"; echo "$after"  | sed 's/^/   /'
[ "$before" = "$after" ] || { echo "ERROR: el estado de Docker cambió"; diff <(echo "$before") <(echo "$after"); exit 1; }
kill "$holder"; trap - EXIT

echo "== 3. init.sh dos veces"
./scripts/init.sh
./scripts/init.sh
for kind in network:honeynet $(source_volume_names | sed 's/^/volume:/'); do
  docker "${kind%%:*}" inspect -f '{{json .Labels}}' "${kind#*:}" | grep -q '"io.winnie.project":"winnie-the-root"' \
    || { echo "ERROR: ${kind#*:} sin etiqueta del proyecto"; exit 1; }
done
echo "-- segunda ejecución sin errores y recursos etiquetados: ok"

if [ "${1:-}" = "--cleanup" ]; then ./scripts/down.sh full --purge; fi
echo "OK"
