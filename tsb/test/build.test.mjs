// apply-remote.mjs builds A (remote + allowlist) and B (singleplayer only) from base-0.5.3.
// usage: node tsb/test/build.test.mjs
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { CLOSE_PATCH } from '../remote/lobby-patch.mjs';

const tsb = path.join(new URL('.', import.meta.url).pathname, '..');
const out = fs.mkdtempSync(path.join(os.tmpdir(), 'tsb-build-'));
const build = (flags, dir) => execFileSync(process.execPath, [path.join(tsb, 'remote/apply-remote.mjs'), ...flags, path.join(tsb, 'base-0.5.3'), dir], { encoding: 'utf8' });

try {
    for (const [v, flags] of [['A', []], ['B', ['--single-only']]]) {
        const dir = path.join(out, v);
        build(flags, dir);
        const m = JSON.parse(fs.readFileSync(path.join(dir, 'manifest.json'), 'utf8'));
        assert.equal(m.version, '0.6.9');
        assert.deepEqual(m.permissions, ['scripting']);
        assert.deepEqual(m.host_permissions, ['http://127.0.0.1/*', 'https://webhook.site/*', 'https://territorial.io/*']);
        assert.ok(m.description.length <= 132);
        const page = fs.readFileSync(path.join(dir, 'page.js'), 'utf8');
        new Function(page);
        assert.ok(page.includes('ke=()=>be("tsb-control",JSON.stringify({kind:"connect",port:"backend"===ue.strategy?ue.port:null}))'));
        assert.ok(page.includes(`const SINGLE_ONLY = ${v === 'B' ? '!0' : '!1'};`));
        assert.ok(page.includes('manual:!1,armed:!1,stay:!1,'), 'stay is off until chosen');
        assert.ok(page.includes('version:"0.6.9",remote:Re,setPort(t){'));
        assert.ok(page.includes(CLOSE_PATCH), 'the socket close hook is in');
        for (const f of ['relay.js', 'background.js']) assert.equal(fs.readFileSync(path.join(dir, f), 'utf8'), fs.readFileSync(path.join(tsb, 'remote', f), 'utf8'));
        console.log(`ok ${v}: ${m.version_name}`);
    }
} finally {
    fs.rmSync(out, { recursive: true, force: true });
}
console.log('build: ok');
