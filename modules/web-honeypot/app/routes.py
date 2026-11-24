"""Rutas señuelo. TODO es SIMULADO: no se ejecuta input del atacante ni se leen ficheros reales.

Las rutas no escriben logs: solo anotan datos en scope["hp_extra"] (auth, file, event_type,
session_id) y el middleware emite el evento final. Este módulo NO clasifica ataques.
"""
from __future__ import annotations

import asyncio
import base64
import binascii
import hashlib
import hmac
import os
import re
import secrets
import sys
from typing import Any, Callable

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse, Response
from starlette.datastructures import UploadFile

from . import pages
from .config import Settings
from .middleware import SESSION_COOKIE
from .sim import cmd, lfi, sql

router = APIRouter()

GET_HEAD = ("GET", "HEAD")
GET_HEAD_POST = ("GET", "HEAD", "POST")

USER_KEYS = ("username", "user", "login", "log", "user_name", "uname", "email", "usr", "pma_username", "j_username")
PASS_KEYS = ("password", "pass", "pwd", "passwd", "pma_password", "j_password", "secret")


def route(*paths: str, methods: tuple[str, ...] = GET_HEAD) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Registra el mismo handler en varias rutas (alias típicos de escáner)."""

    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        for p in paths:
            router.add_api_route(p, fn, methods=list(methods), include_in_schema=False, response_model=None)
        return fn

    return decorator


# --------------------------------------------------------------------------- utilidades
def _settings(request: Request) -> Settings:
    return request.app.state.settings  # type: ignore[no-any-return]


def _extras(request: Request) -> dict[str, Any]:
    return request.scope.setdefault("hp_extra", {})  # type: ignore[no-any-return]


def html(content: str, status: int = 200, headers: dict[str, str] | None = None) -> HTMLResponse:
    return HTMLResponse(content, status_code=status, headers=headers)


async def read_fields(request: Request) -> dict[str, str]:
    """Parámetros de query + body (form o JSON) como dict de str. Tolerante a body malformado."""
    cached = request.scope.get("hp_fields")
    if cached is not None:
        return cached  # type: ignore[no-any-return]
    fields: dict[str, str] = {}
    ctype = request.headers.get("content-type", "").lower()
    try:
        if ctype.startswith(("application/x-www-form-urlencoded", "multipart/form-data")):
            form = await request.form()
            for key, value in form.multi_items():
                if isinstance(value, str):
                    fields.setdefault(key, value)
        elif "json" in ctype:
            payload = await request.json()
            if isinstance(payload, dict):
                for key, value in payload.items():
                    if isinstance(value, (str, int, float)):
                        fields.setdefault(str(key), str(value))
    except Exception:
        pass  # body malformado: se trata como vacío (ya queda registrado en el log)
    for key, value in request.query_params.items():
        fields.setdefault(key, value)
    request.scope["hp_fields"] = fields
    return fields


def _pick(fields: dict[str, str], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        if key in fields:
            return fields[key]
    return None


def _basic_auth(request: Request) -> tuple[str, str] | None:
    header = request.headers.get("authorization", "")
    if header.lower().startswith("basic "):
        try:
            raw = base64.b64decode(header[6:].strip(), validate=False).decode("utf-8", "replace")
        except (binascii.Error, ValueError):
            return None
        user, _, pwd = raw.partition(":")
        return user, pwd
    return None


def _weak_ok(settings: Settings, username: str | None, password: str | None) -> bool:
    if not settings.weak_pass or username is None or password is None:
        return False
    return hmac.compare_digest(username.encode(), settings.weak_user.encode()) and hmac.compare_digest(
        password.encode(), settings.weak_pass.encode()
    )


# --------------------------------------------------------------------------- inicio y logins
@route("/", "/index.php", "/index.html")
async def home(request: Request) -> Response:
    return html(pages.home_page())


_RENDER = {
    "login": lambda err, user: pages.login_page("Usuario o contrasena incorrectos." if err else None, user),
    "admin": lambda err, user: pages.admin_page("Credenciales no validas." if err else None, user),
    "wp": lambda err, user: pages.wp_login_page(
        ("bad_password" if user.lower() in ("admin", "administrator", "editor") else "bad_user") if err else None,
        user,
    ),
    "pma": lambda err, user: pages.pma_login_page("error" if err else None, user),
}


async def _login(request: Request, kind: str) -> Response:
    settings = _settings(request)
    fields = await read_fields(request)
    username, password = _pick(fields, USER_KEYS), _pick(fields, PASS_KEYS)
    via_basic = False
    if username is None and password is None:
        basic = _basic_auth(request)
        if basic:
            username, password, via_basic = basic[0], basic[1], True

    if username is None and password is None:  # GET normal o POST sin credenciales
        return html(_RENDER[kind](False, ""))

    success = _weak_ok(settings, username, password)
    extras = _extras(request)
    extras["event_type"] = "auth_attempt"
    extras["auth"] = {"username": username, "password": password, "success": success}

    if success:
        sid = request.app.state.sessions.create()
        extras["session_id"] = sid
        resp = RedirectResponse("/panel", status_code=302)
        resp.set_cookie(SESSION_COOKIE, sid, httponly=True, path="/")
        return resp
    if via_basic:
        return html(
            pages.apache_error(401, request.url.path, request.method, request.headers.get("host", ""), settings.server_header),
            401,
            {"WWW-Authenticate": 'Basic realm="Intranet Admin"'},
        )
    return html(_RENDER[kind](True, (username or "")[:100]))


@route("/login", "/login.php", methods=GET_HEAD_POST)
async def login(request: Request) -> Response:
    return await _login(request, "login")


@route("/admin", "/admin/", "/admin/login.php", "/administrator", methods=GET_HEAD_POST)
async def admin(request: Request) -> Response:
    return await _login(request, "admin")


@route("/wp-login.php", methods=GET_HEAD_POST)
async def wp_login(request: Request) -> Response:
    return await _login(request, "wp")


@route("/phpmyadmin", "/phpmyadmin/", "/phpmyadmin/index.php", "/pma/", methods=GET_HEAD_POST)
async def phpmyadmin(request: Request) -> Response:
    return await _login(request, "pma")


@route("/panel", "/panel/", "/dashboard")
async def panel(request: Request) -> Response:
    if request.app.state.sessions.is_valid(request.cookies.get(SESSION_COOKIE)):
        return html(pages.panel_page())
    return RedirectResponse("/login", status_code=302)


@route("/logout")
async def logout(request: Request) -> Response:
    request.app.state.sessions.delete(request.cookies.get(SESSION_COOKIE))
    resp = RedirectResponse("/login", status_code=302)
    resp.delete_cookie(SESSION_COOKIE, path="/")
    return resp


# --------------------------------------------------------------------------- SQL injection
@route("/search", "/search.php", methods=GET_HEAD_POST)
async def search(request: Request) -> Response:
    fields = await read_fields(request)
    if "q" not in fields:
        return html(pages.search_page(None, None))
    q = fields["q"][: sql.MAX_Q]
    result = sql.simulate(q, _settings(request).sleep_cap_s)
    if result.delay_s > 0:
        await asyncio.sleep(result.delay_s)  # SLEEP() simulado y acotado
    return html(pages.search_page(q, result))


# --------------------------------------------------------------------------- LFI / path traversal
@route("/view", "/view.php", methods=GET_HEAD_POST)
async def view(request: Request) -> Response:
    fields = await read_fields(request)
    file = fields.get("file", "")
    if not file:
        return html(pages.view_page(None, None))
    file = file[:1024]
    return html(pages.view_page(file, lfi.resolve(file)))  # solo diccionario en memoria


# --------------------------------------------------------------------------- command injection
@route("/ping", "/ping.php", methods=GET_HEAD_POST)
async def ping(request: Request) -> Response:
    fields = await read_fields(request)
    if "host" not in fields:
        return html(pages.ping_page(None, None))
    host = fields["host"][:512]
    return html(pages.ping_page(host, cmd.simulate_ping(host)))  # NO se ejecuta nada


# --------------------------------------------------------------------------- XSS reflejado
@route("/comment", "/comment.php", methods=GET_HEAD_POST)
async def comment(request: Request) -> Response:
    """Refleja name/comment sin escapar SOLO en la respuesta al propio solicitante (no se guardan)."""
    settings = _settings(request)
    fields = await read_fields(request)
    name = fields.get("name", "")[:500]
    text = fields.get("comment")
    text = text[:5000] if text is not None else None
    headers = {"X-XSS-Protection": "0", "Cache-Control": "no-store"}
    if settings.comment_csp:
        headers["Content-Security-Policy"] = settings.comment_csp
    return html(pages.comment_page(name, text), headers=headers)


# --------------------------------------------------------------------------- subida de ficheros
def _upload_usage(directory: str) -> tuple[int, int]:
    count = total = 0
    with os.scandir(directory) as it:
        for entry in it:
            if entry.is_file(follow_symlinks=False):
                count += 1
                total += entry.stat(follow_symlinks=False).st_size
    return count, total


def _store(settings: Settings, data: bytes) -> bool:
    """Guarda el fichero con nombre aleatorio y permisos 0640 (sin ejecución). Devuelve si se guardó."""
    try:
        os.makedirs(settings.upload_dir, exist_ok=True)
        count, total = _upload_usage(settings.upload_dir)
        if count >= settings.upload_max_files or total + len(data) > settings.upload_max_total_bytes:
            return False  # volumen "lleno": se finge éxito pero no se guarda (ya queda sha256 en el log)
        path = os.path.join(settings.upload_dir, secrets.token_hex(16))
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o640)
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
        return True
    except OSError as exc:
        print(f"[upload] no se pudo guardar el fichero: {exc}", file=sys.stderr)
        return False


@route("/upload", "/upload.php", methods=GET_HEAD_POST)
async def upload(request: Request) -> Response:
    settings = _settings(request)
    if request.method != "POST":
        return html(pages.upload_page())

    try:
        form = await request.form()
    except Exception:
        return html(pages.upload_page("Peticion no valida.", error=True), 400)
    try:
        item = next(
            (v for _, v in form.multi_items() if isinstance(v, UploadFile) and v.filename),
            None,
        )
        if item is None:
            return html(pages.upload_page("No se ha seleccionado ningun fichero.", error=True), 400)

        name = item.filename[:255]
        data = await item.read(settings.max_upload_bytes + 1)
        extras = _extras(request)
        extras["event_type"] = "file_upload"
        if len(data) > settings.max_upload_bytes:
            extras["file"] = {"name": name, "sha256": None, "size": None, "url": None}
            return html(
                pages.apache_error(413, request.url.path, "POST", request.headers.get("host", ""), settings.server_header),
                413,
            )
        extras["file"] = {"name": name, "sha256": hashlib.sha256(data).hexdigest(), "size": len(data), "url": None}
        _store(settings, data)  # nombre aleatorio; nunca se sirve
        safe = re.sub(r"[^A-Za-z0-9._-]", "_", os.path.basename(name.replace("\\", "/")))[:64] or "file"
        fake_url = f"/uploads/{secrets.token_hex(6)}/{safe}"  # URL FALSA: no existe ruta que la sirva
        return html(pages.upload_page("Fichero subido correctamente:", url=fake_url))
    finally:
        await form.close()


# --------------------------------------------------------------------------- descuidos de escáner
@route("/robots.txt")
async def robots(request: Request) -> Response:
    return PlainTextResponse(pages.ROBOTS_TXT)


@route("/.env")
async def dotenv(request: Request) -> Response:
    return PlainTextResponse(pages.FAKE_ENV)


@route("/.git/config")
async def git_config(request: Request) -> Response:
    return PlainTextResponse(pages.FAKE_GIT_CONFIG)


@route("/.git/HEAD")
async def git_head(request: Request) -> Response:
    return PlainTextResponse("ref: refs/heads/main\n")


@route("/backup.zip")
async def backup_zip(request: Request) -> Response:
    return Response(pages.EMPTY_ZIP, media_type="application/zip")


@route("/server-status", "/server-status/")
async def server_status(request: Request) -> Response:
    return html(pages.server_status_page(_settings(request).server_header, request.headers.get("host", "")))
