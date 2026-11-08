import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import net from 'node:net';
import tls from 'node:tls';
import https from 'node:https';
import crypto from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { Worker, isMainThread, parentPort, workerData } from 'node:worker_threads';
import { createRequire } from 'node:module';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
function resolveAssetPath(localName, tmpFallback) {
  const localPath = path.join(__dirname, localName);
  if (fs.existsSync(localPath)) return localPath;
  return tmpFallback;
}

let WS = null;
for (const cand of [path.join(__dirname, 'node_modules/ws/package.json'), '/tmp/node_modules/ws/package.json']) {
  if (fs.existsSync(cand)) {
    try { WS = createRequire(cand)('ws'); break; } catch {}
  }
}

// ============================================================================
// MAIN THREAD API: spawns a dedicated Worker thread for each Headless Bot
// so BFS / Voronoi calculations NEVER block the main thread or packet stream!
// ============================================================================
export function createHeadlessBot(bot, { onResult, onGameInit, onGamePacket, onSpawnRequest, getStrategySource, mintTurnstileToken }) {
  const { port, socksPort, donorChromePort, name, slot } = bot;
  const worker = new Worker(new URL(import.meta.url), {
    execArgv: [],
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
    lastReloadAt: 0,
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
      if (msg.text.includes('error 4591') || msg.text.includes('error 4215') || msg.text.includes('error 4577') || msg.text.includes('error 4229')) {
        client.freshToken = false;
        client.enteredLobbyAt = 0;
        if (msg.text.includes('error 4229')) {
          client.evalJs(`(() => { const d = window.dictionary, g = d && window[d.game]; if (g && g[d.sbLeave] && g[d.gameState] !== 0) g[d.sbLeave](true); })()`);
        }
      }
    } else if (msg.type === 'result') {
      if (onResult) onResult(client, msg.payload);
    } else if (msg.type === 'game_init') {
      if (onGameInit) onGameInit(client, msg.initData);
    } else if (msg.type === 'game_pkt') {
      if (onGamePacket) onGamePacket(client, msg.pkt);
    } else if (msg.type === 'spawn_req') {
      if (onSpawnRequest) onSpawnRequest(client, msg);
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

  const gameJsSource = fs.readFileSync(resolveAssetPath('live_game_js.js', '/tmp/live_game_js.js'), 'utf8')
    .replaceAll('if(bi.ds){bi.ds=false;a0J()}', 'if(bi.ds){bi.ds=false}')
    .replaceAll('if(bi.ds){bi.ds=false;a1C()}', 'if(bi.ds){bi.ds=false}')
    .replace('this.aeB=function(){bi.ds=true;nF();this.eI=0}', 'this.aeB=function(){this.eI=0}')
    .replace('this.af7=function(){bi.ds=true;nF();this.eI=0}', 'this.af7=function(){this.eI=0}')
    .replace(
      'this.aDe=function(aD){if(aE.a2G===2){return}bB.qi.ee(aD);bC.ee();',
      'this.aDe=function(aD){if(aE.a2G===2){return}bB.qi.ee(aD);bC.ee();if(window.__fx?.strategyBot?.beforeFrame)window.__fx.strategyBot.beforeFrame();'
    )
    .replace(
      'this.aEZ=function(aD){if(aE.a38===2){return}bB.qk.ee(aD);bC.ee();',
      'this.aEZ=function(aD){if(aE.a38===2){return}bB.qk.ee(aD);bC.ee();if(window.__fx?.strategyBot?.beforeFrame)window.__fx.strategyBot.beforeFrame();'
    )
    .replace(
      'if(aE.hx){bi.ds=aX.aDe(-1)||bi.ds;nI()}',
      'if(aE.hx){if(window.__fx?.strategyBot?.beforeFrame)window.__fx.strategyBot.beforeFrame();bi.ds=aX.aDe(-1)||bi.ds;nI()}'
    )
    .replace(
      'if(aE.hx){bi.ds=aX.aEZ(-1)||bi.ds;nI()}',
      'if(aE.hx){if(window.__fx?.strategyBot?.beforeFrame)window.__fx.strategyBot.beforeFrame();bi.ds=aX.aEZ(-1)||bi.ds;nI()}'
    )
    .replace(
      'if(this.ae5!==this.aIt*7){n8();be.render();return}',
      'if(this.ae5!==this.aIt*7){n8();while(this.ae7.length>0&&this.ae5<this.aIt*7&&aE.a2G!==2){n8()}if(this.ae7.length===0){return}}'
    )
    .replace(
      'if(this.af1!==this.aK3*7){n8();be.render();return}',
      'if(this.af1!==this.aK3*7){n8();while(this.af3.length>0&&this.af1<this.aK3*7&&aE.a38!==2){n8()}if(this.af3.length===0){return}}'
    )
    .replace(
      'if(this.eI===0){if(bi.eZ>=this.eZ){this.eZ+=bi.aDd*Math.floor(1+(bi.eZ-this.eZ)/bi.aDd);if(aE.a2G===2){n6()}else{this.aeA()}this.eI++;if(bi.eZ-this.ae9>27){this.aeB()}}}else{this.aeB()}',
      'var _steps=0;while(bi.eZ>=this.eZ&&_steps++<28){this.eZ+=bi.aDd;if(aE.a2G===2){n6();break}this.aeA();if(this.ae5===this.aIt*7&&this.ae7.length===0)break}if(bi.eZ>=this.eZ)this.eZ=bi.eZ+bi.aDd;this.eI=0;'
    )
    .replace(
      'if(this.eI===0){if(bi.eZ>=this.eZ){this.eZ+=bi.aEY*Math.floor(1+(bi.eZ-this.eZ)/bi.aEY);if(aE.a38===2){n6()}else{this.af6()}this.eI++;if(bi.eZ-this.af5>27){this.af7()}}}else{this.af7()}',
      'var _steps=0;while(bi.eZ>=this.eZ&&_steps++<28){this.eZ+=bi.aEY;if(aE.a38===2){n6();break}this.af6();if(this.af1===this.aK3*7&&this.af3.length===0)break}if(bi.eZ>=this.eZ)this.eZ=bi.eZ+bi.aEY;this.eI=0;'
    )
    .replace(
      'this.ae7.push(aD);if(aE.a2G===2){',
      'this.ae7.push(aD);if(aE.a2G===1&&!aE.hx&&(this.ae5===this.aIt*7||this.ae7.length>1)){bi.eZ=performance.now();this.ee();return}if(aE.a2G===2){'
    )
    .replace(
      'this.af3.push(aD);if(aE.a38===2){',
      'this.af3.push(aD);if(aE.a38===1&&!aE.hx&&(this.af1===this.aK3*7||this.af3.length>1)){bi.eZ=performance.now();this.ee();return}if(aE.a38===2){'
    )
    .replace('bV.ym.dk();', '')
    .replace('bV.zf.dk();', '');
  const pageJsSource = fs.readFileSync(resolveAssetPath('page.js', '/tmp/tsb-team-ext/page.js'), 'utf8')
    .replaceAll(
      'queueMicrotask(()=>{this.afterQueued=!1,this.afterTick()})',
      'queueMicrotask(()=>{this.afterQueued&&(this.afterQueued=!1,this.afterTick())})'
    )
    .replace(
      'beforeTick(){if(this.eligible()&&this.options().play)try{const t=this.sync();t.online?this.queueAfterTick():!this.error&&t.canAct(t.me)&&this.strategy.act(t)}catch(t){this.fail(t)}}',
      'beforeTick(){if(this.eligible()&&this.options().play)try{if(window[dictionary.game]&&!window[dictionary.game][dictionary.gIsSingleplayer])return;const t=this.sync();!this.error&&t.canAct(t.me)&&this.strategy.act(t)}catch(t){this.fail(t)}}'
    )
    .replace(
      'i&&this.view.online&&"sbSpawn"!==t&&(this.inflight=Ct(),this.view.sendsHeld=!0)',
      'i&&this.view.online&&"sbSpawn"!==t&&(this.inflight=Ct(),this.inflightTick=this.view.t,this.view.sendsHeld=!0)'
    )
    .replace(
      'if(null!==this.inflight&&Ct()-this.inflight<450)return;',
      'if(null!==this.inflight&&Ct()-this.inflight<110&&t.t-(this.inflightTick??0)<2)return;'
    )
    .replace(
      'if(null!==this.inflight&&Ct()-this.inflight<450&&t.t-(this.inflightTick??0)<8)return;',
      'if(null!==this.inflight&&Ct()-this.inflight<110&&t.t-(this.inflightTick??0)<2)return;'
    );
  const dictSource = fs.readFileSync(resolveAssetPath('live_dictionary.json', '/tmp/live_dictionary.json'), 'utf8');

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

  function createNativeWsOverAgent(urlStr, agent, useProxy) {
    const u = new URL(urlStr);
    const host = u.hostname;
    const port = Number(u.port) || (u.protocol === 'wss:' ? 443 : 80);
    const pathAndQuery = (u.pathname || '/') + (u.search || '');
    const handlers = { open: [], message: [], close: [], error: [] };
    const emit = (ev, ...args) => { for (const fn of handlers[ev] || []) { try { fn(...args); } catch {} } };
    let state = 0; // 0=CONNECTING, 1=OPEN, 2=CLOSING, 3=CLOSED
    let sockRef = null;
    let upgraded = false;
    let rxBuf = Buffer.alloc(0);
    let fragOpcode = 0;
    let fragChunks = [];

    const sendFrame = (opcode, payloadBuf) => {
      if (!sockRef || sockRef.destroyed) return;
      const len = payloadBuf.length;
      let hdrLen = 2 + 4;
      if (len >= 126 && len <= 65535) hdrLen += 2;
      else if (len > 65535) hdrLen += 8;
      const frame = Buffer.allocUnsafe(hdrLen + len);
      frame[0] = 0x80 | (opcode & 0x0f);
      let offset = 2;
      if (len < 126) {
        frame[1] = 0x80 | len;
      } else if (len <= 65535) {
        frame[1] = 0x80 | 126;
        frame.writeUInt16BE(len, 2);
        offset = 4;
      } else {
        frame[1] = 0x80 | 127;
        frame.writeBigUInt64BE(BigInt(len), 2);
        offset = 10;
      }
      const mask = crypto.randomBytes(4);
      mask.copy(frame, offset);
      offset += 4;
      for (let i = 0; i < len; i++) {
        frame[offset + i] = payloadBuf[i] ^ mask[i & 3];
      }
      try { sockRef.write(frame); } catch {}
    };

    const parseFrames = () => {
      while (rxBuf.length >= 2) {
        const b0 = rxBuf[0];
        const b1 = rxBuf[1];
        const fin = (b0 & 0x80) !== 0;
        const opcode = b0 & 0x0f;
        const masked = (b1 & 0x80) !== 0;
        let len = b1 & 0x7f;
        let idx = 2;
        if (len === 126) {
          if (rxBuf.length < 4) return;
          len = rxBuf.readUInt16BE(2);
          idx = 4;
        } else if (len === 127) {
          if (rxBuf.length < 10) return;
          len = Number(rxBuf.readBigUInt64BE(2));
          idx = 10;
        }
        if (masked) idx += 4;
        if (rxBuf.length < idx + len) return;
        let payload = rxBuf.subarray(idx, idx + len);
        if (masked) {
          const m = rxBuf.subarray(idx - 4, idx);
          const unmasked = Buffer.allocUnsafe(len);
          for (let i = 0; i < len; i++) unmasked[i] = payload[i] ^ m[i & 3];
          payload = unmasked;
        }
        rxBuf = rxBuf.subarray(idx + len);

        if (opcode === 0x08) {
          let code = 1000;
          let reason = '';
          if (payload.length >= 2) {
            code = payload.readUInt16BE(0);
            reason = payload.subarray(2).toString('utf8');
          }
          state = 3;
          try { sockRef.destroy(); } catch {}
          emit('close', code, Buffer.from(reason));
          return;
        } else if (opcode === 0x09) {
          sendFrame(0x0a, payload);
        } else if (opcode === 0x0a) {
          // pong
        } else if (opcode === 0x01 || opcode === 0x02 || opcode === 0x00) {
          if (opcode !== 0x00) {
            fragOpcode = opcode;
            fragChunks = [Buffer.from(payload)];
          } else {
            fragChunks.push(Buffer.from(payload));
          }
          if (fin) {
            const full = fragChunks.length === 1 ? fragChunks[0] : Buffer.concat(fragChunks);
            fragChunks = [];
            emit('message', full, fragOpcode === 0x02);
          }
        }
      }
    };

    const onSocketReady = (err, tlsSock) => {
      if (err || !tlsSock) {
        state = 3;
        emit('error', err || new Error('Socket connect failed'));
        emit('close', 1006, Buffer.alloc(0));
        return;
      }
      sockRef = tlsSock;
      const key = crypto.randomBytes(16).toString('base64');
      const req =
        `GET ${pathAndQuery} HTTP/1.1\r\n` +
        `Host: ${host}\r\n` +
        `Upgrade: websocket\r\n` +
        `Connection: Upgrade\r\n` +
        `Sec-WebSocket-Key: ${key}\r\n` +
        `Sec-WebSocket-Version: 13\r\n` +
        `Origin: https://territorial.io\r\n` +
        `User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36\r\n\r\n`;
      tlsSock.write(req);

      tlsSock.on('data', (chunk) => {
        rxBuf = Buffer.concat([rxBuf, chunk]);
        if (!upgraded) {
          const sep = rxBuf.indexOf('\r\n\r\n');
          if (sep < 0) return;
          const hdrStr = rxBuf.subarray(0, sep).toString('utf8');
          rxBuf = rxBuf.subarray(sep + 4);
          if (!hdrStr.startsWith('HTTP/1.1 101') && !hdrStr.includes(' 101 ')) {
            state = 3;
            try { tlsSock.destroy(); } catch {}
            emit('error', new Error('WS upgrade failed: ' + hdrStr.split('\r\n')[0]));
            emit('close', 1006, Buffer.alloc(0));
            return;
          }
          upgraded = true;
          state = 1;
          emit('open');
        }
        if (upgraded) parseFrames();
      });

      tlsSock.on('error', (e) => {
        emit('error', e);
      });
      tlsSock.on('close', () => {
        if (state !== 3) {
          state = 3;
          emit('close', 1006, Buffer.alloc(0));
        }
      });
    };

    if (useProxy) {
      agent.createConnection({ host, port, servername: host }, onSocketReady);
    } else {
      const s = tls.connect({ host, port, servername: host, rejectUnauthorized: false }, () => onSocketReady(null, s));
      s.on('error', (e) => onSocketReady(e, null));
    }

    return {
      get readyState() { return state; },
      on(ev, fn) { if (handlers[ev]) handlers[ev].push(fn); },
      send(data) {
        if (state !== 1) return;
        if (typeof data === 'string') {
          sendFrame(0x01, Buffer.from(data, 'utf8'));
        } else if (data instanceof ArrayBuffer) {
          sendFrame(0x02, Buffer.from(data));
        } else if (ArrayBuffer.isView(data)) {
          sendFrame(0x02, Buffer.from(data.buffer, data.byteOffset, data.byteLength));
        } else {
          sendFrame(0x02, Buffer.from(data));
        }
      },
      close(code = 1000) {
        if (state === 3) return;
        state = 2;
        const b = Buffer.allocUnsafe(2);
        b.writeUInt16BE(code, 0);
        sendFrame(0x08, b);
        setTimeout(() => {
          if (state !== 3) {
            state = 3;
            try { sockRef?.destroy(); } catch {}
            emit('close', code, Buffer.alloc(0));
          }
        }, 200);
      }
    };
  }

  function makeProxiedWebSocketClass(sp) {
    const agent = makeSocksAgent(sp);
    return class ProxiedWebSocket {
      static CONNECTING = 0; static OPEN = 1; static CLOSING = 2; static CLOSED = 3;
      constructor(url, protocols) {
        this.url = url;
        this.CONNECTING = 0; this.OPEN = 1; this.CLOSING = 2; this.CLOSED = 3;
        this.binaryType = 'blob';
        const isProxied = typeof url === 'string' && url.includes('territorial.io');
        this._ws = WS
          ? new WS(url, protocols, {
              agent: isProxied ? agent : undefined,
              headers: {
                'Origin': 'https://territorial.io',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36'
              }
            })
          : createNativeWsOverAgent(url, agent, isProxied);
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
    putImageData(img) {},
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
    spawn: true, play: true, autoStart: false, manual: true, armed: true, stay: true,
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
  }, 16);

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
    __tsbFollowLeader: 'kazerd183',
    __tsbWaitForLeader: true,
    __tsbSquadSyncHold: true,
    __hlLog(text) {
      parentPort.postMessage({ type: 'log', text: String(text) });
    },
    __hlSpawnReq(payload) {
      parentPort.postMessage({ type: 'spawn_req', ...payload });
    },
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
    } catch (err) {
      parentPort.postMessage({ type: 'log', text: `[HL-ERR] tsb-remote parse: ${err?.message || err}` });
    }
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
  // Strip canvas dirty-rect & putImageData work completely in Headless Worker
  vm.runInContext(`(() => {
    if (typeof be === "object" && be) {
      be.render = function() {};
      be.a6d = function() {};
      be.a2S = function() {};
    }
    if (typeof bX === "object" && bX?.eS && typeof bX.eS.ei === "function") {
      bX.eS.ei = function(ej) {
        const sendAns = b1?.eg?.x6 || b1?.eg?.wC;
        if (ej && ej.id >= 0 && typeof b1 === "object" && b1?.z?.ef?.(0) && sendAns) {
          sendAns.call(b1.eg, 0, ej.id);
          setTimeout(() => {
            try { if (b1.z.ef(0)) sendAns.call(b1.eg, 1, ej.id); } catch {}
          }, 350 + Math.floor(Math.random() * 450));
        }
      };
    }
    if (typeof ax === "object" && ax && typeof ax.iK === "function" && !ax.__hookedPeaceCaller) {
      ax.__hookedPeaceCaller = true;
      const origIk = ax.iK.bind(ax);
      ax.iK = function(player) {
        window.__lastPeaceCaller = player;
        return origIk(player);
      };
    }
    const hdl = (typeof bB === "object" && (bB?.qi || bB?.qg)) || null;
    if (hdl && !hdl.__hookedQuit) {
      hdl.__hookedQuit = true;
      window.__quitPlayers = new Set();
      for (const fnName of ["r8", "rd", "rA", "rf"]) {
        if (typeof hdl[fnName] === "function") {
          const origFn = hdl[fnName].bind(hdl);
          hdl[fnName] = function(player) {
            window.__quitPlayers?.add(player);
            return origFn(player);
          };
        }
      }
    }
    window.__hlPerf = { ticks: 0, totalMs: 0, maxMs: 0, lastTick: -1, dupTicks: 0, skippedTicks: 0 };
    if (window.__fx?.strategyBot?.afterTick) {
      const origAfterTick = window.__fx.strategyBot.afterTick.bind(window.__fx.strategyBot);
      window.__fx.strategyBot.afterTick = function() {
        const t0 = performance.now();
        const curTick = typeof bi === "object" && bi?.kr ? bi.kr() : -1;
        const pf = window.__hlPerf;
        if (curTick >= 0) {
          if (curTick === pf.lastTick) pf.dupTicks++;
          else if (pf.lastTick >= 0 && curTick > pf.lastTick + 1) pf.skippedTicks += (curTick - pf.lastTick - 1);
          pf.lastTick = curTick;
        }
        try {
          return origAfterTick();
        } finally {
          const dt = performance.now() - t0;
          pf.ticks++;
          pf.totalMs += dt;
          if (dt > pf.maxMs) pf.maxMs = dt;
          if (dt > 25 && window.__hlLog) {
            window.__hlLog(\`[HL-SLOW-TICK] t=\${curTick} took \${dt.toFixed(1)}ms (max=\${pf.maxMs.toFixed(1)}ms)\`);
          }
        }
      };
    }
  })()`, sandbox);

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
    } catch (err) {
      parentPort.postMessage({ type: 'log', text: `[HL-ERR] init strategy import: ${err?.message || err}` });
    }
  }

  // Hook bq.aFy.aH4 / bq.aF3.aFu and bi.a3R.aXQ / bi.a2Q.aWV (re-hooking on every new game!)
  vm.runInContext(`(() => {
    const startHolder = (typeof bq === "object" && (bq?.aFy?.aH4 ? bq.aFy : bq?.aF3?.aFu ? bq.aF3 : null));
    const startFnName = startHolder?.aH4 ? "aH4" : "aFu";
    if (startHolder && typeof startHolder[startFnName] === "function") {
      const origAfu = startHolder[startFnName].bind(startHolder);
      startHolder[startFnName] = function(tN, aFq, aFr) {
        window.__hlPerf = { ticks: 0, totalMs: 0, maxMs: 0, lastTick: -1, dupTicks: 0, skippedTicks: 0 };
        window.__lastPeaceCaller = -1;
        window.__tsbAssignedSpawn = null;
        window.__quitPlayers = new Set();
        if (Array.isArray(aFq)) {
          for (let i = 0; i < aFq.length; i++) {
            const p = aFq[i];
            if (p && (p.aGM || p.aGT || p.aFN || p.aFU)) {
              p.username = p.aGM || p.aGT || p.aFN || p.aFU || p.username;
            }
          }
        }
        origAfu(tN, aFq, aFr);
        try {
          const modeVal = tN.vz ?? tN.aFp;
          if (window.__hlLog) {
            window.__hlLog(\`[HL-GAME-INIT] mode=\${modeVal} map=\${tN.fF} mapSeed=\${tN.mapSeed} players=\${aFq?.length || 0} me=\${aFr}\`);
          }
          if (window.__onHeadlessGameInit) {
            window.__onHeadlessGameInit({
              tN: { spawningSeed: tN.spawningSeed, aFp: modeVal, aFv: tN.wN ?? tN.aFv, fF: tN.fF, mapSeed: tN.mapSeed },
              aFq: Array.from(aFq, p => ({ color: p.color, username: p.username, uY: p.uX ?? p.uY, elo: p.elo || 0 })),
              aFr
            });
          }
          const loopObj = bi?.a3R || bi?.a2Q;
          const pktFn = loopObj?.aXQ ? "aXQ" : loopObj?.aWV ? "aWV" : null;
          if (loopObj && pktFn && !loopObj.__hooked) {
            loopObj.__hooked = true;
            const origAwv = loopObj[pktFn].bind(loopObj);
            loopObj[pktFn] = function(aD) {
              if (window.__onHeadlessGamePacket && aD) {
                window.__onHeadlessGamePacket(new Uint8Array(aD));
              }
              return origAwv(aD);
            };
          }
        } catch (e) {
          if (window.__hlLog) window.__hlLog(\`[HL-ERR] aFu hook: \${e?.message || e}\`);
        }
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
      } catch (err) {
        parentPort.postMessage({ type: 'log', text: `[HL-ERR] eval failed: ${err?.message || err}` });
        parentPort.postMessage({ type: 'eval_res', id: msg.id, value: null });
      }
    } else if (msg.type === 'set_spawn') {
      sandbox.__tsbAssignedSpawn = msg.pos;
      try {
        vm.runInContext(
          `(() => {
            const pos = window.__tsbAssignedSpawn;
            const bot = window.__fx?.strategyBot;
            const v = bot?.view;
            if (pos && v && v.spawnPhase && Number.isInteger(pos.x) && Number.isInteger(pos.y)) {
              const cur = bot.spawn;
              if (!cur || Math.abs(pos.x - cur.x) + Math.abs(pos.y - cur.y) > 4) {
                if (v.chooseSpawn(pos.x, pos.y)) {
                  bot.spawn = { x: pos.x, y: pos.y };
                  if (window.__hlLog && (!window.__lastImmediateSpawnLog || Math.hypot(pos.x - window.__lastImmediateSpawnLog.x, pos.y - window.__lastImmediateSpawnLog.y) > 6)) {
                    window.__lastImmediateSpawnLog = { x: pos.x, y: pos.y };
                    window.__hlLog(\`[HL-SPAWN-BACKEND] me=\${v.me} slot=\${pos.slot ?? window.__tsbSquadSlot} role=\${pos.role || "SQUAD"} -> (\${pos.x},\${pos.y}) bossDist=\${pos.bossDist ?? -1} minAllyDist=\${pos.minAllyDist ?? -1} voronoi=\${pos.voronoiPixels ?? -1}\`);
                  }
                }
              }
            }
          })()`,
          sandbox
        );
      } catch {}
    } else if (msg.type === 'token') {
      if (turnstileCallback) {
        try { turnstileCallback(msg.token); } catch (err) {
          parentPort.postMessage({ type: 'log', text: `[HL-ERR] turnstileCallback: ${err?.message || err}` });
        }
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
      } catch (err) {
        parentPort.postMessage({ type: 'log', text: `[HL-ERR] token strategy import: ${err?.message || err}` });
      }
    }
  });
}
