// engine_host.cjs — 在 Node 里原样加载线上客户端（live_game_js.js），只把浏览器接口换成空壳，
// 让引擎自己的结算代码（经济、陆攻、船、内置 AI、配额、投票、出局）一行不改地跑起来。
//
// 用途：按录像逐拍重放整局，得到全场每个玩家每一拍的真实状态（scripts/engine_replay.cjs）。
// 这里不重写任何规则；凡是规则都来自线上原文。空壳只负责：DOM 元素、画布、图片、网络、存储、计时器。
//
// 导出：createHost(opts) → { ctx, run(code), timers, log }
const fs = require('fs');
const vm = require('vm');

const LIVE = '/agent/repos/c136-data/src/engine/live_game_js.js';

function createHost(opts = {}) {
  const log = [];
  const timers = [];
  let now = 1000;

  // 万能空壳：任何属性都是它自己，调用返回它自己，转成数字是 0，转成字符串是 ''
  const makeU = (name) => {
    const f = function () {};
    const p = new Proxy(f, {
      get(t, k) {
        if (k === Symbol.toPrimitive) return (hint) => (hint === 'string' ? '' : 0);
        if (k === 'toString') return () => '';
        if (k === 'valueOf') return () => 0;
        if (k === 'length') return 0;
        if (k === 'then') return undefined;
        if (k === Symbol.iterator) return function* () {};
        if (k in t.__store) return t.__store[k];
        return p;
      },
      set(t, k, v) { t.__store[k] = v; return true; },
      apply() { return p; },
      construct() { return p; },
      has() { return true; },
    });
    f.__store = {};
    return p;
  };
  const U = makeU('U');

  const makeImageData = (w, h) => ({ width: w | 0, height: h | 0, data: new Uint8ClampedArray(Math.max(0, (w | 0) * (h | 0) * 4)) });
  const makeCtx = (canvas) => {
    const base = {
      canvas,
      getImageData: (x, y, w, h) => makeImageData(w, h),
      createImageData: (w, h) => (typeof w === 'object' ? makeImageData(w.width, w.height) : makeImageData(w, h)),
      putImageData() {},
      measureText: (s) => ({ width: 8 * String(s).length }),
      createLinearGradient: () => ({ addColorStop() {} }),
      createRadialGradient: () => ({ addColorStop() {} }),
      createPattern: () => ({}),
      getLineDash: () => [],
    };
    return new Proxy(base, {
      get(t, k) {
        if (k in t) return t[k];
        return function () {};
      },
      set(t, k, v) { t[k] = v; return true; },
    });
  };
  const makeEl = (tag) => {
    const el = {
      tagName: String(tag || 'div').toUpperCase(),
      style: new Proxy({}, { get: (t, k) => (k in t ? t[k] : ''), set: (t, k, v) => { t[k] = v; return true; } }),
      children: [], childNodes: [], classList: { add() {}, remove() {}, contains: () => false, toggle() {} },
      dataset: {}, attributes: {},
      width: 300, height: 150, clientWidth: 1280, clientHeight: 720, offsetWidth: 1280, offsetHeight: 720, scrollTop: 0, scrollHeight: 0,
      innerHTML: '', textContent: '', value: '', checked: false, files: [],
      appendChild(c) { this.children.push(c); return c; },
      removeChild(c) { const i = this.children.indexOf(c); if (i >= 0) this.children.splice(i, 1); return c; },
      insertBefore(c) { this.children.push(c); return c; },
      replaceChild(c) { return c; },
      remove() {}, focus() {}, blur() {}, click() {}, select() {}, scrollIntoView() {}, setSelectionRange() {},
      addEventListener() {}, removeEventListener() {}, dispatchEvent() { return true; },
      setAttribute(k, v) { this.attributes[k] = v; }, getAttribute(k) { return this.attributes[k] ?? null; }, removeAttribute() {},
      getBoundingClientRect: () => ({ left: 0, top: 0, right: 1280, bottom: 720, width: 1280, height: 720, x: 0, y: 0 }),
      getContext() { if (!this.__ctx) this.__ctx = makeCtx(this); return this.__ctx; },
      toDataURL: () => 'data:image/png;base64,AAAA',
      toBlob(cb) { cb && cb(null); },
      querySelector: () => null, querySelectorAll: () => [],
      contains: () => false, cloneNode() { return makeEl(tag); },
      requestFullscreen() {}, requestPointerLock() {},
      sheet: { cssRules: [], insertRule(r, i) { this.cssRules.splice(i || 0, 0, { cssText: r, style: {} }); return i || 0; }, deleteRule(i) { this.cssRules.splice(i, 1); } },
    };
    return el;
  };
  function FakeImage() {
    const im = makeEl('img');
    im.width = 16; im.height = 16; im.naturalWidth = 16; im.naturalHeight = 16; im.complete = true;
    let src = '';
    Object.defineProperty(im, 'src', {
      get: () => src,
      set(v) { src = v; if (opts.autoImageLoad !== false) timers.push({ at: now, fn: () => { if (typeof im.onload === 'function') im.onload({ target: im }); } }); },
    });
    return im;
  }
  function FakeWebSocket(url) {
    const ws = { url, readyState: 0, OPEN: 1, CONNECTING: 0, CLOSED: 3, binaryType: 'arraybuffer', send() {}, close() { this.readyState = 3; }, addEventListener() {} };
    log.push('WebSocket ' + url);
    return ws;
  }
  FakeWebSocket.OPEN = 1; FakeWebSocket.CONNECTING = 0; FakeWebSocket.CLOSED = 3;
  const storage = {};
  const body = makeEl('body');
  const documentStub = {
    body, documentElement: makeEl('html'), head: makeEl('head'), hidden: false, visibilityState: 'visible', fonts: { ready: { then() {} }, load: () => ({ then() {} }) },
    createElement: (t) => makeEl(t), createElementNS: (ns, t) => makeEl(t), createTextNode: () => makeEl('#text'),
    getElementById: () => makeEl('div'), getElementsByTagName: () => [makeEl('div')], getElementsByClassName: () => [], querySelector: () => null, querySelectorAll: () => [],
    addEventListener() {}, removeEventListener() {}, exitPointerLock() {}, exitFullscreen() {}, cookie: '', title: '', referrer: '', fullscreenElement: null,
    styleSheets: [makeEl('style').sheet],
  };
  const sandbox = {
    console: { log: (...a) => { log.push(a.map(String).join(' ')); if (opts.echo) console.log('[engine]', ...a); }, warn() {}, error: (...a) => log.push('ERR ' + a.map(String).join(' ')) },
    document: documentStub,
    navigator: { userAgent: 'node', language: 'en', languages: ['en'], platform: 'Linux', maxTouchPoints: 0, clipboard: { writeText: () => ({ then() {}, catch() {} }) }, onLine: true, hardwareConcurrency: 4, vibrate() {} },
    location: { hostname: 'localhost', href: 'http://localhost/', search: '', protocol: 'http:', host: 'localhost', pathname: '/', hash: '', reload() {}, replace() {}, assign() {} },
    history: { replaceState() {}, pushState() {} },
    localStorage: { getItem: (k) => (k in storage ? storage[k] : null), setItem: (k, v) => { storage[k] = String(v); }, removeItem: (k) => { delete storage[k]; }, clear() {} },
    sessionStorage: { getItem: () => null, setItem() {}, removeItem() {} },
    performance: { now: () => now },
    Date: class extends Date { constructor(...a) { if (a.length) super(...a); else super(1762700000000 + now); } static now() { return 1762700000000 + now; } },
    setTimeout: (fn, ms) => { timers.push({ at: now + (ms || 0), fn }); return timers.length; },
    clearTimeout() {}, setInterval: () => 0, clearInterval() {},
    requestAnimationFrame: () => 0, cancelAnimationFrame() {},
    alert: (s) => log.push('ALERT ' + s), confirm: () => false, prompt: () => null,
    Image: FakeImage, WebSocket: FakeWebSocket, Audio: function () { return makeEl('audio'); },
    XMLHttpRequest: function () { return { open() {}, send() {}, setRequestHeader() {}, addEventListener() {} }; },
    fetch: () => ({ then() { return this; }, catch() { return this; }, finally() { return this; } }),
    URL: class { constructor(u) { this.href = String(u); this.searchParams = { get: () => null, set() {}, has: () => false, toString: () => '' }; this.search = ''; } toString() { return this.href; } static createObjectURL() { return 'blob:x'; } static revokeObjectURL() {} },
    Blob: function () {}, FileReader: function () { return { readAsDataURL() {}, readAsArrayBuffer() {}, readAsText() {} }; },
    screen: { width: 1280, height: 720, orientation: { type: 'landscape-primary' } },
    innerWidth: 1280, innerHeight: 720, devicePixelRatio: 1, pageXOffset: 0, pageYOffset: 0, scrollX: 0, scrollY: 0,
    addEventListener() {}, removeEventListener() {}, dispatchEvent() { return true; }, open() {}, focus() {}, close() {}, scrollTo() {}, getComputedStyle: () => ({ getPropertyValue: () => '' }),
    matchMedia: () => ({ matches: false, addEventListener() {}, addListener() {} }),
    atob: (s) => Buffer.from(String(s), 'base64').toString('binary'), btoa: (s) => Buffer.from(String(s), 'binary').toString('base64'),
    TextEncoder, TextDecoder, Uint8Array, Uint16Array, Uint32Array, Int8Array, Int16Array, Int32Array, Float32Array, Float64Array, Uint8ClampedArray, ArrayBuffer, DataView,
    Math, JSON, Object, Array, String, Number, Boolean, RegExp, Error, TypeError, RangeError, Map, Set, WeakMap, Promise, Symbol, parseInt, parseFloat, isNaN, isFinite, encodeURIComponent, decodeURIComponent, encodeURI, decodeURI, Infinity, NaN, undefined,
    __fx: { strategyBot: { beforeTick() {}, afterTick: null, beforeFrame() {}, setAttackSlots() {}, replay() {}, closed() {} } },
    __U: U,
  };
  sandbox.window = sandbox; sandbox.self = sandbox; sandbox.top = sandbox; sandbox.parent = sandbox; sandbox.globalThis = sandbox;
  // 不用 vm 沙箱：沙箱里每次读写顶层变量都要过拦截器，引擎会慢一个数量级。
  // 改为把整份源码包进一个函数：引擎的顶层 var / function 成了这个函数的局部量，浏览器接口用同名形参顶替。
  const src = fs.readFileSync(LIVE, 'utf8');
  const patched = opts.patch ? opts.patch(src) : src;
  const names = Object.keys(sandbox).filter((k) => /^[A-Za-z_$][\w$]*$/.test(k) && !['undefined', 'NaN', 'Infinity', 'globalThis'].includes(k));
  const wrapper = '(function(' + names.join(',') + '){' + patched + '\n;return function(__c){"use strict";return eval(__c);};})';
  const factory = vm.runInThisContext(wrapper, { filename: 'live_game_js.js' });
  const ev = factory(...names.map((k) => sandbox[k]));
  const ctx = sandbox; // 给引擎传数据：ctx.__x = …，引擎里用 window.__x 读
  const run = (code) => ev(code);
  const flushTimers = (maxRounds = 50, advance = 0) => {
    now += advance;
    for (let r = 0; r < maxRounds; r++) {
      const due = [];
      for (let i = timers.length - 1; i >= 0; i--) if (timers[i].at <= now) due.push(timers.splice(i, 1)[0]);
      if (!due.length) break;
      due.reverse();
      for (const t of due) { try { t.fn(); } catch (e) { log.push('TIMER-ERR ' + (e && e.stack ? e.stack.split('\n').slice(0, 3).join(' | ') : e)); } }
    }
  };
  return { ctx, run, timers, log, flushTimers, advance: (ms) => { now += ms; }, makeImageData };
}

module.exports = { createHost, LIVE };

if (require.main === module) {
  // 自检：加载并跑引导函数 bx()，报告走到哪一步
  const h = createHost({ echo: process.argv.includes('--echo') });
  let ok = true;
  try {
    h.run('bx(true)');
  } catch (e) {
    ok = false;
    console.log('BOOT-FAIL', e && e.stack ? e.stack.split('\n').slice(0, 6).join('\n') : e);
  }
  h.flushTimers();
  console.log('boot ok =', ok, '| typeof aE =', h.run('typeof aE'), '| aE ctor ok =', h.run('!!(aE && aE.a7g)'), '| log lines', h.log.length);
  console.log(h.log.slice(0, 12).join('\n'));
}
