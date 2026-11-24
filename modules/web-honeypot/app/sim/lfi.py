"""Simulador de LFI / path traversal para /view?file=.

REGLA DE ORO: este módulo NUNCA abre ficheros reales. Solo manipula TEXTO (normaliza la ruta con
posixpath, que no toca el disco) y busca el resultado en el diccionario en memoria FAKE_FILES.
Tampoco descarga nada: las URL (RFI) se rechazan como haría PHP con allow_url_include=0.
"""
from __future__ import annotations

import base64
import posixpath
import re
from dataclasses import dataclass, field
from urllib.parse import unquote

BASE_DIR = "/var/www/html/pages"
ALT_BASE = "/var/www/html"
INCLUDE_PATH = ".:/usr/share/php"

FAKE_FILES: dict[str, str] = {
    "/etc/passwd": (
        "root:x:0:0:root:/root:/bin/bash\n"
        "daemon:x:1:1:daemon:/usr/sbin:/usr/sbin/nologin\n"
        "bin:x:2:2:bin:/bin:/usr/sbin/nologin\n"
        "sys:x:3:3:sys:/dev:/usr/sbin/nologin\n"
        "sync:x:4:65534:sync:/bin:/bin/sync\n"
        "games:x:5:60:games:/usr/games:/usr/sbin/nologin\n"
        "man:x:6:12:man:/var/cache/man:/usr/sbin/nologin\n"
        "lp:x:7:7:lp:/var/spool/lpd:/usr/sbin/nologin\n"
        "mail:x:8:8:mail:/var/mail:/usr/sbin/nologin\n"
        "news:x:9:9:news:/var/spool/news:/usr/sbin/nologin\n"
        "www-data:x:33:33:www-data:/var/www:/usr/sbin/nologin\n"
        "backup:x:34:34:backup:/var/backups:/usr/sbin/nologin\n"
        "nobody:x:65534:65534:nobody:/nonexistent:/usr/sbin/nologin\n"
        "systemd-network:x:100:102:systemd Network Management,,,:/run/systemd:/usr/sbin/nologin\n"
        "systemd-resolve:x:101:103:systemd Resolver,,,:/run/systemd:/usr/sbin/nologin\n"
        "sshd:x:110:65534::/run/sshd:/usr/sbin/nologin\n"
        "mysql:x:112:116:MySQL Server,,,:/nonexistent:/bin/false\n"
        "deploy:x:1000:1000:Deploy User,,,:/home/deploy:/bin/bash\n"
        "svc-backup:x:1001:1001::/home/svc-backup:/bin/bash\n"
    ),
    "/etc/hostname": "web01\n",
    "/etc/hosts": (
        "127.0.0.1 localhost\n"
        "127.0.1.1 web01\n"
        "10.10.4.21 web01.intranet.nexora.local web01\n"
        "10.10.4.30 db01.intranet.nexora.local db01\n\n"
        "::1 ip6-localhost ip6-loopback\n"
    ),
    "/etc/issue": "Ubuntu 20.04.6 LTS \\n \\l\n\n",
    "/etc/os-release": (
        'NAME="Ubuntu"\nVERSION="20.04.6 LTS (Focal Fossa)"\nID=ubuntu\nID_LIKE=debian\n'
        'PRETTY_NAME="Ubuntu 20.04.6 LTS"\nVERSION_ID="20.04"\nVERSION_CODENAME=focal\n'
    ),
    "/proc/version": (
        "Linux version 5.4.0-135-generic (buildd@lcy02-amd64-066) (gcc version 9.4.0 "
        "(Ubuntu 9.4.0-1ubuntu1~20.04.1)) #152-Ubuntu SMP Wed Nov 23 20:19:22 UTC 2022\n"
    ),
    "/proc/self/cmdline": "/usr/sbin/apache2 -k start\n",
    "/proc/self/environ": (
        "APACHE_RUN_DIR=/var/run/apache2\nAPACHE_RUN_USER=www-data\nAPACHE_RUN_GROUP=www-data\n"
        "APACHE_LOG_DIR=/var/log/apache2\nPATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin\n"
        "LANG=C\nPWD=/\n"
    ),
    "/var/www/html/config.php": (
        "<?php\n// Configuracion de la intranet - NO SUBIR A GIT\n"
        "define('DB_HOST', 'localhost');\ndefine('DB_USER', 'intranet_app');\n"
        "define('DB_PASS', 'Nx!ntr4n3t_2020');\ndefine('DB_NAME', 'intranet');\n"
        "define('SECRET_KEY', 'a1b2c3d4e5f60718293a4b5c6d7e8f90');\ndefine('DEBUG', true);\n"
    ),
    "/var/www/html/index.php": (
        "<?php\nrequire_once 'config.php';\nsession_start();\ninclude 'pages/home.php';\n"
    ),
    "/etc/apache2/sites-enabled/000-default.conf": (
        "<VirtualHost *:80>\n\tServerAdmin webmaster@localhost\n\tDocumentRoot /var/www/html\n"
        "\tErrorLog ${APACHE_LOG_DIR}/error.log\n\tCustomLog ${APACHE_LOG_DIR}/access.log combined\n"
        "</VirtualHost>\n"
    ),
    "/var/log/apache2/access.log": (
        '10.10.4.5 - - [23/Nov/2026:08:02:11 +0000] "GET / HTTP/1.1" 200 3120 "-" "Mozilla/5.0"\n'
        '10.10.4.5 - - [23/Nov/2026:08:02:12 +0000] "GET /search?q=laura HTTP/1.1" 200 1844 "-" "Mozilla/5.0"\n'
        '10.10.4.17 - - [23/Nov/2026:08:14:40 +0000] "GET /view?file=policy.txt HTTP/1.1" 200 912 "-" "Mozilla/5.0"\n'
    ),
    # Documentos "legítimos" de la intranet (rutas relativas a BASE_DIR)
    BASE_DIR + "/about.txt": (
        "Nexora Industries - Intranet corporativa\n"
        "Portal interno para empleados: directorio, documentos y herramientas de soporte.\n"
    ),
    BASE_DIR + "/policy.txt": (
        "Politica de seguridad de la informacion (v3.2)\n"
        "1. Las contrasenas se cambian cada 90 dias.\n2. No compartir credenciales.\n"
        "3. Notificar incidencias a soporte@intranet.nexora.local.\n"
    ),
    BASE_DIR + "/contact.txt": (
        "Soporte TI: soporte@intranet.nexora.local - ext. 4100\n"
        "Recursos Humanos: rrhh@intranet.nexora.local - ext. 4200\n"
    ),
    BASE_DIR + "/readme.txt": "Documentos de la intranet. Usa /view?file=<nombre>.\n",
}

PUBLIC_DOCS = ("about.txt", "policy.txt", "contact.txt", "readme.txt")

# Rutas que existirían pero que www-data no puede leer -> "Permission denied"
_DENIED_PREFIXES = (
    "/root",
    "/etc/shadow",
    "/etc/sudoers",
    "/etc/ssh/ssh_host",
    "/var/lib/mysql",
    "/proc/self/mem",
)
_DENIED_HOME_RE = re.compile(r"^/home/[^/]+/\.(?:ssh|bash_history|mysql_history|aws)")
_WRAPPER_RE = re.compile(r"^(?P<scheme>[a-z][a-z0-9+.\-]*):(?://|/)?", re.I)
_BLOCKED_URL_SCHEMES = {"http", "https", "ftp", "ftps", "data", "expect", "phar", "zip", "glob"}


@dataclass
class LfiResult:
    kind: str  # "ok" | "denied" | "missing" | "wrapper"
    path: str = ""
    content: str = ""
    warnings: list[str] = field(default_factory=list)  # avisos estilo PHP, en texto plano


def normalize(raw: str) -> str:
    """Normaliza SOLO el texto de la ruta (no toca el disco)."""
    p = raw.strip().replace("\\", "/")
    p = re.sub(r"\.{2,}/+", "../", p)  # '....//' -> '../'
    p = re.sub(r"/{2,}", "/", p)
    if not p.startswith("/"):
        p = BASE_DIR + "/" + p
    return posixpath.normpath(p)


def resolve(param: str) -> LfiResult:
    """Resuelve el parámetro `file` contra el diccionario falso."""
    if re.search(r"%2e|%2f|%00|%25", param, re.I):  # doble codificación (Starlette ya decodificó una vez)
        param = unquote(param)
    raw = param.split("\x00", 1)[0]  # truncado por byte nulo (PHP antiguo), simulado
    low = raw.strip().lower()

    if low.startswith("php://filter"):
        m = re.search(r"resource=(.*)$", raw, re.I | re.S)
        inner = resolve(m.group(1)) if m else _wrapper_blocked(raw, "php://filter")
        if inner.kind == "ok" and "base64-encode" in low:
            inner.content = base64.b64encode(inner.content.encode()).decode()
        return inner

    if low.startswith("file://"):
        raw = raw.strip()[len("file://") :]
        low = raw.lower()

    wm = _WRAPPER_RE.match(raw.strip())
    if wm and len(wm.group("scheme")) > 1:  # >1 evita confundir con letras de unidad (C:)
        scheme = wm.group("scheme").lower()
        if scheme in _BLOCKED_URL_SCHEMES or scheme == "php":
            return _wrapper_blocked(raw, scheme + "://")
        return LfiResult(
            "wrapper",
            raw,
            warnings=[
                f'include(): Unable to find the wrapper "{scheme}" - did you forget to enable it '
                "when you configured PHP?",
                f"include({raw}): failed to open stream: No such file or directory",
                _failed_opening(raw),
            ],
        )

    path = normalize(raw)
    if path not in FAKE_FILES and not raw.strip().startswith(("/", "\\")):
        alt = posixpath.normpath(ALT_BASE + "/" + raw.strip().replace("\\", "/"))  # include_path '.'
        if alt in FAKE_FILES:
            path = alt
    if path in FAKE_FILES:
        return LfiResult("ok", path, content=FAKE_FILES[path])
    if path.startswith(_DENIED_PREFIXES) or _DENIED_HOME_RE.match(path):
        return LfiResult(
            "denied",
            path,
            warnings=[
                f"include({path}): failed to open stream: Permission denied",
                _failed_opening(raw),
            ],
        )
    return LfiResult(
        "missing",
        path,
        warnings=[
            f"include({path}): failed to open stream: No such file or directory",
            _failed_opening(raw),
        ],
    )


def _failed_opening(raw: str) -> str:
    return f"include(): Failed opening '{raw}' for inclusion (include_path='{INCLUDE_PATH}')"


def _wrapper_blocked(raw: str, wrapper: str) -> LfiResult:
    return LfiResult(
        "wrapper",
        raw,
        warnings=[
            f"include(): {wrapper} wrapper is disabled in the server configuration by allow_url_include=0",
            f"include({raw}): failed to open stream: no suitable wrapper could be found",
            _failed_opening(raw),
        ],
    )
