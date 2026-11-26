# NOTAS_CONTRATO.md — Módulo C (pipeline)

## Estado de verificación (leer primero)
Se validó en el entorno de desarrollo: sintaxis de YAML/JSON/bash/Python, generador de datos
(6002 eventos indexables, 7 líneas corruptas) y coherencia interna del NDJSON de dashboards.
**No se pudo ejecutar** Docker, Vector, OpenSearch ni Dashboards allí: `vector test`, `e2e_check.sh`
y la importación de dashboards están escritos pero sin ejecutar. Si `vector test` se queja de
alguna función VRL o de la sintaxis de `extract_from: <transform>.dropped`, ajustar es local
(ficheros `vector/rules/*.vrl` y `vector/tests.yaml`).

## Suposiciones
1. **Contenedores extra** con prefijo `pl-`: `pl-perms` (root, una vez, chown del volumen de Vector) y
   `pl-setup` (plantilla/ISM). Ambos terminan y no publican puertos. Red propia `pl-internal` (sin Internet)
   y `pl-frontend` (solo para publicar Dashboards en 127.0.0.1:5601). C no usa `honeynet`.
2. **Telnet vs SSH en Cowrie**: solo `cowrie.session.connect` indica el protocolo. Un transform Lua guarda
   el protocolo por sesión; si Vector arranca a mitad de una sesión, sus eventos salen como `ssh`.
3. **Todo login** (también `cowrie.login.success`) se clasifica `brute_force`; `credential_stuffing` queda
   previsto pero desactivado (requiere agregación temporal).
4. `connection` → `recon_scan`; `session_close` → `other` (sin MITRE). Los dashboards de attack_type excluyen `other`.
5. **event_id determinista** para lo nativo (formato UUID v4 derivado del SHA-256 de la línea) → reiniciar
   Vector o releer ficheros no duplica documentos. Web conserva el UUID de B.
6. **Índice diario por fecha del evento** (campo auxiliar `idx`, no indexado), no por hora de ingesta;
   `doc_id` = `event_id` como `_id`.
7. **OpenCanary**: logtypes asumidos de `opencanary/logger.py` (2000 FTP, 8001 MySQL, 17001 Redis,
   4000-4002 SSH, 6001 Telnet, 3000/3001 HTTP; ≥2000 desconocidos → `connection` por puerto).
   Redis: claves `CMD`/`ARGS` en `logdata`. `dst_port` se guarda tal cual lo registra OpenCanary
   (puerto interno del contenedor: 21/3306/6379), no el publicado en el host.
8. **Cola de eventos fallidos**: (a) líneas ilegibles o que incumplen el esquema mínimo →
   `/var/lib/vector/dead_letter/errors-YYYY-MM-DD.jsonl`; (b) OpenSearch caído → buffer en disco (512 MB)
   con reintentos y acks. Los rechazos 400 del propio OpenSearch (mapping) solo se registran en el log de Vector.
9. **Retención ISM** se calcula sobre la edad del índice (momento de creación), no sobre la fecha de los
   eventos: los índices de datos sintéticos antiguos se borrarán 30 días después de crearse.
10. **Modo prod**: usa los certificados de demo de OpenSearch (TLS interno, sin verificar) y `admin` como
    usuario de Dashboards; `pl-setup` borra los usuarios demo borrables, pero `kibanaserver` (reservado) conserva
    su contraseña por defecto. Para producción real, montar un `internal_users.yml` propio. Con multitenancy,
    elegir el tenant **Global** al entrar. Dashboards solo escucha en 127.0.0.1 (acceder por túnel SSH).
11. **GeoIP**: la descarga usa la URL con `license_key` de MaxMind; si MaxMind la restringe, usar `geoipupdate`
    y dejar el .mmdb en `geoip/`.
12. `modules/pipeline/samples/` contiene entradas nativas de ejemplo, no salida normalizada (ver su README).

## Dudas para integración
- ¿Debe C crear `honeylogs` si no existe? Se asume que lo hace `scripts/init.sh`.
  Resuelto en W04: un volumen por fuente; ver docs/lab-containment.md.
- Host: `vm.max_map_count=262144` en Linux (`sudo sysctl -w vm.max_map_count=262144`).
- Si A añade OpenCanary SSH/HTTP, ya están mapeados.
