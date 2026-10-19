#!/bin/bash
# Coin Scout installer for a fresh Ubuntu server. Run as root:
#   curl -fsSL https://raw.githubusercontent.com/cultureXD-jpg/watchtower/main/server/install.sh | bash
set -e
REPO="https://github.com/cultureXD-jpg/watchtower.git"
APP=/opt/coin-scout

echo "== Installing Coin Scout. This takes 2-4 minutes. =="
export DEBIAN_FRONTEND=noninteractive
apt-get update -y -q
apt-get install -y -q nodejs npm git python3-venv >/dev/null

if [ -d "$APP/.git" ]; then git -C "$APP" pull -q; else git clone -q "$REPO" "$APP"; fi
cd "$APP/server"
cp -f ../coin-scout.html ./coin-scout.html
npm install --omit=dev --no-audit --no-fund -q jsdom@24.1.3 >/dev/null 2>&1

mkdir -p data
if [ ! -s data/password.txt ]; then
  tr -dc 'A-HJ-NP-Za-km-z2-9' </dev/urandom | head -c 14 > data/password.txt
fi
chmod 600 data/password.txt

cat > /etc/systemd/system/coin-scout.service <<EOF
[Unit]
Description=Coin Scout paper-trading bot
After=network-online.target
Wants=network-online.target

[Service]
WorkingDirectory=$APP/server
ExecStart=/usr/bin/node --max-old-space-size=600 $APP/server/server.js
Restart=always
RestartSec=5
Environment=PORT=80

[Install]
WantedBy=multi-user.target
EOF

# a little swap space so the small server never runs out of memory
if [ ! -f /swapfile ]; then
  fallocate -l 1G /swapfile && chmod 600 /swapfile && mkswap /swapfile >/dev/null && swapon /swapfile && echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

# ---------- gold diary: runs every day at 1:15 PM California time ----------
cd "$APP/gold"
[ -d .venv ] || python3 -m venv .venv
.venv/bin/pip install -q --upgrade pip >/dev/null 2>&1
.venv/bin/pip install -q alpaca-py requests >/dev/null 2>&1
mkdir -p data
[ -s data/gold_diary.csv ] || cp seed_diary.csv data/gold_diary.csv
cat > /etc/systemd/system/gold-diary.service <<EOF2
[Unit]
Description=Gold diary daily entry
[Service]
Type=oneshot
WorkingDirectory=$APP/gold
ExecStart=$APP/gold/.venv/bin/python $APP/gold/gold_diary_writer.py
EOF2
cat > /etc/systemd/system/gold-diary.timer <<EOF2
[Unit]
Description=Run the gold diary at 1:15 PM Pacific
[Timer]
OnCalendar=*-*-* 13:15:00 America/Los_Angeles
Persistent=true
[Install]
WantedBy=timers.target
EOF2
cd "$APP/server"

systemctl daemon-reload
systemctl enable coin-scout >/dev/null 2>&1
systemctl enable --now gold-diary.timer >/dev/null 2>&1
systemctl restart coin-scout
[ -s "$APP/gold/.env" ] || bash "$APP/server/gold-keys.sh" 
sleep 3

IP=$(curl -s -4 --max-time 5 https://ifconfig.me || hostname -I | awk '{print $1}')
echo
echo "================================================================"
echo "  Coin Scout is running."
echo
echo "  Open:      http://$IP"
echo "  Username:  anything (for example: daniel)"
echo "  Password:  $(cat data/password.txt)"
echo
echo "  Gold diary: http://$IP/gold  (new entry every weekday at 1:15 PM)"
echo
echo "  Save that password. To see it again later, run:"
echo "    cat $APP/server/data/password.txt"
echo "================================================================"
