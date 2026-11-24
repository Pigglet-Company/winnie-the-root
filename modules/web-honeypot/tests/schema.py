"""Validador del esquema común (contrato, punto 6) para los eventos del módulo B."""
from __future__ import annotations

import ipaddress
import re
import uuid
from typing import Any

TS_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$")
EVENT_TYPES = {"request", "auth_attempt", "file_upload"}
ALLOWED_TOP = {
    "@timestamp", "event_id", "honeypot", "service", "event_type", "src_ip", "src_port", "dst_port",
    "session_id", "auth", "command", "http", "file", "duration_s", "raw",
}
FORBIDDEN_TOP = {"attack_type", "mitre_technique", "mitre_tactic", "geo"}  # los añade el módulo C


def validate_event(ev: dict[str, Any]) -> list[str]:
    """Devuelve la lista de problemas (vacía = evento válido)."""
    errs: list[str] = []
    if not isinstance(ev.get("@timestamp"), str) or not TS_RE.match(ev["@timestamp"]):
        errs.append("@timestamp inválido")
    try:
        if uuid.UUID(str(ev.get("event_id"))).version != 4:
            errs.append("event_id no es uuid4")
    except ValueError:
        errs.append("event_id no es uuid")
    if ev.get("honeypot") != "web":
        errs.append("honeypot != web")
    if ev.get("service") != "http":
        errs.append("service != http")
    if ev.get("event_type") not in EVENT_TYPES:
        errs.append("event_type inválido")
    try:
        ipaddress.ip_address(ev.get("src_ip"))
    except ValueError:
        errs.append("src_ip inválida")
    if "src_port" not in ev or not (ev["src_port"] is None or isinstance(ev["src_port"], int)):
        errs.append("src_port inválido")
    if not isinstance(ev.get("dst_port"), int):
        errs.append("dst_port inválido")
    if not (ev.get("session_id") is None or isinstance(ev["session_id"], str)):
        errs.append("session_id inválido")
    http = ev.get("http")
    if not isinstance(http, dict):
        errs.append("falta http")
    else:
        for key, typ in (("method", str), ("path", str), ("headers", dict)):
            if not isinstance(http.get(key), typ):
                errs.append(f"http.{key} inválido")
        if not isinstance(http.get("status"), int):
            errs.append("http.status inválido")
        body = http.get("body")
        if body is not None and len(body.encode("utf-8")) > 8 * 1024 + 4:
            errs.append("http.body > 8 KB")
    if ev.get("event_type") == "auth_attempt":
        auth = ev.get("auth")
        if not isinstance(auth, dict) or not isinstance(auth.get("success"), bool):
            errs.append("auth inválido")
    if ev.get("event_type") == "file_upload":
        f = ev.get("file")
        if not isinstance(f, dict) or not f.get("name"):
            errs.append("file inválido")
    errs += [f"campo no permitido: {k}" for k in ev if k not in ALLOWED_TOP]
    errs += [f"campo reservado a C: {k}" for k in ev if k in FORBIDDEN_TOP]
    return errs
