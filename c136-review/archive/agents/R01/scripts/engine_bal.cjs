#!/usr/bin/env node
// engine_bal.cjs — 用线上引擎原文（总部的 engine_replay.cjs）把一局录像重放到指定区间，逐拍打印几个号的领土 / 余额。
// 用途：核对“非决策拍（t%5≠0）上重演的余额是否和真引擎一致”——日志只在 5 的倍数拍上留有余额，别的拍只能靠真引擎。
// 用法：node engine_bal.cjs <matchId> --bots riku_x,kaito9 --t0 11900 --t1 11910 [--replay 另一局的录像]
// 输出：每拍一行：t  名字 领土 余额 …（余额取自引擎自己的状态数组 ah.hb，时刻 = 该拍结算完成之后）
//       拍号口径：引擎 bi.kr() 的值；和 resim / 日志 [HL-TICK] 的拍号是否同一口径，用 --check 在 90 的倍数拍上与日志对一下。
const path = require('path');
const fs = require('fs');
const { startReplay, DATA } = require('/agent/repos/c136-data/src/tools/engine_replay.cjs');

const a = process.argv.slice(2);
const opt = (k, d) => { const i = a.indexOf('--' + k); return i >= 0 ? a[i + 1] : d; };
const mid = a[0];
const rep = opt('replay', mid);
const bots = (opt('bots', '') || '').split(',').filter(Boolean);
const t0 = +opt('t0', 0), t1 = +opt('t1', t0 + 10);

const { info, api } = startReplay(rep, { echo: false });
const names = api.names();
const ids = bots.map((b) => {
  const hit = [];
  for (let p = 0; p < names.length; p++) if (String(names[p]).replace(/^\[[^\]]*\]\s*/, '') === b || names[p] === b) hit.push(p);
  if (hit.length !== 1) { console.error(`找不到唯一的 ${b}：`, hit); process.exit(1); }
  return hit[0];
});
// 先走完出生阶段，再走到 t0
let [t, spawning, st] = api.advance(0);
let guard = 0;
while (spawning && guard++ < 5000) [t, spawning, st] = api.advance(1);
while (t < t0 && st !== 2) [t, spawning, st] = api.advance(Math.min(500, t0 - t));
const logSnap = {};
if (a.includes('--check')) {
  const re = /\[([^\]]+)\] \[HL-TICK\] t=(\d+) terr=(\d+)\([^)]*\) bal=(\d+)/;
  for (const line of fs.readFileSync(path.join(DATA, mid, 'in_game.log'), 'utf8').split('\n')) {
    const m = re.exec(line);
    if (m) logSnap[m[1] + '@' + m[2]] = [+m[3], +m[4]];
  }
}
console.log(`# ${mid} 真引擎逐拍：${bots.map((b, i) => b + '#' + ids[i]).join(' ')}`);
for (;;) {
  const s = api.snap(ids);
  let line = `t=${t}`;
  bots.forEach((b, i) => {
    line += `  ${b} terr=${s[4 * i]} bal=${s[4 * i + 1]}`;
    const k = logSnap[b + '@' + t];
    if (k) line += k[0] === s[4 * i] && k[1] === s[4 * i + 1] ? ' [=日志]' : ` [日志 terr=${k[0]} bal=${k[1]}]`;
  });
  console.log(line);
  if (t >= t1 || st === 2) break;
  [t, spawning, st] = api.advance(1);
}
