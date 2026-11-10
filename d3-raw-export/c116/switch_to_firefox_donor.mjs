import fs from 'node:fs';

let tsb = fs.readFileSync('tsb-apex-squad.mjs', 'utf8').replace(/\r\n/g, '\n');

const startMarker = `for (const bot of CHROME_BOTS) {`;
const endMarker = `// Centralized Backend Spawn Coordinator (TeamSpawnCoordinator):`;

const sIdx = tsb.indexOf(startMarker);
const eIdx = tsb.indexOf(endMarker);
if (sIdx === -1 || eIdx === -1) {
  console.error('Could not find markers in tsb-apex-squad.mjs!', sIdx, eIdx);
  process.exit(1);
}

const firefoxBlock = `let activeStreamOwner = null;
let activeStreamKey = null;

let firefoxDonor = null;

async function ensureFirefoxDonor(port = 9228) {
  if (firefoxDonor && firefoxDonor.ws && firefoxDonor.ws.readyState === 1 && firefoxDonor.ctx) {
    return firefoxDonor;
  }
  const { spawn } = await import('node:child_process');
  const ffExe = path.join(__dirname, 'firefox_bin', 'firefox.exe');
  const profDir = path.join(__dirname, 'firefox_donor_9228');

  const tryConnectBidi = () => new Promise((resolve) => {
    const ws = new WebSocket(\`ws://127.0.0.1:\${port}/session\`);
    const t = setTimeout(() => { try { ws.close(); } catch {} resolve(null); }, 3000);
    ws.addEventListener('open', () => { clearTimeout(t); resolve(ws); });
    ws.addEventListener('error', () => { clearTimeout(t); resolve(null); });
  });

  let ws = await tryConnectBidi();
  if (!ws && fs.existsSync(ffExe)) {
    console.log(\`[FIREFOX-DONOR] Launching Mozilla Firefox on port \${port}...\`);
    const child = spawn(ffExe, ['-no-remote', '-profile', profDir, '--remote-debugging-port', String(port), 'https://territorial.io/'], {
      detached: true,
      stdio: 'ignore'
    });
    child.unref();
    for (let retry = 0; retry < 12; retry++) {
      await new Promise((r) => setTimeout(r, 1000));
      ws = await tryConnectBidi();
      if (ws) break;
    }
  }
  if (!ws) throw new Error(\`Firefox BiDi not reachable on port \${port}\`);

  let seq = 0;
  const pending = new Map();
  ws.addEventListener('message', (ev) => {
    try {
      const msg = JSON.parse(ev.data);
      if (msg.id && pending.has(msg.id)) {
        const fn = pending.get(msg.id);
        pending.delete(msg.id);
        fn(msg);
      }
    } catch {}
  });
  ws.addEventListener('close', () => {
    if (firefoxDonor && firefoxDonor.ws === ws) firefoxDonor = null;
  });

  const callBidi = (method, params = {}) => new Promise((resolve) => {
    if (ws.readyState !== 1) return resolve(null);
    const id = ++seq;
    const timer = setTimeout(() => {
      pending.delete(id);
      resolve(null);
    }, 8000);
    pending.set(id, (msg) => {
      clearTimeout(timer);
      resolve(msg);
    });
    ws.send(JSON.stringify({ id, method, params }));
  });

  // End any stale BiDi session first, then create a fresh session
  await callBidi('session.end', {});
  const sess = await callBidi('session.new', { capabilities: {} });
  if (!sess?.result?.sessionId) {
    // If a previous process held a session on this Firefox instance, reconnect cleanly
    console.log('[FIREFOX-DONOR] BiDi session busy or re-initializing...');
  }

  await callBidi('script.addPreloadScript', {
    functionDeclaration: \`() => {
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
    }\`
  });

  const tree = await callBidi('browsingContext.getTree', {});
  const topCtx = tree?.result?.contexts?.find((c) => c.url?.includes('territorial.io')) || tree?.result?.contexts?.[0];
  const ctx = topCtx?.context;
  if (!ctx) {
    try { ws.close(); } catch {}
    throw new Error('No browsingContext found in Firefox Donor');
  }

  await callBidi('browsingContext.activate', { context: ctx });

  // Check if navigator.webdriver is already false in topCtx; if not, reload once so addPreloadScript takes effect
  const wdCheck = await callBidi('script.evaluate', {
    expression: 'String(navigator.webdriver) + ":" + String(typeof window.turnstile)',
    target: { context: ctx },
    awaitPromise: false
  });
  const wdVal = wdCheck?.result?.result?.value || '';
  if (!wdVal.startsWith('false:object')) {
    console.log(\`[FIREFOX-DONOR] Reloading territorial.io tab so preloadScript (webdriver=false) takes effect (was \${wdVal})...\`);
    await callBidi('browsingContext.reload', { context: ctx, wait: 'complete' });
    await new Promise((r) => setTimeout(r, 2500));
  }

  console.log(\`[FIREFOX-DONOR] Connected to Mozilla Firefox BiDi on :\${port} (ctx=\${ctx}, webdriver=false)!\`);
  firefoxDonor = { ws, callBidi, ctx, port, _mintChain: Promise.resolve() };
  return firefoxDonor;
}

await ensureFirefoxDonor(9228).catch((e) => console.error('[FIREFOX-DONOR] Init warn:', e.message));

async function mintViaDonorChrome(donorPort = 9228) {
  const donor = await ensureFirefoxDonor(donorPort);
  const runMint = async () => {
    const { callBidi, ctx } = donor;
    await callBidi('script.evaluate', {
      expression: \`(() => {
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
        const wid = window.turnstile.render(div, {
          sitekey: "0x4AAAAAAEI8HZoG8nJMzxt1",
          action: "enter_lobby",
          appearance: "interaction-only",
          callback: (tok) => {
            window.__mintedToken = tok;
            try { window.turnstile.remove(wid); div.remove(); } catch {}
          }
        });
        return "RENDERED:" + wid;
      })()\`,
      target: { context: ctx },
      awaitPromise: false,
      userActivation: true
    });

    for (let i = 0; i < 14; i++) {
      await new Promise((r) => setTimeout(r, 650));
      const check = await callBidi('script.evaluate', {
        expression: 'window.__mintedToken || ""',
        target: { context: ctx },
        awaitPromise: false
      });
      const tok0 = check?.result?.result?.value || '';
      if (typeof tok0 === 'string' && tok0.length > 100) {
        return tok0;
      }
      await callBidi('input.performActions', {
        context: ctx,
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
      });
    }
    throw new Error('Firefox BiDi mint timeout');
  };

  const next = (donor._mintChain || Promise.resolve()).then(runMint, runMint);
  donor._mintChain = next.catch(() => {});
  return next;
}

`;

tsb = tsb.slice(0, sIdx) + firefoxBlock + tsb.slice(eIdx);
fs.writeFileSync('tsb-apex-squad.mjs', tsb, 'utf8');
console.log('Successfully switched tsb-apex-squad.mjs Turnstile Donor from Chrome to Mozilla Firefox BiDi!');
