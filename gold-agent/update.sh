#!/bin/bash
# Updates the Gold Agent only. Its keys, diary and password are kept.
git -C /opt/watchtower pull -q
/opt/watchtower/gold-agent/.venv/bin/pip install -q alpaca-py requests >/dev/null 2>&1
systemctl restart gold-viewer
