// send-command.mjs (0.6.8): signed body, --wait finds the extension's ack on the result
// webhook, or says why none came. Fake webhook.site, fake clock.
// usage: node tsb/test/send-command.test.mjs
import assert from 'node:assert/strict';
import { createHmac } from 'node:crypto';
import { main } from '../remote/send-command.mjs';

const KEY = 'test-key';
const CMD = 'https://webhook.site/00000000-0000-4000-8000-000000000001';
const RESULT = 'https://webhook.site/00000000-0000-4000-8000-000000000002';
const API = 'https://webhook.site/token/00000000-0000-4000-8000-000000000002/requests?sorting=newest&per_page=50';
const REQ = '11111111-2222-4333-8444-555555555555';
const T0 = Date.UTC(2026, 10, 1, 5, 0, 0);
const stamp = (ms) => new Date(ms).toISOString().slice(0, 19).replace('T', ' ');

// results(t): what the result webhook lists at time t, newest first
function run(argv, { results = () => [], cmdStatus = 200, requestId = REQ, apiStatus = 200, env = {} } = {}) {
    let t = T0;
    const out = [], err = [], posts = [], gets = [];
    const fetch = async (url, init = {}) => {
        if (init.method === 'POST') {
            posts.push({ url, init });
            return { status: cmdStatus, ok: cmdStatus >= 200 && cmdStatus < 300, headers: { get: (h) => (h.toLowerCase() === 'x-request-id' ? requestId : null) } };
        }
        gets.push({ url, t });
        assert.equal(url, API);
        const status = typeof apiStatus === 'function' ? apiStatus(t) : apiStatus;
        return { status, json: async () => ({ data: results(t, posts) }) };
    };
    const io = {
        env: { TSB_KEY: KEY, TSB_CMD_URL: CMD, ...env }, fetch,
        now: () => t, sleep: async (ms) => void (t += ms),
        out: (s) => out.push(s), err: (s) => err.push(s)
    };
    return main(argv, io).then((code) => ({ code, out, err, posts, gets, elapsed: t - T0 }));
}
const ack = (extra) => ({ uuid: `r${Math.random()}`, method: 'POST', created_at: stamp(T0 + 4e3), content: JSON.stringify({ type: 'ack', id: REQ, cmd: 'ping', seq: null, ok: true, state: { manual: true }, ext: '0.6.8', at: '' , ...extra }) });

const results = [];
const test = async (name, fn) => {
    try {
        await fn();
        results.push(['ok', name]);
    } catch (e) {
        results.push(['FAIL', name, e]);
    }
};

await test('signed body: p verifies with the key, ts and nonce set', async () => {
    const r = await run(['ping']);
    assert.equal(r.code, 0);
    const { p, sig } = JSON.parse(r.posts[0].init.body);
    assert.equal(createHmac('sha256', KEY).update(p).digest('base64url'), sig);
    const c = JSON.parse(p);
    assert.equal(c.cmd, 'ping');
    assert.equal(c.ts, T0);
    assert.ok(c.nonce.length >= 16);
    assert.equal(c.seq, undefined, 'no seq unless asked for or waiting');
    assert.deepEqual(r.out, ['ping: HTTP 200']);
    assert.match(r.err[0], /--wait/);
});

await test('--wait: prints the answer with the request id from webhook.site, ignores other acks', async () => {
    const r = await run(['ping', '--wait', '--result', RESULT], {
        results: (t) => t < T0 + 4e3 ? [ack({ id: 'someone-else' })] : [ack(), ack({ id: 'someone-else' })]
    });
    assert.equal(r.code, 0);
    assert.equal(r.out[0], 'ping: HTTP 200');
    assert.equal(r.out[1], 'answer after 4 s:');
    const a = JSON.parse(r.out[2]);
    assert.equal(a.id, REQ);
    assert.equal(a.ok, true);
    assert.equal(r.gets.length, 3);
});

await test('--wait with TSB_RESULT_URL as a bare token', async () => {
    const r = await run(['ping', '--wait'], { env: { TSB_RESULT_URL: '00000000-0000-4000-8000-000000000002' }, results: () => [ack()] });
    assert.equal(r.code, 0);
});

await test('--wait: an answer with ok false (bad signature) is printed, exit 1', async () => {
    const r = await run(['ping', '--wait', '--result', RESULT], { results: () => [ack({ ok: false, error: 'bad signature', cmd: undefined })] });
    assert.equal(r.code, 1);
    assert.equal(JSON.parse(r.out[2]).error, 'bad signature');
});

await test('--wait, no request id (command webhook elsewhere): matched by the seq it adds', async () => {
    const seqOf = (posts) => JSON.parse(JSON.parse(posts[0].init.body).p).seq;
    const r = await run(['stop', '--wait', '--result', RESULT], {
        requestId: null,
        results: (t, posts) => [ack({ id: 'x', cmd: 'stop', seq: seqOf(posts) + 1 }), ack({ id: 'y', cmd: 'stop', seq: seqOf(posts) })]
    });
    assert.equal(r.code, 0);
    assert.ok(Number.isInteger(seqOf(r.posts)));
    assert.equal(JSON.parse(r.out[2]).id, 'y');
});

await test('no answer, empty OPTIONS on the result webhook: an old or unrefreshed tab posting from the page', async () => {
    const r = await run(['ping', '--wait', '--result', RESULT, '--timeout', '10'], {
        results: () => [{ uuid: 'o', method: 'OPTIONS', created_at: stamp(T0 - 60e3), content: '' }]
    });
    assert.equal(r.code, 3);
    assert.match(r.err[0], /within 10 s/);
    assert.match(r.err[0], /OPTIONS/);
    assert.match(r.err[0], /older than 0\.6\.8/);
    assert.ok(r.elapsed >= 10e3 && r.elapsed <= 12e3);
});

await test('no answer, the extension posted lately: points at an unrefreshed tab, the address, the clock and slow tabs', async () => {
    const r = await run(['ping', '--wait', '--result', RESULT, '--timeout', '6'], {
        results: () => [{ uuid: 'p', method: 'POST', created_at: stamp(T0 - 30e3), content: JSON.stringify({ type: 'result', ext: '0.6.8' }) }]
    });
    assert.equal(r.code, 3);
    assert.match(r.err[0], /last: result, 3\d s ago, version 0\.6\.8/);
    assert.match(r.err[0], /reloaded, updated or removed since/);
    assert.match(r.err[0], /指令 webhook/);
    assert.match(r.err[0], /12 minutes/);
});

await test('no answer, nothing from the extension lately: no tab is polling', async () => {
    const r = await run(['ping', '--wait', '--result', RESULT, '--timeout', '4'], {
        results: () => [{ uuid: 'q', method: 'POST', created_at: stamp(T0 - 3600e3), content: JSON.stringify({ type: 'ack', ext: '0.6.7' }) }]
    });
    assert.equal(r.code, 3);
    assert.match(r.err[0], /Nothing from the extension/);
    assert.match(r.err[0], /unrefreshed after the extension was reloaded or updated/);
});

await test('result webhook 404 / 401: stops at once with the reason', async () => {
    const a = await run(['ping', '--wait', '--result', RESULT], { apiStatus: 404 });
    assert.equal(a.code, 1);
    assert.match(a.err[0], /expired/);
    assert.equal(a.gets.length, 1);
    const b = await run(['ping', '--wait', '--result', RESULT], { apiStatus: 401 });
    assert.match(b.err[0], /password or an API key/);
});

await test('result webhook 429: waits longer, keeps trying', async () => {
    const r = await run(['ping', '--wait', '--result', RESULT], { apiStatus: (t) => (t < T0 + 5e3 ? 429 : 200), results: () => [ack()] });
    assert.equal(r.code, 0);
    assert.equal(r.gets.length, 2);
    assert.equal(r.gets[1].t - r.gets[0].t, 5e3);
});

await test('command webhook 404: says it does not exist or expired, exit 1, no waiting', async () => {
    const r = await run(['ping', '--wait', '--result', RESULT], { cmdStatus: 404 });
    assert.equal(r.code, 1);
    assert.match(r.out[0], /^ping: HTTP 404 \(no such command webhook, or it has expired\)$/);
    assert.equal(r.gets.length, 0);
});

await test('--wait needs a webhook.site result address', async () => {
    await assert.rejects(run(['ping', '--wait']), /TSB_RESULT_URL/);
    await assert.rejects(run(['ping', '--wait', '--result', 'https://example.com/00000000-0000-4000-8000-000000000002']), /webhook\.site/);
});

await test('usage: unknown command exits 2; --print sends nothing', async () => {
    const a = await run(['pong']);
    assert.equal(a.code, 2);
    const b = await run(['start', '--mp', '--print', '--wait']);
    assert.equal(b.code, 0);
    assert.equal(b.posts.length, 0);
    assert.equal(JSON.parse(JSON.parse(b.out[0]).p).mp, true);
});

let failed = 0;
for (const [s, name, e] of results) {
    console.log(`${s} ${name}`);
    if (e) failed++, console.log(e);
}
console.log(`${results.length - failed}/${results.length} passed`);
process.exit(failed ? 1 : 0);
