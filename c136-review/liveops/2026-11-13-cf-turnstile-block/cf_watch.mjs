// Diagnostic watcher: render the enter_lobby Turnstile widget and WATCH for up to <waitSec> seconds
// WITHOUT clicking. Captures the widget callbacks, the Cloudflare console lines, the challenge
// iframe's resource timing, and the frame tree, so we can tell apart "silent pass eventually",
// "challenge error", and "truly stuck". Token value is never stored, only its length.
// Run with cwd = c116:  node_apex.exe ..\c136\cf_watch.mjs <port> <profileDir> <waitSec>
import fs from 'node:fs';
import path from 'node:path';
import { spawn } from 'node:child_process';

const port = Number(process.argv[2] || 9228);
const base = process.cwd();
const profDir = path.resolve(base, process.argv[3] || `firefox_donor_${port}`);
const waitSec = Number(process.argv[4] || 60);
const ffExe = path.join(base, 'firefox_bin', 'firefox.exe');
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const T0 = Date.now();
const out = { port, profile: path.basename(profDir), waitSec, verdict: null, tokenLen: 0, events: [], timeline: [], cfConsole: [], cfResources: [], frames: [], wd: null };

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
  const div = document.createElement('div'); div.id = 'mint-ts'; div.style.position = 'fixed'; div.style.left = '0'; div.style.top = '0'; div.style.zIndex = '2147483647'; document.body.appendChild(div);
  if (!window.turnstile || typeof window.turnstile.render !== 'function') { p('NO_TS'); return 'NO_TS'; }
  window.turnstile.render(div, { sitekey: '0x4AAAAAAEI8HZoG8nJMzxt1', action: 'enter_lobby', appearance: 'interaction-only',
    callback: (t) => { window.__tok = t; p('success', t ? t.length : 0); },
    'error-callback': (c) => p('error', c), 'expired-callback': () => p('expired'), 'timeout-callback': () => p('timeout'),
    'before-interactive-callback': () => p('before-interactive'), 'after-interactive-callback': () => p('after-interactive') });
  p('rendered'); return 'RENDERED'; })()`;
const POLL = `JSON.stringify({ tok: (window.__tok || '').length, ev: window.__pev || [], rect: (() => { const d = document.getElementById('mint-ts'); const r = d && d.firstElementChild && d.firstElementChild.getBoundingClientRect(); return r ? [Math.round(r.width), Math.round(r.height)] : null; })() })`;
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
  ws.addEventListener('message', (e) => { let m; try { m = JSON.parse(e.data); } catch { return; } if (m.id && pending.has(m.id)) { const f = pending.get(m.id); pending.delete(m.id); f(m); } else if (m.method === 'log.entryAdded') { const t = String(m.params?.text || ''); if (/turnstile|cloudflare|challenge/i.test(t) && out.cfConsole.length < 120) out.cfConsole.push((Date.now() - T0) + 'ms[' + m.params?.level + '] ' + t.slice(0, 180)); } });
  const sess = await call('session.new', { capabilities: {} });
  if (!sess?.result?.sessionId) { out.verdict = 'FAIL: session.new empty (BiDi locked)'; return; }
  await call('session.subscribe', { events: ['log.entryAdded'] });
  await call('script.addPreloadScript', { functionDeclaration: PRELOAD });
  const tree = await call('browsingContext.getTree', {});
  const top = tree?.result?.contexts?.find((c) => c.url?.includes('territorial.io')) || tree?.result?.contexts?.[0];
  const ctx = top?.context; if (!ctx) { out.verdict = 'FAIL: no context'; return; }
  await call('browsingContext.activate', { context: ctx });
  const wd = await ev(ctx, `String(navigator.webdriver) + ':' + String(typeof window.turnstile)`);
  if (!(wd.ok && String(wd.value).startsWith('false:object'))) { await call('browsingContext.reload', { context: ctx, wait: 'interactive' }); await sleep(3500); }
  out.wd = (await ev(ctx, 'String(navigator.webdriver)')).value;
  for (let w = 0; w < 12; w++) { const r = await ev(ctx, 'typeof window.turnstile?.render'); if (r.ok && r.value === 'function') break; await sleep(600); }
  const rend = await ev(ctx, RENDER, { userActivation: true });
  out.rendered = rend.ok ? rend.value : 'render-failed';
  const loops = Math.ceil(waitSec);
  for (let i = 0; i < loops; i++) {
    await sleep(1000);
    const r = await ev(ctx, POLL); let st = {}; try { st = JSON.parse(r.value); } catch {}
    if (Array.isArray(st.ev)) out.events = st.ev;
    if (i % 5 === 0 || (st.tok > 100)) out.timeline.push({ s: i + 1, tok: st.tok, rect: st.rect, ev: (st.ev || []).length });
    if (st.tok > 100) { out.tokenLen = st.tok; break; }
  }
  out.cfResources = JSON.parse((await ev(ctx, RES)).value || '[]');
  const tree2 = await call('browsingContext.getTree', {});
  const walk = (c, d = 0) => { out.frames.push(d + ':' + String(c.url || '').slice(0, 90)); (c.children || []).forEach((k) => walk(k, d + 1)); };
  (tree2?.result?.contexts || []).forEach((c) => walk(c, 0));
  if (out.tokenLen > 100) out.verdict = 'TOKEN_OK';
  else if (out.rendered === 'NO_TS') out.verdict = 'NO_TS';
  else if (out.events.some((e) => e.includes(':error'))) out.verdict = 'WIDGET_ERROR';
  else if (out.events.some((e) => e.includes(':timeout'))) out.verdict = 'WIDGET_TIMEOUT';
  else if (out.events.some((e) => e.includes(':before-interactive'))) out.verdict = 'INTERACTION_REQUESTED (not clicked)';
  else out.verdict = 'SILENT (rendered, no callback in ' + waitSec + 's)';
}

const hard = setTimeout(() => { out.verdict = (out.verdict || '') + ' [hardstop]'; done(); }, (waitSec + 30) * 1000);
let fin = false;
async function done() {
  if (fin) return; fin = true; clearTimeout(hard);
  try { if (ws && ws.readyState === 1) await call('browser.close', {}); } catch {}
  try { ws?.close(); } catch {}
  out.elapsedMs = Date.now() - T0;
  console.log(JSON.stringify(out));
  setTimeout(() => process.exit(0), 1200);
}
main().catch((e) => { out.verdict = 'EXCEPTION: ' + String(e?.message || e).slice(0, 200); }).finally(done);
