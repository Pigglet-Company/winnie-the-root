#!/bin/sh
# Elige la etapa final (con o sin GeoIP) y arranca Vector.
set -eu

DB=/geoip/city.mmdb
[ -s "$DB" ] || [ ! -s /geoip/GeoLite2-City.mmdb ] || DB=/geoip/GeoLite2-City.mmdb   # nombre anterior
if [ -s "$DB" ]; then
  echo "[entrypoint] $DB encontrado: GeoIP ACTIVADO"
  sed "s#/geoip/city.mmdb#$DB#" /etc/vector/final_geo.yaml > /tmp/final.yaml
else
  echo "[entrypoint] Sin /geoip/city.mmdb: se indexa SIN campo geo (ver scripts/download_geoip.sh)"
  cp /etc/vector/final_nogeo.yaml /tmp/final.yaml
fi

exec vector --config /etc/vector/vector.yaml --config /tmp/final.yaml
