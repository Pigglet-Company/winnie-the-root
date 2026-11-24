#!/usr/bin/env python3
"""Genera dashboards/honeypot.ndjson (objetos guardados de OpenSearch Dashboards 2.x).

    python3 tools/build_dashboards.py

El NDJSON resultante se importa con scripts/import_dashboards.sh (que antes crea
el index pattern "honeypot-events*", id "honeypot-events", campo temporal @timestamp).
Si quieres cambiar o añadir paneles, edita este fichero y vuelve a ejecutarlo.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

IDX = "honeypot-events"
UPDATED = "2026-11-23T00:00:00.000Z"
NOT_OTHER = 'NOT attack_type:"other"'

objects: list[dict[str, Any]] = []
panels: list[tuple[str, str, dict[str, int]]] = []     # (tipo, id, gridData)


def index_ref() -> list[dict[str, str]]:
    return [{"name": "kibanaSavedObjectMeta.searchSourceJSON.index", "type": "index-pattern", "id": IDX}]


def search_source(query: str = "") -> str:
    return json.dumps({"query": {"query": query, "language": "kuery"}, "filter": [],
                       "indexRefName": "kibanaSavedObjectMeta.searchSourceJSON.index"})


# ------------------------------------------------------------------ agregaciones
COUNT = {"id": "1", "enabled": True, "type": "count", "schema": "metric", "params": {}}


def terms(agg_id: str, field: str, schema: str = "segment", size: int = 10, label: str | None = None) -> dict[str, Any]:
    params: dict[str, Any] = {"field": field, "orderBy": "1", "order": "desc", "size": size, "otherBucket": False,
                              "otherBucketLabel": "Otros", "missingBucket": False, "missingBucketLabel": "Sin dato"}
    if label:
        params["customLabel"] = label
    return {"id": agg_id, "enabled": True, "type": "terms", "schema": schema, "params": params}


def date_hist(agg_id: str, interval: str) -> dict[str, Any]:
    return {"id": agg_id, "enabled": True, "type": "date_histogram", "schema": "segment",
            "params": {"field": "@timestamp", "useNormalizedEsInterval": True, "useNormalizedOpenSearchInterval": True,
                       "scaleMetricValues": False, "interval": interval, "drop_partials": False,
                       "min_doc_count": 1, "extended_bounds": {}}}


# ------------------------------------------------------------------ parámetros por tipo
def xy_params(kind: str, horizontal: bool = False, stacked: bool = True) -> dict[str, Any]:
    return {
        "type": kind, "grid": {"categoryLines": False},
        "categoryAxes": [{"id": "CategoryAxis-1", "type": "category", "position": "left" if horizontal else "bottom",
                          "show": True, "style": {}, "scale": {"type": "linear"},
                          "labels": {"show": True, "filter": True, "truncate": 100}, "title": {}}],
        "valueAxes": [{"id": "ValueAxis-1", "name": "LeftAxis-1", "type": "value",
                       "position": "bottom" if horizontal else "left", "show": True, "style": {},
                       "scale": {"type": "linear", "mode": "normal"},
                       "labels": {"show": True, "rotate": 0, "filter": False, "truncate": 100},
                       "title": {"text": "Eventos"}}],
        "seriesParams": [{"show": True, "type": kind if kind != "horizontal_bar" else "histogram",
                          "mode": "stacked" if stacked else "normal",
                          "data": {"label": "Eventos", "id": "1"}, "valueAxis": "ValueAxis-1",
                          "drawLinesBetweenPoints": True, "lineWidth": 2, "showCircles": True}],
        "addTooltip": True, "addLegend": True, "legendPosition": "right", "times": [],
        "addTimeMarker": False, "labels": {"show": False}, "thresholdLine": {"show": False, "value": 10, "width": 1, "style": "full", "color": "#E7664C"},
    }


PIE = {"type": "pie", "addTooltip": True, "addLegend": True, "legendPosition": "right", "isDonut": True,
       "labels": {"show": False, "values": True, "last_level": True, "truncate": 100}}
TABLE = {"perPage": 10, "showPartialRows": False, "showMetricsAtAllLevels": False,
         "sort": {"columnIndex": None, "direction": None}, "showTotal": False, "totalFunc": "sum"}
METRIC = {"addTooltip": True, "addLegend": False, "type": "metric",
          "metric": {"percentageMode": False, "useRanges": False, "colorSchema": "Green to Red",
                     "metricColorMode": "None", "colorsRange": [{"from": 0, "to": 10000}], "labels": {"show": True},
                     "invertColors": False, "style": {"bgFill": "#000", "bgColor": False, "labelColor": False,
                                                      "subText": "", "fontSize": 52}}}
TILE_MAP = {"colorSchema": "Yellow to Red", "mapType": "Scaled Circle Markers", "isDesaturated": True,
            "addTooltip": True, "heatClusterSize": 1.5, "legendPosition": "bottomright", "mapZoom": 2,
            "mapCenter": [20, 0], "wms": {"enabled": False, "options": {"format": "image/png", "transparent": True}}}


def vis(vid: str, title: str, vtype: str, params: dict[str, Any], aggs: list[dict[str, Any]],
        grid: dict[str, int], query: str = "") -> None:
    state = {"title": title, "type": vtype, "params": params, "aggs": aggs}
    objects.append({
        "id": vid, "type": "visualization",
        "attributes": {"title": title, "visState": json.dumps(state), "uiStateJSON": "{}", "description": "",
                       "version": 1, "kibanaSavedObjectMeta": {"searchSourceJSON": search_source(query)}},
        "references": index_ref(), "migrationVersion": {"visualization": "7.10.0"}, "updated_at": UPDATED})
    panels.append(("visualization", vid, grid))


def g(x: int, y: int, w: int, h: int) -> dict[str, int]:
    return {"x": x, "y": y, "w": w, "h": h}


# ============================================================ VISUALIZACIONES
# Fila 0: filtros (fechas = selector de tiempo del dashboard)
controls = [("1", "service", "Servicio"), ("2", "honeypot", "Honeypot"),
            ("3", "attack_type", "Tipo de ataque"), ("4", "src_ip", "IP origen")]
vis("hp-controls", "Filtros (servicio, honeypot, tipo de ataque, IP)", "input_control_vis",
    {"controls": [{"id": cid, "indexPattern": IDX, "fieldName": field, "parent": "", "label": label, "type": "list",
                   "options": {"type": "terms", "multiselect": True, "dynamicOptions": True, "size": 20, "order": "desc"}}
                  for cid, field, label in controls],
     "updateFiltersOnChange": True, "useTimeFilter": True, "pinFilters": False},
    [], g(0, 0, 48, 7))

# Fila 1: KPIs
vis("hp-total", "Eventos totales", "metric", METRIC, [COUNT], g(0, 7, 8, 9))
vis("hp-by-service", "Eventos por servicio", "pie", PIE, [COUNT, terms("2", "service")], g(8, 7, 10, 9))
vis("hp-attack-type", "Top attack_type", "pie", PIE, [COUNT, terms("2", "attack_type", size=12)], g(18, 7, 15, 9), NOT_OTHER)
vis("hp-mitre-tactic", "Tácticas MITRE ATT&CK", "pie", PIE, [COUNT, terms("2", "mitre_tactic")], g(33, 7, 15, 9))

# Fila 2: series temporales
vis("hp-ts-hour", "Eventos por hora (por honeypot)", "histogram", xy_params("histogram"),
    [COUNT, date_hist("2", "h"), terms("3", "honeypot", schema="group")], g(0, 16, 24, 13))
vis("hp-ts-day", "Eventos por día (por tipo de ataque)", "histogram", xy_params("histogram"),
    [COUNT, date_hist("2", "d"), terms("3", "attack_type", schema="group", size=12)], g(24, 16, 24, 13))

# Fila 3: geografía + atacantes
vis("hp-map", "Mapa de atacantes (requiere GeoIP)", "tile_map", TILE_MAP,
    [COUNT, {"id": "2", "enabled": True, "type": "geohash_grid", "schema": "segment",
             "params": {"field": "geo.location", "autoPrecision": True, "isFilteredByCollar": True,
                        "useGeocentroid": True, "mapZoom": 2, "mapCenter": [0, 0], "precision": 2}}],
    g(0, 29, 22, 15))
vis("hp-top-ips", "Top IPs atacantes", "table", TABLE,
    [COUNT, terms("2", "src_ip", schema="bucket", size=15, label="IP origen")], g(22, 29, 13, 15))
vis("hp-countries", "Top países (requiere GeoIP)", "horizontal_bar", xy_params("horizontal_bar", True, False),
    [COUNT, terms("2", "geo.country_name", size=10)], g(35, 29, 13, 15))

# Fila 4: MITRE + credenciales
vis("hp-mitre-tech", "Top técnicas MITRE ATT&CK", "horizontal_bar", xy_params("horizontal_bar", True, False),
    [COUNT, terms("2", "mitre_technique", size=12)], g(0, 44, 16, 14))
vis("hp-top-users", "Top usuarios probados", "horizontal_bar", xy_params("horizontal_bar", True, False),
    [COUNT, terms("2", "auth.username", size=12)], g(16, 44, 16, 14))
vis("hp-top-passwords", "Top contraseñas probadas", "horizontal_bar", xy_params("horizontal_bar", True, False),
    [COUNT, terms("2", "auth.password", size=12)], g(32, 44, 16, 14))

# Fila 5: comandos y web
vis("hp-top-commands", "Top comandos ejecutados (SSH/Telnet/Redis)", "table", TABLE,
    [COUNT, terms("2", "command.keyword", schema="bucket", size=20, label="Comando")], g(0, 58, 24, 15),
    "event_type:command")
vis("hp-top-paths", "Top paths (web)", "horizontal_bar", xy_params("horizontal_bar", True, False),
    [COUNT, terms("2", "http.path.keyword", size=12)], g(24, 58, 12, 15), "honeypot:web")
vis("hp-top-payloads", "Top payloads / querystrings (web)", "table", TABLE,
    [COUNT, terms("2", "http.query.keyword", schema="bucket", size=15, label="Query")], g(36, 58, 12, 15),
    "honeypot:web and http.query:*")

# Fila 6: sesiones (resumen) -> la búsqueda guardada de abajo da el detalle
vis("hp-sessions", "Sesiones (resumen; clic en session_id para filtrar)", "table",
    {**TABLE, "perPage": 15},
    [COUNT,
     {"id": "3", "enabled": True, "type": "max", "schema": "metric",
      "params": {"field": "duration_s", "customLabel": "Duración máx. (s)"}},
     terms("2", "session_id", schema="bucket", size=100, label="Sesión"),
     terms("4", "src_ip", schema="bucket", size=1, label="IP"),
     terms("5", "service", schema="bucket", size=1, label="Servicio")],
    g(0, 73, 48, 15), "session_id:*")

# Búsqueda guardada: detalle de eventos con drill-down
objects.append({
    "id": "hp-search-events", "type": "search",
    "attributes": {
        "title": "Detalle de eventos (drill-down por sesión / IP)", "description": "", "hits": 0,
        "columns": ["session_id", "honeypot", "service", "event_type", "src_ip", "attack_type",
                    "auth.username", "auth.password", "command", "http.path", "http.query"],
        "sort": [["@timestamp", "desc"]], "version": 1,
        "kibanaSavedObjectMeta": {"searchSourceJSON": search_source("")}},
    "references": index_ref(), "migrationVersion": {"search": "7.9.3"}, "updated_at": UPDATED})
panels.append(("search", "hp-search-events", g(0, 88, 48, 22)))

# ============================================================ DASHBOARD
panel_defs = []
refs = []
for i, (ptype, pid, grid) in enumerate(panels):
    panel_defs.append({"version": "7.10.2", "gridData": {**grid, "i": str(i)}, "panelIndex": str(i),
                       "embeddableConfig": {}, "panelRefName": f"panel_{i}"})
    refs.append({"name": f"panel_{i}", "type": ptype, "id": pid})

objects.append({
    "id": "hp-dashboard", "type": "dashboard",
    "attributes": {
        "title": "Honeypot TFM - Visión general",
        "description": "Eventos, ataques, MITRE ATT&CK, atacantes, credenciales, comandos y web de los honeypots.",
        "hits": 0, "panelsJSON": json.dumps(panel_defs),
        "optionsJSON": json.dumps({"hidePanelTitles": False, "useMargins": True}),
        "version": 1, "timeRestore": True, "timeFrom": "now-30d", "timeTo": "now",
        "refreshInterval": {"pause": True, "value": 0},
        "kibanaSavedObjectMeta": {"searchSourceJSON": json.dumps({"query": {"language": "kuery", "query": ""}, "filter": []})}},
    "references": refs, "migrationVersion": {"dashboard": "7.9.3"}, "updated_at": UPDATED})

out = Path(__file__).resolve().parent.parent / "dashboards" / "honeypot.ndjson"
out.write_text("\n".join(json.dumps(o, ensure_ascii=False) for o in objects) + "\n", encoding="utf-8")
print(f"{len(objects)} objetos escritos en {out}")
