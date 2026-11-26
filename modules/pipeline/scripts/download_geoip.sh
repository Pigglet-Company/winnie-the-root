#!/usr/bin/env bash
# Descarga la base GeoIP a ./geoip/city.mmdb. Tras descargar:  docker compose restart pl-vector
#   ./scripts/download_geoip.sh   DB-IP IP to City Lite (por defecto; CC BY 4.0, sin cuenta)
#   Con MAXMIND_LICENSE_KEY (en .env o en el entorno) descarga MaxMind GeoLite2-City (EULA propia).
# Sin base, el pipeline funciona igual (sin campo geo).
# DB-IP exige atribución: "IP Geolocation by DB-IP" (https://db-ip.com), ver README del módulo.
set -euo pipefail
cd "$(dirname "$0")/.."

KEY="${MAXMIND_LICENSE_KEY:-}"
if [ -z "$KEY" ] && [ -f .env ]; then KEY="$(grep -E '^MAXMIND_LICENSE_KEY=' .env | tail -1 | cut -d= -f2- || true)"; fi

tmp="$(mktemp -d)"; trap 'rm -rf "${tmp:?}"' EXIT
if [ -n "$KEY" ]; then
  echo "Descargando MaxMind GeoLite2-City ..."
  curl -fsSL "https://download.maxmind.com/app/geoip_download?edition_id=GeoLite2-City&license_key=${KEY}&suffix=tar.gz" -o "$tmp/db.tgz"
  tar -xzf "$tmp/db.tgz" -C "$tmp"
  mmdb="$(find "$tmp" -name 'GeoLite2-City.mmdb' | head -1)"
  [ -n "$mmdb" ] || { echo "ERROR: el archivo no contiene GeoLite2-City.mmdb"; exit 1; }
else
  # DB-IP publica una edición al mes; al principio de mes puede no estar aún: se prueba la anterior.
  for month in "$(date -u +%Y-%m)" "$(date -u -d "$(date -u +%Y-%m-15) -1 month" +%Y-%m)"; do
    url="https://download.db-ip.com/free/dbip-city-lite-$month.mmdb.gz"
    echo "Descargando DB-IP IP to City Lite $month ..."
    curl -fsSL "$url" -o "$tmp/db.mmdb.gz" && break
    rm -f "$tmp/db.mmdb.gz"
  done
  [ -s "$tmp/db.mmdb.gz" ] || { echo "ERROR: no se pudo descargar DB-IP City Lite"; exit 1; }
  gzip -dc "$tmp/db.mmdb.gz" > "$tmp/db.mmdb"
  mmdb="$tmp/db.mmdb"
fi
grep -aq 'database_type' "$mmdb" || { echo "ERROR: el fichero descargado no parece una base MMDB"; exit 1; }
mkdir -p geoip && install -m 0644 "$mmdb" geoip/city.mmdb
echo "OK: geoip/city.mmdb ($(sha256sum geoip/city.mmdb | cut -c1-16)…). Reinicia Vector:  docker compose restart pl-vector"
