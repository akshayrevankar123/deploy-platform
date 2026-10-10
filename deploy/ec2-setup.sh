#!/usr/bin/env bash
# One-time setup for a fresh Amazon Linux 2023 EC2 instance.
# Run it as the normal user (ec2-user), NOT with sudo:
#   bash ec2-setup.sh
# It is safe to run again; it will not overwrite an existing .env.
set -euo pipefail

if [ "$(id -u)" -eq 0 ]; then
  echo "Run this as ec2-user, without sudo. (It uses sudo itself where needed.)"
  exit 1
fi

echo "==> Installing Docker"
sudo dnf install -y docker
sudo systemctl enable --now docker
sudo usermod -aG docker "$USER"   # lets you run docker without sudo after you log in again

APP_DIR=/opt/deploy-platform
echo "==> Creating $APP_DIR"
sudo mkdir -p "$APP_DIR"
sudo chown "$USER" "$APP_DIR"

if [ -f "$APP_DIR/.env" ]; then
  echo "==> $APP_DIR/.env already exists. Leaving it alone."
else
  echo "==> Creating $APP_DIR/.env with freshly generated random secrets"
  umask 077   # only you can read the file
  {
    echo "SECRET_KEY=$(openssl rand -hex 32)"
    echo "DEPLOY_REPORT_TOKEN=$(openssl rand -hex 32)"
    echo "DATABASE_URL=sqlite:////data/app.db"
    echo "CORS_ORIGINS="
  } > "$APP_DIR/.env"
  chmod 600 "$APP_DIR/.env"
fi

cat <<'MSG'

Setup finished.

IMPORTANT: log out and log back in now (type: exit), so the docker group applies.
Then check it with:   docker ps

The secrets in /opt/deploy-platform/.env were generated on this server.
Never paste them into chat, GitHub issues, or screenshots.
MSG
