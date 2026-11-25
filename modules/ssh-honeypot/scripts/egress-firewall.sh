#!/usr/bin/env bash
# scripts/egress-firewall.sh
# Bloquea el tráfico SALIENTE de la honeynet (172.30.0.0/24) en la cadena DOCKER-USER,
# salvo respuestas a conexiones entrantes. Solo Linux con iptables. Requiere root.
#
# Uso:
#   sudo ./egress-firewall.sh                    # bloqueo total de salida (por defecto)
#   sudo ./egress-firewall.sh --allow-downloads  # permite salida SOLO a TCP 80/443 (+DNS), con límite de ritmo
#   sudo ./egress-firewall.sh --status
#   sudo ./egress-firewall.sh --remove
set -euo pipefail

SUBNET="${HONEYNET_SUBNET:-172.30.0.0/24}"
EGRESS_CHAIN="HONEYNET_EGRESS"
INPUT_CHAIN="HONEYNET_INPUT"
ALLOW_DOWNLOADS=0
ACTION="apply"

log() { printf '[egress-fw] %s\n' "$*"; }
die() { printf '[egress-fw] ERROR: %s\n' "$*" >&2; exit 1; }

usage() {
  sed -n '2,11p' "$0" | sed 's/^# \{0,1\}//'
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
command -v iptables >/dev/null 2>&1 || die "iptables no encontrado"

remove_rules() {
  while iptables -D DOCKER-USER -s "$SUBNET" -j "$EGRESS_CHAIN" 2>/dev/null; do :; done
  while iptables -D INPUT -s "$SUBNET" -j "$INPUT_CHAIN" 2>/dev/null; do :; done
  local c
  for c in "$EGRESS_CHAIN" "$INPUT_CHAIN"; do
    if iptables -n -L "$c" >/dev/null 2>&1; then
      iptables -F "$c"
      iptables -X "$c"
    fi
  done
}

apply_rules() {
  iptables -n -L DOCKER-USER >/dev/null 2>&1 \
    || die "no existe la cadena DOCKER-USER (¿está Docker arrancado?)"

  remove_rules   # idempotente: se recrea desde cero

  # ---- Tráfico que SALE de la honeynet hacia fuera (FORWARD) ----
  iptables -N "$EGRESS_CHAIN"
  # 1) Respuestas a conexiones entrantes (lo que hace funcionar a los señuelos)
  iptables -A "$EGRESS_CHAIN" -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
  # 2) Tráfico interno de la propia honeynet
  iptables -A "$EGRESS_CHAIN" -d "$SUBNET" -j ACCEPT
  # 3) Nunca hacia redes privadas, loopback, CGNAT ni metadatos cloud (evita pivotar)
  local net
  for net in 10.0.0.0/8 172.16.0.0/12 192.168.0.0/16 169.254.0.0/16 100.64.0.0/10 127.0.0.0/8; do
    iptables -A "$EGRESS_CHAIN" -d "$net" -j DROP
  done
  # 4) Modo controlado: solo web (+DNS), con límite de ritmo
  if (( ALLOW_DOWNLOADS )); then
    log "MODO --allow-downloads: se permite salida a TCP 80/443 y DNS (limitada)"
    iptables -A "$EGRESS_CHAIN" -p tcp -m multiport --dports 80,443 \
      -m conntrack --ctstate NEW -m limit --limit 30/min --limit-burst 30 -j ACCEPT
    iptables -A "$EGRESS_CHAIN" -p udp --dport 53 \
      -m conntrack --ctstate NEW -m limit --limit 60/min --limit-burst 60 -j ACCEPT
    iptables -A "$EGRESS_CHAIN" -p tcp --dport 53 \
      -m conntrack --ctstate NEW -m limit --limit 60/min --limit-burst 60 -j ACCEPT
  fi
  # 5) Todo lo demás: registrar (limitado) y descartar
  iptables -A "$EGRESS_CHAIN" -m limit --limit 6/min \
    -j LOG --log-prefix "HONEYNET-EGRESS-DROP: " --log-level 4
  iptables -A "$EGRESS_CHAIN" -j DROP
  iptables -I DOCKER-USER 1 -s "$SUBNET" -j "$EGRESS_CHAIN"

  # ---- Conexiones NUEVAS desde la honeynet hacia el propio host (INPUT) ----
  iptables -N "$INPUT_CHAIN"
  iptables -A "$INPUT_CHAIN" -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
  iptables -A "$INPUT_CHAIN" -j DROP
  iptables -I INPUT 1 -s "$SUBNET" -j "$INPUT_CHAIN"

  log "reglas aplicadas para $SUBNET"
}

case "$ACTION" in
  apply)  apply_rules ;;
  remove) remove_rules; log "reglas eliminadas" ;;
  status)
    iptables -n -v -L "$EGRESS_CHAIN" 2>/dev/null || echo "($EGRESS_CHAIN no aplicada)"
    iptables -n -v -L "$INPUT_CHAIN" 2>/dev/null || true
    echo "--- DOCKER-USER ---"
    iptables -n -v -L DOCKER-USER
    ;;
esac
