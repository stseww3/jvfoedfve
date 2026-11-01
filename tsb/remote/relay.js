// Content script (isolated world): carries messages between the page script
// (page.js, DOM events with JSON text) and the service worker (background.js,
// a runtime port), which holds the WebSocket to the backend. In manual (remote)
// mode it also polls the command webhook and posts results for page.js, through
// the service worker.
(() => {
    // after the extension is reloaded, updated, disabled or removed, this copy keeps running in the page without it
    const DEAD = '插件已更新或停用，请刷新页面';
    // waits before the 2nd, 3rd and 4th try of a result post that failed on the way or with 429 / 5xx
    const POST_RETRY_MS = [2000, 5000, 15000];
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
    const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
    const httpText = (s) => `HTTP ${s}` + (404 === s || 410 === s ? '：地址不存在或已过期'
        : 401 === s || 403 === s ? '：地址要密码或 API key'
            : 429 === s ? '：请求太频繁，或 webhook.site 免费地址的 50 条用完了（换新地址）' : s >= 500 ? '：服务器出错' : '');
    const alive = () => {
        try {
            return !!chrome.runtime.id;
        } catch {
            return false;
        }
    };

    function failWaiting(why) {
        for (const w of httpWaiting.values()) {
            clearTimeout(w.timer);
            w.reject(new Error(why));
        }
        httpWaiting.clear();
    }

    function goDead() {
        if (dead) return;
        dead = true;
        port = null;
        clearTimeout(retry);
        retry = null;
        failWaiting(DEAD);
        status({ connected: false, port: wanted, error: DEAD });
        remoteStatus({ kind: 'worker', ok: false, dead: true, error: DEAD });
    }

    // The port is opened right away and kept open: the webhook requests need it even
    // when no backend is wanted (then the service worker opens no WebSocket).
    function open() {
        clearTimeout(retry);
        retry = null;
        if (port || dead) return;
        if (!alive()) return goDead();
        let p;
        try {
            p = chrome.runtime.connect({ name: 'tsb' });
        } catch {
            return goDead();
        }
        port = p;
        p.onMessage.addListener((m) => {
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
        p.onDisconnect.addListener(() => {
            if (port !== p) return;
            port = null;
            status({ connected: false, port: wanted, error: null });
            if (!alive()) return goDead();
            failWaiting('后台断开了');
            remoteStatus({ kind: 'worker', ok: false, dead: false, error: '后台重连中' });
            retry = setTimeout(open, 1000);
        });
        try {
            p.postMessage({ kind: 'connect', port: wanted });
        } catch {
            port = null;
            if (!alive()) return goDead();
            retry = setTimeout(open, 1000);
            return;
        }
        remoteStatus({ kind: 'worker', ok: true });
    }

    function send(m) {
        if (!port) return false;
        try {
            port.postMessage(m);
            return true;
        } catch {
            port = null;
            open();
            return false;
        }
    }

    function viaWorker(method, url, body) {
        return new Promise((resolve, reject) => {
            const id = ++httpId;
            const timer = setTimeout(() => {
                httpWaiting.delete(id);
                reject(new Error('后台 15 秒没回应'));
            }, 15000);
            httpWaiting.set(id, { resolve, reject, timer });
            if (!send({ kind: 'http', id, method, url, body })) {
                httpWaiting.delete(id);
                clearTimeout(timer);
                reject(new Error(dead ? DEAD : '后台没连上'));
            }
        });
    }

    // Only through the service worker, which has host permission for webhook.site and the
    // relay: the webhook.site API sends no CORS headers, so the same request from this content
    // script (it runs with the page's origin) is always blocked.
    function http(method, url, body) {
        port || open();
        if (!port) return Promise.reject(new Error(dead ? DEAD : '后台没连上'));
        return viaWorker(method, url, body);
    }

    async function pollOnce() {
        if (!poll || polling) return;
        polling = true;
        const { url } = poll;
        try {
            const r = await http('GET', url);
            if (r.status !== 200) throw new Error(httpText(r.status));
            let d;
            try {
                d = JSON.parse(r.text);
            } catch {
                throw new Error('返回的不是 JSON（指令地址填错了？）');
            }
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
        for (let attempt = 0; ; attempt++) {
            let s;
            try {
                const r = await http('POST', url, body);
                const ok = r.status >= 200 && r.status < 300;
                s = { kind: 'post', ok, status: r.status, tag, error: ok ? null : httpText(r.status) };
                if (ok || !(429 === r.status || r.status >= 500)) return remoteStatus(s);
            } catch (e) {
                s = { kind: 'post', ok: false, error: errorText(e), tag };
                if (dead) return remoteStatus(s);
            }
            if (attempt >= POST_RETRY_MS.length) return remoteStatus(s);
            remoteStatus({ ...s, retry: attempt + 1 });
            await sleep(POST_RETRY_MS[attempt]);
        }
    }

    document.addEventListener('tsb-control', (e) => {
        const c = JSON.parse(e.detail);
        if (c.kind !== 'connect') return;
        wanted = c.port ?? null;
        if (port) send({ kind: 'connect', port: wanted });
        else open();
    });
    document.addEventListener('tsb-send', (e) => {
        send({ kind: 'message', data: e.detail });
    });
    document.addEventListener('tsb-remote', (e) => {
        let c;
        try {
            c = JSON.parse(e.detail);
        } catch {
            return;
        }
        if (c.kind === 'poll') {
            const url = typeof c.url === 'string' && /^https?:\/\//i.test(c.url) ? c.url : null;
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
        } else if (c.kind === 'post' && typeof c.url === 'string' && /^https?:\/\//i.test(c.url) && typeof c.body === 'string') {
            post(c.url, c.body, c.tag || null);
        }
    });
    // port messages keep the service worker running
    setInterval(() => {
        send({ kind: 'keepalive' });
    }, 20000);
    open();
    toPage('tsb-status', JSON.stringify({ kind: 'relay' }));
})();
