#!/usr/bin/env bash
# scripts/preflight.sh - comprueba el host ANTES de arrancar. Solo lee: no crea, borra ni cambia nada.
#   ./scripts/preflight.sh synthetic   requisitos del perfil con datos sintéticos
#   ./scripts/preflight.sh full        requisitos del sistema completo
#   ./scripts/preflight.sh --help
# Sale con 0 si todo está listo y con 1 si algo impide arrancar (lo explica cada línea [FALLO]).
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=lib/contract.sh
. "$ROOT/scripts/lib/contract.sh"

usage() { sed -n '2,6p' "$0" | sed 's/^# \{0,1\}//'; exit "${1:-0}"; }
PROFILE="${1:-}"
[ "$PROFILE" = "--help" ] || [ "$PROFILE" = "-h" ] && usage 0
profile_modules "$PROFILE" >/dev/null 2>&1 || usage 1

FAILS=0
ok()   { echo "  [ok]    $*"; }
warn() { echo "  [aviso] $*"; }
fail() { echo "  [FALLO] $*"; FAILS=$((FAILS + 1)); }

echo "[preflight] perfil $PROFILE"

echo "Programas del host:"
for c in $REQUIRED_COMMANDS; do
  if command -v "$c" >/dev/null 2>&1; then ok "$c"; else fail "falta '$c' (instálalo y repite)"; fi
done
DOCKER_OK=0
if command -v docker >/dev/null 2>&1; then
  if ! docker compose version >/dev/null 2>&1; then
    fail "falta Docker Compose v2 (comando 'docker compose')"
  elif ! docker info >/dev/null 2>&1; then
    fail "no puedo hablar con el daemon de Docker (¿arrancado? ¿tu usuario está en el grupo docker?)"
  else
    ok "Docker Compose v2 y daemon accesibles"; DOCKER_OK=1
  fi
fi

echo "Sistema:"
if [ "$(uname -s)" = "Linux" ] && [ -r "$MAX_MAP_COUNT_FILE" ]; then
  cur="$(cat "$MAX_MAP_COUNT_FILE")"
  if [ "$cur" -ge "$MIN_MAX_MAP_COUNT" ]; then ok "vm.max_map_count=$cur"
  else fail "vm.max_map_count=$cur (< $MIN_MAX_MAP_COUNT; OpenSearch no arrancará). Ejecuta: sudo sysctl -w vm.max_map_count=$MIN_MAX_MAP_COUNT"; fi
fi
if [ "$DOCKER_OK" = 1 ] && docker network inspect "$SHARED_NET" >/dev/null 2>&1; then
  subnet="$(docker network inspect -f '{{range .IPAM.Config}}{{.Subnet}} {{end}}' "$SHARED_NET")"
  case "$subnet" in
    *"$SHARED_SUBNET"*) ok "red $SHARED_NET ya existe ($SHARED_SUBNET)" ;;
    *) fail "la red $SHARED_NET existe con otra subred ($subnet); se espera $SHARED_SUBNET" ;;
  esac
fi

echo "Configuración efectiva:"
mode="$(effective pipeline SECURITY_MODE dev)"
echo "  pipeline  SECURITY_MODE=$mode  OPENSEARCH_HEAP=$(effective pipeline OPENSEARCH_HEAP 1g)  RETENTION_DAYS=$(effective pipeline RETENTION_DAYS 30)"
if [ "$mode" = "prod" ] && [ -z "$(effective pipeline OPENSEARCH_ADMIN_PASSWORD '')" ]; then
  fail "SECURITY_MODE=prod exige OPENSEARCH_ADMIN_PASSWORD en modules/pipeline/.env"
fi
case "$mode" in dev|prod) ;; *) fail "SECURITY_MODE='$mode' no válido (dev|prod)" ;; esac
echo "  OpenSearch 9200: solo red interna de Docker (no se publica)"

echo "Puertos del host:"
own_port() {   # ¿lo publica ya un contenedor de este módulo?
  [ "$DOCKER_OK" = 1 ] || return 1
  local name
  for name in $(docker ps --filter "publish=$2" --format '{{.Names}}' 2>/dev/null); do
    case " $(module_containers "$1") " in *" $name "*) echo "$name"; return 0 ;; esac
  done
  return 1
}
port_free() {   # intenta enlazar y suelta al momento
  python3 - "$1" "$2" <<'EOF' 2>/dev/null
import socket, sys
s = socket.socket(socket.AF_INET6 if ":" in sys.argv[1] else socket.AF_INET)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
try:
    s.bind((sys.argv[1], int(sys.argv[2])))
except OSError:
    sys.exit(1)
finally:
    s.close()
EOF
}
while read -r module addr port service; do
  label="$service $addr:$port"
  if ! command -v python3 >/dev/null 2>&1; then
    warn "$label sin comprobar (falta python3)"
  elif port_free "$addr" "$port"; then
    ok "$label libre"
  elif holder="$(own_port "$module" "$port")"; then
    ok "$label ya publicado por $holder (este proyecto)"
  else
    fail "$label ocupado por otro proceso (libéralo o cambia el puerto en modules/$module/.env)"
  fi
  [ "$addr" = "127.0.0.1" ] || warn "$label escucha fuera de localhost: visible desde otros equipos"
done < <(published_ports "$PROFILE")

if [ "$FAILS" -gt 0 ]; then
  echo "[preflight] $FAILS problema(s). No se ha modificado nada."
  exit 1
fi
echo "[preflight] listo para arrancar el perfil $PROFILE"
