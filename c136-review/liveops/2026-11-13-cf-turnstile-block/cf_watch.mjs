// Diagnostic watcher: render the enter_lobby Turnstile widget and WATCH for up to <waitSec> seconds
// WITHOUT clicking. Captures the widget callbacks, the Cloudflare console lines, the challenge
// iframe's resource timing, and the frame tree, so we can tell apart "silent pass eventually",
// "challenge error", and "truly stuck". Token value is never stored, only its length.
// Also records: page visibility + requestAnimationFrame rate (is the window actually being painted?),
// the OS window state, and every request to a Cloudflare host with its outcome (which one hangs?).
// Optional 4th arg "click": once the widget asks for interaction, click the checkbox (max 4 tries).
// Run with cwd = c116:  node_apex.exe ..\c136\cf_watch.mjs <port> <profileDir> <waitSec> [click]
import fs from 'node:fs';
import path from 'node:path';
import { spawn } from 'node:child_process';

const port = Number(process.argv[2] || 9228);
const base = process.cwd();
const profDir = path.resolve(base, process.argv[3] || `firefox_donor_${port}`);
const waitSec = Number(process.argv[4] || 60);
const doClick = process.argv[5] === 'click';
const ffExe = path.join(base, 'firefox_bin', 'firefox.exe');
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const T0 = Date.now();
const out = { port, profile: path.basename(profDir), waitSec, verdict: null, tokenLen: 0, events: [], timeline: [], cfConsole: [], cfResources: [], frames: [], wd: null, win: null, net: [], netSummary: null, iframeVis: [], clicks: 0 };
const reqs = new Map();
const shortUrl = (u) => { try { const x = new URL(u); return x.host.replace('.challenges.cloudflare.com', '.ch.cf').replace('challenges.cloudflare.com', 'ch.cf') + x.pathname.slice(0, 46); } catch { return String(u).slice(0, 60); } };

let ws = null, seq = 0;
const pending = new Map();
const connect = () => new Promise((res) => {
  let s; try { s = new WebSocket(`ws://127.0.0.1:${port}/session`); } catch { return res(null); }
  const t = setTimeout(() => { try { s.close(); } catch {} res(null); }, 3000);
  s.addEventListener('open', () => { clearTimeout(t); res(s); });
  s.addEventListener('error', () => { clearTimeout(t); res(null); });
});
const call = (method, params = {}) => new Promise((res) => {
  if (!ws || ws.readyState !== 1) return res(null);
  const id = ++seq;
  const tm = setTimeout(() => { pending.delete(id); res(null); }, 8000);
  pending.set(id, (m) => { clearTimeout(tm); res(m); });
  ws.send(JSON.stringify({ id, method, params }));
});
async function ev(ctx, expression, extra = {}) {
  const r = await call('script.evaluate', { expression, target: { context: ctx }, awaitPromise: false, ...extra });
  if (!r) return { ok: false };
  if (r.type === 'error' || r.result?.type === 'exception') return { ok: false };
  return { ok: true, value: r.result?.result?.value };
}

const PRELOAD = `() => { try { const o = { get webdriver() { return false; } }; Object.defineProperty(Navigator.prototype, 'webdriver', { get: Object.getOwnPropertyDescriptor(o, 'webdriver').get, enumerable: true, configurable: true }); } catch {} }`;
const RENDER = `(() => { const e = (window.__pev = []); const t0 = performance.now(); const p = (n, d) => e.push(Math.round(performance.now() - t0) + ':' + n + (d === undefined ? '' : '=' + d));
  try { if (typeof bX === 'object' && bX?.turnstile?.close) bX.turnstile.close(); } catch {}
  if (typeof b1 === 'object' && b1?.z?.close) b1.z.close(1, 3252);
  for (const el of Array.from(document.querySelectorAll('div'))) { if (el.id !== 'mint-ts' && el.style?.position === 'fixed' && (el.style?.zIndex === '100' || el.getBoundingClientRect().width === 300)) el.remove(); }
  window.__tok = null; const old = document.getElementById('mint-ts'); if (old) old.remove();
  if (!window.__rafOn) { window.__rafOn = 1; window.__raf = 0; const rf = () => { window.__raf++; requestAnimationFrame(rf); }; requestAnimationFrame(rf); }
  const div = document.createElement('div'); div.id = 'mint-ts'; div.style.position = 'fixed'; div.style.left = '0'; div.style.top = '0'; div.style.zIndex = '2147483647'; document.body.appendChild(div);
  if (!window.turnstile || typeof window.turnstile.render !== 'function') { p('NO_TS'); return 'NO_TS'; }
  window.turnstile.render(div, { sitekey: '0x4AAAAAAEI8HZoG8nJMzxt1', action: 'enter_lobby', appearance: 'interaction-only',
    callback: (t) => { window.__tok = t; p('success', t ? t.length : 0); },
    'error-callback': (c) => p('error', c), 'expired-callback': () => p('expired'), 'timeout-callback': () => p('timeout'),
    'before-interactive-callback': () => p('before-interactive'), 'after-interactive-callback': () => p('after-interactive') });
  p('rendered'); return 'RENDERED'; })()`;
const POLL = `JSON.stringify({ tok: (window.__tok || '').length, ev: window.__pev || [], raf: window.__raf || 0, vis: document.visibilityState, foc: document.hasFocus(), rect: (() => { const d = document.getElementById('mint-ts'); const r = d && d.firstElementChild && d.firstElementChild.getBoundingClientRect(); return r ? [Math.round(r.width), Math.round(r.height)] : null; })() })`;
const RES = `JSON.stringify(performance.getEntriesByType('resource').filter((e) => e.name.includes('challenges.cloudflare.com')).map((e) => e.name.slice(0, 95) + ' [' + Math.round(e.startTime) + '+' + Math.round(e.duration) + 'ms st=' + e.responseStatus + ']'))`;

async function main() {
  if (!fs.existsSync(ffExe)) { out.verdict = 'ABORT: no firefox.exe'; return; }
  if (!fs.existsSync(path.join(profDir, 'user.js'))) { out.verdict = 'ABORT: profile user.js missing'; return; }
  if (await connect().then((s) => { if (s) { try { s.close(); } catch {} return true; } return false; })) { out.verdict = `ABORT: BiDi already live on :${port}`; return; }
  try { fs.unlinkSync(path.join(profDir, 'parent.lock')); } catch {}
  try { fs.unlinkSync(path.join(profDir, '.startup-incomplete')); } catch {}
  const child = spawn(ffExe, ['-no-remote', '-profile', profDir, '--remote-debugging-port', String(port), 'https://territorial.io/'], { detached: true, stdio: 'ignore' });
  child.unref();
  for (let i = 0; i < 18 && !ws; i++) { await sleep(1000); ws = await connect(); }
  if (!ws) { out.verdict = 'FAIL: BiDi not reachable in 18s'; return; }
  ws.addEventListener('message', (e) => { let m; try { m = JSON.parse(e.data); } catch { return; } if (m.id && pending.has(m.id)) { const f = pending.get(m.id); pending.delete(m.id); f(m); } else if (m.method === 'network.beforeRequestSent') { const u = String(m.params?.request?.url || ''); if (u.includes('cloudflare') && reqs.size < 400) reqs.set(m.params.request.request, { u: shortUrl(u), t0: Date.now() - T0, m: m.params.request.method, up: m.params.request.bodySize }); } else if (m.method === 'network.responseCompleted') { const r = reqs.get(m.params?.request?.request); if (r) { r.st = m.params?.response?.status; r.dur = Date.now() - T0 - r.t0; r.down = m.params?.response?.bytesReceived; r.proto = m.params?.response?.protocol; const tm = m.params?.request?.timings; if (tm && tm.requestTime) { const d = (a, b) => (tm[a] > 0 && tm[b] > 0 ? Math.round(tm[b] - tm[a]) : -1); r.tm = `conn=${d('connectStart', 'connectEnd')} tls=${d('tlsStart', 'tlsEnd')} send>first=${d('requestStart', 'responseStart')} recv=${d('responseStart', 'responseEnd')}`; } } } else if (m.method === 'network.fetchError') { const r = reqs.get(m.params?.request?.request); if (r) { r.err = String(m.params?.errorText || 'error').slice(0, 40); r.dur = Date.now() - T0 - r.t0; } } else if (m.method === 'log.entryAdded') { const t = String(m.params?.text || ''); if (/turnstile|cloudflare|challenge/i.test(t) && out.cfConsole.length < 120) out.cfConsole.push((Date.now() - T0) + 'ms[' + m.params?.level + '] ' + t.slice(0, 180)); } });
  const sess = await call('session.new', { capabilities: {} });
  if (!sess?.result?.sessionId) { out.verdict = 'FAIL: session.new empty (BiDi locked)'; return; }
  await call('session.subscribe', { events: ['log.entryAdded', 'network.beforeRequestSent', 'network.responseCompleted', 'network.fetchError'] });
  await call('script.addPreloadScript', { functionDeclaration: PRELOAD });
  const tree = await call('browsingContext.getTree', {});
  const top = tree?.result?.contexts?.find((c) => c.url?.includes('territorial.io')) || tree?.result?.contexts?.[0];
  const ctx = top?.context; if (!ctx) { out.verdict = 'FAIL: no context'; return; }
  await call('browsingContext.activate', { context: ctx });
  const cw = await call('browser.getClientWindows', {});
  out.win = (cw?.result?.clientWindows || []).map((w) => `${w.state}${w.active ? '/active' : '/inactive'} ${w.width}x${w.height}@${w.x},${w.y}`).join(' ; ') || 'n/a';
  const wd = await ev(ctx, `String(navigator.webdriver) + ':' + String(typeof window.turnstile)`);
  if (!(wd.ok && String(wd.value).startsWith('false:object'))) { await call('browsingContext.reload', { context: ctx, wait: 'interactive' }); await sleep(3500); }
  out.wd = (await ev(ctx, 'String(navigator.webdriver)')).value;
  for (let w = 0; w < 12; w++) { const r = await ev(ctx, 'typeof window.turnstile?.render'); if (r.ok && r.value === 'function') break; await sleep(600); }
  const rend = await ev(ctx, RENDER, { userActivation: true });
  out.rendered = rend.ok ? rend.value : 'render-failed';
  const loops = Math.ceil(waitSec);
  let lastRaf = 0, lastRafS = 0, lastClick = 0;
  for (let i = 0; i < loops; i++) {
    await sleep(1000);
    const r = await ev(ctx, POLL); let st = {}; try { st = JSON.parse(r.value); } catch {}
    if (Array.isArray(st.ev)) out.events = st.ev;
    if (i % 5 === 0 || (st.tok > 100)) { out.timeline.push({ s: i + 1, tok: st.tok, rect: st.rect, ev: (st.ev || []).length, vis: st.vis, foc: st.foc, rafPerSec: Math.round(((st.raf || 0) - lastRaf) / Math.max(1, i + 1 - lastRafS)) }); lastRaf = st.raf || 0; lastRafS = i + 1; }
    if (st.tok > 100) { out.tokenLen = st.tok; break; }
    if (doClick && out.clicks < 4 && (st.ev || []).some((e) => e.includes(':before-interactive')) && st.rect && st.rect[0] > 100 && Date.now() - lastClick > 2600) {
      lastClick = Date.now(); out.clicks++;
      const x = 26 + out.clicks * 2, y = Math.round(st.rect[1] / 2);
      await call('input.performActions', { context: ctx, actions: [{ type: 'pointer', id: 'm1', parameters: { pointerType: 'mouse' }, actions: [{ type: 'pointerMove', x: x + 40, y: y + 30, duration: 120 }, { type: 'pointerMove', x, y, duration: 260 }, { type: 'pause', duration: 90 }, { type: 'pointerDown', button: 0 }, { type: 'pause', duration: 70 }, { type: 'pointerUp', button: 0 }] }] });
      await call('input.releaseActions', { context: ctx });
    }
  }
  out.cfResources = JSON.parse((await ev(ctx, RES)).value || '[]');
  const tree2 = await call('browsingContext.getTree', {});
  const walk = (c, d = 0) => { out.frames.push(d + ':' + String(c.url || '').slice(0, 90)); (c.children || []).forEach((k) => walk(k, d + 1)); };
  (tree2?.result?.contexts || []).forEach((c) => walk(c, 0));
  const kids = []; const coll = (c) => { (c.children || []).forEach((k) => { kids.push(k); coll(k); }); }; (tree2?.result?.contexts || []).forEach(coll);
  for (const k of kids.slice(0, 3)) {
    const r = await call('script.evaluate', { expression: `new Promise((res) => { let n = 0; const f = () => { n++; requestAnimationFrame(f); }; requestAnimationFrame(f); setTimeout(() => res(document.visibilityState + ' focus=' + document.hasFocus() + ' rafPerSec=' + n + ' inner=' + innerWidth + 'x' + innerHeight), 1000); })`, target: { context: k.context, sandbox: 'probe' }, awaitPromise: true });
    out.iframeVis.push(String(r?.result?.result?.value ?? r?.result?.type ?? r?.error ?? 'n/a'));
  }
  const all = Array.from(reqs.values());
  out.netSummary = { total: all.length, ok: all.filter((r) => r.st >= 200 && r.st < 400).length, http4xx5xx: all.filter((r) => r.st >= 400).length, errors: all.filter((r) => r.err).length, pending: all.filter((r) => r.st === undefined && !r.err).length, slowOver3s: all.filter((r) => (r.dur || 0) > 3000).length };
  const interesting = all.filter((r) => r.err || r.st === undefined || r.st >= 400 || (r.dur || 0) > 3000);
  const pick = interesting.concat(all.filter((r) => !interesting.includes(r))).slice(0, 45).sort((a, b) => a.t0 - b.t0);
  out.net = pick.map((r) => `${r.t0}ms ${r.m} ${r.u} -> ${r.err ? 'ERR ' + r.err : (r.st === undefined ? 'PENDING' : r.st)} ${r.dur === undefined ? '' : r.dur + 'ms'}${r.up ? ' up=' + r.up + 'B' : ''}${r.down ? ' down=' + r.down + 'B' : ''}${r.proto ? ' ' + r.proto : ''}${r.tm ? ' [' + r.tm + ']' : ''}`);
  if (out.tokenLen > 100) out.verdict = 'TOKEN_OK';
  else if (out.rendered === 'NO_TS') out.verdict = 'NO_TS';
  else if (out.events.some((e) => e.includes(':error'))) out.verdict = 'WIDGET_ERROR';
  else if (out.events.some((e) => e.includes(':timeout'))) out.verdict = 'WIDGET_TIMEOUT';
  else if (out.events.some((e) => e.includes(':before-interactive'))) out.verdict = 'INTERACTION_REQUESTED (not clicked)';
  else out.verdict = 'SILENT (rendered, no callback in ' + waitSec + 's)';
}

const hard = setTimeout(() => { out.verdict = (out.verdict || '') + ' [hardstop]'; done(); }, (waitSec + 34) * 1000);
let fin = false;
async function done() {
  if (fin) return; fin = true; clearTimeout(hard);
  try { if (ws && ws.readyState === 1) await call('browser.close', {}); } catch {}
  try { ws?.close(); } catch {}
  out.elapsedMs = Date.now() - T0;
  console.log(JSON.stringify(out).replace(/[^\x20-\x7e]/g, '?'));
  setTimeout(() => process.exit(0), 1200);
}
main().catch((e) => { out.verdict = 'EXCEPTION: ' + String(e?.message || e).slice(0, 200); }).finally(done);
