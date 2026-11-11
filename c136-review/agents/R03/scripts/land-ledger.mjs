#!/usr/bin/env node
// land-ledger.mjs — 「好地实际抢到多少」的硬账（广播 0007 第 3 节），全部由逐拍重放的地图归属机械算出，不含判断。
//
//   bash c136-review/tools/run-heavy.sh node scripts/land-ledger.mjs <mid> [--until 1800] [--at 630,900,1200,1500,1530,1800] [--freeze 600] [--quiet]
//   写 out/dossier/<mid>-land.txt 和 out/dossier/<mid>-land-facts.json
//
// 口径（与 R05 的 spawn_voronoi.mjs 对齐）：
//   [G1] 出生份额：选点期结束那一拍，每个真人的出生点 = 它那块地的质心；把全图每一格陆地（T_LAND 或已被占的格）
//        分给直线距离最近的真人出生点（Voronoi，不看地形阻隔、不看内置 AI）。份额小 = 四周的地先天就少。
//        「份额÷人头」= (编队名下格数/全图陆地) ÷ (编队号数/开局有地的真人数)。
//   [G2] 实际拿到÷出生份额：各采样拍 每人实际领土 ÷ 名下格数（编队合计、每号中位；其他真人合计、中位、四分位；各队合计）。
//   [G3] 我方名下范围里的地，各采样拍实际归谁（编队 / 同队路人 / 敌方真人 / 内置 AI / 无主）；编队的地有多少在名下范围之外。
//   [G4] 身边内置 AI 的地去向：把 --freeze 拍（默认 600）的归属定格，取三组格子——
//        (A) 当时落在我方名下范围内、属于内置 AI 的格；(B) 当时与编队任何一个号接壤的内置 AI 的全部格；
//        (C) 出生点落在我方名下范围内的内置 AI 当时的全部格——之后各采样拍看这些格子在谁手里。
//        另列：到末拍为止，从 (B) 组里拿得最多的几个玩家。
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { resim } from './resim.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const OUT = path.join(HERE, '..', 'out', 'dossier');
const NEUTRAL = 512, P_INNER = 16, T_LAND = 1;

const args = process.argv.slice(2);
const mid = args[0];
if (!mid) { console.error('用法：node land-ledger.mjs <mid> [--until 1800] [--at …] [--freeze 600] [--quiet]'); process.exit(2); }
const opt = (k, d) => (args.includes(`--${k}`) ? args[args.indexOf(`--${k}`) + 1] : d);
const AT = String(opt('at', '630,900,1200,1500,1530,1800')).split(',').map(Number).sort((a, b) => a - b);
const FREEZE = +opt('freeze', 600);
const UNTIL = Math.max(+opt('until', 1800), AT[AT.length - 1], FREEZE);
const quiet = args.includes('--quiet');

const lines = [];
const w = (s = '') => lines.push(s);
const pc = (a, b) => (b > 0 ? (100 * a / b).toFixed(1) + '%' : '—');
const med = (v) => { const s = [...v].sort((x, y) => x - y); return s.length ? (s.length % 2 ? s[(s.length - 1) / 2] : (s[s.length / 2 - 1] + s[s.length / 2]) / 2) : 0; };
const qt = (v, f) => { const s = [...v].sort((x, y) => x - y); return s.length ? s[Math.min(s.length - 1, Math.floor(s.length * f))] : 0; };

let H = 0, W = 0, N = 0, names = null, squad = null, sqIds = null, sqSet = null, teamGame = false, myTeam = 0;
let land = null, vor = null, vcnt = null, pts = null, total = 0;
let own0 = null;            // 定格拍的归属：-2 非陆地，-1 无主，否则玩家号
let setA = null, setB = null, setC = null, adjAI = null, bornAI = null;
let frozen = false;
const facts = { matchId: mid, freezeTick: FREEZE, at: AT };
const rowsG2 = [], rowsG3 = [], rowsG4 = { A: [], B: [], C: [] };
let takersB = null;
const botNameOf = new Map();

const ownerAt = (g, c) => (g.px[c] >= P_INNER ? g.own[c] : (g.px[c] === T_LAND ? -1 : -2));
const clsOf = (g, o) => {
  if (o === -1) return 'neutral';
  if (o >= H) return 'ai';
  if (sqSet.has(o)) return 'squad';
  if (teamGame && g.teams[o] === myTeam) return 'mate';
  return 'enemy';
};
const nm = (p) => (p >= H ? `AI${p}` : `${Array.from(String(names[p] || '').replace('[APEX] ', '')).slice(0, 14).join('')}#${p}`);

function init(g, ctx) {
  H = ctx.H; W = g.W; N = g.px.length; names = ctx.names; squad = ctx.squad; teamGame = ctx.teamGame;
  sqIds = Object.values(squad).map((s) => s.id).filter((x) => x >= 0);
  sqSet = new Set(sqIds);
  myTeam = teamGame && sqIds.length ? g.teams[sqIds[0]] : 0;
  land = new Uint8Array(N);
  const sx = new Float64Array(512), sy = new Float64Array(512), sn = new Int32Array(512);
  for (let c = 0; c < N; c++) {
    const v = g.px[c];
    if (v === T_LAND || v >= P_INNER) { land[c] = 1; total++; }
    if (v >= P_INNER) { const o = g.own[c]; sx[o] += c % W; sy[o] += Math.floor(c / W); sn[o]++; }
  }
  pts = [];
  for (let p = 0; p < H; p++) if (sn[p] > 0) pts.push({ id: p, x: sx[p] / sn[p], y: sy[p] / sn[p], team: teamGame ? g.teams[p] : 0 });
  vor = new Int16Array(N).fill(-1);
  vcnt = new Int32Array(512);
  for (let c = 0; c < N; c++) {
    if (!land[c]) continue;
    const x = c % W, y = Math.floor(c / W);
    let best = -1, bd = Infinity;
    for (const p of pts) {
      const d = (p.x - x) * (p.x - x) + (p.y - y) * (p.y - y);
      if (d < bd) { bd = d; best = p.id; }
    }
    vor[c] = best; vcnt[best]++;
  }
  // 出生在我方名下范围内的内置 AI
  bornAI = new Set();
  for (let p = H; p < 512; p++) {
    if (sn[p] <= 0) continue;
    const cx = Math.round(sx[p] / sn[p]), cy = Math.round(sy[p] / sn[p]);
    const c = cy * W + cx;
    let o = vor[c];
    if (o < 0) {
      // 质心落在水上：取最近的真人出生点
      let bd = Infinity;
      for (const q of pts) { const d = (q.x - cx) ** 2 + (q.y - cy) ** 2; if (d < bd) { bd = d; o = q.id; } }
    }
    if (sqSet.has(o)) bornAI.add(p);
  }
  const ours = pts.filter((p) => sqSet.has(p.id)), others = pts.filter((p) => !sqSet.has(p.id));
  const sumO = ours.reduce((s, p) => s + vcnt[p.id], 0);
  const nn = (p, set) => { const v = set.filter((o) => o.id !== p.id).map((o) => Math.hypot(o.x - p.x, o.y - p.y)); return v.length ? Math.round(Math.min(...v)) : -1; };
  const ratio = sumO / total / (ours.length / pts.length);
  w(`[G1] 出生份额（Voronoi：每格陆地归直线最近的真人出生点；不看地形、不看内置 AI）`);
  w(`  图 ${W}×${Math.round(N / W)}，陆地 ${total} 格；开局有地的真人 ${pts.length} 个（人均 ${Math.round(total / pts.length)} 格）；编队 ${ours.length} 个号`);
  w(`  编队名下合计 ${sumO} 格 = 全图 ${pc(sumO, total)}，人头占 ${pc(ours.length, pts.length)} → 份额÷人头 ${ratio.toFixed(2)}`);
  const ov = ours.map((p) => vcnt[p.id]), tv = others.map((p) => vcnt[p.id]);
  w(`  每号名下：中位 ${med(ov)}、最小 ${Math.min(...ov)}、最大 ${Math.max(...ov)}；其他真人每人：中位 ${med(tv)}、下四分位 ${qt(tv, 0.25)}、最小 ${tv.length ? Math.min(...tv) : 0}；名下比编队中位还小的其他真人 ${others.filter((p) => vcnt[p.id] < med(ov)).length}/${others.length} 个`);
  for (const [b, s] of Object.entries(squad)) if (s.id >= 0) botNameOf.set(s.id, b);
  const botName = botNameOf;
  w('  逐号：' + ours.map((p) => `${botName.get(p.id)}(${Math.round(p.x)},${Math.round(p.y)}) ${vcnt[p.id]} 格、最近真人 ${nn(p, pts)}、最近非编队真人 ${nn(p, others.concat([p]))}`).join('；'));
  const grp = new Map();
  for (const p of pts) {
    const key = sqSet.has(p.id) ? '编队' : (teamGame ? `队${p.team}${p.team === myTeam ? '路人' : ''}` : '其他真人');
    const e = grp.get(key) ?? { n: 0, s: 0 };
    e.n++; e.s += vcnt[p.id]; grp.set(key, e);
  }
  w('  各队名下：' + [...grp.entries()].map(([key, e]) => `${key} ${e.n} 人 ${e.s} 格（${pc(e.s, total)}，人均 ${Math.round(e.s / e.n)}）`).join('；'));
  w();
  facts.voronoi = {
    land: total, humans: pts.length, squadBots: ours.length, squadCells: sumO, squadCellsPct: +(100 * sumO / total).toFixed(2),
    headPct: +(100 * ours.length / pts.length).toFixed(2), shareOverHead: +ratio.toFixed(3),
    perBot: Object.fromEntries(ours.map((p) => [botName.get(p.id), { x: Math.round(p.x), y: Math.round(p.y), cells: vcnt[p.id], nearestHuman: nn(p, pts), nearestNonSquad: nn(p, others.concat([p])) }])),
    squadMedian: med(ov), squadMin: Math.min(...ov), squadMax: Math.max(...ov), othersMedian: med(tv), othersQ1: qt(tv, 0.25),
    othersSmallerThanSquadMedian: others.filter((p) => vcnt[p.id] < med(ov)).length, others: others.length,
    groups: Object.fromEntries([...grp.entries()].map(([key, e]) => [key, { n: e.n, cells: e.s }])),
    bornAIInSquadCells: bornAI.size,
  };
}

function freeze(g) {
  frozen = true;
  own0 = new Int16Array(N);
  for (let c = 0; c < N; c++) own0[c] = ownerAt(g, c);
  adjAI = new Set();
  const d4 = g.dir4;
  for (const p of sqIds) {
    const B = g.border[p];
    if (!B || !g.alive[p]) continue;
    for (let i = 0; i < B.length; i++) {
      for (let k = 0; k < 4; k++) {
        const c = B[i] + d4[k];
        if (g.px[c] >= P_INNER) { const o = g.own[c]; if (o >= H) adjAI.add(o); }
      }
    }
  }
  setA = []; setB = []; setC = [];
  for (let c = 0; c < N; c++) {
    const o = own0[c];
    if (o < H) continue;
    if (sqSet.has(vor[c])) setA.push(c);
    if (adjAI.has(o)) setB.push(c);
    if (bornAI.has(o)) setC.push(c);
  }
  takersB = new Map();
}

function tally(g, cells) {
  const r = { squad: 0, mate: 0, enemy: 0, ai: 0, neutral: 0, n: cells.length };
  for (const c of cells) { const o = ownerAt(g, c); if (o === -2) continue; r[clsOf(g, o)]++; }
  return r;
}

function sample(g) {
  const t = g.t;
  // G2
  const live = pts.filter((p) => g.terr[p.id] > 0);
  const ours = live.filter((p) => sqSet.has(p.id)), others = live.filter((p) => !sqSet.has(p.id));
  const rt = (set) => set.map((p) => g.terr[p.id] / Math.max(1, vcnt[p.id]));
  const sumT = (set) => set.reduce((s, p) => s + g.terr[p.id], 0), sumC = (set) => set.reduce((s, p) => s + vcnt[p.id], 0);
  const teams = new Map();
  for (const p of live) {
    const key = sqSet.has(p.id) ? '编队' : (teamGame ? `队${p.team}${p.team === myTeam ? '路人' : ''}` : '其他真人');
    const e = teams.get(key) ?? { n: 0, terr: 0, cells: 0 };
    e.n++; e.terr += g.terr[p.id]; e.cells += vcnt[p.id]; teams.set(key, e);
  }
  // 人头口径：编队地 ÷ (全图陆地 × 编队在场号数 / 在场真人数)
  const fair = total * ours.length / Math.max(1, live.length);
  const row2 = {
    t, squadAlive: ours.length, humansAlive: live.length, squadTerr: sumT(ours), squadCells: sumC(ours), squadRatio: +(sumT(ours) / Math.max(1, sumC(ours))).toFixed(3),
    squadMedianRatio: +med(rt(ours)).toFixed(3), squadMinRatio: ours.length ? +Math.min(...rt(ours)).toFixed(3) : null, squadMaxRatio: ours.length ? +Math.max(...rt(ours)).toFixed(3) : null,
    othersTerr: sumT(others), othersCells: sumC(others), othersRatio: +(sumT(others) / Math.max(1, sumC(others))).toFixed(3),
    othersMedianRatio: +med(rt(others)).toFixed(3), othersQ1: +qt(rt(others), 0.25).toFixed(3), othersQ3: +qt(rt(others), 0.75).toFixed(3),
    squadMedianTerr: med(ours.map((p) => g.terr[p.id])), othersMedianTerr: med(others.map((p) => g.terr[p.id])),
    vsFair: +(sumT(ours) / Math.max(1, fair)).toFixed(3), squadSharePct: +(100 * sumT(ours) / total).toFixed(2),
    teams: Object.fromEntries([...teams.entries()].map(([key, e]) => [key, { n: e.n, terr: e.terr, cells: e.cells, ratio: +(e.terr / Math.max(1, e.cells)).toFixed(3) }])),
  };
  row2.perBot = Object.fromEntries(pts.filter((p) => sqSet.has(p.id)).map((p) => [botNameOf.get(p.id), { terr: g.terr[p.id], cells: vcnt[p.id], ratio: +(g.terr[p.id] / Math.max(1, vcnt[p.id])).toFixed(2) }]));
  rowsG2.push(row2);
  // G3：我方名下范围
  const reg = { squad: 0, mate: 0, enemy: 0, ai: 0, neutral: 0, n: 0 };
  let sqIn = 0;
  for (let c = 0; c < N; c++) {
    if (!land[c] || !sqSet.has(vor[c])) continue;
    const o = ownerAt(g, c);
    if (o === -2) continue;
    reg.n++;
    const k = clsOf(g, o);
    reg[k]++;
    if (k === 'squad') sqIn++;
  }
  rowsG3.push({ t, ...reg, squadTerr: row2.squadTerr, squadInside: sqIn, squadOutside: row2.squadTerr - sqIn });
  // G4
  if (frozen) {
    rowsG4.A.push({ t, ...tally(g, setA) });
    rowsG4.B.push({ t, ...tally(g, setB) });
    rowsG4.C.push({ t, ...tally(g, setC) });
  }
}

let inited = false, G = null, lastSampled = -1;
const R = resim(mid, {
  until: UNTIL,
  onState: (g, ctx) => {
    G = g;
    if (!inited) { inited = true; init(g, ctx); }
    if (!frozen && g.t >= FREEZE) freeze(g);
    if (AT.includes(g.t)) { sample(g); lastSampled = g.t; }
  },
});
// 对局在最后一个采样拍之前就结束：在终局那一拍补一个采样
if (G && inited && lastSampled !== G.t && G.t < AT[AT.length - 1]) { sample(G); lastSampled = G.t; }
if (G && frozen) {
  for (const c of setB) {
    const o = ownerAt(G, c);
    if (o < 0 || o === own0[c]) continue;
    takersB.set(o, (takersB.get(o) || 0) + 1);
  }
}

const head = `# ${mid} 抢地账（land-ledger.mjs；重放到 ${R.endTick} 拍；定格拍 ${FREEZE}；采样拍 ${AT.join('、')}）`;
lines.unshift('', head);
lines.shift();
lines.splice(1, 0, '');

w('[G2] 实际拿到 ÷ 出生份额（在场且有地的真人；「人头口径」= 编队地 ÷ (全图陆地 × 编队在场号数 ÷ 在场真人数)）');
for (const r of rowsG2) {
  w(`  t=${r.t}: 编队 ${r.squadAlive} 个号 地 ${r.squadTerr}（全图 ${r.squadSharePct}%）÷ 名下 ${r.squadCells} = ${r.squadRatio.toFixed(2)}（每号中位 ${r.squadMedianRatio.toFixed(2)}，最小 ${r.squadMinRatio} 最大 ${r.squadMaxRatio}；单号地中位 ${r.squadMedianTerr}）`
    + `｜其他真人 ${r.humansAlive - r.squadAlive} 个 合计 ${r.othersRatio.toFixed(2)}（中位 ${r.othersMedianRatio.toFixed(2)}，四分位 ${r.othersQ1.toFixed(2)}~${r.othersQ3.toFixed(2)}；单人地中位 ${r.othersMedianTerr}）｜人头口径 ${r.vsFair.toFixed(2)}`);
  w('         各队 地÷名下：' + Object.entries(r.teams).map(([key, e]) => `${key} ${e.n} 人 ${e.terr}/${e.cells}=${e.ratio.toFixed(2)}`).join('；'));
  w('         逐号 地/名下：' + Object.entries(r.perBot).map(([b, e]) => `${b} ${e.terr}/${e.cells}=${e.ratio.toFixed(2)}`).join('；'));
}
w();
w('[G3] 我方名下范围（Voronoi 份额内的陆地）各拍归谁；编队的地有多少在名下范围之外');
for (const r of rowsG3) {
  w(`  t=${r.t}: 范围内 ${r.n} 格 → 编队 ${pc(r.squad, r.n)}、同队路人 ${pc(r.mate, r.n)}、敌方真人 ${pc(r.enemy, r.n)}、内置 AI ${pc(r.ai, r.n)}、无主 ${pc(r.neutral, r.n)}｜编队地 ${r.squadTerr} = 范围内 ${r.squadInside} + 范围外 ${r.squadOutside}`);
}
w();
w(`[G4] 身边内置 AI 的地去向（把 ${FREEZE} 拍的归属定格）`);
const g4 = (title, cells, rows) => {
  w(`  ${title}：${cells.length} 格`);
  for (const r of rows) w(`     t=${r.t}: 编队 ${r.squad}（${pc(r.squad, r.n)}）、同队路人 ${r.mate}（${pc(r.mate, r.n)}）、敌方真人 ${r.enemy}（${pc(r.enemy, r.n)}）、仍属内置 AI ${r.ai}（${pc(r.ai, r.n)}）、无主 ${r.neutral}（${pc(r.neutral, r.n)}）`);
};
if (frozen) {
  g4(`(A) ${FREEZE} 拍时落在我方名下范围内、属于内置 AI 的格`, setA, rowsG4.A);
  g4(`(B) ${FREEZE} 拍时与编队接壤的内置 AI（${adjAI.size} 个）的全部格`, setB, rowsG4.B);
  g4(`(C) 出生点在我方名下范围内的内置 AI（${bornAI.size} 个）在 ${FREEZE} 拍的全部格`, setC, rowsG4.C);
  const tk = [...takersB.entries()].sort((a, b) => b[1] - a[1]).slice(0, 10);
  w(`  到 ${G.t} 拍为止，(B) 组的格子换到谁手里（前 10）：` + tk.map(([p, n]) => `${sqSet.has(p) ? '*' : ''}${nm(p)}${p < H && teamGame ? '(队' + R.teams[p] + ')' : ''} ${n}`).join('、') + '（* = 编队的号）');
  facts.aiFate = { freezeTick: FREEZE, A: { cells: setA.length, rows: rowsG4.A }, B: { cells: setB.length, ais: adjAI.size, rows: rowsG4.B }, C: { cells: setC.length, ais: bornAI.size, rows: rowsG4.C },
    takersB: tk.map(([p, n]) => ({ id: p, name: nm(p), squad: sqSet.has(p), team: p < H && teamGame ? R.teams[p] : null, cells: n })) };
} else {
  w(`  重放没有到 ${FREEZE} 拍（对局在 ${R.endTick} 拍结束），这一节空缺`);
}
facts.capture = rowsG2;
facts.region = rowsG3;
facts.endTick = R.endTick;
fs.mkdirSync(OUT, { recursive: true });
fs.writeFileSync(path.join(OUT, `${mid}-land.txt`), lines.join('\n') + '\n');
fs.writeFileSync(path.join(OUT, `${mid}-land-facts.json`), JSON.stringify(facts));
if (!quiet) console.log(lines.join('\n'));
else console.log(`${mid}: 已写 out/dossier/${mid}-land.txt（${lines.length} 行）`);
