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
 && useradd --system --uid 10001 --create-home --home-dir /home/canary --shell /usr/sbin/nologin canary
COPY --from=build /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH" PYTHONUNBUFFERED=1
USER 10001:10001
WORKDIR /home/canary
# --dev = primer plano (necesario en contenedores). Config: /etc/opencanaryd/opencanary.conf
CMD ["opencanaryd", "--dev"]
