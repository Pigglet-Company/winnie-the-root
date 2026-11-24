"""Escritor de eventos JSON Lines.

- Un evento por línea, UTF-8, flush inmediato (StreamHandler vacía el buffer en cada emit).
- RotatingFileHandler (por defecto 50 MB x 5 ficheros).
- Escritura en un hilo aparte (QueueHandler + QueueListener) para no bloquear el bucle de eventos.
- Un fallo de logging NUNCA tumba la app: se informa por stderr y se sigue.
- Si no se puede abrir el fichero (permisos, volumen ausente...) se cae a stderr.
"""
from __future__ import annotations

import json
import logging
import logging.handlers
import os
import queue
import sys
import time
from typing import Any


def _warn(msg: str) -> None:
    try:
        print(f"[event_logger] {msg}", file=sys.stderr, flush=True)
    except Exception:  # pragma: no cover - ni stderr debe tumbar la app
        pass


class _SafeQueueHandler(logging.handlers.QueueHandler):
    """QueueHandler acotado: si la cola se llena descarta el evento y avisa (como mucho 1/s)."""

    def __init__(self, q: "queue.Queue[Any]") -> None:
        super().__init__(q)
        self.dropped = 0
        self._last_warn = 0.0

    def enqueue(self, record: logging.LogRecord) -> None:
        try:
            self.queue.put_nowait(record)
        except queue.Full:
            self.dropped += 1
            now = time.monotonic()
            if now - self._last_warn > 1.0:
                self._last_warn = now
                _warn(f"cola llena: eventos descartados hasta ahora = {self.dropped}")


class EventLogger:
    def __init__(
        self,
        path: str,
        max_bytes: int = 50 * 1024 * 1024,
        backups: int = 5,
        use_queue: bool = True,
        queue_size: int = 10000,
    ) -> None:
        self.path = path
        self._listener: logging.handlers.QueueListener | None = None
        # Logger independiente (fuera del registro global) para que cada instancia sea aislada.
        self._log = logging.Logger(f"hp-web-events-{id(self)}", level=logging.INFO)
        self._log.propagate = False

        target = self._make_target(path, max_bytes, backups)
        if use_queue:
            q: "queue.Queue[Any]" = queue.Queue(maxsize=queue_size)
            self._log.addHandler(_SafeQueueHandler(q))
            self._listener = logging.handlers.QueueListener(q, target)
            self._listener.start()
            self._target = target
        else:
            self._log.addHandler(target)
            self._target = target

    @staticmethod
    def _make_target(path: str, max_bytes: int, backups: int) -> logging.Handler:
        handler: logging.Handler
        try:
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
            handler = logging.handlers.RotatingFileHandler(
                path, maxBytes=max_bytes, backupCount=backups, encoding="utf-8"
            )
        except OSError as exc:
            _warn(f"no puedo abrir {path!r} ({exc}); los eventos irán a stderr")
            handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(logging.Formatter("%(message)s"))
        return handler

    def log(self, event: dict[str, Any]) -> None:
        """Serializa y encola el evento. No lanza nunca excepciones."""
        try:
            line = json.dumps(event, ensure_ascii=False, separators=(",", ":"), default=str)
            self._log.info(line)
        except Exception as exc:
            _warn(f"no se pudo registrar un evento: {exc!r}")

    def close(self) -> None:
        """Vacía la cola pendiente y cierra el fichero."""
        try:
            if self._listener is not None:
                self._listener.stop()
                self._listener = None
            for handler in list(self._log.handlers):
                self._log.removeHandler(handler)
                handler.close()
            self._target.close()
        except Exception as exc:  # pragma: no cover
            _warn(f"error al cerrar: {exc!r}")
