#!/usr/bin/env bash
# scripts/egress-firewall.sh
# Bloquea el tráfico SALIENTE de la honeynet (172.30.0.0/24) en la cadena DOCKER-USER,
# salvo respuestas a conexiones entrantes: ni pares de la honeynet, ni host, ni redes privadas,
# ni metadatos cloud, ni Internet. Solo IPv4: la honeynet no tiene IPv6 (docs/lab-containment.md).
# Aplícalo ANTES de arrancar los señuelos: si DOCKER-USER aún no existe la crea, y Docker la respeta.
# Instalación a prueba de fallos: primero pone un "guard" que corta toda conexión nueva desde la
# subred y lo quita solo al terminar; si algo falla a medias, la salida queda cerrada, no abierta.
# Solo Linux con iptables. Requiere root.
#
# Uso:
#   sudo ./egress-firewall.sh                    # bloqueo total de salida (por defecto)
#   sudo ./egress-firewall.sh --allow-downloads  # permite salida SOLO a TCP 80/443 (+DNS), con límite de ritmo
#   sudo ./egress-firewall.sh --status
#   sudo ./egress-firewall.sh --remove   # también tras un fallo a medias
set -euo pipefail

SUBNET="${HONEYNET_SUBNET:-172.30.0.0/24}"
EGRESS_CHAIN="HONEYNET_EGRESS"
INPUT_CHAIN="HONEYNET_INPUT"
ALLOW_DOWNLOADS=0
ACTION="apply"
IPT="${IPTABLES:-iptables}"     # sustituible en pruebas (tests/check_isolation_docker.sh)
GUARD="winnie-egress-guard"

log() { printf '[egress-fw] %s\n' "$*"; }
die() { printf '[egress-fw] ERROR: %s\n' "$*" >&2; exit 1; }

usage() {
  sed -n '2,16p' "$0" | sed 's/^# \{0,1\}//'
}

while (( $# )); do
  case "$1" in
    --allow-downloads) ALLOW_DOWNLOADS=1 ;;
    --remove)          ACTION="remove" ;;
    --status)          ACTION="status" ;;
    -h|--help)         usage; exit 0 ;;
    *)                 die "opción desconocida: $1" ;;
  esac
  shift
done

[[ $EUID -eq 0 ]] || die "ejecuta como root (sudo)"
command -v "$IPT" >/dev/null 2>&1 || die "$IPT no encontrado"

# Paso de instalación: si falla, el guard sigue puesto (salida cerrada) y se sale con error.
ipt() { "$IPT" "$@" || die "falló: iptables $* -- el guard mantiene cerrada la salida; corrige y repite, o usa --remove"; }

guard_rules() {   # $1=-I|-D: las dos reglas que cortan conexiones nuevas desde la subred
  "$IPT" "$1" DOCKER-USER -s "$SUBNET" -m conntrack ! --ctstate ESTABLISHED,RELATED \
    -m comment --comment "$GUARD" -j DROP 2>/dev/null &&
  "$IPT" "$1" INPUT -s "$SUBNET" -m conntrack ! --ctstate ESTABLISHED,RELATED \
    -m comment --comment "$GUARD" -j DROP 2>/dev/null
}

remove_chains() {
  while "$IPT" -D DOCKER-USER -s "$SUBNET" -j "$EGRESS_CHAIN" 2>/dev/null; do :; done
  while "$IPT" -D INPUT -s "$SUBNET" -j "$INPUT_CHAIN" 2>/dev/null; do :; done
  local c
  for c in "$EGRESS_CHAIN" "$INPUT_CHAIN"; do
    if "$IPT" -n -L "$c" >/dev/null 2>&1; then
      "$IPT" -F "$c"
      "$IPT" -X "$c"
    fi
  done
}

remove_rules() {
  remove_chains
  while "$IPT" -D DOCKER-USER -s "$SUBNET" -m conntrack ! --ctstate ESTABLISHED,RELATED \
    -m comment --comment "$GUARD" -j DROP 2>/dev/null; do :; done
  while "$IPT" -D INPUT -s "$SUBNET" -m conntrack ! --ctstate ESTABLISHED,RELATED \
    -m comment --comment "$GUARD" -j DROP 2>/dev/null; do :; done
}

apply_rules() {
  # Antes de Docker: la cadena se crea vacía y Docker la conserva al arrancar.
  "$IPT" -n -L DOCKER-USER >/dev/null 2>&1 || ipt -N DOCKER-USER

  guard_rules -I || die "no pude poner el guard completo; repite o usa --remove"
  remove_chains   # idempotente: se recrea desde cero, con el guard puesto

  # ---- Tráfico que SALE de la honeynet (FORWARD) ----
  ipt -N "$EGRESS_CHAIN"
  # 1) Respuestas a conexiones entrantes (lo que hace funcionar a los señuelos)
  ipt -A "$EGRESS_CHAIN" -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
  # 2) Nunca hacia pares de la honeynet, redes privadas, loopback, CGNAT ni metadatos cloud
  local net
  for net in "$SUBNET" 10.0.0.0/8 172.16.0.0/12 192.168.0.0/16 169.254.0.0/16 100.64.0.0/10 127.0.0.0/8; do
    ipt -A "$EGRESS_CHAIN" -d "$net" -j DROP
  done
  # 3) Modo controlado: solo web (+DNS), con límite de ritmo
  if (( ALLOW_DOWNLOADS )); then
    log "MODO --allow-downloads: se permite salida a TCP 80/443 y DNS (limitada)"
    ipt -A "$EGRESS_CHAIN" -p tcp -m multiport --dports 80,443 \
      -m conntrack --ctstate NEW -m limit --limit 30/min --limit-burst 30 -j ACCEPT
    ipt -A "$EGRESS_CHAIN" -p udp --dport 53 \
      -m conntrack --ctstate NEW -m limit --limit 60/min --limit-burst 60 -j ACCEPT
    ipt -A "$EGRESS_CHAIN" -p tcp --dport 53 \
      -m conntrack --ctstate NEW -m limit --limit 60/min --limit-burst 60 -j ACCEPT
  fi
  # 4) Todo lo demás: registrar (limitado) y descartar
  ipt -A "$EGRESS_CHAIN" -m limit --limit 6/min \
    -j LOG --log-prefix "HONEYNET-EGRESS-DROP: " --log-level 4
  ipt -A "$EGRESS_CHAIN" -j DROP
  ipt -I DOCKER-USER 1 -s "$SUBNET" -j "$EGRESS_CHAIN"

  # ---- Conexiones NUEVAS desde la honeynet hacia el propio host (INPUT) ----
  ipt -N "$INPUT_CHAIN"
  ipt -A "$INPUT_CHAIN" -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
  ipt -A "$INPUT_CHAIN" -j DROP
  ipt -I INPUT 1 -s "$SUBNET" -j "$INPUT_CHAIN"

  guard_rules -D || die "las reglas están puestas pero no pude quitar el guard"
  while guard_rules -D; do :; done   # restos de un intento anterior fallido
  log "reglas aplicadas para $SUBNET"
}

case "$ACTION" in
  apply)  apply_rules ;;
  remove) remove_rules; log "reglas eliminadas" ;;
  status)
    "$IPT" -n -v -L "$EGRESS_CHAIN" 2>/dev/null || echo "($EGRESS_CHAIN no aplicada)"
    "$IPT" -n -v -L "$INPUT_CHAIN" 2>/dev/null || true
    echo "--- DOCKER-USER ---"
    "$IPT" -n -v -L DOCKER-USER
    ;;
esac
