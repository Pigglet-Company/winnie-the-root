#!/usr/bin/env bash
# scripts/init.sh - recursos compartidos de Winnie (idempotente: se puede repetir).
#   - red externa "honeynet" (172.30.0.0/24; las IPs fijas .10 y .11 son de Cowrie y OpenCanary)
#   - volumen externo "honeylogs" con /logs/{cowrie,opencanary,web}
# Los permisos 0777 son SOLO para pruebas: cada productor corre con un UID distinto.
# Antes de recibir tráfico real, ajusta propietarios (ver docs/RUN.md).
set -euo pipefail

NET="honeynet"
SUBNET="172.30.0.0/24"
IP_RANGE="172.30.0.128/25"      # auto-asignación lejos de las IPs fijas (.10/.11)
VOL="honeylogs"
BUSYBOX="${BUSYBOX_IMAGE:-busybox:1.36.1}"

die() { echo "ERROR: $*" >&2; exit 1; }

command -v docker >/dev/null 2>&1 || die "docker no está instalado"
docker info >/dev/null 2>&1 || die "no puedo hablar con el daemon de Docker (¿está arrancado? ¿tu usuario está en el grupo docker?)"
docker compose version >/dev/null 2>&1 || die "falta Docker Compose v2 (comando 'docker compose')"

if docker network inspect "$NET" >/dev/null 2>&1; then
  current="$(docker network inspect -f '{{range .IPAM.Config}}{{.Subnet}} {{end}}' "$NET")"
  case "$current" in
    *"$SUBNET"*) echo "[init] red $NET ya existe ($SUBNET)";;
    *) die "la red $NET existe con otra subred ($current). Bórrala (docker network rm $NET) o ajusta las IPs fijas del compose.";;
  esac
else
  docker network create --driver bridge --subnet "$SUBNET" --ip-range "$IP_RANGE" "$NET" >/dev/null
  echo "[init] red $NET creada ($SUBNET)"
fi

if docker volume inspect "$VOL" >/dev/null 2>&1; then
  echo "[init] volumen $VOL ya existe"
else
  docker volume create "$VOL" >/dev/null
  echo "[init] volumen $VOL creado"
fi

docker run --rm -v "$VOL":/logs "$BUSYBOX" sh -c \
  'mkdir -p /logs/cowrie /logs/opencanary /logs/web && chmod 0777 /logs /logs/cowrie /logs/opencanary /logs/web'
echo "[init] directorios /logs/{cowrie,opencanary,web} listos"
