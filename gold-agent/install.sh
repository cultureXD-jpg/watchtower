#!/bin/bash
# GOLD AGENT installer (its own program, its own data folder). Run as root.
set -e
REPO="https://github.com/cultureXD-jpg/watchtower.git"
CODE=/opt/watchtower
APP=$CODE/gold-agent
DATA=/var/lib/gold-agent

echo "== Installing Gold Agent =="
export DEBIAN_FRONTEND=noninteractive
dpkg -s python3-venv >/dev/null 2>&1 && command -v git >/dev/null || { apt-get update -y -q; apt-get install -y -q python3-venv git >/dev/null; }
if [ -d "$CODE/.git" ]; then git -C "$CODE" pull -q; else git clone -q "$REPO" "$CODE"; fi
cd "$APP"
[ -d .venv ] || python3 -m venv .venv
.venv/bin/pip install -q --upgrade pip >/dev/null 2>&1
.venv/bin/pip install -q alpaca-py requests >/dev/null 2>&1

mkdir -p "$DATA"
[ -s "$DATA/gold_diary.csv" ] || cp seed_diary.csv "$DATA/gold_diary.csv"
[ -s "$DATA/password.txt" ] || tr -dc 'A-HJ-NP-Za-km-z2-9' </dev/urandom | head -c 14 > "$DATA/password.txt"
chmod 600 "$DATA/password.txt"

cat > /etc/systemd/system/gold-diary.service <<EOF2
[Unit]
Description=Gold Agent: daily diary entry
After=network-online.target
Wants=network-online.target
StartLimitIntervalSec=3h
StartLimitBurst=5
[Service]
Type=oneshot
Restart=on-failure
RestartSec=15min
Environment=GOLD_HOME=$DATA
WorkingDirectory=$APP
ExecStart=$APP/.venv/bin/python $APP/gold_diary_writer.py
EOF2
cat > /etc/systemd/system/gold-diary.timer <<EOF2
[Unit]
Description=Gold Agent: run the diary at 1:15 PM Pacific
[Timer]
OnCalendar=*-*-* 13:15:00 America/Los_Angeles
Persistent=true
[Install]
WantedBy=timers.target
EOF2
cat > /etc/systemd/system/gold-intraday.service <<EOF2
[Unit]
Description=Gold Agent: save the day's 1-minute GLD bars
After=network-online.target
Wants=network-online.target
StartLimitIntervalSec=3h
StartLimitBurst=5
[Service]
Type=oneshot
Restart=on-failure
RestartSec=15min
Environment=GOLD_HOME=$DATA
WorkingDirectory=$APP
ExecStart=$APP/.venv/bin/python $APP/gold_intraday.py
EOF2
cat > /etc/systemd/system/gold-intraday.timer <<EOF2
[Unit]
Description=Gold Agent: record the day's minute bars at 1:45 PM Pacific (after the close)
[Timer]
OnCalendar=Mon..Fri 13:45:00 America/Los_Angeles
Persistent=true
[Install]
WantedBy=timers.target
EOF2
cat > /etc/systemd/system/gold-viewer.service <<EOF2
[Unit]
Description=Gold Agent: diary page
After=network-online.target
[Service]
Environment=GOLD_HOME=$DATA
Environment=PORT=8080
ExecStart=/usr/bin/python3 $APP/viewer.py
Restart=always
RestartSec=5
[Install]
WantedBy=multi-user.target
EOF2

systemctl daemon-reload
systemctl enable --now gold-diary.timer >/dev/null 2>&1
systemctl enable --now gold-intraday.timer >/dev/null 2>&1
systemctl enable gold-viewer >/dev/null 2>&1
systemctl restart gold-viewer
[ -s "$DATA/.env" ] || bash "$APP/keys.sh"
IP=$(curl -s -4 --max-time 5 https://ifconfig.me || hostname -I | awk '{print $1}')
echo
echo "----------------------------------------------------------------"
echo "  GOLD AGENT is running (separate from Coin Scout)"
echo "    Diary page: http://$IP:8080"
echo "    Name:       anything"
echo "    Password:   $(cat $DATA/password.txt)"
echo "----------------------------------------------------------------"
