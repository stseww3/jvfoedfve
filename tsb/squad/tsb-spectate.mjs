import http from 'node:http';

let latestJpeg = null;
let latestMeta = { chosen: null, squad: [] };
let pendingZoom = null;

const HTML = `<!doctype html>
<html lang="zh">
<head>
<meta charset="utf-8" />
<title>[NPL] 10兄弟 全图实时观战</title>
<style>
  body { margin: 0; background: #0b0e14; color: #e6edf3; font-family: system-ui, -apple-system, sans-serif; display: flex; flex-direction: column; height: 100vh; overflow: hidden; }
  header { padding: 8px 16px; background: #161b22; border-bottom: 1px solid #30363d; display: flex; justify-content: space-between; align-items: center; font-size: 13px; flex-shrink: 0; gap: 10px; flex-wrap: wrap; }
  .squad { display: flex; gap: 6px; flex-wrap: wrap; }
  .bot-pill { padding: 3px 7px; border-radius: 5px; background: #21262d; border: 1px solid #30363d; font-size: 12px; }
  .bot-pill.alive { border-color: #2ea043; }
  .bot-pill.active { background: #1f6feb33; border-color: #58a6ff; }
  main { flex: 1; display: flex; align-items: center; justify-content: center; background: #000; overflow: hidden; }
  img { max-width: 100%; max-height: 100%; object-fit: contain; display: block; }
</style>
</head>
<body>
<header>
  <div id="title"><strong>[NPL] 全图实时观战</strong></div>
  <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;">
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
      document.getElementById('title').innerHTML = \`<strong>当前视角：\${c.name}</strong> | Team \${c.team} | Tick \${c.tick} (\${c.time}) | 排名 #\${c.rank}/\${c.players} | 领土 \${(c.terr || 0).toLocaleString()} (\${pct})\`;
    }
    if (m.squad) {
      document.getElementById('squad').innerHTML = m.squad.map(b => {
        const pct = b.land > 0 ? ((b.terr / b.land) * 100).toFixed(1) + '%' : (b.lobby?.inLobby ? '大厅' : '-');
        const cls = ['bot-pill', b.alive ? 'alive' : '', m.chosen?.port === b.port ? 'active' : ''].join(' ');
        return \`<span class="\${cls}">\${b.name.replace('[NPL] ','')}: \${b.alive ? '#' + b.rank + ' (' + pct + ')' : (b.inGame ? '阵亡' : '大厅')}</span>\`;
      }).join('');
    }
  } catch {}
}, 800);
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
    pendingZoom = dir === 'out' ? 'out' : 'in';
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ ok: true, dir: pendingZoom }));
    return;
  }
  if (u.pathname === '/ingest' && req.method === 'POST') {
    let body = '';
    req.on('data', (c) => body += c);
    req.on('end', () => {
      try {
        const msg = JSON.parse(body);
        if (msg.type === 'all_stats') {
          if (msg.stats) latestMeta = { chosen: msg.chosen, squad: msg.stats };
          if (msg.jpeg) latestJpeg = Buffer.from(msg.jpeg, 'base64');
        } else if (msg.type === 'frame_only' && msg.jpeg) {
          latestJpeg = Buffer.from(msg.jpeg, 'base64');
          if (msg.chosen) latestMeta.chosen = msg.chosen;
        }
      } catch {}
      const z = pendingZoom;
      pendingZoom = null;
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ zoom: z }));
    });
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
  console.log('Single-brother browser screen spectator listening on http://127.0.0.1:8199');
});
