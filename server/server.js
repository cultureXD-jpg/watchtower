/* Coin Scout server: runs the bot 24/7 and serves the dashboard.
   The bot is the same code as Coin Scout.html, running inside a page that nobody needs to look at. */
'use strict';
const fs = require('fs');
const path = require('path');
const http = require('http');
const { execFile } = require('child_process');
const { JSDOM, VirtualConsole } = require('jsdom');

const DIR = __dirname;
const DATA = process.env.COINSCOUT_DATA || path.join(DIR, 'data');
const PORT = +process.env.PORT || 80;
const HTML_FILE = path.join(DIR, 'coin-scout.html');
const STORE_FILE = path.join(DATA, 'storage.json');
const PASS_FILE = path.join(DATA, 'password.txt');
fs.mkdirSync(DATA, {recursive:true});

const html = fs.readFileSync(HTML_FILE, 'utf8');
const VERSION = (html.match(/const VERSION = '([^']+)'/) || [])[1] || '?';
let PASSWORD = '';
try{ PASSWORD = fs.readFileSync(PASS_FILE, 'utf8').trim(); }catch(e){}
if (!PASSWORD){ console.error('No password set in ' + PASS_FILE); process.exit(1); }

/* ---------- saved data ---------- */
let saved = {};
try{ saved = JSON.parse(fs.readFileSync(STORE_FILE, 'utf8')); }catch(e){}
if (!saved['coinscout:cfg']){
  /* first start: quick flips + pump.fun coins on, like Daniel's setup */
  saved['coinscout:cfg'] = JSON.stringify({tpUsd:5, stopLoss:10, halfAtTP:false, trailStart:12, trail:5, maxHoldMin:30, maxOpen:8, minAgeMin:5, allowCurve:true});
}

/* ---------- the bot ---------- */
const vc = new VirtualConsole();
vc.on('error', (...a) => console.error('[bot]', ...a));
vc.on('warn', (...a) => console.warn('[bot]', ...a));
vc.on('jsdomError', e => console.error('[bot error]', e && (e.stack || e.message)));
if (process.env.COINSCOUT_MOCK) global.fetch = require(process.env.COINSCOUT_MOCK);
const dom = new JSDOM(html, {
  url:'http://localhost/', runScripts:'dangerously', pretendToBeVisual:true, virtualConsole:vc, storageQuota:300e6,
  beforeParse(w){
    w.__COINSCOUT_ENGINE__ = true;
    w.fetch = (...a) => fetch(...a);
    w.AbortController = AbortController;
    w.matchMedia = () => ({matches:true, addEventListener(){}, removeEventListener(){}});
    for (const [k, v] of Object.entries(saved)) w.localStorage.setItem(k, v);
  }
});
const W = dom.window;
const UP_SINCE = Date.now();

function persist(){
  try{
    const o = {};
    for (let i = 0; i < W.localStorage.length; i++){ const k = W.localStorage.key(i); o[k] = W.localStorage.getItem(k); }
    const tmp = STORE_FILE + '.tmp';
    fs.writeFileSync(tmp, JSON.stringify(o));
    fs.renameSync(tmp, STORE_FILE);
  }catch(e){ console.error('save failed:', e.message); }
}
setInterval(persist, 15000);
for (const sig of ['SIGTERM', 'SIGINT']) process.on(sig, () => { persist(); process.exit(0); });
process.on('uncaughtException', e => console.error('uncaught:', e && e.stack));
process.on('unhandledRejection', e => console.error('unhandled:', e && (e.stack || e)));

/* ---------- web dashboard ---------- */
function authed(req){
  const h = req.headers.authorization || '';
  if (!h.startsWith('Basic ')) return false;
  const dec = Buffer.from(h.slice(6), 'base64').toString();
  return dec.slice(dec.indexOf(':') + 1) === PASSWORD;
}
function body(req){
  return new Promise((res, rej) => {
    let b = ''; req.on('data', c => { b += c; if (b.length > 1e6) req.destroy(); });
    req.on('end', () => { try{ res(b ? JSON.parse(b) : {}); }catch(e){ rej(e); } });
  });
}
function json(res, code, obj, extra){
  res.writeHead(code, Object.assign({'Content-Type':'application/json', 'Cache-Control':'no-store'}, extra || {}));
  res.end(JSON.stringify(obj));
}

http.createServer(async (req, res) => {
  try{
    if (!authed(req)){
      res.writeHead(401, {'WWW-Authenticate':'Basic realm="Coin Scout"', 'Content-Type':'text/plain'});
      return res.end('Password needed. Any username works; use your Coin Scout password.');
    }
    const url = req.url.split('?')[0];
    if (req.method === 'GET' && (url === '/' || url === '/index.html')){
      res.writeHead(200, {'Content-Type':'text/html; charset=utf-8', 'Cache-Control':'no-store'});
      return res.end(html);
    }
    if (req.method === 'GET' && (url === '/gold' || url === '/gold.csv')){
      const f = path.join(DIR, '..', 'gold', 'data', 'gold_diary.csv');
      let csv = ''; try{ csv = fs.readFileSync(f, 'utf8'); }catch(e){}
      if (url === '/gold.csv'){ res.writeHead(200, {'Content-Type':'text/csv', 'Content-Disposition':'attachment; filename="gold_diary.csv"'}); return res.end(csv); }
      const esc = t => String(t).replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
      const rows = csv.trim().split('\n').filter(Boolean).map(l => l.split(','));
      const head = rows.shift() || [];
      const keyOk = fs.existsSync(path.join(DIR, '..', 'gold', '.env'));
      res.writeHead(200, {'Content-Type':'text/html; charset=utf-8', 'Cache-Control':'no-store'});
      return res.end('<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Gold diary</title><style>' +
        ':root{color-scheme:light dark;--bg:#F2F0EA;--s:#fff;--i:#15171C;--m:#5D636F;--l:#DCD8CE;--up:#0B9466;--dn:#D9412A}@media (prefers-color-scheme:dark){:root{--bg:#0D0F13;--s:#15181E;--i:#ECEEF2;--m:#9399A5;--l:#262A33;--up:#33D399;--dn:#FF6B57}}' +
        'body{margin:0;background:var(--bg);color:var(--i);font:15px/1.5 system-ui,sans-serif}.w{max-width:900px;margin:0 auto;padding:22px 16px}h1{font-size:1.7rem;margin:0 0 4px}p{color:var(--m);margin:0 0 16px}a{color:inherit}' +
        '.t{background:var(--s);border:1px solid var(--l);border-radius:14px;overflow-x:auto}table{width:100%;border-collapse:collapse;font-size:.9rem;min-width:620px}th{text-align:left;font-size:.72rem;text-transform:uppercase;letter-spacing:.05em;color:var(--m);padding:9px 12px;border-bottom:1px solid var(--l)}td{padding:9px 12px;border-bottom:1px solid var(--l);font-variant-numeric:tabular-nums}tr:last-child td{border:0}.up{color:var(--up)}.down{color:var(--dn)}</style></head><body><div class="w">' +
        '<h1>Gold diary</h1><p>One entry every market day at 1:15 PM, written by your server. ' + (keyOk ? '' : '<b>Keys not set yet</b>: run <code>bash /opt/coin-scout/server/gold-keys.sh</code> in the server console. ') + '<a href="/gold.csv">Download CSV</a> · <a href="/">Back to Coin Scout</a></p>' +
        '<div class="t"><table><thead><tr>' + head.map(h => '<th>' + esc(h) + '</th>').join('') + '</tr></thead><tbody>' +
        rows.reverse().map(r => '<tr>' + r.map((c, i) => '<td' + ((i === 2 || i === 4) ? ' class="' + esc(c) + '"' : '') + '>' + esc(c) + '</td>').join('') + '</tr>').join('') +
        '</tbody></table></div></div></body></html>');
    }
    if (req.method === 'GET' && url === '/api/state'){
      const d = W.eval('slim()');
      d.server = {upSince:UP_SINCE, version:VERSION};
      return json(res, 200, d);
    }
    if (req.method === 'POST' && url === '/api/cmd'){
      W.__cmd = await body(req);
      const r = W.eval('remoteCmd(window.__cmd)');
      persist();
      return json(res, 200, {ok:true, result:r});
    }
    if (req.method === 'GET' && url === '/api/export'){
      const name = 'coin-scout-data-' + new Date().toISOString().slice(0, 16).replace(/[:T]/g, '-') + '.json';
      res.writeHead(200, {'Content-Type':'application/json', 'Content-Disposition':'attachment; filename="' + name + '"'});
      return res.end(JSON.stringify(W.eval('exportData()')));
    }
    if (req.method === 'POST' && url === '/api/update'){
      json(res, 200, {ok:true});
      persist();
      execFile('systemd-run', ['--collect', '--unit=coin-scout-update-' + Date.now(), '/bin/bash', path.join(DIR, 'update.sh')], err => { if (err) console.error('update failed to start:', err.message); });
      return;
    }
    res.writeHead(404); res.end('Not found');
  }catch(e){
    console.error('request failed:', e && e.stack);
    json(res, 500, {error:String(e && e.message)});
  }
}).listen(PORT, () => console.log('Coin Scout ' + VERSION + ' running on port ' + PORT));
