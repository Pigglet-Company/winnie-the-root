# NOTAS_CONTRATO.md – Módulo B (web-honeypot)

## Estado de verificación (importante)
- Entorno de desarrollo SIN red: no pude instalar FastAPI/pytest ni ejecutar Docker o `jq`.
- **Ejecutado y en verde:** 17 tests de `tests/test_core.py` (eventos, logger con rotación, rate limit, sesiones,
  simuladores SQLi/LFI/cmd y el middleware completo contra una app ASGI de juguete), validación del
  esquema sobre `samples/web.sample.jsonl`, `bash -n` sobre `smoke_web.sh`.
- **NO ejecutado:** `tests/test_routes.py` (necesita FastAPI + httpx), `tests/smoke_web.sh` (necesita jq + stack
  levantado), `docker compose build/up`. Están escritos con cuidado, pero hay que correrlos en tu máquina
  antes de darlos por buenos; si falla algo, probablemente sea un detalle de integración con Starlette.
- Versiones fijadas en `requirements.txt` (fastapi 0.115.6, starlette 0.41.3, uvicorn 0.34.0, python-multipart 0.0.20,
  pydantic 2.10.4) escritas de memoria; verifica que resuelven al hacer `docker compose build`.
- `samples/web.sample.jsonl` está generado con `tests/make_samples.py` (mismo constructor de eventos del módulo, IPs RFC 5737),
  no capturado de un contenedor en marcha.

## Suposiciones
1. **Una petición = un evento.** Un login es `auth_attempt` y una subida `file_upload` (con el bloque `http` completo);
   no se emite además un `request` duplicado.
2. `http.path`/`http.query` van decodificados una vez; `http.body` es texto UTF-8 con reemplazo en bytes inválidos (multipart incluido, truncado a 8 KB).
3. `session_id` solo se rellena para sesiones del panel falso. En el resto es `null`.
4. `file.url` es `null` en subidas (en el contrato es la URL de descarga origen). La URL falsa devuelta al atacante no se registra.
   Solo se procesa el **primer** fichero de una subida multi-fichero.
5. Fichero subido > 2 MB: 413 y evento `file_upload` con `sha256`/`size` = `null`. Body > `MAX_BODY_BYTES` (64 KB; `/upload` admite 2 MB + 256 KB): 413 con evento `request`.
6. Si se alcanzan `UPLOAD_MAX_FILES`/`UPLOAD_MAX_TOTAL_BYTES` se finge éxito pero no se guarda (el sha256 sigue en el log).
7. El volumen de subidas es un named volume (`hp-web-uploads`) con permisos `0640`; no se monta `noexec` (los volúmenes nombrados no lo permiten sin driver_opts). `/tmp` sí es tmpfs `noexec`.
8. `dst_port` es el puerto del socket dentro del contenedor (8080); en producción con 80→8080 seguirá siendo 8080.
9. Rate limit por defecto holgado (300/min, ráfaga 100) para no espantar a los atacantes; cuando salta, responde 429 y se registra.
10. `compose.yml` usa `env_file` con `required: false` (Compose ≥ 2.24). `ports` usa `${WEB_HOST_PORT:-8080}`.
11. El `compose.yml` del módulo no declara `name:` para poder incluirse con `include` desde la raíz.

## Dudas para integración
- ¿Prefiere C leer `src_port: null` (con proxy) o un valor 0? Se deja `null`.
- `X-Forwarded-For` toma la ÚLTIMA entrada (un solo proxy de confianza). Si habrá cadena de proxies, hay que ajustarlo.
- El volumen `honeylogs` con `0777` (solo desarrollo): el contenedor escribe como UID 10001; al endurecer, `chown 10001` en `/logs/web`.
  Resuelto en W04: un volumen por fuente; ver docs/lab-containment.md.
- Las reglas de C deberían contemplar `User-Agent` de herramientas y payloads con doble codificación (`%252e`).
- `COMMENT_CSP` vacío deja el XSS reflejado ejecutable en el navegador del atacante (intencionado); pon una CSP si prefieres neutralizarlo.
