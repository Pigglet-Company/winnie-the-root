"""Construcción de eventos en el ESQUEMA COMÚN (contrato, punto 6).

Este módulo NO clasifica ataques (attack_type, MITRE...): eso lo hace el módulo C.
Solo registra lo observado.
"""
from __future__ import annotations

import ipaddress
import uuid
from datetime import datetime, timezone
from typing import Any, Iterable
from urllib.parse import unquote_plus

HONEYPOT = "web"
SERVICE = "http"
EVENT_TYPES = ("request", "auth_attempt", "file_upload")  # los que emite este módulo

MAX_HEADERS = 64
MAX_HEADER_VALUE = 1024
MAX_PATH = 2048
MAX_QUERY = 4096
MAX_AUTH_FIELD = 512


def utc_timestamp(now: datetime | None = None) -> str:
    """ISO 8601 UTC con milisegundos y sufijo Z: 2026-11-23T10:15:30.123Z."""
    now = now or datetime.now(timezone.utc)
    return now.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def normalize_ip(value: str | None) -> str | None:
    """Devuelve la IP normalizada (IPv4-mapeada -> IPv4) o None si no es una IP válida."""
    if not value:
        return None
    try:
        ip = ipaddress.ip_address(value.strip())
    except ValueError:
        return None
    if ip.version == 6 and ip.ipv4_mapped is not None:
        ip = ip.ipv4_mapped
    return str(ip)


def clean_headers(raw: Iterable[tuple[bytes, bytes]]) -> dict[str, str]:
    """Cabeceras con clave en minúsculas; duplicadas unidas con ', '; valores acotados."""
    out: dict[str, str] = {}
    for name_b, value_b in raw:
        name = name_b.decode("latin-1").lower()
        value = value_b.decode("latin-1")[:MAX_HEADER_VALUE]
        if name in out:
            out[name] = (out[name] + ", " + value)[:MAX_HEADER_VALUE]
        elif len(out) < MAX_HEADERS:
            out[name] = value
    return out


def decode_query(raw_query: bytes | str) -> str:
    """Query string decodificada (una vez) y acotada. Ej.: q=1' OR 1=1--"""
    if isinstance(raw_query, bytes):
        raw_query = raw_query.decode("latin-1")
    return unquote_plus(raw_query, errors="replace")[:MAX_QUERY]


def body_to_text(body: bytes, limit: int) -> str | None:
    """Body truncado a `limit` BYTES y decodificado de forma tolerante."""
    if not body:
        return None
    return body[:limit].decode("utf-8", errors="replace")


def build_event(
    *,
    now: datetime | None,
    src_ip: str | None,
    src_port: int | None,
    dst_port: int | None,
    method: str,
    path: str,
    query: str,
    headers: dict[str, str],
    body: bytes,
    status: int | None,
    body_limit: int = 8 * 1024,
    event_type: str = "request",
    session_id: str | None = None,
    auth: dict[str, Any] | None = None,
    file: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Crea un evento del esquema común. Los campos no aplicables van a null/ausentes."""
    event: dict[str, Any] = {
        "@timestamp": utc_timestamp(now),
        "event_id": str(uuid.uuid4()),
        "honeypot": HONEYPOT,
        "service": SERVICE,
        "event_type": event_type,
        "src_ip": src_ip,
        "src_port": src_port,
        "dst_port": dst_port,
        "session_id": session_id,
    }
    if auth is not None:
        event["auth"] = {
            "username": _cut(auth.get("username")),
            "password": _cut(auth.get("password")),
            "success": bool(auth.get("success", False)),
        }
    event["http"] = {
        "method": method,
        "path": path[:MAX_PATH],
        "query": query or None,
        "headers": headers,
        "body": body_to_text(body, body_limit),
        "user_agent": headers.get("user-agent"),
        "status": status,
    }
    if file is not None:
        event["file"] = {
            "name": file.get("name"),
            "sha256": file.get("sha256"),
            "size": file.get("size"),
            "url": file.get("url"),
        }
    return event


def _cut(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)[:MAX_AUTH_FIELD]
