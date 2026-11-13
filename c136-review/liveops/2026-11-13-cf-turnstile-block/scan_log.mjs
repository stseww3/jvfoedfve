// Scan an engine log (can be hundreds of MB): count the token / lobby / Redacted events and show
// the first lines of one bot, so the real token consumption and the Redacted history can be read off.
// Token values are never printed (long runs of token-like characters are masked).
// Run with cwd = c116:  node_apex.exe ..\c136\scan_log.mjs <logfile> [botNameNeedle] [firstN]
import fs from 'node:fs';
import readline from 'node:readline';

const file = process.argv[2];
const needle = process.argv[3] || 'ryan_m';
const firstN = Number(process.argv[4] || 30);
const safe = (l, n = 170) => l.replace(/[A-Za-z0-9_\-.]{40,}/g, '<MASK>').replace(/[^\x20-\x7e]/g, '?').slice(0, n);
const keys = ['Requesting Turnstile token', 'Fresh Turnstile token ready', 'Turnstile mint error', 'BiDi mint timeout', 'chain step', 'hard timeout 90s',
  'sendTokenToLobby', 'Launching Mozilla Firefox', 'Connected to Mozilla Firefox BiDi', 'recycling Firefox donor', '[SELF-CHECK REDACTED]', '[SELF-CHECK OK]', '[ERR]'];
const out = { file: String(file).split(/[\\/]/).pop(), lines: 0, counts: {}, samples: {}, redacted: { shapes: {}, bots: 0, top: [], okAfterRedacted: 0, redactedAgainWithoutOk: 0, stillRedactedAtEnd: 0 }, stops: {}, first: [] };
for (const k of keys) out.counts[k] = 0;
const perBot = new Map();
const pendingRed = new Set();
const rl = readline.createInterface({ input: fs.createReadStream(file, { encoding: 'utf8', highWaterMark: 1 << 20 }) });
rl.on('line', (l) => {
  out.lines++;
  for (const k of keys) {
    if (l.includes(k)) {
      out.counts[k]++;
      if (k === 'sendTokenToLobby' || k === '[SELF-CHECK REDACTED]' || k === 'Turnstile mint error') {
        const arr = (out.samples[k] = out.samples[k] || []);
        if (arr.length < 3) arr.push(safe(l));
      }
    }
  }
  if (l.includes('[SELF-CHECK REDACTED]')) {
    const m = /\] (.+?) banned as "([^"]*)"/.exec(l);
    if (m) {
      const shape = m[2].replace(/Redacted\s+\S+/, 'Redacted XX').replace(/\d+/g, 'N').replace(/[^\x20-\x7e]/g, '?');
      out.redacted.shapes[shape] = (out.redacted.shapes[shape] || 0) + 1;
      perBot.set(m[1], (perBot.get(m[1]) || 0) + 1);
      if (pendingRed.has(m[1])) out.redacted.redactedAgainWithoutOk++;
      pendingRed.add(m[1]);
    }
  } else if (l.includes('[SELF-CHECK OK]')) {
    const m = /\] (.+?) verified in Room 0/.exec(l);
    if (m && pendingRed.delete(m[1])) out.redacted.okAfterRedacted++;
  }
  const sm = /stopped[^0-9]{0,40}(4591|4577|4555|4215|1006)/.exec(l);
  if (sm) out.stops[sm[1]] = (out.stops[sm[1]] || 0) + 1;
  if (out.first.length < firstN && l.includes(needle)) out.first.push(safe(l));
});
rl.on('close', () => {
  out.redacted.bots = perBot.size;
  out.redacted.top = Array.from(perBot.entries()).sort((a, b) => b[1] - a[1]).slice(0, 6).map(([n, c]) => `${n.replace(/[^\x20-\x7e]/g, '?')} x${c}`);
  out.redacted.stillRedactedAtEnd = pendingRed.size;
  console.log(JSON.stringify(out));
});
