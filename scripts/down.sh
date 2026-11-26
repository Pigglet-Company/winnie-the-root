#!/usr/bin/env bash
# scripts/down.sh - para los contenedores de un perfil. Conserva los datos salvo con --purge.
#   ./scripts/down.sh [full]             para señuelos y pipeline (por defecto)
#   ./scripts/down.sh synthetic          para solo el pipeline
#   ./scripts/down.sh [perfil] --purge   además BORRA los volúmenes de esos módulos; con full,
#                                        también la red y los volúmenes de logs por fuente
# El volumen anterior a W04 (honeylogs) nunca se borra aquí: es el legado de la migración.
# Solo toca proyectos Compose de Winnie y recursos con la etiqueta del proyecto.
# Sale con 1 si algo no se pudo parar o borrar.
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=lib/contract.sh
. "$ROOT/scripts/lib/contract.sh"

usage() { sed -n '2,9p' "$0" | sed 's/^# \{0,1\}//'; exit "${1:-0}"; }
PROFILE=full; PURGE=0
for arg in "$@"; do
  case "$arg" in
    --purge) PURGE=1 ;;
    --help|-h) usage 0 ;;
    *) profile_modules "$arg" >/dev/null 2>&1 || usage 1; PROFILE="$arg" ;;
  esac
done

command -v docker >/dev/null 2>&1 || { echo "ERROR: docker no está instalado" >&2; exit 1; }
docker info >/dev/null 2>&1 || { echo "ERROR: no puedo hablar con el daemon de Docker" >&2; exit 1; }

FAILS=0
report() {   # $1=descripción; resto=comando
  local what="$1" out; shift
  if out="$("$@" 2>&1)"; then echo "[down] $what: ok"
  else echo "[down] ERROR $what:" >&2; echo "$out" | sed 's/^/    /' >&2; FAILS=$((FAILS + 1)); fi
}

V=(); [ "$PURGE" = 1 ] && V=(-v)
# Orden inverso al de arranque: primero quien lee los logs.
for m in $(profile_modules "$PROFILE" | awk '{for (i = NF; i > 0; i--) print $i}'); do
  # shellcheck disable=SC2046
  report "$m" bash -c 'cd "$1" && shift && docker compose "$@"' _ "$ROOT/modules/$m" \
    $(compose_files "$PROFILE" "$m") down ${V[@]+"${V[@]}"}
done

remove_shared() {   # $1=volume|network $2=nombre
  local labels
  docker "$1" inspect "$2" >/dev/null 2>&1 || return 0
  labels="$(docker "$1" inspect -f '{{json .Labels}}' "$2" 2>/dev/null)"
  case "$labels" in
    *"\"${PROJECT_LABEL%%=*}\":\"${PROJECT_LABEL#*=}\""*) report "$1 $2" docker "$1" rm "$2" ;;
    *) echo "[down] aviso: $1 $2 no lleva la etiqueta $PROJECT_LABEL; no lo borro." \
            "Si es de Winnie, bórralo a mano: docker $1 rm $2" ;;
  esac
}
if [ "$PURGE" = 1 ] && [ "$PROFILE" = full ]; then
  for vol in $(source_volume_names); do remove_shared volume "$vol"; done
  remove_shared network "$SHARED_NET"
  if docker volume inspect "$LEGACY_VOL" >/dev/null 2>&1; then
    echo "[down] conservo el volumen legado $LEGACY_VOL (anterior a W04). Bórralo a mano cuando ya" \
         "no necesites volver atrás: docker volume rm $LEGACY_VOL"
  fi
fi

if [ "$FAILS" -gt 0 ]; then
  echo "[down] $FAILS operación(es) fallaron; revisa los errores de arriba." >&2
  exit 1
fi
if [ "$PURGE" = 1 ]; then echo "Perfil $PROFILE parado y sus datos borrados."
else echo "Perfil $PROFILE parado. Datos conservados (usa --purge para borrarlos)."; fi
