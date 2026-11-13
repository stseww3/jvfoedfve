// Compact donor verifier: one Firefox, one Turnstile solve, verdict + token length only.
// Engine-identical launch / preload / render / click. No screenshots. Token value never stored.
// Run with cwd = c116:  node_apex.exe ..\c136\cf_verify.mjs <port> <profileDir>
import fs from 'node:fs';
import path from 'node:path';
import { spawn } from 'node:child_process';

const port = Number(process.argv[2] || 9228);
const base = process.cwd();
const profDir = path.resolve(base, process.argv[3] || `firefox_donor_${port}`);
const ffExe = path.join(base, 'firefox_bin', 'firefox.exe');
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const out = { port, profile: path.basename(profDir), verdict: null, tokenLen: 0, events: [], steps: [], wd: null };

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
async function evalStr(ctx, expression, extra = {}) {
  const r = await call('script.evaluate', { expression, target: { context: ctx }, awaitPromise: false, ...extra });
  if (!r) return { ok: false, err: 'no-response' };
  if (r.type === 'error') return { ok: false, err: String(r.error) };
  if (r.result?.type === 'exception') return { ok: false, err: 'exception' };
  return { ok: true, value: r.result?.result?.value };
}

const PRELOAD = `() => { try { const o = { get webdriver() { return false; } }; Object.defineProperty(Navigator.prototype, 'webdriver', { get: Object.getOwnPropertyDescriptor(o, 'webdriver').get, enumerable: true, configurable: true }); } catch {} }`;
const RENDER = `(() => { const ev = (window.__pev = []); const p = (n, d) => ev.push(n + (d === undefined ? '' : '=' + d));
  try { if (typeof bX === 'object' && bX?.turnstile?.close) bX.turnstile.close(); } catch {}
  if (typeof b1 === 'object' && b1?.z?.close) b1.z.close(1, 3252);
  for (const el of Array.from(document.querySelectorAll('div'))) { if (el.id !== 'mint-ts' && el.style?.position === 'fixed' && (el.style?.zIndex === '100' || el.getBoundingClientRect().width === 300)) el.remove(); }
  window.__tok = null; const old = document.getElementById('mint-ts'); if (old) old.remove();
  const div = document.createElement('div'); div.id = 'mint-ts'; div.style.position = 'fixed'; div.style.left = '0'; div.style.top = '0'; div.style.zIndex = '2147483647'; document.body.appendChild(div);
  if (!window.turnstile || typeof window.turnstile.render !== 'function') { p('NO_TS'); return 'NO_TS'; }
  window.turnstile.render(div, { sitekey: '0x4AAAAAAEI8HZoG8nJMzxt1', action: 'enter_lobby', appearance: 'interaction-only',
    callback: (t) => { window.__tok = t; p('success', t ? t.length : 0); },
    'error-callback': (c) => { p('error', c); }, 'expired-callback': () => p('expired'),
    'before-interactive-callback': () => p('before-interactive'), 'after-interactive-callback': () => p('after-interactive') });
  p('rendered'); return 'RENDERED'; })()`;
const POLL = `JSON.stringify({ tok: (window.__tok || '').length, ev: window.__pev || [], rect: (() => { const d = document.getElementById('mint-ts'); const r = d && d.getBoundingClientRect(); return r ? [Math.round(r.width), Math.round(r.height)] : null; })() })`;
const CLICK = { actions: [{ type: 'pointer', id: 'm', parameters: { pointerType: 'mouse' }, actions: [
  { type: 'pointerMove', x: 180, y: 180, duration: 40 }, { type: 'pointerMove', x: 28, y: 32, duration: 70 },
  { type: 'pointerDown', button: 0 }, { type: 'pause', duration: 60 }, { type: 'pointerUp', button: 0 }] }] };

async function main() {
  if (!fs.existsSync(ffExe)) { out.verdict = 'ABORT: no firefox.exe (wrong cwd?)'; return; }
  if (!fs.existsSync(path.join(profDir, 'user.js'))) { out.verdict = 'ABORT: profile user.js missing'; return; }
  if (await connect().then((s) => { if (s) { try { s.close(); } catch {} return true; } return false; })) { out.verdict = `ABORT: BiDi already live on :${port}`; return; }
  out.mousePref = /remote\.events\.async\.mouse\.enabled",\s*true/.test(fs.readFileSync(path.join(profDir, 'user.js'), 'utf8'));
  try { fs.unlinkSync(path.join(profDir, 'parent.lock')); } catch {}
  try { fs.unlinkSync(path.join(profDir, '.startup-incomplete')); } catch {}
  const child = spawn(ffExe, ['-no-remote', '-profile', profDir, '--remote-debugging-port', String(port), 'https://territorial.io/'], { detached: true, stdio: 'ignore' });
  child.unref(); out.steps.push('spawned ' + child.pid);
  for (let i = 0; i < 18 && !ws; i++) { await sleep(1000); ws = await connect(); }
  if (!ws) { out.verdict = 'FAIL: BiDi not reachable in 18s'; return; }
  ws.addEventListener('message', (e) => { let m; try { m = JSON.parse(e.data); } catch { return; } if (m.id && pending.has(m.id)) { const f = pending.get(m.id); pending.delete(m.id); f(m); } });
  const sess = await call('session.new', { capabilities: {} });
  if (!sess?.result?.sessionId) { out.verdict = 'FAIL: session.new empty (BiDi session locked)'; return; }
  await call('script.addPreloadScript', { functionDeclaration: PRELOAD });
  const tree = await call('browsingContext.getTree', {});
  const top = tree?.result?.contexts?.find((c) => c.url?.includes('territorial.io')) || tree?.result?.contexts?.[0];
  const ctx = top?.context; if (!ctx) { out.verdict = 'FAIL: no context'; return; }
  await call('browsingContext.activate', { context: ctx });
  const wd = await evalStr(ctx, `String(navigator.webdriver) + ':' + String(typeof window.turnstile)`);
  if (!(wd.ok && String(wd.value).startsWith('false:object'))) { await call('browsingContext.reload', { context: ctx, wait: 'interactive' }); await sleep(3500); }
  out.wd = (await evalStr(ctx, 'String(navigator.webdriver)')).value;
  for (let w = 0; w < 12; w++) { const r = await evalStr(ctx, 'typeof window.turnstile?.render'); if (r.ok && r.value === 'function') break; await sleep(600); }
  const rend = await evalStr(ctx, RENDER, { userActivation: true });
  out.steps.push('render ' + (rend.ok ? rend.value : rend.err));
  for (let i = 0; i < 22; i++) {
    await sleep(650);
    const r = await evalStr(ctx, POLL); let st = {}; try { st = JSON.parse(r.value); } catch {}
    if (Array.isArray(st.ev)) out.events = st.ev;
    if (st.tok > 100) { out.tokenLen = st.tok; break; }
    await call('input.performActions', { context: ctx, ...CLICK });
  }
  await evalStr(ctx, '(() => { try { window.turnstile.remove(); } catch {} return 1; })()');
  if (out.tokenLen > 100) out.verdict = 'TOKEN_OK';
  else if (rend.ok && rend.value === 'NO_TS') out.verdict = 'NO_TS';
  else if (out.events.some((e) => e.startsWith('error'))) out.verdict = 'WIDGET_ERROR ' + out.events.filter((e) => e.startsWith('error')).join(',');
  else if (out.events.includes('before-interactive')) out.verdict = 'INTERACTION_REQUESTED_BUT_NOT_PASSED';
  else out.verdict = 'NO_TOKEN_NO_EVENT';
}

const hard = setTimeout(() => { out.verdict = (out.verdict || '') + ' [hardstop]'; done(); }, 80000);
let fin = false;
async function done() {
  if (fin) return; fin = true; clearTimeout(hard);
  try { if (ws && ws.readyState === 1) await call('browser.close', {}); } catch {}
  try { ws?.close(); } catch {}
  console.log(JSON.stringify(out));
  setTimeout(() => process.exit(0), 1200);
}
main().catch((e) => { out.verdict = 'EXCEPTION: ' + String(e?.message || e).slice(0, 200); }).finally(done);
