#!/usr/bin/env bash
# deploy/redirect-ports.sh — Fase 2 (VPS)
# Redirige los puertos "reales" del VPS hacia los señuelos mediante DNAT a la IP fija
# del contenedor (preserva la IP de origen del atacante; ver NOTAS_CONTRATO.md).
#   22->Cowrie:2222 (solo si REDIRECT_SSH=1)   23->Cowrie:2223
#   21->OpenCanary:2121   3306->OpenCanary:3306   6379->OpenCanary:6379
# Uso: sudo ./redirect-ports.sh apply|remove|status
set -euo pipefail

COWRIE_IP="${COWRIE_IP:-172.30.0.10}"
CANARY_IP="${CANARY_IP:-172.30.0.11}"
REDIRECT_SSH="${REDIRECT_SSH:-0}"
CHAIN="HONEYNET_REDIRECT"

die() { printf '[redirect] ERROR: %s\n' "$*" >&2; exit 1; }
log() { printf '[redirect] %s\n' "$*"; }

[[ $EUID -eq 0 ]] || die "ejecuta como root"
command -v iptables >/dev/null 2>&1 || die "iptables no encontrado"

mappings() {   # puerto_host  ip_contenedor  puerto_contenedor
  if [[ "$REDIRECT_SSH" == "1" ]]; then
    echo "22 $COWRIE_IP 2222"
  fi
  echo "23 $COWRIE_IP 2223"
  echo "21 $CANARY_IP 2121"
  echo "3306 $CANARY_IP 3306"
  echo "6379 $CANARY_IP 6379"
}

remove_rules() {
  while iptables -t nat -D PREROUTING -m addrtype --dst-type LOCAL -j "$CHAIN" 2>/dev/null; do :; done
  if iptables -t nat -n -L "$CHAIN" >/dev/null 2>&1; then
    iptables -t nat -F "$CHAIN"
    iptables -t nat -X "$CHAIN"
  fi
}

apply_rules() {
  remove_rules
  iptables -t nat -N "$CHAIN"
  local hp ip cp
  while read -r hp ip cp; do
    iptables -t nat -A "$CHAIN" -p tcp --dport "$hp" -j DNAT --to-destination "${ip}:${cp}"
    log "tcp/${hp} -> ${ip}:${cp}"
  done < <(mappings)
  # Antes de la cadena DOCKER para que tenga prioridad
  iptables -t nat -I PREROUTING 1 -m addrtype --dst-type LOCAL -j "$CHAIN"
}

case "${1:-}" in
  apply)  apply_rules ;;
  remove) remove_rules; log "redirecciones eliminadas" ;;
  status) iptables -t nat -n -v -L "$CHAIN" 2>/dev/null || echo "(no aplicadas)" ;;
  *)      die "uso: $0 apply|remove|status" ;;
esac
