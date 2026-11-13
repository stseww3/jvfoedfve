import fs from 'node:fs';
const f = 'tsb-apex-squad.mjs';
let s = fs.readFileSync(f, 'utf8');
const orig = s;
const cnt = (sub) => s.split(sub).length - 1;
const bak = f + '.bak-coldstart';
if (!fs.existsSync(bak)) fs.writeFileSync(bak, s);

// 1) Raise donor recycle threshold 2 -> 5 so cold donors survive to first cf_clearance
const aOld = 'if (donor._mintFailCount >= 2) {';
if (cnt(aOld) !== 1) throw new Error('threshold anchor count=' + cnt(aOld));
s = s.replace(aOld, 'if (donor._mintFailCount >= 5) {');

// 2) Extend Turnstile solve window 14 -> 22 iterations (~9s -> ~14s) for slow cold challenges
const re = /for \(let i = 0; i < 14; i\+\+\) \{(\r?\n\s*await new Promise\(\(r\) => setTimeout\(r, 650\)\);)/;
if (!re.test(s)) throw new Error('solve-window anchor not found');
s = s.replace(re, 'for (let i = 0; i < 22; i++) {$1');

if (s === orig) throw new Error('no changes applied');
fs.writeFileSync(f, s);
console.log('PATCHED OK | threshold>=5:', cnt('donor._mintFailCount >= 5'), '| solveWin22:', cnt('i < 22; i++) {'), '| len:', s.length);
