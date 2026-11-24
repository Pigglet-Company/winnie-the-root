#!/usr/bin/env bash
# Valida la configuración de Vector y ejecuta los tests unitarios (vector/tests.yaml).
set -euo pipefail
cd "$(dirname "$0")/.."
IMAGE="timberio/vector:0.43.1-debian"   # misma versión que compose.yml

docker run --rm -v "$PWD/vector:/etc/vector:ro" --entrypoint vector "$IMAGE" \
  test /etc/vector/vector.yaml /etc/vector/final_nogeo.yaml /etc/vector/tests.yaml
