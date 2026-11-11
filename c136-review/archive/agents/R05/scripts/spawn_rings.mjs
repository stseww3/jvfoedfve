// spawn_rings.mjs — 把「真正执行的出生点」和各版本协调器源码里的环半径公式对一下（角落扇形阵，A 系 10 人编队）。
// 公式（三份 spawn-coordinator-c116*.mjs 的 837–838、1074–1077、1135–1137 行，只有系数不同）：
//   rCell = round(sqrt(max(10000, land) / (π × max(8, 已落点真人数))))            （这里用全场真人数 H 代入 → rCell 的下界）
//   minReqSep = clamp(round(0.95 rCell), 42, 68)；r0 = clamp(round(0.48 rCell), 28, 46)
//   Va: r1 = clamp(round(1.38 rCell), max(78, r0+minReqSep), 132)；r2 = clamp(round(2.35 rCell), max(142, r1+minReqSep), 225)；半角 π/3.2；内弧 min(3,max(2,floor((K−1)×0.34)))
//   Vb: r1 = clamp(round(1.12 rCell), max(66, r0+minReqSep), 108)；r2 = clamp(round(1.88 rCell), max(122, r1+minReqSep), 182)；半角 π/3.2；内弧同 Va
//   Vc: r1 = clamp(round(1.32 rCell), max(76, r0+minReqSep), 126)；r2 = clamp(round(2.28 rCell), max(145, r1+minReqSep), 220)；半角 π/2.55；内弧 min(2,max(1,floor((K−1)×0.22)))
// 几何：角尖号在中轴上距角锚点 r0；内弧号在 r1 弧上、偏离中轴 ≤0.82×半角；外墙号在 r2 弧上、偏离中轴 ≤半角。
//   所以「角尖号→内弧号」距离理论区间 [r1−r0, sqrt(r1²+r0²−2 r1 r0 cos(0.82×半角))]，「角尖号→外墙号」 [r2−r0, sqrt(r2²+r0²−2 r2 r0 cos(半角))]。
//   落点还要吸附到陆地（吸附半径 32/36/42 像素）并可能换用 0.52–1.24 倍半径，所以只做带 ±TOL 像素余量的区间检验。
// 输出：每局一行 + 末尾按版本汇总。用法：node spawn_rings.mjs [matchId ...]
import fs from 'node:fs';
import path from 'node:path';
import { spawnTruth } from './spawn_truth.mjs';

const DATA = process.env.C136_DATA || '/agent/repos/c136-data';
const idsArg = process.argv.slice(2);
const ids = idsArg.length ? idsArg : fs.readdirSync(path.join(DATA, 'bundles')).filter((x) => x.startsWith('A')).sort();
const clamp = (v, lo, hi) => (v < lo ? lo : v > hi ? hi : v); // 与协调器源码第 67 行同义（下界优先）
const med = (a) => { if (!a.length) return ''; const s = [...a].sort((x, y) => x - y); return Math.round(s[s.length >> 1]); };
const TOL = 12;
const VER = {
  Va: { m1: 1.38, lo1: 78, hi1: 132, m2: 2.35, lo2: 142, hi2: 225, fan: Math.PI / 3.2, inner: (K) => Math.min(3, Math.max(2, Math.floor((K - 1) * 0.34))) },
  Vb: { m1: 1.12, lo1: 66, hi1: 108, m2: 1.88, lo2: 122, hi2: 182, fan: Math.PI / 3.2, inner: (K) => Math.min(3, Math.max(2, Math.floor((K - 1) * 0.34))) },
  Vc: { m1: 1.32, lo1: 76, hi1: 126, m2: 2.28, lo2: 145, hi2: 220, fan: Math.PI / 2.55, inner: (K) => Math.min(2, Math.max(1, Math.floor((K - 1) * 0.22))) },
};
const verOf = (id) => { const n = +id.slice(1); return n <= 17 ? 'Va' : n <= 95 ? 'Vb' : 'Vc'; };
export function rings(ver, land, humans) {
  const v = VER[ver];
  const rCell = Math.round(Math.sqrt(Math.max(10000, land) / (Math.PI * Math.max(8, humans))));
  const minReqSep = clamp(Math.round(0.95 * rCell), 42, 68);
  const r0 = clamp(Math.round(0.48 * rCell), 28, 46);
  const r1 = clamp(Math.round(v.m1 * rCell), Math.max(v.lo1, r0 + minReqSep), v.hi1);
  const r2 = clamp(Math.round(v.m2 * rCell), Math.max(v.lo2, r1 + minReqSep), v.hi2);
  const far = (R, ang) => Math.sqrt(R * R + r0 * r0 - 2 * R * r0 * Math.cos(ang));
  return { rCell, minReqSep, r0, r1, r2, innerRange: [r1 - r0, Math.round(far(r1, 0.82 * v.fan))], outerRange: [r2 - r0, Math.round(far(r2, v.fan))], innerCount10: v.inner(10) };
}

if (import.meta.url === `file://${process.argv[1]}`) {
  console.log(['matchId', 'ver', 'land', 'humans', 'rCell', 'minReqSep', 'r0', 'r1', 'r2', 'nInner', 'nOuter', 'srcInner(K=10)', 'apexToInner_med', 'innerRange', 'innerInRange', 'apexToOuter_med', 'outerRange', 'outerInRange', 'nearestAlly_med', 'dupPairs', 'noSpawnCmd'].join('\t'));
  const agg = {};
  for (const id of ids) {
    let r; try { r = spawnTruth(id); } catch (e) { r = null; }
    if (!r || !r.W) continue;
    let land = 0;
    try { const rc = fs.readFileSync(path.join(DATA, 'bundles', id, 'results.csv'), 'utf8').split('\n'); const hd = rc[0].split(','); land = +rc[1].split(',')[hd.indexOf('land')]; } catch (e) { land = 0; }
    if (!land) continue;
    const ver = verOf(id), R = rings(ver, land, r.H);
    const fb = r.bots.filter((b) => b.final);
    const apex = fb.find((b) => b.roleExec === 'CORNER_APEX_BANK');
    const base = [id, ver, land, r.H, R.rCell, R.minReqSep, R.r0, R.r1, R.r2];
    if (!apex) { console.log([...base, '', '', R.innerCount10, '', R.innerRange.join('-'), '', '', R.outerRange.join('-'), '', r.medNearestAlly, r.dupPairs.length, r.nNoSpawnCmd].join('\t')); continue; }
    const d = (b) => Math.hypot(b.final.x - apex.final.x, b.final.y - apex.final.y);
    const inner = fb.filter((b) => b.roleExec === 'INNER_ARC_BANK').map(d), outer = fb.filter((b) => b.roleExec === 'OUTER_SHIELD_WALL').map(d);
    const inR = (arr, rg) => arr.filter((x) => x >= rg[0] - TOL && x <= rg[1] + TOL).length;
    const a = (agg[ver] ||= { n: 0, in: 0, inT: 0, out: 0, outT: 0, innerCounts: {}, ratioIn: [], ratioOut: [] });
    a.n++; a.in += inR(inner, R.innerRange); a.inT += inner.length; a.out += inR(outer, R.outerRange); a.outT += outer.length;
    a.innerCounts[inner.length] = (a.innerCounts[inner.length] || 0) + 1;
    if (inner.length) a.ratioIn.push(med(inner) / R.rCell); if (outer.length) a.ratioOut.push(med(outer) / R.rCell);
    console.log([...base, inner.length, outer.length, R.innerCount10, med(inner), R.innerRange.join('-'), `${inR(inner, R.innerRange)}/${inner.length}`, med(outer), R.outerRange.join('-'), `${inR(outer, R.outerRange)}/${outer.length}`, r.medNearestAlly, r.dupPairs.length, r.nNoSpawnCmd].join('\t'));
  }
  const m2 = (a) => { if (!a.length) return ''; const s = [...a].sort((x, y) => x - y); return s[s.length >> 1].toFixed(2); };
  for (const [ver, a] of Object.entries(agg)) {
    console.log(`# ${ver}: 有角尖号的局 ${a.n}；内弧号落在本版公式区间(±${TOL}px) ${a.in}/${a.inT}；外墙号 ${a.out}/${a.outT}；每局内弧号个数分布 ${JSON.stringify(a.innerCounts)}；角尖→内弧/rCell 中位 ${m2(a.ratioIn)}；角尖→外墙/rCell 中位 ${m2(a.ratioOut)}`);
  }
}
