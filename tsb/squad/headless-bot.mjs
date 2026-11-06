import fs from 'node:fs';
import vm from 'node:vm';
import net from 'node:net';
import tls from 'node:tls';
import https from 'node:https';
import { Worker, isMainThread, parentPort, workerData } from 'node:worker_threads';
import { createRequire } from 'node:module';

const require = createRequire('/tmp/node_modules/ws/package.json');
const WS = require('ws');

// ============================================================================
// MAIN THREAD API: spawns a dedicated Worker thread for each Headless Bot
// so BFS / Voronoi calculations NEVER block the main thread or packet stream!
// ============================================================================
export function createHeadlessBot(bot, { onResult, onGameInit, onGamePacket, getStrategySource, mintTurnstileToken }) {
  const { port, socksPort, donorChromePort, name, slot } = bot;
  const worker = new Worker(new URL(import.meta.url), {
    workerData: { bot, strategySource: getStrategySource() }
  });

  let seq = 0;
  const pending = new Map();

  const client = {
    port,
    socksPort,
    donorChromePort,
    name,
    slot,
    isHeadless: true,
    freshToken: false,
    wasInGame: false,
    lastReloadAt: Date.now(),
    enteredLobbyAt: 0,
    enteredGameAt: 0,
    minting: false,
    worker,
    send() {},
    evalJs(expression, awaitPromise = false) {
      return new Promise((resolve) => {
        const id = ++seq;
        const timer = setTimeout(() => {
          pending.delete(id);
          resolve(null);
        }, 3000);
        pending.set(id, (val) => {
          clearTimeout(timer);
          resolve(val);
        });
        worker.postMessage({ type: 'eval', id, expression, awaitPromise });
      });
    },
    mintToken() {
      if (this.minting) return;
      this.minting = true;
      console.log(`[${name}] (Worker) Requesting Turnstile token from Chrome :${donorChromePort}...`);
      mintTurnstileToken(donorChromePort)
        .then((tok) => {
          this.minting = false;
          this.freshToken = true;
          worker.postMessage({
            type: 'token',
            token: tok,
            strategySource: getStrategySource()
          });
        })
        .catch((err) => {
          this.minting = false;
          console.error(`[${name}] (Worker) Turnstile mint error on :${donorChromePort}:`, err.message);
        });
    }
  };

  worker.on('message', (msg) => {
    if (msg.type === 'eval_res') {
      const fn = pending.get(msg.id);
      if (fn) {
        pending.delete(msg.id);
        fn(msg.value);
      }
    } else if (msg.type === 'need_token') {
      client.freshToken = false;
      client.enteredLobbyAt = 0;
    } else if (msg.type === 'token_imported') {
      client.freshToken = true;
      console.log(`[${name}] (Worker) Fresh Turnstile token ready & v27team (slot=${slot}) imported!`);
    } else if (msg.type === 'log') {
      console.log(`[${name}]`, msg.text);
      if (msg.text.includes('error 4591') || msg.text.includes('error 4215') || msg.text.includes('error 4577')) {
        client.freshToken = false;
        client.enteredLobbyAt = 0;
      }
    } else if (msg.type === 'result') {
      if (onResult) onResult(client, msg.payload);
    } else if (msg.type === 'game_init') {
      if (onGameInit) onGameInit(client, msg.initData);
    } else if (msg.type === 'game_pkt') {
      if (onGamePacket) onGamePacket(client, msg.pkt);
    }
  });

  worker.on('error', (err) => {
    console.error(`[${name}] Worker error:`, err.message);
  });

  return client;
}

// ============================================================================
// WORKER THREAD IMPLEMENTATION
// ============================================================================
if (!isMainThread && workerData?.bot) {
  const { bot } = workerData;
  const { socksPort, name, slot, id, pw } = bot;

  const gameJsSource = fs.readFileSync('/tmp/live_game_js.js', 'utf8')
    .replace('if(bi.ds){bi.ds=false;a0J()}', 'if(bi.ds){bi.ds=false}')
    .replace('this.aeB=function(){bi.ds=true;nF();this.eI=0}', 'this.aeB=function(){this.eI=0}')
    .replace('bV.ym.dk();', '');
  const pageJsSource = fs.readFileSync('/tmp/tsb-team-ext/page.js', 'utf8');
  const dictSource = fs.readFileSync('/tmp/live_dictionary.json', 'utf8');

  function makeSocksAgent(sp) {
    const agent = new https.Agent({ keepAlive: false });
    agent.createConnection = (opts, cb) => {
      const host = opts.host || opts.hostname;
      const port = Number(opts.port) || 443;
      const sock = net.connect(sp, '127.0.0.1');
      let stage = 0;
      let buf = Buffer.alloc(0);
      sock.on('error', (err) => cb(err));
      sock.on('connect', () => sock.write(Buffer.from([0x05, 0x01, 0x00])));
      sock.on('data', (chunk) => {
        buf = Buffer.concat([buf, chunk]);
        if (stage === 0 && buf.length >= 2) {
          buf = buf.subarray(2);
          stage = 1;
          const hb = Buffer.from(host, 'utf8');
          const req = Buffer.alloc(4 + 1 + hb.length + 2);
          req[0] = 0x05; req[1] = 0x01; req[2] = 0x00; req[3] = 0x03;
          req[4] = hb.length;
          hb.copy(req, 5);
          req.writeUInt16BE(port, 5 + hb.length);
          sock.write(req);
        }
        if (stage === 1 && buf.length >= 10) {
          if (buf[1] !== 0x00) {
            sock.destroy();
            return cb(new Error('SOCKS5 connect failed: ' + buf[1]));
          }
          sock.removeAllListeners('data');
          sock.removeAllListeners('error');
          const tlsSock = tls.connect({
            socket: sock,
            servername: opts.servername || host,
            rejectUnauthorized: false,
          });
          cb(null, tlsSock);
        }
      });
    };
    return agent;
  }

  function makeProxiedWebSocketClass(sp) {
    const agent = makeSocksAgent(sp);
    return class ProxiedWebSocket {
      static CONNECTING = 0; static OPEN = 1; static CLOSING = 2; static CLOSED = 3;
      constructor(url, protocols) {
        this.url = url;
        this.CONNECTING = 0; this.OPEN = 1; this.CLOSING = 2; this.CLOSED = 3;
        this.binaryType = 'blob';
        const isProxied = typeof url === 'string' && !url.includes('game.territorial.io');
        this._ws = new WS(url, protocols, {
          agent: isProxied ? agent : undefined,
          headers: {
            'Origin': 'https://territorial.io',
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36'
          }
        });
        this._ws.on('open', () => { if (typeof this.onopen === 'function') this.onopen({ target: this }); });
        this._ws.on('message', (data, isBinary) => {
          if (typeof this.onmessage === 'function') {
            if (this.binaryType === 'arraybuffer' || isBinary) {
              const b = Buffer.from(data);
              this.onmessage({ data: b.buffer.slice(b.byteOffset, b.byteOffset + b.byteLength), target: this });
            } else {
              this.onmessage({ data: data.toString(), target: this });
            }
          }
        });
        this._ws.on('close', (code, reason) => {
          if (typeof this.onclose === 'function') this.onclose({ code, reason: reason?.toString() || '', target: this });
        });
        this._ws.on('error', (err) => { if (typeof this.onerror === 'function') this.onerror(err); });
      }
      get readyState() { return this._ws.readyState; }
      send(data) { if (this._ws.readyState === 1) this._ws.send(data); }
      close(code) { try { this._ws.close(code); } catch {} }
    };
  }

  function findAll(root, pred, out = []) {
    for (const c of root.children || []) {
      if (pred(c)) out.push(c);
      findAll(c, pred, out);
    }
    return out;
  }

  function matchSel(el, sel) {
    if (!el || !el.tagName) return false;
    if (sel === '.captcha-actions button') return el.tagName === 'BUTTON';
    if (sel.startsWith('.')) return String(el.className || '').split(/\s+/).includes(sel.slice(1));
    return el.tagName === sel.toUpperCase();
  }

  const makeStyle = () => new Proxy({ setProperty() {} }, {
    get(t, k) { return t[k] ?? ''; },
    set(t, k, v) { t[k] = String(v); return true; }
  });

  const makeContext2d = (canvas) => ({
    canvas,
    fillStyle: '', strokeStyle: '', font: '', textAlign: '', textBaseline: '', globalAlpha: 1, lineWidth: 1, imageSmoothingEnabled: true,
    fillRect() {}, clearRect() {}, strokeRect() {}, beginPath() {}, closePath() {}, moveTo() {}, lineTo() {}, arc() {},
    fill() {}, stroke() {}, clip() {}, save() {}, restore() {}, scale() {}, rotate() {}, translate() {}, transform() {},
    setTransform() {}, drawImage() {}, fillText() {}, strokeText() {},
    measureText(s) { return { width: String(s || '').length * 8 }; },
    createImageData(w, h) {
      const width = Math.max(1, w | 0), height = Math.max(1, h | 0);
      return { width, height, data: new Uint8ClampedArray(width * height * 4) };
    },
    getImageData(x, y, w, h) {
      const width = Math.max(1, w | 0), height = Math.max(1, h | 0);
      if (width === 24 && height === 24) {
        const data = new Uint8ClampedArray(24 * 24 * 4);
        for (let i = 0; i < 35; i++) data[i * 4] = 255;
        data[35 * 4] = 13;
        return { width, height, data };
      }
      if (!canvas.__imgData || canvas.__imgData.width !== width || canvas.__imgData.height !== height) {
        canvas.__imgData = { width, height, data: new Uint8ClampedArray(width * height * 4) };
      }
      return canvas.__imgData;
    },
    putImageData(img) {
      canvas.__imgData = { width: img.width, height: img.height, data: new Uint8ClampedArray(img.data) };
    },
    createLinearGradient() { return { addColorStop() {} }; },
    createRadialGradient() { return { addColorStop() {} }; },
  });

  const makeElement = (tag) => {
    let _w = 300, _h = 150;
    return {
      nodeName: String(tag || 'DIV').toUpperCase(),
      tagName: String(tag || 'DIV').toUpperCase(),
      className: '',
      style: makeStyle(),
      children: [],
      childNodes: [],
      classList: { add() {}, remove() {}, contains() { return false; }, toggle() {} },
      attributes: {},
      get width() { return _w; },
      set width(v) { _w = v | 0; this.__imgData = null; },
      get height() { return _h; },
      set height(v) { _h = v | 0; this.__imgData = null; },
      offsetWidth: 1280, offsetHeight: 900, clientWidth: 1280, clientHeight: 900,
      value: '', checked: false, textContent: '', innerHTML: '',
      isConnected: true,
      sheet: { cssRules: [{ style: makeStyle() }, { style: makeStyle() }], insertRule() { this.cssRules.push({ style: makeStyle() }); return 0; }, deleteRule() {} },
      appendChild(c) {
        this.children.push(c); this.childNodes.push(c);
        this.firstChild = this.children[0] || null;
        this.lastChild = this.children[this.children.length - 1] || null;
        if (c && typeof c === 'object') c.parentNode = this;
        if (c && c.nodeName === 'SCRIPT' && c.src && c.src.includes('turnstile')) {
          setTimeout(() => { if (typeof c.onload === 'function') c.onload(); }, 10);
        } else if (c && c.nodeName === 'SCRIPT' && c.textContent && typeof sandbox === 'object') {
          try { vm.runInContext(c.textContent, sandbox); } catch {}
        }
        return c;
      },
      replaceChildren(...cs) { this.children = [...cs]; this.childNodes = [...cs]; },
      insertBefore(c) { return this.appendChild(c); },
      replaceChild(n) { return this.appendChild(n); },
      replaceWith() {},
      contains() { return true; },
      append(...cs) { for (const c of cs) this.appendChild(c); },
      removeChild(c) { return c; },
      remove() {},
      setAttribute(k, v) { this.attributes[k] = String(v); },
      getAttribute(k) { return this.attributes[k] ?? null; },
      hasAttribute(k) { return Object.prototype.hasOwnProperty.call(this.attributes, k); },
      addEventListener(ev, fn) { (this._l = this._l || {})[ev] = (this._l[ev] || []).concat(fn); },
      removeEventListener() {},
      dispatchEvent(ev) { for (const fn of this._l?.[ev.type] || []) fn(ev); return true; },
      click() { this.dispatchEvent({ type: 'click', target: this, preventDefault() {} }); },
      focus() {}, blur() {}, select() {},
      querySelector(sel) { return findAll(this, (e) => matchSel(e, sel))[0] || null; },
      querySelectorAll(sel) { return findAll(this, (e) => matchSel(e, sel)); },
      getBoundingClientRect() { return { left: 0, top: 0, width: 128, height: 40 }; },
      getContext() { return this.__ctx || (this.__ctx = makeContext2d(this)); },
    };
  };

  const extCfg = {
    spawn: true, play: true, autoStart: false, manual: true, armed: false, stay: true,
    allow: '', cmdUrl: '', resultUrl: 'http://127.0.0.1/team-result',
    key: 'aKURzbiCpouWOcpOSOffKLXqTXPaVsLG', pollMs: 3000, folded: true, port: 8765, strategy: 'file:v27team'
  };
  const storageMap = new Map([
    ['d105', id], ['v105', '0'],
    ['d106', pw], ['v106', '0'],
    ['d140', '1'], ['v140', '0'],
    ['d121', '4095'], ['v121', '0'],
    ['d122', name], ['v122', '0'],
    ['d158', '0'], ['v158', '0'],
    ['territorialStrategyBotExtension', JSON.stringify(extCfg)],
  ]);

  const docIds = new Map([['canvasA', makeElement('canvas')]]);
  const docListeners = {};
  const document = {
    readyState: 'complete', visibilityState: 'visible', hidden: false, cookie: '',
    head: makeElement('head'), body: makeElement('body'), documentElement: makeElement('html'),
    createElement: makeElement,
    createDocumentFragment: () => makeElement('fragment'),
    createTextNode: (t) => ({ nodeName: '#text', textContent: String(t), style: makeStyle() }),
    getElementById: (eid) => docIds.get(eid) || (docIds.set(eid, makeElement('div')), docIds.get(eid)),
    querySelector(sel) { return this.body.querySelector(sel); },
    querySelectorAll(sel) { return this.body.querySelectorAll(sel); },
    addEventListener(ev, fn) { (docListeners[ev] = docListeners[ev] || []).push(fn); },
    removeEventListener() {},
    dispatchEvent(ev) { for (const fn of docListeners[ev.type] || []) fn(ev); return true; }
  };

  const rafs = [];
  setInterval(() => {
    const batch = rafs.splice(0, rafs.length);
    const now = performance.now();
    for (const fn of batch) {
      try { fn(now); } catch {}
    }
  }, 45);

  let turnstileCallback = null;

  const customConsole = {
    log(...args) {
      const text = args.join(' ');
      if (text.includes('sendTokenToLobby') || text.includes('Connection to Server') || text.includes('socket close')) {
        parentPort.postMessage({ type: 'log', text });
      }
    },
    warn() {},
    error(...args) {
      parentPort.postMessage({ type: 'log', text: 'ERROR: ' + args.join(' ') });
    }
  };

  const sandbox = {
    console: customConsole,
    queueMicrotask,
    setTimeout, clearTimeout, setInterval, clearInterval, performance, Date, Math, JSON,
    Array, Object, String, Number, Boolean, RegExp, Map, Set, WeakMap, WeakSet, Promise, Symbol,
    Error, TypeError, RangeError, SyntaxError, Uint8Array, Uint8ClampedArray, Uint16Array, Uint32Array,
    Int8Array, Int16Array, Int32Array, Float32Array, Float64Array, ArrayBuffer, DataView,
    TextEncoder, TextDecoder, URL, URLSearchParams,
    WebSocket: makeProxiedWebSocketClass(socksPort),
    crypto: globalThis.crypto, atob: globalThis.atob, btoa: globalThis.btoa, fetch: globalThis.fetch,
    structuredClone: globalThis.structuredClone,
    parseInt, parseFloat, isNaN, isFinite, encodeURIComponent, decodeURIComponent, Intl,
    Image: class {
      constructor() {
        const el = makeElement('img');
        el.width = 64; el.height = 64;
        Object.defineProperty(el, 'src', {
          get() { return this._src || ''; },
          set(v) { this._src = v; setTimeout(() => el.onload?.({ target: el }), 1); }
        });
        return el;
      }
    },
    MutationObserver: class { observe() {} disconnect() {} },
    Event: class { constructor(t, o) { this.type = t; Object.assign(this, o); } },
    CustomEvent: class { constructor(t, o) { this.type = t; this.detail = o?.detail; } },
    KeyboardEvent: class { constructor(t, o) { this.type = t; this.key = o?.key || ''; this.code = o?.code || ''; Object.assign(this, o); } },
    document,
    localStorage: {
      getItem: (k) => storageMap.get(k) ?? null,
      setItem: (k, v) => storageMap.set(k, String(v)),
      removeItem: (k) => storageMap.delete(k)
    },
    sessionStorage: { getItem: () => null, setItem() {}, removeItem() {} },
    navigator: { userAgent: 'Mozilla/5.0', language: 'en-US', locks: null, clipboard: { writeText: async () => {} } },
    location: {
      href: 'https://territorial.io/', hostname: 'territorial.io', origin: 'https://territorial.io', protocol: 'https:', search: '',
      reload() { parentPort.postMessage({ type: 'need_token' }); }
    },
    history: { replaceState() {}, pushState() {} },
    screen: { width: 1280, height: 1024 }, innerWidth: 1280, innerHeight: 900, devicePixelRatio: 1,
    requestAnimationFrame: (fn) => (rafs.push(fn), rafs.length),
    cancelAnimationFrame() {}, alert() {}, confirm: () => true, open() {},
    addEventListener: (ev, fn) => document.addEventListener(ev, fn),
    removeEventListener() {},
    dispatchEvent: (ev) => document.dispatchEvent(ev),
    __tsbPlayerName: name,
    __tsbPlayerColor: 4095,
    __tsbSquadSlot: slot,
    __tsbFollowLeader: 'npl',
    __tsbWaitForLeader: true,
    __tsbSquadSyncHold: true,
    __tsbReportResult(payload) {
      parentPort.postMessage({ type: 'result', payload });
    },
    turnstile: {
      render(el, opts) {
        turnstileCallback = opts.callback;
        parentPort.postMessage({ type: 'need_token' });
        return 'wid_1';
      },
      remove() {}
    },
    dictionary: JSON.parse(dictSource)
  };
  sandbox.window = sandbox;
  sandbox.self = sandbox;
  sandbox.globalThis = sandbox;
  sandbox.top = sandbox;
  sandbox.parent = sandbox;

  document.addEventListener('tsb-remote', (e) => {
    try {
      const c = JSON.parse(e.detail);
      if (c.kind === 'post' && sandbox.__tsbReportResult) {
        sandbox.__tsbReportResult(c.body);
      }
    } catch {}
  });

  vm.createContext(sandbox);
  vm.runInContext(pageJsSource, sandbox, { filename: 'page.js' });
  if (sandbox.__fx?.strategyBotExtension?.status) {
    sandbox.__fx.strategyBotExtension.status.phase = 'patched';
  }
  vm.runInContext(gameJsSource, sandbox, { filename: 'live_game_js.js' });
  if (typeof sandbox.onload === 'function') {
    sandbox.onload();
  }
  if (workerData.strategySource) {
    try {
      vm.runInContext(
        `(async () => {
          const ext = window.__fx?.strategyBotExtension;
          if (!ext) return;
          const sid = await ext.strategies.add({ name: "v27team.js", text: async () => ${JSON.stringify(workerData.strategySource)} });
          const targetSid = sid || "file:v27team";
          ext.settings.strategy = targetSid;
          ext.settings.armed = true;
          ext.remote.state.loop = "team";
          if (ext.strategies.changed) ext.strategies.changed(targetSid);
        })()`,
        sandbox
      );
    } catch {}
  }

  // Hook bq.aF3.aFu and bi.a2Q.aWV (re-hooking bi.a2Q on every new game!)
  vm.runInContext(`(() => {
    if (typeof bq === "object" && bq?.aF3?.aFu) {
      const origAfu = bq.aF3.aFu.bind(bq.aF3);
      bq.aF3.aFu = function(tN, aFq, aFr) {
        origAfu(tN, aFq, aFr);
        try {
          if (window.__onHeadlessGameInit) {
            window.__onHeadlessGameInit({
              tN: { spawningSeed: tN.spawningSeed, aFp: tN.aFp, aFv: tN.aFv, fF: tN.fF, mapSeed: tN.mapSeed },
              aFq: Array.from(aFq, p => ({ color: p.color, username: p.username, uY: p.uY, elo: p.elo || 0 })),
              aFr
            });
          }
          if (bi?.a2Q?.aWV && !bi.a2Q.__hooked) {
            bi.a2Q.__hooked = true;
            const origAwv = bi.a2Q.aWV.bind(bi.a2Q);
            bi.a2Q.aWV = function(aD) {
              if (window.__onHeadlessGamePacket && aD) {
                window.__onHeadlessGamePacket(new Uint8Array(aD));
              }
              return origAwv(aD);
            };
          }
        } catch (e) {}
      };
    }
  })()`, sandbox);

  sandbox.__onHeadlessGameInit = (initData) => {
    parentPort.postMessage({ type: 'game_init', initData });
  };
  sandbox.__onHeadlessGamePacket = (pkt) => {
    parentPort.postMessage({ type: 'game_pkt', pkt });
  };

  parentPort.on('message', async (msg) => {
    if (msg.type === 'eval') {
      try {
        let res = vm.runInContext(msg.expression, sandbox);
        if (msg.awaitPromise && res && typeof res.then === 'function') {
          res = await res;
        }
        parentPort.postMessage({ type: 'eval_res', id: msg.id, value: res });
      } catch {
        parentPort.postMessage({ type: 'eval_res', id: msg.id, value: null });
      }
    } else if (msg.type === 'token') {
      if (turnstileCallback) {
        try { turnstileCallback(msg.token); } catch {}
      }
      try {
        const src = msg.strategySource;
        const p = vm.runInContext(
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
          sandbox
        );
        await p;
        parentPort.postMessage({ type: 'token_imported' });
      } catch {}
    }
  });
}
