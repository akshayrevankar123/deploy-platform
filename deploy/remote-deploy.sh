#!/usr/bin/env bash
# Runs ON the EC2 server. The GitHub Actions deploy workflow pipes it over SSH:
#   ssh user@host "IMAGE='you/deploy-platform:abc1234' bash -s" < deploy/remote-deploy.sh
#
# What it does:
#   1. pulls the new image
#   2. replaces the running container
#   3. waits for /health to answer
#   4. if the new version is broken, it puts the previous version back (rollback)
set -euo pipefail

: "${IMAGE:?IMAGE is required, e.g. IMAGE=you/deploy-platform:abc1234}"
APP_DIR=/opt/deploy-platform
NAME=deploy-platform

if [ ! -f "$APP_DIR/.env" ]; then
  echo "Missing $APP_DIR/.env. Run deploy/ec2-setup.sh first."
  exit 1
fi

# Remember what is running now, so we can roll back to it.
PREVIOUS_IMAGE=$(docker inspect --format '{{.Config.Image}}' "$NAME" 2>/dev/null || true)

run_container() {
  # --env-file    : secrets come from the file on the server, never from the image
  # -v deploy_data: named volume so the database survives redeploys
  # -p 80:8000    : public port 80 -> app port 8000 inside the container
  # --memory      : stop one runaway container from freezing the whole small server
  # --cap-drop    : the app needs no special Linux privileges
  docker run -d --name "$NAME" --restart unless-stopped \
    --env-file "$APP_DIR/.env" \
    -v deploy_data:/data \
    -p 80:8000 \
    --memory 512m \
    --cap-drop ALL \
    --security-opt no-new-privileges \
    "$1" >/dev/null
}

wait_healthy() {
  for _ in $(seq 1 20); do
    if curl -fsS --max-time 3 http://localhost/health >/dev/null 2>&1; then
      return 0
    fi
    sleep 3
  done
  return 1
}

show_logs() {
  # Redact anything that looks like a secret before it reaches a CI log.
  docker logs --tail 40 "$NAME" 2>&1 \
    | sed -E 's/(([A-Za-z_]*(SECRET|TOKEN|PASSWORD|KEY)[A-Za-z_]*)[=:] *)[^ ]+/\1[REDACTED]/Ig' || true
}

echo "Pulling $IMAGE"
docker pull "$IMAGE"

docker rm -f "$NAME" >/dev/null 2>&1 || true
run_container "$IMAGE"

if wait_healthy; then
  echo "New version is healthy: $IMAGE"
  docker image prune -f >/dev/null 2>&1 || true
  exit 0
fi

echo "New version FAILED its health check. Last log lines:"
show_logs
docker rm -f "$NAME" >/dev/null 2>&1 || true

if [ -n "$PREVIOUS_IMAGE" ] && [ "$PREVIOUS_IMAGE" != "$IMAGE" ]; then
  echo "Rolling back to $PREVIOUS_IMAGE"
  run_container "$PREVIOUS_IMAGE"
  if wait_healthy; then
    echo "Rollback succeeded. The old version is serving again."
  else
    echo "Rollback also failed. Log in to the server and check 'docker logs $NAME'."
  fi
fi
exit 1
