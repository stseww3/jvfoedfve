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

await callBidi('browsingContext.activate', { context: ctx });

// Close game's own turnstile widget & remove any competing fixed divs at (0,0)
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
    return "RENDERED:" + wid + " focus=" + document.hasFocus();
  })()`,
  target: { context: ctx },
  awaitPromise: false,
  userActivation: true
});
console.log('renderRes:', renderRes?.result?.result?.value);

for (let i = 0; i < 12; i++) {
  await new Promise((r) => setTimeout(r, 700));
  const check = await callBidi('script.evaluate', {
    expression: 'window.__mintedToken || ""',
    target: { context: ctx },
    awaitPromise: false
  });
  const tok = check?.result?.result?.value || '';
  if (tok.length > 100) {
    console.log(`MINTED TOKEN IN FIREFOX! step=${i} len=${tok.length} prefix=${tok.slice(0, 45)}...`);
    break;
  }
  await callBidi('browsingContext.activate', { context: ctx });
  // Click both in topCtx and in child turnstile iframe context if present
  const t2 = await callBidi('browsingContext.getTree', { root: ctx });
  const children = t2?.result?.contexts?.[0]?.children || [];
  const targetCtx = children.length > 0 ? children[children.length - 1].context : ctx;
  const clickRes = await callBidi('input.performActions', {
    context: ctx,
    actions: [
      {
        type: 'pointer',
        id: 'mouse1',
        parameters: { pointerType: 'mouse' },
        actions: [
          { type: 'pointerMove', x: 180, y: 180, duration: 50 },
          { type: 'pointerMove', x: 28, y: 32, duration: 80 },
          { type: 'pointerDown', button: 0 },
          { type: 'pause', duration: 70 },
          { type: 'pointerUp', button: 0 }
        ]
      }
    ]
  });
  console.log(`step ${i} clicked (children=${children.length}):`, clickRes?.type);
}

await callBidi('session.end', {});
ws.close();
process.exit(0);
