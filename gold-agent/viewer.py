# GOLD AGENT: small password-protected page showing the gold diary. Separate from Coin Scout.
import base64, csv, html, io, os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HOME = os.environ.get("GOLD_HOME", "/var/lib/gold-agent")
PORT = int(os.environ.get("PORT", "8080"))
DIARY = os.path.join(HOME, "gold_diary.csv")
PASSWORD = open(os.path.join(HOME, "password.txt")).read().strip()

STYLE = """:root{color-scheme:light dark;--bg:#F4F1E8;--s:#fff;--i:#1B1A17;--m:#6B665C;--l:#DDD6C6;--up:#0B8A5F;--dn:#C8452C;--gold:#A87B12}
@media (prefers-color-scheme:dark){:root{--bg:#12110E;--s:#1B1A16;--i:#EFEBE1;--m:#A39D90;--l:#2E2B24;--up:#36C98F;--dn:#F07158;--gold:#E2B54A}}
body{margin:0;background:var(--bg);color:var(--i);font:15px/1.5 system-ui,-apple-system,sans-serif}
.w{max-width:920px;margin:0 auto;padding:24px 16px 60px}h1{font-size:1.8rem;margin:0 0 4px}h1 span{color:var(--gold)}
p{color:var(--m);margin:0 0 18px}a{color:inherit}.t{background:var(--s);border:1px solid var(--l);border-radius:14px;overflow-x:auto}
table{width:100%;border-collapse:collapse;font-size:.92rem;min-width:640px}th{text-align:left;font-size:.72rem;text-transform:uppercase;letter-spacing:.05em;color:var(--m);padding:10px 12px;border-bottom:1px solid var(--l)}
td{padding:10px 12px;border-bottom:1px solid var(--l);font-variant-numeric:tabular-nums}tr:last-child td{border:0}.up{color:var(--up)}.down{color:var(--dn)}.warn{color:var(--dn)}"""

def page():
    rows = []
    if os.path.exists(DIARY):
        with open(DIARY) as f:
            rows = [r for r in csv.reader(f) if r]
    head, body = (rows[0], rows[1:]) if rows else ([], [])
    keys_ok = os.path.exists(os.path.join(HOME, ".env"))
    note = "" if keys_ok else ' <b class="warn">Keys not set yet</b>: run <code>bash /opt/watchtower/gold-agent/keys.sh</code> in the server console.'
    cells = lambda r: "".join('<td%s>%s</td>' % (' class="%s"' % html.escape(c) if i in (2, 4) else "", html.escape(c)) for i, c in enumerate(r))
    return ("<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>Gold Agent</title><style>%s</style></head><body><div class='w'>"
            "<h1><span>Gold</span> Agent</h1><p>Daily gold diary: one entry every market day at 1:15 PM California time.%s <a href='/gold_diary.csv'>Download CSV</a></p>"
            "<div class='t'><table><thead><tr>%s</tr></thead><tbody>%s</tbody></table></div></div></body></html>"
            % (STYLE, note, "".join("<th>%s</th>" % html.escape(h) for h in head), "".join("<tr>%s</tr>" % cells(r) for r in reversed(body))))

class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def authed(self):
        h = self.headers.get("Authorization", "")
        if not h.startswith("Basic "): return False
        try: dec = base64.b64decode(h[6:]).decode()
        except Exception: return False
        return dec.split(":", 1)[-1] == PASSWORD
    def send(self, code, body, ctype, extra=None):
        b = body.encode()
        self.send_response(code); self.send_header("Content-Type", ctype); self.send_header("Content-Length", str(len(b))); self.send_header("Cache-Control", "no-store")
        for k, v in (extra or {}).items(): self.send_header(k, v)
        self.end_headers(); self.wfile.write(b)
    def do_GET(self):
        if not self.authed():
            return self.send(401, "Password needed (any name works).", "text/plain", {"WWW-Authenticate": 'Basic realm="Gold Agent"'})
        if self.path.split("?")[0] == "/gold_diary.csv":
            data = open(DIARY).read() if os.path.exists(DIARY) else ""
            return self.send(200, data, "text/csv", {"Content-Disposition": 'attachment; filename="gold_diary.csv"'})
        self.send(200, page(), "text/html; charset=utf-8")

if __name__ == "__main__":
    ThreadingHTTPServer(("", PORT), H).serve_forever()
