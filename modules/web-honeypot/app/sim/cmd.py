"""Simulador de command injection para /ping?host=.

REGLA DE ORO: NO se ejecuta NADA. Ni subprocess, ni os.system, ni eval. El texto del atacante se
trocea (shlex solo parsea cadenas) y cada "comando" se contesta desde una tabla de salidas falsas.
Las descargas (wget/curl) y las shells inversas NO hacen ninguna conexión: se contestan con un
fallo de red inventado o con silencio.
"""
from __future__ import annotations

import hashlib
import random
import re
import shlex
from datetime import datetime, timezone

from . import data, lfi

_SPLIT_RE = re.compile(r"(&&|\|\||[;|&\n\r])")
_SUBST_RE = re.compile(r"\$\(([^()]*)\)|`([^`]*)`")
_IPV4_RE = re.compile(r"^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$")
_HOST_RE = re.compile(r"^[A-Za-z0-9_.\-]+$")
_DOMAIN_RE = re.compile(r"^(?:[A-Za-z0-9](?:[A-Za-z0-9\-]*[A-Za-z0-9])?\.)+[A-Za-z]{2,}$")
MAX_COMMANDS = 8
MAX_OUTPUT = 4000

_ID = "uid=33(www-data) gid=33(www-data) groups=33(www-data)"
_UNAME_A = (
    f"Linux {data.HOSTNAME} 5.4.0-135-generic #152-Ubuntu SMP Wed Nov 23 20:19:22 UTC 2022 "
    "x86_64 x86_64 x86_64 GNU/Linux"
)
_LS = "config.php  css  img  index.php  login.php  pages  search.php  upload.php  view.php"
_LS_LA = (
    "total 48\n"
    "drwxr-xr-x 5 www-data www-data 4096 Sep 14 09:12 .\n"
    "drwxr-xr-x 3 root     root     4096 Mar  2  2024 ..\n"
    "-rw-r----- 1 www-data www-data  412 Mar  2  2024 config.php\n"
    "drwxr-xr-x 2 www-data www-data 4096 Mar  2  2024 css\n"
    "drwxr-xr-x 2 www-data www-data 4096 Mar  2  2024 img\n"
    "-rw-r--r-- 1 www-data www-data 3120 Sep 14 09:12 index.php\n"
    "-rw-r--r-- 1 www-data www-data 1844 Sep 14 09:12 login.php\n"
    "drwxr-xr-x 2 www-data www-data 4096 Sep 14 09:12 pages\n"
    "-rw-r--r-- 1 www-data www-data 2210 Sep 14 09:12 search.php\n"
    "-rw-r--r-- 1 www-data www-data 1630 Sep 14 09:12 upload.php\n"
    "-rw-r--r-- 1 www-data www-data  987 Sep 14 09:12 view.php"
)
_IFCONFIG = (
    "eth0: flags=4163<UP,BROADCAST,RUNNING,MULTICAST>  mtu 1500\n"
    "        inet 10.10.4.21  netmask 255.255.255.0  broadcast 10.10.4.255\n"
    "        ether 02:42:0a:0a:04:15  txqueuelen 0  (Ethernet)\n\n"
    "lo: flags=73<UP,LOOPBACK,RUNNING>  mtu 65536\n"
    "        inet 127.0.0.1  netmask 255.0.0.0"
)
_PS = (
    "USER       PID %CPU %MEM    VSZ   RSS TTY      STAT START   TIME COMMAND\n"
    "root         1  0.0  0.3 169436 11876 ?        Ss   Nov20   0:03 /sbin/init\n"
    "root       612  0.0  0.5 207420 20124 ?        Ss   Nov20   0:11 /usr/sbin/apache2 -k start\n"
    "www-data   913  0.0  0.4 207800 17348 ?        S    08:01   0:00 /usr/sbin/apache2 -k start\n"
    "mysql      702  0.2  8.9 1790164 358420 ?      Ssl  Nov20   4:52 /usr/sbin/mysqld\n"
    "www-data  1204  0.0  0.1   2608   596 ?        S    19:50   0:00 sh -c ping -c 4"
)
_ENV = (
    "APACHE_RUN_USER=www-data\nAPACHE_RUN_GROUP=www-data\nAPACHE_LOG_DIR=/var/log/apache2\n"
    "PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin\nPWD=/var/www/html\nLANG=C"
)
_KNOWN_BINS = {
    "ls", "cat", "id", "whoami", "uname", "pwd", "wget", "curl", "nc", "bash", "sh",
    "python", "python3", "perl", "php", "ping", "echo", "ps", "env", "date", "hostname",
}


def simulate_ping(raw_host: str) -> str:
    """Devuelve la salida (falsa) que daría `ping -c 4 <raw_host>` con inyección incluida."""
    segments = _SPLIT_RE.split(raw_host.replace("\r\n", "\n"))
    host_part = _expand(segments[0].strip())
    rest: list[tuple[str, str]] = []
    for i in range(1, len(segments) - 1, 2):
        sep, cmd = segments[i], segments[i + 1].strip()
        if cmd:
            rest.append((sep, cmd))
    rest = rest[:MAX_COMMANDS]

    ping_text, last_ok = _ping(host_part)
    outputs: list[str] = [ping_text]
    for sep, cmd in rest:
        cmd = _expand(cmd)
        name, args = _split_cmd(cmd)
        if sep == "|":
            if name in _FILTERS:  # `... | head`, `| grep x`, `| wc -l`: se filtra la salida previa
                if outputs:
                    outputs[-1] = _apply_filter(name, args, outputs[-1])
                last_ok = True
                continue
            if outputs:  # tubería hacia otro comando: su stdin consume la salida anterior
                outputs.pop()
        elif sep == "&&" and not last_ok:
            continue
        elif sep == "||" and last_ok:
            continue
        text, ok = _exec(cmd)
        outputs.append(text)
        last_ok = ok
    return "\n".join(o for o in outputs if o)[:MAX_OUTPUT]


def _split_cmd(cmd: str) -> tuple[str, list[str]]:
    try:
        tokens = shlex.split(cmd)
    except ValueError:
        tokens = cmd.split()
    if not tokens:
        return ("", [])
    return (tokens[0].rsplit("/", 1)[-1], tokens[1:])


_FILTERS = {"head", "tail", "grep", "wc", "sort", "uniq", "cut", "tr", "sed", "awk", "base64", "xxd", "tee", "less", "more"}


def _apply_filter(name: str, args: list[str], text: str) -> str:
    """Filtros de pipe MUY básicos sobre texto ya falso (sin ejecutar nada)."""
    lines = text.split("\n")
    if name in ("head", "tail"):
        n = 10
        for i, a in enumerate(args):
            if a == "-n" and i + 1 < len(args) and args[i + 1].lstrip("-").isdigit():
                n = int(args[i + 1])
            elif re.fullmatch(r"-\d+", a):
                n = int(a[1:])
            elif re.fullmatch(r"-n\d+", a):
                n = int(a[2:])
        n = max(min(n, 200), 0)
        return "\n".join(lines[:n] if name == "head" else lines[-n:] if n else [])
    if name == "wc":
        return str(len(lines)) if "-l" in args else f"{len(lines)} {len(text.split())} {len(text)}"
    if name == "grep":
        words = [a for a in args if not a.startswith("-")]
        if not words:
            return text
        needle, invert = words[0].lower(), "-v" in args
        return "\n".join(ln for ln in lines if (needle in ln.lower()) != invert)
    if name == "sort":
        return "\n".join(sorted(lines))
    return text


# --------------------------------------------------------------------------- ping falso
def _ping(host: str) -> tuple[str, bool]:
    host = host.strip()
    if not host:
        return ("Usage: ping [-aAbBdDfhLnOqrRUvV] [-c count] [-i interval] [-I interface] destination", False)
    if not _HOST_RE.match(host):
        return (f"ping: {host}: Name or service not known", False)
    ip = _resolve(host)
    if ip is None:
        return (f"ping: {host}: Name or service not known", False)

    rng = random.Random(hashlib.sha256(host.encode()).digest())
    base = 0.04 if ip.startswith("127.") else rng.uniform(4.0, 38.0)
    ttl = 64 if ip.startswith("127.") else rng.choice((52, 55, 57, 58, 117))
    times = [round(max(base + rng.uniform(-0.6, 1.4), 0.02), 2 if ip.startswith("127.") else 1) for _ in range(4)]
    is_name = host != ip
    label = f"{host} ({ip})" if is_name else ip
    head = f"PING {host} ({ip}) 56(84) bytes of data."
    lines = [head]
    for seq, t in enumerate(times, 1):
        lines.append(f"64 bytes from {label}: icmp_seq={seq} ttl={ttl} time={t} ms")
    avg = sum(times) / len(times)
    mdev = (sum((t - avg) ** 2 for t in times) / len(times)) ** 0.5
    lines += [
        "",
        f"--- {host} ping statistics ---",
        "4 packets transmitted, 4 received, 0% packet loss, time 3004ms",
        f"rtt min/avg/max/mdev = {min(times):.3f}/{avg:.3f}/{max(times):.3f}/{mdev:.3f} ms",
    ]
    return ("\n".join(lines), True)


def _resolve(host: str) -> str | None:
    if host.lower() == "localhost":
        return "127.0.0.1"
    m = _IPV4_RE.match(host)
    if m:
        return host if all(int(g) <= 255 for g in m.groups()) else None
    if _DOMAIN_RE.match(host):  # nombre "resoluble": IP inventada del rango de documentación TEST-NET-3
        n = hashlib.sha256(host.lower().encode()).digest()[0] % 253 + 1
        return f"203.0.113.{n}"
    return None


# --------------------------------------------------------------------------- shell falsa
def _expand(text: str) -> str:
    """Sustituye $(cmd) y `cmd` por la salida FALSA del comando (una sola pasada)."""

    def repl(m: re.Match[str]) -> str:
        inner = m.group(1) if m.group(1) is not None else m.group(2)
        out, _ok = _exec(inner.strip())
        return out.strip().replace("\n", " ")

    return _SUBST_RE.sub(repl, text)


def _exec(cmd: str) -> tuple[str, bool]:
    """Salida falsa de un comando. No ejecuta nada."""
    try:
        tokens = shlex.split(cmd)
    except ValueError:
        tokens = cmd.split()
    if not tokens:
        return ("", True)
    name = tokens[0].rsplit("/", 1)[-1]
    args = tokens[1:]

    if name == "id":
        return ("33" if "-u" in args else _ID, True)
    if name == "whoami":
        return ("www-data", True)
    if name == "hostname":
        return (data.HOSTNAME, True)
    if name == "uname":
        if "-a" in args:
            return (_UNAME_A, True)
        if "-r" in args:
            return ("5.4.0-135-generic", True)
        return ("Linux", True)
    if name == "pwd":
        return ("/var/www/html", True)
    if name == "ls":
        return (_LS_LA if any(a.startswith("-") and "l" in a for a in args) else _LS, True)
    if name == "cat":
        return _cat(args)
    if name == "echo":
        return (" ".join(a for a in args if not a.startswith("-n")), True)
    if name in ("ifconfig", "ip"):
        return (_IFCONFIG, True)
    if name == "ps":
        return (_PS, True)
    if name in ("env", "printenv"):
        return (_ENV, True)
    if name == "date":
        return (datetime.now(timezone.utc).strftime("%a %b %d %H:%M:%S UTC %Y"), True)
    if name == "which":
        return ("\n".join(f"/usr/bin/{a}" for a in args if a in _KNOWN_BINS), True)
    if name in ("wget", "curl"):
        return (_download_failure(name, args), False)
    if name in ("nc", "ncat", "bash", "sh", "python", "python3", "perl", "php", "socat", "telnet", "sleep", "touch", "chmod", "rm", "mkdir", "cd", "export"):
        return ("", True)  # silencio: shells inversas / efectos secundarios no hacen nada
    return (f"sh: 1: {name}: not found", False)


def _cat(args: list[str]) -> tuple[str, bool]:
    files = [a for a in args if not a.startswith("-")]
    if not files:
        return ("", True)
    out: list[str] = []
    ok = True
    for f in files[:4]:
        res = lfi.resolve(f)
        if res.kind == "ok":
            out.append(res.content.rstrip("\n"))
        elif res.kind == "denied":
            out.append(f"cat: {f}: Permission denied")
            ok = False
        else:
            out.append(f"cat: {f}: No such file or directory")
            ok = False
    return ("\n".join(out), ok)


def _download_failure(tool: str, args: list[str]) -> str:
    url = next((a for a in args if "://" in a or re.match(r"^[\w.\-]+\.[a-z]{2,}", a)), "")
    host = re.sub(r"^[a-z]+://", "", url).split("/")[0].split(":")[0] or "host"
    if tool == "curl":
        return f"curl: (28) Failed to connect to {host} port 80: Connection timed out"
    return f"Connecting to {host}|203.0.113.7|:80... failed: Connection timed out."
