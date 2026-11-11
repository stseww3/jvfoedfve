// sea_landings.mjs — 谁从海上登陆到本队的地上：记录每一条靠在本队某个号领土上的敌方船（引擎 boats.js landAt → addAttack）。
// 用法：node sea_landings.mjs <matchId> [--replay id] [--log id1,id2] [--bots a,b] [--min 0]
// 输出 out/<matchId>/sea_landings.csv：t,owner,ownerTeam,ownerTerr,ownerBal,troops,x,y,bot,botTerr,botBal,botDens,hadLandBorder
//   hadLandBorder = 登陆那一拍之前，这个对手和这个号有没有陆地接壤（0 = 这条船是它第一次碰到这个号）
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { openMatch, readLogSnaps, P_INNER } from './resim_lib.mjs';

const args = process.argv.slice(2);
const mid = args[0];
const opt = (k, d) => (args.includes(`--${k}`) ? args[args.indexOf(`--${k}`) + 1] : d);
const HERE = path.dirname(fileURLToPath(import.meta.url));
const OUT = path.resolve(HERE, '..', 'out', mid);
fs.mkdirSync(OUT, { recursive: true });
const m = openMatch(mid, { replay: opt('replay', mid) });
const { g, H } = m;
const onlyBots = opt('bots', '') ? new Set(opt('bots', '').split(',')) : null;
const minTroops = +opt('min', 0);
const squad = {};
for (const lb of opt('log', mid).split(',')) {
  const { me } = readLogSnaps(lb, lb === mid ? '' : lb + ':', onlyBots);
  for (const [b, p] of Object.entries(me)) squad[(lb === mid ? '' : lb + ':') + b] = p;
}
const label = Object.fromEntries(Object.entries(squad).map(([b, p]) => [p, b]));
const W = g.W;
const touches = (a, b) => {
  // a 的边界格有没有挨着 b 的格
  const d = g.dir4, own = g.own, px = g.px;
  for (const c of g.border[a] || []) for (let k = 0; k < 4; k++) { const n = c + d[k]; if (px[n] >= P_INNER && own[n] === b) return true; }
  return false;
};
const out = [];
const landAt0 = g.landAt.bind(g);
g.landAt = function (p, troops, c, at) {
  const v = this.px[c];
  if (v >= P_INNER) {
    const o = this.own[c];
    if (label[o] !== undefined && this.isEnemy(p, o) && troops >= minTroops) {
      out.push({ t: this.t, p, troops, x: c % W, y: Math.floor(c / W), o, oTerr: this.terr[o], oBal: this.bal[o], pTerr: this.terr[p], pBal: this.bal[p], had: touches(o, p) ? 1 : 0 });
    }
  }
  return landAt0(p, troops, c, at);
};
while (m.tick());
const nm = (p) => (p < H ? m.names[p] : `AI#${p}`);
const rows = ['t,owner,ownerTeam,ownerTerr,ownerBal,troops,x,y,bot,botTerr,botBal,botDens,hadLandBorder'];
console.log(`# ${mid} 敌方船在本队领土登陆 ${out.length} 条`);
console.log('     t 对手/队                         对手领土   对手余额     船上兵  登陆点        本队号    领土     余额   密度  此前陆地接壤');
for (const r of out) {
  rows.push([r.t, JSON.stringify(nm(r.p)), g.teams[r.p], r.pTerr, r.pBal, r.troops, r.x, r.y, label[r.o], r.oTerr, r.oBal, (r.oBal / Math.max(1, r.oTerr)).toFixed(1), r.had].join(','));
  console.log(`${String(r.t).padStart(6)} ${(nm(r.p) + '/T' + g.teams[r.p]).padEnd(30)} ${String(r.pTerr).padStart(7)} ${String(r.pBal).padStart(10)} ${String(r.troops).padStart(8)}  (${r.x},${r.y})`.padEnd(88) + ` ${label[r.o].padEnd(8)} ${String(r.oTerr).padStart(6)} ${String(r.oBal).padStart(8)} ${(r.oBal / Math.max(1, r.oTerr)).toFixed(1).padStart(6)}  ${r.had ? '有' : '无'}`);
}
fs.writeFileSync(path.join(OUT, 'sea_landings.csv'), rows.join('\n') + '\n');
const first = out.filter((r) => !r.had);
console.log(`# 其中登陆前双方没有陆地接壤的 ${first.length} 条，船上兵合计 ${first.reduce((s, r) => s + r.troops, 0)}`);
