"""Rate limit básico por IP (token bucket en memoria).

El honeypot no debe caerse por un escaneo agresivo: cada IP tiene un cubo de `burst`
tokens que se rellena a `per_min / 60` tokens por segundo. Sin tokens -> 429.
"""
from __future__ import annotations

import math
import time


class RateLimiter:
    def __init__(self, per_min: int, burst: int, max_entries: int = 20000) -> None:
        self.enabled = per_min > 0
        self.rate = max(per_min, 1) / 60.0
        self.burst = float(max(burst, 1))
        self.max_entries = max_entries
        self._buckets: dict[str, tuple[float, float]] = {}  # ip -> (tokens, último_instante)

    def allow(self, key: str, now: float | None = None) -> bool:
        if not self.enabled:
            return True
        now = time.monotonic() if now is None else now
        tokens, last = self._buckets.get(key, (self.burst, now))
        tokens = min(self.burst, tokens + (now - last) * self.rate)
        allowed = tokens >= 1.0
        if allowed:
            tokens -= 1.0
        self._buckets[key] = (tokens, now)
        if len(self._buckets) > self.max_entries:
            self._purge(now)
        return allowed

    def retry_after(self) -> int:
        """Segundos sugeridos para la cabecera Retry-After."""
        return max(1, math.ceil(1.0 / self.rate))

    def _purge(self, now: float) -> None:
        """Elimina cubos inactivos (llenos); si aun así hay demasiados, vacía todo (memoria acotada)."""
        full_after = self.burst / self.rate
        self._buckets = {k: v for k, v in self._buckets.items() if now - v[1] < full_after}
        if len(self._buckets) > self.max_entries:
            self._buckets.clear()
