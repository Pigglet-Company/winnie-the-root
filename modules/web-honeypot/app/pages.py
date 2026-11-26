"""Páginas HTML del señuelo (intranet ficticia "Nexora Industries") y errores estilo Apache.

Todo el HTML es autocontenido (sin recursos externos). El texto controlado por el visitante se
escapa SIEMPRE con esc(), salvo en comment_page(), que refleja XSS a propósito (ver ahí).
"""
from __future__ import annotations

import html
import random
import re
from http import HTTPStatus
from typing import Any

from .sim import data, lfi
from .sim.sql import SqlResult

SITE = "Nexora Industries"

_CSS = """
body{font-family:Arial,Helvetica,sans-serif;margin:0;background:#eef1f5;color:#222}
header{background:#0b3d6b;color:#fff;padding:14px 28px;font-size:20px;font-weight:bold}
nav{background:#08305a;padding:0 20px}
nav a{display:inline-block;color:#cfe2f5;padding:10px 14px;text-decoration:none;font-size:14px}
nav a.on,nav a:hover{background:#0b3d6b;color:#fff}
main{max-width:860px;margin:24px auto;background:#fff;padding:24px 32px;border:1px solid #d5dbe3}
h1{font-size:22px;margin-top:0;color:#0b3d6b}
table{border-collapse:collapse;width:100%;margin-top:12px}
th,td{border:1px solid #ccd3dc;padding:6px 10px;text-align:left;font-size:14px}
th{background:#e6ecf3}
input[type=text],input[type=password],textarea{width:100%;padding:8px;margin:4px 0 12px;box-sizing:border-box}
button,input[type=submit]{background:#0b3d6b;color:#fff;border:0;padding:9px 18px;cursor:pointer}
pre{background:#101820;color:#d8e6f2;padding:12px;overflow:auto;font-size:13px}
.err{background:#fdecea;border-left:4px solid #c62828;padding:8px 12px;margin:10px 0}
.ok{background:#e8f5e9;border-left:4px solid #2e7d32;padding:8px 12px;margin:10px 0}
footer{text-align:center;color:#778;font-size:12px;margin:18px 0}
"""

_NAV = (
    ("home", "/", "Inicio"),
    ("dir", "/search", "Directorio"),
    ("docs", "/view", "Documentos"),
    ("tools", "/ping", "Herramientas"),
    ("contact", "/comment", "Contacto"),
    ("upload", "/upload", "Subir ficheros"),
    ("login", "/login", "Acceso empleados"),
)


def esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def layout(title: str, body: str, active: str = "") -> str:
    links = []
    for key, href, label in _NAV:
        cls = ' class="on"' if key == active else ""
        links.append(f'<a href="{href}"{cls}>{label}</a>')
    return (
        '<!DOCTYPE html>\n<html lang="es"><head><meta charset="utf-8">'
        f"<title>{esc(title)} - {SITE}</title>"
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<style>{_CSS}</style></head><body>"
        f"<header>{SITE} &middot; Intranet</header><nav>{''.join(links)}</nav>"
        f"<main>{body}</main><footer>&copy; 2024 {SITE}. Uso interno. v2.3.1</footer>"
        "</body></html>\n"
    )


# --------------------------------------------------------------------------- errores Apache
_REASONS = {
    400: ("Bad Request", "Your browser sent a request that this server could not understand.<br />"),
    401: ("Unauthorized", "This server could not verify that you are authorized to access the document requested."),
    403: ("Forbidden", "You don't have permission to access this resource."),
    404: ("Not Found", "The requested URL {path} was not found on this server."),
    405: ("Method Not Allowed", "The requested method {method} is not allowed for this URL."),
    408: ("Request Timeout", "Server timeout waiting for the HTTP request from the client."),
    413: (
        "Request Entity Too Large",
        "The requested resource<br />{path}<br />does not allow request data with {method} "
        "requests, or the amount of data provided in the request exceeds the capacity limit.",
    ),
    429: ("Too Many Requests", "You have sent too many requests in a given amount of time."),
    500: (
        "Internal Server Error",
        "The server encountered an internal error or misconfiguration and was unable to complete your request.</p>"
        "<p>Please contact the server administrator at webmaster@localhost to inform them of the time this "
        "error occurred, and the actions you performed just before this error.</p>"
        "<p>More information about this error may be available in the server error log.",
    ),
    503: ("Service Unavailable", "The server is temporarily unable to service your request."),
    504: ("Gateway Timeout", "The gateway did not receive a timely response from the upstream server or application."),
}


def _phrase(status: int) -> str:
    try:
        return HTTPStatus(status).phrase
    except ValueError:
        return "Error"


def apache_error(status: int, path: str, method: str, host_header: str, server_header: str) -> str:
    """Página de error idéntica en forma a las de Apache 2.4 (404, 500...)."""
    title, msg = _REASONS.get(status) or (_phrase(status), "")
    msg = msg.replace("{path}", esc(path[:200])).replace("{method}", esc(method[:16]))
    m = re.match(r"^(.*?)(?::(\d{1,5}))?$", host_header.strip()[:100])
    host = esc(m.group(1) if m and m.group(1) else "localhost")
    port = esc(m.group(2) if m and m.group(2) else "80")
    return (
        '<!DOCTYPE HTML PUBLIC "-//IETF//DTD HTML 2.0//EN">\n<html><head>\n'
        f"<title>{status} {title}</title>\n</head><body>\n<h1>{title}</h1>\n<p>{msg}</p>\n<hr>\n"
        f"<address>{esc(server_header)} Server at {host} Port {port}</address>\n</body></html>\n"
    )


# --------------------------------------------------------------------------- inicio y logins
def home_page() -> str:
    body = (
        "<h1>Bienvenido a la Intranet</h1>"
        "<p>Portal interno de empleados de Nexora Industries.</p>"
        "<ul>"
        '<li><a href="/search">Directorio de empleados</a></li>'
        '<li><a href="/view?file=policy.txt">Politica de seguridad (v3.2)</a></li>'
        '<li><a href="/ping">Diagnostico de red</a> (solo Sistemas)</li>'
        '<li><a href="/comment">Buzon de sugerencias</a></li>'
        '<li><a href="/upload">Subir documentos</a></li>'
        "</ul><h1>Novedades</h1>"
        "<p><b>23/11</b> &ndash; Mantenimiento del servidor de ficheros esta noche.</p>"
        "<p><b>14/11</b> &ndash; Nueva politica de contrasenas: cambio cada 90 dias.</p>"
    )
    return layout("Inicio", body, "home")


def _login_form(action: str, user_field: str, pass_field: str, error: str | None, username: str) -> str:
    err = f'<div class="err">{error}</div>' if error else ""
    return (
        f'{err}<form method="post" action="{action}">'
        f'<label>Usuario</label><input type="text" name="{user_field}" value="{esc(username)}" autocomplete="off">'
        f'<label>Contrasena</label><input type="password" name="{pass_field}">'
        '<input type="submit" value="Entrar"></form>'
    )


def login_page(error: str | None = None, username: str = "") -> str:
    err = esc(error) if error else None
    return layout("Acceso", "<h1>Acceso empleados</h1>" + _login_form("/login", "username", "password", err, username), "login")


def admin_page(error: str | None = None, username: str = "") -> str:
    err = esc(error) if error else None
    body = "<h1>Administracion</h1><p>Zona restringida al personal de Sistemas.</p>"
    return layout("Administracion", body + _login_form("/admin", "username", "password", err, username))


def wp_login_page(error: str | None = None, username: str = "") -> str:
    err = ""
    if error == "bad_password":
        err = (
            f'<div id="login_error"><strong>Error</strong>: The password you entered for the username '
            f"<strong>{esc(username)}</strong> is incorrect. <a href=\"/wp-login.php?action=lostpassword\">"
            "Lost your password?</a></div>"
        )
    elif error == "bad_user":
        err = (
            f'<div id="login_error"><strong>Error</strong>: The username <strong>{esc(username)}</strong> '
            "is not registered on this site.</div>"
        )
    return (
        '<!DOCTYPE html>\n<html lang="en-US"><head><meta charset="utf-8"><title>Log In &lsaquo; '
        f"{SITE} Blog &#8212; WordPress</title><style>body{{background:#f0f0f1;font-family:sans-serif}}"
        "#login{width:320px;margin:8% auto}form{background:#fff;padding:24px;border:1px solid #c3c4c7}"
        "input[type=text],input[type=password]{width:100%;padding:6px;margin:4px 0 14px;box-sizing:border-box}"
        "#login_error{border-left:4px solid #d63638;background:#fff;padding:12px;margin-bottom:16px}"
        "h1{text-align:center;font-weight:400}</style></head><body class=\"login\"><div id=\"login\">"
        f"<h1>{SITE} Blog</h1>{err}"
        '<form name="loginform" id="loginform" action="/wp-login.php" method="post">'
        '<label>Username or Email Address</label><input type="text" name="log" id="user_login">'
        '<label>Password</label><input type="password" name="pwd" id="user_pass">'
        '<input type="submit" name="wp-submit" value="Log In">'
        '<input type="hidden" name="redirect_to" value="/wp-admin/"></form>'
        '<p><a href="/wp-login.php?action=lostpassword">Lost your password?</a></p></div></body></html>\n'
    )


def pma_login_page(error: str | None = None, username: str = "") -> str:
    err = (
        f'<div class="err">#1045 - Access denied for user &#039;{esc(username)}&#039;@&#039;localhost&#039; '
        "(using password: YES)</div>"
        if error
        else ""
    )
    return (
        '<!DOCTYPE html>\n<html lang="en"><head><meta charset="utf-8"><title>phpMyAdmin</title>'
        "<style>body{font-family:sans-serif;background:#f3f3f3}.box{width:340px;margin:7% auto;background:#fff;"
        "padding:20px;border:1px solid #aaa}.err{background:#fdd;border:1px solid #c00;padding:6px;margin:8px 0}"
        "input[type=text],input[type=password]{width:100%;padding:5px;margin:4px 0 10px;box-sizing:border-box}"
        "</style></head><body><div class=\"box\"><h2>Welcome to phpMyAdmin</h2>"
        f'{err}<form method="post" action="/phpmyadmin/index.php">'
        '<label>Username:</label><input type="text" name="pma_username">'
        '<label>Password:</label><input type="password" name="pma_password">'
        '<input type="hidden" name="server" value="1"><input type="submit" value="Go"></form>'
        "<small>phpMyAdmin 5.0.2 &middot; MySQL " + esc(data.MYSQL_VERSION) + "</small></div></body></html>\n"
    )


def panel_page() -> str:
    rows = "".join(
        f"<tr><td>{u[0]}</td><td>{esc(u[1])}</td><td>{esc(u[3])}</td><td>{esc(u[2])}</td></tr>" for u in data.USERS
    )
    body = (
        "<h1>Panel de administracion</h1><div class=\"ok\">Sesion iniciada.</div>"
        "<p>Servidor: <b>web01</b> &middot; Uptime: 41 dias &middot; Carga: 0.18</p>"
        "<h1>Usuarios</h1><table><tr><th>ID</th><th>Usuario</th><th>Rol</th><th>Email</th></tr>"
        f"{rows}</table><p><a href=\"/ping\">Diagnostico</a> &middot; <a href=\"/upload\">Subir</a> &middot; "
        '<a href="/view">Documentos</a> &middot; <a href="/logout">Cerrar sesion</a></p>'
    )
    return layout("Panel", body)


# --------------------------------------------------------------------------- SQLi
def _php_warning(msg: str, script: str = "search.php", line: int = 31) -> str:
    return (
        f"<br />\n<b>Warning</b>:  {esc(msg)} in <b>/var/www/html/{script}</b> "
        f"on line <b>{line}</b><br />\n"
    )


def search_page(q: str | None, result: SqlResult | None) -> str:
    form = (
        '<form method="get" action="/search"><label>Buscar empleado</label>'
        f'<input type="text" name="q" value="{esc(q or "")}"><input type="submit" value="Buscar"></form>'
    )
    out = ""
    if result is not None:
        if result.is_error:
            out = _php_warning(
                f"mysqli_query(): ({result.error_state}/{result.error_code}): {result.error_message}"
            ) + "<p>No se pudo completar la busqueda.</p>"
        elif not result.rows:
            out = "<p>No se encontraron resultados.</p>"
        else:
            head = "".join(f"<th>{esc(c)}</th>" for c in result.columns)
            body = "".join(
                "<tr>" + "".join(f"<td>{'NULL' if v is None else esc(v)}</td>" for v in row) + "</tr>"
                for row in result.rows
            )
            out = f"<table><tr>{head}</tr>{body}</table>"
    return layout("Directorio", f"<h1>Directorio de empleados</h1>{form}{out}", "dir")


# --------------------------------------------------------------------------- LFI
def view_page(file: str | None, result: lfi.LfiResult | None) -> str:
    if not file or result is None:
        items = "".join(f'<li><a href="/view?file={d}">{d}</a></li>' for d in lfi.PUBLIC_DOCS)
        return layout("Documentos", f"<h1>Documentos</h1><ul>{items}</ul>", "docs")
    if result.kind == "ok":
        body = f"<h1>{esc(file)}</h1><pre>{esc(result.content)}</pre>"
    else:
        warnings = "".join(_php_warning(w, "view.php", 12) for w in result.warnings)
        body = f"<h1>Documentos</h1>{warnings}<p>No se pudo cargar el documento.</p>"
    return layout("Documentos", body, "docs")


# --------------------------------------------------------------------------- command injection
def ping_page(host: str | None, output: str | None) -> str:
    form = (
        '<form method="get" action="/ping"><label>Host a comprobar</label>'
        f'<input type="text" name="host" value="{esc(host or "")}"><input type="submit" value="Ping"></form>'
    )
    out = f"<pre>{esc(output)}</pre>" if output is not None else ""
    return layout("Herramientas", f"<h1>Diagnostico de red</h1>{form}{out}", "tools")


# --------------------------------------------------------------------------- XSS reflejado
def comment_page(name: str | None, comment: str | None, raw: bool = False) -> str:
    """Refleja name y comment solo en la respuesta a quien los envió; no se guardan ni los ve otro
    visitante. Escapados por defecto (DOM inerte). raw=True devuelve el XSS reflejado "vivo"."""
    form = (
        '<form method="post" action="/comment"><label>Nombre</label><input type="text" name="name">'
        '<label>Comentario</label><textarea name="comment" rows="4"></textarea>'
        '<input type="submit" value="Enviar"></form>'
    )
    reflected = ""
    if comment is not None or name:
        if not raw:
            name, comment = esc(name or ""), esc(comment or "")
        reflected = (
            f'<div class="ok">Gracias {name or "anonimo"}, hemos recibido tu comentario:'
            f"<blockquote>{comment or ''}</blockquote></div>"  # escapado arriba salvo raw
        )
    return layout("Contacto", f"<h1>Buzon de sugerencias</h1>{reflected}{form}", "contact")


# --------------------------------------------------------------------------- subidas
def upload_page(message: str | None = None, url: str | None = None, error: bool = False) -> str:
    note = ""
    if message:
        note = f'<div class="{"err" if error else "ok"}">{esc(message)}'
        if url:
            note += f' <a href="{esc(url)}">{esc(url)}</a>'
        note += "</div>"
    form = (
        '<form method="post" action="/upload" enctype="multipart/form-data">'
        '<label>Selecciona un fichero (max. 2 MB)</label><input type="file" name="file">'
        '<br><br><input type="submit" value="Subir"></form>'
    )
    return layout("Subir ficheros", f"<h1>Subir documentos</h1>{note}{form}", "upload")


# --------------------------------------------------------------------------- "descuidos" de escáner
def server_status_page(server_header: str, host_header: str) -> str:
    m = re.match(r"^(.*?)(?::(\d{1,5}))?$", host_header.strip()[:100])
    host = esc(m.group(1) if m and m.group(1) else "localhost")
    port = esc(m.group(2) if m and m.group(2) else "80")
    rng = random.Random()
    total = rng.randint(180_000, 260_000)
    rows = "".join(
        f"<tr><td>{i}-0</td><td>{rng.randint(900, 1300)}</td><td>0/{rng.randint(10, 400)}/{rng.randint(1000, 9000)}</td>"
        f"<td>_</td><td>{rng.uniform(0.1, 9.9):.2f}</td><td>{rng.randint(0, 40)}</td><td>0</td>"
        f"<td>0.0</td><td>0.00</td><td>0.00</td><td>10.10.4.{rng.randint(2, 40)}</td><td>{host}:{port}</td>"
        f"<td nowrap>GET {p} HTTP/1.1</td></tr>"
        for i, p in enumerate(("/", "/search?q=ana", "/view?file=policy.txt", "/server-status"))
    )
    return (
        '<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 3.2 Final//EN">\n<html><head><title>Apache Status</title></head>'
        f"<body><h1>Apache Server Status for {host} (via 127.0.1.1)</h1><dl>"
        f"<dt>Server Version: {esc(server_header)} mod_php/7.4.3</dt>"
        "<dt>Server MPM: prefork</dt><dt>Server Built: 2023-03-08T17:32:54</dt></dl><hr>"
        "<dl><dt>Current Time: Monday, 23-Nov-2026 10:15:30 UTC</dt>"
        "<dt>Restart Time: Friday, 20-Nov-2026 06:25:01 UTC</dt>"
        "<dt>Parent Server Config. Generation: 1</dt><dt>Server uptime: 3 days 3 hours 50 minutes</dt>"
        f"<dt>Total accesses: {total} - Total Traffic: {total // 130} MB</dt>"
        "<dt>CPU Usage: u12.4 s3.1 cu0 cs0 - .0571% CPU load</dt>"
        "<dt>.675 requests/sec - 7.2 kB/second - 10.9 kB/request</dt>"
        "<dt>1 requests currently being processed, 5 idle workers</dt></dl>"
        "<table border=0><tr><th>Srv</th><th>PID</th><th>Acc</th><th>M</th><th>CPU</th><th>SS</th><th>Req</th>"
        "<th>Conn</th><th>Child</th><th>Slot</th><th>Client</th><th>VHost</th><th>Request</th></tr>"
        f"{rows}</table><hr><address>{esc(server_header)} Server at {host} Port {port}</address></body></html>\n"
    )


ROBOTS_TXT = (
    "User-agent: *\nDisallow: /admin/\nDisallow: /phpmyadmin/\nDisallow: /backup.zip\n"
    "Disallow: /.git/\nDisallow: /.env\nDisallow: /server-status\nDisallow: /upload\n"
)

# Credenciales 100 % FALSAS (las claves AWS son las de EJEMPLO de la documentación oficial).
FAKE_ENV = (
    "APP_NAME=NexoraIntranet\nAPP_ENV=production\nAPP_DEBUG=true\n"
    "APP_KEY=base64:8kVq1m3Zr0pQe5X7hT2yLwB9sNdJcA4uGfOiRb6vYxE=\n\n"
    "DB_CONNECTION=mysql\nDB_HOST=127.0.0.1\nDB_PORT=3306\nDB_DATABASE=intranet\n"
    "DB_USERNAME=intranet_app\nDB_PASSWORD=Nx!ntr4n3t_2020\n\n"
    "MAIL_HOST=smtp.nexora.local\nMAIL_PORT=587\nMAIL_USERNAME=notificaciones\nMAIL_PASSWORD=Notif#2020\n\n"
    "AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE\n"
    "AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY\nAWS_DEFAULT_REGION=eu-west-1\n"
)

FAKE_GIT_CONFIG = (
    "[core]\n\trepositoryformatversion = 0\n\tfilemode = true\n\tbare = false\n\tlogallrefupdates = true\n"
    '[remote "origin"]\n\turl = https://git.nexora.local/intranet/webapp.git\n'
    "\tfetch = +refs/heads/*:refs/remotes/origin/*\n"
    '[branch "main"]\n\tremote = origin\n\tmerge = refs/heads/main\n'
)

# ZIP vacío válido: solo el registro "End of central directory" (22 bytes).
EMPTY_ZIP = b"PK\x05\x06" + b"\x00" * 18
