"""Configuración del señuelo web.

Todo se lee de variables de entorno (en Docker Compose vienen del fichero .env).
Valores inválidos NO tumban la aplicación: se usa el valor por defecto y se avisa por stderr.
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass

_TRUE = {"1", "true", "yes", "on", "si", "sí"}


def _env_str(name: str, default: str) -> str:
    value = os.environ.get(name)
    return default if value is None else value


def _env_bool(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None or value.strip() == "":
        return default
    return value.strip().lower() in _TRUE


def _env_int(name: str, default: int) -> int:
    value = os.environ.get(name)
    if value is None or value.strip() == "":
        return default
    try:
        return int(value.strip())
    except ValueError:
        print(f"[config] {name}={value!r} no es un entero; uso {default}", file=sys.stderr)
        return default


def _env_float(name: str, default: float) -> float:
    value = os.environ.get(name)
    if value is None or value.strip() == "":
        return default
    try:
        return float(value.strip())
    except ValueError:
        print(f"[config] {name}={value!r} no es un número; uso {default}", file=sys.stderr)
        return default


@dataclass(frozen=True)
class Settings:
    # --- Apariencia -------------------------------------------------------
    server_header: str = "Apache/2.4.41 (Ubuntu)"
    powered_by: str = "PHP/7.4.3"

    # --- Credencial débil que "entra" al panel falso (weak_pass vacío = desactivada)
    weak_user: str = "admin"
    weak_pass: str = ""

    # --- Origen de la petición ---------------------------------------------
    trust_proxy: bool = False

    # --- Logging -------------------------------------------------------------
    log_dir: str = "/logs/web"
    log_file_name: str = "web.jsonl"
    log_max_bytes: int = 50 * 1024 * 1024
    log_backups: int = 5
    log_async: bool = True          # False solo en tests (escritura síncrona)
    log_queue_size: int = 10000
    log_body_max_bytes: int = 8 * 1024

    # --- Subidas -----------------------------------------------------------------
    upload_dir: str = "/uploads"
    max_upload_bytes: int = 2 * 1024 * 1024        # límite por fichero
    upload_max_files: int = 1000                    # tope de ficheros guardados
    upload_max_total_bytes: int = 256 * 1024 * 1024  # tope de espacio total

    # --- Protección frente a abuso -------------------------------------------------
    max_body_bytes: int = 64 * 1024                 # body máximo (salvo /upload)
    upload_body_overhead_bytes: int = 256 * 1024    # margen multipart sobre max_upload_bytes
    body_read_timeout_s: float = 10.0               # máx. espera por cada trozo de body
    request_timeout_s: float = 15.0                 # máx. tiempo total del handler
    rate_limit_per_min: int = 300                   # 0 = sin límite
    rate_limit_burst: int = 100

    # --- Simulaciones --------------------------------------------------------------
    sleep_cap_s: float = 3.0                        # tope de SLEEP() simulado
    comment_reflect_raw: bool = False               # True = /comment refleja SIN escapar (XSS "vivo", solo laboratorio)
    comment_csp: str = ""                           # CSP opcional para /comment

    @property
    def log_path(self) -> str:
        return os.path.join(self.log_dir, self.log_file_name)

    @property
    def upload_body_limit(self) -> int:
        return self.max_upload_bytes + self.upload_body_overhead_bytes

    @classmethod
    def from_env(cls) -> "Settings":
        d = cls()
        return cls(
            server_header=_env_str("SERVER_HEADER", d.server_header),
            powered_by=_env_str("POWERED_BY", d.powered_by),
            weak_user=_env_str("WEAK_USER", d.weak_user),
            weak_pass=_env_str("WEAK_PASS", d.weak_pass),
            trust_proxy=_env_bool("TRUST_PROXY", d.trust_proxy),
            log_dir=_env_str("LOG_DIR", d.log_dir),
            log_max_bytes=_env_int("LOG_MAX_BYTES", d.log_max_bytes),
            log_backups=_env_int("LOG_BACKUPS", d.log_backups),
            log_async=_env_bool("LOG_ASYNC", d.log_async),
            upload_dir=_env_str("UPLOAD_DIR", d.upload_dir),
            max_upload_bytes=_env_int("MAX_UPLOAD_BYTES", d.max_upload_bytes),
            upload_max_files=_env_int("UPLOAD_MAX_FILES", d.upload_max_files),
            upload_max_total_bytes=_env_int("UPLOAD_MAX_TOTAL_BYTES", d.upload_max_total_bytes),
            max_body_bytes=_env_int("MAX_BODY_BYTES", d.max_body_bytes),
            body_read_timeout_s=_env_float("BODY_READ_TIMEOUT_S", d.body_read_timeout_s),
            request_timeout_s=_env_float("REQUEST_TIMEOUT_S", d.request_timeout_s),
            rate_limit_per_min=_env_int("RATE_LIMIT_PER_MIN", d.rate_limit_per_min),
            rate_limit_burst=_env_int("RATE_LIMIT_BURST", d.rate_limit_burst),
            sleep_cap_s=_env_float("SLEEP_CAP_S", d.sleep_cap_s),
            comment_reflect_raw=_env_bool("COMMENT_REFLECT_RAW", d.comment_reflect_raw),
            comment_csp=_env_str("COMMENT_CSP", d.comment_csp),
        )
