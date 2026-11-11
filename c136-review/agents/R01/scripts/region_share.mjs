// region_share.mjs — “家门口的地最后归了谁”：以本队各号实际出生点为圆心、半径 R 像素以内的全部陆地格，
// 在指定拍按归属分类计数：本队号 / 同队其他人类号 / 敌队人类号 / 内置 AI / 无主地。
// 用法：node region_share.mjs <matchId> [--replay id] [--log id1,id2] [--bots a,b] [--radius 100,150,200] [--ticks 180,630,...] [--per-bot]
//   --per-bot：再按“离哪个号的出生点最近”把圈内的地分给各号（泰森多边形），逐号给出同样的分类（只用第一个半径）。
// 输出：标准输出一张表 + out/<matchId>/region_share.csv（t,radius,scope,land,squad,mates,enemy,ai,neutral）。
// 说明：分母是圈内的全部陆地格（含山以外的可占陆地；水和山不算）。出生阶段结束之前（t=0）圈内几乎全是无主地。
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { openMatch, readLogSnaps, T_LAND, P_INNER } from './resim_lib.mjs';

const args = process.argv.slice(2);
const mid = args[0];
const opt = (k, d) => (args.includes(`--${k}`) ? args[args.indexOf(`--${k}`) + 1] : d);
const rmid = opt('replay', mid);
const radii = opt('radius', '100,150,200').split(',').map(Number);
const ticks = opt('ticks', '180,450,630,900,1170,1530,2070,2970').split(',').map(Number).sort((a, b) => a - b);
const perBot = args.includes('--per-bot');
const HERE = path.dirname(fileURLToPath(import.meta.url));
const OUT = path.resolve(HERE, '..', 'out', mid);
fs.mkdirSync(OUT, { recursive: true });

const m = openMatch(mid, { replay: rmid });
const { g, H } = m;
const onlyBots = opt('bots', '') ? new Set(opt('bots', '').split(',')) : null;
const squad = {};
for (const lb of opt('log', mid).split(',')) {
  const { me } = readLogSnaps(lb, lb === mid ? '' : lb + ':', onlyBots);
  for (const [b, p] of Object.entries(me)) squad[(lb === mid ? '' : lb + ':') + b] = p;
}
const sqIds = new Set(Object.values(squad));
const label = Object.fromEntries(Object.entries(squad).map(([b, p]) => [p, b]));

// openMatch 已经把出生阶段放完，m.spawn 里是每个号最后一条出生指令的坐标
const sp = [];
for (const p of sqIds) if (m.spawn[p]) sp.push([p, m.spawn[p][0], m.spawn[p][1]]);
if (!sp.length) { console.error('没有出生点'); process.exit(1); }

// 每个陆地格：到最近出生点的距离、最近的是哪个号
const W = g.W, Hh = g.H, N = g.N;
const Rmax = Math.max(...radii);
const cells = []; // [c, dist, nearestP]
const isLandCell = (c) => { const v = g.px[c]; return v === T_LAND || v >= P_INNER; };
for (let y = 0; y < Hh; y++) for (let x = 0; x < W; x++) {
  let best = 1e18, bp = -1;
  for (const [p, sx, sy] of sp) { const d = (x - sx) * (x - sx) + (y - sy) * (y - sy); if (d < best) { best = d; bp = p; } }
  if (best > Rmax * Rmax) continue;
  const c = y * W + x;
  if (!isLandCell(c)) continue;
  cells.push([c, Math.sqrt(best), bp]);
}
const myTeam = g.teams[sp[0][0]];
const cls = (c) => {
  if (g.px[c] < P_INNER) return 4; // 无主
  const o = g.own[c];
  if (sqIds.has(o)) return 0;
  if (o >= H) return 3;
  return g.teams[o] === myTeam ? 1 : 2;
};
const rows = ['t,radius,scope,land,squad,mates,enemy,ai,neutral'];
const pct = (a, b) => (b ? (100 * a / b).toFixed(1) : '-');
console.log(`# ${mid} 出生点 ${sp.length} 个，我方队伍 ${myTeam}；圈内陆地格：` + radii.map((r) => `R=${r}: ${cells.filter((x) => x[1] <= r).length}`).join('，') + `；全图陆地 ${g.land}`);
console.log('    拍  半径   圈内陆地 | 本队号%  同队他人%  敌队%  内置AI%  无主%');
const snap = () => {
  for (const r of radii) {
    const k = [0, 0, 0, 0, 0]; let n = 0;
    for (const [c, d] of cells) if (d <= r) { k[cls(c)]++; n++; }
    rows.push([g.t, r, 'all', n, ...k].join(','));
    console.log(`${String(g.t).padStart(6)} ${String(r).padStart(5)} ${String(n).padStart(10)} | ${pct(k[0], n).padStart(6)} ${pct(k[1], n).padStart(9)} ${pct(k[2], n).padStart(7)} ${pct(k[3], n).padStart(7)} ${pct(k[4], n).padStart(6)}`);
  }
  if (perBot) {
    const r = radii[0];
    const by = new Map();
    for (const [c, d, bp] of cells) if (d <= r) {
      if (!by.has(bp)) by.set(bp, [0, 0, 0, 0, 0, 0, 0]);
      const a = by.get(bp); a[cls(c)]++; a[5]++;
      if (g.px[c] >= P_INNER && g.own[c] === bp) a[6]++;
    }
    for (const [bp, a] of by) {
      rows.push([g.t, r, label[bp], a[5], a[0], a[1], a[2], a[3], a[4]].join(','));
      console.log(`${String(g.t).padStart(6)} ${String(r).padStart(5)} ${String(a[5]).padStart(10)} | ${pct(a[0], a[5]).padStart(6)} ${pct(a[1], a[5]).padStart(9)} ${pct(a[2], a[5]).padStart(7)} ${pct(a[3], a[5]).padStart(7)} ${pct(a[4], a[5]).padStart(6)}  ${label[bp]}（自己占 ${pct(a[6], a[5])}%）`);
    }
  }
};
let ti = 0;
while (ti < ticks.length) {
  if (g.t >= ticks[ti]) { snap(); ti++; continue; }
  if (!m.tick()) break;
}
fs.writeFileSync(path.join(OUT, 'region_share.csv'), rows.join('\n') + '\n');
