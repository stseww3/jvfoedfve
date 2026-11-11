// 调试：引擎 AI（含「真人离线后由 AI 接管的空壳」）给队友送兵的全部记录（真值重演）。
// 用法：node dbg/husk-gifts.mjs <mid> [--json 输出文件]
// 引擎口径：bots.js botAttackTeam L142~170：AI 在陆上没有可打的目标、发不了船、翻不了山时走 botDonate（L180~200）；
//   真人席位（离线空壳）给的是「全部余额」（L185 dn = B），手续费 64/1024（game.js transfer L388~395），不占受捐额度，
//   只受对方硬上限 150×领土 的余量限制；优先给「最近在交战」的队友（recentWar），其次给「有船在海上」的队友。
// 这类到账不在录像指令里（不是玩家指令），所以 cmdLog/日志里都看不到，只能在重演里挂钩子数。
import fs from 'node:fs';
import { resim } from '../resim.mjs';

const args = process.argv.slice(2);
const mid = args[0];
const jsonIdx = args.indexOf('--json');
const rows = [];
let hooked = false;
const R = resim(mid, {
  onState: (g) => {
    if (hooked) return;
    hooked = true;
    const orig = g.botGive;
    g.botGive = function (p, q, dn) {
      const bq = this.bal[q], bp = this.bal[p];
      const r = orig.call(this, p, q, dn);
      const got = this.bal[q] - bq;
      if (got > 0) rows.push([this.t, p, q, got, bp - this.bal[p] - got, bp, this.terr[p], bq, this.terr[q]]);
      return r;
    };
  },
});
const names = R.names, H = R.H, teams = R.teams;
const sq = new Map(Object.entries(R.squad).map(([b, s]) => [s.id, b]));
const nm = (q) => (sq.has(q) ? sq.get(q) : q < H ? `${(names[q] || '?').slice(0, 12)}#${q}T${teams[q]}${R.leftT[q] > 0 ? '(离线' + R.leftT[q] + ')' : ''}` : `AI${q}`);
const k = (x) => (Math.abs(x) >= 1e6 ? (x / 1e6).toFixed(2) + 'M' : Math.abs(x) >= 1e4 ? Math.round(x / 1e3) + 'k' : String(x));
const toSquad = rows.filter((r) => sq.has(r[2]));
console.log(`AI/空壳送兵共 ${rows.length} 次，到账合计 ${k(rows.reduce((s, r) => s + r[3], 0))}；其中送给本编队号 ${toSquad.length} 次，到账 ${k(toSquad.reduce((s, r) => s + r[3], 0))}`);
const byPair = new Map();
for (const r of rows) {
  const key = `${nm(r[1])} → ${nm(r[2])}`;
  const a = byPair.get(key) || [0, 0, 0, r[0], r[0]];
  a[0]++; a[1] += r[3]; a[2] += r[4]; a[4] = r[0];
  byPair.set(key, a);
}
console.log('按 送出方 → 接收方 汇总（次数、到账、手续费、首末拍）：');
for (const [key, a] of [...byPair].sort((x, y) => y[1][1] - x[1][1]).slice(0, 40)) console.log(`  ${key}: ${a[0]} 次 到账 ${k(a[1])} 费 ${k(a[2])} | ${a[3]}~${a[4]}`);
console.log('送给本编队号的逐条（拍、送出方、接收方、到账、送出方原余额/领土、接收方原余额/领土、到账后是否顶到硬上限）：');
for (const r of toSquad) console.log(`  t=${r[0]} ${nm(r[1])} → ${nm(r[2])} 到账 ${r[3]}（送出方 ${k(r[5])}/${r[6]} 格；接收方 ${k(r[7])}/${r[8]} 格 → ${r[7] + r[3] >= 150 * r[8] ? '顶到硬上限 ' + 150 * r[8] : '未到硬上限'}）`);
if (jsonIdx >= 0) fs.writeFileSync(args[jsonIdx + 1], JSON.stringify({ mid, rows }));
