"""Simulador de un backend MySQL vulnerable para /search?q=.

NO hay base de datos ni se ejecuta SQL: se analiza el TEXTO de q con expresiones regulares y se
devuelve un resultado inventado. La consulta "imaginaria" es:

    SELECT id, name, department FROM employees WHERE name LIKE '%{q}%'

Comportamiento (de más a menos prioritario):
  1. extractvalue()/updatexml()      -> error XPATH con la versión de MySQL
  2. UNION SELECT                    -> nº de columnas != 3: error 1222; si coincide: filas falsas
  3. ORDER BY n (n > 3)              -> error 1054 (sirve para "contar columnas")
  4. OR <tautología> (1=1, 'a'='a')  -> tabla falsa de usuarios con hashes
  5. comilla impar sin comentario    -> error de sintaxis 1064
  6. AND a=b                         -> lista completa si a==b, vacía si no (blind booleano)
  7. resto                           -> búsqueda normal en el directorio ficticio
SLEEP(n) añade un retardo (acotado por sleep_cap_s) para parecer vulnerable a time-based.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from . import data

MAX_Q = 2000

COMMENT_RE = re.compile(r"(--(?:\s|$)|#|/\*)")
UNION_RE = re.compile(r"\bunion\b(?:\s+(?:all|distinct))?\s+select\b(?P<tail>.*)", re.I | re.S)
TAUTOLOGY_RE = re.compile(
    r"\bor\b\s*\(?\s*(['\"]?)(\w+)\1\s*=\s*\(?\s*\1\2\1?|\bor\s+true\b", re.I
)
BOOL_AND_RE = re.compile(r"\band\b\s*\(?\s*(['\"]?)(\w+)\1\s*=\s*\(?\s*(['\"]?)(\w+)\3", re.I)
ORDER_BY_RE = re.compile(r"\border\s+by\s+(\d+)", re.I)
SLEEP_RE = re.compile(r"\bsleep\s*\(\s*(\d+(?:\.\d+)?)", re.I)
BENCHMARK_RE = re.compile(r"\bbenchmark\s*\(", re.I)
ERROR_BASED_RE = re.compile(r"\b(?:extractvalue|updatexml)\s*\(", re.I)
NUMBER_RE = re.compile(r"-?\d+(?:\.\d+)?")
HEX_RE = re.compile(r"0x([0-9a-fA-F]+)")
CAST_RE = re.compile(r"(?:cast|convert)\((.*?)\s+as\s+\w+(?:\(\d+\))?\)", re.I | re.S)

_FUNCS: dict[str, str] = {
    "version()": data.MYSQL_VERSION,
    "@@version": data.MYSQL_VERSION,
    "@@version_comment": "(Ubuntu)",
    "database()": data.DB_NAME,
    "schema()": data.DB_NAME,
    "user()": data.DB_USER,
    "current_user()": data.DB_USER,
    "system_user()": data.DB_USER,
    "session_user()": data.DB_USER,
    "@@hostname": "db01",
    "@@datadir": "/var/lib/mysql/",
    "@@basedir": "/usr/",
}


@dataclass
class SqlResult:
    columns: tuple[str, ...] = ()
    rows: list[tuple[Any, ...]] = field(default_factory=list)
    error_code: int | None = None
    error_state: str = ""
    error_message: str = ""
    delay_s: float = 0.0

    @property
    def is_error(self) -> bool:
        return self.error_code is not None


def simulate(q: str, sleep_cap_s: float = 3.0) -> SqlResult:
    """Punto de entrada. Nunca lanza excepciones por culpa del input."""
    q = q[:MAX_Q]
    try:
        result = _simulate(q)
    except Exception:  # defensa: el input del atacante no debe provocar un 500
        result = _error(1064, "42000", "You have an error in your SQL syntax")
    result.delay_s = _delay(q, sleep_cap_s)
    return result


# --------------------------------------------------------------------------- lógica principal
def _simulate(q: str) -> SqlResult:
    if ERROR_BASED_RE.search(q):
        return _error(1105, "HY000", f"XPATH syntax error: '~{data.MYSQL_VERSION}'")

    union = UNION_RE.search(q)
    if union:
        return _union(q[: union.start()], union.group("tail"))

    order = ORDER_BY_RE.search(q)
    if order and int(order.group(1)) > len(data.EMP_COLUMNS):
        return _error(1054, "42S22", f"Unknown column '{order.group(1)}' in 'order clause'")

    if TAUTOLOGY_RE.search(q):
        return SqlResult(columns=data.USER_COLUMNS, rows=list(data.USERS))

    has_comment = bool(COMMENT_RE.search(q))
    if q.count("'") % 2 == 1 and not has_comment:
        idx = q.index("'")
        near = (q[idx + 1 :] + "%'")[:80]
        return _error(
            1064,
            "42000",
            "You have an error in your SQL syntax; check the manual that corresponds to your "
            f"MySQL server version for the right syntax to use near '{near}' at line 1",
        )

    boolean = BOOL_AND_RE.search(q)
    if boolean:
        rows = list(data.EMPLOYEES) if boolean.group(2) == boolean.group(4) else []
        return SqlResult(columns=data.EMP_COLUMNS, rows=rows)

    if has_comment and "'" in q:  # la comilla cierra el literal y el comentario anula el resto
        return SqlResult(columns=data.EMP_COLUMNS, rows=list(data.EMPLOYEES))

    return SqlResult(columns=data.EMP_COLUMNS, rows=_search(q))


def _search(needle: str) -> list[tuple[int, str, str]]:
    needle = needle.strip().lower()
    if not needle:
        return list(data.EMPLOYEES)
    return [e for e in data.EMPLOYEES if needle in e[1].lower() or needle in e[2].lower()]


def _error(code: int, state: str, message: str) -> SqlResult:
    return SqlResult(error_code=code, error_state=state, error_message=message)


def _delay(q: str, cap: float) -> float:
    delay = 0.0
    m = SLEEP_RE.search(q)
    if m:
        delay = max(delay, float(m.group(1)))
    if BENCHMARK_RE.search(q):
        delay = max(delay, 1.5)
    return min(delay, max(cap, 0.0))


# --------------------------------------------------------------------------- UNION SELECT
def _union(prefix: str, tail: str) -> SqlResult:
    tail = COMMENT_RE.split(tail, maxsplit=1)[0]
    parts = re.split(r"\bfrom\b", tail, maxsplit=1, flags=re.I)
    exprs = _split_top_level(parts[0])
    from_src = parts[1].strip() if len(parts) > 1 else ""

    if len(exprs) != len(data.EMP_COLUMNS):
        return _error(1222, "21000", "The used SELECT statements have a different number of columns")

    contexts = _contexts(from_src)
    if isinstance(contexts, SqlResult):
        return contexts

    extracted: list[tuple[Any, ...]]
    if any(re.match(r"\s*group_concat\s*\(", e, re.I) for e in exprs):
        row = []
        for e in exprs:
            m = re.fullmatch(r"\s*group_concat\s*\((.*)\)\s*", e, re.I | re.S)
            if m:
                inner = re.sub(r"^\s*distinct\s+", "", m.group(1), flags=re.I)
                row.append(",".join(str(_eval(inner, c)) for c in contexts))
            else:
                row.append(_eval(e, contexts[0] if contexts else {}))
        extracted = [tuple(row)]
    else:
        extracted = [tuple(_eval(e, c) for e in exprs) for c in contexts]

    needle = prefix.strip().strip("'\"").strip()
    base = _search(needle) if needle else list(data.EMPLOYEES)
    return SqlResult(columns=data.EMP_COLUMNS, rows=[*base, *extracted])


def _contexts(from_src: str) -> "list[dict[str, Any]] | SqlResult":
    low = from_src.lower()
    if not low:
        return [{}]
    if "information_schema.tables" in low:
        return [{"table_name": t, "table_schema": data.DB_NAME} for t in data.TABLES]
    if "information_schema.columns" in low:
        return [
            {"column_name": c, "table_name": "users", "table_schema": data.DB_NAME}
            for c in data.USER_COLUMNS
        ]
    if "information_schema.schemata" in low:
        return [{"schema_name": "information_schema"}, {"schema_name": data.DB_NAME}]
    token = re.split(r"[\s,;)]", low.strip("` "), maxsplit=1)[0].split(".")[-1].strip("`")
    if token == "users":
        return [{**dict(zip(data.USER_COLUMNS, u)), "password": u[4], "user": u[1]} for u in data.USERS]
    if token == "employees":
        return [dict(zip(data.EMP_COLUMNS, e)) for e in data.EMPLOYEES]
    return _error(1146, "42S02", f"Table '{data.DB_NAME}.{token}' doesn't exist")


def _eval(expr: str, ctx: dict[str, Any]) -> Any:
    """Evalúa de forma MUY simplificada una expresión de la lista del SELECT inyectado."""
    e = expr.strip()
    if not e:
        return ""
    low = e.lower()
    if low == "null":
        return None
    if NUMBER_RE.fullmatch(e):
        return e
    hx = HEX_RE.fullmatch(e)
    if hx:
        try:
            return bytes.fromhex(hx.group(1)).decode("latin-1")
        except ValueError:
            return e
    if len(e) >= 2 and e[0] == e[-1] and e[0] in "'\"":
        return e[1:-1]
    if low in _FUNCS:
        return _FUNCS[low]
    cast = CAST_RE.fullmatch(e)
    if cast:
        return _eval(cast.group(1), ctx)
    m = re.fullmatch(r"(concat_ws|concat|ifnull|coalesce)\s*\((.*)\)", e, re.I | re.S)
    if m:
        fn, args = m.group(1).lower(), _split_top_level(m.group(2))
        vals = [_eval(a, ctx) for a in args]
        if fn == "concat_ws" and vals:
            return str(vals[0]).join("" if v is None else str(v) for v in vals[1:])
        if fn in ("ifnull", "coalesce"):
            return next((v for v in vals if v is not None), "")
        return "".join("" if v is None else str(v) for v in vals)
    ident = low.split(".")[-1].strip("`")
    if ident in ctx:
        return ctx[ident]
    return e


def _split_top_level(src: str) -> list[str]:
    """Divide por comas ignorando las que van entre paréntesis o comillas."""
    out: list[str] = []
    depth = 0
    quote = ""
    cur: list[str] = []
    i = 0
    while i < len(src):
        ch = src[i]
        if quote:
            cur.append(ch)
            if ch == "\\" and i + 1 < len(src):
                cur.append(src[i + 1])
                i += 1
            elif ch == quote:
                quote = ""
        elif ch in "'\"":
            quote = ch
            cur.append(ch)
        elif ch == "(":
            depth += 1
            cur.append(ch)
        elif ch == ")":
            depth = max(depth - 1, 0)
            cur.append(ch)
        elif ch == "," and depth == 0:
            out.append("".join(cur))
            cur = []
        else:
            cur.append(ch)
        i += 1
    out.append("".join(cur))
    return out
