import fs from 'node:fs';

const ws = new WebSocket('ws://127.0.0.1:9228/session');
let seq = 0;
const pending = new Map();
ws.addEventListener('message', (ev) => {
  const msg = JSON.parse(ev.data);
  if (msg.id && pending.has(msg.id)) {
    const fn = pending.get(msg.id);
    pending.delete(msg.id);
    fn(msg);
  }
});
function callBidi(method, params = {}) {
  return new Promise((resolve) => {
    const id = ++seq;
    pending.set(id, resolve);
    ws.send(JSON.stringify({ id, method, params }));
  });
}

await new Promise((r) => ws.addEventListener('open', r));
await callBidi('session.new', { capabilities: {} });

// 1. Register W3C BiDi preloadScript that runs in ALL frames (including cross-origin challenges.cloudflare.com!) before any page script!
const preloadRes = await callBidi('script.addPreloadScript', {
  functionDeclaration: `() => {
    try {
      const desc = Object.getOwnPropertyDescriptor(Navigator.prototype, 'webdriver');
      if (desc) {
        const fakeGet = { get webdriver() { return false; } };
        const getter = Object.getOwnPropertyDescriptor(fakeGet, 'webdriver').get;
        Object.defineProperty(Navigator.prototype, 'webdriver', {
          get: getter,
          enumerable: true,
          configurable: true
        });
      }
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
  }`
});
console.log('addPreloadScript:', JSON.stringify(preloadRes));

const tree = await callBidi('browsingContext.getTree', {});
const topCtx = tree?.result?.contexts?.find((c) => c.url?.includes('territorial.io')) || tree?.result?.contexts?.[0];
const ctx = topCtx.context;

await callBidi('browsingContext.activate', { context: ctx });

// Reload territorial.io so the preloadScript is active from the very start
await callBidi('browsingContext.reload', { context: ctx, wait: 'complete' });
await new Promise((r) => setTimeout(r, 2500));

// Verify navigator.webdriver in topCtx and child iframe
const tAfter = await callBidi('browsingContext.getTree', { root: ctx });
const childrenAfter = tAfter?.result?.contexts?.[0]?.children || [];
console.log('Children after reload:', childrenAfter.length);
if (childrenAfter.length > 0) {
  const cw = await callBidi('script.evaluate', {
    expression: 'JSON.stringify({ webdriver: navigator.webdriver, href: location.href.slice(0, 60) })',
    target: { context: childrenAfter[0].context },
    awaitPromise: false
  });
  console.log('Iframe webdriver check:', cw?.result?.result?.value);
}

// Now render Turnstile and mint token!
const renderRes = await callBidi('script.evaluate', {
  expression: `(() => {
    try { if (typeof bX === "object" && bX?.turnstile?.close) bX.turnstile.close(); } catch {}
    for (const el of Array.from(document.querySelectorAll("div"))) {
      if (el.id !== "mint-ts" && el.style?.position === "fixed" && (el.style?.zIndex === "100" || el.getBoundingClientRect().width === 300)) {
        el.remove();
      }
    }
    window.__mintedToken = null;
    const old = document.getElementById("mint-ts");
    if (old) old.remove();
    const d = document.createElement("div");
    d.id = "mint-ts";
    d.style.position = "fixed";
    d.style.left = "0";
    d.style.top = "0";
    d.style.zIndex = "2147483647";
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
    return "RENDERED:" + wid;
  })()`,
  target: { context: ctx },
  awaitPromise: false,
  userActivation: true
});
console.log('renderRes:', renderRes?.result?.result?.value);

for (let i = 0; i < 10; i++) {
  await new Promise((r) => setTimeout(r, 700));
  const check = await callBidi('script.evaluate', {
    expression: 'window.__mintedToken || ""',
    target: { context: ctx },
    awaitPromise: false
  });
  const tok = check?.result?.result?.value || '';
  if (tok.length > 100) {
    console.log(`SUCCESS! Minted Turnstile token in Firefox! step=${i} len=${tok.length} prefix=${tok.slice(0, 45)}...`);
    break;
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
  console.log('Clicked at step', i);
}

// Take screenshot of top-left 320x80
const shot = await callBidi('browsingContext.captureScreenshot', {
  context: ctx,
  clip: { type: 'box', x: 0, y: 0, width: 320, height: 80 }
});
if (shot?.result?.data) {
  fs.writeFileSync('ff_turnstile_clip2.png', Buffer.from(shot.result.data, 'base64'));
}

await callBidi('session.end', {});
ws.close();
process.exit(0);
