#!/usr/bin/env bash
# scripts/init.sh - recursos compartidos de Winnie (idempotente: se puede repetir).
#   - red externa "honeynet" (172.30.0.0/24; .10 y .11 son de Cowrie y OpenCanary), sin tráfico
#     entre contenedores y sin IPv6
#   - un volumen de logs por fuente (SOURCE_VOLUMES en lib/contract.sh), propiedad del UID que
#     escribe y legible solo por el grupo del colector (modo 2750)
# Repetirlo reaplica esos mismos propietarios y modos: nunca abre permisos.
# Si encuentra la disposición anterior a W04 (red sin aislar), para y remite a migrate_honeylogs.sh.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=lib/contract.sh
. "$ROOT/scripts/lib/contract.sh"

NET="$SHARED_NET"
SUBNET="$SHARED_SUBNET"
IP_RANGE="172.30.0.128/25"      # auto-asignación lejos de las IPs fijas (.10/.11)
ICC_OPT="com.docker.network.bridge.enable_icc"
BUSYBOX="${BUSYBOX_IMAGE:-busybox:1.36.1}"

die() { echo "ERROR: $*" >&2; exit 1; }

command -v docker >/dev/null 2>&1 || die "docker no está instalado"
docker info >/dev/null 2>&1 || die "no puedo hablar con el daemon de Docker (¿está arrancado? ¿tu usuario está en el grupo docker?)"
docker compose version >/dev/null 2>&1 || die "falta Docker Compose v2 (comando 'docker compose')"

if docker network inspect "$NET" >/dev/null 2>&1; then
  current="$(docker network inspect -f '{{range .IPAM.Config}}{{.Subnet}} {{end}}' "$NET")"
  case "$current" in
    *"$SUBNET"*) ;;
    *) die "la red $NET existe con otra subred ($current). Bórrala (docker network rm $NET) o ajusta las IPs fijas del compose.";;
  esac
  isolation="$(docker network inspect -f "{{index .Options \"$ICC_OPT\"}} {{.EnableIPv6}}" "$NET")"
  [ "$isolation" = "false false" ] || die "la red $NET permite tráfico entre contenedores o IPv6 ($ICC_OPT/IPv6 = $isolation). Es la disposición anterior a W04: para los módulos y ejecuta scripts/migrate_honeylogs.sh"
  echo "[init] red $NET ya existe ($SUBNET, aislada)"
else
  docker network create --label "$PROJECT_LABEL" --driver bridge --subnet "$SUBNET" --ip-range "$IP_RANGE" \
    -o "$ICC_OPT=false" "$NET" >/dev/null
  echo "[init] red $NET creada ($SUBNET, sin tráfico entre contenedores ni IPv6)"
fi

mounts=(); fix=""
for spec in $SOURCE_VOLUMES; do
  IFS=: read -r src vol uid _ <<<"$spec"
  if docker volume inspect "$vol" >/dev/null 2>&1; then
    echo "[init] volumen $vol ya existe"
  else
    docker volume create --label "$PROJECT_LABEL" --label "io.winnie.source=$src" "$vol" >/dev/null
    echo "[init] volumen $vol creado"
  fi
  mounts+=(-v "$vol:/v/$src")
  fix="$fix chown $uid:$READER_GID /v/$src && chmod 2750 /v/$src &&"
done
docker run --rm --network none "${mounts[@]}" "$BUSYBOX" sh -c "${fix} true"
echo "[init] volúmenes de logs listos: propietario = productor, grupo $READER_GID (colector) en solo lectura, modo 2750"
