# Módulo B – Señuelo web (`modules/web-honeypot/`)

Aplicación web señuelo con aspecto de **intranet corporativa vulnerable** ("Nexora Industries", ficticia).
Registra **cada petición** en el esquema común en `/logs/web/web.jsonl`. **No clasifica ataques**
(eso lo hace el módulo C). Contenedor `hp-web`, FastAPI + Uvicorn, puerto interno 8080.

> Todo es SIMULADO: nunca se ejecuta input del atacante, nunca se lee un fichero real del host,
> nunca se hacen conexiones salientes. Datos y credenciales son 100 % ficticios.

## Estructura

```
modules/web-honeypot/
├── compose.yml  Dockerfile  requirements*.txt  pytest.ini  .env.example  .dockerignore
├── app/        main.py (fábrica) · routes.py · middleware.py · pages.py · events.py
│               event_logger.py · ratelimit.py · sessions.py · config.py
│   └── sim/    sql.py · lfi.py · cmd.py · data.py   (simuladores, solo texto)
├── tests/      test_core.py · test_routes.py · conftest.py · schema.py · smoke_web.sh · make_samples.py
├── samples/    web.sample.jsonl   (41 líneas)
└── NOTAS_CONTRATO.md
```

## Arranque (local)

```bash
# 1) Una sola vez, desde la raíz del repo (crea red "honeynet" y volumen "honeylogs")
./scripts/init.sh

# 2) Módulo B
cd modules/web-honeypot
cp .env.example .env            # opcional: ajusta WEAK_PASS, etc.
docker compose up -d --build
```

La web queda en <http://localhost:8080>. Parar: `docker compose down` (los volúmenes se conservan).

## Rutas señuelo

| Ruta | Qué simula | Evento |
|---|---|---|
| `/`, `/index.php` | Portada de la intranet | `request` |
| `/login`, `/admin`, `/wp-login.php`, `/phpmyadmin/` | Logins falsos. Siempre fallan salvo la credencial débil de `.env`, que redirige (302 + cookie `PHPSESSID`) a `/panel` falso. También se registran credenciales por query o `Authorization: Basic` | `auth_attempt` |
| `/search?q=` | SQLi estilo MySQL: errores 1064/1222/1054/1105, `UNION SELECT` con filas falsas, `' OR 1=1` → tabla de usuarios con hashes, blind booleano y `SLEEP()` (acotado) | `request` |
| `/view?file=` | LFI/traversal contra un **diccionario en memoria** (`/etc/passwd` falso, `config.php` falso, `php://filter`…). `/etc/shadow` → *Permission denied*; URLs (RFI) rechazadas | `request` |
| `/ping?host=` | Command injection: ping falso y, con `; \| && $()` + `id`, `whoami`, `uname`, `cat`…, salida falsa. No ejecuta nada | `request` |
| `/comment` | XSS reflejado **solo** en la respuesta al solicitante; no se guarda ni se muestra a otros | `request` |
| `/upload` | Acepta cualquier fichero (≤ 2 MB): nombre aleatorio, permisos `0640`, volumen aislado, **nunca se sirve**; responde con URL falsa | `file_upload` |
| `/robots.txt`, `/.env`, `/.git/config`, `/.git/HEAD`, `/backup.zip` (ZIP vacío de 22 bytes), `/server-status` | "Descuidos" para escáneres (credenciales FALSAS) | `request` |
| cualquier otra | 404/405/500 con el formato de Apache 2.4 | `request` |

`/docs`, `/redoc` y `/openapi.json` están desactivados (delatarían FastAPI). Cabeceras: `Server: Apache/2.4.41 (Ubuntu)`, `X-Powered-By: PHP/7.4.3`.

## Qué se registra

Una línea JSON por petición (UTF-8, flush inmediato, hora UTC, rotación 50 MB × 5) con: `@timestamp`, `event_id` (uuid4),
`honeypot:"web"`, `service:"http"`, `event_type`, `src_ip`, `src_port`, `dst_port`, `session_id` y `http{method,path,query,headers,body≤8 KB,user_agent,status}`;
más `auth{}` o `file{name,sha256,size,url}` según el caso. Ver `samples/web.sample.jsonl`.

* **IP de origen**: la del socket. `X-Forwarded-For` solo si `TRUST_PROXY=true` (entonces se usa la **última** entrada, la añadida por tu proxy, y `src_port` es `null`).
* `http.path` y `http.query` se guardan **decodificados una vez** (p. ej. `q=1' OR 1=1--`); el módulo C debería decodificar de nuevo para payloads con doble codificación.
* `session_id`: solo existe tras entrar con la credencial débil (cookie `PHPSESSID` válida del panel falso).
* Las peticiones bloqueadas (429, 413, 408…) también se registran.
* Un fallo de logging nunca tumba la app (aviso por stderr; si no se puede abrir el fichero, los eventos van a stderr).
* Limitación: peticiones HTTP malformadas que Uvicorn rechaza antes de llegar a la app no generan evento.

## Variables `.env`

Ver `.env.example`. Principales: `WEB_HOST_PORT`, `SERVER_HEADER`, `POWERED_BY`, `WEAK_USER`/`WEAK_PASS` (vacío = desactivada),
`TRUST_PROXY`, `LOG_*`, `UPLOAD_*` (tope por fichero, nº y espacio total), `MAX_BODY_BYTES`, `BODY_READ_TIMEOUT_S`,
`REQUEST_TIMEOUT_S`, `RATE_LIMIT_PER_MIN`/`RATE_LIMIT_BURST` (token bucket por IP; 0 = sin límite), `SLEEP_CAP_S`, `COMMENT_CSP`.

## Seguridad del contenedor

Usuario 10001 sin root · `cap_drop: ALL` · `no-new-privileges` · `read_only` (+ `/tmp` tmpfs `noexec`) · 0,5 CPU / 256 MB / 128 PIDs ·
imagen `python:3.12.8-slim-bookworm` y dependencias con versión fija · solo en `honeynet` · sin `docker.sock` ·
uploads en el volumen propio `hp-web-uploads` (solo lo monta este contenedor) · un único worker (la rotación no es segura con varios).

## Verificación

```bash
docker compose ps                                   # hp-web  Up (healthy)
curl -i http://localhost:8080/                      # 200, Server: Apache/2.4.41 (Ubuntu)
docker exec hp-web tail -n 3 /logs/web/web.jsonl    # eventos recientes
# o desde fuera del contenedor, tal como lo verá el módulo C (solo lectura):
docker run --rm -v honeylogs:/logs:ro busybox tail -n 3 /logs/web/web.jsonl

# Smoke test (necesita curl, jq y docker); debe terminar en "OK"
tests/smoke_web.sh                                  # BASE_URL, CONTAINER o LOG_FILE configurables

# Tests unitarios
python3.12 -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt
pytest -q
```

Regenerar las muestras: `python -m tests.make_samples`.

**Nota Docker Desktop (macOS/Windows):** `src_ip` suele aparecer como la IP de la pasarela (p. ej. `172.30.0.1`); en un VPS Linux con puertos publicados se ve la IP real.
