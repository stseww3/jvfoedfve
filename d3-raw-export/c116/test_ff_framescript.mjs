import fs from 'node:fs';
import path from 'node:path';
import http from 'node:http';
import { spawn } from 'node:child_process';

const ffDir = path.resolve('firefox_bin');
const prefDir = path.join(ffDir, 'defaults', 'pref');
fs.mkdirSync(prefDir, { recursive: true });

// 1. Write defaults/pref/autoconfig.js
fs.writeFileSync(
  path.join(prefDir, 'autoconfig.js'),
  `pref("general.config.filename", "firefox.cfg");\npref("general.config.obscure_value", 0);\npref("general.config.sandbox_enabled", false);\n`,
  'utf8'
);

// 2. Write profile user.js with mixed_content & csp disabled and focusmanager.testmode enabled
const profDir = path.resolve('firefox_donor_9228');
fs.mkdirSync(profDir, { recursive: true });
fs.writeFileSync(
  path.join(profDir, 'user.js'),
  `user_pref("browser.shell.checkDefaultBrowser", false);
user_pref("datareporting.policy.dataSubmissionEnabled", false);
user_pref("toolkit.telemetry.reportingpolicy.firstRun", false);
user_pref("browser.startup.homepage_override.mstone", "ignore");
user_pref("browser.aboutwelcome.enabled", false);
user_pref("trailhead.firstrun.didSeeAboutWelcome", true);
user_pref("focusmanager.testmode", true);
user_pref("security.mixed_content.block_active_content", false);
user_pref("security.mixed_content.block_display_content", false);
user_pref("security.csp.enable", false);
user_pref("network.websocket.allowInsecureFromHTTPS", true);
`,
  'utf8'
);

// 3. Write Frame Script inside firefox.cfg
const frameScript = `
(function() {
  const { setInterval, clearInterval, setTimeout } = ChromeUtils.importESModule("resource://gre/modules/Timer.sys.mjs");
  let hookedWin = null;
  let mintBusy = false;

  setInterval(() => {
    try {
      const win = content;
      if (!win || !win.location || !String(win.location.href).startsWith("https://territorial.io")) return;
      const uw = win.wrappedJSObject || win;
      if (!uw || !uw.document || !uw.document.body) return;

      // Keep game/lobby silenced in Donor Firefox
      try {
        if (uw.bX && uw.bX.turnstile && typeof uw.bX.turnstile.close === "function") {
          uw.bX.turnstile.close();
        }
      } catch {}

      if (mintBusy) return;
      const xhr = new win.XMLHttpRequest();
      xhr.open("GET", "http://127.0.0.1:8297/ff-donor-work?webdriver=" + String(uw.navigator.webdriver) + "&hasTs=" + String(typeof uw.turnstile), true);
      xhr.onload = function() {
        try {
          const resp = JSON.parse(xhr.responseText || "{}");
          if (!resp.wantToken || mintBusy) return;
          if (typeof uw.turnstile !== "object" || !uw.turnstile.render) return;
          mintBusy = true;

          // Inject page-context script to render Turnstile cleanly in page realm
          const s = uw.document.createElement("script");
          s.textContent = \`(() => {
            window.__mintedToken = null;
            const old = document.getElementById("mint-ts");
            if (old) old.remove();
            const d = document.createElement("div");
            d.id = "mint-ts";
            d.style.position = "fixed";
            d.style.left = "0";
            d.style.top = "0";
            d.style.zIndex = "99999";
            document.body.appendChild(d);
            const wid = window.turnstile.render(d, {
              sitekey: "0x4AAAAAAEI8HZoG8nJMzxt1",
              action: "enter_lobby",
              appearance: "interaction-only",
              callback: (tok) => {
                window.__mintedToken = tok;
                try { window.turnstile.remove(wid); d.remove(); } catch {}
              }
            });
            window.__mintWid = wid;
          })()\`;
          uw.document.body.appendChild(s);
          s.remove();

          let step = 0;
          const pollTimer = setInterval(() => {
            step++;
            const tok = uw.__mintedToken || "";
            if (typeof tok === "string" && tok.length > 100) {
              clearInterval(pollTimer);
              mintBusy = false;
              const postXhr = new win.XMLHttpRequest();
              postXhr.open("POST", "http://127.0.0.1:8297/ff-donor-token", true);
              postXhr.setRequestHeader("Content-Type", "application/json");
              postXhr.send(JSON.stringify({ token: tok }));
              return;
            }
            if (step >= 20) {
              clearInterval(pollTimer);
              mintBusy = false;
              return;
            }
            try {
              const utils = win.windowUtils;
              if (utils) {
                utils.sendMouseEvent("mousemove", 180, 180, 0, 0, 0);
                utils.sendMouseEvent("mousemove", 28, 32, 0, 0, 0);
                utils.sendMouseEvent("mousedown", 28, 32, 0, 1, 0);
                utils.sendMouseEvent("mouseup", 28, 32, 0, 1, 0);
              }
            } catch {}
          }, 600);
        } catch {
          mintBusy = false;
        }
      };
      xhr.onerror = function() {};
      xhr.send();
    } catch {}
  }, 600);
})();
`;

const cfgCode = `// Mozilla AutoConfig
try {
  const { Services } = ChromeUtils.importESModule("resource://gre/modules/Services.sys.mjs");
  const scriptUrl = "data:application/javascript," + encodeURIComponent(${JSON.stringify(frameScript)});
  Services.mm.loadFrameScript(scriptUrl, true);
} catch (e) {}
`;

fs.writeFileSync(path.join(ffDir, 'firefox.cfg'), cfgCode, 'utf8');
console.log('Configured firefox.cfg with Services.mm.loadFrameScript!');

// 4. Start a test HTTP server on :8297 and launch Firefox WITHOUT --remote-debugging-port!
let wantToken = true;
const srv = http.createServer((req, res) => {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Headers', '*');
  if (req.method === 'OPTIONS') { res.writeHead(200); res.end(); return; }
  if (req.url.startsWith('/ff-donor-work')) {
    console.log('[FF-POLL]', req.url);
    const u = new URL(req.url, 'http://127.0.0.1:8297');
    const hasTs = u.searchParams.get('hasTs') === 'object';
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ wantToken: wantToken && hasTs }));
    if (wantToken && hasTs) wantToken = false;
    return;
  }
  if (req.url === '/ff-donor-token' && req.method === 'POST') {
    let body = '';
    req.on('data', (c) => body += c);
    req.on('end', () => {
      const data = JSON.parse(body);
      console.log('SUCCESS! Minted token from pure Firefox (webdriver=false)! len=' + data.token.length + ' prefix=' + data.token.slice(0, 40));
      res.writeHead(200);
      res.end('OK');
      setTimeout(() => process.exit(0), 200);
    });
    return;
  }
  res.writeHead(404);
  res.end();
});

srv.listen(8297, '127.0.0.1', () => {
  console.log('Test server listening on 127.0.0.1:8297');
});
