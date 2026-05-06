#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${1:-http://localhost:8080}"
failed=0

check() {
  local name="$1"
  local path="$2"
  if curl -fsS "${BASE_URL}${path}" >/dev/null; then
    echo "${name}: OK"
  else
    echo "${name}: FAIL (${BASE_URL}${path})"
    failed=1
  fi
}

echo "Checking gateway and microservices via ${BASE_URL}..."
check "auth-service" "/api/auth/health"
check "user-service" "/api/users/health"
check "product-service" "/api/products/health"
check "order-service" "/api/orders/health"
check "chat-service" "/api/chat/health"

if [[ "${failed}" -eq 0 ]]; then
  echo "All health checks passed."
else
  echo "One or more health checks failed."
  exit 1
fi

