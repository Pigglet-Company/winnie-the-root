#!/usr/bin/env bash
# scripts/check_egress.sh - comprueba desde dentro de honeynet que la salida nueva está cerrada.
#   ./scripts/check_egress.sh               sondas por defecto (Internet y metadatos cloud)
#   EGRESS_PROBES="ip:puerto ..." ./scripts/check_egress.sh
# Lo llama up.sh full ANTES de arrancar los señuelos. No cambia nada: revisa la red y lanza un
# contenedor de sonda efímero, sin privilegios, que intenta abrir conexiones nuevas.
# Todas deben fallar. Sale con 1 si alguna conecta o si la red no está aislada.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=lib/contract.sh
. "$ROOT/scripts/lib/contract.sh"
BUSYBOX="${BUSYBOX_IMAGE:-busybox:1.36.1}"
PROBES="${EGRESS_PROBES:-1.1.1.1:443 9.9.9.9:53 169.254.169.254:80}"

fail=0
isolation="$(docker network inspect -f '{{index .Options "com.docker.network.bridge.enable_icc"}} {{.EnableIPv6}}' "$SHARED_NET")"
if [ "$isolation" = "false false" ]; then echo "[egress] red $SHARED_NET: sin tráfico entre contenedores ni IPv6"
else echo "[egress] FALLO red $SHARED_NET no aislada (icc/IPv6 = $isolation)"; fail=1; fi

out="$(docker run --rm --network "$SHARED_NET" --user 65534:65534 --cap-drop ALL --read-only \
  --security-opt no-new-privileges:true --sysctl net.ipv6.conf.all.disable_ipv6=1 \
  -e PROBES="$PROBES" "$BUSYBOX" sh -c \
  'for p in $PROBES; do
     if nc -w 3 "${p%:*}" "${p#*:}" </dev/null >/dev/null 2>&1; then echo "ABIERTA $p"; else echo "cerrada $p"; fi
   done')"
echo "$out" | sed 's/^/[egress] salida nueva hacia /'
echo "$out" | grep -q '^ABIERTA' && fail=1

if [ "$fail" = 1 ]; then
  echo "[egress] La honeynet puede abrir conexiones que la política de laboratorio no aprueba."
  echo "[egress] Aplica antes la política (requiere root; hazlo tú): sudo modules/ssh-honeypot/scripts/egress-firewall.sh"
  exit 1
fi
echo "[egress] ok: ninguna conexión nueva sale de $SHARED_NET"
