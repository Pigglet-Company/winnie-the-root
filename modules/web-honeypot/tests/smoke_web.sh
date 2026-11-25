#!/usr/bin/env bash
# Smoke test del honeypot web (módulo B). Requiere: curl, jq y (docker o LOG_FILE).
#   BASE_URL   (def. http://localhost:8080)
#   CONTAINER  (def. hp-web)      -> lee /logs/web/web.jsonl con "docker exec"
#   LOG_FILE   (opcional)         -> lee un fichero local en vez de usar docker
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8080}"
CONTAINER="${CONTAINER:-hp-web}"
LOG_FILE="${LOG_FILE:-}"
RUN_ID="smoke-$(date +%s)-$RANDOM"
UA="SmokeTest/${RUN_ID}"
TMP="$(mktemp)"; trap 'rm -f "$TMP"' EXIT

pass() { echo "  [ok]   $*"; }
fail() { echo "  [FAIL] $*" >&2; exit 1; }
for bin in curl jq; do command -v "$bin" >/dev/null || fail "falta '$bin'"; done
[[ -n "$LOG_FILE" ]] || command -v docker >/dev/null || fail "falta docker (o define LOG_FILE)"

read_log() {
  if [[ -n "$LOG_FILE" ]]; then cat "$LOG_FILE"; else docker exec "$CONTAINER" cat /logs/web/web.jsonl; fi
}

# wait_event "descripción" 'filtro jq' -> espera (máx. 10 s) un evento de ESTA ejecución que cumpla el filtro
wait_event() {
  local desc="$1" filter="$2" out="" i
  for i in $(seq 1 20); do
    out="$(read_log | jq -c --arg ua "$UA" "select(.http.user_agent == \$ua) | select($filter)" 2>/dev/null | head -n1 || true)"
    if [[ -n "$out" ]]; then pass "$desc"; return 0; fi
    sleep 0.5
  done
  fail "$desc (no apareció el evento esperado en web.jsonl)"
}

req() { curl -sS -A "$UA" "$@"; }

echo "== Smoke test contra $BASE_URL (run $RUN_ID)"

echo "1) Petición normal"
code="$(req -o /dev/null -w '%{http_code}' "$BASE_URL/")"; [[ "$code" == "200" ]] || fail "GET / devolvió $code"
wait_event "GET / registrado" '.event_type == "request" and .http.path == "/" and .http.status == 200 and .honeypot == "web"'

echo "2) Login falso"
req -o /dev/null -d "username=smoke_user&password=smoke_pass_${RUN_ID}" "$BASE_URL/login"
wait_event "auth_attempt registrado" '.event_type == "auth_attempt" and .auth.username == "smoke_user" and .auth.success == false'

echo "3) SQL injection"
out="$(req -G --data-urlencode "q=' OR 1=1-- -" "$BASE_URL/search")"
grep -q "password_hash" <<<"$out" || fail "la respuesta no trae la tabla falsa de usuarios"
wait_event "payload SQLi registrado" '.http.path == "/search" and (.http.query | contains("OR 1=1"))'

echo "4) LFI"
out="$(req -G --data-urlencode "file=../../../../etc/passwd" "$BASE_URL/view")"
grep -q "root:x:0:0" <<<"$out" || fail "la respuesta no trae el /etc/passwd FALSO"
wait_event "payload LFI registrado" '.http.path == "/view" and (.http.query | contains("etc/passwd"))'

echo "5) Command injection"
out="$(req -G --data-urlencode "host=127.0.0.1;id" "$BASE_URL/ping")"
grep -q "uid=33(www-data)" <<<"$out" || fail "la respuesta no trae la salida FALSA de id"
wait_event "payload command injection registrado" '.http.path == "/ping" and (.http.query | contains(";id"))'

echo "6) Subida de fichero"
printf '<?php echo "smoke_%s"; ?>' "$RUN_ID" > "$TMP"
SHA="$(sha256sum "$TMP" | cut -d' ' -f1)"; SIZE="$(wc -c < "$TMP" | tr -d ' ')"
out="$(req -F "file=@${TMP};filename=shell.php" "$BASE_URL/upload")"
grep -q "/uploads/" <<<"$out" || fail "la respuesta no trae la URL falsa"
wait_event "file_upload registrado con sha256/size correctos" \
  ".event_type == \"file_upload\" and .file.name == \"shell.php\" and .file.sha256 == \"$SHA\" and .file.size == $SIZE"

echo "7) Validación de esquema de TODAS las líneas de web.jsonl"
SCHEMA='
  (.["@timestamp"] | type == "string" and test("^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\\.[0-9]{3}Z$"))
  and (.event_id | type == "string" and test("^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"))
  and .honeypot == "web" and .service == "http"
  and (.event_type == "request" or .event_type == "auth_attempt" or .event_type == "file_upload")
  and (.src_ip | type == "string") and (.dst_port | type == "number")
  and (.http.method | type == "string") and (.http.path | type == "string")
  and (.http.headers | type == "object") and (.http.status | type == "number")
  and (if .event_type == "auth_attempt" then (.auth.success | type == "boolean") else true end)
  and (if .event_type == "file_upload" then (.file.name | type == "string") else true end)
  and (has("attack_type") | not) and (has("mitre_technique") | not)'
LOG_COPY="$(mktemp)"; read_log > "$LOG_COPY"
jq -e . "$LOG_COPY" >/dev/null || { rm -f "$LOG_COPY"; fail "hay líneas que no son JSON válido"; }
total="$(wc -l < "$LOG_COPY" | tr -d ' ')"
bad="$(jq -c "select(($SCHEMA) | not)" "$LOG_COPY" | wc -l | tr -d ' ')"
rm -f "$LOG_COPY"
[[ "$bad" == "0" ]] || fail "$bad de $total líneas no cumplen el esquema"
pass "$total líneas válidas"

echo
echo "OK"
