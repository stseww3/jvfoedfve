import fs from 'node:fs';
import path from 'node:path';
import http from 'node:http';
import net from 'node:net';
import { fileURLToPath } from 'node:url';
import { createHeadlessBot } from './headless-bot.mjs';
import { TeamSpawnCoordinator } from './spawn-coordinator.mjs';
import { SQUAD_NAME_POOL, SQUAD_NAME_SET } from './name-pool.mjs';

let namePoolOrder = [];
let namePoolCursor = 0;
const activeBotNames = new Set();

function pickNextUniqueSquadName(oldName = '') {
  if (oldName) activeBotNames.delete(oldName);
  for (let tries = 0; tries < SQUAD_NAME_POOL.length * 2; tries++) {
    if (namePoolCursor >= namePoolOrder.length) {
      namePoolOrder = SQUAD_NAME_POOL.slice();
      for (let i = namePoolOrder.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        const tmp = namePoolOrder[i];
        namePoolOrder[i] = namePoolOrder[j];
        namePoolOrder[j] = tmp;
      }
      namePoolCursor = 0;
    }
    const cand = namePoolOrder[namePoolCursor++];
    if (!activeBotNames.has(cand) && cand !== oldName) {
      activeBotNames.add(cand);
      return cand;
    }
  }
  const fallback = SQUAD_NAME_POOL[Math.floor(Math.random() * SQUAD_NAME_POOL.length)];
  activeBotNames.add(fallback);
  return fallback;
}

const __dirname = path.dirname(fileURLToPath(import.meta.url));
function resolveAssetPath(localName, tmpFallback) {
  const localPath = path.join(__dirname, localName);
  if (fs.existsSync(localPath)) return localPath;
  return tmpFallback;
}

function rotateSocksSession(socksPort) {
  return new Promise((resolve) => {
    if (!socksPort) return resolve(false);
    const sock = net.connect(socksPort, '127.0.0.1');
    let stage = 0;
    let buf = Buffer.alloc(0);
    const done = (ok) => {
      try { sock.destroy(); } catch {}
      resolve(ok);
    };
    const timer = setTimeout(() => done(false), 2000);
    sock.on('error', () => { clearTimeout(timer); done(false); });
    sock.on('connect', () => sock.write(Buffer.from([0x05, 0x01, 0x00])));
    sock.on('data', (chunk) => {
      buf = Buffer.concat([buf, chunk]);
      if (stage === 0 && buf.length >= 2) {
        buf = buf.subarray(2);
        stage = 1;
        const hb = Buffer.from('rotate.proxy.local', 'utf8');
        const req = Buffer.alloc(4 + 1 + hb.length + 2);
        req[0] = 0x05; req[1] = 0x01; req[2] = 0x00; req[3] = 0x03;
        req[4] = hb.length;
        hb.copy(req, 5);
        req.writeUInt16BE(80, 5 + hb.length);
        sock.write(req);
      } else if (stage === 1 && buf.length >= 10) {
        clearTimeout(timer);
        done(buf[1] === 0x00);
      }
    });
  });
}

const pageJsSource = fs.readFileSync(resolveAssetPath('page.js', '/tmp/tsb-team-ext/page.js'), 'utf8');
let cachedV27TeamSource = '';
const getV27TeamSource = () => {
  try {
    const s = fs.readFileSync(resolveAssetPath('v27-team-live.js', '/tmp/v27-team-live.js'), 'utf8');
    if (s && s.length > 1000) cachedV27TeamSource = s;
  } catch {}
  return cachedV27TeamSource;
};

const CHROME_BOTS = [
  { port: 9223, name: 'KFC', slot: 0, id: '', pw: '' },
  { port: 9224, name: 'Mexican', slot: 1, id: '', pw: '' },
  { port: 9225, name: 'Sever (rus)', slot: 2, id: '', pw: '' },
  { port: 9226, name: 'KUKU', slot: 3, id: '', pw: '' },
  { port: 9227, name: 'World empire', slot: 4, id: '', pw: '' },
  { port: 9228, name: 'Napoléon', slot: 5, id: '', pw: '' },
];

const HEADLESS_BOTS = [
  { port: 9301, socksPort: 10801, donorChromePort: 9225, name: 'KFC', slot: 0, id: '', pw: '' },
  { port: 9302, socksPort: 10802, donorChromePort: 9225, name: 'Mexican', slot: 1, id: '', pw: '' },
  { port: 9303, socksPort: 10803, donorChromePort: 9225, name: 'Sever (rus)', slot: 2, id: '', pw: '' },
  { port: 9304, socksPort: 10804, donorChromePort: 9225, name: 'KUKU', slot: 3, id: '', pw: '' },
  { port: 9305, socksPort: 10805, donorChromePort: 9225, name: 'World empire', slot: 4, id: '', pw: '' },
  { port: 9306, socksPort: 10806, donorChromePort: 9226, name: 'LLXRScorpio', slot: 5, id: '', pw: '' },
  { port: 9307, socksPort: 10807, donorChromePort: 9226, name: 'Team destroyer', slot: 6, id: '', pw: '' },
  { port: 9308, socksPort: 10808, donorChromePort: 9226, name: 'SPQR', slot: 7, id: '', pw: '' },
  { port: 9309, socksPort: 10809, donorChromePort: 9226, name: 'xX_Shadow_Xx', slot: 8, id: '', pw: '' },
  { port: 9310, socksPort: 10810, donorChromePort: 9226, name: 'Polska Gurom', slot: 9, id: '', pw: '' },
  { port: 9311, socksPort: 10811, donorChromePort: 9227, name: 'Bismarck', slot: 10, id: '', pw: '' },
  { port: 9312, socksPort: 10812, donorChromePort: 9227, name: 'giga_chad', slot: 11, id: '', pw: '' },
  { port: 9313, socksPort: 10813, donorChromePort: 9227, name: 'San Marino', slot: 12, id: '', pw: '' },
  { port: 9314, socksPort: 10814, donorChromePort: 9227, name: 'NoobSlayer', slot: 13, id: '', pw: '' },
  { port: 9315, socksPort: 10815, donorChromePort: 9227, name: 'Vatican City', slot: 14, id: '', pw: '' },
  { port: 9316, socksPort: 10816, donorChromePort: 9225, name: 'Napoléon', slot: 15, id: '', pw: '' },
  { port: 9317, socksPort: 10817, donorChromePort: 9225, name: 'TokyoGhoul', slot: 16, id: '', pw: '' },
  { port: 9318, socksPort: 10818, donorChromePort: 9226, name: 'Ottoman', slot: 17, id: '', pw: '' },
  { port: 9319, socksPort: 10819, donorChromePort: 9226, name: 'bruh', slot: 18, id: '', pw: '' },
  { port: 9320, socksPort: 10820, donorChromePort: 9227, name: '404 Not Found', slot: 19, id: '', pw: '' },
];

const isWaitNplMode = () => fs.existsSync(path.join(__dirname, 'tsb-wait-npl.flag')) || fs.existsSync('/tmp/tsb-wait-npl.flag');
const isHeadlessOnlyMode = () => !(fs.existsSync(path.join(__dirname, 'tsb-enable-chrome-play.flag')) || fs.existsSync('/tmp/tsb-enable-chrome-play.flag'));

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
  window.__tsbFollowLeader = "kazerd183";
  window.__tsbWaitForLeader = true;
  window.__tsbSquadSyncHold = true;
  window.__hlSpawnReq = (payload) => {
    try { if (window.__tsbSpawnReq) window.__tsbSpawnReq(JSON.stringify(payload)); } catch {}
  };
  try {
    sessionStorage.removeItem('territorialStrategyBotRecover');
    const extCfg = {
      spawn: true,
      play: true,
      autoStart: false,
      manual: true,
      armed: true,
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
      const resFile = fs.existsSync(__dirname) ? path.join(__dirname, 'tsb-team-results.jsonl') : '/tmp/tsb-team-results.jsonl';
      fs.appendFileSync(resFile, line + '\n');
      console.log(`[RESULT ${name}] result=${data.result} event=${data.event} place=${data.place} peak=${data.peak} team=${JSON.stringify(data.team || null)}`);
    }
  } catch {}
}

async function attachChromeBot(bot) {
  const { port, name, slot } = bot;
  let pages;
  try {
    pages = await getJson(`http://127.0.0.1:${port}/json`);
  } catch {
    return null;
  }
  const page = Array.isArray(pages) ? pages.find((p) => p.type === 'page' && p.url.includes('territorial.io')) : null;
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
    if (isHeadlessOnlyMode()) {
      await evalJs(`(() => {
        const d = window.dictionary;
        const g = d && window[d.game];
        if (g && g[d.sbLeave] && g[d.gameState] !== 0) g[d.sbLeave](true);
        if (typeof b1 === "object" && b1?.z?.close) b1.z.close(1, 3252);
        const ext = window.__fx?.strategyBotExtension;
        if (ext) {
          ext.settings.armed = false;
          if (ext.remote?.state) ext.remote.state.loop = null;
        }
        window.__tsbSquadSyncHold = true;
      })()`);
      client.freshToken = true;
      console.log(`[${name}] Donor Chrome on :${port} ready for Turnstile minting (lobby/game disabled)!`);
      return;
    }
    const src = getV27TeamSource();
    await evalJs(
      `(async () => {
        window.__tsbPlayerName = ${JSON.stringify(name)};
        window.__tsbPlayerColor = 4095;
        window.__tsbSquadSlot = ${slot};
        const ext = window.__fx.strategyBotExtension;
        const sid = await ext.strategies.add({ name: "v27team.js", text: async () => ${JSON.stringify(src)} });
        const targetSid = sid || "file:v27team";
        ext.settings.strategy = targetSid;
        ext.settings.armed = true;
        ext.remote.state.loop = "team";
        if (ext.strategies.changed) ext.strategies.changed(targetSid);
        return "OK";
      })()`,
      true
    );
    client.freshToken = true;
    console.log(`[${name}] Fresh Turnstile token ready & v30-team (slot=${slot}) imported!`);
  }

  ws.onopen = async () => {
    send('Page.enable');
    send('Runtime.enable');
    send('Runtime.addBinding', { name: '__tsbReportResult' });
    send('Runtime.addBinding', { name: '__tsbSpawnReq' });
    const bootstrap = makeBootstrapScript(bot);
    send('Page.addScriptToEvaluateOnNewDocument', { source: bootstrap });
    const alreadyPatched = await evalJs(`(() => {
      if (!window.dictionary || !window.__fx?.strategyBotExtension) return "NO";
      const ext = window.__fx.strategyBotExtension;
      if (ext.status.phase === "failed") {
        ext.status.phase = "patched";
        ext.status.error = null;
      }
      if (!window.__hlSpawnReq) {
        window.__hlSpawnReq = (payload) => {
          try { if (window.__tsbSpawnReq) window.__tsbSpawnReq(JSON.stringify(payload)); } catch {}
        };
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
      localStorage.setItem("d105", ${JSON.stringify(bot.id)});
      localStorage.setItem("d106", ${JSON.stringify(bot.pw)});
      localStorage.setItem("v105", "0");
      localStorage.setItem("v106", "0");
      localStorage.setItem("d122", ${JSON.stringify(name)});
      localStorage.setItem("v122", "0");
      localStorage.setItem("d121", "4095");
      localStorage.setItem("v121", "0");
      if (typeof bm === "object" && bm?.qo?.qp) {
        bm.qo.qp(105, ${JSON.stringify(bot.id)});
        bm.qo.qp(106, ${JSON.stringify(bot.pw)});
        bm.qo.qp(122, ${JSON.stringify(name)});
      }
      window.__tsbPlayerName = ${JSON.stringify(name)};
      window.__tsbPlayerColor = 4095;
      window.__tsbSquadSlot = ${slot};
      return "YES";
    })()`);
    if (alreadyPatched === 'YES' && !isHeadlessOnlyMode()) {
      await importStrategy();
      console.log(`[${name}] Hot-attached without Page.reload (existing Turnstile session preserved)!`);
      return;
    }
    if (alreadyPatched === 'YES' && isHeadlessOnlyMode()) {
      await evalJs(`(() => {
        const d = window.dictionary;
        const g = d && window[d.game];
        if (g && g[d.sbLeave] && g[d.gameState] !== 0) g[d.sbLeave](true);
        if (typeof b1 === "object" && b1?.z?.close) b1.z.close(1, 3252);
        const ext = window.__fx?.strategyBotExtension;
        if (ext) {
          ext.settings.armed = false;
          if (ext.remote?.state) ext.remote.state.loop = null;
        }
        window.__tsbSquadSyncHold = true;
      })()`);
      client.freshToken = true;
      console.log(`[${name}] Donor Chrome on :${port} silenced (left lobby so Headless workers own the room)!`);
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
    } else if (msg.method === 'Runtime.bindingCalled' && msg.params.name === '__tsbSpawnReq') {
      try {
        handleBackendSpawnRequest(client, JSON.parse(msg.params.payload));
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

let activeStreamOwner = null;
let activeStreamKey = null;

const firefoxDonors = new Map();
const firefoxDonorConnecting = new Map();

function ensureFirefoxProfile(profDir, socksPort = 0) {
  fs.mkdirSync(profDir, { recursive: true });
  const proxyPrefs = socksPort > 0 ? `
user_pref("network.proxy.type", 1);
user_pref("network.proxy.socks", "127.0.0.1");
user_pref("network.proxy.socks_port", ${socksPort});
user_pref("network.proxy.socks_version", 5);
user_pref("network.proxy.socks_remote_dns", true);
` : '';
  const userJs = `
user_pref("remote.active-protocols", 3);
user_pref("remote.events.async.wheel.enabled", true);
user_pref("browser.shell.checkDefaultBrowser", false);
user_pref("datareporting.policy.dataSubmissionEnabled", false);
user_pref("toolkit.telemetry.reportingpolicy.firstRun", false);
user_pref("browser.startup.homepage_override.mstone", "ignore");
user_pref("browser.aboutwelcome.enabled", false);
user_pref("trailhead.firstrun.didSeeAboutWelcome", true);
user_pref("focusmanager.testmode", true);
${proxyPrefs}
`;
  fs.writeFileSync(path.join(profDir, 'user.js'), userJs, 'utf8');
}

async function ensureFirefoxDonor(port = 9225) {
  const existing = firefoxDonors.get(port);
  if (existing && existing.ws && existing.ws.readyState === 1 && existing.ctx) {
    return existing;
  }
  if (firefoxDonorConnecting.has(port)) {
    return firefoxDonorConnecting.get(port);
  }
  const connectPromise = (async () => {
    const { spawn } = await import('node:child_process');
    const localFf = path.join(__dirname, 'firefox_bin', 'firefox.exe');
    const c116Ff = path.resolve(__dirname, '../c116/firefox_bin/firefox.exe');
    const ffExe = fs.existsSync(localFf) ? localFf : c116Ff;
    const profDir = path.join(__dirname, `firefox_donor_${port}`);
    const portToSocks = { 9225: 10801, 9226: 10806, 9227: 10811 };

    const tryConnectBidi = () => new Promise((resolve) => {
      const ws = new WebSocket(`ws://127.0.0.1:${port}/session`);
      const t = setTimeout(() => { try { ws.close(); } catch {} resolve(null); }, 3000);
      ws.addEventListener('open', () => { clearTimeout(t); resolve(ws); });
      ws.addEventListener('error', () => { clearTimeout(t); resolve(null); });
    });

    let ws = await tryConnectBidi();
    if (!ws && fs.existsSync(ffExe)) {
      ensureFirefoxProfile(profDir, portToSocks[port] || 0);
      console.log(`[FIREFOX-DONOR] Launching Mozilla Firefox on port ${port} (socks=${portToSocks[port] || 'direct'})...`);
      const child = spawn(ffExe, ['-no-remote', '-profile', profDir, '--remote-debugging-port', String(port), 'https://territorial.io/'], {
        detached: true,
        stdio: 'ignore'
      });
      child.unref();
      for (let retry = 0; retry < 15; retry++) {
        await new Promise((r) => setTimeout(r, 1000));
        ws = await tryConnectBidi();
        if (ws) break;
      }
    }
    if (!ws) throw new Error(`Firefox BiDi not reachable on port ${port}`);

    let seq = 0;
    const pending = new Map();
    ws.addEventListener('message', (ev) => {
      try {
        const msg = JSON.parse(ev.data);
        if (msg.id && pending.has(msg.id)) {
          const fn = pending.get(msg.id);
          pending.delete(msg.id);
          fn(msg);
        }
      } catch {}
    });
    ws.addEventListener('close', () => {
      const cur = firefoxDonors.get(port);
      if (cur && cur.ws === ws) firefoxDonors.delete(port);
    });

    const callBidi = (method, params = {}) => new Promise((resolve) => {
      if (ws.readyState !== 1) return resolve(null);
      const id = ++seq;
      const timer = setTimeout(() => {
        pending.delete(id);
        resolve(null);
      }, 8000);
      pending.set(id, (msg) => {
        clearTimeout(timer);
        resolve(msg);
      });
      ws.send(JSON.stringify({ id, method, params }));
    });

    await callBidi('session.end', {});
    const sess = await callBidi('session.new', { capabilities: {} });
    if (!sess?.result?.sessionId) {
      console.log(`[FIREFOX-DONOR] BiDi session on :${port} busy or re-initializing...`);
    }

    await callBidi('script.addPreloadScript', {
      functionDeclaration: `() => {
        try {
          const fakeGet = { get webdriver() { return false; } };
          const getter = Object.getOwnPropertyDescriptor(fakeGet, 'webdriver').get;
          Object.defineProperty(Navigator.prototype, 'webdriver', {
            get: getter,
            enumerable: true,
            configurable: true
          });
        } catch {}
        try {
          if (location.hostname.includes('cloudflare.com')) {
            const noop = function() {};
            console.log = noop;
            console.debug = noop;
            console.info = noop;
            console.warn = noop;
            console.dir = noop;
            console.table = noop;
          }
        } catch {}
      }`
    });

    const tree = await callBidi('browsingContext.getTree', {});
    const topCtx = tree?.result?.contexts?.find((c) => c.url?.includes('territorial.io')) || tree?.result?.contexts?.[0];
    const ctx = topCtx?.context;
    if (!ctx) {
      try { ws.close(); } catch {}
      throw new Error(`No browsingContext found in Firefox Donor on :${port}`);
    }

    await callBidi('browsingContext.activate', { context: ctx });

    const wdCheck = await callBidi('script.evaluate', {
      expression: 'String(navigator.webdriver) + ":" + String(typeof window.turnstile)',
      target: { context: ctx },
      awaitPromise: false
    });
    const wdVal = wdCheck?.result?.result?.value || '';
    if (!wdVal.startsWith('false:object')) {
      console.log(`[FIREFOX-DONOR] Reloading territorial.io tab on :${port} so preloadScript (webdriver=false) takes effect (was ${wdVal})...`);
      await callBidi('browsingContext.reload', { context: ctx, wait: 'complete' });
      await new Promise((r) => setTimeout(r, 2500));
    }

    console.log(`[FIREFOX-DONOR] Connected to Mozilla Firefox BiDi on :${port} (ctx=${ctx}, webdriver=false)!`);
    const donorObj = { ws, callBidi, ctx, port, _mintChain: Promise.resolve() };
    firefoxDonors.set(port, donorObj);
    return donorObj;
  })().finally(() => {
    firefoxDonorConnecting.delete(port);
  });
  firefoxDonorConnecting.set(port, connectPromise);
  return connectPromise;
}

for (const ffPort of [9225, 9226, 9227]) {
  await ensureFirefoxDonor(ffPort).catch((e) => console.error(`[FIREFOX-DONOR :${ffPort}] Init warn:`, e.message));
}

async function mintViaDonorChrome(donorPort = 9225) {
  const targetPort = (donorPort === 9228 || !donorPort) ? 9225 : donorPort;
  let donor;
  try {
    donor = await ensureFirefoxDonor(targetPort);
  } catch {
    donor = await ensureFirefoxDonor(9225);
  }
  const runMint = async () => {
    const { callBidi, ctx } = donor;
    await callBidi('script.evaluate', {
      expression: `(() => {
        try { if (typeof bX === "object" && bX?.turnstile?.close) bX.turnstile.close(); } catch {}
        const d = window.dictionary;
        const g = d && window[d.game];
        if (g && g[d.sbLeave] && g[d.gameState] !== 0) g[d.sbLeave](true);
        if (typeof b1 === "object" && b1?.z?.close) b1.z.close(1, 3252);
        for (const el of Array.from(document.querySelectorAll("div"))) {
          if (el.id !== "mint-ts" && el.style?.position === "fixed" && (el.style?.zIndex === "100" || el.getBoundingClientRect().width === 300)) {
            el.remove();
          }
        }
        window.__mintedToken = null;
        const old = document.getElementById("mint-ts");
        if (old) old.remove();
        const div = document.createElement("div");
        div.id = "mint-ts";
        div.style.position = "fixed";
        div.style.left = "0";
        div.style.top = "0";
        div.style.zIndex = "2147483647";
        document.body.appendChild(div);
        const wid = window.turnstile.render(div, {
          sitekey: "0x4AAAAAAEI8HZoG8nJMzxt1",
          action: "enter_lobby",
          appearance: "interaction-only",
          callback: (tok) => {
            window.__mintedToken = tok;
            try { window.turnstile.remove(wid); div.remove(); } catch {}
          }
        });
        return "RENDERED:" + wid;
      })()`,
      target: { context: ctx },
      awaitPromise: false,
      userActivation: true
    });

    for (let i = 0; i < 14; i++) {
      await new Promise((r) => setTimeout(r, 650));
      const check = await callBidi('script.evaluate', {
        expression: 'window.__mintedToken || ""',
        target: { context: ctx },
        awaitPromise: false
      });
      const tok0 = check?.result?.result?.value || '';
      if (typeof tok0 === 'string' && tok0.length > 100) {
        return tok0;
      }
      await callBidi('input.performActions', {
        context: ctx,
        actions: [
          {
            type: 'pointer',
            id: 'mouse1',
            parameters: { pointerType: 'mouse' },
            actions: [
              { type: 'pointerMove', x: 180, y: 180, duration: 40 },
              { type: 'pointerMove', x: 28, y: 32, duration: 70 },
              { type: 'pointerDown', button: 0 },
              { type: 'pause', duration: 60 },
              { type: 'pointerUp', button: 0 }
            ]
          }
        ]
      });
    }
    throw new Error('Firefox BiDi mint timeout');
  };

  const next = (donor._mintChain || Promise.resolve()).then(runMint, runMint);
  donor._mintChain = next.catch(() => {});
  return next;
}

// Centralized Backend Spawn Coordinator (TeamSpawnCoordinator):
// Receives map terrain (once per match) + live human positions (Boss npl, enemies, allies) during the 6s spawnPhase,
// solves the global joint Geodesic Voronoi + Boss Flank Guard formation + Bitmask DP minimum-displacement assignment,
// and pushes each bot's dedicated (x, y, role) back via worker.postMessage({ type: 'set_spawn', pos }) & CDP!
const spawnCoordinator = new TeamSpawnCoordinator({ port: 8198 });
spawnCoordinator.startHttpServer();
const botSpawnMeta = new Map();
let lastCoordLogKey = '';
let lastCoordLogAt = 0;

function handleBackendSpawnRequest(client, req) {
  const { matchKey, W, H, land, me, myTeam = 0, curX = -1, curY = -1, humans = [], mapType, packedLandB64 } = req;
  if (!W || !H) return;
  const key = matchKey || `${W}x${H}_${land || 0}`;
  if (spawnCoordinator.matchKey !== key) {
    botSpawnMeta.clear();
  }
  if (mapType || packedLandB64) {
    spawnCoordinator.setMap({ matchKey: key, W, H, land, mapType, packedLandB64 });
  }
  botSpawnMeta.set(client.port, { meId: me, curX, curY });

  if (!spawnCoordinator.landMask) return;

  const now = Date.now();
  if (!spawnCoordinator.lastPlan || spawnCoordinator.lastPlan.matchKey !== key || now - spawnCoordinator.lastSolvedAt >= 320) {
    const headlessOnly = isHeadlessOnlyMode();
    let activeClients = headlessOnly
      ? clients.filter((c) => c.isHeadless)
      : wantTenForCurrentLobby
        ? clients
        : clients.filter((c) => !c.isHeadless);
    if (!activeClients.includes(client)) {
      activeClients = clients.filter((c) => c.isHeadless === client.isHeadless);
    }

    const squadBots = activeClients.map((c) => {
      const meta = botSpawnMeta.get(c.port) || {};
      return {
        slot: c.slot,
        port: c.port,
        name: c.name,
        meId: meta.meId ?? -1,
        curX: meta.curX ?? -1,
        curY: meta.curY ?? -1,
      };
    });

    const plan = spawnCoordinator.solve({ squadBots, humans, myTeam });
    if (plan.ok) {
      const summary = [];
      for (const c of activeClients) {
        const pos = plan.assignments[c.slot];
        if (!pos) continue;
        if (c.isHeadless) {
          c.worker?.postMessage({ type: 'set_spawn', pos });
        } else {
          c.evalJs(`(() => {
            window.__tsbAssignedSpawn = ${JSON.stringify(pos)};
            const bot = window.__fx?.strategyBot;
            const v = bot?.view;
            if (v && v.spawnPhase) {
              const cur = bot.spawn;
              if (!cur || Math.abs(${pos.x} - cur.x) + Math.abs(${pos.y} - cur.y) > 4) {
                if (v.chooseSpawn(${pos.x}, ${pos.y})) bot.spawn = { x: ${pos.x}, y: ${pos.y} };
              }
            }
          })()`);
        }
        summary.push(`${c.name.replace('[NPL] ', '')}(${pos.role === 'FLANK_GUARD' ? 'GUARD' : 'BANK'})->(${pos.x},${pos.y})`);
      }
      const sig = `${key}:${summary.join('|')}`;
      if (sig !== lastCoordLogKey || now - lastCoordLogAt > 1500) {
        lastCoordLogKey = sig;
        lastCoordLogAt = now;
        const bossInfo = plan.boss ? `(${plan.boss.x},${plan.boss.y})` : 'none';
        console.log(
          `[BACKEND-SPAWN-COORD] Solved ${plan.squadCount} bots in ${plan.elapsedMs}ms (map=${W}x${H}, minSep=${plan.minPairwiseDist}px, boss=${bossInfo}): ${summary.join(' | ')}`
        );
      }
    }
  } else {
    const pos = spawnCoordinator.lastPlan.assignments[client.slot];
    if (pos) {
      if (client.isHeadless) {
        client.worker?.postMessage({ type: 'set_spawn', pos });
      }
    }
  }
}

for (const bot of HEADLESS_BOTS) {
  bot.name = pickNextUniqueSquadName(bot.name);
  const hc = createHeadlessBot(bot, {
    getStrategySource: getV27TeamSource,
    mintTurnstileToken: mintViaDonorChrome,
    onSpawnRequest: handleBackendSpawnRequest,
    onRotateProxy(c) {
      rotateSocksSession(c.socksPort).then(() => {
        c.evalJs(`(() => {
          if (typeof b1 === "object" && b1?.z?.close) {
            b1.z.close(0, 3253);
            const reconn = b1.z.aJc || b1.z.aIR;
            if (typeof reconn === "function") reconn.call(b1.z, 0, 18, 0);
          }
        })()`);
      });
    },
    onResult(c, payload) {
      recordResult(c.name, c.port, payload);
      if (c.isHeadless) {
        c.name = pickNextUniqueSquadName(c.name);
        c.evalJs(`(() => {
          window.__tsbPlayerName = ${JSON.stringify(c.name)};
          localStorage.setItem("d122", ${JSON.stringify(c.name)});
          localStorage.setItem("v122", "0");
          const setSetting = bm?.qq?.qr || bm?.qo?.qp;
          if (typeof bm === "object" && typeof setSetting === "function") {
            setSetting.call(bm.qq || bm.qo, 122, ${JSON.stringify(c.name)});
          }
        })()`);
      }
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
let wantTenForCurrentLobby = false;

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
  if (clients.length < HEADLESS_BOTS.length) return;
  const waitMode = isWaitNplMode();
  const headlessOnly = isHeadlessOnlyMode();

  const states = await Promise.all(
    clients.map(async (c) => {
      if (!c.isHeadless && headlessOnly) {
        return { ok: true, donorOnly: true, inGame: false, lobby: { inLobby: false }, room0Players: 0 };
      }
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
        if (ext?.settings) {
          ext.settings.folded = true;
          ext.settings.armed = true;
          if (ext.strategies?.has?.("file:v27team") && ext.settings.strategy !== "file:v27team") {
            ext.settings.strategy = "file:v27team";
            ext.strategies.changed?.("file:v27team");
          }
        }
        if (ext?.remote?.state) {
          ext.remote.state.loop = "team";
        }
        const panel = document.getElementById("tsb-panel");
        if (panel && !panel.classList.contains("tsb-folded")) {
          panel.classList.add("tsb-folded");
          const btn = panel.querySelector(".tsb-fold");
          if (btn) btn.textContent = "+";
        }
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
        let room0Players = 0;
        let room0NopeCount = 0;
        let bossReadyInRoom0 = false;
        const lob = ext?.remote?.lobby;
        const mgr = lob?.mgr || (d && d.lobbyManager && window[d.lobbyManager]) || (typeof bq === "object" ? bq : null);
        if (mgr) {
          let list = null;
          let readyCount = 0;
          if (mgr.wZ && Array.isArray(mgr.wZ.w1)) {
            list = mgr.wZ.w1;
            readyCount = typeof mgr.wZ.wa === "number" ? (mgr.wZ.wa | 0) : 0;
          } else {
            let vh = null, vi = null;
            for (const v of Object.values(mgr)) {
              if (v && typeof v === "object") {
                if (d?.lobbyPlayers && Array.isArray(v[d.lobbyPlayers])) {
                  vh = v[d.lobbyPlayers];
                  vi = v[d.lobbyReadyCounts];
                  break;
                }
                const vals = Object.values(v);
                const arr4 = vals.find((x) => Array.isArray(x) && x.length === 4 && Array.isArray(x[0]));
                const cnt4 = vals.find((x) => Array.isArray(x) && x.length === 4 && typeof x[0] === "number");
                if (arr4) {
                  vh = arr4;
                  vi = cnt4;
                  break;
                }
              }
            }
            if (vh && Array.isArray(vh[0])) {
              list = vh[0];
              readyCount = vi && typeof vi[0] === "number" ? (vi[0] | 0) : 0;
            }
          }
          if (Array.isArray(list)) {
            room0Players = list.length;
            for (let idx = 0; idx < list.length; idx++) {
              const p = list[idx];
              const disp = String((p && p.username) || "").trim();
              if (disp.toLowerCase().includes("[nope]")) room0NopeCount++;
              const gt = String(p?.aGT || "").trim();
              const gm = String(p?.aGM || "").trim();
              const raw = String((gt && !gt.includes("Redacted")) ? gt : (gm && !gm.includes("Redacted")) ? gm : (gt || gm || p?.aFN || p?.username || p?.name || "")).trim();
              const low = raw.toLowerCase();
              const stripped = raw.replace(/\[[^\]]*\]/g, "").trim().toLowerCase();
              if (
                low.includes("mishi") || low.includes("matzz") || low.includes("kiholma") ||
                low.includes("leo_99") || low.includes("racoon") || low.includes("zexos") ||
                low.includes("talon") || low.includes("vortex") || low.includes("kronos") || low.includes("nexus") ||
                low.includes("777") || low.includes("sayo") || low.includes("kaito") ||
                low.includes("riku") || low.includes("_alex") || low.includes("tomo") ||
                low.includes("zero_2") || low.includes("sora") ||
                low.includes("lucas94") || low.includes("dave_w") || low.includes("mark07") ||
                low.includes("kevin_k") || low.includes("ethan21") || low.includes("ryan_m") ||
                low.includes("noah88") || low.includes("leo_tx") || low.includes("jake_09") || low.includes("owen_h") ||
                low.includes("liam_c") || low.includes("mason22") || low.includes("logan_b") || low.includes("caleb14") ||
                low.includes("isaac_v") || low.includes("nolan81") || low.includes("eli_fox") || low.includes("wyatt04") ||
                low.includes("carter7") || low.includes("luke_r") ||
                low === "kfc" || low === "mexican" || low === "sever (rus)" || low === "kuku" ||
                low === "world empire" || low === "llxrscorpio" || low === "team destroyer" ||
                low === "spqr" || low === "xx_shadow_xx" || low === "polska gurom" || low === "bismarck" ||
                low === "giga_chad" || low === "san marino" || low === "noobslayer" || low === "vatican city" ||
                low === "napoléon" || low === "tokyoghoul" || low === "ottoman" || low === "bruh" || low === "404 not found"
              ) continue;
              if (stripped === "kazerd183" || stripped.includes("kazerd") || low.includes("kazerd183") || stripped === "npl" || low === "[npl]npl" || low.includes("auouf")) {
                if (idx < readyCount) {
                  if (typeof p?.uX === "number" && p.uX > 0) window.__lastBossUx = p.uX;
                  bossReadyInRoom0 = true;
                }
              }
            }
          }
        }
        const myLobbyObj = typeof bq === "object" ? (bq?.aFv || bq?.aF0) : null;
        const myLobbyUsername = myLobbyObj ? myLobbyObj.username : null;
        if (myLobbyUsername && (myLobbyUsername.startsWith("Player ") || myLobbyUsername.includes("Redacted")) && typeof b1 === "object" && b1?.eg?.eh && b1?.z?.ef?.(0)) {
          if (!window.__lastNameVerifyAsk || Date.now() - window.__lastNameVerifyAsk > 3000) {
            window.__lastNameVerifyAsk = Date.now();
            try { b1.eg.eh(5); } catch {}
          }
        }
        const myAccId = typeof bm === "object" && bm?.buffer?.data?.[105] ? bm.buffer.data[105].value : null;
        const teams = d && window[d.sbTeamHolder]?.[d.sbTeams];
        const me = g && g[d.playerId];
        if ((!g || g[d.gameState] === 0) && typeof bq === "object" && bq?.f6 === 1 && typeof b1 === "object" && b1?.z?.ef?.(1)) {
          s.lobby = s.lobby || {};
          s.lobby.inLobby = true;
          s.lobby.room = 0;
          if (bq.sH && typeof bq.sH.wF === "number") {
            const firstRoom = bq.sH.sH?.[0];
            s.lobby.ready = !!(firstRoom && bq.sH.wF === firstRoom.id && firstRoom.id > 0);
            s.lobby.startsIn = firstRoom ? (firstRoom.wK ?? 99) : 99;
          } else {
            s.lobby.room = bq?.z?.tM?.[0] ?? 0;
            s.lobby.ready = !!(bq?.z?.tM?.[3]);
          }
        }
        s.ok = true;
        s.myLobbyUsername = myLobbyUsername;
        s.myAccId = myAccId;
        s.room0NopeCount = typeof room0NopeCount === "number" ? room0NopeCount : 0;
        s.room0Players = room0Players;
        s.bossReadyInRoom0 = bossReadyInRoom0;
        s.spawnPhase = !!info?.spawnPhase;
        s.tick = info?.tick || 0;
        if (s.inGame) {
          if (s.tick > 0 && !s.spawnPhase && window.__lastObsTick === s.tick) {
            window.__stalledCount = (window.__stalledCount || 0) + 1;
          } else {
            window.__lastObsTick = s.tick;
            window.__stalledCount = 0;
          }
          if ((window.__stalledCount || 0) >= 20 && g && g[d.sbLeave]) {
            window.__stalledCount = 0;
            g[d.sbLeave](true);
            s.inGame = false;
          }
        } else {
          window.__stalledCount = 0;
        }
        s.terr = info?.territory || 0;
        s.land = info?.land || 0;
        s.bal = info?.balance || 0;
        s.rank = info?.rank || "-";
        s.players = info?.players || "-";
        s.sent = info?.sent || 0;
        s.accepted = info?.accepted || 0;
        s.armed = !!ext?.settings?.armed;
        s.strategy = ext?.settings?.strategy || "-";
        s.err = ext?.status?.error || ext?.bots?.local?.error || info?.error || null;
        s.meId = Number.isInteger(me) ? me : -1;
        s.team = teams && Number.isInteger(me) ? teams[me] : "-";
        // Auto-self-heal in game if unarmed or stuck at <= 16 territory after tick 30!
        if (s?.inGame && !s.over && s.alive && ext) {
          if (!ext.settings.armed || ext.settings.strategy !== "file:v27team") {
            ext.settings.armed = true;
            ext.settings.strategy = "file:v27team";
            if (ext.strategies?.changed) ext.strategies.changed("file:v27team");
          }
          if (s.tick >= 115 && s.terr <= 16 && s.sent === 0 && s.bal >= 256 && g && d?.sbCommands && d?.sbSendAttack) {
            try {
              if (ext.strategies?.changed) ext.strategies.changed("file:v27team");
              window[d.sbCommands]?.[d.sbSendAttack]?.(256, 512);
              s.healedExpand = true;
            } catch {}
          }
        }
        if (s?.inGame) {
          const pd = d && window[d.playerData];
          const rawNames = pd && pd[d.rawPlayerNames];
          const pStates = pd && pd[d.playerStates];
          const pAlive = pd && pd[d.sbAlive];
          const pTerr = pd && pd[d.playerTerritories];
          const H = (g && g[d.gHumans]) || 512;
          let bossIdx = -1;
          if (rawNames) {
            for (let p = 0; p < H; p++) {
              if (typeof window === "object" && window.__lastBossUx > 0 && window.aE?.data?.a7z?.[p] === window.__lastBossUx) {
                bossIdx = p;
                break;
              }
              const raw = String(rawNames[p] ?? "").trim();
              if (!raw) continue;
              const low = raw.toLowerCase();
              if (
                low.includes("mishi") || low.includes("matzz") || low.includes("kiholma") ||
                low.includes("leo_99") || low.includes("racoon") || low.includes("zexos") ||
                low.includes("talon") || low.includes("vortex") || low.includes("kronos") || low.includes("nexus") ||
                low.includes("777") || low.includes("sayo") || low.includes("kaito") ||
                low.includes("riku") || low.includes("_alex") || low.includes("tomo") ||
                low.includes("zero_2") || low.includes("sora") ||
                low.includes("lucas94") || low.includes("dave_w") || low.includes("mark07") ||
                low.includes("kevin_k") || low.includes("ethan21") || low.includes("ryan_m") ||
                low.includes("noah88") || low.includes("leo_tx") || low.includes("jake_09") || low.includes("owen_h") ||
                low.includes("liam_c") || low.includes("mason22") || low.includes("logan_b") || low.includes("caleb14") ||
                low.includes("isaac_v") || low.includes("nolan81") || low.includes("eli_fox") || low.includes("wyatt04") ||
                low.includes("carter7") || low.includes("luke_r") ||
                low === "kfc" || low === "mexican" || low === "sever (rus)" || low === "kuku" ||
                low === "world empire" || low === "llxrscorpio" || low === "team destroyer" ||
                low === "spqr" || low === "xx_shadow_xx" || low === "polska gurom" || low === "bismarck" ||
                low === "giga_chad" || low === "san marino" || low === "noobslayer" || low === "vatican city" ||
                low === "napoléon" || low === "tokyoghoul" || low === "ottoman" || low === "bruh" || low === "404 not found"
              ) continue;
              const stripped = raw.replace(/\[[^\]]*\]/g, "").trim().toLowerCase();
              if (stripped === "kazerd183" || stripped.includes("kazerd") || low.includes("kazerd183") || stripped === "npl" || low === "[npl]npl" || low.includes("auouf")) {
                bossIdx = p;
                break;
              }
            }
          }
          s.bossId = bossIdx;
          s.bossActiveInGame = bossIdx >= 0;
        }
        return JSON.stringify(s);
      })()`);
      try {
        const parsed = JSON.parse(raw || '{}');
        if (parsed && parsed.ok) {
          c.lastGoodState = parsed;
          c.lastGoodStateAt = Date.now();
          return parsed;
        }
      } catch {}
      if (c.lastGoodState && Date.now() - (c.lastGoodStateAt || 0) < 15000) {
        return c.lastGoodState;
      }
      if (c.wasInGame && Date.now() - (c.enteredGameAt || 0) < 35000) {
        return { ok: true, inGame: true, spawnPhase: true, tick: 0, alive: true, terr: 12 };
      }
      return {};
    })
  );

  // Determine Room 0 player count and whether 10 bots (room >= 35 players) or 5 bots (< 35 players) should enter
  const inRoom0 = states.filter((s) => s.lobby && s.lobby.inLobby && s.lobby.room === 0);
  const chromeInRoom0 = states.filter((s, idx) => !clients[idx].isHeadless && s.lobby && s.lobby.inLobby && s.lobby.room === 0).length;
  const headlessInRoom0 = states.filter((s, idx) => clients[idx].isHeadless && s.lobby && s.lobby.inLobby && s.lobby.room === 0).length;
  const maxRoom0Players = inRoom0.reduce((m, s) => Math.max(m, s.room0Players || 0), 0);
  if (inRoom0.length === 0) {
    wantTenForCurrentLobby = false;
  } else if (!headlessOnly && maxRoom0Players >= 35) {
    if (!wantTenForCurrentLobby) {
      console.log(`[SQUAD-SYNC] Room 0 reached ${maxRoom0Players} players (>= 35)! Waking up 5 reserve Headless bots for 10-bot entry!`);
    }
    wantTenForCurrentLobby = true;
  }

  // Send active bots' stats + fallback JPEG screenshot to spectator server
  const allStats = [];
  for (let i = 0; i < clients.length; i++) {
    const c = clients[i];
    const s = states[i];
    if (!c.isHeadless && headlessOnly) continue;
    if (s?.ok) {
      const isStandby = !headlessOnly && c.isHeadless && !s.inGame && !(s.lobby?.inLobby) && !wantTenForCurrentLobby;
      allStats.push({
        port: c.port,
        slot: c.slot,
        name: c.name,
        myLobbyUsername: s.myLobbyUsername || null,
        myAccId: s.myAccId || null,
        room0NopeCount: s.room0NopeCount || 0,
        meId: s.meId ?? -1,
        inGame: !!s.inGame,
        standby: isStandby,
        lobby: s.lobby,
        room0Players: s.room0Players || 0,
        tick: s.tick || 0,
        time: s.tick ? Math.floor(s.tick * 0.056 / 60) + ':' + String(Math.floor((s.tick * 0.056) % 60)).padStart(2, '0') : '-',
        alive: !!s.alive,
        terr: s.terr || 0,
        land: s.land || 0,
        bal: s.bal || 0,
        rank: s.rank || '-',
        players: s.players || '-',
        team: s.team || '-',
        sent: s.sent || 0,
        accepted: s.accepted || 0,
        err: s.err || null,
        healedExpand: !!s.healedExpand
      });
    }
  }
  const primaryInStats = headlessOnly ? allStats : allStats.filter((b) => b.port < 9300);
  const chosen = primaryInStats.slice().sort((a, b) => (b.alive - a.alive) || (b.inGame - a.inGame) || (b.terr - a.terr))[0] || allStats[0];
  currentChosenBot = chosen || null;
  postSpectatorIngest({ type: 'all_stats', stats: allStats, chosen });

  // Only skip state transitions if ALL bots failed to respond
  if (states.every((s) => !s.ok)) return;

  const now = Date.now();
  states.forEach((s, idx) => {
    if (s.inGame || s.lobby?.inLobby) {
      clients[idx].lobbyFailCount = 0;
    }
    if (s.inGame) {
      if (!clients[idx].wasInGame) clients[idx].enteredGameAt = now;
      clients[idx].wasInGame = true;
      clients[idx].enteredLobbyAt = 0;
    } else {
      if (clients[idx].wasInGame) {
        // Turnstile verification in territorial.io (eU: ew=60min) is valid for 1 full hour per (account, lobbyServer)!
        clients[idx].lastReloadAt = 0;
      }
      clients[idx].wasInGame = false;
    }
    if (s.lobby?.stopped) {
      clients[idx].evalJs(`(() => {
        const ext = window.__fx?.strategyBotExtension;
        if (ext?.remote?.state) {
          ext.remote.state.loop = "team";
          if (ext.remote.lobby) ext.remote.lobby.stopped = null;
        }
      })()`);
      if (s.lobby.stopped.includes('4591') || s.lobby.stopped.includes('4577') || s.lobby.stopped.includes('4215') || s.lobby.stopped.includes('1006')) {
        clients[idx].freshToken = false;
        clients[idx].enteredLobbyAt = 0;
      }
    }
    // Self-check each bot's own display username in Room 0 (#6694):
    // Detect account-level or IP-level "Redacted XX" and auto-rotate account & re-enter!
    const c = clients[idx];
    if ((c.isHeadless || !headlessOnly) && s.lobby?.inLobby && s.lobby?.room === 0 && s.myLobbyUsername) {
      if (s.myLobbyUsername.includes('Redacted')) {
        if (!c.redactedDetectedAt) c.redactedDetectedAt = now;
        if (now - c.redactedDetectedAt >= 20000) {
          console.log(`[SELF-CHECK REDACTED] ${c.name} still "${s.myLobbyUsername}" (acc=${s.myAccId}) after 20s in Room 0 -> rotating sticky proxy IP & fresh account & re-entering!`);
          c.redactedDetectedAt = 0;
          c.lastVerifiedLobbyName = null;
          c.freshToken = false;
          c.enteredLobbyAt = 0;
          rotateSocksSession(c.socksPort).then(() => {
            c.evalJs(`(() => {
              localStorage.setItem("d105", "");
              localStorage.setItem("d106", "");
              localStorage.setItem("v105", "0");
              localStorage.setItem("v106", "0");
              const setSetting = bm?.qq?.qr || bm?.qo?.qp;
              if (typeof bm === "object" && typeof setSetting === "function") {
                setSetting.call(bm.qq || bm.qo, 105, "");
                setSetting.call(bm.qq || bm.qo, 106, "");
              }
              if (typeof b1 === "object" && b1?.z?.close) {
                b1.z.close(1, 3252);
                b1.z.close(0, 3253);
                const reconn = b1.z.aJc || b1.z.aIR;
                if (typeof reconn === "function") reconn.call(b1.z, 0, 18, 0);
              }
            })()`);
          });
        }
      } else if (s.myLobbyUsername === c.name || s.myLobbyUsername.startsWith('[Nope]')) {
        c.redactedDetectedAt = 0;
        if (c.lastVerifiedLobbyName !== s.myLobbyUsername) {
          c.lastVerifiedLobbyName = s.myLobbyUsername;
          console.log(`[SELF-CHECK OK] ${c.name} verified in Room 0 as "${s.myLobbyUsername}" (acc=${s.myAccId})`);
        }
      }
    } else if (!s.lobby?.inLobby) {
      c.redactedDetectedAt = 0;
      c.lastVerifiedLobbyName = null;
    }
  });

  // In Boss-Guard waitMode: never kick bots out of an active match once they entered!
  if (false && waitMode) {
    for (let i = 0; i < clients.length; i++) {
      const s = states[i];
      if (s?.inGame && !s.bossActiveInGame) {
        console.log(`[BOSS-SYNC] ${clients[i].name} is in a match without active Boss [Nope]kazerd183 (bossId=${s.bossId ?? -1}) -> leaving immediately to rejoin Lobby!`);
        s.inGame = false;
        clients[i].wasInGame = false;
        clients[i].lastReloadAt = 0;
        clients[i].evalJs(`(() => {
          window.__tsbSquadSyncHold = true;
          const d = window.dictionary;
          const g = d && window[d.game];
          if (g && g[d.sbLeave] && g[d.gameState] !== 0) g[d.sbLeave](true);
        })()`);
      }
    }
  }

  // Hot-import updated strategy file immediately even while bots are in-game!
  const srcHashNow = getV27TeamSource().length;
  for (const c of clients) {
    if (!c.isHeadless && headlessOnly) continue;
    if (c.lastStrategyLen !== srcHashNow) {
      c.lastStrategyLen = srcHashNow;
      const newSrc = getV27TeamSource();
      c.evalJs(`(async () => {
        const ext = window.__fx?.strategyBotExtension;
        if (ext) {
          const sid = await ext.strategies.add({ name: "v27team.js", text: async () => ${JSON.stringify(newSrc)} });
          const targetSid = sid || "file:v27team";
          ext.settings.strategy = targetSid;
          if (ext.strategies.changed) ext.strategies.changed(targetSid);
        }
      })()`, true);
      console.log(`[HOT-IMPORT] Injected updated v27team.js (${srcHashNow} bytes) into ${c.name} live!`);
    }
  }

  // Never reload or re-open lobby while ANY bot has meaningful territory (> 80 px) or is in opening (< 30s)
  let anyMeaningfulAlive = false;
  for (let idx = 0; idx < states.length; idx++) {
    const s = states[idx];
    if (!s?.inGame || s.over) continue;
    const prevTick = clients[idx].lastPollTick ?? -1;
    clients[idx].lastPollTick = s.tick;
    if (s.tick > 0 && s.tick === prevTick) {
      clients[idx].stalledPolls = (clients[idx].stalledPolls || 0) + 1;
    } else {
      clients[idx].stalledPolls = 0;
    }
    if ((clients[idx].stalledPolls || 0) >= 20) {
      clients[idx].evalJs(`(() => { const d = window.dictionary, g = d && window[d.game]; if (g && g[d.sbLeave] && g[d.gameState] !== 0) g[d.sbLeave](true); })()`);
      continue;
    }
    const minMeaningfulTerr = s.tick >= 3600 ? 1500 : 80;
    if (s.spawnPhase || s.tick < 60 || now - clients[idx].enteredGameAt < 30000 || (s.alive && (s.terr || 0) >= minMeaningfulTerr)) {
      anyMeaningfulAlive = true;
    }
  }
  if (anyMeaningfulAlive) {
    reloadingForFreshTokens = false;
    wantTenForCurrentLobby = false;
    // Opening Watchdog:
    // 1) Detect & auto-heal Case 1 ("delayed pass" stuck at tick===0 for >6.5s)
    // 2) Log one-time [OPENING-CHECK] report at tick >= 180 verifying all active bots expanded!
    const maxTickNow = Math.max(...states.map((s) => s?.tick || 0));
    states.forEach((s, idx) => {
      const c = clients[idx];
      if (s?.healedExpand) {
        console.log(`[OPENING-WATCHDOG] ${c.name} had terr=${s.terr} sent=${s.sent} at tick=${s.tick} -> auto-fired opening expansion pulse!`);
      }
    });
    if (maxTickNow >= 180 && maxTickNow <= 450 && now - (globalThis.__lastOpeningCheckAt || 0) > 60000) {
      globalThis.__lastOpeningCheckAt = now;
      const inGameStates = allStats.filter((b) => b.inGame);
      const summary = inGameStates
        .map((b) => `${b.name.replace('[NPL] ', '')}:tick=${b.tick},terr=${b.terr},sent=${b.sent}${b.terr < 100 ? '(WARN:LOW_TERR!)' : '(OK)'}`)
        .join(' | ');
      console.log(`[OPENING-CHECK ${inGameStates.length} bots @ tick ${maxTickNow}] ${summary}`);
    }
    return;
  }

  // If no bot has >= 80 territory anymore (match is effectively over for our squad), leave lingering dead/tiny games to main menu!
  for (let i = 0; i < clients.length; i++) {
    if (states[i]?.inGame) {
      clients[i].wasInGame = false;
      clients[i].lastReloadAt = 0;
      clients[i].evalJs(`(() => {
        window.__tsbSquadSyncHold = true;
        const d = window.dictionary;
        const g = d && window[d.game];
        if (g && g[d.sbLeave] && g[d.gameState] !== 0) g[d.sbLeave](true);
      })()`);
    }
  }

  // Rule #5641 + #5645:
  // - If Room 0 has < 35 players (!wantTenForCurrentLobby): 5 Chrome bots enter, ready ONLY when all 5/5 Chrome bots are in Room 0 (or >= 4 in final 8s)
  // - If Room 0 has >= 35 players (wantTenForCurrentLobby): all 10 bots enter, ready ONLY when all 10/10 bots are in Room 0 (or >= 8 in final 8s)
  const readyCountInRoom0 = inRoom0.length;
  const minStartsIn = inRoom0.length ? Math.min(...inRoom0.map((s) => s.lobby.startsIn || 999)) : 999;
  const timerSpreadOk =
    inRoom0.length > 0 &&
    Math.max(...inRoom0.map((s) => s.lobby.startsIn || 0)) - Math.min(...inRoom0.map((s) => s.lobby.startsIn || 0)) <= 25;

  const allReadyInRoom0 =
    timerSpreadOk &&
    (headlessOnly
      ? (headlessInRoom0 >= HEADLESS_BOTS.length - 2 || (headlessInRoom0 >= HEADLESS_BOTS.length - 5 && minStartsIn <= 15))
      : wantTenForCurrentLobby
        ? (readyCountInRoom0 === 10 || (readyCountInRoom0 >= 8 && minStartsIn <= 8))
        : (chromeInRoom0 === 5 || (chromeInRoom0 >= 4 && minStartsIn <= 8)));

  const bossReadyNow = inRoom0.some((s) => !!s.bossReadyInRoom0);

  const srcHash = getV27TeamSource().length;
  await Promise.all(
    clients.map((c) => {
      if (!c.isHeadless && headlessOnly) return Promise.resolve(null);
      const isStandby = !headlessOnly && c.isHeadless && !wantTenForCurrentLobby;
      const allowReady = !isStandby && (waitMode ? bossReadyNow : allReadyInRoom0);
      const needHotImport = c.lastStrategyLen !== srcHash;
      if (needHotImport) c.lastStrategyLen = srcHash;
      return c.evalJs(`(async () => {
        window.__tsbPlayerName = ${JSON.stringify(c.name)};
        window.__tsbPlayerColor = 4095;
        window.__tsbSquadSlot = ${c.slot};
        window.__tsbFollowLeader = ${allowReady ? JSON.stringify('') : JSON.stringify('kazerd183')};
        window.__tsbWaitForLeader = ${allowReady ? 'false' : 'true'};
        const ext = window.__fx?.strategyBotExtension;
        if (ext) {
          if (${needHotImport ? 'true' : 'false'}) {
            const sid = await ext.strategies.add({ name: "v27team.js", text: async () => ${JSON.stringify(getV27TeamSource())} });
            const targetSid = sid || "file:v27team";
            ext.settings.strategy = targetSid;
            if (ext.strategies.changed) ext.strategies.changed(targetSid);
          }
          ext.settings.armed = true;
          ext.remote.state.loop = "team";
          const isInLobbyNow = (typeof bq === "object" && bq?.f6 === 1 && typeof b1 === "object" && b1?.z?.ef?.(1));
          const isReadyNow = isInLobbyNow && (bq?.sH ? !!(bq.sH.sH?.[0] && bq.sH.wF === bq.sH.sH[0].id && bq.sH.sH[0].id > 0) : !!(bq?.z?.tM?.[3]));
          if (isInLobbyNow && !isReadyNow && ${allowReady ? 'true' : 'false'}) {
            if (!window.__readyJitterScheduled) {
              window.__readyJitterScheduled = true;
              const delayMs = 120 + ((${c.slot} * 110) % 900) + Math.floor(Math.random() * 250);
              setTimeout(() => {
                window.__readyJitterScheduled = false;
                if (typeof bq === "object" && bq?.f6 === 1 && !window.__tsbWaitForLeader) {
                  if (bq?.sH?.sH?.[0] && typeof bq.sH.select === "function") {
                    const targetRoom = (bq.sH.sH[0] && bq.sH.sH[0].vz < 7) ? bq.sH.sH[0] : (bq.sH.sH.find(r => r && r.vz < 7) || bq.sH.sH[0]);
                    if (targetRoom && bq.sH.wF !== targetRoom.id) {
                      bq.sH.select(targetRoom.id);
                    }
                  } else {
                    document.dispatchEvent(new KeyboardEvent("keyup", { code: "Enter", key: "Enter", bubbles: true, cancelable: true }));
                  }
                }
              }, delayMs);
            }
          } else if (isInLobbyNow && isReadyNow && !${allowReady ? 'true' : 'false'} && !${waitMode ? 'true' : 'false'}) {
            window.__readyJitterScheduled = false;
            if (bq?.sH && typeof bq.sH.select === "function" && bq.sH.wF) {
              bq.sH.select(0);
            } else {
              document.dispatchEvent(new KeyboardEvent("keyup", { code: "Escape", key: "Escape", bubbles: true, cancelable: true }));
            }
          }
        }
      })()`, true);
    })
  );

  // Keep active bots' Turnstile tokens fresh
  const needReload = clients.filter(
    (c, i) =>
      (c.isHeadless || !headlessOnly) &&
      !c.freshToken &&
      !(states[i]?.lobby?.inLobby) &&
      now - c.lastReloadAt > (c.isHeadless ? 15000 : 75000) &&
      now - c.enteredLobbyAt > 12000
  );
  if (needReload.length > 0 && !reloadingForFreshTokens && now - lastSyncLaunch > 6000) {
    reloadingForFreshTokens = true;
    lastSyncLaunch = now;
    console.log(`[SQUAD-SYNC] Minting fresh Turnstile tokens for ${needReload.map((c) => c.name).join(', ')}...`);
    for (const c of needReload) {
      reloadClientForToken(c);
    }
    setTimeout(() => { reloadingForFreshTokens = false; }, 5500);
  }

  // Enter Team Room 0:
  const readyToEnter = clients.filter(
    (c, i) =>
      (headlessOnly ? c.isHeadless : (!c.isHeadless || wantTenForCurrentLobby)) &&
      !states[i]?.inGame &&
      !(states[i]?.lobby?.inLobby && states[i]?.lobby?.room === 0) &&
      c.freshToken &&
      now - c.enteredLobbyAt > 15000
  );
  if (readyToEnter.length > 0 && (headlessOnly || !clients.some((c, i) => !c.isHeadless && !c.freshToken && !(states[i]?.lobby?.inLobby)))) {
    lastSyncLaunch = now;
    console.log(
      `[SQUAD-SYNC] Entering Team Room 0 for ${readyToEnter.map((c) => c.name).join(', ')} (mode=${headlessOnly ? '5-HEADLESS-GUARD' : wantTenForCurrentLobby ? '10-BOT >=35p' : '5-BOT <35p'}, waitBoss=${waitMode}, room0Players=${maxRoom0Players})...`
    );
    for (let i = 0; i < readyToEnter.length; i++) {
      const c = readyToEnter[i];
      c.lobbyFailCount = (c.lobbyFailCount || 0) + 1;
      if (c.lobbyFailCount >= 3) {
        c.freshToken = false;
        c.lobbyFailCount = 0;
        continue;
      }
      c.enteredLobbyAt = now;
      const enterJitterMs = i * 160 + Math.floor(Math.random() * 160);
      setTimeout(() => {
        c.evalJs(`(() => {
          const d = window.dictionary;
          const g = window[d.game];
          if (g && g[d.gameState] === 1) return "ALREADY_IN_GAME";
          if (g && g[d.sbLeave] && g[d.gameState] === 2) g[d.sbLeave](true);
          if (typeof bq === "object" && bq?.f6 === 1 && typeof b1 === "object" && b1?.z?.ef?.(1)) {
            return "ALREADY_IN_LOBBY";
          }
          if (typeof b1 === "object" && b1?.z?.close) {
            b1.z.close(1, 3252);
          }
          window.__tsbPlayerName = ${JSON.stringify(c.name)};
          localStorage.setItem("d122", ${JSON.stringify(c.name)});
          localStorage.setItem("v122", "0");
          const setSetting = bm?.qq?.qr || bm?.qo?.qp;
          if (typeof bm === "object" && typeof setSetting === "function") {
            setSetting.call(bm.qq || bm.qo, 122, ${JSON.stringify(c.name)});
          }
          const ext = window.__fx.strategyBotExtension;
          ext.settings.armed = true;
          ext.remote.state.loop = "team";
          window.__tsbSquadSyncHold = false;
          if (typeof b1 === "object" && b1?.z) b1.z.f7 = 1;
          window.__fx.strategyBot.openMultiplayer(0);
          setTimeout(() => { window.__tsbSquadSyncHold = true; }, 5000);
          return "SYNC_LAUNCHED";
        })()`);
      }, enterJitterMs);
    }
  }
}, 2500);
