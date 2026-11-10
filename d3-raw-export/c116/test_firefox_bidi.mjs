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
const sess = await callBidi('session.new', { capabilities: {} });
console.log('session.new:', JSON.stringify(sess).slice(0, 200));

const tree = await callBidi('browsingContext.getTree', {});
console.log('getTree:', JSON.stringify(tree));
const ctx = tree?.result?.contexts?.find((c) => c.url?.includes('territorial.io'))?.context || tree?.result?.contexts?.[0]?.context;
console.log('Selected context:', ctx);

const eval1 = await callBidi('script.evaluate', {
  expression: `(() => {
    window.__mintedToken = null;
    const old = document.getElementById("mint-ts");
    if (old) old.remove();
    const d = document.createElement("div");
    d.id = "mint-ts";
    d.style.position = "fixed";
    d.style.left = "0";
    d.style.top = "0";
    d.style.zIndex = "100";
    document.body.appendChild(d);
    if (typeof window.turnstile !== "object") return "NO_TURNSTILE";
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
console.log('Render eval:', JSON.stringify(eval1));

for (let i = 0; i < 10; i++) {
  await new Promise((r) => setTimeout(r, 700));
  const check = await callBidi('script.evaluate', {
    expression: 'window.__mintedToken || ""',
    target: { context: ctx },
    awaitPromise: false,
    userActivation: true
  });
  const val = check?.result?.result?.value || '';
  if (val.length > 100) {
    console.log(`SUCCESS! Minted Turnstile token via Firefox BiDi in ${(i + 1) * 700}ms! len=${val.length} prefix=${val.slice(0, 40)}...`);
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
          { type: 'pointerMove', x: 28, y: 32, duration: 60 },
          { type: 'pointerDown', button: 0 },
          { type: 'pause', duration: 60 },
          { type: 'pointerUp', button: 0 }
        ]
      }
    ]
  });
}

await callBidi('session.end', {});
ws.close();
process.exit(0);
