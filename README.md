# watchtower

Daniel's server. It holds **two separate projects** that share nothing but the machine:

| Project | Folder | Data on the server | Page |
|---|---|---|---|
| **Coin Scout**: meme-coin quick-flip bot (paper trading) | `coin-scout/` | `/var/lib/coin-scout` | `http://<server>` |
| **Gold Agent**: gold day-trading project (daily diary for now) | `gold-agent/` | `/var/lib/gold-agent` | `http://<server>:8080` |

Each has its own installer, updater, password and data. Install one or both on a fresh Ubuntu server (as root):

    bash /opt/watchtower/coin-scout/server/install.sh
    bash /opt/watchtower/gold-agent/install.sh
