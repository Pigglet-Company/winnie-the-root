#!/bin/sh
# Elige la etapa final (con o sin GeoIP) y arranca Vector.
set -eu

if [ -s /geoip/GeoLite2-City.mmdb ]; then
  echo "[entrypoint] GeoLite2 encontrado: GeoIP ACTIVADO"
  cp /etc/vector/final_geo.yaml /tmp/final.yaml
else
  echo "[entrypoint] Sin /geoip/GeoLite2-City.mmdb: se indexa SIN campo geo (ver scripts/download_geolite.sh)"
  cp /etc/vector/final_nogeo.yaml /tmp/final.yaml
fi

exec vector --config /etc/vector/vector.yaml --config /tmp/final.yaml
