#!/usr/bin/env python3
"""scripts/evidence.py - integrity manifest and retention of lab captures (evidence and IOCs).

  ./scripts/evidence.py manifest              hash every capture, compare with the previous manifest
  ./scripts/evidence.py retention             list captures past their TTL (dry run)
  ./scripts/evidence.py retention --apply     delete them and record each deletion

Captures are the native logs (passwords, commands), Cowrie TTY logs, cowrie.log, Cowrie downloads and
web uploads (docs/design.md §10, «Gestión de las capturas de evidencia»). Volumes are mounted read-only,
except under `retention --apply`. Output lives in var/evidence/ (outside git):
  manifest-<UTC>.json   sha256, size, mtime and mode of each file; chained to the previous manifest
  deletions.ndjson      one line per expired file deleted (registro de borrados)
  holds.txt             per-case holds: "<store> <glob> # motivo", one per line; a match is never deleted
Exit 1 if a closed capture changed or vanished without a recorded deletion, a content-addressed file does
not match its name, or a capture is executable.
"""
import argparse
import datetime as dt
import fnmatch
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(os.environ.get("EVIDENCE_DIR", ROOT / "var" / "evidence"))
BUSYBOX = os.environ.get("BUSYBOX_IMAGE", "busybox:1.36.1")
TTL_DAYS = int(os.environ.get("EVIDENCE_TTL_DAYS", "90"))
SHA_NAME = re.compile(r"(^|/)[0-9a-f]{64}$")

# Private stores (not in SOURCE_VOLUMES): volume, files that are evidence, files still being written.
PRIVATE_STORES = {
    "cowrie-data": ("ssh-honeypot_cowrie-data",
                    ["lib/cowrie/tty/*", "lib/cowrie/downloads/*", "log/cowrie/cowrie.log*"],
                    ["log/cowrie/cowrie.log"]),
    "web-uploads": ("web-honeypot_hp_web_uploads", ["*"], []),
}
ACTIVE_LOG = {"cowrie": "cowrie.json", "opencanary": "opencanary.log", "web": "web.jsonl"}

# One line per file: hex(path) size mtime mode sha256. Hex keeps spaces and odd bytes intact; a name with
# a newline would split (stored names are random hex or sha256, so none has one).
LIST_SH = r"""cd /v && find . -type f | while IFS= read -r f; do
  p="${f#./}"; printf '%s %s %s\n' "$(printf '%s' "$p" | od -An -tx1 | tr -d ' \n')" \
    "$(stat -c '%s %Y %a' "$f")" "$(sha256sum "$f" | cut -d' ' -f1)"; done"""


def stores():
    """name -> (volume, evidence globs, active files). Source volumes come from scripts/lib/contract.sh."""
    out = subprocess.run(["bash", "-c", f'. "{ROOT}/scripts/lib/contract.sh"; echo "$SOURCE_VOLUMES"'],
                         capture_output=True, text=True, check=True).stdout.split()
    result = {}
    for spec in out:
        src, vol = spec.split(":")[:2]
        result[src] = (vol, ["*"], [ACTIVE_LOG[src]])
    result.update(PRIVATE_STORES)
    return result


def parse_listing(store, text, globs):
    files = {}
    for line in text.splitlines():
        parts = line.split()
        if len(parts) != 5:
            continue
        path = bytes.fromhex(parts[0]).decode("utf-8", "backslashreplace")
        if not any(fnmatch.fnmatchcase(path, g) for g in globs):
            continue
        files[f"{store}:{path}"] = {"store": store, "path": path, "size": int(parts[1]),
                                    "mtime": int(parts[2]), "mode": parts[3], "sha256": parts[4]}
    return files


CONTENT_ADDRESSED = ("lib/cowrie/tty/", "lib/cowrie/downloads/")   # Cowrie renames to sha256 on close
ROTATION = re.compile(r"\.\d+$")                                    # opencanary.log.1, web.jsonl.3…


def is_open(rec, active):
    """Still being written: the live log, or a TTY/download not yet renamed to its sha256."""
    if f'{rec["store"]}:{rec["path"]}' in active:
        return True
    return rec["path"].startswith(CONTENT_ADDRESSED) and not SHA_NAME.search(rec["path"])


def check(current, previous, deleted, active):
    """Issues for the current listing against the previous manifest.

    A closed capture may be renamed (numbered rotations shift), so it is followed by content: its
    sha256 must still exist in the same store, or appear in the deletion record. Only the oldest
    numbered rotation may drop out, because the producer discards it (noted, not an issue).
    """
    issues, notes = [], []
    hashes = {(r["store"], r["sha256"]) for r in current.values()}
    for key, rec in current.items():
        if int(rec["mode"], 8) & 0o111:
            issues.append({"key": key, "issue": "executable"})
        if SHA_NAME.search(rec["path"]) and os.path.basename(rec["path"]) != rec["sha256"]:
            issues.append({"key": key, "issue": "content does not match its sha256 name"})
    for key, old in previous.items():
        if is_open(old, active) or (old["store"], old["sha256"]) in hashes:
            continue
        if key in deleted or old["sha256"] in deleted:
            continue
        if ROTATION.search(old["path"]) and key not in current:
            notes.append({"key": key, "note": "rotated out by the producer"})
            continue
        now = current.get(key)
        issues.append({"key": key, "issue": "closed capture changed" if now else "missing without a recorded deletion",
                       "was": old["sha256"], "now": now["sha256"] if now else None})
    return issues, notes


def parse_holds(text):
    holds = []
    for line in text.splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            store, glob = line.split(None, 1)
            holds.append((store, glob.strip()))
    return holds


def expired(current, now_ts, ttl_days, holds, active):
    limit = now_ts - ttl_days * 86400
    return sorted(k for k, r in current.items()
                  if r["mtime"] < limit and not is_open(r, active)
                  and not any(r["store"] == s and fnmatch.fnmatchcase(r["path"], g) for s, g in holds))


def docker(args, **kw):
    return subprocess.run(["docker", "run", "--rm", "--network", "none", *args], check=True, **kw)


def collect():
    current, active, missing = {}, set(), []
    for name, (vol, globs, live) in stores().items():
        if subprocess.run(["docker", "volume", "inspect", vol], capture_output=True).returncode:
            missing.append(vol)
            continue
        listing = docker(["-v", f"{vol}:/v:ro", BUSYBOX, "sh", "-c", LIST_SH], capture_output=True, text=True).stdout
        current.update(parse_listing(name, listing, globs))
        active.update(f"{name}:{p}" for p in live)
    return current, active, missing


def previous_manifest():
    found = sorted(OUT.glob("manifest-*.json"))
    return found[-1] if found else None


def deleted_keys():
    path = OUT / "deletions.ndjson"
    if not path.exists():
        return set()
    rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    return {f'{d["store"]}:{d["path"]}' for d in rows} | {d["sha256"] for d in rows}


def cmd_manifest(_args):
    current, active, missing = collect()
    prev_path = previous_manifest()
    previous = {f'{f["store"]}:{f["path"]}': f for f in json.loads(prev_path.read_text())["files"]} if prev_path else {}
    issues, notes = check(current, previous, deleted_keys(), active)
    now = dt.datetime.now(dt.timezone.utc)
    OUT.mkdir(parents=True, exist_ok=True)
    out = OUT / f"manifest-{now:%Y%m%dT%H%M%SZ}.json"
    json.dump({"generated_at": now.isoformat(timespec="seconds"),
               "previous": prev_path.name if prev_path else None,
               "previous_sha256": hashlib.sha256(prev_path.read_bytes()).hexdigest() if prev_path else None,
               "missing_volumes": missing, "files": [current[k] for k in sorted(current)],
               "issues": issues, "notes": notes, "ok": not issues}, out.open("w"), indent=2, ensure_ascii=False)
    print(f"[evidence] {out}: {len(current)} ficheros, {len(issues)} incidencias")
    for i in issues:
        print(f"[evidence] INCIDENCIA {i['key']}: {i['issue']}", file=sys.stderr)
    return 1 if issues else 0


def cmd_retention(args):
    current, active, _ = collect()
    holds_file = OUT / "holds.txt"
    holds = parse_holds(holds_file.read_text()) if holds_file.exists() else []
    victims = expired(current, int(dt.datetime.now(dt.timezone.utc).timestamp()), args.ttl, holds, active)
    for k in victims:
        print(f"[retention] {'borro' if args.apply else 'caducado'} {k}")
    if not args.apply:
        print(f"[retention] {len(victims)} ficheros con más de {args.ttl} d (simulación; --apply para borrar)")
        return 0
    OUT.mkdir(parents=True, exist_ok=True)
    volumes = {name: spec[0] for name, spec in stores().items()}
    with (OUT / "deletions.ndjson").open("a") as log:
        for name in sorted({current[k]["store"] for k in victims}):
            paths = [current[k]["path"] for k in victims if current[k]["store"] == name]
            docker(["-i", "-v", f"{volumes[name]}:/v", BUSYBOX, "sh", "-c", "cd /v && xargs -0 rm -f --"],
                   input=b"\0".join(p.encode() for p in paths))
            stamp = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
            for k in (k for k in victims if current[k]["store"] == name):
                r = current[k]
                log.write(json.dumps({"deleted_at": stamp, "store": name, "path": r["path"],
                                      "sha256": r["sha256"], "reason": f"ttl {args.ttl} d"}) + "\n")
    print(f"[retention] {len(victims)} ficheros borrados y registrados en {OUT / 'deletions.ndjson'}")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("manifest")
    r = sub.add_parser("retention")
    r.add_argument("--apply", action="store_true")
    r.add_argument("--ttl", type=int, default=TTL_DAYS)
    args = ap.parse_args(argv)
    return {"manifest": cmd_manifest, "retention": cmd_retention}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
