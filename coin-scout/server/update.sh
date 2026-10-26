#!/bin/bash
# Updates Coin Scout only. Its data and password are kept.
sleep 1
git -C /opt/watchtower pull -q
cd /opt/watchtower/coin-scout/server && npm install --omit=dev --no-audit --no-fund -q >/dev/null 2>&1
# never let systemd give up restarting the bot (it used to stop after 5 quick restarts)
U=/etc/systemd/system/coin-scout.service
if [ -f "$U" ] && ! grep -q StartLimitIntervalSec "$U"; then sed -i 's/^\[Unit\]$/[Unit]\nStartLimitIntervalSec=0/' "$U"; systemctl daemon-reload; fi
systemctl restart coin-scout
