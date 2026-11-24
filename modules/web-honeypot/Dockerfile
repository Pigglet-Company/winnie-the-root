FROM python:3.12.8-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Usuario sin privilegios; /uploads queda a su nombre (un volumen nuevo hereda este propietario)
RUN groupadd --system --gid 10001 hpweb \
 && useradd --system --uid 10001 --gid 10001 --no-create-home --shell /usr/sbin/nologin hpweb \
 && mkdir -p /app /uploads \
 && chown 10001:10001 /uploads \
 && chmod 0750 /uploads

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY app/ ./app/

USER 10001:10001
EXPOSE 8080

# Solo abre el socket (sin petición HTTP) para no ensuciar los logs con eventos de salud
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD ["python", "-c", "import socket; socket.create_connection(('127.0.0.1', 8080), 2).close()"]

# Un solo worker: la rotación de web.jsonl no es segura con varios procesos
CMD ["python", "-m", "uvicorn", "app.main:create_app", "--factory", \
     "--host", "0.0.0.0", "--port", "8080", \
     "--no-server-header", "--no-access-log", "--no-proxy-headers", "--ws", "none", \
     "--limit-concurrency", "256", "--timeout-keep-alive", "5", "--log-level", "warning"]
