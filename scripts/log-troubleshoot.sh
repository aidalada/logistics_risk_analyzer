#!/usr/bin/env bash
set -euo pipefail

LINES="${1:-400}"
OUT_DIR="artifacts/troubleshooting"
TS="$(date +%Y%m%d-%H%M%S)"
OUT_FILE="${OUT_DIR}/log-analysis-${TS}.md"

mkdir -p "${OUT_DIR}"

echo "# Automated Log Troubleshooting Report (${TS})" >"${OUT_FILE}"
echo "" >>"${OUT_FILE}"
echo "- Analyzed last \`${LINES}\` lines per container." >>"${OUT_FILE}"
echo "- Source: \`docker compose logs --tail=${LINES}\`" >>"${OUT_FILE}"
echo "" >>"${OUT_FILE}"

logs="$(docker compose logs --no-color --tail="${LINES}" 2>&1 || true)"

print_count() {
  local label="$1"
  local regex="$2"
  local count
  count="$(printf "%s\n" "${logs}" | grep -Eic "${regex}" || true)"
  echo "- ${label}: **${count}**" >>"${OUT_FILE}"
}

echo "## Pattern Matches" >>"${OUT_FILE}"
print_count "Database connection failures" "connection (refused|reset|timed out)|could not connect to server|database.*unavailable|psycopg2\\.OperationalError"
print_count "Restart-loop indicators" "restarting|back-off|crashloop|exited with code|service unavailable"
print_count "5xx/API errors" "HTTP/[0-9.]+\" 5[0-9]{2}|status=5[0-9]{2}|internal server error|traceback"
print_count "Timeouts/dependency failures" "timeout|timed out|upstream.*failed|name or service not known|temporary failure in name resolution"
echo "" >>"${OUT_FILE}"

echo "## Recent Suspicious Log Lines" >>"${OUT_FILE}"
echo '```text' >>"${OUT_FILE}"
printf "%s\n" "${logs}" \
  | grep -Ei "error|exception|traceback|timeout|refused|unavailable|restarting|5[0-9]{2}" \
  | tail -n 120 >>"${OUT_FILE}" || true
echo '```' >>"${OUT_FILE}"
echo "" >>"${OUT_FILE}"

echo "## Container Restart Counts" >>"${OUT_FILE}"
echo '```text' >>"${OUT_FILE}"
for c in $(docker compose ps -q); do
  name="$(docker inspect --format '{{.Name}}' "${c}" | sed 's#^/##')"
  restart_count="$(docker inspect --format '{{.RestartCount}}' "${c}")"
  health="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}n/a{{end}}' "${c}")"
  echo "${name}: restart_count=${restart_count}, health=${health}" >>"${OUT_FILE}"
done
echo '```' >>"${OUT_FILE}"
echo "" >>"${OUT_FILE}"

echo "## Quick Interpretation Guide" >>"${OUT_FILE}"
echo "- If \`Database connection failures > 0\`, verify \`DATABASE_URL\` and DB container health first." >>"${OUT_FILE}"
echo "- If \`Restart-loop indicators > 0\`, inspect affected container logs and image entrypoint." >>"${OUT_FILE}"
echo "- If \`5xx/API errors\` rise with load, correlate with CPU/memory from Grafana and autoscaling thresholds." >>"${OUT_FILE}"

echo "Report generated: ${OUT_FILE}"
