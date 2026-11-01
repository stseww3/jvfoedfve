// tsb/relay/relay.py (the webhook.site stand-in), run for real on a free local port: addresses,
// the request list the extension polls, send-command.mjs --wait against it, and a restart.
// usage: node tsb/test/relay-server.test.mjs   (needs python3)
import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import fs from 'node:fs';
import net from 'node:net';
import os from 'node:os';
import path from 'node:path';
import { main } from '../remote/send-command.mjs';

const here = path.dirname(new URL(import.meta.url).pathname);
const data = fs.mkdtempSync(path.join(os.tmpdir(), 'tsb-relay-'));
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

function start() {
    const p = spawn('python3', [path.join(here, '../relay/relay.py'), '--host', '127.0.0.1', '--port', '0', '--data', data], { stdio: ['ignore', 'pipe', 'inherit'] });
    return new Promise((resolve, reject) => {
        let out = '';
        p.stdout.on('data', (d) => {
            out += d;
            const m = /on 127\.0\.0\.1:(\d+)/.exec(out);
            if (m) resolve({ p, base: `http://127.0.0.1:${m[1]}` });
        });
        p.on('exit', (code) => reject(new Error(`relay exited with ${code}`)));
    });
}
const stop = (p) => new Promise((r) => (p.once('exit', r), p.kill()));

const results = [];
const test = async (name, fn) => {
    try {
        await fn();
        results.push(['ok', name]);
    } catch (e) {
        results.push(['FAIL', name, e]);
    }
};

let { p, base } = await start();
const json = async (r) => ({ status: r.status, body: await r.json() });
const list = async (t, q = 'sorting=newest&per_page=20') => json(await fetch(`${base}/token/${t}/requests?${q}`));
let cmd, res;

try {
    await test('addresses come from POST /token; unknown ones are 404 for posts and lists', async () => {
        const a = await json(await fetch(`${base}/token`, { method: 'POST' }));
        const b = await json(await fetch(`${base}/token`, { method: 'POST' }));
        assert.equal(a.status, 201);
        assert.match(a.body.uuid, /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/);
        [cmd, res] = [a.body.uuid, b.body.uuid];
        assert.deepEqual((await list(cmd)).body, { data: [], total: 0, per_page: 20, current_page: 1, is_last_page: true, from: null, to: null });
        const unknown = '00000000-0000-4000-8000-000000000009';
        assert.equal((await fetch(`${base}/${unknown}`, { method: 'POST', body: 'x' })).status, 404);
        assert.equal((await fetch(`${base}/token/${unknown}/requests`)).status, 404);
        assert.equal((await fetch(`${base}/token/${unknown}`)).status, 404);
    });

    await test('a post is listed the way webhook.site lists it, with the request id it answered with', async () => {
        const r = await fetch(`${base}/${cmd}`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{"p":"x","sig":"y"}' });
        assert.equal(r.status, 200);
        assert.equal(await r.text(), 'ok');
        assert.equal(r.headers.get('access-control-allow-origin'), '*');
        const id = r.headers.get('x-request-id');
        const { body } = await list(cmd);
        assert.equal(body.total, 1);
        const [x] = body.data;
        assert.equal(x.uuid, id);
        assert.equal(x.method, 'POST');
        assert.equal(x.content, '{"p":"x","sig":"y"}');
        assert.match(x.created_at, /^\d{4}-\d\d-\d\d \d\d:\d\d:\d\d$/);
        assert.ok(Math.abs(Date.parse(`${x.created_at.replace(' ', 'T')}Z`) - Date.now()) < 5e3, 'created_at is UTC');
        const pre = await fetch(`${base}/${cmd}`, { method: 'OPTIONS' });
        assert.equal(pre.status, 204);
        assert.equal((await list(cmd)).body.total, 1, 'a CORS preflight is not stored');
    });

    await test('newest / oldest first and pages', async () => {
        for (let i = 0; i < 4; i++) await fetch(`${base}/${res}`, { method: 'POST', body: `n${i}` });
        assert.deepEqual((await list(res, 'sorting=newest&per_page=3')).body.data.map((x) => x.content), ['n3', 'n2', 'n1']);
        const second = (await list(res, 'sorting=newest&per_page=3&page=2')).body;
        assert.deepEqual(second.data.map((x) => x.content), ['n0']);
        assert.equal(second.is_last_page, true);
        assert.deepEqual((await list(res, 'per_page=2')).body.data.map((x) => x.content), ['n0', 'n1'], 'oldest first by default');
    });

    await test('send-command.mjs ping --wait: the ack a fake extension posts for that request id', async () => {
        const done = { stop: false };
        const seen = new Set((await list(cmd)).body.data.map((x) => x.uuid));
        const extension = (async () => {
            while (!done.stop) {
                for (const x of (await list(cmd)).body.data) {
                    if (seen.has(x.uuid)) continue;
                    seen.add(x.uuid);
                    await fetch(`${base}/${res}`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ type: 'ack', id: x.uuid, cmd: 'ping', ok: true, ext: '0.7.0' }) });
                }
                await sleep(100);
            }
        })();
        const out = [], err = [];
        const code = await main(['ping', '--wait', '--timeout', '20'], {
            env: { TSB_KEY: 'k', TSB_CMD_URL: `${base}/${cmd}`, TSB_RESULT_URL: `${base}/${res}` },
            out: (s) => out.push(s), err: (s) => err.push(s)
        });
        done.stop = true;
        await extension;
        assert.equal(code, 0, err.join('\n'));
        assert.equal(out[0], 'ping: HTTP 200');
        assert.equal(JSON.parse(out.slice(2).join('\n')).ext, '0.7.0');
    });

    await test('a body over 4 MB is refused before it is read', async () => {
        const { port } = new URL(base);
        const head = await new Promise((resolve, reject) => {
            const s = net.connect(Number(port), '127.0.0.1', () => s.write(`POST /${res} HTTP/1.1\r\nHost: x\r\nContent-Length: ${(4 << 20) + 1}\r\n\r\n`));
            let got = '';
            s.on('data', (d) => (got += d));
            s.on('end', () => resolve(got.split('\r\n')[0]));
            s.on('error', reject);
        });
        assert.match(head, /^HTTP\/1\.[01] 413 /);
    });

    await test('a restart keeps the addresses and what they got', async () => {
        const before = (await list(res, 'sorting=newest&per_page=100')).body;
        await stop(p);
        ({ p, base } = await start());
        const after = (await list(res, 'sorting=newest&per_page=100')).body;
        assert.deepEqual(after, before);
        assert.equal((await json(await fetch(`${base}/token/${cmd}`))).body.uuid, cmd);
    });
} finally {
    await stop(p);
    fs.rmSync(data, { recursive: true, force: true });
}

let failed = 0;
for (const [s, name, e] of results) {
    console.log(`${s} ${name}`);
    if (e) failed++, console.log(e);
}
console.log(`${results.length - failed}/${results.length} passed`);
process.exit(failed ? 1 : 0);
