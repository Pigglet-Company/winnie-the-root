#!/usr/bin/env bash
# tests/check_isolation_docker.sh - aceptación de W04 (contención del laboratorio) con Docker real.
# SOLO en un host DESECHABLE (el runner de CI): cambia iptables del host con sudo, arranca los
# señuelos y borra recursos de Winnie. Exige WINNIE_DISPOSABLE_HOST=1.
#   1) migración en frío desde la disposición anterior (legado RO, manifiesto, init repetido)
#   2) montajes del modelo Compose: cada productor solo su volumen; el colector todos en RO
#   3) salida: fallo a medias de la instalación (queda cerrada), instalación, sondas a Internet,
#      metadatos, host y pares; IPv6 ausente
#   4) señuelos reales: respuesta por los puertos publicados, escritura propia con su UID,
#      denegación cruzada de lectura/escritura/borrado, lectura del colector, reinicio
#   5) retirada de reglas y limpieza
# Esto es la contención del LABORATORIO (W04). La contención exterior de un sensor (ACL, vNIC,
# revocación) es H02 y no se prueba aquí.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
[ "${WINNIE_DISPOSABLE_HOST:-}" = 1 ] || { echo "ERROR: solo en un host desechable (WINNIE_DISPOSABLE_HOST=1)" >&2; exit 2; }
# shellcheck source=../scripts/lib/contract.sh
. scripts/lib/contract.sh
unset HP_BIND_ADDR WEB_HOST_PORT
BB=busybox:1.36.1
FW=modules/ssh-honeypot/scripts/egress-firewall.sh
T="$(mktemp -d)"
GW=172.30.0.1
HOST_PORT=18099

fail() { echo "ERROR: $*" >&2; exit 1; }
ok() { echo "  ok: $*"; }
cleanup() {
  set +e
  docker rm -f w04-peer >/dev/null 2>&1
  for m in web-honeypot ssh-honeypot; do (cd "modules/$m" && docker compose down >/dev/null 2>&1); done
  sudo bash "$FW" --remove >/dev/null 2>&1
  [ -n "${holder:-}" ] && kill "$holder" 2>/dev/null
  rm -rf "${T:?}"
}
trap cleanup EXIT
probe() { docker run --rm --network "$SHARED_NET" --user 65534:65534 "$BB" nc -w 3 "${1%:*}" "${1#*:}" </dev/null >/dev/null 2>&1; }
closed() { if probe "$1"; then fail "$2: $1 conecta"; else ok "$2: $1 no conecta"; fi; }
vol() { local s; for s in $SOURCE_VOLUMES; do [ "${s%%:*}" = "$1" ] && { s="${s#*:}"; echo "${s%%:*}"; }; done; }
uid() { local s; for s in $SOURCE_VOLUMES; do [ "${s%%:*}" = "$1" ] && { s="${s#*:*:}"; echo "${s%%:*}"; }; done; }
FILES="cowrie:cowrie.json opencanary:opencanary.log web:web.jsonl"
file_of() { local f; for f in $FILES; do [ "${f%%:*}" = "$1" ] && echo "${f#*:}"; done; }
in_vol() { local v="$1"; shift; docker run --rm --network none -v "$v:/v:ro" "$BB" "$@"; }
legacy_hash() { docker run --rm --network none -v "$LEGACY_VOL:/old:ro" "$BB" sh -c 'cd /old && find . -type f -exec sha256sum {} + | sort; stat -c "%a %n" /old /old/*' | sha256sum; }

echo "== 1. Migración en frío desde la disposición anterior"
docker network create --label "$PROJECT_LABEL" --driver bridge --subnet "$SHARED_SUBNET" --ip-range 172.30.0.128/25 "$SHARED_NET" >/dev/null
docker volume create --label "$PROJECT_LABEL" "$LEGACY_VOL" >/dev/null
docker run --rm -v "$LEGACY_VOL:/logs" "$BB" sh -c '
  mkdir -p /logs/cowrie /logs/opencanary /logs/web && chmod 0777 /logs /logs/cowrie /logs/opencanary /logs/web
  echo "{\"eventid\":\"cowrie.session.connect\",\"legacy\":1}" > /logs/cowrie/cowrie.json
  echo "{\"eventid\":\"cowrie.session.closed\",\"legacy\":1}" > /logs/cowrie/cowrie.json.2026-11-01
  echo "{\"logtype\":2000,\"legacy\":1}" > /logs/opencanary/opencanary.log
  echo "{\"event\":\"http.request\",\"legacy\":1}" > /logs/web/web.jsonl
  echo suelto > /logs/stray.txt'
before="$(legacy_hash)"
if ./scripts/init.sh >"$T/init.out" 2>&1; then fail "init.sh aceptó la red sin aislar"; fi
grep -q migrate_honeylogs "$T/init.out" || fail "init.sh no remite a la migración: $(cat "$T/init.out")"
ok "init.sh se niega con la red anterior y remite a migrate_honeylogs.sh"
./scripts/migrate_honeylogs.sh
manifest="$(ls -t var/migrations/honeylogs-*.json | head -1)"
python3 - "$manifest" <<'PY'
import json, sys
m = json.load(open(sys.argv[1]))
assert m["ok"] and not m["mismatches"], m["mismatches"]
moved = {f["legacy"] for f in m["files"] if f["target"]}
assert moved == {"cowrie/cowrie.json", "cowrie/cowrie.json.2026-11-01", "opencanary/opencanary.log", "web/web.jsonl"}, moved
assert [f["legacy"] for f in m["files"] if not f["target"]] == ["stray.txt"]
print(f"  ok: manifiesto {sys.argv[1]} con {len(m['files'])} ficheros y 0 discrepancias")
PY
[ "$(legacy_hash)" = "$before" ] || fail "el legado cambió durante la migración"
ok "legado $LEGACY_VOL intacto (contenido y modos)"
if ./scripts/migrate_honeylogs.sh >"$T/mig2.out" 2>&1; then fail "la segunda migración sobrescribió destinos con datos"; fi
grep -q "ya tiene datos" "$T/mig2.out" || fail "segunda migración: $(cat "$T/mig2.out")"
[ "$(legacy_hash)" = "$before" ] || fail "el legado cambió en la segunda migración"
ok "segunda migración rechazada sin tocar nada"
./scripts/init.sh >/dev/null
./scripts/init.sh >/dev/null
for s in cowrie opencanary web; do
  got="$(in_vol "$(vol $s)" stat -c '%u:%g %a' /v)"
  [ "$got" = "$(uid $s):$READER_GID 2750" ] || fail "$(vol $s) tras dos init: $got"
  ok "$(vol $s) tras dos init.sh: $got (no se reabre)"
done
grep -n '0777\|a+rwX\|chmod 777' scripts/init.sh && fail "init.sh vuelve a abrir permisos"
[ "$(docker network inspect -f '{{index .Options "com.docker.network.bridge.enable_icc"}} {{.EnableIPv6}}' "$SHARED_NET")" = "false false" ] \
  || fail "red no aislada tras migrar"
ok "red $SHARED_NET recreada sin icc ni IPv6"

echo "== 2. Montajes del modelo Compose"
for spec in "ssh-honeypot:hp-cowrie:cowrie" "ssh-honeypot:hp-opencanary:opencanary" "web-honeypot:hp-web:web"; do
  IFS=: read -r m svc src <<<"$spec"
  (cd "modules/$m" && docker compose config --format json) | python3 -c '
import json, sys
svc, own = sys.argv[1], sys.argv[2]
logs = [v for v in json.load(sys.stdin)["services"][svc]["volumes"] if v.get("type") == "volume" and v["source"].startswith("honeylogs")]
assert [(v["source"], v.get("read_only", False)) for v in logs] == [(own, False)], logs
print(f"  ok: {svc} monta solo {own} (RW)")' "$svc" "$(vol "$src")"
done
for extra in "" "-f compose.dev.yml"; do
  # shellcheck disable=SC2086
  (cd modules/pipeline && docker compose -f compose.yml $extra config --format json) | python3 -c '
import json, sys
vols = json.load(sys.stdin)["services"]["pl-vector"]["volumes"]
logs = {v["target"]: (v["source"].rsplit("/", 1)[-1], v.get("read_only", False)) for v in vols if v["target"].startswith("/logs")}
assert set(logs) == {"/logs/cowrie", "/logs/opencanary", "/logs/web"}, logs
assert all(ro for _, ro in logs.values()), logs
assert all(src != "honeylogs" for src, _ in logs.values()), logs
print("  ok: pl-vector (%s) lee las tres fuentes en RO: %s" % (sys.argv[1], sorted(s for s, _ in logs.values())))' "${extra:-full}"
done

echo "== 3. Política de salida (IPv4) e IPv6"
python3 -m http.server "$HOST_PORT" --bind 0.0.0.0 >/dev/null 2>&1 &
holder=$!
sleep 1
docker run -d --name w04-peer --network "$SHARED_NET" "$BB" httpd -f -p 9000 >/dev/null
PEER="$(docker inspect -f "{{(index .NetworkSettings.Networks \"$SHARED_NET\").IPAddress}}" w04-peer)"
probe 1.1.1.1:443 || fail "sin reglas, la sonda no sale a Internet: la prueba no discrimina en este host"
ok "sin reglas la sonda sale a 1.1.1.1:443 (la prueba discrimina)"
if probe "$GW:$HOST_PORT"; then ok "sin reglas la sonda llega al host $GW:$HOST_PORT"; else echo "  nota: el host ya filtra $GW:$HOST_PORT sin reglas"; fi
closed "$PEER:9000" "par de la honeynet (icc desactivado, sin reglas)"

cat > "$T/ipt" <<'EOF'
#!/bin/sh
# iptables que falla en la tercera regla de HONEYNET_EGRESS: simula una instalación a medias
case "$*" in *"-A HONEYNET_EGRESS"*)
  n=$(( $(cat "$COUNT" 2>/dev/null || echo 0) + 1 )); echo "$n" > "$COUNT"; [ "$n" -ge 3 ] && exit 1 ;;
esac
exec iptables "$@"
EOF
chmod +x "$T/ipt"
if sudo env IPTABLES="$T/ipt" COUNT="$T/count" bash "$FW" >"$T/fw.out" 2>&1; then fail "la instalación con fallo inyectado terminó bien"; fi
sudo iptables -S DOCKER-USER | grep -q winnie-egress-guard || fail "tras el fallo no queda el guard"
ok "fallo a medias: el script sale con error y deja el guard puesto"
closed 1.1.1.1:443 "tras el fallo a medias, Internet"
closed "$GW:$HOST_PORT" "tras el fallo a medias, host"
sudo bash "$FW"
sudo iptables -S | grep -q winnie-egress-guard && fail "el guard sigue tras instalar bien"
ok "reinstalación: reglas puestas y guard retirado"
closed 1.1.1.1:443 "Internet"
closed 9.9.9.9:53 "DNS externo"
closed 169.254.169.254:80 "metadatos cloud"
closed "$GW:$HOST_PORT" "host desde la honeynet"
closed "$PEER:9000" "par de la honeynet"
./scripts/check_egress.sh >/dev/null || fail "check_egress.sh no reconoce la política aplicada"
ok "check_egress.sh pasa con la política aplicada"
v6="$(docker run --rm --network "$SHARED_NET" "$BB" ip -6 addr show scope global)"
[ -z "$v6" ] || fail "la sonda tiene IPv6 global: $v6"
ok "la red no da direcciones IPv6 globales"
docker rm -f w04-peer >/dev/null

echo "== 4. Señuelos reales"
(cd modules/ssh-honeypot && docker compose up -d --build --quiet-pull) >/dev/null
(cd modules/web-honeypot && docker compose up -d --build --quiet-pull) >/dev/null
wait_healthy() {
  local c
  for c in hp-cowrie hp-opencanary hp-web; do
    for _ in $(seq 90); do [ "$(docker inspect -f '{{.State.Health.Status}}' "$c")" = healthy ] && break; sleep 2; done
    [ "$(docker inspect -f '{{.State.Health.Status}}' "$c")" = healthy ] || { docker logs --tail 30 "$c"; fail "$c no está sano"; }
  done
}
traffic() {   # respuestas por los puertos publicados (y eventos para los logs)
  local banner
  banner="$(timeout 5 bash -c 'exec 3<>/dev/tcp/127.0.0.1/2222; head -c 7 <&3')" || true
  [ "$banner" = "SSH-2.0" ] || fail "sin respuesta SSH por 127.0.0.1:2222 ($banner)"
  banner="$(timeout 5 bash -c 'exec 3<>/dev/tcp/127.0.0.1/2121; head -c 3 <&3')" || true
  [ "$banner" = "220" ] || fail "sin respuesta FTP por 127.0.0.1:2121 ($banner)"
  [ "$(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:8080/?w04=$1")" = 200 ] || fail "sin respuesta web por 127.0.0.1:8080"
}
lines() { in_vol "$(vol "$1")" sh -c "cat /v/$(file_of "$1") 2>/dev/null | wc -l" | tr -d ' '; }
wait_lines() {   # $1=fuente $2=mínimo
  for _ in $(seq 30); do [ "$(lines "$1")" -ge "$2" ] && return 0; sleep 2; done
  fail "$(vol "$1"): menos de $2 líneas en $(file_of "$1")"
}
wait_healthy
traffic 1
ok "respuestas por SSH 2222, FTP 2121 y web 8080 con la salida cerrada"
declare -A seen
for s in cowrie opencanary web; do
  wait_lines "$s" 2   # la línea migrada + al menos una nueva
  seen[$s]="$(lines "$s")"
  owner="$(in_vol "$(vol $s)" sh -c "ls -n /v | awk 'NR>1 {print \$3}' | sort -u | tr '\n' ' '")"
  [ "$owner" = "$(uid $s) " ] || fail "$(vol $s): ficheros con propietarios '$owner', esperado $(uid $s)"
  ok "$s escribe en $(vol $s) con su UID $(uid $s) (${seen[$s]} líneas)"
done
for c in hp-cowrie:cowrie hp-opencanary:opencanary hp-web:web; do
  got="$(docker inspect -f '{{range .Mounts}}{{if eq .Type "volume"}}{{.Name}}:{{.RW}} {{end}}{{end}}' "${c%%:*}" | tr ' ' '\n' | grep '^honeylogs' || true)"
  [ "$got" = "$(vol "${c#*:}"):true" ] || fail "${c%%:*} monta: $got"
  pid="$(docker inspect -f '{{.State.Pid}}' "${c%%:*}")"
  [ "$(sudo nsenter -t "$pid" -n cat /proc/sys/net/ipv6/conf/all/disable_ipv6)" = 1 ] || fail "${c%%:*} con IPv6 activo"
  [ -z "$(sudo nsenter -t "$pid" -n ip -6 addr show scope global)" ] || fail "${c%%:*} con IPv6 global"
done
ok "en marcha: cada señuelo monta solo su volumen de logs y no tiene IPv6"

for p in cowrie opencanary web; do
  for s in cowrie opencanary web; do
    [ "$p" = "$s" ] && continue
    f="$(file_of "$s")"; u="$(uid "$p")"
    # Aunque el volumen ajeno se le montara por error, los permisos lo impiden.
    if docker run --rm --network none --user "$u:$u" -v "$(vol "$s"):/v" "$BB" sh -c "cat /v/$f || ls /v || touch /v/x || rm -f /v/$f" >/dev/null 2>&1; then
      fail "UID $u ($p) pudo leer, escribir o borrar en $(vol "$s")"
    fi
    [ "$(lines "$s")" -ge "${seen[$s]}" ] || fail "$(vol "$s") perdió líneas tras el intento de $p"
  done
  ok "UID $(uid "$p") ($p): sin lectura, escritura ni borrado en los volúmenes ajenos"
done
reader=(); for s in cowrie opencanary web; do reader+=(-v "$(vol $s):/logs/$s:ro"); done
docker run --rm --network none --user "1000:$READER_GID" "${reader[@]}" "$BB" sh -c \
  'head -c1 /logs/cowrie/cowrie.json /logs/opencanary/opencanary.log /logs/web/web.jsonl' >/dev/null \
  || fail "el colector (1000:$READER_GID) no lee las tres fuentes"
for s in cowrie opencanary web; do
  if docker run --rm --network none --user "1000:$READER_GID" -v "$(vol $s):/v" "$BB" sh -c "touch /v/x || rm -f /v/$(file_of $s)" >/dev/null 2>&1; then
    fail "el colector puede escribir o borrar en $(vol $s) incluso sin RO"
  fi
done
ok "colector 1000:$READER_GID: lee las tres fuentes; no escribe ni borra (ni sin montaje RO)"

first="$(in_vol "$(vol cowrie)" head -1 /v/cowrie.json)"
(cd modules/ssh-honeypot && docker compose restart) >/dev/null
(cd modules/web-honeypot && docker compose restart) >/dev/null
wait_healthy
traffic 2
for s in cowrie opencanary web; do
  wait_lines "$s" $(( seen[$s] + 1 ))
  ok "$s tras reinicio: $(lines "$s") líneas (antes ${seen[$s]}), datos previos conservados"
done
[ "$(in_vol "$(vol cowrie)" head -1 /v/cowrie.json)" = "$first" ] || fail "la primera línea de cowrie.json cambió tras el reinicio"
./scripts/volume_usage.sh

echo "== 5. Retirada de reglas y limpieza"
for m in web-honeypot ssh-honeypot; do (cd "modules/$m" && docker compose down) >/dev/null 2>&1; done
sudo bash "$FW" --remove
sudo iptables -S | grep -q 'HONEYNET_\|winnie-egress-guard' && fail "quedan reglas tras --remove"
probe 1.1.1.1:443 || fail "tras --remove la salida sigue cortada"
ok "--remove retira cadenas, saltos y guard (la sonda vuelve a salir)"
./scripts/down.sh full --purge >/dev/null
docker volume inspect "$LEGACY_VOL" >/dev/null 2>&1 || fail "down --purge borró el legado"
docker volume rm "$LEGACY_VOL" >/dev/null
ok "down --purge conserva el legado; borrado a mano"
echo "OK"
