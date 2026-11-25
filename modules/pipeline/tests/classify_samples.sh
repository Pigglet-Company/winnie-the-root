#!/usr/bin/env bash
# tests/classify_samples.sh - baseline legacy de clasificación sobre las muestras de los paneles.
#   tests/classify_samples.sh           clasifica sample-logs/ y compara con vector/baseline/
#   tests/classify_samples.sh --write   reescribe el baseline de la versión de regla actual
# Ejecuta la configuración real (vector.yaml + final_nogeo.yaml) con un sink de fichero en vez de
# OpenSearch. El baseline fija el sha256 de cada muestra, los recuentos por attack_type, la
# técnica MITRE de cada tipo y las reglas que deciden. Docker (imagen fijada) o VECTOR_BIN=<binario>.
set -euo pipefail
cd "$(dirname "$0")/.."
IMAGE="timberio/vector:0.43.1-debian"   # misma versión que compose.yml
TIMEOUT="${CLASSIFY_TIMEOUT:-180}"

version="$(sed -n 's/^RULES_VERSION = "\(.*\)"$/\1/p' vector/rules/classify.vrl)"
version="${version:-1.0.0}"             # 1.0.0 = revisión previa, sin rule.version
baseline="vector/baseline/winnie-legacy-$version.json"
expected="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["expected_indexed"])' sample-logs/manifest.json)"

W="$(mktemp -d)"; chmod 755 "$W"
cleanup() { [ -n "${cid:-}" ] && docker rm -f "$cid" >/dev/null 2>&1; [ -n "${pid:-}" ] && kill "$pid" 2>/dev/null; rm -rf "${W:?}"; }
trap cleanup EXIT
mkdir -p "$W/data" "$W/out"
cp -r vector "$W/vector"; cp -r sample-logs "$W/logs"
sed -n '/^sinks:/q;p' vector/vector.yaml > "$W/vector/vector.yaml"
cat >> "$W/vector/vector.yaml" <<EOF
sinks:
  events:
    type: file
    inputs: [final]
    path: $W/out/events.jsonl
    encoding: { codec: json }
  dropped:
    type: file
    inputs: [norm_cowrie.dropped, norm_opencanary.dropped, norm_web.dropped, classify.dropped]
    path: $W/out/dropped.jsonl
    encoding: { codec: json }
EOF
grep -rl '/etc/vector\|/var/lib/vector\|"/logs/' "$W/vector" | xargs sed -i.bak \
  -e "s#/etc/vector#$W/vector#g" -e "s#/var/lib/vector#$W/data#g" -e "s#\"/logs/#\"$W/logs/#g"
find "$W/vector" -name '*.bak' -delete
chmod -R a+rwX "$W"

args=(--quiet --config "$W/vector/vector.yaml" --config "$W/vector/final_nogeo.yaml")
if [ -n "${VECTOR_BIN:-}" ]; then
  "$VECTOR_BIN" "${args[@]}" &
  pid=$!
else
  # Con el usuario del host: así los checkpoints que escribe Vector se pueden borrar al limpiar.
  cid="$(docker run -d --user "$(id -u):$(id -g)" -v "$W:$W" --entrypoint vector "$IMAGE" "${args[@]}")"
fi

count() { cat "$W"/out/events.jsonl 2>/dev/null | wc -l | tr -d ' '; }
for _ in $(seq "$TIMEOUT"); do
  [ "$(count)" -ge "$expected" ] && break
  sleep 1
done
sleep 2   # deja terminar el último lote antes de resumir
[ "$(count)" -ge "$expected" ] || { echo "ERROR: $(count)/$expected eventos clasificados en ${TIMEOUT}s"; exit 1; }

summary="$W/summary.json"
python3 - "$W/out" sample-logs "$version" > "$summary" <<'PY'
import collections, hashlib, json, pathlib, sys
out, samples, version = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2]), sys.argv[3]
events = [json.loads(line) for line in (out / "events.jsonl").read_text().splitlines()]
dropped = out / "dropped.jsonl"
by_type, by_rule, mitre = collections.Counter(), collections.Counter(), collections.defaultdict(set)
by_honeypot = collections.defaultdict(collections.Counter)
overlaps = collections.Counter()
for e in events:
    at = e["attack_type"]
    by_type[at] += 1
    by_honeypot[e["honeypot"]][at] += 1
    mitre[at].add(f'{e.get("mitre_technique", "-")} {e.get("mitre_tactic", "-")}')
    rule = e.get("rule", {})
    by_rule[rule.get("id", "-")] += 1
    if len(rule.get("matches", [])) > 1:
        overlaps[" + ".join(rule["matches"])] += 1
print(json.dumps({
    "ruleset": "winnie-legacy",
    "rule_version": version,
    "fixtures": {str(p.relative_to(samples)): hashlib.sha256(p.read_bytes()).hexdigest()
                 for p in sorted(samples.rglob("*")) if p.is_file()},
    "events": len(events),
    "dropped": len(dropped.read_text().splitlines()) if dropped.exists() else 0,
    "attack_type": dict(sorted(by_type.items())),
    "attack_type_by_honeypot": {h: dict(sorted(c.items())) for h, c in sorted(by_honeypot.items())},
    "mitre_by_attack_type": {k: sorted(v) for k, v in sorted(mitre.items())},
    "rule_id": dict(sorted(by_rule.items())),
    "overlaps": dict(sorted(overlaps.items())),
}, indent=2, ensure_ascii=False))
PY

if [ "${1:-}" = "--write" ]; then
  mkdir -p vector/baseline; cp "$summary" "$baseline"; echo "baseline escrito: $baseline"; exit 0
fi
[ -f "$baseline" ] || { echo "ERROR: falta $baseline (ejecuta con --write y revisa el diff)"; exit 1; }
if diff -u "$baseline" "$summary"; then
  echo "OK: clasificación de las muestras = $baseline ($(count) eventos)"
else
  echo "ERROR: la clasificación difiere del baseline $baseline (arriba, el diff)"; exit 1
fi
