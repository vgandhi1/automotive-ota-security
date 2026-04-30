#!/usr/bin/env bash
# Smoke test: call presign API then HEAD the URL. With default compose, the URL
# host is "minio:9000" (reachable from containers); from the host, add a hosts
# entry or run this script inside a container on the compose network.
set -euo pipefail
BASE="${1:-http://localhost:8080}"
KEY="${2:-samples/hello.bin}"
API_KEY="${PRESIGN_API_KEY:-dev-local-key}"
resp="$(curl -fsS -X POST "${BASE}/v1/presign" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${API_KEY}" \
  -d "{\"object_key\":\"${KEY}\"}")"
url="$(python3 -c 'import json,sys; print(json.loads(sys.argv[1])["url"])' "${resp}")"
echo "Presigned URL issued (length ${#url}). Fetch head:"
curl -sI "${url}" | head -n 5
