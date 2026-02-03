#!/usr/bin/env bash
set -euo pipefail

OPA_URL=${OPA_URL:-http://localhost:8181}
MOODLE_URL=${MOODLE_URL:-http://localhost:8080}

echo "Waiting for Moodle to be ready at $MOODLE_URL"
for i in $(seq 1 60); do
  if curl -sSfL "$MOODLE_URL" >/dev/null 2>&1; then
    echo "Moodle is up"
    break
  fi
  sleep 2
done

# Check plugin availability (the folder should exist)
if curl -sSf "$MOODLE_URL/local/caex_integration/README.md" >/dev/null 2>&1; then
  echo "Plugin files available at Moodle (may need install)"
else
  echo "Plugin files may not be web-accessible; ensure the plugin is in the container"
fi

# Run Moodle CLI upgrade to install plugins
# Prefer getting container via compose, fallback to ancestor filter; detect configured image
MOODLE_IMAGE=${MOODLE_IMAGE:-bitnami/moodle:4}
MOODLE_CONTAINER=$(docker compose -f ../docker-compose.e2e.yml ps -q moodle 2>/dev/null || true)
if [ -z "$MOODLE_CONTAINER" ]; then
  # fallback: match by ancestor image
  MOODLE_CONTAINER=$(docker ps --filter "ancestor=$MOODLE_IMAGE" --format "{{.ID}}" | head -n1)
fi

if [ -n "$MOODLE_CONTAINER" ]; then
  echo "Running Moodle CLI upgrade inside container $MOODLE_CONTAINER"
  docker exec "$MOODLE_CONTAINER" bash -lc "/opt/bitnami/moodle/bin/php /opt/bitnami/moodle/admin/cli/upgrade.php --non-interactive" || true
  echo "Attempting to purge caches via CLI"
  docker exec "$MOODLE_CONTAINER" bash -lc "/opt/bitnami/moodle/bin/php /opt/bitnami/moodle/admin/cli/purge_caches.php" || true
else
  echo "Moodle container not found; cannot run CLI upgrades"
  echo "-- Docker service list --"
  docker compose -f ../docker-compose.e2e.yml ps || true
  echo "-- Docker ps (recent) --"
  docker ps --format "{{.ID}} {{.Image}} {{.Names}}" --no-trunc | sed -n '1,200p' || true
fi

# Basic smoke test: check home page contains 'Moodle'
curl -sSf "$MOODLE_URL" | grep -i "moodle" || (echo "Moodle home page did not contain keyword" && exit 1)

echo "Moodle E2E basic checks passed"

# Perform a headless admin login and call plugin test endpoint to exercise grade update flow
COOKIEJAR=$(mktemp)
LOGIN_PAGE=$(curl -sSfL "$MOODLE_URL/login/index.php")
# extract logintoken value (if present)
LOGINTOKEN=$(echo "$LOGIN_PAGE" | grep -oP 'name="logintoken" value="\K[^"]+' || true)
if [ -n "$LOGINTOKEN" ]; then
  echo "Logging in as admin (with logintoken)"
  curl -sSfL -c "$COOKIEJAR" -d "username=$MOODLE_USERNAME&password=$MOODLE_PASSWORD&logintoken=$LOGINTOKEN" "$MOODLE_URL/login/index.php" >/dev/null
else
  echo "Logging in as admin (no token)"
  curl -sSfL -c "$COOKIEJAR" -d "username=$MOODLE_USERNAME&password=$MOODLE_PASSWORD" "$MOODLE_URL/login/index.php" >/dev/null
fi

# Verify we can reach the plugin test endpoint
echo "Pinging plugin test endpoint"
resp=$(curl -sSfL -b "$COOKIEJAR" -X POST -H "Content-Type: application/json" -d '{"action":"ping"}' "$MOODLE_URL/local/caex_integration/web/test_endpoint.php" || true)
if echo "$resp" | grep -q '"status":"ok"'; then
  echo "Plugin test ping OK"
else
  echo "Plugin test ping failed: $resp" && exit 1
fi

# Trigger a test grade update
echo "Triggering test grade update via plugin (test_update_grade)"
CLIENT_REQ_ID="e2e-$(date +%s)"
resp2=$(curl -sSfL -b "$COOKIEJAR" -X POST -H "Content-Type: application/json" -d '{"action":"test_update_grade","itemid":1,"userid":1,"grade":0.5,"client_request_id":"'"$CLIENT_REQ_ID"'"}' "$MOODLE_URL/local/caex_integration/web/test_endpoint.php" || true)
if echo "$resp2" | grep -q '"status":"ok"'; then
  echo "Plugin test_update_grade OK"
else
  echo "Plugin test_update_grade failed: $resp2" && exit 1
fi

# Extract operation_id (if present)
if command -v jq >/dev/null 2>&1; then
  OP_ID=$(echo "$resp2" | jq -r '.result.operation_id // empty')
else
  OP_ID=$(echo "$resp2" | sed -n 's/.*"operation_id":\s*\([0-9]*\).*/\1/p' || true)
fi
if [ -z "$OP_ID" ]; then
  echo "No operation_id returned; cannot verify operation record" && exit 1
fi

echo "First grade update produced operation_id=$OP_ID"

# Re-send same client_request_id to assert idempotency
echo "Re-sending update with same client_request_id to check idempotency"
resp3=$(curl -sSfL -b "$COOKIEJAR" -X POST -H "Content-Type: application/json" -d '{"action":"test_update_grade","itemid":1,"userid":1,"grade":0.5,"client_request_id":"'"$CLIENT_REQ_ID"'"}' "$MOODLE_URL/local/caex_integration/web/test_endpoint.php" || true)
if echo "$resp3" | grep -q '"already_applied"'; then
  echo "Idempotency check OK: second call reported already_applied"
else
  echo "Idempotency check failed: $resp3" && exit 1
fi

# Verify operation record exists via check_operation
echo "Verifying stored operation record via check_operation"
resp4=$(curl -sSfL -b "$COOKIEJAR" -X POST -H "Content-Type: application/json" -d '{"action":"check_operation","client_request_id":"'"$CLIENT_REQ_ID"'"}' "$MOODLE_URL/local/caex_integration/web/test_endpoint.php" || true)
if echo "$resp4" | grep -q '"status":"ok"'; then
  echo "Operation record found for client_request_id=$CLIENT_REQ_ID"
else
  echo "Operation record not found: $resp4" && exit 1
fi

echo "Moodle E2E plugin interactions succeeded"
