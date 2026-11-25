# scripts/lib/contract.sh - contrato único de perfiles, puertos y requisitos de host.
# Lo cargan up.sh, down.sh y preflight.sh (source). No ejecuta nada por sí mismo.
# Cambia aquí un puerto, un módulo o un requisito y los tres scripts lo heredan.

# Perfiles de laboratorio disponibles en esta versión.
#   synthetic  pipeline con datos inventados (sin señuelos, nada expuesto)
#   full       señuelos A (SSH) + B (web) + pipeline C
PROFILES="synthetic full"

# Módulos que arranca cada perfil, en orden de arranque.
profile_modules() {
  case "$1" in
    synthetic) echo "pipeline" ;;
    full)      echo "ssh-honeypot web-honeypot pipeline" ;;
    *)         return 1 ;;
  esac
}

# Argumentos -f de Compose para un módulo dentro de un perfil.
compose_files() {   # $1=perfil $2=módulo
  if [ "$2" = "pipeline" ] && [ "$1" = "synthetic" ]; then
    echo "-f compose.yml -f compose.dev.yml"
  else
    echo "-f compose.yml"
  fi
}

# Contenedores que pertenecen a cada módulo (para reconocer puertos propios).
module_containers() {
  case "$1" in
    ssh-honeypot) echo "hp-cowrie hp-opencanary" ;;
    web-honeypot) echo "hp-web" ;;
    pipeline)     echo "pl-dashboards pl-opensearch pl-vector pl-setup pl-perms" ;;
  esac
}

# Recursos compartidos que crea init.sh. La etiqueta marca que son de este proyecto:
# down.sh --purge solo borra los que la llevan.
SHARED_NET="honeynet"
SHARED_SUBNET="172.30.0.0/24"
SHARED_VOL="honeylogs"
PROJECT_LABEL="io.winnie.project=winnie-the-root"

# Requisitos de host.
REQUIRED_COMMANDS="docker python3 curl"
MIN_MAX_MAP_COUNT=262144
MAX_MAP_COUNT_FILE="${MAX_MAP_COUNT_FILE:-/proc/sys/vm/max_map_count}"

# Valor efectivo de una variable para un módulo, con la misma precedencia que Compose:
# entorno del shell > modules/<módulo>/.env > valor por defecto.
effective() {   # $1=módulo $2=VARIABLE $3=defecto
  local val envf="$ROOT/modules/$1/.env"
  if [ -n "${!2+x}" ]; then
    val="${!2}"
  elif [ -f "$envf" ] && grep -qE "^$2=" "$envf"; then
    val="$(grep -E "^$2=" "$envf" | tail -1 | cut -d= -f2-)"
  else
    val="$3"
  fi
  printf '%s' "$val"
}

# Puertos publicados en el host: una línea "módulo dirección puerto servicio" por puerto.
# Las direcciones por defecto deben coincidir con los compose.yml (lo comprueba tests/).
published_ports() {   # $1=perfil
  local m addr
  for m in $(profile_modules "$1"); do
    case "$m" in
      ssh-honeypot)
        addr="$(effective ssh-honeypot HP_BIND_ADDR 127.0.0.1)"
        printf '%s %s %s %s\n' "$m" "$addr" 2222 ssh "$m" "$addr" 2223 telnet \
          "$m" "$addr" 2121 ftp "$m" "$addr" 3307 mysql "$m" "$addr" 6380 redis ;;
      web-honeypot)
        printf '%s %s %s %s\n' "$m" "$(effective web-honeypot HP_BIND_ADDR 127.0.0.1)" \
          "$(effective web-honeypot WEB_HOST_PORT 8080)" web ;;
      pipeline)
        printf '%s %s %s %s\n' "$m" 127.0.0.1 5601 dashboards ;;
    esac
  done
}
