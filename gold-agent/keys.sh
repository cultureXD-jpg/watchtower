#!/bin/bash
# Asks for the gold diary's keys and saves them on this server only.
ENVF=/var/lib/gold-agent/.env
mkdir -p /var/lib/gold-agent
echo
echo "== Gold diary keys (same three as in your Mac's GoldAgent/.env file) =="
echo "Paste each one and press Enter. Press Enter on an empty line to skip for now."
read -r -p "ALPACA_API_KEY: " A </dev/tty
[ -z "$A" ] && { echo "Skipped. Run this later: bash /opt/watchtower/gold-agent/keys.sh"; exit 0; }
read -r -p "ALPACA_SECRET_KEY: " B </dev/tty
read -r -p "FRED_KEY: " C </dev/tty
clean(){ local v="$1"; v="${v#*=}"; v="${v//\"/}"; v="${v//\'/}"; v="$(echo -n "$v" | tr -d '[:space:]')"; echo -n "$v"; }
A="$(clean "$A")"; B="$(clean "$B")"; C="$(clean "$C")"
printf 'ALPACA_API_KEY=%s\nALPACA_SECRET_KEY=%s\nFRED_KEY=%s\n' "$A" "$B" "$C" > "$ENVF"
chmod 600 "$ENVF"
echo "Saved. Testing it now..."
GOLD_HOME=/var/lib/gold-agent /opt/watchtower/gold-agent/.venv/bin/python /opt/watchtower/gold-agent/gold_diary_writer.py && echo "Gold diary works." || echo "That didn't work - double-check the keys and run this again."
