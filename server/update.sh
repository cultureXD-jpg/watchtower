#!/bin/bash
# Pulls the newest Coin Scout code and restarts it. Your data and password are kept.
APP=/opt/coin-scout
sleep 1
git -C "$APP" pull -q && cp -f "$APP/coin-scout.html" "$APP/server/coin-scout.html"
[ -d "$APP/gold/.venv" ] && "$APP/gold/.venv/bin/pip" install -q alpaca-py requests >/dev/null 2>&1
systemctl restart coin-scout
