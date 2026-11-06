import fs from 'fs';
import http from 'http';

const pageJsSource = fs.readFileSync('/tmp/tsb-team-ext/page.js', 'utf8');
const getV27TeamSource = () => fs.readFileSync('/tmp/v27-team-live.js', 'utf8');

const BOTS = [
  { port: 9223, name: '[NPL] Mishi', slot: 0, id: 'mTd7B', pw: 'vivELD0lOKgghLr' },
  { port: 9224, name: '[NPL] Matzz', slot: 1, id: 'vgLjn', pw: 'Cl2xSE00tjOjVBq' },
  { port: 9225, name: '[NPL] Kiholma', slot: 2, id: 'NJmJY', pw: 'zmUT69zzi_Rk80I' },
  { port: 9226, name: '[NPL] Leo_99', slot: 3, id: 'byk85', pw: 'iLFHoRHz4rHvEt0' },
  { port: 9227, name: '[NPL] Racoon', slot: 4, id: '5nvnY', pw: 'DzMzg9vRC1Qnj3z' },
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

// Mutex so only 1 browser brings window to front & clicks Turnstile at a time on shared DISPLAY=:100
let focusChain = Promise.resolve();
function withWindowFocus(fn) {
  const next = focusChain.then(fn, fn);
  focusChain = next.catch(() => {});
  return next;
}

const clients = [];

async function attachBot(bot) {
  const { port, name, slot } = bot;
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

  const client = {
    port,
    name,
    slot,
    ws,
    send,
    evalJs,
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
        const id = await ext.strategies.add({ name: "v27team.js", text: async () => ${JSON.stringify(src)} });
        if (ext.strategies.changed) ext.strategies.changed(id || "file:v27team");
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

for (const bot of BOTS) {
  await attachBot(bot);
}

let lastSyncLaunch = Date.now();
let reloadingForFreshTokens = false;

function reloadClientForToken(c) {
  c.freshToken = false;
  c.wasInGame = false;
  c.enteredLobbyAt = 0;
  c.lastReloadAt = Date.now();
  c.send('Page.reload', { ignoreCache: false });
}

setInterval(async () => {
  if (clients.length < 5) return;
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
        const s = ext?.remote?.snapshot?.() || {};
        const info = ext?.remote?.state?.info;
        s.ok = true;
        s.spawnPhase = !!info?.spawnPhase;
        s.tick = info?.tick || 0;
        if (s?.inGame && !s.over && s.alive) {
          const d = window.dictionary;
          const g = d && window[d.game];
          const pd = d && window[d.playerData];
          const terr = pd && pd[d.playerTerritories];
          const teams = d && window[d.sbTeamHolder]?.[d.sbTeams];
          const me = g && g[d.playerId];
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

  // If any evalJs timed out this tick, skip state transitions so we never misjudge an active game!
  if (states.some((s) => !s.ok)) return;

  // Never reload or re-open lobby while ANY bot is in an active game (including spawnPhase or first 30s!)
  const anyAliveInGame = states.some(
    (s, idx) => s.inGame && !s.over && (s.alive || s.spawnPhase || s.tick < 50 || now - clients[idx].enteredGameAt < 30000)
  );
  if (anyAliveInGame) {
    reloadingForFreshTokens = false;
    return;
  }

  // Only allow bots to click Ready when ALL 5 bots are in Team Room 0 together!
  const inRoom0 = states.filter((s) => s.lobby && s.lobby.inLobby && s.lobby.room === 0);
  const all5InRoom0 =
    inRoom0.length >= 5 &&
    Math.max(...inRoom0.map((s) => s.lobby.startsIn || 0)) - Math.min(...inRoom0.map((s) => s.lobby.startsIn || 0)) <= 20;

  await Promise.all(
    clients.map((c) =>
      c.evalJs(`(() => {
        window.__tsbPlayerName = ${JSON.stringify(c.name)};
        window.__tsbPlayerColor = 4095;
        window.__tsbSquadSlot = ${c.slot};
        window.__tsbFollowLeader = ${waitMode || !all5InRoom0 ? JSON.stringify('npl') : JSON.stringify('')};
        window.__tsbWaitForLeader = ${waitMode || !all5InRoom0 ? 'true' : 'false'};
        const ext = window.__fx?.strategyBotExtension;
        if (ext && ${all5InRoom0 ? 'true' : 'false'}) {
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

  if (all5InRoom0) return;

  // Reload any bot that lacks a fresh token and is not already in the lobby (and hasn't just launched into lobby)
  const needReload = clients.filter(
    (c, i) =>
      !c.freshToken &&
      !(states[i]?.lobby?.inLobby) &&
      now - c.lastReloadAt > 90000 &&
      now - c.enteredLobbyAt > 15000
  );
  if (needReload.length > 0 && !reloadingForFreshTokens && now - lastSyncLaunch > 10000) {
    reloadingForFreshTokens = true;
    lastSyncLaunch = now;
    console.log(`[SQUAD-SYNC] Reloading ${needReload.map((c) => c.name).join(', ')} to mint fresh Turnstile tokens...`);
    for (const c of needReload) {
      reloadClientForToken(c);
    }
    setTimeout(() => { reloadingForFreshTokens = false; }, 7500);
    return;
  }

  // Wait until every bot either is already in the lobby OR has a fresh Turnstile token ready
  if (clients.some((c, i) => !c.freshToken && !(states[i]?.lobby?.inLobby))) return;

  // Only call openMultiplayer(0) ONCE per fresh Turnstile token when NOT in an active game!
  const readyToEnter = clients.filter(
    (c, i) =>
      !states[i]?.inGame &&
      !(states[i]?.lobby?.inLobby && states[i]?.lobby?.room === 0) &&
      c.freshToken &&
      now - c.enteredLobbyAt > 25000
  );
  if (readyToEnter.length > 0) {
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
      }, i * 500);
    }
  }
}, 2500);
