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
//
// After I die or the game ends, an armed bot leaves the game by itself 3 seconds later.
//
// options: --key <key> (or env TSB_KEY), --url <command webhook> (or env TSB_CMD_URL),
//          --seq <n>, --name <strategy name>, --print (print the body, do not send)
import { createHmac, randomBytes } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { basename } from 'node:path';

const args = process.argv.slice(2);
const cmd = args.shift();
const opt = {};
for (let i = 0; i < args.length; i++) {
    const a = args[i];
    if (!a.startsWith('--')) throw new Error(`unexpected argument ${a}`);
    const k = a.slice(2);
    opt[k] = ['single', 'mp', 'print'].includes(k) ? true : args[++i];
}
if (!['ping', 'start', 'stop', 'end'].includes(cmd)) {
    console.error('usage: node send-command.mjs <ping|start|stop|end> [--single | --mp] [--strategy file.js] [--use v3] [--seq n] [--key k] [--url u] [--print]');
    process.exit(2);
}
if (opt.single && opt.mp) throw new Error('--single and --mp do not go together');
const key = opt.key || process.env.TSB_KEY;
const url = opt.url || process.env.TSB_CMD_URL;
if (!key) throw new Error('no key: pass --key or set TSB_KEY');
if (!url && !opt.print) throw new Error('no command webhook: pass --url or set TSB_CMD_URL');

const c = { cmd, ts: Date.now(), nonce: randomBytes(12).toString('base64url') };
if (opt.seq !== undefined) c.seq = Number(opt.seq);
if (opt.strategy) {
    c.strategy = readFileSync(opt.strategy, 'utf8');
    c.name = opt.name || basename(opt.strategy).replace(/\.m?js$/i, '');
}
if (opt.use) c.use = opt.use;
if (opt.single) c.single = true;
if (opt.mp) c.mp = true;

const p = JSON.stringify(c);
const sig = createHmac('sha256', key).update(p).digest('base64url');
const body = JSON.stringify({ p, sig });
if (opt.print) {
    console.log(body);
} else {
    const r = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body });
    console.log(`${cmd}: HTTP ${r.status}`);
    if (!r.ok) process.exit(1);
}
