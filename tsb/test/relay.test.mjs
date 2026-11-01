// relay.js (0.6.8): webhook requests only through the service worker, a dead extension
// context reported to the page, result posts retried. Fake clock, fake runtime port.
// usage: node tsb/test/relay.test.mjs
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

const here = new URL('.', import.meta.url).pathname;
const SRC = fs.readFileSync(`${here}../remote/relay.js`, 'utf8');
const POLL = 'https://webhook.site/token/00000000-0000-4000-8000-000000000001/requests?sorting=newest&per_page=20';
const RESULT = 'https://webhook.site/00000000-0000-4000-8000-000000000002';
const flush = () => new Promise((resolve) => setImmediate(resolve));

function env({ connectThrows = false } = {}) {
    let now = 0;
    let timers = [];
    let seq = 0;
    const listeners = {};
    const events = [];
    const ports = [];
    const fetches = [];
    const document = {
        addEventListener: (t, f) => (listeners[t] ||= []).push(f),
        dispatchEvent: (e) => (events.push({ type: e.type, detail: e.detail }), (listeners[e.type] || []).forEach((f) => f(e)), true)
    };
    const runtime = {
        id: 'ext',
        connect({ name }) {
            assert.equal(name, 'tsb');
            if (connectThrows || !runtime.id) throw new Error('Extension context invalidated.');
            const on = { message: [], disconnect: [] };
            const p = {
                sent: [],
                closed: false,
                onMessage: { addListener: (f) => on.message.push(f) },
                onDisconnect: { addListener: (f) => on.disconnect.push(f) },
                postMessage(m) {
                    if (p.closed) throw new Error('Attempting to use a disconnected port object');
                    p.sent.push(JSON.parse(JSON.stringify(m)));
                },
                deliver: (m) => on.message.forEach((f) => f(m)),
                disconnect: () => ((p.closed = true), on.disconnect.forEach((f) => f()))
            };
            ports.push(p);
            return p;
        }
    };
    const clear = (id) => (timers = timers.filter((x) => x.id !== id));
    const ctx = vm.createContext({
        document,
        chrome: { runtime },
        CustomEvent: class { constructor(type, o) { this.type = type; this.detail = o && o.detail; } },
        fetch: (...a) => (fetches.push(a), Promise.reject(new Error('blocked by CORS policy'))),
        setTimeout: (fn, ms = 0) => (timers.push({ id: ++seq, at: now + ms, fn }), seq),
        setInterval: (fn, ms) => (timers.push({ id: ++seq, at: now + ms, fn, every: ms }), seq),
        clearTimeout: clear,
        clearInterval: clear,
        console, JSON, Map, Set, Promise, Error, String, Number, Array, Math
    });
    vm.runInContext(SRC, ctx);
    const fire = (type, detail) => document.dispatchEvent({ type, detail: JSON.stringify(detail) });
    const t = {
        runtime, ports, fetches, events,
        get port() { return ports[ports.length - 1]; },
        get now() { return now; },
        fire,
        async advance(ms) {
            const end = now + ms;
            for (;;) {
                const due = timers.filter((x) => x.at <= end).sort((a, b) => a.at - b.at)[0];
                if (!due) break;
                now = due.at;
                timers = timers.filter((x) => x !== due);
                due.every && timers.push({ ...due, at: due.at + due.every });
                due.fn();
                await flush();
            }
            now = end;
            await flush();
        },
        http: () => t.port.sent.filter((m) => m.kind === 'http'),
        answer(m, reply) {
            t.port.deliver({ kind: 'http', id: m.id, ...reply });
            return flush();
        },
        remote: (kind) => events.filter((e) => e.type === 'tsb-remote-status').map((e) => JSON.parse(e.detail)).filter((s) => s.kind === kind),
        last: (kind) => t.remote(kind).at(-1),
        page: (type) => events.filter((e) => e.type === type).map((e) => JSON.parse(e.detail))
    };
    return t;
}

const results = [];
const test = async (name, fn) => {
    try {
        await fn();
        results.push(['ok', name]);
    } catch (err) {
        results.push(['FAIL', name, err]);
    }
};

await test('opens the worker port at once; no backend port until the page asks for one', async () => {
    const t = env();
    assert.equal(t.ports.length, 1);
    assert.deepEqual(t.port.sent, [{ kind: 'connect', port: null }]);
    assert.equal(t.last('worker').ok, true);
    t.fire('tsb-control', { kind: 'connect', port: 8765 });
    t.fire('tsb-control', { kind: 'connect', port: null });
    assert.deepEqual(t.port.sent.slice(1), [{ kind: 'connect', port: 8765 }, { kind: 'connect', port: null }]);
    assert.equal(t.ports.length, 1);
});

await test('polls through the worker and hands new commands to the page, oldest first', async () => {
    const t = env();
    t.fire('tsb-remote', { kind: 'poll', url: POLL, ms: 3000 });
    const [get] = t.http();
    assert.equal(get.method, 'GET');
    assert.equal(get.url, POLL);
    await t.answer(get, { status: 200, text: JSON.stringify({ data: [{ uuid: 'b', created_at: '2026-11-01 04:00:02', content: 'B' }, { uuid: 'a', created_at: '2026-11-01 04:00:01', content: 'A' }] }) });
    assert.deepEqual(t.page('tsb-remote-msg')[0].map((m) => m.id), ['a', 'b']);
    assert.equal(t.last('poll').ok, true);
    await t.advance(3000);
    assert.equal(t.http().length, 2);
    assert.equal(t.fetches.length, 0);
});

await test('poll answered with 404 / 429 / not JSON: a readable reason for the panel', async () => {
    const t = env();
    t.fire('tsb-remote', { kind: 'poll', url: POLL, ms: 3000 });
    await t.answer(t.http()[0], { status: 404, text: '{"success":false}' });
    assert.match(t.last('poll').error, /^HTTP 404：地址不存在或已过期$/);
    await t.advance(3000);
    await t.answer(t.http()[1], { status: 429, text: '' });
    assert.match(t.last('poll').error, /请求太频繁/);
    await t.advance(3000);
    await t.answer(t.http()[2], { status: 200, text: '<html>' });
    assert.match(t.last('poll').error, /不是 JSON/);
});

await test('worker reports a failed fetch: the reason reaches the panel as is', async () => {
    const t = env();
    t.fire('tsb-remote', { kind: 'poll', url: POLL, ms: 3000 });
    await t.answer(t.http()[0], { error: '插件没有 webhook.site 的访问权限（扩展详情→网站访问权限→在所有网站上）' });
    assert.match(t.last('poll').error, /访问权限/);
});

await test('extension reloaded while the page stays open: no direct fetch, the page is told', async () => {
    const t = env();
    t.fire('tsb-remote', { kind: 'poll', url: POLL, ms: 3000 });
    await t.answer(t.http()[0], { status: 200, text: '{"data":[]}' });
    t.runtime.id = undefined;
    t.port.disconnect();
    const w = t.last('worker');
    assert.equal(w.dead, true);
    assert.equal(w.error, '插件已更新或停用，请刷新页面');
    assert.equal(t.page('tsb-status').at(-1).error, '插件已更新或停用，请刷新页面');
    await t.advance(30e3);
    assert.equal(t.fetches.length, 0, 'never fetches from the content script');
    assert.equal(t.ports.length, 1, 'does not try to reconnect');
    assert.equal(t.last('poll').error, '插件已更新或停用，请刷新页面');
    t.fire('tsb-remote', { kind: 'post', url: RESULT, body: '{}', tag: 'ack' });
    await t.advance(60e3);
    const posts = t.remote('post');
    assert.equal(posts.length, 1, 'no retries once the extension is gone');
    assert.equal(posts[0].error, '插件已更新或停用，请刷新页面');
});

await test('runtime.connect throws at load: dead from the start, still no fetch', async () => {
    const t = env({ connectThrows: true });
    assert.equal(t.last('worker').dead, true);
    t.fire('tsb-remote', { kind: 'poll', url: POLL, ms: 3000 });
    await t.advance(10e3);
    assert.equal(t.fetches.length, 0);
    assert.equal(t.last('poll').error, '插件已更新或停用，请刷新页面');
});

await test('service worker restarted: requests in flight fail, the port comes back, polling goes on', async () => {
    const t = env();
    t.fire('tsb-control', { kind: 'connect', port: 8765 });
    t.fire('tsb-remote', { kind: 'poll', url: POLL, ms: 3000 });
    t.port.disconnect();
    await t.advance(0);
    assert.equal(t.last('poll').error, '后台断开了');
    assert.deepEqual(t.last('worker'), { kind: 'worker', ok: false, dead: false, error: '后台重连中' });
    await t.advance(1000);
    assert.equal(t.ports.length, 2);
    assert.deepEqual(t.port.sent[0], { kind: 'connect', port: 8765 }, 'the backend port is asked for again');
    await t.advance(2000);
    const [get] = t.http();
    await t.answer(get, { status: 200, text: '{"data":[]}' });
    assert.equal(t.last('poll').ok, true);
    assert.equal(t.fetches.length, 0);
});

await test('a poll during the reconnect gap reconnects at once instead of failing', async () => {
    const t = env();
    t.port.disconnect();
    t.fire('tsb-remote', { kind: 'poll', url: POLL, ms: 3000 });
    assert.equal(t.ports.length, 2);
    assert.equal(t.http().length, 1);
});

await test('result post: retried after 500 and a failed fetch, then sent', async () => {
    const t = env();
    t.fire('tsb-remote', { kind: 'post', url: RESULT, body: '{"type":"ack"}', tag: 'ack' });
    await t.answer(t.http()[0], { status: 500, text: '' });
    assert.deepEqual(t.last('post'), { kind: 'post', ok: false, status: 500, tag: 'ack', error: 'HTTP 500：服务器出错', retry: 1 });
    await t.advance(1999);
    assert.equal(t.http().length, 1);
    await t.advance(1);
    await t.answer(t.http()[1], { error: 'Failed to fetch' });
    assert.equal(t.last('post').retry, 2);
    await t.advance(5000);
    const third = t.http()[2];
    assert.equal(third.method, 'POST');
    assert.equal(third.body, '{"type":"ack"}');
    await t.answer(third, { status: 200, text: '' });
    assert.deepEqual(t.last('post'), { kind: 'post', ok: true, status: 200, tag: 'ack', error: null });
});

await test('result post: 400 is not retried; four failures in a row give up', async () => {
    const t = env();
    t.fire('tsb-remote', { kind: 'post', url: RESULT, body: '{}', tag: 'result' });
    await t.answer(t.http()[0], { status: 400, text: '' });
    await t.advance(60e3);
    assert.equal(t.http().length, 1);
    assert.equal(t.last('post').error, 'HTTP 400');
    const u = env();
    u.fire('tsb-remote', { kind: 'post', url: RESULT, body: '{}', tag: 'result' });
    for (let i = 0; i < 4; i++) {
        await u.answer(u.http()[i], { status: 503, text: '' });
        await u.advance(20e3);
    }
    assert.equal(u.http().length, 4);
    assert.equal(u.last('post').retry, undefined);
    assert.equal(u.last('post').ok, false);
});

await test('the worker does not answer: the request fails after 15 s', async () => {
    const t = env();
    t.fire('tsb-remote', { kind: 'poll', url: POLL, ms: 60e3 });
    await t.advance(15e3);
    assert.equal(t.last('poll').error, '后台 15 秒没回应');
});

let failed = 0;
for (const [s, name, err] of results) {
    console.log(`${s} ${name}`);
    if (err) failed++, console.log(err);
}
console.log(`${results.length - failed}/${results.length} passed`);
process.exit(failed ? 1 : 0);
