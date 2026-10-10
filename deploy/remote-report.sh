#!/usr/bin/env bash
# Runs ON the EC2 server (piped over SSH by the deploy workflow).
# Tells the platform's own API whether the deployment worked.
#
# Why on the server: the secret token already lives in /opt/deploy-platform/.env,
# and talking to localhost over SSH means the token never travels over plain HTTP
# and never needs to be stored in GitHub as well.
#
# Inputs (environment variables): PROJECT_ID, STATUS (success|failed), MESSAGE, LIVE_URL
set -euo pipefail

APP_DIR=/opt/deploy-platform
TOKEN=$(grep '^DEPLOY_REPORT_TOKEN=' "$APP_DIR/.env" | cut -d= -f2- || true)
if [ -z "$TOKEN" ]; then
  echo "No DEPLOY_REPORT_TOKEN on the server. Skipping the report."
  exit 0
fi

BODY=$(python3 - <<'PY'
import json, os
print(json.dumps({
    "project_id": int(os.environ["PROJECT_ID"]),
    "status": os.environ["STATUS"],
    "message": os.environ.get("MESSAGE", "")[:300],
    "live_url": os.environ.get("LIVE_URL") or None,
}))
PY
)

curl -fsS --max-time 10 -X POST http://localhost/deployments/report \
  -H "Content-Type: application/json" \
  -H "X-Deploy-Token: $TOKEN" \
  -d "$BODY"
echo
