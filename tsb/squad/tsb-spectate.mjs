import http from 'http';

const BOTS = [
  { port: 9223, name: '[NPL] Mishi', slot: 0 },
  { port: 9224, name: '[NPL] Matzz', slot: 1 },
  { port: 9225, name: '[NPL] Kiholma', slot: 2 },
  { port: 9226, name: '[NPL] Leo_99', slot: 3 },
  { port: 9227, name: '[NPL] Racoon', slot: 4 },
];

let latestJpeg = null;
let latestMeta = {};

function getJson(url) {
  return new Promise((resolve, reject) => {
    http.get(url, (res) => {
      let data = '';
      res.on('data', (c) => data += c);
      res.on('end', () => {
        try { resolve(JSON.parse(data)); } catch (e) { reject(e); }
      });
    }).on('error', reject);
  });
}

const conns = new Map();

async function ensureConn(bot) {
  const cur = conns.get(bot.port);
  if (cur && cur.ws && cur.ws.readyState === 1) return cur;
  try {
    const pages = await getJson(`http://127.0.0.1:${bot.port}/json`);
    const page = pages.find((p) => p.type === 'page' && p.url.includes('territorial.io'));
    if (!page) return null;
    const ws = new WebSocket(page.webSocketDebuggerUrl);
    let seq = 0;
    const pending = new Map();
    await new Promise((res, rej) => {
      const t = setTimeout(() => rej(new Error('timeout')), 1500);
      ws.onopen = () => { clearTimeout(t); res(); };
      ws.onerror = (e) => { clearTimeout(t); rej(e); };
    });
    ws.onmessage = (ev) => {
      try {
        const msg = JSON.parse(ev.data);
        if (msg.id && pending.has(msg.id)) {
          const fn = pending.get(msg.id);
          pending.delete(msg.id);
          fn(msg.result);
        }
      } catch {}
    };
    const call = (method, params = {}) =>
      new Promise((resolve) => {
        if (ws.readyState !== 1) return resolve(null);
        const id = ++seq;
        const timer = setTimeout(() => {
          pending.delete(id);
          resolve(null);
        }, 1500);
        pending.set(id, (res) => {
          clearTimeout(timer);
          resolve(res);
        });
        ws.send(JSON.stringify({ id, method, params }));
      });
    const obj = { bot, ws, call, lastZoomTick: -1 };
    conns.set(bot.port, obj);
    return obj;
  } catch {
    return null;
  }
}

setInterval(async () => {
  const allStats = [];
  for (const bot of BOTS) {
    const c = await ensureConn(bot);
    if (!c) continue;
    const st = await c.call('Runtime.evaluate', {
      expression: `(() => {
        const panel = document.getElementById("tsb-panel");
        if (panel && !panel.classList.contains("tsb-folded")) {
          panel.classList.add("tsb-folded");
          const btn = panel.querySelector(".tsb-fold");
          if (btn) btn.textContent = "+";
        }
        const ext = window.__fx?.strategyBotExtension;
        if (ext?.settings) ext.settings.folded = true;
        const info = ext?.remote?.state?.info;
        const s = ext?.remote?.snapshot?.();
        const d = window.dictionary;
        const g = d && window[d.game];
        const pixels = d && window[d.sbPixels];
        const teams = d && window[d.sbTeamHolder]?.[d.sbTeams];
        const me = g && g[d.playerId];
        if (s?.inGame && info?.tick > 15 && pixels) {
          if (window.__lastFullZoomTick && window.__fixedTinyZoom !== pixels) {
            window.__fixedTinyZoom = pixels;
            window.__zoomedGamePixels = pixels;
            for (let i = 0; i < 7; i++) {
              document.dispatchEvent(new KeyboardEvent("keydown", { code: "NumpadAdd", key: "+", bubbles: true, cancelable: true }));
            }
          } else if (window.__zoomedGamePixels !== pixels) {
            window.__zoomedGamePixels = pixels;
            window.__fixedTinyZoom = pixels;
            for (let i = 0; i < 11; i++) {
              document.dispatchEvent(new KeyboardEvent("keydown", { code: "NumpadSubtract", key: "-", bubbles: true, cancelable: true }));
            }
          }
        }
        return JSON.stringify({
          port: ${bot.port},
          name: ${JSON.stringify(bot.name)},
          inGame: !!s?.inGame,
          lobby: s?.lobby,
          tick: info?.tick || 0,
          time: info?.tick ? Math.floor(info.tick * 0.056 / 60) + ":" + String(Math.floor((info.tick * 0.056) % 60)).padStart(2, "0") : "-",
          alive: !!info?.alive,
          terr: info?.territory || 0,
          land: info?.land || 0,
          bal: info?.balance || 0,
          rank: info?.rank || "-",
          players: info?.players || "-",
          team: teams && Number.isInteger(me) ? teams[me] : "-"
        });
      })()`,
      returnByValue: true,
    });
    if (st?.result?.value) {
      try { allStats.push(JSON.parse(st.result.value)); } catch {}
    }
  }

  if (!allStats.length) return;

  // Pick the best active bot to display (prefer alive with largest territory, else inGame, else first)
  const chosen =
    allStats
      .slice()
      .sort((a, b) => (b.alive - a.alive) || (b.inGame - a.inGame) || (b.terr - a.terr))[0] || allStats[0];

  const c = conns.get(chosen.port);
  if (c) {
    const shot = await c.call('Page.captureScreenshot', { format: 'jpeg', quality: 78 });
    if (shot?.data) {
      latestJpeg = Buffer.from(shot.data, 'base64');
      latestMeta = { chosen, squad: allStats };
    }
  }
}, 900);

const HTML = `<!doctype html>
<html lang="zh">
<head>
<meta charset="utf-8" />
<title>[NPL] 全图实时观战</title>
<style>
  body { margin: 0; background: #0b0e14; color: #e6edf3; font-family: system-ui, -apple-system, sans-serif; display: flex; flex-direction: column; height: 100vh; overflow: hidden; }
  header { padding: 8px 16px; background: #161b22; border-bottom: 1px solid #30363d; display: flex; justify-content: space-between; align-items: center; font-size: 13px; flex-shrink: 0; }
  .squad { display: flex; gap: 10px; flex-wrap: wrap; }
  .bot-pill { padding: 3px 8px; border-radius: 5px; background: #21262d; border: 1px solid #30363d; }
  .bot-pill.alive { border-color: #2ea043; }
  .bot-pill.active { background: #1f6feb33; border-color: #58a6ff; }
  main { flex: 1; display: flex; align-items: center; justify-content: center; background: #000; overflow: hidden; }
  img { max-width: 100%; max-height: 100%; object-fit: contain; display: block; }
</style>
</head>
<body>
<header>
  <div id="title"><strong>[NPL] 全图实时观战</strong></div>
  <div style="display:flex;gap:8px;align-items:center;">
    <button onclick="fetch('/zoom?dir=in')" style="padding:3px 10px;border-radius:5px;border:1px solid #58a6ff;background:#1f6feb44;color:#fff;cursor:pointer;">🔍+ 放大</button>
    <button onclick="fetch('/zoom?dir=out')" style="padding:3px 10px;border-radius:5px;border:1px solid #30363d;background:#21262d;color:#e6edf3;cursor:pointer;">🔍- 缩小</button>
    <div class="squad" id="squad">加载中...</div>
  </div>
</header>
<main>
  <img id="screen" src="/live.jpg" />
</main>
<script>
setInterval(async () => {
  const t = Date.now();
  const img = document.getElementById('screen');
  if (img) img.src = '/live.jpg?t=' + t;
  try {
    const r = await fetch('/meta?t=' + t);
    const m = await r.json();
    if (m.chosen) {
      const c = m.chosen;
      const pct = c.land > 0 ? ((c.terr / c.land) * 100).toFixed(1) + '%' : '-';
      document.getElementById('title').innerHTML = \`<strong>当前视角：\${c.name}</strong> | Team \${c.team} | Tick \${c.tick} (\${c.time}) | 排名 #\${c.rank}/\${c.players} | 领土 \${c.terr.toLocaleString()} (\${pct})\`;
    }
    if (m.squad) {
      document.getElementById('squad').innerHTML = m.squad.map(b => {
        const pct = b.land > 0 ? ((b.terr / b.land) * 100).toFixed(1) + '%' : (b.lobby?.inLobby ? '大厅' : '-');
        const cls = ['bot-pill', b.alive ? 'alive' : '', m.chosen?.port === b.port ? 'active' : ''].join(' ');
        return \`<span class="\${cls}">\${b.name.replace('[NPL] ','')}: \${b.alive ? '#' + b.rank + ' (' + pct + ')' : (b.inGame ? '阵亡' : '大厅')}</span>\`;
      }).join('');
    }
  } catch {}
}, 900);
</script>
</body>
</html>`;

http.createServer((req, res) => {
  const u = new URL(req.url, 'http://127.0.0.1');
  if (u.pathname === '/' || u.pathname === '/index.html') {
    res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8', 'Cache-Control': 'no-store' });
    res.end(HTML);
    return;
  }
  if (u.pathname === '/zoom') {
    const dir = u.searchParams.get('dir');
    const code = dir === 'out' ? 'NumpadSubtract' : 'NumpadAdd';
    const key = dir === 'out' ? '-' : '+';
    for (const c of conns.values()) {
      c.call('Runtime.evaluate', {
        expression: `for(let i=0;i<2;i++) document.dispatchEvent(new KeyboardEvent("keydown", { code: "${code}", key: "${key}", bubbles: true, cancelable: true }));`
      });
    }
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ ok: true, dir }));
    return;
  }
  if (u.pathname === '/meta') {
    res.writeHead(200, { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' });
    res.end(JSON.stringify(latestMeta));
    return;
  }
  if (u.pathname === '/live.jpg') {
    if (!latestJpeg) {
      res.writeHead(404);
      res.end();
      return;
    }
    res.writeHead(200, { 'Content-Type': 'image/jpeg', 'Cache-Control': 'no-store' });
    res.end(latestJpeg);
    return;
  }
  res.writeHead(404);
  res.end('Not found');
}).listen(8199, '127.0.0.1', () => {
  console.log('Single full-map spectator server listening on http://127.0.0.1:8199');
});
