#!/usr/bin/env bash
# Valida la configuración de Vector y ejecuta los tests unitarios:
#   vector/tests.yaml       rama sin GeoIP (siempre)
#   vector/tests_geo.yaml   rama GeoIP, solo si existe geoip/city.mmdb (scripts/download_geoip.sh);
#                           si falta, se anuncia como PENDIENTE y sale con 0
set -euo pipefail
cd "$(dirname "$0")/.."
IMAGE="timberio/vector:0.43.1-debian"   # misma versión que compose.yml

docker run --rm -v "$PWD/vector:/etc/vector:ro" --entrypoint vector "$IMAGE" \
  test /etc/vector/vector.yaml /etc/vector/final_nogeo.yaml /etc/vector/tests.yaml

if [ -s geoip/city.mmdb ]; then
  docker run --rm -v "$PWD/vector:/etc/vector:ro" -v "$PWD/geoip:/geoip:ro" --entrypoint vector "$IMAGE" \
    test /etc/vector/vector.yaml /etc/vector/final_geo.yaml /etc/vector/tests.yaml /etc/vector/tests_geo.yaml
else
  echo "PENDIENTE: rama GeoIP sin probar (falta geoip/city.mmdb; ejecuta scripts/download_geoip.sh)"
fi
