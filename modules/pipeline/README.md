# Módulo C — Pipeline (Vector + OpenSearch + Dashboards)

Lee los logs de los honeypots (volumen `honeylogs`, solo lectura), los **normaliza** al esquema común,
los **enriquece** (GeoIP opcional), los **clasifica** (`attack_type` + MITRE ATT&CK) y los indexa en
OpenSearch (`honeypot-events-YYYY.MM.DD`, alias `honeypot-events`, retención 30 días). Incluye dashboards.

```
Cowrie / OpenCanary / Web  ->  Vector (tail -> VRL -> clasificar -> geo) -> OpenSearch -> Dashboards :5601
                                   └─ errores -> /var/lib/vector/dead_letter/*.jsonl
```

## Requisitos
Docker + Compose v2, `python3` y `curl` en el host. Linux: `sudo sysctl -w vm.max_map_count=262144`.
Preparación: `cp .env.example .env` (ajusta si quieres).

## 1. Modo dev con datos sintéticos (sin módulos A y B)
```bash
cd modules/pipeline
cp .env.example .env
python3 tools/generate_sample_data.py          # ./sample-logs (≈6000 eventos, 7 días)
docker compose -f compose.yml -f compose.dev.yml up -d
./scripts/import_dashboards.sh                 # espera a Dashboards e importa
./tests/e2e_check.sh                           # verificación extremo a extremo
```
Abre <http://localhost:5601/app/dashboards#/view/hp-dashboard> (rango de tiempo: últimos 30 días).

## 2. Modo con logs reales (A y B escribiendo en `honeylogs`)
```bash
./scripts/init.sh            # en la raíz del repo (crea honeynet y honeylogs)
cd modules/pipeline && docker compose up -d
./scripts/import_dashboards.sh
```
Si Compose se queja de que `honeylogs` no existe: `docker volume create honeylogs`.

## 3. Seguridad: dev / prod
`SECURITY_MODE` en `.env`: `dev` (sin autenticación) o `prod` (autenticación + TLS interno). En prod,
define `OPENSEARCH_ADMIN_PASSWORD` y entra a Dashboards con `admin` (tenant **Global**). Tras cambiar de
modo: `docker compose down -v` (el volumen de datos cambia de esquema de seguridad). Detalles y límites en
`NOTAS_CONTRATO.md`. Dashboards solo escucha en `127.0.0.1:5601`; en un VPS accede con
`ssh -L 5601:127.0.0.1:5601 usuario@vps`. El heap se ajusta con `OPENSEARCH_HEAP` (por defecto `1g`).

## 4. GeoIP (opcional)
Pon `MAXMIND_LICENSE_KEY` en `.env`, ejecuta `./scripts/download_geolite.sh` y
`docker compose restart pl-vector`. Sin clave todo funciona, salvo mapa y países (paneles vacíos).

## 5. Dashboards
`dashboards/honeypot.ndjson` se genera con `python3 tools/build_dashboards.py`. Contiene: eventos totales,
serie por hora y por día, top `attack_type`, técnicas y tácticas MITRE, top IPs, mapa, países, usuarios,
contraseñas, comandos, paths y payloads web, tabla de sesiones y búsqueda guardada de detalle (drill-down:
clic en un valor → filtro). Filtros: selector de fechas, y controles de servicio, honeypot, tipo de ataque e IP.
Si algún panel pide campos, refresca el index pattern (Dashboards Management → Index patterns).

## 6. Ampliar las reglas de clasificación
Todo está en **`vector/rules/classify.vrl`** (comentado). Cada evento conserva el **hecho** observado
(`event_type`, `service`, `command`, `file.*`) y recibe aparte la **interpretación** ATT&CK (`attack_type`,
`mitre_*`) junto a la regla que la produjo:

| Campo | Significado |
|---|---|
| `rule.ruleset` / `rule.version` | Conjunto y versión de reglas (`winnie-legacy` / `RULES_VERSION`) |
| `rule.id` | Regla que decide `attack_type` (p. ej. `web.sqli`, `auth.login_attempt`); ausente si es `other` |
| `rule.matches` | Todas las reglas web que coinciden, en orden de precedencia (solapamientos) |

Precedencia web: `command_injection > lfi_rfi > sqli > xss > recon_scan`. Así `?host=1;cat /etc/passwd`
es `command_injection` y `rule.matches` conserva también `web.lfi_rfi`. Las conexiones desde loopback
(healthchecks de los contenedores) son `connection.sensor_health` con `attack_type=other`.

Los comandos Redis conservan la semántica de su servicio: `attack_type=redis_command`, `rule.id=redis.command`
y **sin técnica MITRE**. Es un comando del protocolo Redis, enviado sin login ni shell, y el señuelo solo lo
emula. No prueba ejecución en el host, así que T1059.004 (shell Unix) no se sostiene (diseño V2, «Adaptación de
eventos»). Los comandos de la shell emulada de Cowrie siguen siendo `post_exploitation_command`.

Para cambiar una regla: edítala, sube `RULES_VERSION`, añade casos positivos, negativos y de solape en
`vector/tests.yaml` y regenera el baseline:
```bash
./tests/run_vector_tests.sh             # vector test (casos positivos, negativos, solape e inocuos)
./tests/classify_samples.sh --write     # nuevo vector/baseline/winnie-legacy-<versión>.json; revisa el diff
./tests/classify_samples.sh             # compara las muestras de los paneles con el baseline (lo hace CI)
docker compose restart pl-vector
```
`classify_samples.sh` usa la imagen fijada de Vector con Docker, o `VECTOR_BIN=<binario>` sin Docker.

### Reglas: versiones y vuelta atrás

| Versión | Revisión | Notas |
|---|---|---|
| 1.2.0 | esta rama (W03) | Redis: `redis_command` sin MITRE (177 eventos de muestra dejan de ser `post_exploitation_command`) |
| 1.1.0 | `e6e5f8c` | Compila con Vector 0.43.1; añade `rule.*`, precedencia contextual y salud por loopback |
| 1.0.0 | `c81fdf0` | Última revisión validada antes de W03; mismos `attack_type` que 1.1.0 sobre las muestras, sin `rule.*` |

Volver a una versión conocida (los datos ya indexados se conservan; sustituye la revisión de la tabla):
```bash
git checkout e6e5f8c -- modules/pipeline/vector/rules/classify.vrl
docker compose restart pl-vector
```
Cada versión tiene su baseline en `vector/baseline/winnie-legacy-<versión>.json`. Compararlos muestra qué
cambia al volver atrás. 1.1.0 → 1.0.0 no cambia ningún recuento por `attack_type`, y 1.2.0 → 1.1.0 solo mueve
los 177 comandos Redis. Los tests de `vector/tests.yaml` escritos para la versión nueva fallarán con la antigua:
es lo esperado.
Los eventos ya indexados no se reclasifican (borra el índice y reinicia con `docker compose down -v` si necesitas
reprocesar; el `_id` determinista evita duplicados al releer).

## 7. Exportar datos para el informe
```bash
python3 tools/export_events.py --format csv --since 7d --out export-7d.csv
python3 tools/export_events.py --format ndjson --query 'attack_type:sqli' --out export-sqli.ndjson
```
También: en cualquier tabla de Dashboards, *Inspect → Download CSV*.

## Verificación rápida
```bash
docker compose ps                                   # pl-opensearch healthy; pl-setup/pl-perms exited 0
docker logs pl-vector | head                        # "GeoIP ACTIVADO/Sin ... " y sin errores
docker exec pl-opensearch curl -s localhost:9200/_cat/indices/honeypot-events-*?v   # (modo dev)
docker exec pl-vector sh -c 'wc -l /var/lib/vector/dead_letter/*.jsonl'   # líneas corruptas
```

## Estructura
`compose.yml`/`compose.dev.yml` · `env/` (variables por modo) · `opensearch/` (template, ISM, setup) ·
`vector/` (`vector.yaml`, `rules/*.vrl`, `tests.yaml`) · `dashboards/` · `scripts/` · `tools/` · `tests/` · `samples/`.
