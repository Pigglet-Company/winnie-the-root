#!/bin/sh
# Inicializa OpenSearch (idempotente): plantilla de indice + alias + retencion ISM.
# Se ejecuta en el contenedor pl-setup ANTES de arrancar Vector, para que ningun
# indice diario se cree con mapping dinamico.
set -eu

OS_PROTO="${OS_PROTO:-http}"
BASE="${OS_PROTO}://pl-opensearch:9200"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
AUTH=""

case "$RETENTION_DAYS" in
  ''|*[!0-9]*) echo "[setup] ERROR: RETENTION_DAYS debe ser un entero (valor: '$RETENTION_DAYS')"; exit 1 ;;
esac

if [ "${SECURITY_MODE:-dev}" = "prod" ]; then
  [ -n "${OS_PASS:-}" ] || { echo "[setup] ERROR: OPENSEARCH_ADMIN_PASSWORD vacia en modo prod"; exit 1; }
  AUTH="admin:${OS_PASS}"
fi

call() { # call METODO RUTA [args de curl...]
  m="$1"; p="$2"; shift 2
  if [ -n "$AUTH" ]; then
    curl -sk -u "$AUTH" -H 'Content-Type: application/json' -X "$m" "${BASE}${p}" "$@"
  else
    curl -sk -H 'Content-Type: application/json' -X "$m" "${BASE}${p}" "$@"
  fi
}

echo "[setup] Esperando a OpenSearch en ${BASE} ..."
i=0
until call GET /_cluster/health 2>/dev/null | grep -Eq '"status":"(green|yellow)"'; do
  i=$((i + 1))
  [ "$i" -le 60 ] || { echo "[setup] ERROR: OpenSearch no responde"; exit 1; }
  sleep 5
done

echo "[setup] Index template honeypot-events (alias honeypot-events)"
res=$(call PUT /_index_template/honeypot-events --data-binary @/setup/index_template.json)
echo "$res" | grep -q '"acknowledged":true' || { echo "[setup] ERROR template: $res"; exit 1; }

echo "[setup] Politica de retencion ISM: ${RETENTION_DAYS} dias"
policy=$(sed "s/__RETENTION_DAYS__/${RETENTION_DAYS}/g" /setup/ism_policy.json)
existing=$(call GET /_plugins/_ism/policies/honeypot-retention 2>/dev/null || true)
if echo "$existing" | grep -q '"_seq_no"'; then
  seq=$(echo "$existing" | grep -o '"_seq_no":[0-9]*' | head -1 | cut -d: -f2)
  pt=$(echo "$existing" | grep -o '"_primary_term":[0-9]*' | head -1 | cut -d: -f2)
  res=$(echo "$policy" | call PUT "/_plugins/_ism/policies/honeypot-retention?if_seq_no=${seq}&if_primary_term=${pt}" --data-binary @-)
else
  res=$(echo "$policy" | call PUT /_plugins/_ism/policies/honeypot-retention --data-binary @-)
fi
echo "$res" | grep -q '"_id":"honeypot-retention"' || { echo "[setup] ERROR ISM: $res"; exit 1; }

# Indices que ya existian (p. ej. de una ejecucion previa) -> aplicarles la politica
call POST '/_plugins/_ism/add/honeypot-events-*' -d '{"policy_id":"honeypot-retention"}' >/dev/null 2>&1 || true

if [ "${SECURITY_MODE:-dev}" = "prod" ]; then
  # El "demo config" de OpenSearch crea usuarios de ejemplo con contrasenas publicas.
  for u in kibanaro logstash readall snapshotrestore; do
    call DELETE "/_plugins/_security/api/internalusers/$u" >/dev/null 2>&1 || true
  done
  echo "[setup] Usuarios de demo eliminados (cuando la API lo permite)"
fi

echo "[setup] OK"
