import fs from 'node:fs';
const f = 'tsb-apex-squad.mjs';
let s = fs.readFileSync(f, 'utf8');
const orig = s;
const cnt = (x) => s.split(x).length - 1;
const bak = f + '.bak-gentlecf';
if (!fs.existsSync(bak)) fs.writeFileSync(bak, s);

function rep(oldStr, newStr, label){
  const n = cnt(oldStr);
  console.log(label + ' count=' + n);
  if (n !== 1) throw new Error(label + ' anchor not unique: ' + n);
  s = s.replace(oldStr, newStr);
}

// 1) token retry interval 15s/75s -> 90s/180s (stop hammering CF when a bot lacks a token)
rep('(c.isHeadless ? 15000 : 75000)', '(c.isHeadless ? 90000 : 180000)', 'retry-interval');
// 2) per-donor mint wave cap 2 -> 1 (one BiDi solve per donor at a time)
rep('if (cur < 2) {', 'if (cur < 1) {', 'donor-cap');
// 3) squad-sync wave cadence 3.5s -> 8s between waves
rep('now - lastSyncLaunch > 3500', 'now - lastSyncLaunch > 8000', 'wave-cadence');
// 4) reloadingForFreshTokens reset 3.2s -> 7s
rep('setTimeout(() => { reloadingForFreshTokens = false; }, 3200);', 'setTimeout(() => { reloadingForFreshTokens = false; }, 7000);', 'reload-reset');

if (s === orig) throw new Error('no changes');
fs.writeFileSync(f, s);
console.log('GENTLE-CF OK | 90000:' + cnt('90000') + ' | cur<1:' + cnt('if (cur < 1) {') + ' | >8000:' + cnt('lastSyncLaunch > 8000') + ' | 7000:' + cnt(', 7000);') + ' | len:' + s.length);
