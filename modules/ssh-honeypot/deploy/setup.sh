#!/usr/bin/env bash
# deploy/setup.sh — despliegue del módulo A en un VPS Ubuntu 22.04/24.04 LIMPIO (Fase 2)
#
# Proceso en DOS pasos para no perder el acceso al servidor:
#   1) sudo ./setup.sh prepare --admin-user USUARIO [--ssh-port 22022] [--wireguard]
#        - instala Docker, ufw, mueve el SSH real a un puerto alto (el 22 sigue
#          abierto TEMPORALMENTE), levanta los honeypots y aplica el firewall de salida.
#        - PRUEBA entonces, desde otra terminal:  ssh -p 22022 USUARIO@IP
#   2) sudo ./setup.sh finalize
#        - quita el 22 del SSH real y redirige 22->2222 (Cowrie).
#   Extras: status | rollback (vuelve a abrir el SSH real en el 22)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODULE_DIR="$(dirname "$SCRIPT_DIR")"
REPO_ROOT="$(cd "$MODULE_DIR/../.." && pwd)"
SSHD_DROPIN="/etc/ssh/sshd_config.d/00-honeypot-admin.conf"
FW_ENV="/etc/honeypot/firewall.env"
REAL_SSH_PORT=22022
ADMIN_USER=""
WITH_WG=0
ASSUME_YES=0

export DEBIAN_FRONTEND=noninteractive

log() { printf '\n[setup] %s\n' "$*"; }
die() { printf '\n[setup] ERROR: %s\n' "$*" >&2; exit 1; }
require_root() { [[ $EUID -eq 0 ]] || die "ejecuta como root (sudo)"; }

check_os() {
  # shellcheck disable=SC1091
  . /etc/os-release
  [[ "${ID:-}" == "ubuntu" && ( "${VERSION_ID:-}" == "22.04" || "${VERSION_ID:-}" == "24.04" ) ]] \
    || die "solo Ubuntu 22.04/24.04 (detectado: ${PRETTY_NAME:-desconocido})"
}

# Todo lo que prepare necesita del repositorio, comprobado ANTES de tocar paquetes, SSH o ufw.
check_repo_files() {
  local f
  for f in "$MODULE_DIR/compose.yml" "$MODULE_DIR/scripts/egress-firewall.sh" \
           "$SCRIPT_DIR/redirect-ports.sh" "$REPO_ROOT/scripts/init.sh" "$REPO_ROOT/scripts/lib/contract.sh"; do
    [[ -f "$f" ]] || die "falta $f (checkout incompleto); no se ha cambiado nada"
  done
  [[ -f "$MODULE_DIR/.env" || -f "$MODULE_DIR/.env.example" ]] \
    || die "falta $MODULE_DIR/.env.example; no se ha cambiado nada"
}

install_packages() {
  log "Instalando paquetes base"
  apt-get update -y
  apt-get install -y ca-certificates curl gnupg ufw iptables jq cron
}

install_docker() {
  if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
    log "Docker y compose ya instalados"; return
  fi
  log "Instalando Docker (repositorio oficial)"
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
  chmod a+r /etc/apt/keyrings/docker.asc
  # shellcheck disable=SC1091
  . /etc/os-release
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu ${VERSION_CODENAME} stable" \
    > /etc/apt/sources.list.d/docker.list
  apt-get update -y
  apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
  systemctl enable --now docker
}

configure_docker_logs() {
  if [[ ! -f /etc/docker/daemon.json ]]; then
    log "Configurando rotación de logs de Docker"
    mkdir -p /etc/docker
    cat > /etc/docker/daemon.json <<'EOF'
{ "log-driver": "json-file", "log-opts": { "max-size": "10m", "max-file": "3" } }
EOF
    systemctl restart docker
  fi
}

reload_sshd() {
  # Ubuntu 24.04 usa activación por socket y entonces ignora "Port" de sshd_config
  if systemctl is-enabled --quiet ssh.socket 2>/dev/null; then
    systemctl disable --now ssh.socket
    systemctl enable ssh.service
  fi
  systemctl restart ssh
}

write_sshd_dropin() {   # argumentos: lista de puertos
  local tmp p
  tmp="$(mktemp)"
  {
    echo "# Gestionado por honeypot-tfm deploy/setup.sh"
    for p in "$@"; do echo "Port $p"; done
    cat <<EOF
PasswordAuthentication no
KbdInteractiveAuthentication no
PubkeyAuthentication yes
PermitRootLogin prohibit-password
AllowUsers $ADMIN_USER
MaxAuthTries 3
LoginGraceTime 30
X11Forwarding no
EOF
  } > "$tmp"
  install -m 0644 "$tmp" "$SSHD_DROPIN"
  rm -f "$tmp"
  if ! sshd -t; then
    rm -f "$SSHD_DROPIN"
    die "la configuración de sshd no es válida; se ha revertido el cambio"
  fi
  reload_sshd
}

configure_ufw() {
  log "Configurando ufw"
  ufw default deny incoming
  ufw default allow outgoing
  ufw allow 22/tcp comment 'SSH real (TEMPORAL hasta finalize)'
  ufw limit "${REAL_SSH_PORT}/tcp" comment 'SSH real de administracion'
  local p
  for p in 21 23 2121 2222 2223 3306 3307 6379 6380; do
    ufw allow "${p}/tcp" comment 'senuelo'
  done
  ufw --force enable
}

ensure_shared_resources() {
  if docker network inspect honeynet >/dev/null 2>&1 && docker volume inspect honeylogs >/dev/null 2>&1; then
    log "honeynet y honeylogs ya existen"; return
  fi
  [[ -f "$REPO_ROOT/scripts/init.sh" ]] || die "falta $REPO_ROOT/scripts/init.sh (lo aporta la integración)"
  log "Ejecutando scripts/init.sh"
  bash "$REPO_ROOT/scripts/init.sh"
}

start_honeypots() {
  log "Levantando honeypots"
  if [[ ! -f "$MODULE_DIR/.env" ]]; then
    cp "$MODULE_DIR/.env.example" "$MODULE_DIR/.env"
    # En el VPS los señuelos deben escuchar en todas las interfaces (el ejemplo trae 127.0.0.1).
    sed -i 's/^HP_BIND_ADDR=.*/HP_BIND_ADDR=0.0.0.0/' "$MODULE_DIR/.env"
  fi
  grep -q '^HP_BIND_ADDR=' "$MODULE_DIR/.env" || echo 'HP_BIND_ADDR=0.0.0.0' >> "$MODULE_DIR/.env"
  log "Señuelos publicados en $(grep '^HP_BIND_ADDR=' "$MODULE_DIR/.env" | tail -1)"
  (cd "$MODULE_DIR" && docker compose up -d --build)
}

install_firewall_service() {
  log "Instalando servicio honeypot-firewall (egress + redirecciones, persistente)"
  mkdir -p /etc/honeypot
  [[ -f "$FW_ENV" ]] || echo "REDIRECT_SSH=0" > "$FW_ENV"
  chmod +x "$MODULE_DIR/scripts/egress-firewall.sh" "$SCRIPT_DIR/redirect-ports.sh"
  cat > /etc/systemd/system/honeypot-firewall.service <<EOF
[Unit]
Description=Honeypot: firewall de salida y redirecciones de puertos
After=docker.service network-online.target
Wants=network-online.target
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
EnvironmentFile=-$FW_ENV
ExecStart=$MODULE_DIR/scripts/egress-firewall.sh
ExecStart=$SCRIPT_DIR/redirect-ports.sh apply
ExecStop=$SCRIPT_DIR/redirect-ports.sh remove
ExecStop=$MODULE_DIR/scripts/egress-firewall.sh --remove

[Install]
WantedBy=multi-user.target
EOF
  systemctl daemon-reload
  systemctl enable honeypot-firewall.service
  systemctl restart honeypot-firewall.service
}

install_log_pruning() {
  # Cowrie rota a diario (cowrie.json.AAAA-MM-DD); se conservan 5 días
  cat > /etc/cron.daily/honeypot-prune-logs <<'EOF'
#!/bin/sh
find /var/lib/docker/volumes/honeylogs/_data/cowrie -name 'cowrie.json.*' -mtime +5 -delete
EOF
  chmod 0755 /etc/cron.daily/honeypot-prune-logs
}

setup_wireguard() {
  log "Configurando WireGuard (servidor 10.8.0.1/24, UDP 51820)"
  apt-get install -y wireguard
  mkdir -p /etc/wireguard
  (
    umask 077
    [[ -f /etc/wireguard/server.key ]] || wg genkey | tee /etc/wireguard/server.key | wg pubkey > /etc/wireguard/server.pub
    if [[ ! -f /etc/wireguard/wg0.conf ]]; then
      cat > /etc/wireguard/wg0.conf <<EOF
[Interface]
Address = 10.8.0.1/24
ListenPort = 51820
PrivateKey = $(cat /etc/wireguard/server.key)
EOF
    fi
  )
  ufw allow 51820/udp comment 'WireGuard'
  systemctl enable --now wg-quick@wg0
  cat <<EOF

  Clave pública del servidor: $(cat /etc/wireguard/server.pub)
  Para añadir un cliente (genera su clave con 'wg genkey | tee c.key | wg pubkey'):
    wg set wg0 peer <CLAVE_PUBLICA_CLIENTE> allowed-ips 10.8.0.2/32 && wg-quick save wg0
  Opcional (más estricto, SOLO tras comprobar que el túnel funciona):
    ufw delete limit ${REAL_SSH_PORT}/tcp ; ufw allow from 10.8.0.0/24 to any port ${REAL_SSH_PORT} proto tcp
EOF
}

cmd_prepare() {
  require_root; check_os
  while (( $# )); do
    case "$1" in
      --admin-user) ADMIN_USER="${2:-}"; shift ;;
      --ssh-port)   REAL_SSH_PORT="${2:-}"; shift ;;
      --wireguard)  WITH_WG=1 ;;
      *) die "opción desconocida: $1" ;;
    esac
    shift
  done
  [[ -n "$ADMIN_USER" ]] || die "indica --admin-user USUARIO (el usuario con el que entras por SSH)"
  [[ "$REAL_SSH_PORT" =~ ^[0-9]+$ && "$REAL_SSH_PORT" -gt 1024 ]] || die "--ssh-port debe ser numérico y > 1024"
  id "$ADMIN_USER" >/dev/null 2>&1 || die "el usuario $ADMIN_USER no existe"
  local home keys
  home="$(getent passwd "$ADMIN_USER" | cut -d: -f6)"
  keys="$home/.ssh/authorized_keys"
  [[ -s "$keys" ]] || die "$keys no existe o está vacío: se desactiva la contraseña, necesitas clave pública"
  check_repo_files

  install_packages
  install_docker
  configure_docker_logs
  write_sshd_dropin 22 "$REAL_SSH_PORT"       # el 22 sigue abierto hasta 'finalize'
  configure_ufw
  ensure_shared_resources
  start_honeypots
  install_firewall_service
  install_log_pruning
  (( WITH_WG )) && setup_wireguard

  cat <<EOF

================================================================
 PREPARACIÓN COMPLETADA. NO cierres esta sesión todavía.
 1) Desde OTRA terminal comprueba el acceso por el puerto nuevo:
      ssh -p ${REAL_SSH_PORT} ${ADMIN_USER}@<IP_DEL_VPS>
 2) Solo si funciona:  sudo $SCRIPT_DIR/setup.sh finalize
 Si algo falla:  sudo $SCRIPT_DIR/setup.sh rollback
================================================================
EOF
}

cmd_finalize() {
  require_root
  [[ -f "$SSHD_DROPIN" ]] || die "ejecuta primero 'prepare'"
  REAL_SSH_PORT="$(awk '/^Port /{print $2}' "$SSHD_DROPIN" | grep -vx 22 | head -n1)"
  [[ -n "$REAL_SSH_PORT" ]] || die "no encuentro el puerto SSH alto en $SSHD_DROPIN"
  ss -ltn | grep -q ":${REAL_SSH_PORT} " || die "sshd no escucha en ${REAL_SSH_PORT}"
  if (( ! ASSUME_YES )); then
    read -r -p "¿Has entrado por SSH en el puerto ${REAL_SSH_PORT} desde otra terminal? Escribe 'SSH OK': " ans
    [[ "$ans" == "SSH OK" ]] || die "cancelado"
  fi
  log "Quitando el puerto 22 del SSH real"
  sed -i '/^Port 22$/d' "$SSHD_DROPIN"
  sshd -t || die "sshd_config inválido tras el cambio"
  reload_sshd
  ufw delete allow 22/tcp || true
  echo "REDIRECT_SSH=1" > "$FW_ENV"
  systemctl restart honeypot-firewall.service
  log "Hecho. El 22 va a Cowrie; el SSH real está solo en ${REAL_SSH_PORT}."
  ss -ltnp | grep -E ':22 ' || echo "(ningún proceso del host escucha en :22, correcto)"
}

cmd_rollback() {
  require_root
  [[ -f "$SSHD_DROPIN" ]] || die "no hay nada que revertir"
  grep -qx 'Port 22' "$SSHD_DROPIN" || sed -i '1a Port 22' "$SSHD_DROPIN"
  sshd -t || die "sshd_config inválido"
  reload_sshd
  ufw allow 22/tcp || true
  echo "REDIRECT_SSH=0" > "$FW_ENV"
  systemctl restart honeypot-firewall.service
  log "SSH real de nuevo accesible en el 22 (y en el puerto alto)."
}

cmd_status() {
  echo "--- Listeners ---";  ss -ltnup | grep -E ':(21|22|23|3306|6379|2121|2222|2223|3307|6380|'"$REAL_SSH_PORT"') ' || true
  echo "--- ufw ---";        ufw status verbose || true
  echo "--- Redirecciones ---"; "$SCRIPT_DIR/redirect-ports.sh" status || true
  echo "--- Contenedores ---";  docker ps --filter name=hp- --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'
}

case "${1:-}" in
  prepare)  shift; cmd_prepare "$@" ;;
  finalize) shift; [[ "${1:-}" == "--yes" ]] && ASSUME_YES=1; cmd_finalize ;;
  rollback) cmd_rollback ;;
  status)   cmd_status ;;
  *) sed -n '2,13p' "$0" | sed 's/^# \{0,1\}//'; exit 1 ;;
esac
