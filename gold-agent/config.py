import os

GOLD_HOME = os.environ.get("GOLD_HOME", "/var/lib/gold-agent")
env_path = os.path.join(GOLD_HOME, ".env")

if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                name, value = line.split("=", 1)
                os.environ.setdefault(name.strip(), value.strip().strip('"').strip("'"))

def need(name):
    value = os.environ.get(name)
    if not value:
        raise SystemExit(f"Missing {name} - run: bash /opt/watchtower/gold-agent/keys.sh")
    return value

API_KEY = need("ALPACA_API_KEY")
SECRET_KEY = need("ALPACA_SECRET_KEY")
FRED_KEY = need("FRED_KEY")
