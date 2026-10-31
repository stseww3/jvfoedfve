// Content script (isolated world): carries messages between the page script
// (page.js, DOM events with JSON text) and the service worker (background.js,
// a runtime port), which holds the WebSocket to the backend. In manual (remote)
// mode it also polls the command webhook and posts results for page.js, through
// the service worker.
(() => {
    let port = null;
    let wanted = null;
    let retry = null;
    let dead = false;
    const toPage = (type, detail) => document.dispatchEvent(new CustomEvent(type, { detail }));
    const status = (s) => toPage('tsb-status', JSON.stringify({ kind: 'status', ...s }));

    let poll = null;
    let pollTimer = null;
    let polling = false;
    let forwarded = new Set();
    let httpId = 0;
    const httpWaiting = new Map();
    const remoteStatus = (s) => toPage('tsb-remote-status', JSON.stringify(s));
    const errorText = (e) => String((e && e.message) || e);

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
            else if (m.kind === 'http') {
                const w = httpWaiting.get(m.id);
                if (!w) return;
                httpWaiting.delete(m.id);
                clearTimeout(w.timer);
                if (m.error) w.reject(new Error(m.error));
                else w.resolve({ status: m.status, text: m.text });
            }
        });
        port.onDisconnect.addListener(() => {
            port = null;
            status({ connected: false, port: wanted, error: null });
            for (const w of httpWaiting.values()) {
                clearTimeout(w.timer);
                w.reject(new Error('service worker disconnected'));
            }
            httpWaiting.clear();
            retry = setTimeout(open, 1000);
        });
        port.postMessage({ kind: 'connect', port: wanted });
    }

    function viaWorker(method, url, body) {
        return new Promise((resolve, reject) => {
            if (!port) return reject(new Error('no service worker'));
            const id = ++httpId;
            const timer = setTimeout(() => {
                httpWaiting.delete(id);
                reject(new Error('timeout'));
            }, 15000);
            httpWaiting.set(id, { resolve, reject, timer });
            port.postMessage({ kind: 'http', id, method, url, body });
        });
    }

    // The webhook.site API sends no CORS headers, so a content script cannot read
    // it; the service worker can, because the extension has host permission there.
    async function http(method, url, body) {
        if (port) return viaWorker(method, url, body);
        const init = { method, cache: 'no-store', credentials: 'omit' };
        if (body !== undefined) {
            init.body = body;
            init.headers = { 'Content-Type': 'application/json' };
        }
        const r = await fetch(url, init);
        return { status: r.status, text: await r.text() };
    }

    async function pollOnce() {
        if (!poll || polling) return;
        polling = true;
        const { url } = poll;
        try {
            const r = await http('GET', url);
            if (r.status !== 200) throw new Error(`HTTP ${r.status}`);
            const d = JSON.parse(r.text);
            const list = (Array.isArray(d) ? d : d && Array.isArray(d.data) ? d.data : []).filter((x) => x && typeof x.uuid === 'string');
            if (!poll || poll.url !== url) return;
            // newest first from webhook.site; the page gets them oldest first
            const fresh = list.filter((x) => !forwarded.has(x.uuid)).reverse();
            forwarded = new Set(list.map((x) => x.uuid));
            if (fresh.length) toPage('tsb-remote-msg', JSON.stringify(fresh.map((x) => ({ id: x.uuid, at: x.created_at, content: x.content }))));
            remoteStatus({ kind: 'poll', ok: true });
        } catch (e) {
            remoteStatus({ kind: 'poll', ok: false, error: errorText(e) });
        } finally {
            polling = false;
        }
    }

    async function post(url, body, tag) {
        try {
            const r = await http('POST', url, body);
            remoteStatus({ kind: 'post', ok: r.status >= 200 && r.status < 300, status: r.status, tag });
        } catch (e) {
            remoteStatus({ kind: 'post', ok: false, error: errorText(e), tag });
        }
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
    document.addEventListener('tsb-remote', (e) => {
        let c;
        try {
            c = JSON.parse(e.detail);
        } catch {
            return;
        }
        if (c.kind === 'poll') {
            const url = typeof c.url === 'string' && /^https:\/\//i.test(c.url) ? c.url : null;
            const ms = Math.max(1000, Number(c.ms) || 3000);
            if (poll && url === poll.url && ms === poll.ms) return;
            clearInterval(pollTimer);
            pollTimer = null;
            if (!poll || url !== poll.url) forwarded = new Set();
            poll = url ? { url, ms } : null;
            if (poll) {
                pollTimer = setInterval(pollOnce, ms);
                pollOnce();
            }
        } else if (c.kind === 'post' && typeof c.url === 'string' && /^https:\/\//i.test(c.url) && typeof c.body === 'string') {
            post(c.url, c.body, c.tag || null);
        }
    });
    // port messages keep the service worker running
    setInterval(() => {
        if (port) port.postMessage({ kind: 'keepalive' });
    }, 20000);
    toPage('tsb-status', JSON.stringify({ kind: 'relay' }));
})();
