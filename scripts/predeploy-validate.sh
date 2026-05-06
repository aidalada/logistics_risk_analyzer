#!/usr/bin/env bash
set -euo pipefail

ENV_FILE="${1:-.env}"

required_vars=(
  "DATABASE_URL"
  "SECRET_KEY"
  "ALGORITHM"
  "ACCESS_TOKEN_EXPIRE_MINUTES"
)

fail() {
  echo "[predeploy-check] ERROR: $1" >&2
  exit 1
}

warn() {
  echo "[predeploy-check] WARNING: $1" >&2
}

echo "[predeploy-check] validating environment file: ${ENV_FILE}"

if [[ ! -f "${ENV_FILE}" ]]; then
  fail "Environment file '${ENV_FILE}' not found. Create it from .env.example."
fi

set -a
# shellcheck disable=SC1090
source "${ENV_FILE}"
set +a

for key in "${required_vars[@]}"; do
  if [[ -z "${!key:-}" ]]; then
    fail "Required variable '${key}' is missing or empty."
  fi
done

if [[ ! "${DATABASE_URL}" =~ ^postgres(ql)?://[^:/?#]+:[^@/?#]+@[^/?#:]+(:[0-9]+)?/[A-Za-z0-9_.-]+(\?.+)?$ ]]; then
  fail "DATABASE_URL has invalid format. Expected: postgres://user:password@host[:port]/db_name[?params]"
fi

if [[ "${SECRET_KEY}" == "your_secret_key_here" || "${SECRET_KEY}" == "dev-secret-key" ]]; then
  warn "SECRET_KEY uses a weak/default value. Use a strong secret for production/demo."
fi

if [[ ! "${ALGORITHM}" =~ ^(HS256|HS384|HS512)$ ]]; then
  fail "ALGORITHM must be one of: HS256, HS384, HS512"
fi

if ! [[ "${ACCESS_TOKEN_EXPIRE_MINUTES}" =~ ^[0-9]+$ ]]; then
  fail "ACCESS_TOKEN_EXPIRE_MINUTES must be an integer."
fi

if (( ACCESS_TOKEN_EXPIRE_MINUTES < 5 || ACCESS_TOKEN_EXPIRE_MINUTES > 1440 )); then
  fail "ACCESS_TOKEN_EXPIRE_MINUTES must be between 5 and 1440."
fi

echo "[predeploy-check] validating docker compose config"
docker compose config >/dev/null
echo "[predeploy-check] OK: validation passed"
