"""Middleware ASGI puro: registra CADA petición en el esquema común y protege al honeypot.

Orden de trabajo por petición:
  1. Determina la IP de origen (socket; X-Forwarded-For solo si TRUST_PROXY=true).
  2. Rate limit por IP  -> 429.
  3. Límite de tamaño de body (Content-Length y bytes reales) -> 413; timeout de lectura -> 408.
  4. Reenvía la petición a la app (con timeout total) y captura el status de la respuesta.
  5. Fuerza las cabeceras Server / X-Powered-By "creíbles".
  6. En `finally` escribe SIEMPRE el evento (aunque haya error, timeout o cancelación).

Las rutas pueden enriquecer el evento escribiendo en scope["hp_extra"]:
  event_type ("auth_attempt" | "file_upload"), auth {...}, file {...}, session_id.
"""
from __future__ import annotations

import asyncio
import sys
import traceback
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable

from . import events, pages
from .config import Settings
from .event_logger import EventLogger
from .ratelimit import RateLimiter
from .sessions import SessionStore

Scope = dict[str, Any]
Message = dict[str, Any]
Receive = Callable[[], Awaitable[Message]]
Send = Callable[[Message], Awaitable[None]]
ASGIApp = Callable[[Scope, Receive, Send], Awaitable[None]]

UPLOAD_PATHS = {"/upload", "/upload.php"}
SESSION_COOKIE = "PHPSESSID"


def resolve_source(
    client: Any, headers: dict[str, str], trust_proxy: bool
) -> tuple[str | None, int | None]:
    """IP/puerto de origen. Solo con TRUST_PROXY=true se mira X-Forwarded-For y entonces se usa la
    ÚLTIMA entrada (la que añade nuestro proxy de confianza; las anteriores las controla el cliente)."""
    ip = port = None
    if client:
        ip = events.normalize_ip(str(client[0]))
        if ip is not None and len(client) > 1:
            port = client[1]
    if trust_proxy:
        xff = headers.get("x-forwarded-for")
        if xff:
            candidate = events.normalize_ip(xff.split(",")[-1])
            if candidate:
                return candidate, None  # el puerto del socket sería el del proxy
    return ip, port


def _cookie_value(headers: dict[str, str], name: str) -> str | None:
    for part in headers.get("cookie", "").split(";"):
        key, _, value = part.strip().partition("=")
        if key == name and 0 < len(value) <= 64 and value.isalnum():
            return value
    return None


class HoneypotMiddleware:
    def __init__(
        self,
        app: ASGIApp,
        *,
        settings: Settings,
        event_logger: EventLogger,
        limiter: RateLimiter,
        sessions: SessionStore,
    ) -> None:
        self.app = app
        self.settings = settings
        self.events = event_logger
        self.limiter = limiter
        self.sessions = sessions

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":  # lifespan (y websocket, desactivado con --ws none)
            await self.app(scope, receive, send)
            return

        s = self.settings
        started = datetime.now(timezone.utc)
        headers = events.clean_headers(scope.get("headers", []))
        src_ip, src_port = resolve_source(scope.get("client"), headers, s.trust_proxy)
        server = scope.get("server")
        dst_port = server[1] if server and len(server) > 1 else None
        method = scope.get("method", "GET")
        path = scope.get("path", "/")
        query = events.decode_query(scope.get("query_string", b""))
        host = headers.get("host", "")

        extras: dict[str, Any] = {}
        scope["hp_extra"] = extras
        sid = _cookie_value(headers, SESSION_COOKIE)
        if self.sessions.is_valid(sid):
            extras["session_id"] = sid

        status: int | None = None
        body = b""

        async def send_wrapper(message: Message) -> None:
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
                hdrs = [
                    (k, v)
                    for k, v in message.get("headers", [])
                    if k.lower() not in (b"server", b"x-powered-by")
                ]
                hdrs.append((b"server", s.server_header.encode("latin-1", "replace")))
                if s.powered_by:
                    hdrs.append((b"x-powered-by", s.powered_by.encode("latin-1", "replace")))
                message = {**message, "headers": hdrs}
            await send(message)

        async def early_error(code: int, extra: list[tuple[bytes, bytes]] | None = None) -> None:
            page = pages.apache_error(code, path, method, host, s.server_header).encode("utf-8")
            hdrs = [
                (b"content-type", b"text/html; charset=iso-8859-1"),
                (b"content-length", str(len(page)).encode()),
                (b"connection", b"close"),
                *(extra or []),
            ]
            await send_wrapper({"type": "http.response.start", "status": code, "headers": hdrs})
            await send_wrapper(
                {"type": "http.response.body", "body": b"" if method == "HEAD" else page}
            )

        try:
            # --- 2. rate limit -------------------------------------------------------------
            if not self.limiter.allow(src_ip or "unknown"):
                await early_error(429, [(b"retry-after", str(self.limiter.retry_after()).encode())])
                return

            # --- 3. límite de body ---------------------------------------------------------
            limit = s.upload_body_limit if path in UPLOAD_PATHS else s.max_body_bytes
            declared = headers.get("content-length", "")
            if declared.isdigit() and int(declared) > limit:
                await early_error(413)
                return

            chunks: list[bytes] = []
            total = 0
            more = True
            while more:
                try:
                    message = await asyncio.wait_for(receive(), timeout=s.body_read_timeout_s)
                except asyncio.TimeoutError:
                    await early_error(408)
                    return
                if message["type"] == "http.disconnect":
                    return
                chunk = message.get("body", b"")
                total += len(chunk)
                if total > limit:
                    await early_error(413)
                    return
                chunks.append(chunk)
                more = bool(message.get("more_body", False))
            body = b"".join(chunks)

            # --- 4. app con timeout total --------------------------------------------------
            replayed = False

            async def replay() -> Message:
                nonlocal replayed
                if not replayed:
                    replayed = True
                    return {"type": "http.request", "body": body, "more_body": False}
                return await receive()  # tras el body, lo siguiente es http.disconnect

            try:
                async with asyncio.timeout(s.request_timeout_s):
                    await self.app(scope, replay, send_wrapper)
            except TimeoutError:
                if status is None:
                    await early_error(504)
            except Exception:
                traceback.print_exc(file=sys.stderr)
                if status is None:
                    await early_error(500)
                else:
                    raise
        finally:
            self._emit(
                started, src_ip, src_port, dst_port, method, path, query, headers, body, status, extras
            )

    def _emit(
        self,
        now: datetime,
        src_ip: str | None,
        src_port: int | None,
        dst_port: int | None,
        method: str,
        path: str,
        query: str,
        headers: dict[str, str],
        body: bytes,
        status: int | None,
        extras: dict[str, Any],
    ) -> None:
        """Escribe el evento. Un fallo aquí se informa por stderr pero NUNCA tumba la petición."""
        try:
            event = events.build_event(
                now=now,
                src_ip=src_ip,
                src_port=src_port,
                dst_port=dst_port,
                method=method,
                path=path,
                query=query,
                headers=headers,
                body=body,
                status=status,
                body_limit=self.settings.log_body_max_bytes,
                event_type=extras.get("event_type", "request"),
                session_id=extras.get("session_id"),
                auth=extras.get("auth"),
                file=extras.get("file"),
            )
            self.events.log(event)
        except Exception as exc:
            print(f"[middleware] no se pudo generar el evento: {exc!r}", file=sys.stderr)
