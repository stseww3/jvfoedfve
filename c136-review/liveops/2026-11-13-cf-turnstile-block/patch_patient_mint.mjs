// Patch tsb-apex-squad.mjs so token minting is reliable, bounded and stops hammering Cloudflare.
//
// What the logs and measurements on d3 showed (2026-11-14):
//   - old log: 18170 mint requests -> 1429 tokens, 12414 Firefox launches. Waves queued a new mint on
//     every donor every 8 s whether or not the donor was still busy, so requests waited past the bots'
//     90 s limit and were abandoned while the donor kept solving challenges nobody was waiting for.
//   - Turnstile's first challenge request downloads ~1.56 MB and the widget allows 5 s, then 10 s, then
//     ~15 s for it. Through the residential proxy a token took 47 s when it worked at all; over the
//     PC's own line it took 8 s with no click.
//
// What this changes (all inside tsb-apex-squad.mjs):
//   1. a mint waits up to 75 s for the token, and gives up at once when Turnstile reports an error
//   2. it clicks only when the widget really asks for interaction (no blind clicks); the profile pref
//      remote.events.async.mouse.enabled=true makes that click reach the checkbox iframe
//   3. a mint is never queued behind another one: each donor does one at a time, and at most
//      N run together (N = tsb-mint-parallel.txt, default 3 with the direct flag, else 1)
//   4. hard budget: at most CAP mint attempts per rolling 60 min (tsb-mint-hourly-cap.txt, default 90,
//      never above 100), remembered across restarts in tsb-mint-stamps.json; Turnstile's own automatic
//      retry is switched off so one attempt is exactly one challenge
//   5. the donor is chosen by health (fewest recent failures, least recently used); a donor that fails
//      3 times in a row is paused 5/10/15/20 min
//   6. no minting while the squad is in a match (the token would expire before it can be used)
//   7. a widget that gave no token is removed; Cloudflare's error code and each mint's duration are logged
//   8. flag file tsb-donor-direct.flag: donor Firefox profiles are written without the SOCKS proxy
//   9. a donor whose BiDi session cannot be created is relaunched at most twice in a row, not forever
//
// Run with cwd = c116:
//   node_apex.exe ..\c136\patch_patient_mint.mjs --dry     (writes a preview file, syntax-checks it)
//   node_apex.exe ..\c136\patch_patient_mint.mjs --apply   (backs up, then patches in place)
// Undo: copy tsb-apex-squad.mjs.bak-patientmint over tsb-apex-squad.mjs.
import fs from 'node:fs';
import path from 'node:path';
import { spawnSync } from 'node:child_process';

const mode = process.argv[2];
const target = path.resolve(process.argv[3] || 'tsb-apex-squad.mjs');
const report = { mode, target: path.basename(target), ok: false, steps: [] };
const finish = (msg) => { if (msg) report.error = msg; console.log(JSON.stringify(report)); process.exit(report.ok ? 0 : 1); };
if (mode !== '--dry' && mode !== '--apply') finish('usage: --dry | --apply [file]');

const raw = fs.readFileSync(target, 'utf8');
const crlf = (raw.match(/\r\n/g) || []).length;
const loneLf = (raw.match(/(?<!\r)\n/g) || []).length;
report.eol = { crlf, loneLf };
if (crlf > 0 && loneLf > 0) finish('mixed line endings; refusing to rewrite');
if (raw.includes('PATIENT-MINT')) finish('already patched (PATIENT-MINT marker present)');

let s = raw.replace(/\r\n/g, '\n');
function rep(name, anchor, replacement) {
  const n = s.split(anchor).length - 1;
  report.steps.push(`${name}:${n}`);
  if (n !== 1) finish(`anchor "${name}" found ${n} times, expected exactly 1`);
  s = s.replace(anchor, () => replacement);
}

if (!s.includes('remote.events.async.mouse.enabled')) {
  rep('pref-async-mouse',
    'user_pref("remote.events.async.wheel.enabled", true);\nuser_pref("browser.shell.checkDefaultBrowser", false);',
    'user_pref("remote.events.async.wheel.enabled", true);\nuser_pref("remote.events.async.mouse.enabled", true);\nuser_pref("browser.shell.checkDefaultBrowser", false);');
} else {
  report.steps.push('pref-async-mouse:already');
}

rep('direct-flag',
  '  const proxyPrefs = socksPort > 0 ? `\nuser_pref("network.proxy.type", 1);',
  '  const proxyPrefs = fs.existsSync(path.join(__dirname, \'tsb-donor-direct.flag\')) ? `\nuser_pref("network.proxy.type", 0);\n` : socksPort > 0 ? `\nuser_pref("network.proxy.type", 1);');

rep('relaunch-depth-signature',
  'async function _initFirefoxDonor(port = 9228) {\n',
  'async function _initFirefoxDonor(port = 9228, relaunchDepth = 0) {\n');

rep('relaunch-depth-limit',
  '    await new Promise((r) => setTimeout(r, 800));\n    return _initFirefoxDonor(port);\n',
  '    await new Promise((r) => setTimeout(r, 800));\n    if (relaunchDepth >= 2) throw new Error(`Firefox BiDi session.new keeps failing on port ${port}`);\n    return _initFirefoxDonor(port, relaunchDepth + 1);\n');

rep('helpers-and-entry',
  'async function mintViaDonorChrome(donorPort = 9228) {\n',
  `// PATIENT-MINT (2026-11-14): mints are never queued, run a few at a time on the healthiest donor,
// stay under an hourly budget, and a donor that keeps failing is paused instead of retried forever.
const MINT_DONOR_PORTS = [9228, 9229, 9230, 9231];
const donorMintInflight = new Map();
const donorFailStreak = new Map();
const donorCooldownUntil = new Map();
const donorLastUsedAt = new Map();
const mintStampFile = path.join(__dirname, 'tsb-mint-stamps.json');
let mintStamps = [];
try { mintStamps = JSON.parse(fs.readFileSync(mintStampFile, 'utf8')).filter((t) => typeof t === 'number'); } catch {}
let mintKnobCache = { at: 0, parallel: 1, cap: 90 };
let mintCapLoggedAt = 0;
function mintKnobs() {
  const now = Date.now();
  if (now - mintKnobCache.at < 5000) return mintKnobCache;
  const readInt = (name, lo, hi, dflt) => {
    try {
      const n = parseInt(fs.readFileSync(path.join(__dirname, name), 'utf8').trim(), 10);
      if (n >= lo && n <= hi) return n;
    } catch {}
    return dflt;
  };
  const direct = fs.existsSync(path.join(__dirname, 'tsb-donor-direct.flag'));
  mintKnobCache = { at: now, parallel: readInt('tsb-mint-parallel.txt', 1, 4, direct ? 3 : 1), cap: readInt('tsb-mint-hourly-cap.txt', 1, 100, 90) };
  return mintKnobCache;
}
function mintsLastHour() {
  const cut = Date.now() - 3600000;
  while (mintStamps.length && mintStamps[0] < cut) mintStamps.shift();
  return mintStamps.length;
}
function mintInflightTotal() {
  let n = 0;
  for (const v of donorMintInflight.values()) n += v;
  return n;
}
function usableMintDonors() {
  const now = Date.now();
  return MINT_DONOR_PORTS.filter((p) => !(donorMintInflight.get(p) > 0) && now >= (donorCooldownUntil.get(p) || 0));
}
function pickMintDonor() {
  const usable = usableMintDonors();
  if (!usable.length) return 0;
  usable.sort((a, b) => ((donorFailStreak.get(a) || 0) - (donorFailStreak.get(b) || 0)) || ((donorLastUsedAt.get(a) || 0) - (donorLastUsedAt.get(b) || 0)));
  return usable[0];
}
function mintSlotFree(alreadyPicked = 0) {
  const knobs = mintKnobs();
  if (mintInflightTotal() + alreadyPicked >= knobs.parallel) return false;
  if (usableMintDonors().length <= alreadyPicked) return false;
  if (mintsLastHour() + alreadyPicked >= knobs.cap) {
    if (Date.now() - mintCapLoggedAt > 300000) {
      mintCapLoggedAt = Date.now();
      console.log(\`[FIREFOX-DONOR] hourly Cloudflare budget used up (\${mintStamps.length}/\${knobs.cap} mints in the last 60 min) -> no new mint until the oldest one ages out\`);
    }
    return false;
  }
  return true;
}

async function mintViaDonorChrome(requestedDonorPort = 9228) {
  if (mintsLastHour() >= mintKnobs().cap) throw new Error('hourly Cloudflare budget used up');
  const donorPort = pickMintDonor();
  if (!donorPort) throw new Error('no donor free (all busy or paused)');
  const mintStartDelay = mintInflightTotal() * 2500;
  mintStamps.push(Date.now());
  try { fs.writeFileSync(mintStampFile, JSON.stringify(mintStamps)); } catch {}
  donorLastUsedAt.set(donorPort, Date.now());
  donorMintInflight.set(donorPort, (donorMintInflight.get(donorPort) || 0) + 1);
`);

rep('step-start',
  '  const doOne = async () => {\n    const donor = await ensureFirefoxDonor(donorPort);\n',
  '  const doOne = async () => {\n    const stepStartedAt = Date.now();\n    if (mintStartDelay) await new Promise((r) => setTimeout(r, mintStartDelay));\n    const donor = await ensureFirefoxDonor(donorPort);\n');

rep('render-state',
  '        window.__mintedToken = null;\n        const old = document.getElementById("mint-ts");\n',
  '        window.__mintedToken = null;\n        window.__mintErr = "";\n        window.__mintInteractive = 0;\n        const old = document.getElementById("mint-ts");\n');

rep('render-callbacks',
  '          appearance: "interaction-only",\n          callback: (tok) => {\n',
  '          appearance: "interaction-only",\n          retry: "never",\n          "error-callback": (code) => { window.__mintErr = String(code); return true; },\n          "timeout-callback": () => { window.__mintErr = "interactive-timeout"; },\n          "before-interactive-callback": () => { window.__mintInteractive = 1; },\n          callback: (tok) => {\n');

rep('widget-id',
  '        return "RENDERED:" + wid;\n',
  '        window.__mintWid = wid;\n        return "RENDERED:" + wid;\n');

rep('loop-head',
  `    for (let i = 0; i < 22; i++) {
      await new Promise((r) => setTimeout(r, 650));
      const check = await callBidi('script.evaluate', {
        expression: 'window.__mintedToken || ""',
`,
  `    const mintDeadline = Math.min(Date.now() + 75000, stepStartedAt + 86000);
    let lastMintClickAt = 0;
    let mintClicks = 0;
    let mintWidgetSince = 0;
    let mintErrNote = '';
    for (let i = 0; Date.now() < mintDeadline; i++) {
      await new Promise((r) => setTimeout(r, 650));
      const check = await callBidi('script.evaluate', {
        expression: 'JSON.stringify({ t: window.__mintedToken || "", w: Math.round(document.getElementById("mint-ts")?.firstElementChild?.getBoundingClientRect().width || 0), i: window.__mintInteractive || 0, e: window.__mintErr || "" })',
`);

rep('loop-token',
  `      const tok0 = check?.result?.result?.value || '';
      if (typeof tok0 === 'string' && tok0.length > 100) {
        donor._mintFailCount = 0;
        return tok0;
      }
      await callBidi('input.performActions', {
`,
  `      let mintSt = {};
      try { mintSt = JSON.parse(check?.result?.result?.value || '{}') || {}; } catch {}
      const tok0 = typeof mintSt.t === 'string' ? mintSt.t : '';
      if (tok0.length > 100) {
        donor._mintFailCount = 0;
        console.log(\`[FIREFOX-DONOR] mint ok on :\${donor.port} in \${Math.round((Date.now() - stepStartedAt) / 1000)}s (clicks=\${mintClicks}, \${mintStamps.length} mints in the last 60 min)\`);
        return tok0;
      }
      if (mintSt.e) { mintErrNote = String(mintSt.e).slice(0, 40); break; }
      if (!(mintSt.w >= 100)) { mintWidgetSince = 0; continue; }
      if (!mintWidgetSince) mintWidgetSince = Date.now();
      if (!mintSt.i && Date.now() - mintWidgetSince < 6000) continue;
      if (mintClicks >= 6 || Date.now() - lastMintClickAt < 2600) continue;
      lastMintClickAt = Date.now();
      mintClicks++;
      await callBidi('input.performActions', {
`);

rep('click-shape',
  `              { type: 'pointerMove', x: 180, y: 180, duration: 40 },
              { type: 'pointerMove', x: 28, y: 32, duration: 70 },
              { type: 'pointerDown', button: 0 },
`,
  `              { type: 'pointerMove', x: 66 + 2 * (mintClicks % 3), y: 62, duration: 120 },
              { type: 'pointerMove', x: 26 + 2 * (mintClicks % 3), y: 32, duration: 260 },
              { type: 'pause', duration: 90 },
              { type: 'pointerDown', button: 0 },
`);

rep('loop-fail',
  '    donor._mintFailCount = (donor._mintFailCount || 0) + 1;\n    if (donor._mintFailCount >= 5) {\n',
  `    try {
      await callBidi('script.evaluate', {
        expression: '(() => { try { if (window.__mintWid) window.turnstile.remove(window.__mintWid); } catch {} try { document.getElementById("mint-ts")?.remove(); } catch {} window.__mintWid = null; return "CLEANED"; })()',
        target: { context: ctx },
        awaitPromise: false
      });
    } catch {}
    console.log(\`[FIREFOX-DONOR] mint gave no token on :\${donor.port} after \${Math.round((Date.now() - stepStartedAt) / 1000)}s (clicks=\${mintClicks}\${mintErrNote ? ', cf_error=' + mintErrNote : ', no answer from the widget'})\`);
    donor._mintFailCount = (donor._mintFailCount || 0) + 1;
    if (donor._mintFailCount >= 5) {
`);

rep('fail-message',
  "    throw new Error('Firefox BiDi mint timeout');\n",
  "    throw new Error(mintErrNote ? 'Turnstile error ' + mintErrNote : 'Firefox BiDi mint timeout');\n");

rep('step-timeout',
  "new Promise((_, rej) => setTimeout(() => rej(new Error('donor chain step 35s timeout')), 35000))",
  "new Promise((_, rej) => setTimeout(() => rej(new Error('donor chain step 92s timeout')), 92000))");

rep('bookkeeping',
  `  donorMintChains.set(donorPort, next.catch(() => {}));
  return next;
}
`,
  `  donorMintChains.set(donorPort, next.catch(() => {}));
  next.then(
    () => { donorFailStreak.set(donorPort, 0); },
    (err) => {
      const streak = (donorFailStreak.get(donorPort) || 0) + 1;
      donorFailStreak.set(donorPort, streak);
      if (streak >= 3) {
        const pauseMin = Math.min(streak - 2, 4) * 5;
        donorCooldownUntil.set(donorPort, Date.now() + pauseMin * 60000);
        console.log(\`[FIREFOX-DONOR] \${streak} mint failures in a row on :\${donorPort} (last: \${String(err?.message || err).slice(0, 60)}) -> pausing this donor \${pauseMin} min\`);
      }
    }
  ).finally(() => {
    donorMintInflight.set(donorPort, Math.max(0, (donorMintInflight.get(donorPort) || 0) - 1));
  });
  return next;
}
`);

rep('wave-ingame',
  '  const perDonorCnt = new Map();\n  const needReload = [];\n',
  '  const perDonorCnt = new Map();\n  const needReload = [];\n  const squadInGameNow = states.some((s) => !!s?.inGame);\n');

rep('wave-gate',
  '    const cur = perDonorCnt.get(dp) || 0;\n    if (cur < 1) {\n',
  '    const cur = perDonorCnt.get(dp) || 0;\n    if (!squadInGameNow && mintSlotFree(needReload.length)) {\n');

const out = crlf > 0 ? s.replace(/\n/g, '\r\n') : s;
report.sizeBefore = raw.length;
report.sizeAfter = out.length;

const check = (file) => {
  const r = spawnSync(process.execPath, ['--check', file], { encoding: 'utf8' });
  return r.status === 0 ? 'OK' : ('FAIL: ' + String(r.stderr || r.stdout || r.error || '').slice(0, 400));
};

if (mode === '--dry') {
  const preview = target.replace(/\.mjs$/, '.preview-patientmint.mjs');
  fs.writeFileSync(preview, out, 'utf8');
  report.syntax = check(preview);
  report.preview = path.basename(preview);
  report.ok = report.syntax === 'OK';
  finish();
}

const backup = target + '.bak-patientmint';
if (!fs.existsSync(backup)) fs.copyFileSync(target, backup);
report.backup = path.basename(backup);
const tmp = target.replace(/\.mjs$/, '.tmp-patientmint.mjs');
fs.writeFileSync(tmp, out, 'utf8');
report.syntax = check(tmp);
if (report.syntax !== 'OK') { fs.unlinkSync(tmp); finish('patched file fails syntax check; original left untouched'); }
fs.renameSync(tmp, target);
report.ok = true;
finish();
