# NOTAS_CONTRATO.md — Módulo A (ssh-honeypot)

No he modificado el contrato. Suposiciones y dudas:

## Verificar al primer arranque (no he podido ejecutar Docker al escribir esto)
1. **Tags de imagen**: `cowrie/cowrie:v2.6.1`, `python:3.11.11-slim-bookworm`, `opencanary==0.9.4`, `busybox:1.36`.
   Compruébalos con `docker pull` y ajusta si alguno no existe.
2. **Rutas internas de Cowrie** (`/cowrie/cowrie-git/etc|var|honeyfs`) y que el ENTRYPOINT arranque con los montajes.
3. **Imagen de Cowrie sin shell** (supuesto): por eso el healthcheck usa su Python y los tests leen el volumen con busybox.
4. **`read_only: true` en Cowrie**: si falla, quitarlo solo ahí.
5. **OpenCanary**: sin imagen oficial no-root, se construye con Dockerfile propio; ruta de config `/etc/opencanaryd/opencanary.conf`
   y arranque `opencanaryd --dev`. Python 3.11 (no 3.12) por compatibilidad de dependencias. El contrato exige 3.12 para nuestro código; esto es una imagen de terceros.
6. Nombres de campos de `logdata` de OpenCanary (MySQL: USERNAME/PASSWORD/SALT; Redis: CMD/ARGS) y evento
   `cowrie.session.file_download.failed`, escritos de memoria.

## Decisiones
- **IPs fijas** `172.30.0.10` (Cowrie) y `172.30.0.11` (OpenCanary), necesarias para el DNAT de producción.
  Propongo reservar `172.30.0.10–19` para A y que B use `.20+`.
- **Producción: DNAT, no `REDIRECT`**: con Docker, `REDIRECT 22→2222` terminaría en `docker-proxy` y el honeypot vería
  siempre `172.30.0.1` como origen. El `compose.yml` no cambia entre local y producción.
- **Rotación (§5)**: OpenCanary cumple 50 MB × 5 (`RotatingFileHandler`). Cowrie rota a diario de forma nativa y no por tamaño;
  `copytruncate` de logrotate dejaría huecos de NULs (Twisted abre el fichero sin `O_APPEND`). En el VPS se borran los ficheros
  con más de 5 días. Un día de tráfico podría superar los 50 MB en un VPS muy expuesto.
- **Descargas sin `noexec`**: `cowrie-data` es un volumen nombrado; `noexec` a nivel de compose no es posible.
  Mitigación: Cowrie no crea ficheros ejecutables, nada los ejecuta, rootfs de solo lectura, `cap_drop ALL`.
- `scripts/init.sh` del contrato **no es idempotente**; `setup.sh` solo lo invoca si falta la red o el volumen.
- `busybox` en `init.sh` va sin versión (contrato §3); en mi módulo uso `busybox:1.36`.
- `include` del `docker-compose.yml` raíz: las rutas relativas del `compose.yml` se resuelven respecto a su carpeta (Compose ≥ 2.20).

## Para el módulo C (normalización de lo nativo)
- Cowrie: `timestamp` con microsegundos y `Z` → truncar a milisegundos para `@timestamp`.
  `session` → `session_id`; `protocol` (ssh/telnet) → `service`; `eventid` → `event_type`:
  `cowrie.session.connect→connection`, `cowrie.login.*→auth_attempt` (`success` según el evento),
  `cowrie.command.input→command`, `cowrie.session.file_download*→file_download`, `cowrie.session.closed→session_close`.
- `duration` de Cowrie llega como **string** (`"41.4"`): convertir a número para `duration_s`.
- OpenCanary: `logtype` 2000 = FTP login, 8001 = MySQL login, 17001 = Redis command; `utc_time` sin `Z` (es UTC);
  `node_id` = `srv-prod-01`; `src_host`/`dst_host` → `src_ip`/`dst_host`.
- En pruebas locales `src_ip` = `172.30.0.1`; en producción, la IP real del atacante.
- Con el egress bloqueado no habrá `cowrie.session.file_download` con hash, solo `...file_download.failed` y la URL en el comando.

## Dudas
- El UID final de Cowrie lo define la imagen. Al endurecer el `0777` de `honeylogs` habrá que dar permisos al UID de Cowrie y al `10001` de OpenCanary.
  Resuelto en W04: un volumen por fuente; ver docs/lab-containment.md.
- ¿Contempla el módulo B reservar su propio rango de IPs en `honeynet`?
