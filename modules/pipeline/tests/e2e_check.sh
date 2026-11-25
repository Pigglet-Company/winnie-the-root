#!/usr/bin/env bash
# Verificación extremo a extremo (tras arrancar con datos sintéticos):
#   1) llegan ~todos los eventos esperados   2) attack_type siempre relleno
#   3) sin campos obligatorios vacíos        4) MITRE coherente con attack_type
#   5) event_id con formato UUID             6) variedad de ataques/honeypots
#   7) cola de errores con las líneas corruptas   8) alias e index template
# Uso: tests/e2e_check.sh        (requiere sample-logs/manifest.json)
set -uo pipefail
cd "$(dirname "$0")/.."

getenv() { [ -f .env ] && grep -E "^$1=" .env | tail -1 | cut -d= -f2- || true; }
MODE="$(getenv SECURITY_MODE)"; MODE="${MODE:-dev}"
PASS="$(getenv OPENSEARCH_ADMIN_PASSWORD)"
PROTO=http; AUTH=()
if [ "$MODE" = "prod" ]; then PROTO=https; AUTH=(-u "admin:${PASS}"); fi

# OpenSearch no está publicado en el host: se consulta dentro del contenedor.
os() { # os METODO RUTA 'json'
  printf '%s' "${3:-{\}}" | docker exec -i pl-opensearch curl -sk "${AUTH[@]+"${AUTH[@]}"}" \
    -H 'Content-Type: application/json' -X "$1" "${PROTO}://localhost:9200$2" --data-binary @-
}
num() { grep -o '"count":[0-9]*' | head -1 | cut -d: -f2; }

FAILS=0
ok()   { echo "  [OK]   $*"; }
fail() { echo "  [FAIL] $*"; FAILS=$((FAILS + 1)); }

[ -f sample-logs/manifest.json ] || { echo "Falta sample-logs/manifest.json: ejecuta tools/generate_sample_data.py"; exit 2; }
EXPECTED=$(grep -o '"expected_indexed": *[0-9]*' sample-logs/manifest.json | grep -o '[0-9]*$')
CORRUPT=$(grep -o '"corrupt_lines": *[0-9]*' sample-logs/manifest.json | grep -o '[0-9]*$')
MIN=$(( EXPECTED * 99 / 100 ))

echo "== e2e honeypot pipeline (modo ${MODE}; esperados ${EXPECTED} eventos) =="

echo "1) Documentos indexados (espera hasta 3 min)"
TOTAL=0
for _ in $(seq 1 36); do
  os POST /honeypot-events/_refresh >/dev/null 2>&1
  TOTAL=$(os POST /honeypot-events/_count | num); TOTAL=${TOTAL:-0}
  [ "$TOTAL" -ge "$MIN" ] && break
  sleep 5
done
if [ "$TOTAL" -ge "$MIN" ]; then ok "documentos=${TOTAL} (>= ${MIN})"; else fail "documentos=${TOTAL}, se esperaban >= ${MIN}"; fi

echo "2) attack_type relleno"
N=$(os POST /honeypot-events/_count '{"query":{"bool":{"must_not":[{"exists":{"field":"attack_type"}}]}}}' | num)
[ "${N:-x}" = "0" ] && ok "0 eventos sin attack_type" || fail "${N:-?} eventos sin attack_type"

echo "3) Campos obligatorios no vacíos"
for f in '@timestamp' event_id honeypot service event_type src_ip; do
  N=$(os POST /honeypot-events/_count "{\"query\":{\"bool\":{\"must_not\":[{\"exists\":{\"field\":\"$f\"}}]}}}" | num)
  [ "${N:-x}" = "0" ] && ok "$f presente en todos" || fail "$f ausente en ${N:-?} eventos"
done

echo "4) MITRE coherente"
N=$(os POST /honeypot-events/_count '{"query":{"bool":{"must_not":[{"terms":{"attack_type":["other","redis_command"]}},{"exists":{"field":"mitre_technique"}}]}}}' | num)
[ "${N:-x}" = "0" ] && ok "todo attack_type con técnica (salvo other y redis_command) tiene mitre_technique" || fail "${N:-?} eventos sin técnica MITRE"
N=$(os POST /honeypot-events/_count '{"query":{"bool":{"must":[{"term":{"attack_type":"redis_command"}},{"exists":{"field":"mitre_technique"}}]}}}' | num)
[ "${N:-x}" = "0" ] && ok "redis_command sin técnica MITRE" || fail "${N:-?} redis_command con técnica MITRE"

N=$(os POST /honeypot-events/_count '{"query":{"bool":{"must_not":[{"exists":{"field":"rule.version"}}]}}}' | num)
[ "${N:-x}" = "0" ] && ok "todos llevan rule.version" || fail "${N:-?} eventos sin rule.version"

echo "5) event_id con formato UUID"
N=$(os POST /honeypot-events/_count '{"query":{"regexp":{"event_id":"[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}"}}}' | num)
[ "${N:-0}" = "$TOTAL" ] && ok "${N} event_id válidos" || fail "event_id válidos ${N:-0} de ${TOTAL}"

echo "6) Variedad de datos"
TYPES=$(os POST /honeypot-events/_search '{"size":0,"aggs":{"t":{"terms":{"field":"attack_type","size":30}}}}' | grep -o '"key":"[a-z_]*"' | wc -l)
HPS=$(os POST /honeypot-events/_search '{"size":0,"aggs":{"t":{"terms":{"field":"honeypot","size":10}}}}' | grep -o '"key":"[a-z]*"' | wc -l)
[ "$TYPES" -ge 6 ] && ok "${TYPES} attack_type distintos" || fail "solo ${TYPES} attack_type distintos"
[ "$HPS" -ge 3 ] && ok "${HPS} honeypots distintos" || fail "solo ${HPS} honeypots"
G=$(os POST /honeypot-events/_count '{"query":{"exists":{"field":"geo.location"}}}' | num)
if [ "${G:-0}" -gt 0 ]; then ok "GeoIP activo (${G} eventos con geo.location)"; else echo "  [INFO] sin GeoIP (esperado si no hay MAXMIND_LICENSE_KEY)"; fi

echo "7) Cola de errores (líneas corruptas: ${CORRUPT})"
DL=$(docker exec pl-vector sh -c 'cat /var/lib/vector/dead_letter/*.jsonl 2>/dev/null | wc -l' 2>/dev/null | tr -d ' ')
if [ "${DL:-0}" -ge "$CORRUPT" ]; then ok "cola de errores=${DL}"; else fail "cola de errores=${DL:-?}, se esperaban >= ${CORRUPT}"; fi

echo "8) Alias e index template"
os GET /_alias/honeypot-events | grep -q 'honeypot-events-' && ok "alias honeypot-events -> índices diarios" || fail "alias honeypot-events ausente"
os GET /_index_template/honeypot-events | grep -q '"geo_point"' && ok "index template con geo_point" || fail "index template ausente"

echo
if [ "$FAILS" -eq 0 ]; then echo "RESULTADO: TODO OK"; exit 0; else echo "RESULTADO: ${FAILS} comprobaciones fallidas"; exit 1; fi
