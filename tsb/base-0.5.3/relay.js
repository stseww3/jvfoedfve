// Content script (isolated world): carries messages between the page script
// (page.js, DOM events with JSON text) and the service worker (background.js,
// a runtime port), which holds the WebSocket to the backend.
(() => {
    let port = null;
    let wanted = null;
    let retry = null;
    let dead = false;
    const toPage = (type, detail) => document.dispatchEvent(new CustomEvent(type, { detail }));
    const status = (s) => toPage('tsb-status', JSON.stringify({ kind: 'status', ...s }));

    function open() {
        clearTimeout(retry);
        retry = null;
        if (port || wanted === null || dead) return;
        try {
            port = chrome.runtime.connect({ name: 'tsb' });
        } catch (e) {
            // the extension was reloaded or removed: this page keeps the old copy
            dead = true;
            status({ connected: false, port: wanted, error: '插件已更新或停用，请刷新页面' });
            return;
        }
        port.onMessage.addListener((m) => {
            if (m.kind === 'message') toPage('tsb-receive', m.data);
            else if (m.kind === 'status') status(m);
        });
        port.onDisconnect.addListener(() => {
            port = null;
            status({ connected: false, port: wanted, error: null });
            retry = setTimeout(open, 1000);
        });
        port.postMessage({ kind: 'connect', port: wanted });
    }

    document.addEventListener('tsb-control', (e) => {
        const c = JSON.parse(e.detail);
        if (c.kind !== 'connect') return;
        wanted = c.port;
        if (port) port.postMessage({ kind: 'connect', port: wanted });
        else open();
    });
    document.addEventListener('tsb-send', (e) => {
        if (port) port.postMessage({ kind: 'message', data: e.detail });
    });
    // port messages keep the service worker running
    setInterval(() => {
        if (port) port.postMessage({ kind: 'keepalive' });
    }, 20000);
    toPage('tsb-status', JSON.stringify({ kind: 'relay' }));
})();
