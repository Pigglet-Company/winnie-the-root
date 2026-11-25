#!/usr/bin/env bash
# scripts/volume_usage.sh - uso de cada volumen de logs frente a su cuota (SOURCE_VOLUMES).
#   ./scripts/volume_usage.sh
# Solo lectura: monta los volúmenes en RO. Sale con 1 si alguno supera su cuota.
# Es una cuota comprobada, no impuesta por el sistema de ficheros: los límites duros de cada copia
# (rotación, tope de subidas, logs de Docker) están en docs/lab-containment.md.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=lib/contract.sh
. "$ROOT/scripts/lib/contract.sh"
BUSYBOX="${BUSYBOX_IMAGE:-busybox:1.36.1}"

over=0
for spec in $SOURCE_VOLUMES; do
  IFS=: read -r src vol _ quota <<<"$spec"
  used="$(docker run --rm --network none -v "$vol:/v:ro" "$BUSYBOX" du -sm /v | cut -f1)"
  if [ "$used" -gt "$quota" ]; then state="SUPERADA"; over=1; else state="ok"; fi
  printf '[cuota] %-22s %6s MiB de %6s MiB  %s (%s)\n' "$vol" "$used" "$quota" "$state" "$src"
done
exit "$over"
