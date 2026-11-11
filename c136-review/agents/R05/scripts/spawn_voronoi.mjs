// spawn_voronoi.mjs — 出生时「名下的陆地」：把全图每一格陆地分给直线距离最近的那个真人出生点（Voronoi 份额，不看地形阻隔），
//   比较我方号与其他真人各自分到多少格。用来量「出生点排得多挤」：份额小 = 四周的地先天就少。
//   另外给出：把我方号看成一个整体时名下的陆地合计、占全图陆地的比例、与「人数占比」的比值。
//   真人出生点取录像重放 t=1 时各真人的地块质心（与 match_truth.mjs 的 players[].spawn 同一口径：读 truth JSON）。
// 用法：node spawn_voronoi.mjs <matchId> [--list] [--vs 900,1500,…]（--vs：HS 采样拍的实际地 ÷ 出生份额）
import fs from 'node:fs';
import { simulate, P_INNER } from './sim_replay.mjs';
const { T_LAND } = await import('file:///agent/repos/c136-data/src/sim/sim/map.js');

const a = process.argv.slice(2);
const mid = a[0];
const J = JSON.parse(fs.readFileSync(`/tmp/c136-r05/truth/${mid}.json`, 'utf8'));
const H = J.humans;
const sq = new Map(J.squad.map((s) => [s.p, s.bot]));
const pts = J.players.filter((p) => p.id < H && p.spawn && p.spawn[0] >= 0).map((p) => ({ id: p.id, x: p.spawn[0], y: p.spawn[1], name: p.name, team: p.team }));
let W = 0, Hh = 0, land = null;
await simulate(mid, {
  maxTick: 1,
  onStart(g) {
    W = g.W; Hh = g.H; land = new Uint8Array(g.N);
    for (let c = 0; c < g.N; c++) land[c] = g.px[c] === T_LAND || g.px[c] >= P_INNER ? 1 : 0;
  },
});
const cnt = new Map(pts.map((p) => [p.id, 0]));
let total = 0;
for (let y = 0; y < Hh; y++) {
  for (let x = 0; x < W; x++) {
    if (!land[y * W + x]) continue;
    total++;
    let best = -1, bd = Infinity;
    for (const p of pts) {
      const d = (p.x - x) * (p.x - x) + (p.y - y) * (p.y - y);
      if (d < bd) { bd = d; best = p.id; }
    }
    cnt.set(best, cnt.get(best) + 1);
  }
}
const med = (v) => { const s = [...v].sort((x, y) => x - y); return s.length ? (s.length % 2 ? s[(s.length - 1) / 2] : (s[s.length / 2 - 1] + s[s.length / 2]) / 2) : 0; }; // 偶数个取中间两个的平均（早先版本取的是靠上的那个）
const ours = pts.filter((p) => sq.has(p.id)), others = pts.filter((p) => !sq.has(p.id));
const sumO = ours.reduce((s, p) => s + cnt.get(p.id), 0);
const nn = (p, set) => Math.round(Math.min(...set.filter((o) => o.id !== p.id).map((o) => Math.hypot(o.x - p.x, o.y - p.y))));
console.log(`[出生份额] ${mid} 图 ${W}×${Hh} 陆地 ${total} 格｜真人出生点 ${pts.length} 个（人均 ${Math.round(total / pts.length)} 格）｜我方号 ${ours.length} 个`);
console.log(`   我方号名下陆地 合计 ${sumO} 格（全图 ${(100 * sumO / total).toFixed(1)}%，人数占 ${(100 * ours.length / pts.length).toFixed(1)}% → 份额÷人数 ${(sumO / total / (ours.length / pts.length)).toFixed(2)}）`
  + `｜每号 中位 ${med(ours.map((p) => cnt.get(p.id)))}、最小 ${Math.min(...ours.map((p) => cnt.get(p.id)))}、最大 ${Math.max(...ours.map((p) => cnt.get(p.id)))}`);
console.log(`   其他真人 每人 中位 ${med(others.map((p) => cnt.get(p.id)))}、下四分位 ${[...others.map((p) => cnt.get(p.id))].sort((x, y) => x - y)[Math.floor(others.length / 4)]}、最小 ${Math.min(...others.map((p) => cnt.get(p.id)))}`
  + `｜份额比我方号中位还小的其他真人 ${others.filter((p) => cnt.get(p.id) < med(ours.map((q) => cnt.get(q.id)))).length} 个`);
console.log('   我方号逐个：' + ours.map((p) => `${sq.get(p.id)}(${p.x},${p.y}) ${cnt.get(p.id)} 格、最近真人 ${nn(p, pts)}、最近非我方真人 ${nn(p, others.concat([p]))}`).join('；'));
{
  // 各队（我方号单列）名下陆地合计与人数
  const grp = new Map();
  for (const p of pts) {
    const key = sq.has(p.id) ? '我方号' : `T${p.team}${ours.some((o) => o.team === p.team) ? ' 路人' : ''}`;
    const g = grp.get(key) ?? { n: 0, s: 0 };
    g.n++; g.s += cnt.get(p.id); grp.set(key, g);
  }
  console.log('   各队名下陆地：' + [...grp.entries()].map(([key, g]) => `${key} ${g.n} 人 ${g.s} 格（${(100 * g.s / total).toFixed(1)}%，人均 ${Math.round(g.s / g.n)}）`).join('；'));
}
// --vs T[,T…]：把 truth JSON 里 HS 采样拍的实际地与出生份额对比（地÷份额），看「到那一拍为止各人是否大致拿满了自己名下的地」
if (a.includes('--vs')) {
  const HS = J.HS;
  for (const T of a[a.indexOf('--vs') + 1].split(',').map(Number)) {
    const i = HS.t.indexOf(T);
    if (i < 0) { console.log(`   --vs ${T}: HS 没有这个采样拍`); continue; }
    const terr = (p) => HS.terr[i][p.id];
    const live = (set) => set.filter((p) => terr(p) > 0);
    const ratio = (set) => live(set).map((p) => terr(p) / Math.max(1, cnt.get(p.id)));
    const q = (v, f) => { if (f === 0.5) return med(v); const s = [...v].sort((x, y) => x - y); return s.length ? s[Math.min(s.length - 1, Math.floor(s.length * f))] : 0; };
    const ro = ratio(others), rs = ratio(ours);
    const sumT = (set) => live(set).reduce((s, p) => s + terr(p), 0), sumC = (set) => live(set).reduce((s, p) => s + cnt.get(p.id), 0);
    // 秩相关（Spearman）：出生份额的名次 对 该拍实际地的名次，在场真人全体
    const all = live(pts);
    const rank = (f) => { const s = [...all].sort((x, y) => f(x) - f(y)); return new Map(s.map((p, k) => [p.id, k])); };
    const ra = rank((p) => cnt.get(p.id)), rb = rank(terr);
    const n = all.length, d2 = all.reduce((s, p) => s + (ra.get(p.id) - rb.get(p.id)) ** 2, 0);
    const rho = n > 2 ? 1 - (6 * d2) / (n * (n * n - 1)) : 0;
    console.log(`   t=${T} 地÷出生份额：其他真人（在场 ${ro.length}）中位 ${q(ro, 0.5).toFixed(2)}、下四分位 ${q(ro, 0.25).toFixed(2)}、上四分位 ${q(ro, 0.75).toFixed(2)}，合计 ${sumT(others)}÷${sumC(others)} = ${(sumT(others) / Math.max(1, sumC(others))).toFixed(2)}`
      + `｜我方号（在场 ${rs.length}）中位 ${q(rs, 0.5).toFixed(2)}、最小 ${Math.min(...rs).toFixed(2)}、最大 ${Math.max(...rs).toFixed(2)}，合计 ${sumT(ours)}÷${sumC(ours)} = ${(sumT(ours) / Math.max(1, sumC(ours))).toFixed(2)}｜份额名次与地名次的秩相关 ρ=${rho.toFixed(2)}（n=${n}）`);
    console.log('      我方号逐个 地/份额：' + ours.map((p) => `${sq.get(p.id)} ${terr(p)}/${cnt.get(p.id)}`).join('；'));
  }
}
if (a.includes('--list')) {
  for (const p of [...pts].sort((x, y) => cnt.get(x.id) - cnt.get(y.id))) console.log(`   ${sq.has(p.id) ? '*' : ' '} #${p.id} T${p.team} ${String(p.name).slice(0, 16)} (${p.x},${p.y}) ${cnt.get(p.id)} 格`);
}
