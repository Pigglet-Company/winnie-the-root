#!/usr/bin/env bash
# Descarga GeoLite2-City.mmdb a ./geoip/ si hay MAXMIND_LICENSE_KEY (en .env o en el entorno).
# Sin clave no hace nada y el pipeline funciona igual (sin campo geo).
# Tras descargar:  docker compose restart pl-vector
set -euo pipefail
cd "$(dirname "$0")/.."

KEY="${MAXMIND_LICENSE_KEY:-}"
if [ -z "$KEY" ] && [ -f .env ]; then KEY="$(grep -E '^MAXMIND_LICENSE_KEY=' .env | tail -1 | cut -d= -f2- || true)"; fi
if [ -z "$KEY" ]; then
  echo "Sin MAXMIND_LICENSE_KEY: se omite GeoIP (el pipeline funciona sin campo geo)."; exit 0
fi

tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
echo "Descargando GeoLite2-City ..."
curl -fsSL "https://download.maxmind.com/app/geoip_download?edition_id=GeoLite2-City&license_key=${KEY}&suffix=tar.gz" -o "$tmp/db.tgz"
tar -xzf "$tmp/db.tgz" -C "$tmp"
mmdb="$(find "$tmp" -name 'GeoLite2-City.mmdb' | head -1)"
[ -n "$mmdb" ] || { echo "ERROR: el archivo no contiene GeoLite2-City.mmdb"; exit 1; }
mkdir -p geoip && install -m 0644 "$mmdb" geoip/GeoLite2-City.mmdb
echo "OK: geoip/GeoLite2-City.mmdb. Reinicia Vector:  docker compose restart pl-vector"
