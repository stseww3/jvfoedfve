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

// 2. Write firefox_bin/firefox.cfg
const cfgCode = `// Mozilla AutoConfig
try {
  const { Services } = ChromeUtils.importESModule("resource://gre/modules/Services.sys.mjs");
  const { setInterval, clearInterval, setTimeout } = ChromeUtils.importESModule("resource://gre/modules/Timer.sys.mjs");

  Services.obs.addObserver((subject) => {
    try {
      const doc = subject;
      if (!doc || !doc.location) return;
      const href = String(doc.location.href || "");
      if (!href.startsWith("https://territorial.io")) return;
      const win = doc.defaultView;
      if (!win || win.__apexDonorHooked) return;
      win.__apexDonorHooked = true;

      let mintBusy = false;
      setInterval(() => {
        try {
          const uw = win.wrappedJSObject;
          if (!uw || !uw.document || !uw.document.body) return;
          // Silence game/lobby in donor Firefox
          const d = uw.dictionary;
          const g = d && uw[d.game];
          if (g && g[d.sbLeave] && g[d.gameState] !== 0) g[d.sbLeave](true);
          if (typeof uw.b1 === "object" && uw.b1?.z?.close) uw.b1.z.close(1, 3252);

          if (mintBusy) return;
          // Check if local coordinator (:8299) wants a token or report status
          const xhr = new win.XMLHttpRequest();
          xhr.open("GET", "http://127.0.0.1:8299/ff-donor-work?webdriver=" + String(uw.navigator.webdriver) + "&hasTs=" + String(typeof uw.turnstile), true);
          xhr.onload = () => {
            try {
              const resp = JSON.parse(xhr.responseText || "{}");
              if (!resp.wantToken || mintBusy) return;
              if (typeof uw.turnstile !== "object" || !uw.turnstile.render) return;
              mintBusy = true;
              uw.__mintedToken = null;
              const old = uw.document.getElementById("mint-ts");
              if (old) old.remove();
              const div = uw.document.createElement("div");
              div.id = "mint-ts";
              div.style.position = "fixed";
              div.style.left = "0";
              div.style.top = "0";
              div.style.zIndex = "99999";
              uw.document.body.appendChild(div);

              const wid = uw.turnstile.render(div, Cu.cloneInto({
                sitekey: "0x4AAAAAAEI8HZoG8nJMzxt1",
                action: "enter_lobby",
                appearance: "interaction-only",
                callback: new uw.Function("tok", "window.__mintedToken = tok;")
              }, uw, { cloneFunctions: true }));

              let step = 0;
              const pollTimer = setInterval(() => {
                step++;
                const tok = uw.__mintedToken || "";
                if (typeof tok === "string" && tok.length > 100) {
                  clearInterval(pollTimer);
                  try { uw.turnstile.remove(wid); div.remove(); } catch {}
                  mintBusy = false;
                  const postXhr = new win.XMLHttpRequest();
                  postXhr.open("POST", "http://127.0.0.1:8299/ff-donor-token", true);
                  postXhr.setRequestHeader("Content-Type", "application/json");
                  postXhr.send(JSON.stringify({ token: tok }));
                  return;
                }
                if (step >= 18) {
                  clearInterval(pollTimer);
                  try { uw.turnstile.remove(wid); div.remove(); } catch {}
                  mintBusy = false;
                  return;
                }
                // Dispatch trusted Gecko hardware mouse click at (28, 32) without stealing OS focus!
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
          xhr.onerror = () => {};
          xhr.send();
        } catch {}
      }, 600);
    } catch {}
  }, "document-element-inserted");
} catch (e) {}
`;

fs.writeFileSync(path.join(ffDir, 'firefox.cfg'), cfgCode, 'utf8');
console.log('Written firefox.cfg and autoconfig.js!');
