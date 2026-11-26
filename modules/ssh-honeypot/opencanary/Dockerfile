# OpenCanary (FTP/MySQL/Redis señuelo). No hay imagen oficial sin root, así que se construye aquí.
# Python 3.11 por compatibilidad de dependencias de OpenCanary (ver NOTAS_CONTRATO.md).
FROM python:3.11.11-slim-bookworm AS build
RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential libpcap-dev libssl-dev libffi-dev \
 && rm -rf /var/lib/apt/lists/*
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir "setuptools<81" wheel "opencanary==0.9.4"

FROM python:3.11.11-slim-bookworm
RUN apt-get update \
 && apt-get install -y --no-install-recommends libpcap0.8 \
 && rm -rf /var/lib/apt/lists/* \
 && useradd --system --uid 10002 --create-home --home-dir /home/canary --shell /usr/sbin/nologin canary
COPY --from=build /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH" PYTHONUNBUFFERED=1
USER 10002:10002
WORKDIR /home/canary
# Primer plano, sin el envoltorio `opencanaryd --dev`: sin root, ese script ejecuta `$(which sudo) -E …`
# y, como la imagen no trae sudo, nunca arranca (0.9.4 está retirada en PyPI por eso; 0.9.5 mantiene
# la misma función). Es la misma orden que lanzaría el envoltorio. Config: /etc/opencanaryd/opencanary.conf
CMD ["twistd", "--nodaemon", "--no_save", "--pidfile=", "--python", "/opt/venv/bin/opencanary.tac"]
