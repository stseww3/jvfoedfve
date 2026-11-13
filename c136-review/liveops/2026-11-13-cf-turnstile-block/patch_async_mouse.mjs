// Route A fix: let the donor's WebDriver clicks reach the cross-origin Turnstile iframe.
//
// Firefox dispatches a BiDi `input.performActions` mouse event inside the TARGET content process
// unless `remote.events.async.mouse.enabled` is true, in which case it goes through the top chrome
// window (see chrome/remote/content/webdriver-bidi/modules/root/input.sys.mjs #dispatchEvent and
// shared/webdriver/Actions.sys.mjs). The Turnstile checkbox is in a challenges.cloudflare.com
// iframe, a different process from the territorial.io page the engine clicks in, so with the
// default the click never lands on the checkbox and the solve times out whenever Cloudflare asks
// for interaction.
//
// The engine profile already sets the wheel variant of this pref but not the mouse one. Adding the
// mouse pref was enough in the cloud sandbox: with it on, the engine's existing blind-click loop
// obtained a token in under 1s (2/2 runs); with it off, 22 clicks produced nothing (2/2 runs).
//
// Run with the c116 dir as cwd:   node_apex.exe ..\c136\patch_async_mouse.mjs
// Takes effect on the next donor launch, because _initFirefoxDonor rewrites user.js each time.
import fs from 'node:fs';

const f = 'tsb-apex-squad.mjs';
let s = fs.readFileSync(f, 'utf8');
const cnt = (x) => s.split(x).length - 1;

if (cnt('remote.events.async.mouse.enabled') > 0) {
  console.log('ALREADY PATCHED: remote.events.async.mouse.enabled is present; no change.');
  process.exit(0);
}

const bak = f + '.bak-asyncmouse';
if (!fs.existsSync(bak)) fs.writeFileSync(bak, s);

// Anchor on the two adjacent lines of the ensureFirefoxProfile prefs template.
const anchor = 'user_pref("remote.events.async.wheel.enabled", true);\nuser_pref("browser.shell.checkDefaultBrowser", false);';
const n = cnt(anchor);
console.log('anchor count=' + n);
if (n !== 1) throw new Error('prefs-template anchor not unique: ' + n);

const replacement = 'user_pref("remote.events.async.wheel.enabled", true);\nuser_pref("remote.events.async.mouse.enabled", true);\nuser_pref("browser.shell.checkDefaultBrowser", false);';
s = s.replace(anchor, replacement);

fs.writeFileSync(f, s);
console.log('ASYNC-MOUSE OK | mouse-pref:' + cnt('remote.events.async.mouse.enabled') + ' | wheel-pref:' + cnt('remote.events.async.wheel.enabled') + ' | len:' + s.length);
