import fs from 'node:fs';
import http from 'node:http';
import { createRequire } from 'node:module';

const require = createRequire('/tmp/node_modules/ws/package.json');
const { WebSocketServer } = require('ws');

const rawGameJs = fs.readFileSync('/tmp/live_game_js.js', 'utf8');
// Patch hostname check, disable Turnstile & external WebSockets, and add 2-packet jitter buffer in aeA() for buttery-smooth 56ms ticks!
const spectatorGameJs = rawGameJs
  .replace('this.hostname=window.location.hostname.toLowerCase()', 'this.hostname="territorial.io"')
  .replace('https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit', '')
  .replace('b=new WebSocket(mF);', 'b={readyState:3,send(){},close(){}};return;')
  .replace('b=new WebSocket("wss://territorial.io/s52/");', 'b={readyState:3,send(){},close(){}};return;')
  .replace('if(this.ae7.length>0){for(aC=this.ae8-2', 'if(this.ae7.length>2){for(aC=this.ae8-2');

let currentMatch = null; // { key, tN, aFq, aFr, packets: [base64...] }
let latestStats = [];
let latestJpeg = null;
let latestChosen = null;

const viewers = new Set();

function broadcastToViewers(obj) {
  const str = JSON.stringify(obj);
  for (const ws of viewers) {
    if (ws.readyState === 1) {
      try { ws.send(str); } catch {}
    }
  }
}

// All stats, screenshots, and real-time game packets are pushed to /ingest by tsb-team-squad.mjs
// so tsb-spectate NEVER opens a competing CDP WebSocket to 9223..9227!

const HTML = `<!doctype html>
<html lang="zh">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no" />
<title>[NPL] 10兄弟 原生引擎实时观战</title>
<style>
  * { box-sizing: border-box; }
  body { margin: 0; background: #0b0e14; color: #e6edf3; font-family: system-ui, -apple-system, sans-serif; overflow: hidden; width: 100vw; height: 100vh; }
  #topbar {
    position: fixed; top: 0; left: 0; right: 0; z-index: 9999;
    padding: 6px 12px; background: rgba(22, 27, 34, 0.88); backdrop-filter: blur(6px);
    border-bottom: 1px solid #30363d; display: flex; justify-content: space-between; align-items: center;
    font-size: 12px; gap: 8px; flex-wrap: wrap;
  }
  .squad { display: flex; gap: 6px; flex-wrap: wrap; align-items: center; }
  .bot-pill {
    padding: 2px 7px; border-radius: 4px; background: #21262d; border: 1px solid #30363d;
    cursor: pointer; user-select: none; transition: 0.15s; font-size: 11px;
  }
  .bot-pill:hover { border-color: #58a6ff; }
  .bot-pill.alive { border-color: #2ea043; color: #7ee787; }
  .bot-pill.focused { background: #1f6feb66; border-color: #58a6ff; color: #fff; font-weight: 600; }
  .btn {
    padding: 3px 9px; border-radius: 4px; border: 1px solid #30363d; background: #21262d;
    color: #e6edf3; cursor: pointer; font-size: 12px;
  }
  .btn.active { background: #1f6feb; border-color: #58a6ff; color: #fff; }
  #canvasA { position: absolute; top: 0; left: 0; width: 100vw; height: 100vh; z-index: 1; display: block; }
  #fallbackView {
    position: absolute; top: 38px; left: 0; right: 0; bottom: 0; z-index: 5;
    background: #000; display: none; align-items: center; justify-content: center;
  }
  #fallbackView img { max-width: 100%; max-height: 100%; object-fit: contain; }
</style>
</head>
<body>
<div id="topbar">
  <div style="display:flex;align-items:center;gap:8px;">
    <strong id="title">[NPL] 10兄弟 实时引擎观战</strong>
    <span id="statusBadge" style="color:#8b949e;">连接实时帧流中...</span>
  </div>
  <div class="squad" id="squad">加载 10 兄弟状态中...</div>
  <div style="display:flex;gap:6px;align-items:center;">
    <button class="btn active" id="btnEngine" onclick="setMode('engine')">🎮 自由放缩引擎</button>
    <button class="btn" id="btnStream" onclick="setMode('stream')">🖼️ 画面镜像</button>
  </div>
</div>

<canvas id="canvasA"></canvas>
<div id="fallbackView">
  <img id="fallbackImg" src="/live.jpg" />
</div>

<script>
window.dictionary = {};
window.turnstile = { render() { return "spec"; }, remove() {}, reset() {} };
window.__fx = {
  strategyBot: new Proxy({}, {
    get(t, k) {
      if (k === 'beforeTick') return () => true;
      return () => {};
    }
  })
};
</script>
<script src="/game-client.js"></script>
<script>
let viewMode = 'engine';
let activeMatchKey = null;
let focusedPlayerId = -1;
let engineBooted = false;

function setMode(m) {
  viewMode = m;
  document.getElementById('btnEngine').className = 'btn' + (m === 'engine' ? ' active' : '');
  document.getElementById('btnStream').className = 'btn' + (m === 'stream' ? ' active' : '');
  document.getElementById('fallbackView').style.display = m === 'stream' ? 'flex' : 'none';
}

function b64ToUint8(b64) {
  const bin = atob(b64);
  const arr = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) arr[i] = bin.charCodeAt(i);
  return arr;
}

function focusPlayer(pid) {
  if (typeof aE === 'object' && aE && pid >= 0) {
    focusedPlayerId = pid;
    aE.fJ = pid;
    if (typeof aI === 'object' && aI && aI.nq && ah && ah.hN && ah.hN[pid] > 0) {
      aI.nq(pid, 400, true, 0.25);
    }
  }
}

function ensureEngineAssets() {
  return new Promise((resolve) => {
    const check = () => {
      try {
        if (typeof ac === 'object' && ac) {
          if (!ac.v0()) ac.aJ0();
          if (ac.v0()) return resolve();
        }
      } catch {}
      setTimeout(check, 50);
    };
    check();
  });
}

async function startSpectatorMatch(msg) {
  await ensureEngineAssets();
  activeMatchKey = msg.key;
  try {
    if (typeof b1 === 'object' && b1 && b1.z) {
      b1.z.send = function() {};
    }
    if (typeof u === 'object' && u && u.y) u.y();
    // Find first [NPL] player in aFq as default selectedPlayer
    let nplIdx = msg.aFr || 0;
    if (Array.isArray(msg.aFq)) {
      const idx = msg.aFq.findIndex(p => String(p.username || '').toUpperCase().includes('NPL'));
      if (idx >= 0) nplIdx = idx;
    }
    bq.aF3.aFu(msg.tN, msg.aFq, nplIdx);
    engineBooted = true;
    if (viewMode === 'engine') {
      document.getElementById('fallbackView').style.display = 'none';
    }
    const pkts = msg.packets || [];
    const origRender = (typeof be === 'object' && be && be.render) ? be.render.bind(be) : null;
    if (origRender && pkts.length > 2) {
      be.render = function() {};
    }
    for (let i = 0; i < pkts.length; i++) {
      bi.a2Q.aWV(b64ToUint8(pkts[i]));
    }
    // Fast-forward all queued main-game packets right to the live edge!
    if (bi.a2Q && Array.isArray(bi.a2Q.ae7)) {
      while (bi.a2Q.ae7.length > 1) {
        bi.a2Q.aeA();
      }
    }
    if (origRender) {
      be.render = origRender;
      be.render();
    }
    // Zoom out to show full map initially
    setTimeout(() => {
      if (typeof aI === 'object' && aI && aI.o4) {
        aI.o4(300);
      }
    }, 150);
    document.getElementById('statusBadge').textContent = '🟢 实时帧流已同步 (可鼠标拖拽 / 滚轮任意缩放)';
  } catch (e) {
    console.error('startSpectatorMatch error:', e);
  }
}

function connectWS() {
  const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
  const ws = new WebSocket(proto + '//' + location.host + '/ws');
  ws.onmessage = async (ev) => {
    try {
      const msg = JSON.parse(ev.data);
      if (msg.type === 'init') {
        await startSpectatorMatch(msg);
      } else if (msg.type === 'pkts') {
        if (engineBooted && msg.key === activeMatchKey && Array.isArray(msg.pkts)) {
          for (const b64 of msg.pkts) {
            bi.a2Q.aWV(b64ToUint8(b64));
          }
        }
      } else if (msg.type === 'stats' && Array.isArray(msg.squad)) {
        renderSquadBar(msg.squad);
      }
    } catch (e) {}
  };
  ws.onclose = () => setTimeout(connectWS, 1500);
}

function renderSquadBar(squad) {
  const inGameBots = squad.filter(b => b.inGame);
  if (inGameBots.length > 0) {
    const c = inGameBots.slice().sort((a, b) => (b.alive - a.alive) || (b.terr - a.terr))[0];
    const totalTerr = inGameBots.reduce((s, b) => s + (b.terr || 0), 0);
    const pct = c.land > 0 ? ((totalTerr / c.land) * 100).toFixed(1) + '%' : '-';
    document.getElementById('title').innerHTML =
      '<strong>[NPL] 10兄弟</strong> | Team ' + c.team + ' | Tick ' + c.tick + ' (' + c.time + ') | 合计占图 ' + pct;
  } else {
    document.getElementById('statusBadge').textContent = '⏳ 10兄弟正在大厅集结进入下一局...';
  }
  document.getElementById('squad').innerHTML = squad.map(b => {
    const shortName = b.name.replace('[NPL] ', '');
    const pct = b.land > 0 ? ((b.terr / b.land) * 100).toFixed(1) + '%' : (b.lobby?.inLobby ? '大厅' : '-');
    const cls = ['bot-pill', b.alive ? 'alive' : '', (b.meId >= 0 && b.meId === focusedPlayerId) ? 'focused' : ''].join(' ');
    const statusTxt = b.alive ? ('#' + b.rank + ' ' + pct) : (b.inGame ? '阵亡' : (b.lobby?.inLobby ? '大厅R' + b.lobby.room : '准备'));
    return '<span class="' + cls + '" onclick="focusPlayer(' + (b.meId ?? -1) + ')">' + shortName + ': ' + statusTxt + '</span>';
  }).join('');
}

setInterval(() => {
  if (viewMode === 'stream' || !engineBooted) {
    const img = document.getElementById('fallbackImg');
    if (img) img.src = '/live.jpg?t=' + Date.now();
  }
}, 900);

window.addEventListener('load', () => {
  // Hide main menu DOM elements immediately so spectator never sees the raw game menu
  setTimeout(() => {
    try { if (typeof u === 'object' && u && u.y) u.y(); } catch {}
    if (!engineBooted) {
      document.getElementById('fallbackView').style.display = 'flex';
    }
  }, 150);
  setTimeout(connectWS, 200);
});
</script>
</body>
</html>`;

const server = http.createServer((req, res) => {
  const u = new URL(req.url, 'http://127.0.0.1');
  if (u.pathname === '/' || u.pathname === '/index.html') {
    res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8', 'Cache-Control': 'no-store' });
    res.end(HTML);
    return;
  }
  if (u.pathname === '/game-client.js') {
    res.writeHead(200, { 'Content-Type': 'application/javascript; charset=utf-8', 'Cache-Control': 'no-store' });
    res.end(spectatorGameJs);
    return;
  }
  if (u.pathname === '/ingest' && req.method === 'POST') {
    let body = '';
    req.on('data', (c) => body += c);
    req.on('end', () => {
      try {
        const msg = JSON.parse(body);
        if (msg.type === 'all_stats') {
          latestStats = msg.stats || [];
          latestChosen = msg.chosen || latestStats[0] || null;
          if (msg.jpeg) latestJpeg = Buffer.from(msg.jpeg, 'base64');
          broadcastToViewers({ type: 'stats', squad: latestStats });
        } else if (msg.type === 'init') {
          if (!currentMatch || currentMatch.key !== msg.key) {
            currentMatch = { key: msg.key, tN: msg.tN, aFq: msg.aFq, aFr: msg.aFr, packets: msg.pkts || [] };
            broadcastToViewers({ type: 'init', ...currentMatch });
          }
        } else if (msg.type === 'pkt') {
          if (currentMatch && currentMatch.key === msg.key) {
            if (msg.b64) {
              currentMatch.packets.push(msg.b64);
              broadcastToViewers({ type: 'pkts', key: msg.key, pkts: [msg.b64] });
            } else if (Array.isArray(msg.pkts) && msg.pkts.length) {
              currentMatch.packets.push(...msg.pkts);
              broadcastToViewers({ type: 'pkts', key: msg.key, pkts: msg.pkts });
            }
          }
        }
      } catch {}
      res.writeHead(200);
      res.end('ok');
    });
    return;
  }
  if (u.pathname === '/meta') {
    res.writeHead(200, { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' });
    res.end(JSON.stringify({ chosen: latestChosen, squad: latestStats, matchKey: currentMatch?.key || null, pktCount: currentMatch?.packets?.length || 0 }));
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
});

const wss = new WebSocketServer({ server, path: '/ws' });
wss.on('connection', (ws) => {
  viewers.add(ws);
  if (latestStats.length) {
    ws.send(JSON.stringify({ type: 'stats', squad: latestStats }));
  }
  if (currentMatch) {
    ws.send(JSON.stringify({ type: 'init', ...currentMatch }));
  }
  ws.on('close', () => viewers.delete(ws));
});

server.listen(8199, '127.0.0.1', () => {
  console.log('Real-Frontend + 10-Brother Spectator Server listening on http://127.0.0.1:8199');
});
