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

const wd = await callBidi('script.evaluate', {
  expression: 'JSON.stringify({ webdriver: navigator.webdriver, hasFocus: document.hasFocus(), visibility: document.visibilityState })',
  target: { context: ctx },
  awaitPromise: false
});
console.log('Top ctx props:', wd?.result?.result?.value);

for (const child of topCtx.children || []) {
  const cwd = await callBidi('script.evaluate', {
    expression: 'JSON.stringify({ url: location.href.slice(0, 80), webdriver: navigator.webdriver, body: document.body ? document.body.innerText : "no-body", inputs: document.querySelectorAll("input, label, div").length })',
    target: { context: child.context },
    awaitPromise: false
  });
  console.log('Child props:', cwd?.result?.result?.value);
}

await callBidi('session.end', {});
ws.close();
process.exit(0);
