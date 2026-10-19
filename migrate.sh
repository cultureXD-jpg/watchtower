#!/bin/bash
# One-time move from the first setup (/opt/coin-scout, Coin Scout and gold mixed together)
# to two separate projects. Keeps all data, keys and passwords.
set -e
echo "== Separating Coin Scout and Gold Agent =="
systemctl stop coin-scout 2>/dev/null || true
systemctl disable --now gold-diary.timer 2>/dev/null || true

mkdir -p /var/lib/coin-scout /var/lib/gold-agent
OLD=/opt/coin-scout
if [ -d "$OLD" ]; then
  cp -n "$OLD"/server/data/storage.json /var/lib/coin-scout/ 2>/dev/null || true
  cp -n "$OLD"/server/data/password.txt /var/lib/coin-scout/ 2>/dev/null || true
  cp -n "$OLD"/gold/.env /var/lib/gold-agent/.env 2>/dev/null || true
  cp -n "$OLD"/gold/data/gold_diary.csv /var/lib/gold-agent/ 2>/dev/null || true
fi

if [ -d /opt/watchtower/.git ]; then git -C /opt/watchtower pull -q; else git clone -q https://github.com/cultureXD-jpg/watchtower.git /opt/watchtower; fi
bash /opt/watchtower/coin-scout/server/install.sh
bash /opt/watchtower/gold-agent/install.sh

# old mixed folder is no longer used; keep a copy just in case
[ -d "$OLD" ] && mv "$OLD" /opt/coin-scout.old-backup
echo
echo "Done. Coin Scout and Gold Agent are now two separate programs."
