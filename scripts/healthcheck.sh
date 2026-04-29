#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${1:-http://localhost:8080}"

echo "Checking gateway and microservices via ${BASE_URL}..."
curl -fsS "${BASE_URL}/api/auth/health" >/dev/null && echo "auth-service: OK"
curl -fsS "${BASE_URL}/api/users/health" >/dev/null && echo "user-service: OK"
curl -fsS "${BASE_URL}/api/products/health" >/dev/null && echo "product-service: OK"
curl -fsS "${BASE_URL}/api/orders/health" >/dev/null && echo "order-service: OK"
curl -fsS "${BASE_URL}/api/chat/health" >/dev/null && echo "chat-service: OK"

echo "All health checks passed."

