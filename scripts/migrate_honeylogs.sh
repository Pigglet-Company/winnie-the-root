#!/usr/bin/env bash
# scripts/migrate_honeylogs.sh - migración en frío de la disposición anterior a W04.
#   ./scripts/migrate_honeylogs.sh
# Con los módulos PARADOS (./scripts/down.sh full, sin --purge):
#   1) si la red honeynet no está aislada (icc/IPv6), la recrea con init.sh
#   2) copia honeylogs/{cowrie,opencanary,web} a su volumen por fuente, montando el legado en
#      solo lectura, con el propietario de cada productor
#   3) escribe un manifiesto (var/migrations/honeylogs-<fecha>.json) con el sha256 de cada fichero
#      en origen y destino, y falla si alguno no coincide
# El volumen honeylogs no se modifica ni se borra: es la vuelta atrás (docs/lab-containment.md).
# Se niega a escribir sobre un volumen por fuente que ya tenga datos.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=lib/contract.sh
. "$ROOT/scripts/lib/contract.sh"
BUSYBOX="${BUSYBOX_IMAGE:-busybox:1.36.1}"

die() { echo "ERROR: $*" >&2; exit 1; }
[ "${1:-}" = "--help" ] || [ "${1:-}" = "-h" ] && { sed -n '2,11p' "$0" | sed 's/^# \{0,1\}//'; exit 0; }
docker info >/dev/null 2>&1 || die "no puedo hablar con el daemon de Docker"

running="$(docker ps --format '{{.Names}}')"
for m in $(profile_modules full); do
  for c in $(module_containers "$m"); do
    if printf '%s\n' "$running" | grep -qx "$c"; then die "$c está en marcha: la migración es en frío (./scripts/down.sh full)"; fi
  done
done

# 1) Red: la disposición anterior no aislaba a los pares.
if docker network inspect "$SHARED_NET" >/dev/null 2>&1; then
  isolation="$(docker network inspect -f '{{index .Options "com.docker.network.bridge.enable_icc"}} {{.EnableIPv6}}' "$SHARED_NET")"
  if [ "$isolation" != "false false" ]; then
    [ "$(docker network inspect -f '{{len .Containers}}' "$SHARED_NET")" = 0 ] \
      || die "hay contenedores conectados a $SHARED_NET; páralos antes de migrar"
    docker network rm "$SHARED_NET" >/dev/null
    echo "[migrate] red $SHARED_NET anterior borrada (icc/IPv6 = $isolation); init.sh la recrea aislada"
  fi
fi
bash "$ROOT/scripts/init.sh"

if ! docker volume inspect "$LEGACY_VOL" >/dev/null 2>&1; then
  echo "[migrate] no existe el volumen legado $LEGACY_VOL: no hay logs que copiar"; exit 0
fi

# 2) Copia con el legado en RO; los destinos deben estar vacíos.
mounts=(-v "$LEGACY_VOL:/old:ro"); checks=""; script=""
for spec in $SOURCE_VOLUMES; do
  IFS=: read -r src vol uid _ <<<"$spec"
  mounts+=(-v "$vol:/new/$src")
  checks="$checks
    [ -z \"\$(ls -A /new/$src)\" ] || { echo \"$vol ya tiene datos; no lo sobrescribo\" >&2; exit 3; }"
  script="$script
    if [ -d /old/$src ]; then cp -a /old/$src/. /new/$src/; fi
    chown -R $uid:$READER_GID /new/$src
    find /new/$src -type d -exec chmod 2750 {} +
    find /new/$src -type f -exec chmod 0640 {} +"
done
docker run --rm --network none "${mounts[@]}" "$BUSYBOX" sh -ec "$checks $script" \
  || die "copia abortada; el legado $LEGACY_VOL sigue intacto"

# 3) Manifiesto: sha256 de origen y destino.
hashes() { docker run --rm --network none "${mounts[@]}" "$BUSYBOX" sh -c "cd $1 && find . -type f -exec sha256sum {} +"; }
mkdir -p "$ROOT/var/migrations"
manifest="$ROOT/var/migrations/honeylogs-$(date -u +%Y%m%dT%H%M%SZ).json"
python3 - "$manifest" "$LEGACY_VOL" "$SOURCE_VOLUMES" <(hashes /old) <(hashes /new) <<'PY'
import datetime, json, sys
out, legacy, specs, old_f, new_f = sys.argv[1:]
def read(path):
    return {line.split(None, 1)[1].strip()[2:]: line.split()[0] for line in open(path) if line.strip()}
old, new = read(old_f), read(new_f)
targets = {s.split(":")[0]: s.split(":")[1] for s in specs.split()}
files, errors = [], []
for rel, digest in sorted(old.items()):
    src = rel.split("/", 1)[0]
    if src not in targets or "/" not in rel:
        files.append({"legacy": rel, "sha256": digest, "target": None, "note": "fuera de las fuentes: queda solo en el legado"})
        continue
    got = new.get(rel)
    files.append({"legacy": rel, "sha256": digest, "target": f"{targets[src]}:{rel.split('/', 1)[1]}", "target_sha256": got})
    if got != digest:
        errors.append(rel)
json.dump({"migrated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
           "legacy_volume": legacy, "legacy_mounted": "ro", "targets": targets,
           "files": files, "mismatches": errors, "ok": not errors}, open(out, "w"), indent=2, ensure_ascii=False)
print(f"[migrate] manifiesto {out}: {len(files)} ficheros, {len(errors)} discrepancias")
sys.exit(1 if errors else 0)
PY
echo "[migrate] listo. El legado $LEGACY_VOL queda intacto; vuelta atrás en docs/lab-containment.md §Migración."
