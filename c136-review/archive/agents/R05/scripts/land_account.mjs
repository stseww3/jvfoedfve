// land_account.mjs — 一局的「好地账」（广播 0007 第 3 条）：出生份额、实际抢到 ÷ 份额、阵内/贴身机器人地的去向。全部机械计数。
//
// 口径：
//   出生份额（Voronoi）：把全图每一格陆地分给直线距离最近的真人出生点（不看地形阻隔）；出生点 = 录像重放 t=1 时各真人地块的质心
//       （match_truth.mjs 的 players[].spawn）。「我方号名下的地」= 我方各号的格子合起来。
//   实际抢到 ÷ 份额：某一拍某个真人的地 ÷ 它的出生份额；分组合计 = 组内在场者的地之和 ÷ 组内全体的份额之和
//       （阵亡的人份额照算，所以合计口径把「人没了」也算进去；另给在场者的中位数）。
//   名下的地归谁：我方号名下的那些格子，在给定拍分别属于：这个格子的主人自己 / 我方别的号 / 路人队友 / 敌方真人 / 机器人 / 中立。
//   机器人地的去向：在 --bot0 拍（默认 600）属于 AI 机器人的格子，分三个范围——
//       阵内 = 落在我方号名下格子里的；贴身 = 在 --bot0 拍与任一我方号接壤的那些机器人的全部格子；全图 = 所有机器人格子。
//       然后在各检查拍（默认 900,1200,1500,1800）看这些格子归谁：我方号 / 路人队友 / 敌方真人 / 仍是机器人 / 中立。
//   分组：我方号；路人队友（与我方号同队的其他真人）；各敌队（按录像的队号）。
//   我方号分在多个队里的局（B 系）：「路人队友 / 敌方真人」按参照的那个号自己的队算——名下的地、阵内机器人地按格子所属的号；
//       贴身 / 全图机器人地没有唯一的参照号，「路人队友」= 与任一我方号同队的其他真人；分组改成「T<队>真人」。
//       另出逐号表：t=--bot0 贴着这个号的机器人的全部格子，之后归 自己 / 同队真人（含同队我方号）/ 异队我方号 / 其他队真人 / 仍是机器人 / 中立。
// 先跑：node scripts/match_truth.mjs <id>
// 用法：node scripts/land_account.mjs <matchId> [--at 630,1500] [--bot0 600] [--fate 900,1200,1500,1800] [--json FILE]
import fs from 'node:fs';
import { simulate, P_INNER, NEUTRAL } from './sim_replay.mjs';
const { T_LAND } = await import('file:///agent/repos/c136-data/src/sim/sim/map.js');

const a = process.argv.slice(2);
const mid = a[0];
const val = (k, d) => (a.includes(k) ? a[a.indexOf(k) + 1] : d);
const AT = String(val('--at', '630,1500')).split(',').map(Number);
const BOT0 = +val('--bot0', 600);
const FATE = String(val('--fate', '900,1200,1500,1800')).split(',').map(Number);
const jsonOut = val('--json', '');
const J = JSON.parse(fs.readFileSync(`/tmp/c136-r05/truth/${mid}.json`, 'utf8'));
const H = J.humans;
const sq = new Map(J.squad.map((s) => [s.p, s.bot]));
const teamOf = new Map(J.players.filter((p) => p.id < H).map((p) => [p.id, p.team]));
const ourTeam = J.ourTeam ?? (J.squad[0] ? J.squad[0].team : -1);
const pts = J.players.filter((p) => p.id < H && p.spawn && p.spawn[0] >= 0).map((p) => ({ id: p.id, x: p.spawn[0], y: p.spawn[1], name: p.name, team: p.team }));
const sqTeams = new Set(J.squad.map((x) => x.team));
const MULTI = sqTeams.size > 1;
const grpOf = (id) => (sq.has(id) ? '我方号' : MULTI ? `T${teamOf.get(id)}真人` : teamOf.get(id) === ourTeam && ourTeam > 0 ? '路人队友' : `敌队T${teamOf.get(id)}`);
const med = (v) => { const s = [...v].sort((x, y) => x - y); return s.length ? (s.length % 2 ? s[(s.length - 1) / 2] : (s[s.length / 2 - 1] + s[s.length / 2]) / 2) : 0; };
const pct = (x, y) => (y ? (100 * x / y).toFixed(1) + '%' : '-');
const OUT = { matchId: mid, at: AT, bot0: BOT0, fate: FATE };

let W = 0, Hh = 0, N = 0, cell = null, landIdx = null, total = 0;
const cnt = new Map(pts.map((p) => [p.id, 0]));
const terrAt = new Map();      // t -> Int32Array(H)
const cellOwnAt = new Map();   // t -> {自己, 我方别的号, 路人队友, 敌方真人, 机器人, 中立}
let setA = null, setB = null, setC = null, adjBots = null, neutA = 0;
const fateRows = { A: [], B: [], C: [] };
const ownerOf = (g, c) => (g.px[c] >= P_INNER ? g.own[c] : NEUTRAL);
// ref = 参照的我方号（没有就按全队口径）
const isMate = (o, ref) => (ref != null && ref >= 0 && teamOf.has(ref) ? teamOf.get(o) === teamOf.get(ref) : MULTI ? sqTeams.has(teamOf.get(o)) : teamOf.get(o) === ourTeam && ourTeam > 0);
const catOf = (o, ref) => (o >= NEUTRAL ? '中立' : o >= H ? '机器人' : sq.has(o) ? '我方号' : isMate(o, ref) ? '路人队友' : '敌方真人');
const perBotAdj = new Map(); // 我方号 -> { bots:Set, cells:Int32Array, rows:[] }
const wantT = new Set([...AT, BOT0, ...FATE]);
const maxT = Math.max(...wantT) + 1;
let endSeen = 0;

const R = await simulate(mid, {
  maxTick: maxT,
  onStart(g) {
    W = g.W; Hh = g.H; N = g.N;
    cell = new Int16Array(N).fill(-1);
    const li = [];
    for (let y = 0; y < Hh; y++) {
      for (let x = 0; x < W; x++) {
        const c = y * W + x;
        if (!(g.px[c] === T_LAND || g.px[c] >= P_INNER)) continue;
        let best = -1, bd = Infinity;
        for (const p of pts) { const d = (p.x - x) * (p.x - x) + (p.y - y) * (p.y - y); if (d < bd) { bd = d; best = p.id; } }
        cell[c] = best; cnt.set(best, cnt.get(best) + 1); li.push(c);
      }
    }
    landIdx = Int32Array.from(li); total = li.length;
  },
  onTick(g, t) {
    endSeen = t;
    if (!wantT.has(t)) return;
    if (AT.includes(t) || FATE.includes(t) || t === BOT0) {
      terrAt.set(t, Int32Array.from({ length: H }, (_, p) => (g.alive[p] ? g.terr[p] : 0)));
      const comp = { 自己: 0, 我方别的号: 0, 路人队友: 0, 敌方真人: 0, 机器人: 0, 中立: 0 };
      if (MULTI) comp['异队我方号'] = 0;
      for (let i = 0; i < landIdx.length; i++) {
        const c = landIdx[i], co = cell[c];
        if (!sq.has(co)) continue;
        const o = ownerOf(g, c);
        if (o === co) comp['自己']++; else if (o < H && sq.has(o)) comp[MULTI && teamOf.get(o) !== teamOf.get(co) ? '异队我方号' : '我方别的号']++; else comp[catOf(o, co)]++;
      }
      cellOwnAt.set(t, comp);
    }
    if (t === BOT0) {
      adjBots = new Set();
      const d4 = [1, -1, W, -W];
      for (let i = 0; i < landIdx.length; i++) {
        const c = landIdx[i];
        const o = ownerOf(g, c);
        if (!(o < H && sq.has(o))) continue;
        for (const d of d4) {
          const c2 = c + d; if (c2 < 0 || c2 >= N || cell[c2] < 0) continue; const o2 = ownerOf(g, c2);
          if (o2 >= H && o2 < NEUTRAL) { adjBots.add(o2); let e = perBotAdj.get(o); if (!e) { e = { bots: new Set(), cells: null, rows: [] }; perBotAdj.set(o, e); } e.bots.add(o2); }
        }
      }
      for (const [, e] of perBotAdj) { const li2 = []; for (let i = 0; i < landIdx.length; i++) { const o = ownerOf(g, landIdx[i]); if (e.bots.has(o)) li2.push(landIdx[i]); } e.cells = Int32Array.from(li2); }
      const A = [], B = [], C = [];
      for (let i = 0; i < landIdx.length; i++) {
        const c = landIdx[i], o = ownerOf(g, c);
        if (o >= NEUTRAL) { if (sq.has(cell[c])) neutA++; continue; }
        if (o < H) continue;
        C.push(c);
        if (sq.has(cell[c])) A.push(c);
        if (adjBots.has(o)) B.push(c);
      }
      setA = Int32Array.from(A); setB = Int32Array.from(B); setC = Int32Array.from(C);
    }
    if (FATE.includes(t) && setA) {
      for (const [key, S] of [['A', setA], ['B', setB], ['C', setC]]) {
        const r = { t, 我方号: 0, 路人队友: 0, 敌方真人: 0, 机器人: 0, 中立: 0, byHuman: {} };
        for (let i = 0; i < S.length; i++) {
          const o = ownerOf(g, S[i]); const k = catOf(o, key === 'A' ? cell[S[i]] : null); r[k]++;
          if (o < H) r.byHuman[o] = (r.byHuman[o] || 0) + 1;
        }
        fateRows[key].push(r);
      }
      for (const [x, e] of perBotAdj) {
        const r = { t, 自己: 0, 同队真人: 0, 异队我方号: 0, 其他队真人: 0, 机器人: 0, 中立: 0 };
        for (let i = 0; i < e.cells.length; i++) {
          const o = ownerOf(g, e.cells[i]);
          if (o >= NEUTRAL) r['中立']++; else if (o >= H) r['机器人']++; else if (o === x) r['自己']++; else if (teamOf.get(o) === teamOf.get(x)) r['同队真人']++; else if (sq.has(o)) r['异队我方号']++; else r['其他队真人']++;
        }
        e.rows.push(r);
      }
    }
  },
});

// ---------- ① 出生份额 ----------
const ours = pts.filter((p) => sq.has(p.id)), others = pts.filter((p) => !sq.has(p.id));
const sumO = ours.reduce((s, p) => s + cnt.get(p.id), 0);
const groups = new Map();
for (const p of pts) { const k = grpOf(p.id); const g = groups.get(k) ?? { n: 0, cells: 0, ids: [] }; g.n++; g.cells += cnt.get(p.id); g.ids.push(p.id); groups.set(k, g); }
console.log(`===== ${mid} 好地账（图 ${W}×${Hh}，陆地 ${total} 格；真人出生点 ${pts.length} 个，人均 ${Math.round(total / pts.length)} 格；我方号 ${ours.length} 个）=====`);
console.log('\n== ① 出生份额（Voronoi：每格陆地归最近的真人出生点）==');
const headShare = ours.length / pts.length, landShare = sumO / total;
console.log(`   我方号名下 ${sumO} 格 = 全图 ${pct(sumO, total)}；人数占 ${pct(ours.length, pts.length)} → 份额 ÷ 人数 = ${(landShare / headShare).toFixed(2)}`);
console.log(`   每号份额：我方号 中位 ${med(ours.map((p) => cnt.get(p.id)))}（最小 ${Math.min(...ours.map((p) => cnt.get(p.id)))}，最大 ${Math.max(...ours.map((p) => cnt.get(p.id)))}）｜其他真人 中位 ${med(others.map((p) => cnt.get(p.id)))}（最小 ${Math.min(...others.map((p) => cnt.get(p.id)))}，最大 ${Math.max(...others.map((p) => cnt.get(p.id)))}）｜我方中位 ÷ 其他真人中位 = ${(med(ours.map((p) => cnt.get(p.id))) / Math.max(1, med(others.map((p) => cnt.get(p.id))))).toFixed(2)}`);
console.log('   各组：' + [...groups.entries()].map(([k, g]) => `${k} ${g.n} 人 ${g.cells} 格（${pct(g.cells, total)}，人均 ${Math.round(g.cells / g.n)}，份额÷人数 ${(g.cells / total / (g.n / pts.length)).toFixed(2)}）`).join('；'));
console.log('   我方号逐个：' + ours.map((p) => `${sq.get(p.id)}(${p.x},${p.y}) ${cnt.get(p.id)}`).join('；'));
OUT.multiTeam = MULTI; OUT.squadTeams = Object.fromEntries([...sqTeams].sort((x, y) => x - y).map((t) => [t, J.squad.filter((x) => x.team === t).map((x) => x.bot)]));
if (MULTI) console.log('   我方号分在 ' + sqTeams.size + ' 个队：' + Object.entries(OUT.squadTeams).map(([t, b]) => `T${t} ${b.join('、')}`).join('；'));
OUT.voronoi = { land: total, humans: pts.length, squad: ours.length, squadCells: sumO, landShare, headShare, ratio: landShare / headShare, squadMedian: med(ours.map((p) => cnt.get(p.id))), othersMedian: med(others.map((p) => cnt.get(p.id))),
  groups: Object.fromEntries([...groups.entries()].map(([k, g]) => [k, { n: g.n, cells: g.cells }])), perBot: ours.map((p) => ({ bot: sq.get(p.id), x: p.x, y: p.y, cells: cnt.get(p.id) })) };

// ---------- ② 实际抢到 ÷ 份额 ----------
console.log('\n== ② 实际抢到 ÷ 出生份额 ==');
OUT.capture = [];
for (const t of AT) {
  const terr = terrAt.get(t);
  if (!terr) { console.log(`   t=${t}: 对局在这之前已结束（最后一拍 ${endSeen}）`); continue; }
  const row = { t, groups: {} };
  const parts = [];
  for (const [k, g] of groups) {
    const live = g.ids.filter((id) => terr[id] > 0);
    const sumT = live.reduce((s, id) => s + terr[id], 0);
    const ratios = live.map((id) => terr[id] / Math.max(1, cnt.get(id)));
    row.groups[k] = { n: g.n, alive: live.length, land: sumT, cells: g.cells, ratio: sumT / Math.max(1, g.cells), medianRatio: med(ratios), medianLand: med(live.map((id) => terr[id])) };
    parts.push(`${k} 在场 ${live.length}/${g.n}：地 ${sumT} ÷ 份额 ${g.cells} = ${(sumT / Math.max(1, g.cells)).toFixed(2)}（每人 地÷份额 中位 ${med(ratios).toFixed(2)}，地中位 ${Math.round(med(live.map((id) => terr[id])))}）`);
  }
  const oth = others.filter((p) => terr[p.id] > 0);
  row.othersMedianRatio = med(oth.map((p) => terr[p.id] / Math.max(1, cnt.get(p.id))));
  row.othersMedianLand = med(oth.map((p) => terr[p.id]));
  row.perBot = ours.map((p) => ({ bot: sq.get(p.id), land: terr[p.id], cells: cnt.get(p.id), ratio: terr[p.id] / Math.max(1, cnt.get(p.id)) }));
  console.log(`   t=${t}: ` + parts.join('\n          '));
  console.log(`          其他真人合在一起：每人 地÷份额 中位 ${row.othersMedianRatio.toFixed(2)}、地中位 ${Math.round(row.othersMedianLand)}｜我方号逐个 地/份额：` + row.perBot.map((b) => `${b.bot} ${b.land}/${b.cells}=${b.ratio.toFixed(2)}`).join('；'));
  OUT.capture.push(row);
}
console.log('   -- 我方号名下的地在各拍归谁（占名下总格数）');
OUT.cellOwners = [];
for (const t of [...cellOwnAt.keys()].sort((x, y) => x - y)) {
  const c = cellOwnAt.get(t);
  console.log(`      t=${t}: ` + Object.entries(c).map(([k, v]) => `${k} ${pct(v, sumO)}`).join('、'));
  OUT.cellOwners.push({ t, ...c, total: sumO });
}

// ---------- ③ 机器人地的去向 ----------
console.log(`\n== ③ 机器人地的去向（t=${BOT0} 时属于 AI 机器人的格子，之后归谁）==`);
if (!setA) console.log(`   对局在 t=${BOT0} 之前已结束`);
else {
  const nameOf = (id) => (sq.has(+id) ? `我方 ${sq.get(+id)}` : `${(J.players.find((p) => p.id === +id) || {}).name}#${id}`);
  const lab = { A: `阵内（落在我方号名下格子里的机器人地）${setA.length} 格 = 我方名下的 ${pct(setA.length, sumO)}（另有中立 ${neutA} 格 = ${pct(neutA, sumO)}）`, B: `贴身（t=${BOT0} 与我方号接壤的 ${adjBots.size} 个机器人的全部地）${setB.length} 格`, C: `全图机器人地 ${setC.length} 格 = 全图陆地的 ${pct(setC.length, total)}` };
  OUT.botLand = { A: { tiles: setA.length, neutralInCells: neutA }, B: { tiles: setB.length, bots: adjBots.size }, C: { tiles: setC.length }, fate: fateRows };
  for (const key of ['A', 'B', 'C']) {
    const S = key === 'A' ? setA : key === 'B' ? setB : setC;
    console.log(`   ${lab[key]}`);
    for (const r of fateRows[key]) {
      const top = Object.entries(r.byHuman).sort((x, y) => y[1] - x[1]).slice(0, 4).map(([id, v]) => `${nameOf(id)} ${v}`).join('、');
      console.log(`      t=${r.t}: 我方号 ${pct(r['我方号'], S.length)}、路人队友 ${pct(r['路人队友'], S.length)}、敌方真人 ${pct(r['敌方真人'], S.length)}、仍是机器人 ${pct(r['机器人'], S.length)}、中立 ${pct(r['中立'], S.length)}${top ? `｜拿得最多：${top}` : ''}`);
    }
  }
  console.log(`   -- 逐号：t=${BOT0} 贴着这个号的机器人的全部格子，到 t=${FATE[FATE.length - 1]} 归谁`);
  OUT.botLand.perBotAdj = [];
  for (const s0 of J.squad) {
    const e = perBotAdj.get(s0.p);
    if (!e || !e.cells.length) { console.log(`      ${s0.bot}(T${s0.team}): t=${BOT0} 不贴机器人`); OUT.botLand.perBotAdj.push({ bot: s0.bot, team: s0.team, bots: 0, tiles: 0, rows: [] }); continue; }
    const r = e.rows[e.rows.length - 1];
    console.log(`      ${s0.bot}(T${s0.team}): ${e.bots.size} 个机器人 ${e.cells.length} 格 → ` + (r ? ['自己', '同队真人', '异队我方号', '其他队真人', '机器人', '中立'].filter((k) => r[k] || k === '自己').map((k) => `${k === '机器人' ? '仍是机器人' : k} ${pct(r[k], e.cells.length)}`).join('、') : '对局已结束'));
    OUT.botLand.perBotAdj.push({ bot: s0.bot, team: s0.team, bots: e.bots.size, tiles: e.cells.length, rows: e.rows });
  }
  // 人均口径：到最后一个检查拍，每个在场真人从「全图机器人地」里拿到多少
  const last = fateRows.C[fateRows.C.length - 1];
  if (last) {
    const per = (ids) => ids.map((id) => last.byHuman[id] || 0);
    const parts = [];
    for (const [k, g] of groups) parts.push(`${k} 合计 ${per(g.ids).reduce((s, v) => s + v, 0)} 格（人均 ${Math.round(per(g.ids).reduce((s, v) => s + v, 0) / g.n)}，每人中位 ${Math.round(med(per(g.ids)))}）`);
    console.log(`   到 t=${last.t} 各组从全图机器人地里拿到：` + parts.join('；'));
    OUT.botLand.perGroupLast = Object.fromEntries([...groups.entries()].map(([k, g]) => [k, { n: g.n, tiles: per(g.ids).reduce((s, v) => s + v, 0), median: med(per(g.ids)) }]));
  }
}
if (jsonOut) { fs.writeFileSync(jsonOut, JSON.stringify(OUT)); console.log(`\n→ ${jsonOut}`); }
