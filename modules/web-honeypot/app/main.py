"""Fábrica de la aplicación FastAPI del señuelo web (módulo B).

Arranque (ver Dockerfile):  uvicorn app.main:create_app --factory
No hay efectos secundarios al importar este módulo (útil para los tests).
"""
from __future__ import annotations

import os
import sys
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, Response
from starlette.exceptions import HTTPException as StarletteHTTPException

from . import pages, routes
from .config import Settings
from .event_logger import EventLogger
from .middleware import HoneypotMiddleware
from .ratelimit import RateLimiter
from .sessions import SessionStore


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    event_logger = EventLogger(
        settings.log_path,
        max_bytes=settings.log_max_bytes,
        backups=settings.log_backups,
        use_queue=settings.log_async,
        queue_size=settings.log_queue_size,
    )
    try:  # el volumen de subidas debe existir; si no se puede crear, /upload sigue "funcionando"
        os.makedirs(settings.upload_dir, exist_ok=True)
    except OSError as exc:
        print(f"[main] no se pudo crear {settings.upload_dir!r}: {exc}", file=sys.stderr)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        event_logger.close()  # vacía la cola de eventos pendientes al apagar

    # Sin /docs, /redoc ni /openapi.json: delatarían FastAPI.
    app = FastAPI(
        title="intranet",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        redirect_slashes=False,
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.state.events = event_logger
    app.state.sessions = SessionStore()

    app.include_router(routes.router)

    def error_page(request: Request, status: int) -> Response:
        return HTMLResponse(
            pages.apache_error(status, request.url.path, request.method, request.headers.get("host", ""), settings.server_header),
            status_code=status,
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_error(request: Request, exc: StarletteHTTPException) -> Response:
        return error_page(request, exc.status_code)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError) -> Response:
        return error_page(request, 400)

    app.add_middleware(
        HoneypotMiddleware,
        settings=settings,
        event_logger=event_logger,
        limiter=RateLimiter(settings.rate_limit_per_min, settings.rate_limit_burst),
        sessions=app.state.sessions,
    )
    return app
