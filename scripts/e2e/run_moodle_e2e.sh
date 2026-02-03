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
MOODLE_CONTAINER=$(docker ps --filter "ancestor=bitnami/moodle:4" --format "{{.ID}}" | head -n1)
if [ -n "$MOODLE_CONTAINER" ]; then
  echo "Running Moodle CLI upgrade inside container $MOODLE_CONTAINER"
  docker exec "$MOODLE_CONTAINER" bash -lc "/opt/bitnami/moodle/bin/php /opt/bitnami/moodle/admin/cli/upgrade.php --non-interactive" || true
  echo "Attempting to create admin token via CLI"
  docker exec "$MOODLE_CONTAINER" bash -lc "/opt/bitnami/moodle/bin/php /opt/bitnami/moodle/admin/cli/purge_caches.php" || true
else
  echo "Moodle container not found; cannot run CLI upgrades"
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

echo "Moodle E2E plugin interactions succeeded"
