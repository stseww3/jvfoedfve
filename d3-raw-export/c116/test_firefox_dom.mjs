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
console.log('Children:', JSON.stringify(topCtx.children));

const info = await callBidi('script.evaluate', {
  expression: `JSON.stringify({
    mintedLen: (window.__mintedToken || "").length,
    iframes: Array.from(document.querySelectorAll("iframe")).map(f => ({ id: f.id, rect: f.getBoundingClientRect() })),
    divs: Array.from(document.querySelectorAll("div")).map(d => ({ id: d.id, rect: d.getBoundingClientRect() }))
  })`,
  target: { context: ctx },
  awaitPromise: false
});
console.log('DOM info:', info?.result?.result?.value);

const actRes = await callBidi('input.performActions', {
  context: ctx,
  actions: [
    {
      type: 'pointer',
      id: 'mouse1',
      parameters: { pointerType: 'mouse' },
      actions: [
        { type: 'pointerMove', x: 28, y: 32, duration: 50 },
        { type: 'pointerDown', button: 0 },
        { type: 'pause', duration: 60 },
        { type: 'pointerUp', button: 0 }
      ]
    }
  ]
});
console.log('actRes:', JSON.stringify(actRes));

await new Promise((r) => setTimeout(r, 2500));
const check2 = await callBidi('script.evaluate', {
  expression: 'JSON.stringify({ mintedLen: (window.__mintedToken || "").length, tokPrefix: (window.__mintedToken || "").slice(0, 40) })',
  target: { context: ctx },
  awaitPromise: false
});
console.log('After click:', check2?.result?.result?.value);

await callBidi('session.end', {});
ws.close();
process.exit(0);
