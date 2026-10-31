// Service worker: one WebSocket to the local backend per tab (per port from
// relay.js), reconnected while the tab stays open. Messages pass through as
// text both ways.
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
