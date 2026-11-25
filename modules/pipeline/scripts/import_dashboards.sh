#!/usr/bin/env bash
# Espera a OpenSearch Dashboards, crea el index pattern honeypot-events* (campo
# temporal @timestamp) e importa dashboards/honeypot.ndjson con overwrite.
# Uso:  ./scripts/import_dashboards.sh            (DASH_URL=http://127.0.0.1:5601 por defecto)
set -euo pipefail
cd "$(dirname "$0")/.."

getenv() { [ -f .env ] && grep -E "^$1=" .env | tail -1 | cut -d= -f2- || true; }
MODE="$(getenv SECURITY_MODE)"; MODE="${MODE:-dev}"
PASS="$(getenv OPENSEARCH_ADMIN_PASSWORD)"
URL="${DASH_URL:-http://127.0.0.1:5601}"
AUTH=()
[ "$MODE" = "prod" ] && AUTH=(-u "admin:${PASS}")
curl_d() { curl -s "${AUTH[@]+"${AUTH[@]}"}" -H 'osd-xsrf: true' "$@"; }

echo "[import] Esperando a Dashboards en ${URL} (modo ${MODE}) ..."
for i in $(seq 1 90); do
  if curl_d "${URL}/api/status" 2>/dev/null | grep -q '"state":"green"'; then ready=1; break; fi
  sleep 5
done
[ "${ready:-0}" = "1" ] || { echo "[import] ERROR: Dashboards no está listo (revisa: docker logs pl-dashboards)"; exit 1; }

echo "[import] Index pattern honeypot-events*"
res=$(curl_d -X POST "${URL}/api/saved_objects/index-pattern/honeypot-events?overwrite=true" \
  -H 'Content-Type: application/json' \
  -d '{"attributes":{"title":"honeypot-events*","timeFieldName":"@timestamp"}}')
echo "$res" | grep -q '"type":"index-pattern"' || { echo "[import] ERROR index pattern: $res"; exit 1; }

curl_d -X POST "${URL}/api/opensearch-dashboards/settings" -H 'Content-Type: application/json' \
  -d '{"changes":{"defaultIndex":"honeypot-events"}}' >/dev/null || true

echo "[import] Importando dashboards/honeypot.ndjson (overwrite)"
res=$(curl_d -X POST "${URL}/api/saved_objects/_import?overwrite=true" --form file=@dashboards/honeypot.ndjson)
echo "$res" | grep -q '"success":true' || { echo "[import] ERROR importación: $res"; exit 1; }

echo "[import] OK -> ${URL}/app/dashboards#/view/hp-dashboard"
