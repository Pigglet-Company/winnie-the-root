# Módulo C — Pipeline (Vector + OpenSearch + Dashboards)

Los comandos que usan rutas relativas a este módulo se ejecutan desde `modules/pipeline/`, salvo donde se indique que el punto de partida es la raíz del repositorio. Consulta los [recursos compartidos](../../architecture.md#first-run).

Lee los logs de los honeypots (volumen `honeylogs`, solo lectura), los **normaliza** al esquema común,
los **enriquece** (GeoIP opcional), los **clasifica** (`attack_type` + MITRE ATT&CK) y los indexa en
OpenSearch (`honeypot-events-YYYY.MM.DD`, alias `honeypot-events`, retención 30 días). Incluye dashboards.

```
Cowrie / OpenCanary / Web  ->  Vector (tail -> VRL -> clasificar -> geo) -> OpenSearch -> Dashboards :5601
                                   └─ errores -> /var/lib/vector/dead_letter/*.jsonl
```

## Requisitos
Docker + Compose v2, `python3` y `curl` en el host. Linux: `sudo sysctl -w vm.max_map_count=262144`.
Los valores por defecto se declaran en Compose. Crea un `.env` local únicamente para sobrescribirlos.

## 1. Modo dev con datos sintéticos (sin módulos A y B)
```bash
cd modules/pipeline
docker volume create honeylogs                # volumen externo declarado por el modelo base
python3 tools/generate_sample_data.py          # ./sample-logs (≈6000 eventos, 7 días)
docker compose -f compose.yml -f compose.dev.yml up -d
./scripts/import_dashboards.sh                 # espera a Dashboards e importa
./tests/e2e_check.sh                           # verificación extremo a extremo
```
Abre <http://localhost:5601/app/dashboards#/view/hp-dashboard> (rango de tiempo: últimos 30 días).

## 2. Modo con logs reales (A y B escribiendo en `honeylogs`)
```bash
# Prepara los recursos compartidos según la guía de arquitectura.
cd modules/pipeline && docker compose up -d
./scripts/import_dashboards.sh
```
Si Compose se queja de que `honeylogs` no existe: `docker volume create honeylogs`.

## 3. Seguridad: dev / prod

El perfil `prod` conserva credenciales de administración y TLS de demostración. Consulta el [análisis](../../architecture-review.md) para evaluar su uso con datos reales.
`SECURITY_MODE` en `.env`: `dev` (sin autenticación) o `prod` (autenticación + TLS interno). En prod,
define `OPENSEARCH_ADMIN_PASSWORD` y entra a Dashboards con `admin` (tenant **Global**). Usa instalaciones desechables distintas para validar cada modo, pues el volumen de datos cambia de esquema de seguridad. Detalles y límites en
[notas de integración](integration-notes.md). Dashboards solo escucha en `127.0.0.1:5601`; en un VPS accede con
`ssh -L 5601:127.0.0.1:5601 usuario@vps`. El heap se ajusta con `OPENSEARCH_HEAP` (por defecto `1g`).

## 4. GeoIP (opcional)
`./scripts/download_geoip.sh` descarga **DB-IP IP to City Lite** (CC BY 4.0, sin cuenta) a `geoip/city.mmdb`;
después, `docker compose restart pl-vector`. Si `.env` tiene `MAXMIND_LICENSE_KEY`, descarga en su lugar
MaxMind GeoLite2-City (EULA de MaxMind: borrar versiones antiguas a los 30 días). Sin base todo funciona salvo
mapa y países (paneles vacíos). GeoIP es un enriquecimiento opcional y no cambia la clasificación.

**Atribución obligatoria (CC BY 4.0):** quien muestre o publique datos con GeoIP de DB-IP debe citar
«IP Geolocation by [DB-IP](https://db-ip.com)». La base no se sube al repositorio (`geoip/*.mmdb` está ignorado).
DB-IP publica una edición al mes: vuelve a ejecutar el script para actualizarla.

## 5. Dashboards
`dashboards/honeypot.ndjson` se genera con `python3 tools/build_dashboards.py`. Contiene: eventos totales,
serie por hora y por día, top `attack_type`, técnicas y tácticas MITRE, top IPs, mapa, países, usuarios,
contraseñas, comandos, paths y payloads web, tabla de sesiones y búsqueda guardada de detalle (drill-down:
clic en un valor → filtro). Filtros: selector de fechas, y controles de servicio, honeypot, tipo de ataque e IP.
Si algún panel pide campos, refresca el index pattern (Dashboards Management → Index patterns).

## 6. Ampliar las reglas de clasificación
Todo está en **`vector/rules/classify.vrl`** (comentado): añade una alternativa a la regex de la regla, o un
nuevo `else if match(...)` con su `attack_type`, y su par técnica/táctica en la tabla MITRE. Añade un caso en
`vector/tests.yaml` y ejecuta:
```bash
./tests/run_vector_tests.sh        # vector test (casos positivos y negativos)
docker compose restart pl-vector
```
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
