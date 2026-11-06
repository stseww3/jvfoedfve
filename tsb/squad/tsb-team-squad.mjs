import fs from 'fs';
import http from 'http';

const pageJsSource = fs.readFileSync('/tmp/tsb-team-ext/page.js', 'utf8');
const getV27TeamSource = () => fs.readFileSync('/tmp/v27-team-live.js', 'utf8');

const BOTS = [
  { port: 9223, name: 'Mishi [NPL]', slot: 0 },
  { port: 9224, name: '[NPL] Matzz', slot: 1 },
  { port: 9225, name: 'Kiholma [NPL]', slot: 2 },
  { port: 9226, name: 'Leo_99 [NPL]', slot: 3 },
  { port: 9227, name: '[NPL] Racoon', slot: 4 },
];

const isWaitNplMode = () => fs.existsSync('/tmp/tsb-wait-npl.flag');

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

function makeBootstrapScript(botName, slot) {
  return `
if (!window.__tsbPageInjected) {
  window.__tsbPageInjected = true;
  window.__tsbPlayerName = ${JSON.stringify(botName)};
  window.__tsbPlayerColor = 4095;
  window.__tsbSquadSlot = ${slot};
  window.__tsbFollowLeader = ${isWaitNplMode() ? JSON.stringify("npl") : JSON.stringify("")};
  window.__tsbWaitForLeader = ${isWaitNplMode() ? 'true' : 'false'};
  window.__tsbSquadSyncHold = true;
  try {
    sessionStorage.removeItem('territorialStrategyBotRecover');
    const extCfg = {
      spawn: true,
      play: true,
      autoStart: false,
      manual: true,
      armed: false,
      stay: true,
      allow: '',
      cmdUrl: '',
      resultUrl: 'http://127.0.0.1/team-result',
      key: 'aKURzbiCpouWOcpOSOffKLXqTXPaVsLG',
      pollMs: 3000,
      folded: false,
      port: 8765,
      strategy: 'file:v27team'
    };
    localStorage.setItem('territorialStrategyBotExtension', JSON.stringify(extCfg));
  } catch (e) {}
  document.addEventListener('tsb-remote', (e) => {
    try {
      const c = JSON.parse(e.detail);
      if (c.kind === 'post' && window.__tsbReportResult) {
        window.__tsbReportResult(c.body);
      }
    } catch {}
  });
  ${pageJsSource}
}
`;
}

const clients = [];

async function attachBot({ port, name, slot }) {
  const pages = await getJson(`http://127.0.0.1:${port}/json`);
  const page = pages.find((p) => p.type === 'page' && p.url.includes('territorial.io'));
  if (!page) {
    console.error(`[${name}] No territorial.io tab on port ${port}`);
    return null;
  }
  console.log(`[${name}] Attaching on port ${port}:`, page.webSocketDebuggerUrl);
  const ws = new WebSocket(page.webSocketDebuggerUrl);
  let seq = 0;
  let clicking = false;
  const pending = new Map();

  const send = (method, params = {}) => {
    const id = ++seq;
    ws.send(JSON.stringify({ id, method, params }));
    return id;
  };

  const evalJs = (expression, awaitPromise = false) =>
    new Promise((resolve) => {
      const id = send('Runtime.evaluate', { expression, awaitPromise });
      const timer = setTimeout(() => {
        pending.delete(id);
        resolve(null);
      }, 4000);
      pending.set(id, (res) => {
        clearTimeout(timer);
        resolve(res);
      });
    });

  const client = { port, name, slot, ws, send, evalJs, freshToken: false, wasInGame: false, lastReloadAt: Date.now() };

  function clickTurnstile() {
    if (clicking) return;
    clicking = true;
    console.log(`[${name}] Turnstile render detected! Polling for widget & clicking checkbox...`);
    let tries = 0;
    const iv = setInterval(async () => {
      tries++;
      if (client.freshToken || tries > 10) {
        clearInterval(iv);
        clicking = false;
        return;
      }
      const rectStr = await evalJs(`(() => {
        const d = Array.from(document.querySelectorAll("div")).find(x => x.style.zIndex === "100");
        if (!d) return "GONE";
        const r = d.getBoundingClientRect();
        return JSON.stringify({ w: r.width, h: r.height });
      })()`);
      if (rectStr === "GONE") {
        clearInterval(iv);
        clicking = false;
        return;
      }
      try {
        const { w, h } = JSON.parse(rectStr || "{}");
        if (w >= 100 && h >= 30) {
          send("Input.dispatchMouseEvent", { type: "mouseMoved", x: 180, y: 180 });
          setTimeout(() => send("Input.dispatchMouseEvent", { type: "mouseMoved", x: 28, y: 32 }), 250);
          setTimeout(() => send("Input.dispatchMouseEvent", { type: "mousePressed", x: 28, y: 32, button: "left", clickCount: 1 }), 450);
          setTimeout(() => send("Input.dispatchMouseEvent", { type: "mouseReleased", x: 28, y: 32, button: "left", clickCount: 1 }), 560);
        }
      } catch {}
    }, 1800);
  }

  async function importStrategy() {
    const src = getV27TeamSource();
    await evalJs(
      `(async () => {
        window.__tsbPlayerName = ${JSON.stringify(name)};
        window.__tsbPlayerColor = 4095;
        window.__tsbSquadSlot = ${slot};
        window.__tsbFollowLeader = ${isWaitNplMode() ? JSON.stringify("npl") : JSON.stringify("")};
        window.__tsbWaitForLeader = ${isWaitNplMode() ? 'true' : 'false'};
        const ext = window.__fx.strategyBotExtension;
        await ext.strategies.add({ name: "v27team.js", text: async () => ${JSON.stringify(src)} });
        ext.settings.armed = true;
        ext.remote.state.loop = "team";
        return "OK";
      })()`,
      true
    );
    client.freshToken = true;
    console.log(`[${name}] Fresh Turnstile token ready & Distributed-Spawn Boss-Guard v27team (slot=${slot}) imported!`);
  }

  ws.onopen = async () => {
    send('Page.enable');
    send('Runtime.enable');
    send('Runtime.addBinding', { name: '__tsbReportResult' });
    const bootstrap = makeBootstrapScript(name, slot);
    send('Page.addScriptToEvaluateOnNewDocument', { source: bootstrap });
    // Check if already in game or in lobby before reloading!
    const snapStr = await evalJs(`JSON.stringify(window.__fx?.strategyBotExtension?.remote?.snapshot?.() || {})`);
    let snap = {};
    try { snap = JSON.parse(snapStr || '{}'); } catch {}
    if (snap.inGame && snap.alive && !snap.over) {
      console.log(`[${name}] Already alive in an active game! Hot-updating strategy without reload.`);
      await importStrategy();
      return;
    }
    client.lastReloadAt = Date.now();
    send('Page.reload', { ignoreCache: false });
  };

  ws.onmessage = (ev) => {
    let msg;
    try { msg = JSON.parse(ev.data); } catch { return; }
    if (msg.id && pending.has(msg.id)) {
      const fn = pending.get(msg.id);
      pending.delete(msg.id);
      fn(msg.result?.result?.value);
      return;
    }
    if (msg.method === 'Runtime.bindingCalled' && msg.params.name === '__tsbReportResult') {
      try {
        const data = JSON.parse(msg.params.payload);
        if (data.type === 'result') {
          const line = JSON.stringify({ bot: name, port, ...data });
          fs.appendFileSync('/tmp/tsb-team-results.jsonl', line + '\n');
          console.log(`[RESULT ${name}] result=${data.result} event=${data.event} place=${data.place} peak=${data.peak} team=${JSON.stringify(data.team || null)}`);
        }
      } catch {}
    } else if (msg.method === 'Runtime.consoleAPICalled') {
      const text = (msg.params.args || []).map((a) => a.value ?? a.description ?? '').join(' ');
      if (text.includes('turnstile render')) {
        clickTurnstile();
      } else if (text.includes('turnstile success')) {
        console.log(`[${name}]`, text);
        setTimeout(importStrategy, 300);
      } else if (
        text.includes('sendTokenToLobby') ||
        text.includes('Connection to Server') ||
        text.includes('socket close')
      ) {
        console.log(`[${name}]`, text);
        if (text.includes('error 4591') || text.includes('error 4215')) {
          client.freshToken = false;
        }
      }
    }
  };

  clients.push(client);
  return client;
}

for (const bot of BOTS) {
  await attachBot(bot);
}

let lastSyncLaunch = Date.now();
let reloadingForFreshTokens = false;

function reloadClientForToken(c) {
  c.freshToken = false;
  c.wasInGame = false;
  c.lastReloadAt = Date.now();
  c.send('Page.reload', { ignoreCache: false });
}

setInterval(async () => {
  if (clients.length < 5) return;
  const waitMode = isWaitNplMode();

  const states = await Promise.all(
    clients.map(async (c) => {
      const raw = await c.evalJs(`(() => {
        const s = window.__fx?.strategyBotExtension?.remote?.snapshot?.();
        return JSON.stringify(s || {});
      })()`);
      try { return JSON.parse(raw || '{}'); } catch { return {}; }
    })
  );

  // Only allow bots to click Ready when ALL 5 bots are in Team Room 0 together (or when waiting for Boss npl)!
  const all5InRoom0 =
    states.every((s) => s.lobby && s.lobby.inLobby && s.lobby.room === 0) &&
    Math.max(...states.map((s) => s.lobby.startsIn || 0)) - Math.min(...states.map((s) => s.lobby.startsIn || 0)) <= 20;

  await Promise.all(
    clients.map((c) =>
      c.evalJs(`(() => {
        window.__tsbPlayerName = ${JSON.stringify(c.name)};
        window.__tsbPlayerColor = 4095;
        window.__tsbSquadSlot = ${c.slot};
        window.__tsbFollowLeader = ${waitMode || !all5InRoom0 ? JSON.stringify("npl") : JSON.stringify("")};
        window.__tsbWaitForLeader = ${waitMode || !all5InRoom0 ? 'true' : 'false'};
      })()`)
    )
  );

  // Unified Backend Spawn Coordinator: if bots are in spawnPhase, coordinate unique spawn positions!
  const inSpawnIndices = states.map((s, idx) => (s.inGame && s.spawnPhase ? idx : -1)).filter((i) => i >= 0);
  if (inSpawnIndices.length > 0) {
    // Query top 10 spawn candidates from the first bot in spawn phase and assign distinct far-apart spots to each bot!
    const firstClient = clients[inSpawnIndices[0]];
    const candsJson = await firstClient.evalJs(`(() => {
      const d = window.dictionary, g = window[d?.game];
      const view = window.__fx?.strategyBotExtension?.bot?.view;
      const pol = window.__fx?.strategyBotExtension?.bot?.ctl?.policy;
      if (!view || !pol) return "[]";
      view.refresh();
      const cands = pol.spawnVsPeople ? pol.spawnVsPeople(view, 12) : pol.spawnCandidates(view, 12);
      return JSON.stringify({ W: view.W, land: view.land, cands: cands || [] });
    })()`);
    try {
      const { W, land, cands } = JSON.parse(candsJson || '{}');
      if (Array.isArray(cands) && cands.length > 0 && W > 0) {
        const minSep = Math.max(95, Math.min(165, 0.45 * Math.sqrt(land || 250000)));
        const chosen = [];
        for (const p of cands) {
          const x = p % W, y = Math.floor(p / W);
          if (chosen.every((q) => Math.hypot(x - (q % W), y - Math.floor(q / W)) >= minSep)) {
            chosen.push(p);
          }
        }
        while (chosen.length < 5) chosen.push(cands[chosen.length % cands.length]);
        await Promise.all(
          inSpawnIndices.map((idx, rank) => {
            const targetPos = chosen[rank % chosen.length];
            return clients[idx].evalJs(`(() => {
              const view = window.__fx?.strategyBotExtension?.bot?.view;
              if (view && view.spawnPhase) view.spawn(${targetPos}, view.me);
            })()`);
          })
        );
      }
    } catch {}
  }

  states.forEach((s, idx) => {
    if (s.inGame) {
      clients[idx].wasInGame = true;
      clients[idx].freshToken = false;
    }
    if (s.lobby?.stopped && s.lobby.stopped.includes('4591')) {
      clients[idx].freshToken = false;
    }
  });

  const anyAliveInGame = states.some((s) => s.inGame && s.alive && !s.over);
  if (anyAliveInGame) {
    reloadingForFreshTokens = false;
    return;
  }

  const needReload = clients.filter((c, i) => !c.freshToken && !(states[i]?.lobby?.inLobby) && Date.now() - c.lastReloadAt > 45000);
  if (needReload.length > 0 && !reloadingForFreshTokens && Date.now() - lastSyncLaunch > 10000) {
    reloadingForFreshTokens = true;
    lastSyncLaunch = Date.now();
    console.log(`[SQUAD-SYNC] Reloading ${needReload.map(c => c.name).join(', ')} to mint fresh Turnstile tokens...`);
    for (const c of needReload) {
      reloadClientForToken(c);
    }
    setTimeout(() => { reloadingForFreshTokens = false; }, 7500);
    return;
  }

  if (clients.some((c, i) => !c.freshToken && !(states[i]?.lobby?.inLobby))) return;
  if (Date.now() - lastSyncLaunch < 10000) return;

  const notInRoom0 = clients.filter((c, i) => !(states[i]?.lobby?.inLobby && states[i]?.lobby?.room === 0));
  if (notInRoom0.length > 0) {
    lastSyncLaunch = Date.now();
    console.log(`[SQUAD-SYNC] Entering Team Room 0 for ${notInRoom0.map(c => c.name).join(', ')} (waitForLeader=${waitMode})...`);
    for (let i = 0; i < notInRoom0.length; i++) {
      const c = notInRoom0[i];
      setTimeout(() => {
        c.evalJs(`(() => {
          const d = window.dictionary;
          const g = window[d.game];
          if (g && g[d.sbLeave] && g[d.gameState] !== 0) g[d.sbLeave](true);
          const ext = window.__fx.strategyBotExtension;
          ext.settings.armed = true;
          ext.remote.state.loop = "team";
          window.__tsbSquadSyncHold = false;
          window.__fx.strategyBot.openMultiplayer(0);
          setTimeout(() => { window.__tsbSquadSyncHold = true; }, 5000);
          return "SYNC_LAUNCHED";
        })()`);
      }, i * 1600);
    }
  }
}, 2500);
