#!/usr/bin/env python3
"""Exporta eventos de OpenSearch a NDJSON o CSV para el informe (Python 3.12, solo stdlib).

OpenSearch no se publica en el host, así que se consulta con `docker exec pl-opensearch curl`.

Ejemplos:
    python3 tools/export_events.py --format csv --since 7d --out export-7d.csv
    python3 tools/export_events.py --format ndjson --query 'attack_type:sqli' --out export-sqli.ndjson
"""
from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterator

ROOT = Path(__file__).resolve().parent.parent
COLUMNS = ["@timestamp", "event_id", "honeypot", "service", "event_type", "src_ip", "src_port", "dst_port",
           "session_id", "auth.username", "auth.password", "auth.success", "command", "http.method", "http.path",
           "http.query", "http.user_agent", "http.status", "file.name", "file.sha256", "file.url", "duration_s",
           "geo.country_iso", "geo.country_name", "geo.city", "attack_type", "mitre_technique", "mitre_tactic"]


def env_value(key: str) -> str:
    f = ROOT / ".env"
    if f.exists():
        for line in reversed(f.read_text().splitlines()):
            if line.startswith(f"{key}="):
                return line.split("=", 1)[1]
    return ""


def os_call(method: str, path: str, body: dict[str, Any]) -> dict[str, Any]:
    prod = (env_value("SECURITY_MODE") or "dev") == "prod"
    cmd = ["docker", "exec", "-i", "pl-opensearch", "curl", "-sk"]
    if prod:
        cmd += ["-u", f"admin:{env_value('OPENSEARCH_ADMIN_PASSWORD')}"]
    cmd += ["-H", "Content-Type: application/json", "-X", method,
            f"{'https' if prod else 'http'}://localhost:9200{path}", "--data-binary", "@-"]
    res = subprocess.run(cmd, input=json.dumps(body).encode(), capture_output=True, check=True)
    return json.loads(res.stdout)


def scan(query: str, since: str | None) -> Iterator[dict[str, Any]]:
    must: list[dict[str, Any]] = []
    if query:
        must.append({"query_string": {"query": query}})
    if since:
        must.append({"range": {"@timestamp": {"gte": f"now-{since}"}}})
    body = {"size": 1000, "sort": ["_doc"], "query": {"bool": {"must": must or [{"match_all": {}}]}}}
    page = os_call("POST", "/honeypot-events/_search?scroll=2m", body)
    while page.get("hits", {}).get("hits"):
        for hit in page["hits"]["hits"]:
            yield hit["_source"]
        page = os_call("POST", "/_search/scroll", {"scroll": "2m", "scroll_id": page["_scroll_id"]})


def flat(src: dict[str, Any], col: str) -> Any:
    cur: Any = src
    for part in col.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return ""
        cur = cur[part]
    return cur


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--format", choices=["csv", "ndjson"], default="ndjson")
    ap.add_argument("--since", help="ventana relativa, p. ej. 7d, 24h")
    ap.add_argument("--query", default="", help="Lucene query_string, p. ej. 'attack_type:sqli AND service:http'")
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()

    n = 0
    with a.out.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh) if a.format == "csv" else None
        if writer:
            writer.writerow(COLUMNS)
        for src in scan(a.query, a.since):
            if writer:
                writer.writerow([flat(src, c) for c in COLUMNS])
            else:
                fh.write(json.dumps(src, ensure_ascii=False) + "\n")
            n += 1
    print(f"{n} eventos exportados a {a.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
