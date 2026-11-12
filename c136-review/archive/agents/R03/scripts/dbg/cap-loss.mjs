// 调试：硬上限（150×领土）吃掉的兵——引擎 addBalance（game.js L752-764）把入账截到 150×领土 − 余额，多出来的直接没了。
// 真值重演里挂钩子，按入账来源分开数「要入账的兵」和「实际入账的兵」：
//   退兵   endAttack（game.js L1076-1080：进攻打完/和目标不再相邻，槽里剩的兵回余额）、cancelAttack（L852-856）
//   靠己岸 boats.js landAt L268-271（船靠在自己的地上，船上的兵回余额）
//   利息   game.js L783（每 10 拍）与 L788
//   其它   transfer（捐款，receiverRoom 已先截过）、botGive、靠队友岸移交等
// 用法：node dbg/cap-loss.mjs <mid> [--list N] [--all]
//   默认只打本房间编队号；--all 把全部真人按队汇总也打出来；--list N 打损失最大的 N 条明细（默认 12）
import { resim } from '../resim.mjs';

const args = process.argv.slice(2);
const mid = args[0];
const listN = args.includes('--list') ? +args[args.indexOf('--list') + 1] : 12;
const showAll = args.includes('--all');
const rows = []; // [t, p, src, want, got, balBefore, terr]
let hooked = false;
let ctxSrc = null;
const R = resim(mid, {
  onState: (g) => {
    if (hooked) return;
    hooked = true;
    const wrap = (name, src) => {
      const orig = g[name];
      if (typeof orig !== 'function') return;
      g[name] = function (...a) {
        const prev = ctxSrc;
        ctxSrc = src;
        try { return orig.apply(this, a); } finally { ctxSrc = prev; }
      };
    };
    wrap('endAttack', '退兵');
    wrap('cancelAttack', '退兵');
    wrap('landAt', '靠岸');
    wrap('transfer', '捐款');
    wrap('botGive', '空壳送兵');
    const origAdd = g.addBalance;
    g.addBalance = function (p, v) {
      const b0 = this.bal[p], L = this.terr[p];
      const got = origAdd.call(this, p, v);
      if (p < this.humans && v > 0 && got < v) rows.push([this.t, p, ctxSrc || '利息', v, got, b0, L]);
      return got;
    };
  },
});
const names = R.names, H = R.H, teams = R.teams;
const sq = new Map(Object.entries(R.squad).filter(([, s]) => s.id >= 0 && !s.mismatch).map(([b, s]) => [s.id, b]));
const nm = (q) => (sq.has(q) ? sq.get(q) : `${(names[q] || '?').slice(0, 12)}#${q}T${teams[q]}`);
const k = (x) => (Math.abs(x) >= 1e6 ? (x / 1e6).toFixed(2) + 'M' : Math.abs(x) >= 1e4 ? Math.round(x / 1e3) + 'k' : Math.abs(x) >= 1e3 ? (x / 1e3).toFixed(1) + 'k' : String(x));
const SRC = ['退兵', '靠岸', '利息', '捐款', '空壳送兵'];
const sumBy = (rs) => {
  const o = {};
  for (const s of SRC) o[s] = [0, 0, 0];
  for (const r of rs) { const a = o[r[2]] || (o[r[2]] = [0, 0, 0]); a[0]++; a[1] += r[3]; a[2] += r[3] - r[4]; }
  return o;
};
const fmt = (o) => SRC.filter((s) => o[s][0] > 0).map((s) => `${s} ${o[s][0]} 次 要入账 ${k(o[s][1])} 没入账 ${k(o[s][2])}`).join('；') || '无';
console.log(`# ${mid} 硬上限吃掉的兵（cap-loss.mjs；addBalance 把入账截到 150×领土 − 余额；只记「要入账 > 实际入账」的那些次）`);
const sqRows = rows.filter((r) => sq.has(r[1]));
console.log(`  编队合计：${fmt(sumBy(sqRows))}`);
for (const [id, b] of [...sq].sort((x, y) => x[0] - y[0])) {
  const rs = sqRows.filter((r) => r[1] === id);
  if (!rs.length) continue;
  console.log(`  ${b}：${fmt(sumBy(rs))}`);
}
const big = sqRows.filter((r) => r[2] !== '利息').sort((a, b) => (b[3] - b[4]) - (a[3] - a[4])).slice(0, listN);
console.log(`  编队号里没入账最多的 ${big.length} 条（不含利息）：拍 号 来源 要入账 → 实际入账（没入账） | 入账前余额 / 领土（密度）`);
for (const r of big) console.log(`    ${r[0]} ${nm(r[1])} ${r[2]} ${k(r[3])} → ${k(r[4])}（没入账 ${k(r[3] - r[4])}） | ${k(r[5])} / ${r[6]} 格（${(r[5] / Math.max(1, r[6])).toFixed(0)}）`);
if (showAll) {
  const nT = Math.max(...teams.slice(0, H));
  for (let T = 1; T <= nT; T++) {
    const rs = rows.filter((r) => teams[r[1]] === T && !sq.has(r[1]));
    console.log(`  队${T}（不含编队号）：${fmt(sumBy(rs))}`);
  }
}
