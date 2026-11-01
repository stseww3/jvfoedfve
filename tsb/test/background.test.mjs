// background.js (0.6.8): the backend WebSocket only while a port is asked for, readable
// webhook request failures, and remote-mode game tabs reloaded after an install / update.
// usage: node tsb/test/background.test.mjs
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

const here = new URL('.', import.meta.url).pathname;
const SRC = fs.readFileSync(`${here}../remote/background.js`, 'utf8');
const flush = () => new Promise((resolve) => setImmediate(resolve));

function worker({ permitted = true, fetchImpl = null, tabs = [] } = {}) {
    let now = 0, seq = 0, timers = [];
    const on = { connect: [], installed: [] };
    const sockets = [], injected = [], queries = [];
    class WebSocket {
        static OPEN = 1;
        constructor(url) {
            this.url = url;
            this.readyState = 0;
            this.sent = [];
            this.closed = false;
            sockets.push(this);
        }
        send(d) { this.sent.push(d); }
        close() { this.closed = true; this.readyState = 3; }
    }
    const clear = (id) => (timers = timers.filter((x) => x.id !== id));
    const chrome = {
        runtime: { onConnect: { addListener: (f) => on.connect.push(f) }, onInstalled: { addListener: (f) => on.installed.push(f) } },
        permissions: { contains: async ({ origins }) => JSON.stringify(origins) === '["https://webhook.site/*"]' ? permitted : !permitted },
        tabs: { query: async (q) => (queries.push(JSON.parse(JSON.stringify(q))), tabs) },
        scripting: { executeScript: async (o) => (injected.push(o), [{ result: 'skip' }]) }
    };
    const ctx = vm.createContext({
        chrome, WebSocket, URL, console, JSON, Promise, Number, String, Error,
        fetch: fetchImpl || (async () => ({ status: 200, text: async () => '{"data":[]}' })),
        setTimeout: (fn, ms = 0) => (timers.push({ id: ++seq, at: now + ms, fn }), seq),
        setInterval: (fn, ms) => (timers.push({ id: ++seq, at: now + ms, fn, every: ms }), seq),
        clearTimeout: clear, clearInterval: clear
    });
    vm.runInContext(SRC, ctx);
    const connect = () => {
        const listeners = { message: [], disconnect: [] };
        const port = {
            name: 'tsb', got: [],
            postMessage: (m) => port.got.push(JSON.parse(JSON.stringify(m))),
            onMessage: { addListener: (f) => listeners.message.push(f) },
            onDisconnect: { addListener: (f) => listeners.disconnect.push(f) },
            send: (m) => listeners.message.forEach((f) => f(m)),
            disconnect: () => listeners.disconnect.forEach((f) => f())
        };
        on.connect.forEach((f) => f(port));
        return port;
    };
    return {
        sockets, injected, queries, connect,
        install: (reason) => on.installed.forEach((f) => f({ reason })),
        advance(ms) {
            const end = now + ms;
            for (;;) {
                const due = timers.filter((x) => x.at <= end).sort((a, b) => a.at - b.at)[0];
                if (!due) break;
                now = due.at;
                timers = timers.filter((x) => x !== due);
                due.every && timers.push({ ...due, at: due.at + due.every });
                due.fn();
            }
            now = end;
        }
    };
}

// a game page for the injected function, run from its source the way chrome.scripting does
function page({ ext = null, playing = false } = {}) {
    let now = Date.UTC(2026, 10, 1, 4, 0, 0), timers = [], seq = 0;
    const reloads = [], session = new Map();
    const win = {};
    if (ext) win.__fx = { strategyBotExtension: ext };
    const ctx = vm.createContext({
        window: win, JSON,
        Date: class extends Date { static now() { return now; } },
        location: { reload: () => reloads.push(now) },
        sessionStorage: { setItem: (k, v) => session.set(k, v) },
        setInterval: (fn, ms) => (timers.push({ id: ++seq, at: now + ms, fn, every: ms }), seq),
        clearInterval: (id) => (timers = timers.filter((x) => x.id !== id))
    });
    return {
        reloads, session, win,
        run: (func) => vm.runInContext(`(${func.toString()})()`, ctx),
        advance(ms) {
            const end = now + ms;
            for (;;) {
                const due = timers.filter((x) => x.at <= end).sort((a, b) => a.at - b.at)[0];
                if (!due) break;
                now = due.at;
                timers = timers.filter((x) => x !== due);
                timers.push({ ...due, at: due.at + due.every });
                due.fn();
            }
            now = end;
        }
    };
}
// the parts of a 0.6.7 page the injected function uses
const old067 = ({ manual = true, armed = true, loop = 'mp', inGame = false, done = false } = {}) => {
    const remote = {
        state: { loop, game: inGame ? { done } : null },
        rec: { reloads: [1], inRow: 0, resume: null, last: null },
        rw: { pending: false },
        snapshot: () => ({ inGame: remote.state.game !== null, over: false, mode: 'multi' })
    };
    return { settings: { manual, armed }, remote };
};

const results = [];
const test = async (name, fn) => {
    try {
        await fn();
        results.push(['ok', name]);
    } catch (err) {
        results.push(['FAIL', name, err]);
    }
};

await test('no backend port asked for: no WebSocket, ever', async () => {
    const w = worker();
    const p = w.connect();
    p.send({ kind: 'connect', port: null });
    w.advance(60e3);
    assert.equal(w.sockets.length, 0);
    assert.equal(p.got.length, 0);
});

await test('backend port asked for: WebSocket, retried; dropped again when the strategy changes', async () => {
    const w = worker();
    const p = w.connect();
    p.send({ kind: 'connect', port: 8765 });
    assert.equal(w.sockets.length, 1);
    assert.equal(w.sockets[0].url, 'ws://127.0.0.1:8765/');
    w.sockets[0].onclose({ code: 1006 });
    w.advance(2000);
    assert.equal(w.sockets.length, 2);
    p.send({ kind: 'connect', port: null });
    assert.equal(w.sockets[1].closed, true);
    w.advance(60e3);
    assert.equal(w.sockets.length, 2);
    assert.deepEqual(p.got.at(-1), { kind: 'status', connected: false, port: null, error: null });
});

await test('webhook request: status and text go back to the relay', async () => {
    const calls = [];
    const w = worker({ fetchImpl: async (url, init) => (calls.push([url, init]), { status: 201, text: async () => 'ok' }) });
    const p = w.connect();
    p.send({ kind: 'http', id: 7, method: 'POST', url: 'https://webhook.site/x', body: '{"a":1}' });
    await flush();
    assert.deepEqual(p.got, [{ kind: 'http', id: 7, status: 201, text: 'ok' }]);
    assert.equal(calls[0][1].method, 'POST');
    assert.equal(calls[0][1].credentials, 'omit');
    assert.equal(calls[0][1].headers['Content-Type'], 'application/json');
});

await test('failed fetch with the webhook.site permission: "cannot reach" with the reason', async () => {
    const w = worker({ fetchImpl: async () => { throw new TypeError('Failed to fetch'); } });
    const p = w.connect();
    p.send({ kind: 'http', id: 1, method: 'GET', url: 'https://webhook.site/token/x/requests' });
    await flush();
    await flush();
    assert.deepEqual(p.got, [{ kind: 'http', id: 1, error: '连不上 webhook.site：Failed to fetch' }]);
});

await test('failed fetch with site access withheld: says where to grant it', async () => {
    const w = worker({ permitted: false, fetchImpl: async () => { throw new TypeError('Failed to fetch'); } });
    const p = w.connect();
    p.send({ kind: 'http', id: 2, method: 'GET', url: 'https://webhook.site/token/x/requests' });
    await flush();
    await flush();
    assert.match(p.got[0].error, /^插件没有 webhook\.site 的访问权限/);
    assert.match(p.got[0].error, /在所有网站上/);
});

await test('not an https url: refused', async () => {
    const w = worker();
    const p = w.connect();
    p.send({ kind: 'http', id: 3, method: 'GET', url: 'http://webhook.site/x' });
    assert.deepEqual(p.got, [{ kind: 'http', id: 3, error: 'bad url' }]);
});

await test('install / update: every game tab gets the reload check in its main world; other reasons do nothing', async () => {
    const w = worker({ tabs: [{ id: 11 }, { id: 12 }] });
    w.install('chrome_update');
    await flush();
    assert.equal(w.queries.length, 0);
    w.install('update');
    await flush();
    assert.deepEqual(w.queries, [{ url: 'https://territorial.io/*' }]);
    assert.deepEqual(w.injected.map((o) => [o.target.tabId, o.world, o.func.name]), [[11, 'MAIN', 'reloadWhenFree'], [12, 'MAIN', 'reloadWhenFree']]);
    w.install('install');
    await flush();
    assert.equal(w.injected.length, 4);
});

// the injected function, taken from the executeScript call
const w0 = worker({ tabs: [{ id: 1 }] });
w0.install('update');
await flush();
const reloadWhenFree = w0.injected[0].func;

await test('reload check: no bot or not in manual mode: the tab is left alone', async () => {
    const a = page();
    assert.equal(a.run(reloadWhenFree), 'skip');
    const b = page({ ext: old067({ manual: false }) });
    assert.equal(b.run(reloadWhenFree), 'skip');
    b.advance(60e3);
    assert.equal(b.reloads.length, 0);
});

await test('reload check: a 0.6.8 page does it itself', async () => {
    let asked = 0;
    const p = page({ ext: { settings: { manual: true }, remote: { updateReload: () => asked++ } } });
    assert.equal(p.run(reloadWhenFree), 'page');
    assert.equal(asked, 1);
    assert.equal(p.reloads.length, 0);
    assert.equal(p.run(reloadWhenFree), 'skip', 'once per page');
});

await test('reload check, 0.6.7 page out of a game: reloads now and carries the loop over', async () => {
    const ext = old067({ loop: 'mp' });
    const p = page({ ext });
    assert.equal(p.run(reloadWhenFree), 'reload');
    assert.equal(p.reloads.length, 1);
    assert.equal(ext.remote.rw.pending, true);
    const saved = JSON.parse(p.session.get('territorialStrategyBotRecover'));
    assert.equal(saved.resume.loop, 'mp');
    assert.equal(saved.resume.open, false);
    assert.match(saved.resume.why, /插件已更新/);
    assert.equal(JSON.stringify(saved.reloads), `[1,${Date.UTC(2026, 10, 1, 4, 0, 0)}]`, 'counted toward the automatic reloads per hour');
    assert.equal(saved.inRow, 0);
});

await test('reload check, 0.6.7 page in a game: waits for the game to be over, disarmed bot carries no loop', async () => {
    const ext = old067({ inGame: true, armed: false });
    const p = page({ ext });
    assert.equal(p.run(reloadWhenFree), 'wait');
    p.advance(10 * 60e3);
    assert.equal(p.reloads.length, 0);
    ext.remote.state.game.done = true;
    p.advance(1000);
    assert.equal(p.reloads.length, 1);
    assert.equal(JSON.parse(p.session.get('territorialStrategyBotRecover')).resume.loop, null);
    p.advance(10e3);
    assert.equal(p.reloads.length, 1);
});

await test('reload check, 0.6.7 page stuck in a game: reloads after 30 minutes anyway', async () => {
    const p = page({ ext: old067({ inGame: true }) });
    p.run(reloadWhenFree);
    p.advance(29 * 60e3);
    assert.equal(p.reloads.length, 0);
    p.advance(61e3);
    assert.equal(p.reloads.length, 1);
});

let failed = 0;
for (const [s, name, err] of results) {
    console.log(`${s} ${name}`);
    if (err) failed++, console.log(err);
}
console.log(`${results.length - failed}/${results.length} passed`);
process.exit(failed ? 1 : 0);
