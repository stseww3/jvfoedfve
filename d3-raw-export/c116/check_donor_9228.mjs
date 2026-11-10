import http from 'node:http';

function getJson(url) {
  return new Promise((resolve, reject) => {
    http.get(url, (res) => {
      let d = '';
      res.on('data', (c) => d += c);
      res.on('end', () => resolve(JSON.parse(d)));
    }).on('error', reject);
  });
}

const pages = await getJson('http://127.0.0.1:9228/json');
const page = pages.find((p) => p.type === 'page' && p.url.includes('territorial.io'));
console.log('Page:', page?.url, page?.title);
const ws = new WebSocket(page.webSocketDebuggerUrl);
await new Promise((r) => ws.addEventListener('open', r));
ws.send(JSON.stringify({
  id: 1,
  method: 'Runtime.evaluate',
  params: {
    expression: 'JSON.stringify({ hasTurnstile: typeof window.turnstile, mintedLen: (window.__mintedToken || "").length, mintDiv: !!document.getElementById("mint-ts"), bodyText: document.body.innerText.slice(0, 200) })',
    returnByValue: true
  }
}));
const msg = await new Promise((r) => ws.addEventListener('message', (e) => r(JSON.parse(e.data))));
console.log('Eval result:', msg?.result?.result?.value);
ws.close();
process.exit(0);
