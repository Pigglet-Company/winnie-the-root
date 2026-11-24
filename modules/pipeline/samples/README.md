# samples/

Primeras líneas de los logs sintéticos que genera `tools/generate_sample_data.py`
(formato NATIVO de Cowrie / OpenCanary y esquema común web). Sirven de referencia
del formato que consume el pipeline. Los logs completos (≥ 5000 eventos) se
generan con `python3 tools/generate_sample_data.py` en `./sample-logs/`.

El módulo C no produce ficheros de log, sino documentos en OpenSearch. Para
extraer ejemplos reales ya normalizados y clasificados (tras arrancar):

    python3 tools/export_events.py --format ndjson --out samples/normalized_events.ndjson
