import fs from 'node:fs';

let topCtx = '';
const ws = new WebSocket('ws://127.0.0.1:9225/session');
ws.addEventListener('open', () => {
  ws.send(JSON.stringify({ id: 1, method: 'session.end', params: {} }));
  ws.send(JSON.stringify({ id: 2, method: 'session.new', params: { capabilities: {} } }));
  ws.send(JSON.stringify({ id: 3, method: 'browsingContext.getTree', params: {} }));
});
ws.addEventListener('message', (ev) => {
  const m = JSON.parse(ev.data);
  if (m.id === 3) {
    topCtx = m.result?.contexts?.[0]?.context;
    // Reload first so we get the latest HTML if territorial.io updated after 23:15
    ws.send(JSON.stringify({ id: 4, method: 'browsingContext.reload', params: { context: topCtx, wait: 'complete' } }));
  } else if (m.id === 4) {
    setTimeout(() => {
      ws.send(JSON.stringify({
        id: 5,
        method: 'script.evaluate',
        params: {
          expression: `(() => {
            const html = document.documentElement.innerHTML;
            const dM = html.match(/function\\s+\\w+\\(\\)\\{this\\.\\w+=\\d+;this\\.\\w+=17\\d\\d;[\\s\\S]{0,160}/);
            const dxAll = Array.from(html.matchAll(/=17[67]\\d\\b/g)).map(x => html.slice(x.index - 40, x.index + 80));
            return JSON.stringify({ len: html.length, dM: dM ? dM[0] : null, dxAll, html });
          })()`,
          target: { context: topCtx },
          awaitPromise: false
        }
      }));
    }, 2000);
  } else if (m.id === 5) {
    const val = JSON.parse(m.result?.result?.value || '{}');
    console.log('Reloaded 9225 len:', val.len);
    console.log('dM:', val.dM);
    console.log('dxAll:', val.dxAll);
    if (val.html && val.html.length > 500000) {
      fs.writeFileSync('fresh_9225.html', val.html, 'utf8');
      console.log('Saved fresh_9225.html');
    }
    process.exit(0);
  }
});
setTimeout(() => process.exit(0), 15000);
