"""Fixtures: una app de prueba con logs y subidas en directorios temporales."""
from __future__ import annotations

import dataclasses
import json
from pathlib import Path
from typing import Any, Iterator

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app

WEAK_USER, WEAK_PASS = "admin", "Passw0rd123"


class Honeypot:
    """App + cliente de pruebas + utilidades para leer el web.jsonl generado."""

    def __init__(self, tmp_path: Path, **overrides: Any) -> None:
        base = Settings(
            log_dir=str(tmp_path / "logs"),
            upload_dir=str(tmp_path / "uploads"),
            log_async=False,          # escritura síncrona: el fichero está al día tras cada petición
            rate_limit_per_min=0,     # sin rate limit salvo que el test lo pida
            weak_user=WEAK_USER,
            weak_pass=WEAK_PASS,
        )
        self.settings = dataclasses.replace(base, **overrides)
        self.app = create_app(self.settings)
        self.client = TestClient(
            self.app,
            base_url="http://intranet.test:8080",
            client=("203.0.113.5", 51234),
            follow_redirects=False,
        )

    @property
    def log_path(self) -> Path:
        return Path(self.settings.log_path)

    def events(self) -> list[dict[str, Any]]:
        if not self.log_path.exists():
            return []
        return [json.loads(line) for line in self.log_path.read_text(encoding="utf-8").splitlines()]

    def last(self) -> dict[str, Any]:
        return self.events()[-1]

    def uploads(self) -> list[Path]:
        d = Path(self.settings.upload_dir)
        return sorted(p for p in d.iterdir()) if d.exists() else []

    def close(self) -> None:
        self.app.state.events.close()


@pytest.fixture
def make_hp(tmp_path: Path) -> Iterator[Any]:
    created: list[Honeypot] = []

    def factory(**overrides: Any) -> Honeypot:
        hp = Honeypot(tmp_path / f"hp{len(created)}", **overrides)
        created.append(hp)
        return hp

    yield factory
    for hp in created:
        hp.close()


@pytest.fixture
def hp(make_hp: Any) -> Honeypot:
    return make_hp()  # type: ignore[no-any-return]
