#!/usr/bin/env node
// Sends a signed command to the extension's command webhook (Node 18+).
//
//   node send-command.mjs ping
//   node send-command.mjs start                         arm the bot (current / next game)
//   node send-command.mjs start --single                arm and start a singleplayer game now, and a new one after each game
//   node send-command.mjs start --mp                    arm, go to the battle royale lobby and press Ready, again after each game
//                                                       (allowlist build only; the bot plays only when every other human is on the allowlist)
//   node send-command.mjs start --strategy my.js        import my.js (class Policy), select it, arm
//   node send-command.mjs start --use v3                select a strategy the extension already has, arm
//   node send-command.mjs stop                          the bot stops (un-readies in the lobby), the game goes on
//   node send-command.mjs end                           the bot stops and leaves the game or the lobby
//   node send-command.mjs lobby                         reload the game page (stuck on an error page, a frozen game);
//                                                       a loop goes on afterwards, without one the allowlist build opens the battle royale lobby
//
// After I die or the game ends, an armed bot leaves the game by itself 3 seconds later.
// With a loop on (--mp / --single), a page stuck for a while (1006, Lobby Timeout, a frozen game) reloads by itself;
// the game's bot detection, bans, kicks and a second login stop the loop instead.
//
// The extension answers every command with an "ack" on the result webhook. With --wait this waits for that
// answer and prints it, or says where it got stuck; the result webhook has to be a webhook.site address:
//   node send-command.mjs ping --wait                   (result webhook from --result or env TSB_RESULT_URL)
// exit codes: 0 sent (with --wait: answered ok), 1 not sent or answered with an error, 2 usage, 3 no answer in time
//
// options: --key <key> (or env TSB_KEY), --url <command webhook> (or env TSB_CMD_URL),
//          --seq <n>, --name <strategy name>, --print (print the body, do not send),
//          --wait, --result <result webhook> (or env TSB_RESULT_URL), --timeout <seconds, default 90>
import { createHmac, randomBytes } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { basename } from 'node:path';
import { pathToFileURL } from 'node:url';

const CMDS = ['ping', 'start', 'stop', 'end', 'lobby'];
const FLAGS = ['single', 'mp', 'print', 'wait'];
const USAGE = 'usage: node send-command.mjs <ping|start|stop|end|lobby> [--single | --mp] [--strategy file.js] [--use v3] [--seq n] [--key k] [--url u] [--wait [--result u] [--timeout s]] [--print]';
const UUID = /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/i;
// the extension polls every 3 s, but a minimized or background tab may poll only about once a minute
const TIMEOUT_S = 90;

// the webhook.site API address that lists what the result webhook received, newest first
function resultApi(raw) {
    const s = String(raw || '').trim(), m = UUID.exec(s);
    if (!m || !(s === m[0] || /^https:\/\/(www\.)?webhook\.site\//i.test(s))) {
        throw new Error('--wait reads the result webhook through the webhook.site API: pass --result <webhook.site address or token> or set TSB_RESULT_URL');
    }
    return `https://webhook.site/token/${m[0]}/requests?sorting=newest&per_page=50`;
}

const body = (x) => {
    try {
        return JSON.parse(x.content);
    } catch {
        return null;
    }
};

async function listRequests(fetch, api) {
    try {
        const r = await fetch(api, { headers: { Accept: 'application/json' } });
        if (r.status !== 200) return { status: r.status, list: [] };
        const d = await r.json();
        return { status: 200, list: Array.isArray(d && d.data) ? d.data : [] };
    } catch (e) {
        return { status: 0, list: [], error: String((e && e.message) || e) };
    }
}

// why no answer came, from what the result webhook got lately
function diagnose(list, t, timeout) {
    const age = (x) => Math.round((t - Date.parse(`${String(x.created_at).replace(' ', 'T')}Z`)) / 1e3);
    const recent = list.filter((x) => age(x) < 600);
    const lines = [`no answer from the extension within ${Math.round(timeout / 1e3)} s.`];
    if (recent.some((x) => x.method === 'OPTIONS')) {
        lines.push('The result webhook got empty OPTIONS requests: a game tab runs an extension older than 0.6.8 (or was not refreshed after an update) and posts from the page, which CORS blocks. Install 0.6.8 and refresh the game tab once.');
    }
    const last = recent.map((x) => ({ x, b: body(x) })).find(({ b }) => b && b.ext);
    if (last) {
        lines.push(`The extension is posting (last: ${last.b.type}, ${age(last.x)} s ago, version ${last.b.ext}), so a game tab is in manual mode, but it did not answer this command. Check that the panel's 指令 webhook is this command webhook, and that the browser clock is right (commands that look older than 12 minutes are dropped unanswered). A minimized tab polls slowly: try a longer --timeout. The panel's 指令 / 上条指令 rows show what it last did.`);
    } else {
        lines.push('Nothing from the extension on the result webhook in the last 10 minutes: no game tab polls this command webhook (game page closed, 手动（远程） off, another 指令 address in the panel) or the extension cannot reach webhook.site. The panel\'s 指令 row says which.');
    }
    return lines.join('\n');
}

export async function main(argv, io = {}) {
    const {
        env = process.env, fetch = globalThis.fetch, now = Date.now,
        sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms)),
        out = (s) => console.log(s), err = (s) => console.error(s)
    } = io;
    const args = argv.slice();
    const cmd = args.shift();
    const opt = {};
    for (let i = 0; i < args.length; i++) {
        const a = args[i];
        if (!a.startsWith('--')) throw new Error(`unexpected argument ${a}`);
        const k = a.slice(2);
        opt[k] = FLAGS.includes(k) ? true : args[++i];
    }
    if (!CMDS.includes(cmd)) {
        err(USAGE);
        return 2;
    }
    if (opt.single && opt.mp) throw new Error('--single and --mp do not go together');
    const key = opt.key || env.TSB_KEY;
    const url = opt.url || env.TSB_CMD_URL;
    if (!key) throw new Error('no key: pass --key or set TSB_KEY');
    if (!url && !opt.print) throw new Error('no command webhook: pass --url or set TSB_CMD_URL');
    const api = opt.wait && !opt.print ? resultApi(opt.result || env.TSB_RESULT_URL) : null;
    const timeout = 1e3 * (opt.timeout === undefined ? TIMEOUT_S : Number(opt.timeout));
    if (!(timeout >= 0)) throw new Error('--timeout takes seconds');

    const c = { cmd, ts: now(), nonce: randomBytes(12).toString('base64url') };
    if (opt.seq !== undefined) c.seq = Number(opt.seq);
    // to find the answer when the command webhook gives no request id (not webhook.site)
    else if (api) c.seq = randomBytes(4).readUInt32BE() >>> 1;
    if (opt.strategy) {
        c.strategy = readFileSync(opt.strategy, 'utf8');
        c.name = opt.name || basename(opt.strategy).replace(/\.m?js$/i, '');
    }
    if (opt.use) c.use = opt.use;
    if (opt.single) c.single = true;
    if (opt.mp) c.mp = true;

    const p = JSON.stringify(c);
    const sig = createHmac('sha256', key).update(p).digest('base64url');
    const payload = JSON.stringify({ p, sig });
    if (opt.print) {
        out(payload);
        return 0;
    }
    const r = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: payload });
    out(`${cmd}: HTTP ${r.status}${r.status === 404 ? ' (no such command webhook, or it has expired)' : ''}`);
    if (!r.ok) return 1;
    if (!api) {
        err('the answer goes to the result webhook; --wait waits for it here');
        return 0;
    }

    // webhook.site's id for this request is the id the extension puts in its ack
    const id = r.headers.get('x-request-id');
    const t0 = now();
    let seen = [];
    for (;;) {
        const got = await listRequests(fetch, api);
        if (got.status === 200) {
            seen = got.list;
            const ack = seen.map(body).find((b) => b && b.type === 'ack' && (id ? b.id === id : b.seq === c.seq && b.cmd === cmd));
            if (ack) {
                out(`answer after ${Math.round((now() - t0) / 1e3)} s:`);
                out(JSON.stringify(ack, null, 2));
                return ack.ok ? 0 : 1;
            }
        } else if (got.status === 404) {
            err('result webhook: no such webhook.site address, or it has expired');
            return 1;
        } else if (got.status === 401 || got.status === 403) {
            err(`result webhook: HTTP ${got.status}, the address needs a password or an API key`);
            return 1;
        }
        if (now() - t0 >= timeout) break;
        await sleep(got.status === 429 ? 5000 : 2000);
    }
    err(diagnose(seen, now(), timeout));
    return 3;
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) process.exit(await main(process.argv.slice(2)));
