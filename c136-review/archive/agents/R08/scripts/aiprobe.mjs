// aiprobe.mjs —— 真引擎重演里盯住「某个内置 AI（或空壳）打某个号」这一对：每一圈推进是不是新开的进攻（fresh）、
// 这一圈的钱是从余额/进攻兵里出的还是赊账（takeBalance 余额不够时记 debt，上限 5 万）、对方有没有反击兵压着。
// 用法：node aiprobe.mjs <matchId> --ai <玩家号> --bot <名字> [--peer-tag TAG] [--replay-from M] [--win 150]
import { resim } from './resim_r08.mjs';

const args = process.argv.slice(2);
const mid = args[0];
const opt = (k, d) => (args.includes(`--${k}`) ? args[args.indexOf(`--${k}`) + 1] : d);
const ai = +opt('ai', -1), botName = opt('bot', null), WIN = +opt('win', 150);
if (!mid || ai < 0 || !botName) { console.error('用法：node aiprobe.mjs <matchId> --ai <玩家号> --bot <名字> [--win 150]'); process.exit(2); }
let me = -1;
const rows = new Map(); // window -> acc
const acc = (t) => {
  const w = Math.floor(t / WIN) * WIN;
  let r = rows.get(w);
  if (!r) { r = { w, starts: 0, rings: 0, freeRings: 0, cells: 0, dBal: 0, burnt: 0, owed: 0, counterMax: 0, lostRings: 0 }; rows.set(w, r); }
  return r;
};
let inPair = false, owedNow = 0;
const out = resim(mid, {
  replayFrom: opt('replay-from', null), peer: opt('peer', null), peerTag: opt('peer-tag', null),
  onStart: (g, ctx) => {
    me = ctx.squad[botName] ? ctx.squad[botName].id : -1;
    const prevExpand = g.expandAttack, prevTake = g.takeBalance;
    g.takeBalance = function (p, v) {
      if (inPair && p === ai && v > this.bal[p]) owedNow += v - this.bal[p];
      return prevTake.call(this, p, v);
    };
    g.expandAttack = function (p, a) {
      const k = this.slotBase(p) + a;
      if (p !== ai || this.atkTarget[k] !== me) return prevExpand.call(this, p, a);
      const fresh = this.atkFresh[k];
      const own0 = this.totalAttackTroops(p) + this.bal[p], terr0 = this.terr[p], b0 = this.bal[me];
      const counter = this.attackTroopsOn(me, p);
      inPair = true; owedNow = 0;
      prevExpand.call(this, p, a);
      inPair = false;
      const r = acc(this.t);
      const tiles = this.terr[p] - terr0;
      if (fresh) r.starts++;
      if (tiles > 0) { r.rings++; r.cells += tiles; if (owedNow > 0) r.freeRings++; } else r.lostRings++;
      r.dBal += b0 - this.bal[me];
      r.burnt += own0 - (this.totalAttackTroops(p) + this.bal[p]);
      r.owed += owedNow;
      if (counter > r.counterMax) r.counterMax = counter;
    };
  },
  onTick: (g) => {
    if (g.t % WIN === WIN - 1) {
      const r = acc(g.t);
      r.aiBal = g.bal[ai]; r.aiDebt = g.debt[ai]; r.aiTerr = g.terr[ai]; r.botBal = g.bal[me]; r.botTerr = g.terr[me]; r.aiAlive = g.alive[ai];
    }
  },
});
console.log(`${mid} AI${ai} → ${botName}(${me})：窗口 | 新开进攻 次 | 推进成功 圈/格 | 其中靠赊账赢的 圈 | 没推动 圈 | AI 实际耗兵 | 赊的兵 | 号的余额被打掉 | 号压在 AI 身上的反击兵 最大 | 窗口末：AI 格/余额/欠账，号 格/余额`);
let tot = { starts: 0, rings: 0, cells: 0, freeRings: 0, burnt: 0, owed: 0, dBal: 0 };
for (const r of [...rows.values()].sort((a, b) => a.w - b.w)) {
  for (const k of Object.keys(tot)) tot[k] += r[k];
  if (r.starts + r.rings + r.lostRings === 0) continue;
  console.log(`  ${r.w}~${r.w + WIN} | ${r.starts} | ${r.rings}/${r.cells} | ${r.freeRings} | ${r.lostRings} | ${r.burnt} | ${r.owed} | ${r.dBal} | ${r.counterMax} | ${r.aiTerr ?? '-'}/${r.aiBal ?? '-'}/${r.aiDebt ?? '-'}，${r.botTerr ?? '-'}/${r.botBal ?? '-'}`);
}
console.log(`  合计：新开进攻 ${tot.starts} 次，推进成功 ${tot.rings} 圈 ${tot.cells} 格，其中靠赊账赢的 ${tot.freeRings} 圈；AI 实际耗兵 ${tot.burnt}，赊的兵 ${tot.owed}；号的余额被打掉 ${tot.dBal}`);
