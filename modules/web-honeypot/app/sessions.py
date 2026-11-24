"""Sesiones FALSAS del panel señuelo (solo en memoria, acotadas y con caducidad).

Una sesión solo existe si alguien entra con la credencial débil configurada. No da acceso
a nada real: el panel es una página estática simulada.
"""
from __future__ import annotations

import secrets
import time
from collections import OrderedDict


class SessionStore:
    def __init__(self, ttl_s: int = 3600, max_entries: int = 1000) -> None:
        self.ttl_s = ttl_s
        self.max_entries = max_entries
        self._data: "OrderedDict[str, float]" = OrderedDict()

    def create(self) -> str:
        self._purge()
        while len(self._data) >= self.max_entries:
            self._data.popitem(last=False)
        sid = secrets.token_hex(16)
        self._data[sid] = time.monotonic() + self.ttl_s
        return sid

    def is_valid(self, sid: str | None) -> bool:
        if not sid:
            return False
        expires = self._data.get(sid)
        if expires is None:
            return False
        if expires < time.monotonic():
            self._data.pop(sid, None)
            return False
        return True

    def delete(self, sid: str | None) -> None:
        if sid:
            self._data.pop(sid, None)

    def _purge(self) -> None:
        now = time.monotonic()
        for sid in [s for s, exp in self._data.items() if exp < now]:
            self._data.pop(sid, None)
