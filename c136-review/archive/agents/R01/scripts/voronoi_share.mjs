#!/usr/bin/env node
// voronoi_share.mjs — “好地实际抢到多少”的硬账（总部 0007 第 3 条）。一局只重演一遍，出四张表：
//   1) 天然份额：开局第 1 拍每个真人席位的领土包围盒中心当出生点，全图陆地格按“离哪个真人的出生点最近”分掉（泰森多边形，欧氏距离）。
//      本队名下的天然陆地占全图几成、对人头占比；单号天然格数的中位数对其他真人。
//   2) 拿到率：指定拍（默认 630、1500）每个真人的 领土 ÷ 天然份额；本队中位对各队其他真人中位。
//   3) 自家圈里的地归了谁：本队各号天然多边形里的陆地格，在指定拍归 自己 / 本队别的号(同队) / 本队别的号(别队) / 同队路人 / 敌队真人 / 内置 AI / 无主。
//   4) 身边的 AI 地去向：--ai-from 拍（默认 600）时归内置 AI 的陆地格，到 --ai-to 拍（默认 1800）归了谁；分“落在本队天然多边形里的”和“全图”。
// 用法（套 run-heavy.sh）：node scripts/voronoi_share.mjs <局号> [--replay 同局另一个包] [--log id1,id2] [--ticks 630,1500] [--ai-from 600] [--ai-to 1800]
// 输出：标准输出 + out/<局号>/voronoi_seats.csv（每个真人一行）、voronoi_region.csv、voronoi_ai.csv、voronoi_summary.json（给 M6 汇总用）
// 说明：分类里的“同队/敌队”都相对于那块多边形的天然主人（B 组一个编队分在几个队里，不能用一个 myTeam）。
//       离场壳（state=2）单列：壳名下的地算“壳”。出生点没有落地指令的号由引擎随机安放，同样取第 1 拍的包围盒中心。
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { openMatch, readLogSnaps, T_LAND, P_INNER } from './resim_lib.mjs';

const args = process.argv.slice(2);
const mid = args[0];
const opt = (k, d) => (args.includes(`--${k}`) ? args[args.indexOf(`--${k}`) + 1] : d);
const rmid = opt('replay', mid);
const ticks = opt('ticks', '630,1500').split(',').map(Number).sort((a, b) => a - b);
const aiFrom = +opt('ai-from', 600), aiTo = +opt('ai-to', 1800);
const HERE = path.dirname(fileURLToPath(import.meta.url));
const OUT = path.resolve(HERE, '..', 'out', mid);
fs.mkdirSync(OUT, { recursive: true });

const m = openMatch(mid, { replay: rmid });
const { g, H } = m;
const squad = {};
for (const lb of opt('log', mid).split(',')) {
  const { me } = readLogSnaps(lb);
  for (const [b, p] of Object.entries(me)) if (squad[b] === undefined) squad[b] = p;
}
const sqIds = new Set(Object.values(squad));
const label = Object.fromEntries(Object.entries(squad).map(([b, p]) => [p, b]));
const nm = (p) => label[p] ?? m.label(p);

// 第 1 拍：出生点
while (g.t < 1) if (!m.tick()) break;
const W = g.W, Hh = g.H, N = g.N;
const sp = []; // [p, x, y]
for (let p = 0; p < H; p++) if (g.alive[p] && g.terr[p] > 0) sp.push([p, (g.x0[p] + g.x1[p]) >> 1, (g.y0[p] + g.y1[p]) >> 1]);
const isLandCell = (c) => { const v = g.px[c]; return v === T_LAND || v >= P_INNER; };
const natOwner = new Int16Array(N).fill(-1);
const nat = new Int32Array(H);
let landN = 0;
{
  const n = sp.length;
  const sx = new Float64Array(n), sy = new Float64Array(n);
  sp.forEach((s, i) => { sx[i] = s[1]; sy[i] = s[2]; });
  for (let y = 0; y < Hh; y++) for (let x = 0; x < W; x++) {
    const c = y * W + x;
    if (!isLandCell(c)) continue;
    let best = Infinity, bi = -1;
    for (let i = 0; i < n; i++) { const dx = x - sx[i], dy = y - sy[i]; const d = dx * dx + dy * dy; if (d < best) { best = d; bi = i; } }
    natOwner[c] = sp[bi][0];
    nat[sp[bi][0]]++;
    landN++;
  }
}
const median = (a) => { if (!a.length) return 0; const s = [...a].sort((x, y) => x - y); const k = s.length >> 1; return s.length % 2 ? s[k] : (s[k - 1] + s[k]) / 2; };
const humansAtStart = sp.map((s) => s[0]);
const sqStart = humansAtStart.filter((p) => sqIds.has(p));
const othStart = humansAtStart.filter((p) => !sqIds.has(p));
const sqNat = sqStart.reduce((a, p) => a + nat[p], 0);
console.log(`# ${mid}（录像 ${rmid}）地图 ${W}x${Hh}，陆地 ${landN} 格；第 1 拍在场真人 ${humansAtStart.length} 个，其中本队 ${sqStart.length} 个`);
console.log(`== 1) 天然份额（离谁的出生点最近）：本队合计 ${sqNat} 格 = 全图陆地的 ${(100 * sqNat / landN).toFixed(2)}%；本队人头占 ${(100 * sqStart.length / humansAtStart.length).toFixed(2)}%`);
console.log(`   单号天然格数 中位/最小/最大：本队 ${median(sqStart.map((p) => nat[p]))}/${Math.min(...sqStart.map((p) => nat[p]))}/${Math.max(...sqStart.map((p) => nat[p]))}；其他真人 ${median(othStart.map((p) => nat[p]))}/${Math.min(...othStart.map((p) => nat[p]))}/${Math.max(...othStart.map((p) => nat[p]))}`);
{
  const byTeam = {};
  for (const p of humansAtStart) { const k = (sqIds.has(p) ? 'squad' : 'other') + '/T' + g.teams[p]; (byTeam[k] ??= []).push(nat[p]); }
  console.log('   按队：' + Object.entries(byTeam).sort().map(([k, v]) => `${k} n=${v.length} 中位 ${median(v)} 合计 ${v.reduce((a, b) => a + b, 0)}`).join('；'));
}

// 分类：相对于多边形的天然主人 s
// 0 自己 1 本队别的号(同队) 2 本队别的号(别队) 3 同队路人 4 敌队真人 5 内置AI 6 无主 7 离场壳(任何真人席位 state=2)
const CLS = ['self', 'squadSameTeam', 'squadOtherTeam', 'mates', 'enemy', 'ai', 'neutral', 'husk'];
const cls = (c, s) => {
  if (g.px[c] < P_INNER) return 6;
  const o = g.own[c];
  if (o >= H) return 5;
  if (g.state[o] === 2) return 7;
  if (o === s) return 0;
  const same = g.teams[o] === g.teams[s];
  if (sqIds.has(o)) return same ? 1 : 2;
  return same ? 3 : 4;
};

const seatRows = {}; for (const p of humansAtStart) seatRows[p] = { p, name: nm(p), team: g.teams[p], squad: sqIds.has(p) ? 1 : 0, x: 0, y: 0, nat: nat[p] };
for (const [p, x, y] of sp) { seatRows[p].x = x; seatRows[p].y = y; }
const regionRows = ['t,scope,cells,self,squadSameTeam,squadOtherTeam,mates,enemy,ai,neutral,husk'];
const aiRows = ['scope,cellsAtFrom,self,squadSameTeam,squadOtherTeam,mates,enemy,ai,neutral,husk'];
const summary = { mid, replay: rmid, land: landN, humans: humansAtStart.length, squadN: sqStart.length, squadNat: sqNat, squadNatPct: 100 * sqNat / landN, headPct: 100 * sqStart.length / humansAtStart.length,
  natMedSquad: median(sqStart.map((p) => nat[p])), natMedOther: median(othStart.map((p) => nat[p])), ticks: {}, ai: {} };
const pct = (a, b) => (b ? (100 * a / b).toFixed(1) : '-');

let aiCells = null; // Int32Array of cells that are AI-owned at aiFrom
const events = [...new Set([...ticks, aiFrom, aiTo])].sort((a, b) => a - b);
const doTick = (t) => {
  if (ticks.includes(t)) {
    // 2) 拿到率
    const ratio = (p) => (nat[p] ? g.terr[p] / nat[p] : 0);
    for (const p of humansAtStart) { seatRows[p]['terr' + t] = g.alive[p] ? g.terr[p] : 0; seatRows[p]['state' + t] = g.alive[p] ? g.state[p] : -1; }
    const liveSq = sqStart.filter((p) => g.alive[p] && g.state[p] !== 2);
    const rs = sqStart.map(ratio), ro = othStart.map(ratio);
    const byTeam = {};
    for (const p of othStart) (byTeam['T' + g.teams[p]] ??= []).push(ratio(p));
    const sumT = (L) => L.reduce((a, p) => a + (g.alive[p] ? g.terr[p] : 0), 0), sumN = (L) => L.reduce((a, p) => a + nat[p], 0);
    console.log(`== 2) t=${t} 拿到率（领土 ÷ 天然份额）：本队 ${sqStart.length} 个号 中位 ${median(rs).toFixed(2)}（合计 ${sumT(sqStart)}/${sumN(sqStart)} = ${(sumT(sqStart) / sumN(sqStart)).toFixed(2)}；其中还在场的 ${liveSq.length} 个号 中位 ${median(liveSq.map(ratio)).toFixed(2)}）；其他真人 ${othStart.length} 个 中位 ${median(ro).toFixed(2)}（合计 ${(sumT(othStart) / sumN(othStart)).toFixed(2)}）`);
    console.log('      其他真人按队：' + Object.entries(byTeam).sort().map(([k, v]) => `${k} n=${v.length} 中位 ${median(v).toFixed(2)}`).join('；'));
    // 3) 自家圈里的地归了谁
    const k = new Int32Array(8); let n = 0;
    const per = {};
    for (let c = 0; c < N; c++) {
      const s = natOwner[c];
      if (s < 0 || !sqIds.has(s)) continue;
      const q = cls(c, s);
      k[q]++; n++;
      (per[s] ??= new Int32Array(9))[q]++; per[s][8]++;
    }
    regionRows.push([t, 'squad', n, ...k].join(','));
    for (const [s, a] of Object.entries(per)) regionRows.push([t, JSON.stringify(nm(+s)), a[8], ...Array.from(a.subarray(0, 8))].join(','));
    console.log(`== 3) t=${t} 本队天然多边形里的 ${n} 格陆地归了谁：自己 ${pct(k[0], n)}%  本队别的号(同队) ${pct(k[1], n)}%  本队别的号(别队) ${pct(k[2], n)}%  同队路人 ${pct(k[3], n)}%  敌队真人 ${pct(k[4], n)}%  内置AI ${pct(k[5], n)}%  无主 ${pct(k[6], n)}%  离场壳 ${pct(k[7], n)}%`);
    summary.ticks[t] = { ratioMedSquad: median(rs), ratioMedSquadLive: median(liveSq.map(ratio)), liveSquad: liveSq.length, ratioSumSquad: sumT(sqStart) / sumN(sqStart), ratioMedOther: median(ro), ratioSumOther: sumT(othStart) / sumN(othStart),
      region: Object.fromEntries(CLS.map((c, i) => [c, k[i]])), regionCells: n };
  }
  if (t === aiFrom) {
    const L = [];
    for (let c = 0; c < N; c++) if (g.px[c] >= P_INNER && g.own[c] >= H) L.push(c);
    aiCells = Int32Array.from(L);
  }
  if (t === aiTo && aiCells) {
    const kIn = new Int32Array(8), kAll = new Int32Array(8); let nIn = 0;
    const teamAll = {};
    for (const c of aiCells) {
      const s = natOwner[c];
      // 全图口径：按现在的归属粗分（真人按队）
      let key;
      if (g.px[c] < P_INNER) key = 'neutral'; else { const o = g.own[c]; key = o >= H ? 'ai' : (sqIds.has(o) ? 'squad' : 'other') + (g.state[o] === 2 ? '壳' : '') + '/T' + g.teams[o]; }
      teamAll[key] = (teamAll[key] || 0) + 1;
      if (s >= 0 && sqIds.has(s)) { kIn[cls(c, s)]++; nIn++; }
    }
    aiRows.push(['inSquadRegion', nIn, ...kIn].join(','));
    console.log(`== 4) t=${aiFrom} 时归内置 AI 的陆地 ${aiCells.length} 格（其中落在本队天然多边形里 ${nIn} 格），到 t=${aiTo}：`);
    console.log(`      本队多边形里的 ${nIn} 格：多边形主人自己 ${pct(kIn[0], nIn)}%  本队别的号(同队) ${pct(kIn[1], nIn)}%  本队别的号(别队) ${pct(kIn[2], nIn)}%  同队路人 ${pct(kIn[3], nIn)}%  敌队真人 ${pct(kIn[4], nIn)}%  仍是AI ${pct(kIn[5], nIn)}%  无主 ${pct(kIn[6], nIn)}%  离场壳 ${pct(kIn[7], nIn)}%`);
    console.log('      全图：' + Object.entries(teamAll).sort((a, b) => b[1] - a[1]).map(([k2, v]) => `${k2} ${v}(${pct(v, aiCells.length)}%)`).join('  '));
    summary.ai = { from: aiFrom, to: aiTo, cellsAll: aiCells.length, cellsIn: nIn, inRegion: Object.fromEntries(CLS.map((c, i) => [c, kIn[i]])), all: teamAll };
  }
};
let ei = 0;
while (ei < events.length) {
  if (g.t >= events[ei]) { doTick(events[ei]); ei++; continue; }
  if (!m.tick()) break;
}
const cols = ['p', 'name', 'team', 'squad', 'x', 'y', 'nat', ...ticks.flatMap((t) => ['terr' + t, 'state' + t])];
fs.writeFileSync(path.join(OUT, 'voronoi_seats.csv'), cols.join(',') + '\n' + Object.values(seatRows).map((r) => cols.map((c) => (c === 'name' ? JSON.stringify(r[c]) : r[c] ?? '')).join(',')).join('\n') + '\n');
fs.writeFileSync(path.join(OUT, 'voronoi_region.csv'), regionRows.join('\n') + '\n');
fs.writeFileSync(path.join(OUT, 'voronoi_ai.csv'), aiRows.join('\n') + '\n');
fs.writeFileSync(path.join(OUT, 'voronoi_summary.json'), JSON.stringify(summary));
console.log(`# 已写 out/${mid}/voronoi_seats.csv、voronoi_region.csv、voronoi_ai.csv、voronoi_summary.json`);
