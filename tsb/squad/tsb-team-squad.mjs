import fs from 'node:fs';
import http from 'node:http';
import { createHeadlessBot } from './headless-bot.mjs';

const pageJsSource = fs.readFileSync('/tmp/tsb-team-ext/page.js', 'utf8');
const getV27TeamSource = () => fs.readFileSync('/tmp/v27-team-live.js', 'utf8');

const CHROME_BOTS = [
  { port: 9223, name: '[NPL] Mishi', slot: 0, id: 'mTd7B', pw: 'vivELD0lOKgghLr' },
  { port: 9224, name: '[NPL] Matzz', slot: 1, id: 'vgLjn', pw: 'Cl2xSE00tjOjVBq' },
  { port: 9225, name: '[NPL] Kiholma', slot: 2, id: 'NJmJY', pw: 'zmUT69zzi_Rk80I' },
  { port: 9226, name: '[NPL] Leo_99', slot: 3, id: 'byk85', pw: 'iLFHoRHz4rHvEt0' },
  { port: 9227, name: '[NPL] Racoon', slot: 4, id: '5nvnY', pw: 'DzMzg9vRC1Qnj3z' },
];

const HEADLESS_BOTS = [
  { port: 9305, socksPort: 10811, donorChromePort: 9223, name: '[NPL] Zexos', slot: 5, id: 'JwG5J', pw: 'ASEvJoo4K862kll' },
  { port: 9306, socksPort: 10812, donorChromePort: 9224, name: '[NPL] Talon', slot: 6, id: 'QNNy7', pw: 'UpqFcPh3MHISdPg' },
  { port: 9307, socksPort: 10813, donorChromePort: 9225, name: '[NPL] Vortex', slot: 7, id: 'QcNb5', pw: 'oqHseyPLOB_VYfT' },
  { port: 9308, socksPort: 10814, donorChromePort: 9226, name: '[NPL] Kronos', slot: 8, id: 'BRmym', pw: 'IAn4Vw-8_6_VhgK' },
  { port: 9309, socksPort: 10815, donorChromePort: 9227, name: '[NPL] Nexus', slot: 9, id: 'qQGqw', pw: 'kh_nhYj46nGU6R3' },
];

const isWaitNplMode = () => fs.existsSync('/tmp/tsb-wait-npl.flag');

function postSpectatorIngest(payload, onReply = null) {
  try {
    const data = JSON.stringify(payload);
    const req = http.request({
      hostname: '127.0.0.1',
      port: 8199,
      path: '/ingest',
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(data) }
    }, (res) => {
      let body = '';
      res.on('data', (c) => body += c);
      res.on('end', () => {
        if (onReply) {
          try { onReply(JSON.parse(body)); } catch {}
        }
      });
    });
    req.on('error', () => {});
    req.end(data);
  } catch {}
}

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

function makeBootstrapScript(bot) {
  return `
{
  localStorage.setItem("d105", ${JSON.stringify(bot.id)});
  localStorage.setItem("d106", ${JSON.stringify(bot.pw)});
  localStorage.setItem("v105", "0");
  localStorage.setItem("v106", "0");
  localStorage.setItem("d140", "1");
  localStorage.setItem("v140", "0");
  localStorage.setItem("d121", "4095");
  localStorage.setItem("v121", "0");
  localStorage.setItem("d122", ${JSON.stringify(bot.name)});
  localStorage.setItem("v122", "0");
  localStorage.setItem("d158", "0");
  localStorage.setItem("v158", "0");
}
if (!window.__tsbPageInjected) {
  window.__tsbPageInjected = true;
  window.__tsbPlayerName = ${JSON.stringify(bot.name)};
  window.__tsbPlayerColor = 4095;
  window.__tsbSquadSlot = ${bot.slot};
  window.__tsbFollowLeader = "npl";
  window.__tsbWaitForLeader = true;
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
      folded: true,
      port: 8765,
      strategy: 'file:v27team'
    };
    localStorage.setItem('territorialStrategyBotExtension', JSON.stringify(extCfg));
  } catch (e) {}
  if (!window.__tsbResultHooked) {
    window.__tsbResultHooked = true;
    document.addEventListener('tsb-remote', (e) => {
      try {
        const c = JSON.parse(e.detail);
        if (c.kind === 'post' && window.__tsbReportResult) {
          window.__tsbReportResult(c.body);
        }
      } catch {}
    });
  }
  ${pageJsSource}
}
`;
}

let focusChain = Promise.resolve();
function withWindowFocus(fn) {
  const next = focusChain.then(fn, fn);
  focusChain = next.catch(() => {});
  return next;
}

const clients = [];

function recordResult(name, port, rawPayload) {
  try {
    const data = typeof rawPayload === 'string' ? JSON.parse(rawPayload) : rawPayload;
    if (data && data.type === 'result') {
      const line = JSON.stringify({ bot: name, port, ...data });
      fs.appendFileSync('/tmp/tsb-team-results.jsonl', line + '\n');
      console.log(`[RESULT ${name}] result=${data.result} event=${data.event} place=${data.place} peak=${data.peak} team=${JSON.stringify(data.team || null)}`);
    }
  } catch {}
}

async function attachChromeBot(bot) {
  const { port, name, slot } = bot;
  const pages = await getJson(`http://127.0.0.1:${port}/json`);
  const page = pages.find((p) => p.type === 'page' && p.url.includes('territorial.io'));
  if (!page) {
    console.error(`[${name}] No territorial.io tab on port ${port}`);
    return null;
  }
  const wsUrl = page.webSocketDebuggerUrl || `ws://127.0.0.1:${port}/devtools/page/${page.id}`;
  console.log(`[${name}] Attaching on port ${port}:`, wsUrl);
  const ws = new WebSocket(wsUrl);
  let seq = 0;
  let clicking = false;
  const pending = new Map();

  const send = (method, params = {}) => {
    if (ws.readyState !== 1) return -1;
    const id = ++seq;
    ws.send(JSON.stringify({ id, method, params }));
    return id;
  };

  const evalJs = (expression, awaitPromise = false) =>
    new Promise((resolve) => {
      const id = send('Runtime.evaluate', { expression, awaitPromise, returnByValue: true });
      if (id < 0) return resolve(null);
      const timer = setTimeout(() => {
        pending.delete(id);
        resolve(null);
      }, 4000);
      pending.set(id, (res) => {
        clearTimeout(timer);
        resolve(res?.result?.value);
      });
    });

  const callCdp = (method, params = {}) =>
    new Promise((resolve) => {
      const id = send(method, params);
      if (id < 0) return resolve(null);
      const timer = setTimeout(() => {
        pending.delete(id);
        resolve(null);
      }, 2500);
      pending.set(id, (res) => {
        clearTimeout(timer);
        resolve(res);
      });
    });

  const client = {
    port,
    name,
    slot,
    isHeadless: false,
    ws,
    send,
    evalJs,
    callCdp,
    freshToken: false,
    wasInGame: false,
    lastReloadAt: Date.now(),
    enteredLobbyAt: 0,
    enteredGameAt: 0,
  };

  function clickTurnstile() {
    if (clicking) return;
    clicking = true;
    console.log(`[${name}] Turnstile render detected! Queuing serialized focus & click...`);
    let tries = 0;
    const iv = setInterval(async () => {
      tries++;
      if (client.freshToken || tries > 12) {
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
      if (rectStr === 'GONE') {
        clearInterval(iv);
        clicking = false;
        return;
      }
      try {
        const { w, h } = JSON.parse(rectStr || '{}');
        if (w >= 100 && h >= 30) {
          await withWindowFocus(async () => {
            if (client.freshToken) return;
            send('Page.bringToFront');
            send('Emulation.setFocusEmulationEnabled', { enabled: true });
            send('Input.dispatchMouseEvent', { type: 'mouseMoved', x: 180, y: 180 });
            await new Promise((r) => setTimeout(r, 140));
            send('Input.dispatchMouseEvent', { type: 'mouseMoved', x: 28, y: 32 });
            await new Promise((r) => setTimeout(r, 140));
            send('Input.dispatchMouseEvent', { type: 'mousePressed', x: 28, y: 32, button: 'left', clickCount: 1 });
            await new Promise((r) => setTimeout(r, 90));
            send('Input.dispatchMouseEvent', { type: 'mouseReleased', x: 28, y: 32, button: 'left', clickCount: 1 });
            await new Promise((r) => setTimeout(r, 220));
          });
        }
      } catch {}
    }, 2200);
  }

  async function importStrategy() {
    const src = getV27TeamSource();
    await evalJs(
      `(async () => {
        window.__tsbPlayerName = ${JSON.stringify(name)};
        window.__tsbPlayerColor = 4095;
        window.__tsbSquadSlot = ${slot};
        const ext = window.__fx.strategyBotExtension;
        const sid = await ext.strategies.add({ name: "v27team.js", text: async () => ${JSON.stringify(src)} });
        ext.settings.strategy = sid || "file:v27team";
        if (ext.strategies.changed) ext.strategies.changed(sid || "file:v27team");
        const snap = ext.remote?.snapshot?.();
        if (snap?.inGame) {
          ext.settings.armed = true;
          ext.remote.state.loop = "team";
        } else {
          ext.settings.armed = false;
          ext.remote.state.loop = null;
        }
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
    const bootstrap = makeBootstrapScript(bot);
    send('Page.addScriptToEvaluateOnNewDocument', { source: bootstrap });
    const alreadyPatched = await evalJs(`(() => {
      if (!window.dictionary || !window.__fx?.strategyBotExtension) return "NO";
      const ext = window.__fx.strategyBotExtension;
      if (ext.status.phase === "failed") {
        ext.status.phase = "patched";
        ext.status.error = null;
      }
      if (!window.__tsbResultHooked) {
        window.__tsbResultHooked = true;
        document.addEventListener("tsb-remote", (e) => {
          try {
            const c = JSON.parse(e.detail);
            if (c.kind === "post" && window.__tsbReportResult) window.__tsbReportResult(c.body);
          } catch {}
        });
      }
      localStorage.setItem("d122", ${JSON.stringify(name)});
      localStorage.setItem("v122", "0");
      localStorage.setItem("d121", "4095");
      localStorage.setItem("v121", "0");
      window.__tsbPlayerName = ${JSON.stringify(name)};
      window.__tsbPlayerColor = 4095;
      window.__tsbSquadSlot = ${slot};
      return "YES";
    })()`);
    if (alreadyPatched === 'YES') {
      await importStrategy();
      await evalJs(`(() => {
        const ext = window.__fx?.strategyBotExtension;
        if (ext) {
          ext.settings.armed = true;
          ext.remote.state.loop = "team";
        }
      })()`);
      console.log(`[${name}] Hot-attached without Page.reload (existing Turnstile session preserved)!`);
      return;
    }
    client.lastReloadAt = Date.now();
    client.freshToken = false;
    client.enteredLobbyAt = 0;
    send('Page.reload', { ignoreCache: false });
  };

  ws.onmessage = (ev) => {
    let msg;
    try { msg = JSON.parse(ev.data); } catch { return; }
    if (msg.id && pending.has(msg.id)) {
      const fn = pending.get(msg.id);
      pending.delete(msg.id);
      fn(msg.result);
      return;
    }
    if (msg.method === 'Runtime.bindingCalled' && msg.params.name === '__tsbReportResult') {
      recordResult(name, port, msg.params.payload);
    } else if (msg.method === 'Runtime.consoleAPICalled') {
      const text = (msg.params.args || []).map((a) => a.value ?? a.description ?? '').join(' ');
      if (text.includes('turnstile render')) {
        client.freshToken = false;
        client.enteredLobbyAt = 0;
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
          client.enteredLobbyAt = 0;
        }
      }
    }
  };

  clients.push(client);
  return client;
}

for (const bot of CHROME_BOTS) {
  await attachChromeBot(bot);
}

let activeStreamOwner = null;
let activeStreamKey = null;

async function mintViaDonorChrome(donorPort) {
  for (let w = 0; w < 20; w++) {
    const d = clients.find((c) => !c.isHeadless && c.port === donorPort);
    if (d && d.freshToken) break;
    await new Promise((r) => setTimeout(r, 1000));
  }
  const donor = clients.find((c) => !c.isHeadless && c.port === donorPort);
  if (!donor) throw new Error(`No donor Chrome on ${donorPort}`);
  donor.send('Page.bringToFront');
  donor.send('Emulation.setFocusEmulationEnabled', { enabled: true });
  await donor.evalJs(`(() => {
    window.__mintedToken = null;
    const old = document.getElementById("mint-ts");
    if (old) old.remove();
    const d = document.createElement("div");
    d.id = "mint-ts";
    d.style.position = "fixed";
    d.style.left = "0";
    d.style.top = "0";
    d.style.zIndex = "100";
    document.body.appendChild(d);
    const wid = window.turnstile.render(d, {
      sitekey: "0x4AAAAAAEI8HZoG8nJMzxt1",
      action: "enter_lobby",
      appearance: "interaction-only",
      callback: (tok) => {
        window.__mintedToken = tok;
        try { window.turnstile.remove(wid); d.remove(); } catch {}
      }
    });
    return "RENDERED";
  })()`);
  for (let i = 0; i < 12; i++) {
    await new Promise((r) => setTimeout(r, 850));
    donor.send('Input.dispatchMouseEvent', { type: 'mouseMoved', x: 180, y: 180 });
    donor.send('Input.dispatchMouseEvent', { type: 'mouseMoved', x: 28, y: 32 });
    donor.send('Input.dispatchMouseEvent', { type: 'mousePressed', x: 28, y: 32, button: 'left', clickCount: 1 });
    donor.send('Input.dispatchMouseEvent', { type: 'mouseReleased', x: 28, y: 32, button: 'left', clickCount: 1 });
    const tok = await donor.evalJs('window.__mintedToken || ""');
    if (tok && typeof tok === 'string' && tok.length > 100) {
      return tok;
    }
  }
  throw new Error('mint timeout');
}

for (const bot of HEADLESS_BOTS) {
  const hc = createHeadlessBot(bot, {
    getStrategySource: getV27TeamSource,
    mintTurnstileToken: mintViaDonorChrome,
    onResult(c, payload) {
      recordResult(c.name, c.port, payload);
    },
    onGameInit(c, initData) {
      const key = `${initData.tN.fF}_${initData.tN.mapSeed}_${initData.tN.spawningSeed}`;
      if (activeStreamKey !== key) {
        activeStreamKey = key;
        activeStreamOwner = c.port;
        postSpectatorIngest({ type: 'init', key, ...initData });
      }
    },
    onGamePacket(c, pkt) {
      if (activeStreamOwner === c.port && activeStreamKey) {
        const b64 = Buffer.from(pkt).toString('base64');
        postSpectatorIngest({ type: 'pkt', key: activeStreamKey, b64 });
      }
    }
  });
  clients.push(hc);
}

let lastSyncLaunch = Date.now();
let reloadingForFreshTokens = false;
let currentChosenBot = null;

setInterval(async () => {
  const chosen = currentChosenBot || { port: 9224 };
  const chosenClient = clients.find((c) => c.port === chosen.port) || clients[0];
  if (chosenClient?.callCdp) {
    const shot = await chosenClient.callCdp('Page.captureScreenshot', { format: 'jpeg', quality: 78 });
    if (shot?.data) {
      postSpectatorIngest({ type: 'frame_only', jpeg: shot.data, chosen: currentChosenBot }, (reply) => {
        if (reply?.zoom) {
          const code = reply.zoom === 'out' ? 'NumpadSubtract' : 'NumpadAdd';
          const key = reply.zoom === 'out' ? '-' : '+';
          for (const c of clients) {
            if (!c.isHeadless) {
              c.evalJs(`for(let i=0;i<2;i++) document.dispatchEvent(new KeyboardEvent("keydown", { code: "${code}", key: "${key}", bubbles: true, cancelable: true }));`);
            }
          }
        }
      });
    }
  }
}, 800);

function reloadClientForToken(c) {
  c.freshToken = false;
  c.wasInGame = false;
  c.enteredLobbyAt = 0;
  c.lastReloadAt = Date.now();
  if (c.isHeadless) {
    c.mintToken();
  } else {
    c.send('Page.reload', { ignoreCache: false });
  }
}

setInterval(async () => {
  if (clients.length < 10) return;
  const waitMode = isWaitNplMode();

  const states = await Promise.all(
    clients.map(async (c) => {
      const raw = await c.evalJs(`(() => {
        window.__tsbPlayerName = ${JSON.stringify(c.name)};
        window.__tsbPlayerColor = 4095;
        window.__tsbSquadSlot = ${c.slot};
        const ext = window.__fx?.strategyBotExtension;
        if (ext && ext.status.phase === "failed" && window.dictionary) {
          ext.status.phase = "patched";
          ext.status.error = null;
        }
        if (ext?.bots?.local?.error) {
          ext.bots.local.error = null;
        }
        const panel = document.getElementById("tsb-panel");
        if (panel && !panel.classList.contains("tsb-folded")) {
          panel.classList.add("tsb-folded");
          const btn = panel.querySelector(".tsb-fold");
          if (btn) btn.textContent = "+";
        }
        if (ext?.settings) ext.settings.folded = true;
        const s = ext?.remote?.snapshot?.() || {};
        const info = ext?.remote?.state?.info;
        const d = window.dictionary;
        const g = d && window[d.game];
        const pixels = d && window[d.sbPixels];
        if (!${c.isHeadless ? 'true' : 'false'} && s?.inGame && info?.tick > 15 && pixels && window.__zoomedGamePixels !== pixels) {
          window.__zoomedGamePixels = pixels;
          for (let i = 0; i < 11; i++) {
            document.dispatchEvent(new KeyboardEvent("keydown", { code: "NumpadSubtract", key: "-", bubbles: true, cancelable: true }));
          }
        }
        if (g && g[d.gIsSingleplayer] && g[d.gameState] === 1 && g[d.sbLeave]) {
          g[d.sbLeave](true);
        }
        const teams = d && window[d.sbTeamHolder]?.[d.sbTeams];
        const me = g && g[d.playerId];
        s.ok = true;
        s.spawnPhase = !!info?.spawnPhase;
        s.tick = info?.tick || 0;
        s.terr = info?.territory || 0;
        s.land = info?.land || 0;
        s.bal = info?.balance || 0;
        s.rank = info?.rank || "-";
        s.players = info?.players || "-";
        s.meId = Number.isInteger(me) ? me : -1;
        s.team = teams && Number.isInteger(me) ? teams[me] : "-";
        if (s?.inGame && !s.over && s.alive) {
          const pd = d && window[d.playerData];
          const terr = pd && pd[d.playerTerritories];
          let teamLand = info?.territory || 0;
          if (teams && terr && Number.isInteger(me) && teams[me] > 0) {
            teamLand = 0;
            for (let i = 0; i < 512; i++) {
              if (terr[i] > 0 && teams[i] === teams[me]) teamLand += terr[i];
            }
          }
          if (info?.land > 0 && teamLand >= 0.58 * info.land) {
            document.dispatchEvent(new KeyboardEvent("keydown", { code: "KeyP", key: "p", bubbles: true, cancelable: true }));
          }
        }
        return JSON.stringify(s);
      })()`);
      try { return JSON.parse(raw || '{}'); } catch { return {}; }
    })
  );

  // Send all 10 bots' stats + fallback JPEG screenshot to spectator server
  const allStats = [];
  for (let i = 0; i < clients.length; i++) {
    const c = clients[i];
    const s = states[i];
    if (s?.ok) {
      allStats.push({
        port: c.port,
        slot: c.slot,
        name: c.name,
        meId: s.meId ?? -1,
        inGame: !!s.inGame,
        lobby: s.lobby,
        tick: s.tick || 0,
        time: s.tick ? Math.floor(s.tick * 0.056 / 60) + ':' + String(Math.floor((s.tick * 0.056) % 60)).padStart(2, '0') : '-',
        alive: !!s.alive,
        terr: s.terr || 0,
        land: s.land || 0,
        bal: s.bal || 0,
        rank: s.rank || '-',
        players: s.players || '-',
        team: s.team || '-'
      });
    }
  }
  const chromeInStats = allStats.filter((b) => b.port < 9300);
  const chosen = chromeInStats.slice().sort((a, b) => (b.alive - a.alive) || (b.inGame - a.inGame) || (b.terr - a.terr))[0] || chromeInStats[0];
  currentChosenBot = chosen || null;
  postSpectatorIngest({ type: 'all_stats', stats: allStats, chosen });

  // Only skip state transitions if ALL bots failed to respond
  if (states.every((s) => !s.ok)) return;

  const now = Date.now();
  states.forEach((s, idx) => {
    if (s.inGame) {
      if (!clients[idx].wasInGame) clients[idx].enteredGameAt = now;
      clients[idx].wasInGame = true;
      clients[idx].enteredLobbyAt = 0;
    } else {
      clients[idx].wasInGame = false;
    }
    if (s.lobby?.stopped && s.lobby.stopped.includes('4591')) {
      clients[idx].freshToken = false;
      clients[idx].enteredLobbyAt = 0;
    }
  });

  // Never reload or re-open lobby while ANY bot is in an active game (including spawnPhase or first 30s!)
  const anyAliveInGame = states.some(
    (s, idx) => s.inGame && !s.over && (s.alive || s.spawnPhase || s.tick < 50 || now - clients[idx].enteredGameAt < 30000)
  );
  if (anyAliveInGame) {
    reloadingForFreshTokens = false;
    return;
  }

  // Allow bots to click Ready when >= 8 bots are in Team Room 0 together (or >= 6 when timer is getting low)!
  const inRoom0 = states.filter((s) => s.lobby && s.lobby.inLobby && s.lobby.room === 0);
  const readyCountInRoom0 = inRoom0.length;
  const minStartsIn = inRoom0.length ? Math.min(...inRoom0.map((s) => s.lobby.startsIn || 999)) : 999;
  const allReadyInRoom0 =
    (readyCountInRoom0 >= 8 || (readyCountInRoom0 >= 5 && minStartsIn <= 140)) &&
    Math.max(...inRoom0.map((s) => s.lobby.startsIn || 0)) - Math.min(...inRoom0.map((s) => s.lobby.startsIn || 0)) <= 25;

  await Promise.all(
    clients.map((c) =>
      c.evalJs(`(() => {
        window.__tsbPlayerName = ${JSON.stringify(c.name)};
        window.__tsbPlayerColor = 4095;
        window.__tsbSquadSlot = ${c.slot};
        window.__tsbFollowLeader = ${waitMode || !allReadyInRoom0 ? JSON.stringify('npl') : JSON.stringify('')};
        window.__tsbWaitForLeader = ${waitMode || !allReadyInRoom0 ? 'true' : 'false'};
        const ext = window.__fx?.strategyBotExtension;
        if (ext && ${allReadyInRoom0 ? 'true' : 'false'}) {
          ext.settings.armed = true;
          ext.remote.state.loop = "team";
          const snap = ext.remote.snapshot?.();
          if (snap?.lobby?.inLobby && !snap.lobby.ready && !${waitMode ? 'true' : 'false'}) {
            document.dispatchEvent(new KeyboardEvent("keyup", { code: "Enter", key: "Enter", bubbles: true, cancelable: true }));
          }
        }
      })()`)
    )
  );

  if (readyCountInRoom0 >= 10) return;

  // Reload/mint any bot that lacks a fresh token and is not already in the lobby
  const needReload = clients.filter(
    (c, i) =>
      !c.freshToken &&
      !(states[i]?.lobby?.inLobby) &&
      now - c.lastReloadAt > (c.isHeadless ? 18000 : 75000) &&
      now - c.enteredLobbyAt > 15000
  );
  if (needReload.length > 0 && !reloadingForFreshTokens && now - lastSyncLaunch > 8000) {
    reloadingForFreshTokens = true;
    lastSyncLaunch = now;
    console.log(`[SQUAD-SYNC] Minting fresh Turnstile tokens for ${needReload.map((c) => c.name).join(', ')}...`);
    for (const c of needReload) {
      reloadClientForToken(c);
    }
    setTimeout(() => { reloadingForFreshTokens = false; }, 6500);
  }

  // Enter Team Room 0 for any bot that has a fresh token and is not in game or Room 0
  const readyToEnter = clients.filter(
    (c, i) =>
      !states[i]?.inGame &&
      !(states[i]?.lobby?.inLobby && states[i]?.lobby?.room === 0) &&
      c.freshToken &&
      now - c.enteredLobbyAt > 22000
  );
  if (readyToEnter.length > 0 && !clients.some((c, i) => !c.isHeadless && !c.freshToken && !(states[i]?.lobby?.inLobby))) {
    lastSyncLaunch = now;
    console.log(`[SQUAD-SYNC] Entering Team Room 0 for ${readyToEnter.map((c) => c.name).join(', ')} (waitForLeader=${waitMode})...`);
    for (let i = 0; i < readyToEnter.length; i++) {
      const c = readyToEnter[i];
      c.enteredLobbyAt = now;
      setTimeout(() => {
        c.evalJs(`(() => {
          const d = window.dictionary;
          const g = window[d.game];
          if (g && g[d.gameState] === 1) return "ALREADY_IN_GAME";
          if (g && g[d.sbLeave] && g[d.gameState] === 2) g[d.sbLeave](true);
          const ext = window.__fx.strategyBotExtension;
          ext.settings.armed = true;
          ext.remote.state.loop = "team";
          window.__tsbSquadSyncHold = false;
          window.__fx.strategyBot.openMultiplayer(0);
          setTimeout(() => { window.__tsbSquadSyncHold = true; }, 5000);
          return "SYNC_LAUNCHED";
        })()`);
      }, i * 350);
    }
  }
}, 2500);
