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
const tree = await callBidi('browsingContext.getTree', {});
const topCtx = tree?.result?.contexts?.find((c) => c.url?.includes('territorial.io')) || tree?.result?.contexts?.[0];
const ctx = topCtx.context;

// Subscribe to console logs from Firefox
await callBidi('session.subscribe', { events: ['log.entryAdded'] });
ws.addEventListener('message', (ev) => {
  const m = JSON.parse(ev.data);
  if (m.method === 'log.entryAdded') {
    console.log('[FF-CONSOLE]', m.params?.text);
  }
});

// Take screenshot of top-left 350x100 region
const shot = await callBidi('browsingContext.captureScreenshot', {
  context: ctx,
  clip: { type: 'box', x: 0, y: 0, width: 320, height: 80 }
});
if (shot?.result?.data) {
  fs.writeFileSync('ff_turnstile_clip.png', Buffer.from(shot.result.data, 'base64'));
  console.log('Saved ff_turnstile_clip.png (' + shot.result.data.length + ' b64 chars)');
}

// Test render with error-callback logging
await callBidi('script.evaluate', {
  expression: `(() => {
    window.__tsErr = null;
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
    window.turnstile.render(d, {
      sitekey: "0x4AAAAAAEI8HZoG8nJMzxt1",
      action: "enter_lobby",
      appearance: "interaction-only",
      callback: (tok) => { console.log("TS_SUCCESS:" + tok.length); window.__mintedToken = tok; },
      "error-callback": (err) => { console.log("TS_ERROR:" + err); window.__tsErr = err; }
    });
  })()`,
  target: { context: ctx },
  awaitPromise: false
});

await new Promise((r) => setTimeout(r, 4000));
await callBidi('session.end', {});
ws.close();
process.exit(0);
