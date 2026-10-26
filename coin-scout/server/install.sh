#!/bin/bash
# COIN SCOUT installer (its own program, its own data folder). Run as root.
set -e
REPO="https://github.com/cultureXD-jpg/watchtower.git"
CODE=/opt/watchtower
APP=$CODE/coin-scout
DATA=/var/lib/coin-scout

echo "== Installing Coin Scout =="
export DEBIAN_FRONTEND=noninteractive
command -v node >/dev/null && command -v git >/dev/null || { apt-get update -y -q; apt-get install -y -q nodejs npm git >/dev/null; }
if [ -d "$CODE/.git" ]; then git -C "$CODE" pull -q; else git clone -q "$REPO" "$CODE"; fi
cd "$APP/server"
npm install --omit=dev --no-audit --no-fund -q >/dev/null 2>&1

mkdir -p "$DATA"
[ -s "$DATA/password.txt" ] || tr -dc 'A-HJ-NP-Za-km-z2-9' </dev/urandom | head -c 14 > "$DATA/password.txt"
chmod 600 "$DATA/password.txt"

cat > /etc/systemd/system/coin-scout.service <<EOF2
[Unit]
StartLimitIntervalSec=0
Description=Coin Scout paper-trading bot
After=network-online.target
Wants=network-online.target

[Service]
WorkingDirectory=$APP/server
ExecStart=/usr/bin/node --dns-result-order=ipv4first --max-old-space-size=600 $APP/server/server.js
Restart=always
RestartSec=5
Environment=PORT=80
Environment=COINSCOUT_DATA=$DATA

[Install]
WantedBy=multi-user.target
EOF2

if [ ! -f /swapfile ]; then
  fallocate -l 1G /swapfile && chmod 600 /swapfile && mkswap /swapfile >/dev/null && swapon /swapfile && echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

systemctl daemon-reload
systemctl enable coin-scout >/dev/null 2>&1
systemctl restart coin-scout
sleep 2
IP=$(curl -s -4 --max-time 5 https://ifconfig.me || hostname -I | awk '{print $1}')
echo
echo "----------------------------------------------------------------"
echo "  COIN SCOUT is running"
echo "    Open:      http://$IP"
echo "    Name:      anything"
echo "    Password:  $(cat $DATA/password.txt)"
echo "----------------------------------------------------------------"
