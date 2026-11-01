// Service worker: one WebSocket to the local backend per tab (per port from
// relay.js) while that tab uses the backend strategy, reconnected while the tab
// stays open. Messages pass through as text both ways. It also makes the
// remote-mode webhook requests for relay.js (host permission for webhook.site
// means no CORS check here).
const RETRY_MS = 2000;
const PING_MS = 20000;
const GAME_TABS = 'https://territorial.io/*';

// A fetch that fails without a response: either the host permission is withheld
// (site access set to "on click" / specific sites; then it is a CORS error) or no connection.
async function fetchError(url, e) {
    const { host, origin } = new URL(url);
    let allowed = true;
    try {
        allowed = await chrome.permissions.contains({ origins: [`${origin}/*`] });
    } catch { }
    return allowed ? `连不上 ${host}：${String((e && e.message) || e)}` : `插件没有 ${host} 的访问权限（扩展详情→网站访问权限→在所有网站上）`;
}

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
        clearTimeout(timer);
        timer = null;
        if (!ws) return;
        const sock = ws;
        ws = null;
        sock.close();
    }

    port.onMessage.addListener((m) => {
        if (m.kind === 'connect') {
            const want = Number.isInteger(m.port) ? m.port : null;
            if (want !== target) {
                target = want;
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
                .catch(async (e) => post({ kind: 'http', id: m.id, error: await fetchError(m.url, e) }));
        }
    });
    port.onDisconnect.addListener(() => {
        gone = true;
        clearInterval(pinger);
        drop();
    });
    const pinger = setInterval(() => {
        if (ws && ws.readyState === WebSocket.OPEN) ws.send('{"type":"ping"}');
    }, PING_MS);
});

// Runs in a game tab (main world) that still has the scripts of the extension as it was
// before this install or update, cut off from this worker, so no remote command reaches it.
// Remote-mode tabs are reloaded once the bot is not in a running game (at most 30 minutes
// later), with the loop carried over; other tabs are left to the person in front of them.
// Pages from 0.6.8 on do this themselves (remote.updateReload).
// A tab without the bot was loaded while the extension was away (removed, then installed
// again a while later; a 0.6.8 page reloads itself as soon as it is cut off): with manual
// mode in the saved settings it is reloaded now.
function reloadWhenFree() {
    const ext = window.__fx && window.__fx.strategyBotExtension;
    if (!ext) {
        let saved = null;
        try {
            saved = JSON.parse(localStorage.getItem('territorialStrategyBotExtension'));
        } catch { }
        if (!saved || !saved.manual || window.__tsbUpdateReload) return 'skip';
        window.__tsbUpdateReload = true;
        location.reload();
        return 'reload';
    }
    if (!ext.settings || !ext.settings.manual || window.__tsbUpdateReload) return 'skip';
    window.__tsbUpdateReload = true;
    const r = ext.remote;
    if (r && typeof r.updateReload === 'function') return r.updateReload(), 'page';
    const t0 = Date.now();
    const playing = () => {
        try {
            const s = r.snapshot();
            return !!(s.inGame && !s.over && s.mode !== 'replay' && !(r.state.game && r.state.game.done));
        } catch {
            return false;
        }
    };
    let timer = null;
    const go = () => {
        if (playing() && Date.now() - t0 < 18e5) return false;
        clearInterval(timer);
        try {
            const now = Date.now(), why = '插件已更新或停用，刷新页面换上新版本';
            r.rw.pending = true;
            r.rec.reloads.push(now);
            r.rec.resume = { loop: ext.settings.armed ? r.state.loop : null, open: false, at: now, why };
            r.rec.last = { action: 'reload', why, code: null, at: now };
            sessionStorage.setItem('territorialStrategyBotRecover', JSON.stringify(r.rec));
        } catch { }
        location.reload();
        return true;
    };
    if (go()) return 'reload';
    timer = setInterval(go, 1000);
    return 'wait';
}

chrome.runtime.onInstalled.addListener(({ reason }) => {
    if (reason !== 'install' && reason !== 'update') return;
    chrome.tabs.query({ url: GAME_TABS }).then((tabs) => {
        for (const tab of tabs) {
            chrome.scripting.executeScript({ target: { tabId: tab.id }, world: 'MAIN', func: reloadWhenFree }).catch(() => { });
        }
    }, () => { });
});
