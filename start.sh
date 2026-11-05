#!/bin/sh
# Khoi dong tren Render: Tailscale (userspace) -> FoxProfile server mode -> bot.
# Thu tu nay quan trong: bot chi chay duoc khi FoxProfile API 127.0.0.1:8000 da len.
set -e

# Fail nhanh thay vi chay bot khong SSH / khong token (tranh treo o notepad/input cua ban Windows).
: "${TAILSCALE_AUTHKEY:?Chua set TAILSCALE_AUTHKEY tren Render}"
: "${TELEGRAM_BOT_TOKEN:?Chua set TELEGRAM_BOT_TOKEN tren Render}"
: "${FOXPROFILE_API_TOKEN:?Chua set FOXPROFILE_API_TOKEN tren Render (>= 24 ky tu)}"

# Disk Render mount o /var/data. Neu khong co disk, du lieu se mat khi restart/redeploy.
DATA_ROOT="${DATA_ROOT:-/var/data}"
if [ ! -d "$DATA_ROOT" ]; then
  echo "CANH BAO: khong thay $DATA_ROOT — dang dung thu muc tam, profile/login/state se mat khi restart."
  DATA_ROOT="/app/.ephemeral-data"
fi

export FOXPROFILE_API_HOST=127.0.0.1
export FOXPROFILE_API_PORT=8000
export FOXPROFILE_HEADLESS=virtual
export FOXPROFILE_DATA_DIR="$DATA_ROOT/foxprofile"
export FOXPROFILE_PROFILES_FILE="$DATA_ROOT/foxprofile/profiles.json"
export FOXPROFILE_SETTINGS_FILE="$DATA_ROOT/foxprofile/settings.json"
export FOXPROFILE_LOG_DIR="$DATA_ROOT/foxprofile/logs"
# Duong dan Linux, KHONG dung duong dan Windows trong .env.example (..\\Videos\\...).
export FOXPROFILE_UPLOAD_DIRS="$DATA_ROOT/uploads"
export MUSE_UPLOAD_DIR="$DATA_ROOT/uploads/muse_telebot"
export FOXPROFILE_URL=http://127.0.0.1:8000
export BOT_STATE_FILE="$DATA_ROOT/bot/muse_telebot_state.json"

mkdir -p "$FOXPROFILE_DATA_DIR" "$DATA_ROOT/uploads/muse_telebot" "$DATA_ROOT/bot" /var/lib/tailscale /var/run/tailscale

# 1. Tailscale userspace (Render khong co quyen kernel/TUN).
tailscaled --tun=userspace-networking --socks5-server=localhost:1055 \
  --state=/var/lib/tailscale/tailscaled.state \
  --socket=/var/run/tailscale/tailscaled.sock &
for i in $(seq 1 30); do
  [ -S /var/run/tailscale/tailscaled.sock ] && break
  sleep 1
done

# --ssh bat Tailscale SSH; hostname nay dung de ssh tu may cua anh.
# Luu y: ACL tren Tailscale Admin van phai cho phep tai khoan cua anh SSH toi node nay.
tailscale up --authkey="${TAILSCALE_AUTHKEY}" --ssh --hostname=render-muse2tele --accept-dns=false
tailscale status || true

# 2. FoxProfile che do server (API + headless), KHONG phai src/main.py (ban GUI desktop).
cd /app/foxprofile/repo
python -m src.server --host 127.0.0.1 --port 8000 &
cd /app

for i in $(seq 1 60); do
  if curl -fsS http://127.0.0.1:8000/api/v1/health >/dev/null 2>&1; then
    break
  fi
  sleep 2
done
curl -fsS http://127.0.0.1:8000/api/v1/health >/dev/null

# 3. Bot o foreground (Render theo doi tien trinh nay). Shim Linux xu ly
# ctypes.windll + file state tren disk, khong sua code goc cua repo.
exec python run_bot_linux.py
