// One Firefox donor, one Turnstile solve attempt, instrumented.
//
// Mirrors _initFirefoxDonor + mintViaDonorChrome in tsb-apex-squad.mjs step for step (same exe,
// same profile, same args, same preload script, same render options, same click actions) and adds
// only observation: widget callbacks, frame tree, resource timing, screenshots.
// The token value is never written anywhere; only its length is recorded.
//
// Run with cwd = c116:   node_apex.exe ..\c136\probe_one_donor.mjs [port] [outDir] [flags]
//
// Flags (all off by default, so the default run behaves like the engine):
//   --console          also subscribe to log.entryAdded. Off by default because the engine never
//                      subscribes, and a console listener is something a challenge page can notice.
//   --profile=<dir>    profile directory to use instead of firefox_donor_<port>. The probe never
//                      writes user.js; prepare an experimental profile by hand.
//   --click=smart      instead of the engine's blind click every ~0.7s from the start, wait until
//                      the widget is visible and click the checkbox once (at most 3 tries).
import fs from 'node:fs';
import path from 'node:path';
import { spawn } from 'node:child_process';

const flags = process.argv.slice(2).filter((a) => a.startsWith('--'));
const positional = process.argv.slice(2).filter((a) => !a.startsWith('--'));
const flagValue = (name) => (flags.find((f) => f.startsWith(`--${name}=`)) || '').split('=').slice(1).join('=') || null;
const wantConsole = flags.includes('--console');
const clickMode = flagValue('click') === 'smart' ? 'smart' : 'engine';

const port = Number(positional[0] || 9228);
const baseDir = process.cwd();
const outDir = path.resolve(positional[1] || path.join(baseDir, '..', 'c136', 'probe_out'));
const ffExe = path.join(baseDir, 'firefox_bin', 'firefox.exe');
const profDir = path.resolve(baseDir, flagValue('profile') || `firefox_donor_${port}`);
const stamp = new Date().toISOString().replace(/[:.]/g, '-');
const T0 = Date.now();
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const report = {
  stamp, port, baseDir, profile: path.basename(profDir), clickMode, wantConsole, clicks: 0, verdict: null, tokenLen: 0,
  steps: [], pageState: {}, widgetEvents: [], iterations: [], frames: [], resources: [],
  console: [], screenshots: []
};
const step = (name, data) => report.steps.push({ t: Date.now() - T0, name, data: data ?? null });

fs.mkdirSync(outDir, { recursive: true });
const outJson = path.join(outDir, `probe-${stamp}.json`);
const save = () => { try { fs.writeFileSync(outJson, JSON.stringify(report, null, 1)); } catch {} };

let ws = null;
let seq = 0;
const pending = new Map();

const tryConnectBidi = () => new Promise((resolve) => {
  let sock;
  try { sock = new WebSocket(`ws://127.0.0.1:${port}/session`); } catch { return resolve(null); }
  const t = setTimeout(() => { try { sock.close(); } catch {} resolve(null); }, 3000);
  sock.addEventListener('open', () => { clearTimeout(t); resolve(sock); });
  sock.addEventListener('error', () => { clearTimeout(t); resolve(null); });
});

const callBidi = (method, params = {}) => new Promise((resolve) => {
  if (!ws || ws.readyState !== 1) return resolve(null);
  const id = ++seq;
  const timer = setTimeout(() => { pending.delete(id); resolve(null); }, 8000);
  pending.set(id, (msg) => { clearTimeout(timer); resolve(msg); });
  ws.send(JSON.stringify({ id, method, params }));
});

async function evalStr(ctx, expression, extra = {}) {
  const r = await callBidi('script.evaluate', { expression, target: { context: ctx }, awaitPromise: false, ...extra });
  if (!r) return { ok: false, err: 'no-response' };
  if (r.type === 'error') return { ok: false, err: `${r.error}: ${String(r.message || '').slice(0, 200)}` };
  const res = r.result;
  if (res?.type === 'exception') return { ok: false, err: 'exception: ' + String(res.exceptionDetails?.text || '').slice(0, 200) };
  return { ok: true, value: res?.result?.value };
}

async function evalJson(ctx, expression, extra = {}) {
  const r = await evalStr(ctx, expression, extra);
  if (!r.ok) return { __err: r.err };
  try { return JSON.parse(r.value); } catch { return { __raw: String(r.value).slice(0, 200) }; }
}

async function shot(ctx, label, clip) {
  const params = { context: ctx };
  if (clip) params.clip = { type: 'box', x: 0, y: 0, width: clip[0], height: clip[1] };
  const r = await callBidi('browsingContext.captureScreenshot', params);
  const data = r?.result?.data;
  if (!data) { report.screenshots.push({ label, error: r?.message || 'no-data' }); return; }
  const file = path.join(outDir, `probe-${stamp}-${label}.png`);
  const buf = Buffer.from(data, 'base64');
  fs.writeFileSync(file, buf);
  report.screenshots.push({ label, file: path.basename(file), bytes: buf.length, t: Date.now() - T0 });
}

const PRELOAD = `() => {
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
    }`;

const PAGE_STATE = `JSON.stringify({
  wd: String(navigator.webdriver), ts: typeof window.turnstile, tsRender: typeof (window.turnstile && window.turnstile.render),
  rs: document.readyState, vis: document.visibilityState, focus: document.hasFocus(), href: location.href,
  ua: navigator.userAgent, iw: innerWidth, ih: innerHeight
})`;

const RESOURCES = `JSON.stringify(performance.getEntriesByType('resource')
  .filter((e) => e.name.includes('challenges.cloudflare.com'))
  .map((e) => ({ n: e.name.slice(0, 110), start: Math.round(e.startTime), d: Math.round(e.duration), size: e.transferSize, st: e.responseStatus })))`;

// Same cleanup and render as the engine; the extra callbacks only record events.
const RENDER = `(() => {
  const ev = (window.__probeEv = []);
  const t0 = performance.now();
  const push = (name, data) => ev.push({ t: Math.round(performance.now() - t0), name, data: data === undefined ? null : String(data) });
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
  if (!window.turnstile || typeof window.turnstile.render !== "function") { push("NO_TS"); return "NO_TS"; }
  const wid = window.turnstile.render(div, {
    sitekey: "0x4AAAAAAEI8HZoG8nJMzxt1",
    action: "enter_lobby",
    appearance: "interaction-only",
    callback: (tok) => { window.__mintedToken = tok; push("success", "len=" + (tok ? tok.length : 0)); },
    "error-callback": (code) => { push("error", code); },
    "expired-callback": () => { push("expired"); },
    "timeout-callback": () => { push("timeout"); },
    "unsupported-callback": () => { push("unsupported"); },
    "before-interactive-callback": () => { push("before-interactive"); },
    "after-interactive-callback": () => { push("after-interactive"); }
  });
  window.__probeWid = wid;
  push("rendered", wid);
  return "RENDERED:" + wid;
})()`;

const POLL = `JSON.stringify((() => {
  const div = document.getElementById("mint-ts");
  const r = div ? div.getBoundingClientRect() : null;
  return {
    tok: (window.__mintedToken || "").length,
    ev: (window.__probeEv || []).length,
    rect: r ? [Math.round(r.x), Math.round(r.y), Math.round(r.width), Math.round(r.height)] : null,
    kids: div ? div.children.length : -1,
    vis: document.visibilityState,
    focus: document.hasFocus()
  };
})())`;

const CLICK = {
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
};

// Checkbox centre measured from screenshots of the 300x65 widget rendered at 0,0.
const SMART_CLICK = {
  actions: [
    {
      type: 'pointer',
      id: 'mouse1',
      parameters: { pointerType: 'mouse' },
      actions: [
        { type: 'pointerMove', x: 236, y: 148, duration: 90 },
        { type: 'pointerMove', x: 97, y: 71, duration: 210 },
        { type: 'pointerMove', x: 22, y: 33, duration: 170 },
        { type: 'pause', duration: 110 },
        { type: 'pointerDown', button: 0 },
        { type: 'pause', duration: 75 },
        { type: 'pointerUp', button: 0 }
      ]
    }
  ]
};

const flatten = (c, depth = 0, acc = []) => {
  acc.push({ depth, url: String(c.url || '').slice(0, 130) });
  for (const k of c.children || []) flatten(k, depth + 1, acc);
  return acc;
};

async function main() {
  if (!fs.existsSync(ffExe)) { report.verdict = 'ABORT: firefox_bin/firefox.exe not found (wrong cwd?)'; return; }
  const userJs = path.join(profDir, 'user.js');
  if (!fs.existsSync(userJs)) { report.verdict = 'ABORT: donor profile user.js missing'; return; }
  report.pageState.profileSocksPort = (fs.readFileSync(userJs, 'utf8').match(/socks_port",\s*(\d+)/) || [])[1] || null;

  const already = await tryConnectBidi();
  if (already) {
    try { already.close(); } catch {}
    report.verdict = `ABORT: something already answers BiDi on :${port}; not touching it`;
    return;
  }

  try { fs.unlinkSync(path.join(profDir, 'parent.lock')); } catch {}
  try { fs.unlinkSync(path.join(profDir, '.startup-incomplete')); } catch {}
  const child = spawn(ffExe, ['-no-remote', '-profile', profDir, '--remote-debugging-port', String(port), 'https://territorial.io/'], {
    detached: true,
    stdio: 'ignore'
  });
  child.unref();
  step('firefox-spawned', { pid: child.pid });

  for (let retry = 0; retry < 18 && !ws; retry++) {
    await sleep(1000);
    ws = await tryConnectBidi();
  }
  if (!ws) { report.verdict = 'FAIL: Firefox BiDi not reachable within 18s'; return; }
  step('bidi-connected');

  ws.addEventListener('message', (evt) => {
    let msg;
    try { msg = JSON.parse(evt.data); } catch { return; }
    if (msg.id && pending.has(msg.id)) {
      const fn = pending.get(msg.id);
      pending.delete(msg.id);
      fn(msg);
    } else if (msg.method === 'log.entryAdded' && report.console.length < 250) {
      const p = msg.params || {};
      report.console.push({ t: Date.now() - T0, level: p.level, type: p.type, text: String(p.text || '').slice(0, 300) });
    }
  });

  const sess = await callBidi('session.new', { capabilities: {} });
  if (!sess?.result?.sessionId) {
    report.verdict = 'FAIL: session.new returned no sessionId (the engine logs this as "BiDi session locked")';
    step('session-new-failed', sess ? { error: sess.error, message: String(sess.message || '').slice(0, 200) } : 'no-response');
    return;
  }
  step('session-new-ok');

  if (wantConsole) {
    const sub = await callBidi('session.subscribe', { events: ['log.entryAdded'] });
    step('subscribe-log', sub?.type === 'error' ? `${sub.error}` : 'ok');
  }

  const pre = await callBidi('script.addPreloadScript', { functionDeclaration: PRELOAD });
  step('add-preload-script', pre?.result?.script ? 'ok' : (pre ? `${pre.error || 'no-script-id'}: ${String(pre.message || '').slice(0, 160)}` : 'no-response'));

  const tree = await callBidi('browsingContext.getTree', {});
  const topCtx = tree?.result?.contexts?.find((c) => c.url?.includes('territorial.io')) || tree?.result?.contexts?.[0];
  const ctx = topCtx?.context;
  if (!ctx) { report.verdict = 'FAIL: no browsingContext found'; return; }
  step('context', { url: String(topCtx.url || '').slice(0, 100) });

  await callBidi('browsingContext.activate', { context: ctx });

  const wd = await evalStr(ctx, 'String(navigator.webdriver) + ":" + String(typeof window.turnstile)');
  step('engine-wd-check', wd.ok ? wd.value : wd.err);
  if (!(wd.ok && String(wd.value).startsWith('false:object'))) {
    const rl = await callBidi('browsingContext.reload', { context: ctx, wait: 'interactive' });
    step('reload', rl ? (rl.type === 'error' ? `${rl.error}` : 'ok') : 'no-response(8s)');
    await sleep(3500);
  }

  // The engine logs "webdriver=false" here without measuring it. Measure it.
  report.pageState.afterInit = await evalJson(ctx, PAGE_STATE);
  step('page-state-after-init', report.pageState.afterInit);

  // Engine waits up to 12 x 600ms for turnstile.render, then renders regardless.
  let readyAtIter = -1;
  for (let w = 0; w < 12; w++) {
    const r = await evalStr(ctx, 'typeof window.turnstile?.render');
    if (r.ok && r.value === 'function') { readyAtIter = w; break; }
    await sleep(600);
  }
  report.pageState.turnstileReadyWithinEngineWait = readyAtIter >= 0;
  step('engine-ts-wait', { readyAtIter });

  // Diagnostic only: if the engine's wait was not enough, see whether it ever loads.
  if (readyAtIter < 0) {
    const tExtra = Date.now();
    let late = false;
    while (Date.now() - tExtra < 20000) {
      const r = await evalStr(ctx, 'typeof window.turnstile?.render');
      if (r.ok && r.value === 'function') { late = true; break; }
      await sleep(1000);
    }
    report.pageState.turnstileReadyLate = late;
    report.pageState.turnstileLateExtraMs = Date.now() - tExtra;
    step('extra-ts-wait', { late, extraMs: Date.now() - tExtra });
  }

  report.pageState.beforeRender = await evalJson(ctx, PAGE_STATE);
  report.resources = await evalJson(ctx, RESOURCES);
  await shot(ctx, '0-before-render', [520, 300]);

  const rend = await evalStr(ctx, RENDER, { userActivation: true });
  step('render', rend.ok ? rend.value : rend.err);

  const tLoop = Date.now();
  let firstVisibleAt = 0;
  let lastClickAt = 0;
  for (let i = 0; clickMode === 'engine' ? i < 22 : Date.now() - tLoop < 34000; i++) {
    await sleep(650);
    const st = await evalJson(ctx, POLL);
    report.iterations.push({ i, t: Date.now() - T0, ...st });
    if (i === 2) await shot(ctx, '1-iter2', [520, 300]);
    if (i === 9) await shot(ctx, '2-iter9-full', null);
    if (i === 9) await shot(ctx, '2-iter9', [520, 300]);
    if (typeof st.tok === 'number' && st.tok > 100) { report.tokenLen = st.tok; break; }
    if (clickMode === 'engine') {
      await callBidi('input.performActions', { context: ctx, ...CLICK });
      report.clicks++;
      continue;
    }
    const visible = Array.isArray(st.rect) && st.rect[2] > 0;
    if (visible && !firstVisibleAt) firstVisibleAt = Date.now();
    if (visible && Date.now() - firstVisibleAt > 900 && report.clicks < 3 && Date.now() - lastClickAt > 8000) {
      const r = await callBidi('input.performActions', { context: ctx, ...SMART_CLICK });
      report.clicks++;
      lastClickAt = Date.now();
      step('smart-click', { n: report.clicks, result: r ? (r.type === 'error' ? `${r.error}: ${String(r.message || '').slice(0, 120)}` : 'ok') : 'no-response(8s)' });
      await sleep(450);
      await shot(ctx, `c${report.clicks}-after-click`, [520, 300]);
    }
  }
  await shot(ctx, '3-end', [520, 300]);

  report.widgetEvents = await evalJson(ctx, 'JSON.stringify(window.__probeEv || [])');
  report.resourcesAfter = await evalJson(ctx, RESOURCES);
  const tree2 = await callBidi('browsingContext.getTree', {});
  for (const c of tree2?.result?.contexts || []) flatten(c, 0, report.frames);

  await evalStr(ctx, '(() => { try { window.turnstile.remove(window.__probeWid); } catch {} try { document.getElementById("mint-ts")?.remove(); } catch {} window.__mintedToken = null; return "cleaned"; })()');

  const evNames = Array.isArray(report.widgetEvents) ? report.widgetEvents.map((e) => e.name + (e.data && e.name === 'error' ? ':' + e.data : '')) : [];
  if (report.tokenLen > 100) report.verdict = 'TOKEN_OK';
  else if (rend.ok && rend.value === 'NO_TS') report.verdict = 'NO_TS: Turnstile API never loaded in the donor page';
  else if (!rend.ok) report.verdict = 'RENDER_FAILED: ' + rend.err;
  else if (evNames.some((n) => n.startsWith('error'))) report.verdict = 'WIDGET_ERROR ' + evNames.filter((n) => n.startsWith('error')).join(',');
  else if (evNames.includes('before-interactive')) report.verdict = 'INTERACTION_REQUESTED_BUT_NOT_PASSED';
  else report.verdict = 'NO_TOKEN_NO_EVENT (widget silent)';
}

const hardStop = setTimeout(() => { report.verdict = (report.verdict || '') + ' [hard-stop 85s]'; finish(); }, 85000);

let finished = false;
async function finish() {
  if (finished) return;
  finished = true;
  clearTimeout(hardStop);
  try { if (ws && ws.readyState === 1) await callBidi('browser.close', {}); } catch {}
  try { ws?.close(); } catch {}
  report.elapsedMs = Date.now() - T0;
  save();
  const ev = Array.isArray(report.widgetEvents) ? report.widgetEvents : [];
  console.log(JSON.stringify({
    verdict: report.verdict,
    tokenLen: report.tokenLen,
    profile: report.profile,
    clickMode: report.clickMode,
    clicks: report.clicks,
    widgetEvents: ev.map((e) => `${e.t}ms ${e.name}${e.data ? '=' + e.data : ''}`),
    afterInit: report.pageState.afterInit,
    turnstileReadyWithinEngineWait: report.pageState.turnstileReadyWithinEngineWait,
    turnstileReadyLate: report.pageState.turnstileReadyLate,
    lastIter: report.iterations[report.iterations.length - 1] || null,
    frames: report.frames.length,
    turnstileConsole: report.console.filter((c) => /turnstile|cloudflare|challenge/i.test(c.text)).slice(0, 12).map((c) => `${c.t}ms [${c.level}] ${c.text.slice(0, 140)}`),
    report: path.basename(outJson),
    screenshots: report.screenshots.map((s) => s.file || `${s.label}:ERR`),
    elapsedMs: report.elapsedMs
  }));
  setTimeout(() => process.exit(0), 1500);
}

main()
  .catch((e) => { report.verdict = 'EXCEPTION: ' + String(e?.message || e).slice(0, 300); })
  .finally(finish);
