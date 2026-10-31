// Service worker: one WebSocket to the local backend per tab (per port from
// relay.js), reconnected while the tab stays open. Messages pass through as
// text both ways. It also makes the remote-mode webhook requests for relay.js
// (host permission for webhook.site means no CORS check here).
const RETRY_MS = 2000;
const PING_MS = 20000;

chrome.runtime.onConnect.addListener((port) => {
    if (port.name !== 'tsb') return;
    let ws = null;
    let target = null;
    let timer = null;
    let gone = false;

    const post = (m) => {
        try {
            port.postMessage(m);
        } catch {
            gone = true;
        }
    };
    const status = (connected, error = null) => post({ kind: 'status', connected, port: target, error });

    function open() {
        clearTimeout(timer);
        timer = null;
        if (gone || target === null) return;
        let sock;
        try {
            sock = new WebSocket(`ws://127.0.0.1:${target}/`);
        } catch (e) {
            status(false, String(e && e.message || e));
            timer = setTimeout(open, RETRY_MS);
            return;
        }
        ws = sock;
        sock.onopen = () => {
            if (ws === sock) status(true);
        };
        sock.onmessage = (e) => {
            if (ws === sock) post({ kind: 'message', data: e.data });
        };
        sock.onclose = (e) => {
            if (ws !== sock) return;
            ws = null;
            status(false, e.code === 1006 ? null : `closed ${e.code}`);
            if (!gone) timer = setTimeout(open, RETRY_MS);
        };
        sock.onerror = () => { };
    }

    function drop() {
        if (!ws) return;
        const sock = ws;
        ws = null;
        sock.close();
    }

    port.onMessage.addListener((m) => {
        if (m.kind === 'connect') {
            if (m.port !== target) {
                target = m.port;
                drop();
                status(false);
                open();
            } else if (ws && ws.readyState === WebSocket.OPEN) status(true);
            else if (!ws && !timer) open();
        } else if (m.kind === 'message') {
            if (ws && ws.readyState === WebSocket.OPEN) ws.send(m.data);
        } else if (m.kind === 'http') {
            if (typeof m.url !== 'string' || !/^https:\/\//i.test(m.url)) return post({ kind: 'http', id: m.id, error: 'bad url' });
            const init = { method: m.method === 'POST' ? 'POST' : 'GET', cache: 'no-store', credentials: 'omit' };
            if (init.method === 'POST') {
                init.body = String(m.body ?? '');
                init.headers = { 'Content-Type': 'application/json' };
            }
            fetch(m.url, init)
                .then(async (r) => post({ kind: 'http', id: m.id, status: r.status, text: await r.text() }))
                .catch((e) => post({ kind: 'http', id: m.id, error: String((e && e.message) || e) }));
        }
    });
    port.onDisconnect.addListener(() => {
        gone = true;
        clearTimeout(timer);
        clearInterval(pinger);
        drop();
    });
    const pinger = setInterval(() => {
        if (ws && ws.readyState === WebSocket.OPEN) ws.send('{"type":"ping"}');
    }, PING_MS);
});
