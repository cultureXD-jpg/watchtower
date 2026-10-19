import os

env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")

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
        raise SystemExit(f"Missing {name} - run: bash /opt/coin-scout/server/gold-keys.sh")
    return value

API_KEY = need("ALPACA_API_KEY")
SECRET_KEY = need("ALPACA_SECRET_KEY")
FRED_KEY = need("FRED_KEY")
