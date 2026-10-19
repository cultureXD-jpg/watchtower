#!/bin/bash
# Updates Coin Scout only. Its data and password are kept.
sleep 1
git -C /opt/watchtower pull -q
cd /opt/watchtower/coin-scout/server && npm install --omit=dev --no-audit --no-fund -q >/dev/null 2>&1
systemctl restart coin-scout
