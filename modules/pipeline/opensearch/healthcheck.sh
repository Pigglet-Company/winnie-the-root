#!/bin/sh
# Healthcheck de pl-opensearch (valido en modo dev y prod).
curl -sk -u "admin:${OPENSEARCH_INITIAL_ADMIN_PASSWORD}" \
  "${OS_PROTO:-http}://localhost:9200/_cluster/health" | grep -Eq '"status":"(green|yellow)"'
