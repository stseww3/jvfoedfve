#!/usr/bin/env node
// 46_voronoi.mjs — R07：出生点的「天然地盘」、各拍实际拿到多少、身边内置 AI 的地最后归了谁（统筹广播 0007-③ 的三张账）。
//
// 做法（干净模拟器按录像重演，只读不改局面）：
//   1) 出生阶段结束的那一拍，取每个有地的真人位的落点（领土包围盒中心，和 66_spawn_truth.mjs 同口径），
//      把全图每个陆地格分给直线距离最近的真人位（Voronoi；不看水和山的阻隔）→ 每个真人、每个组名下的「天然地盘」格数。
//   2) --at 的各拍（默认 630,1500）：每个组实际领土 ÷ 天然地盘；并且数一遍每个组的天然地盘里的格子当时在谁手里
//      （本组 / 别的真人 / 内置 AI / 无主地），以及本组在自己天然地盘之外拿到的格数。
//   3) --ai-from 拍（默认 630）和每个组接壤的内置 AI，把它们当时的领土记成「脚印」；
//      --ai-to 的各拍（默认 1500,1800）数脚印里的格子在谁手里（本组吃到 / 别的真人吃到 / 还是内置 AI / 无主地）。
//      另列「阵型圈内的 AI」：脚印过半落在我方天然地盘里的内置 AI（不要求当拍接壤）。
// 分组：我方号 / 和我方同队的其他真人 / 每个敌队的真人（没有队伍的真人归「无队真人」）。真人位离开后被接管的仍按原来的队算地盘，
//      但数「格子在谁手里」时，已离开的席位（state=2）和内置 AI 一样算 AI。
//
// 用法（必须套重计算闸）：
//   bash c136-review/tools/run-heavy.sh node c136-review/agents/R07/scripts/46_voronoi.mjs <matchId> [--at 630,1500] [--ai-from 630] [--ai-to 1500,1800]
// 输出：out/<matchId>/voronoi.txt、voronoi.json
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const DATA = '/agent/repos/c136-data';
const HERE = path.dirname(fileURLToPath(import.meta.url));
const args = process.argv.slice(2);
const mid = args[0];
const opt = (k, d) => { const i = args.indexOf(k); return i >= 0 ? args[i + 1] : d; };
if (!mid) { console.error('用法：46_voronoi.mjs <matchId> [--at 630,1500] [--ai-from 630] [--ai-to 1500,1800]'); process.exit(2); }
const atList = opt('--at', '630,1500').split(',').map(Number).filter((x) => x > 0);
const aiFrom = +opt('--ai-from', '630');
const aiTo = opt('--ai-to', '1500,1800').split(',').map(Number).filter((x) => x > aiFrom);
const OUT = path.join(HERE, '..', 'out', mid);
fs.mkdirSync(OUT, { recursive: true });
const SIM = await import(path.join(DATA, 'src/sim/sim/index.js'));
(await import(path.join(HERE, 'r07simfix.mjs'))).applyOddLandingFix(SIM);
const { resim } = await import(path.join(DATA, 'src/tools/resim.mjs'));
const LIB = await import(path.join(DATA, 'src/sim/tools/c102-replay-lib.mjs'));
const { T_LAND, P_INNER } = SIM;
const d = LIB.decodeReplay(fs.readFileSync(path.join(DATA, 'bundles', mid, 'replay.txt'), 'utf8'));
const H = d.vu.humanCount;
const names = d.vu.playerNamesData ? Array.from(d.vu.playerNamesData).slice(0, H).map((s) => String(s ?? '').trim()) : [];
const SQUAD = ['sora_w', 'ryan_m', 'noah88', 'zexos1', 'talon5', 'alex_k', 'leo_tx', 'zero_7', 'kaito9', 'riku_x'];
const squadOf = (p) => { if (p >= H) return null; const n = (names[p] || '').toLowerCase(); for (const s of SQUAD) if (n.endsWith(s)) return s; return null; };
const fmt = (n) => Math.round(n).toLocaleString('en-US');
const pc = (a, b) => (b > 0 ? (100 * a / b).toFixed(1) + '%' : '-');
const med = (a) => { if (!a.length) return 0; const s = [...a].sort((x, y) => x - y); const m = s.length >> 1; return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2; };

let sites = null;        // [{p, x, y, team, squad}]
let vor = null;          // Int16Array：陆地格 → sites 下标；非陆地 -1
let landCells = null;    // Int32Array：全部陆地格
let spawnEndT = -1, landCount = 0, engineLand = 0;
let squadTeams = null;
let groupName = null;    // p → 组名
const snaps = new Map(); // t → {terr, own: Int16Array(陆地格的主人；-1 无主地), left:Set, bal}
let geom = null;         // 阵型朝向：质心、8 个扇区的陆地 / 水
let foot = null;         // {cellAI: Int16Array, ai: Map(id → {cells, bal, adj:Set(组名), adjBots:Set, inOurVor})}
const wantT = new Set([...atList, aiFrom, ...aiTo]);
const maxT = Math.max(...wantT);

const ownerSnap = (g) => {
  const own = new Int16Array(landCells.length);
  const px = g.px, ow = g.own;
  for (let i = 0; i < landCells.length; i++) { const c = landCells[i]; own[i] = px[c] >= P_INNER ? ow[c] : -1; }
  const left = new Set();
  for (let p = 0; p < H; p++) if (g.state[p] === 2) left.add(p);
  return { terr: Array.from(g.terr), bal: Array.from(g.bal), own, left, alive: Array.from(g.alive) };
};

const proto = SIM.Game.prototype;
const origTick = proto.tick;
proto.tick = function () {
  origTick.call(this);
  const g = this;
  if (g.spawnPhase) return;
  if (sites === null) {
    spawnEndT = g.t; engineLand = g.land;
    const W = g.W, px = g.px;
    sites = [];
    for (let p = 0; p < H; p++) {
      if (g.terr[p] <= 0) continue;
      sites.push({ p, x: (g.x0[p] + g.x1[p] + 1) / 2, y: (g.y0[p] + g.y1[p] + 1) / 2, team: g.teams[p], squad: squadOf(p), vor: 0 });
    }
    squadTeams = new Set(sites.filter((s) => s.squad).map((s) => s.team).filter((t) => t !== 0));
    groupName = (p) => {
      if (squadOf(p)) return '我方号';
      const t = g.teams[p];
      if (t === 0) return '无队真人';
      return squadTeams.has(t) ? `T${t} 其他真人` : `T${t} 真人`;
    };
    for (const s of sites) s.group = groupName(s.p);
    // 阵型朝向：以我方落点质心为圆心，8 个方位扇区（每 45°）× 两个环（60~160、160~260 像素）里的陆地 / 水格数
    {
      const sq = sites.filter((s) => s.squad);
      if (sq.length) {
        const cx = sq.reduce((a, s) => a + s.x, 0) / sq.length, cy = sq.reduce((a, s) => a + s.y, 0) / sq.length;
        const Hh = (px.length / W) | 0;
        const sec = Array.from({ length: 8 }, () => ({ land: [0, 0], water: [0, 0], off: [0, 0] }));
        const R = 260;
        for (let dy = -R; dy <= R; dy++) {
          for (let dx = -R; dx <= R; dx++) {
            const dd = Math.hypot(dx, dy);
            if (dd < 60 || dd > R) continue;
            const ring = dd <= 160 ? 0 : 1;
            // 方位：0 = 北（y 减小），顺时针
            const k = ((Math.round((Math.atan2(dx, -dy) * 180 / Math.PI) / 45) % 8) + 8) % 8;
            const x = Math.round(cx + dx), y = Math.round(cy + dy);
            if (x < 0 || y < 0 || x >= W || y >= Hh) { sec[k].off[ring]++; continue; }
            const v = px[y * W + x];
            if (v === T_LAND || v >= P_INNER) sec[k].land[ring]++; else sec[k].water[ring]++;
          }
        }
        geom = { cx, cy, sec, W, Hh };
      }
    }
    const cells = [];
    for (let c = 0; c < px.length; c++) if (px[c] === T_LAND || px[c] >= P_INNER) cells.push(c);
    landCells = Int32Array.from(cells); landCount = cells.length;
    vor = new Int16Array(landCells.length);
    const n = sites.length;
    const sx = Float64Array.from(sites.map((s) => s.x)), sy = Float64Array.from(sites.map((s) => s.y));
    for (let i = 0; i < landCells.length; i++) {
      const c = landCells[i];
      const x = (c % W) + 0.5, y = ((c / W) | 0) + 0.5;
      let best = -1, bd = Infinity;
      for (let k = 0; k < n; k++) { const dx = x - sx[k], dy = y - sy[k]; const dd = dx * dx + dy * dy; if (dd < bd) { bd = dd; best = k; } }
      vor[i] = best; sites[best].vor++;
    }
  }
  if (wantT.has(g.t)) snaps.set(g.t, ownerSnap(g));
  if (g.t === aiFrom) {
    // 每个组接壤的内置 AI（含已离开的席位）
    const px = g.px, own = g.own, d4 = g.dir4;
    const ai = new Map();
    for (const s of sites) {
      const p = s.p;
      if (!g.alive[p] || g.state[p] === 2 || g.terr[p] <= 0) continue;
      const B = g.border[p] || [];
      for (let i = 0; i < B.length; i++) {
        for (let k = 0; k < 4; k++) {
          const c = B[i] + d4[k];
          if (px[c] < P_INNER) continue;
          const o = own[c];
          if (o === p || !g.isBot(o)) continue;
          let e = ai.get(o);
          if (!e) { e = { cells: 0, bal: g.bal[o], team: g.teams[o], adj: new Set(), adjBots: new Set(), mateAdj: new Set(), mateAdjBots: new Set(), inOurVor: 0 }; ai.set(o, e); }
          // 8 队局里内置 AI 也分队：和 p 同队的 AI（以及同队已离开的席位）p 打不了，单独记
          if (g.teams[p] !== 0 && g.teams[o] === g.teams[p]) { e.mateAdj.add(s.group); if (s.squad) e.mateAdjBots.add(s.squad); continue; }
          e.adj.add(s.group);
          if (s.squad) e.adjBots.add(s.squad);
        }
      }
    }
    // 脚印：当拍所有内置 AI 的地都记下来（阵型圈内的 AI 不要求接壤）
    const cellAI = new Int16Array(landCells.length).fill(-1);
    const sq = sites.map((s) => !!s.squad);
    for (let i = 0; i < landCells.length; i++) {
      const c = landCells[i];
      if (px[c] < P_INNER) continue;
      const o = own[c];
      if (!g.isBot(o)) continue;
      let e = ai.get(o);
      if (!e) { e = { cells: 0, bal: g.bal[o], team: g.teams[o], adj: new Set(), adjBots: new Set(), mateAdj: new Set(), mateAdjBots: new Set(), inOurVor: 0 }; ai.set(o, e); }
      e.cells++; cellAI[i] = o;
      if (sq[vor[i]]) e.inOurVor++;
    }
    botTeamed = false;
    for (const e of ai.values()) if (e.team !== 0) botTeamed = true;
    foot = { cellAI, ai };
  }
};
let botTeamed = false;
const res = await resim(mid, { until: maxT + 5 });
const v = res.validate || {};
if (sites === null) { console.error('重演没有走出出生阶段'); process.exit(1); }

const groups = [...new Set(sites.map((s) => s.group))].sort((a, b) => (a === '我方号' ? -1 : b === '我方号' ? 1 : a.localeCompare(b)));
const siteOfP = new Map(sites.map((s, i) => [s.p, i]));
const grpOfP = (p) => (siteOfP.has(p) ? sites[siteOfP.get(p)].group : null);
const nH = sites.length;
const L = [];
L.push(`# ${mid} 出生点的天然地盘（Voronoi）与实际拿到的地（46_voronoi.mjs；干净模拟器重演，核对 ${v.bothExact}/${v.rows}）`);
L.push(`# 出生阶段结束 t=${spawnEndT}；有地的真人位 ${nH} 个；陆地 ${fmt(landCount)} 格（引擎 g.land=${fmt(engineLand)}）；人均 ${fmt(landCount / nH)} 格`);
L.push('# 天然地盘 = 把每个陆地格分给直线距离最近的真人落点；不看水、山的阻隔，也不算内置 AI 的落点——它量的是「站位给了多少地」，不是「能拿到多少地」。');
L.push('');
L.push('A. 分组：人数（占真人位）| 天然地盘（占陆地）| 每人平均 ÷ 全场人均 | 每人中位数 | 最小~最大');
const J = { matchId: mid, spawnEndT, humans: nH, land: landCount, groups: {}, squad: {}, at: {}, ai: {} };
for (const gname of groups) {
  const ss = sites.filter((s) => s.group === gname);
  const tot = ss.reduce((a, s) => a + s.vor, 0);
  const vs = ss.map((s) => s.vor);
  L.push(`  ${gname}\t${ss.length}（${pc(ss.length, nH)}）\t${fmt(tot)}（${pc(tot, landCount)}）\t${(tot / ss.length / (landCount / nH)).toFixed(2)}\t${fmt(med(vs))}\t${fmt(Math.min(...vs))}~${fmt(Math.max(...vs))}`);
  J.groups[gname] = { n: ss.length, headShare: ss.length / nH, vor: tot, vorShare: tot / landCount, perHeadRel: tot / ss.length / (landCount / nH), vorMedian: med(vs) };
}
const allV = sites.map((s) => s.vor).sort((a, b) => a - b);
L.push(`  全场真人位每人天然地盘：中位数 ${fmt(med(allV))}、最小 ${fmt(allV[0])}、最大 ${fmt(allV[allV.length - 1])}`);

L.push('');
L.push('B. 各拍实际拿到的地：组 | 实际领土 | ÷ 天然地盘 | 自己的天然地盘当拍在谁手里：本组 / 别的真人 / 内置 AI（含已离开的席位）/ 无主地 | 本组在天然地盘之外拿到的格数');
for (const t of atList) {
  const s = snaps.get(t);
  if (!s) { L.push(`  t=${t}：录像没有到这一拍`); continue; }
  J.at[t] = {};
  // region[g] = {own, human, ai, neutral}；outside[g]
  const reg = new Map(groups.map((gname) => [gname, { own: 0, human: 0, ai: 0, neutral: 0, byGroup: new Map() }]));
  const inside = new Map(groups.map((gname) => [gname, 0]));
  for (let i = 0; i < landCells.length; i++) {
    const gs = sites[vor[i]].group;
    const r = reg.get(gs);
    const o = s.own[i];
    if (o < 0) { r.neutral++; continue; }
    const go = o < H && !s.left.has(o) ? grpOfP(o) : null;
    if (go === null) { r.ai++; continue; }
    if (go === gs) { r.own++; continue; }
    r.human++; r.byGroup.set(go, (r.byGroup.get(go) || 0) + 1);
  }
  L.push(`  t=${t}`);
  for (const gname of groups) {
    const ss = sites.filter((x) => x.group === gname);
    const vorTot = ss.reduce((a, x) => a + x.vor, 0);
    const terr = ss.reduce((a, x) => a + (s.left.has(x.p) ? 0 : s.terr[x.p]), 0);
    const r = reg.get(gname);
    const by = [...r.byGroup].sort((a, b) => b[1] - a[1]).slice(0, 3).map(([k, n]) => `${k} ${fmt(n)}`).join('、');
    L.push(`    ${gname}\t${fmt(terr)}\t${pc(terr, vorTot)}\t${pc(r.own, vorTot)} / ${pc(r.human, vorTot)}${by ? `（${by}）` : ''} / ${pc(r.ai, vorTot)} / ${pc(r.neutral, vorTot)}\t${fmt(terr - r.own)}`);
    J.at[t][gname] = { terr, vor: vorTot, ratio: terr / Math.max(1, vorTot), ownIn: r.own, humanIn: r.human, aiIn: r.ai, neutralIn: r.neutral, outside: terr - r.own };
  }
}

L.push('');
L.push('C. 我方每个号：天然地盘（在全场真人位里的名次）| 各拍领土（÷ 天然地盘）| 各拍天然地盘归属：自己 / 我方其他号 / 别的真人 / 内置 AI / 无主地');
const rankOf = (x) => 1 + allV.filter((y) => y > x).length;
for (const st of sites.filter((x) => x.squad).sort((a, b) => b.vor - a.vor)) {
  const k = siteOfP.get(st.p);
  const parts = [];
  J.squad[st.squad] = { vor: st.vor, rank: rankOf(st.vor), at: {} };
  for (const t of atList) {
    const s = snaps.get(t);
    if (!s) continue;
    let self = 0, mate = 0, hum = 0, ai = 0, neu = 0;
    for (let i = 0; i < landCells.length; i++) {
      if (vor[i] !== k) continue;
      const o = s.own[i];
      if (o < 0) neu++;
      else if (o === st.p) self++;
      else if (o >= H || s.left.has(o)) ai++;
      else if (squadOf(o)) mate++;
      else hum++;
    }
    parts.push(`t=${t} ${fmt(s.terr[st.p])}（${pc(s.terr[st.p], st.vor)}）；归属 ${pc(self, st.vor)} / ${pc(mate, st.vor)} / ${pc(hum, st.vor)} / ${pc(ai, st.vor)} / ${pc(neu, st.vor)}`);
    J.squad[st.squad].at[t] = { terr: s.terr[st.p], self, mate, human: hum, ai, neutral: neu };
  }
  L.push(`  ${st.squad}\t${fmt(st.vor)}（第 ${rankOf(st.vor)}/${nH}）\t${parts.join(' ｜ ')}`);
}
{
  const ov = sites.filter((x) => x.squad).map((x) => x.vor), oth = sites.filter((x) => !x.squad).map((x) => x.vor);
  L.push(`  我方号天然地盘中位数 ${fmt(med(ov))}；其他真人位中位数 ${fmt(med(oth))}`);
  J.squadVorMedian = med(ov); J.otherVorMedian = med(oth);
}

L.push('');
L.push(`D. 身边内置 AI 的地去了哪：t=${aiFrom} 和本组接壤的内置 AI 当拍的领土（脚印）→ 之后各拍这些格子在谁手里`);
L.push('   组 | 接壤的 AI 个数 / 脚印格数 / 当拍余额 | 到 t：本组 / 别的真人 / 还是内置 AI / 无主地（同一个 AI 可以同时和几个组接壤，各组各算一遍）');
if (botTeamed) L.push('   本局内置 AI 也分了队（实际队数 ≥8 时引擎把 AI 按席位号轮流分进各队）：和某一组同队的 AI 该组打不了。下面「接壤的 AI」只算该组打得了的；同队 AI 另列在每行末尾。');
if (foot) {
  const sFrom = snaps.get(aiFrom);
  for (const gname of groups) {
    const ids = [...foot.ai].filter(([, e]) => e.adj.has(gname)).map(([id]) => id);
    const idSet = new Set(ids);
    const cells = ids.reduce((a, id) => a + foot.ai.get(id).cells, 0);
    const bal = ids.reduce((a, id) => a + foot.ai.get(id).bal, 0);
    const parts = [];
    J.ai[gname] = { n: ids.length, cells, bal, to: {} };
    for (const t of aiTo) {
      const s = snaps.get(t);
      if (!s) { parts.push(`t=${t} 录像没到`); continue; }
      let own = 0, hum = 0, ai = 0, neu = 0;
      const by = new Map();
      for (let i = 0; i < landCells.length; i++) {
        const a = foot.cellAI[i];
        if (a < 0 || !idSet.has(a)) continue;
        const o = s.own[i];
        if (o < 0) { neu++; continue; }
        const go = o < H && !s.left.has(o) ? grpOfP(o) : null;
        if (go === null) ai++;
        else if (go === gname) own++;
        else { hum++; by.set(go, (by.get(go) || 0) + 1); }
      }
      const byTxt = [...by].sort((a, b) => b[1] - a[1]).slice(0, 3).map(([k, n]) => `${k} ${fmt(n)}`).join('、');
      parts.push(`t=${t} ${fmt(own)}（${pc(own, cells)}）/ ${fmt(hum)}（${pc(hum, cells)}${byTxt ? '：' + byTxt : ''}）/ ${fmt(ai)}（${pc(ai, cells)}）/ ${fmt(neu)}（${pc(neu, cells)}）`);
      J.ai[gname].to[t] = { own, human: hum, ai, neutral: neu };
    }
    const mateIds = [...foot.ai].filter(([, e]) => e.mateAdj.has(gname)).map(([id]) => id);
    const mateCells = mateIds.reduce((a, id) => a + foot.ai.get(id).cells, 0);
    J.ai[gname].mateAi = { n: mateIds.length, cells: mateCells };
    L.push(`  ${gname}\t${ids.length} / ${fmt(cells)} / ${fmt(bal)}\t${parts.join(' ｜ ')}${botTeamed ? `\t同队 AI（打不了）${mateIds.length} 个 / ${fmt(mateCells)} 格` : ''}`);
  }
  // 我方逐个 AI
  const lastT = [...aiTo].reverse().find((t) => snaps.has(t));
  L.push('');
  L.push(`D2. 我方接壤的内置 AI 逐个（t=${aiFrom}）：AI | 脚印格数 / 余额 | 贴着的我方号 | 脚印里落在我方天然地盘的比例 | 到 t=${lastT ?? '-'} 归属（前四）`);
  const ourIds = [...foot.ai].filter(([, e]) => e.adj.has('我方号')).sort((a, b) => b[1].cells - a[1].cells);
  for (const [id, e] of ourIds) {
    let txt = '-';
    if (lastT !== undefined) {
      const s = snaps.get(lastT);
      const by = new Map();
      for (let i = 0; i < landCells.length; i++) {
        if (foot.cellAI[i] !== id) continue;
        const o = s.own[i];
        const k = o < 0 ? '无主地' : o === id ? '还是它' : (o >= H || s.left.has(o)) ? '别的内置 AI' : squadOf(o) ? `我方 ${squadOf(o)}` : `${names[o].slice(0, 14)}[${grpOfP(o)}]`;
        by.set(k, (by.get(k) || 0) + 1);
      }
      txt = [...by].sort((a, b) => b[1] - a[1]).slice(0, 4).map(([k, n]) => `${k} ${fmt(n)}`).join('、');
    }
    L.push(`  AI#${id}\t${fmt(e.cells)} / ${fmt(e.bal)}\t${[...e.adjBots].join('、')}\t${pc(e.inOurVor, e.cells)}\t${txt}`);
  }
  if (botTeamed) {
    const mate = [...foot.ai].filter(([, e]) => e.mateAdj.has('我方号')).sort((a, b) => b[1].cells - a[1].cells);
    L.push(`  和我方接壤的同队 AI（打不了）${mate.length} 个 / ${fmt(mate.reduce((a, [, e]) => a + e.cells, 0))} 格：` + mate.map(([id, e]) => `AI#${id} ${fmt(e.cells)} 格 / ${fmt(e.bal)} 兵（贴 ${[...e.mateAdjBots].join('、')}；${pc(e.inOurVor, e.cells)} 在我方天然地盘里）`).join('；'));
  }
  // 阵型圈内的 AI：脚印过半在我方天然地盘里
  const isMateAi = (e) => e.team !== 0 && squadTeams.has(e.team);
  const inIds = [...foot.ai].filter(([, e]) => e.cells > 0 && e.inOurVor * 2 > e.cells && !isMateAi(e)).map(([id]) => id);
  const inMate = [...foot.ai].filter(([, e]) => e.cells > 0 && e.inOurVor * 2 > e.cells && isMateAi(e));
  const inSet = new Set(inIds);
  const inCells = inIds.reduce((a, id) => a + foot.ai.get(id).cells, 0);
  const inAdj = inIds.filter((id) => foot.ai.get(id).adj.has('我方号')).length;
  const parts = [];
  J.aiInOurVor = { n: inIds.length, cells: inCells, adjacent: inAdj, to: {} };
  for (const t of aiTo) {
    const s = snaps.get(t);
    if (!s) continue;
    let own = 0, mate = 0, hum = 0, ai = 0, neu = 0;
    for (let i = 0; i < landCells.length; i++) {
      const a = foot.cellAI[i];
      if (a < 0 || !inSet.has(a)) continue;
      const o = s.own[i];
      if (o < 0) neu++;
      else if (o >= H || s.left.has(o)) ai++;
      else if (squadOf(o)) own++;
      else if (grpOfP(o) && grpOfP(o).endsWith('其他真人')) mate++;
      else hum++;
    }
    parts.push(`t=${t} 我方 ${fmt(own)}（${pc(own, inCells)}）/ 同队其他真人 ${fmt(mate)}（${pc(mate, inCells)}）/ 敌方真人 ${fmt(hum)}（${pc(hum, inCells)}）/ 还是内置 AI ${fmt(ai)}（${pc(ai, inCells)}）/ 无主地 ${fmt(neu)}（${pc(neu, inCells)}）`);
    J.aiInOurVor.to[t] = { own, mate, human: hum, ai, neutral: neu };
  }
  L.push('');
  L.push(`D3. 阵型圈内${botTeamed ? '打得了的' : '的'}内置 AI（t=${aiFrom} 脚印过半落在我方天然地盘里）：${inIds.length} 个 / ${fmt(inCells)} 格（其中当拍和我方接壤的 ${inAdj} 个）→ ${parts.join(' ｜ ') || '录像没到'}`);
  if (botTeamed) {
    const mc = inMate.reduce((a, [, e]) => a + e.cells, 0);
    const lastS = snaps.get([...aiTo].reverse().find((t) => snaps.has(t)));
    let still = 0;
    if (lastS) { const ms = new Set(inMate.map(([id]) => id)); for (let i = 0; i < landCells.length; i++) { const a = foot.cellAI[i]; if (a >= 0 && ms.has(a) && lastS.own[i] === a) still++; } }
    L.push(`    阵型圈内和我方同队的 AI（打不了）：${inMate.length} 个 / ${fmt(mc)} 格；到最后一个对照拍还在它自己手里的 ${fmt(still)} 格`);
    J.aiInOurVor.mate = { n: inMate.length, cells: mc, still };
  }
  // 全图：当拍内置 AI 的地合计，落在各组天然地盘里的格数
  const perG = new Map(groups.map((gname) => [gname, 0]));
  let aiAll = 0;
  const perGMate = new Map(groups.map((gname) => [gname, 0]));
  for (let i = 0; i < landCells.length; i++) if (foot.cellAI[i] >= 0) { aiAll++; const st = sites[vor[i]]; const gs = st.group; const e = foot.ai.get(foot.cellAI[i]); if (st.team !== 0 && e && e.team === st.team) perGMate.set(gs, perGMate.get(gs) + 1); else perG.set(gs, perG.get(gs) + 1); }
  L.push('');
  L.push(`D4. t=${aiFrom} 全图内置 AI 的地 ${fmt(aiAll)} 格，落在各组天然地盘里${botTeamed ? '、该组打得了的' : '的'}：` + groups.map((gname) => `${gname} ${fmt(perG.get(gname))}（每人 ${fmt(perG.get(gname) / sites.filter((s) => s.group === gname).length)}）`).join('、'));
  if (botTeamed) L.push('    其中和该落点同队、打不了的 AI 地：' + groups.map((gname) => `${gname} ${fmt(perGMate.get(gname))}`).join('、'));
  J.aiLandInVor = Object.fromEntries(groups.map((gname) => [gname, perG.get(gname)]));
  J.aiLandAll = aiAll;
  if (sFrom) {
    let neutral = 0;
    const perN = new Map(groups.map((gname) => [gname, 0]));
    for (let i = 0; i < landCells.length; i++) if (sFrom.own[i] < 0) { neutral++; const gs = sites[vor[i]].group; perN.set(gs, perN.get(gs) + 1); }
    L.push(`    同拍全图无主地 ${fmt(neutral)} 格，落在各组天然地盘里的：` + groups.map((gname) => `${gname} ${fmt(perN.get(gname))}`).join('、'));
  }
} else {
  L.push(`  录像没有到 t=${aiFrom}`);
}
if (geom) {
  const DIR = ['北', '东北', '东', '东南', '南', '西南', '西', '西北'];
  const dirOf = (dx, dy) => ((Math.round((Math.atan2(dx, -dy) * 180 / Math.PI) / 45) % 8) + 8) % 8;
  const sq = sites.filter((s) => s.squad);
  const others = sites.filter((s) => !s.squad);
  L.push('');
  L.push(`E. 阵型朝向（出生阶段结束时）：我方落点质心 (${geom.cx.toFixed(0)},${geom.cy.toFixed(0)})；地图 ${geom.W}×${geom.Hh}；方位以质心为圆心，北 = y 减小`);
  L.push('   方位 | 60~160 像素环：陆地格 / 水格（陆地占比）| 160~260 像素环：陆地 / 水（陆地占比）| 260 像素内的敌方真人落点（个数，最近的距离）| 同队其他真人落点 | 站在这个方位的我方号（离质心）');
  J.geom = { cx: geom.cx, cy: geom.cy, sectors: [] };
  for (let k = 0; k < 8; k++) {
    const e = geom.sec[k];
    const en = [], mates = [], mine = [];
    for (const o of others) {
      const dx = o.x - geom.cx, dy = o.y - geom.cy, dd = Math.hypot(dx, dy);
      if (dd > 260 || dirOf(dx, dy) !== k) continue;
      if (o.team !== 0 && squadTeams.has(o.team)) mates.push(dd); else en.push(dd);
    }
    for (const o of sq) { const dx = o.x - geom.cx, dy = o.y - geom.cy; if (Math.hypot(dx, dy) >= 20 && dirOf(dx, dy) === k) mine.push(`${o.squad} ${Math.hypot(dx, dy).toFixed(0)}`); }
    const f = (r) => `${fmt(e.land[r])} / ${fmt(e.water[r])}（${pc(e.land[r], e.land[r] + e.water[r] + e.off[r])}${e.off[r] ? `，图外 ${fmt(e.off[r])}` : ''}）`;
    L.push(`  ${DIR[k]}\t${f(0)}\t${f(1)}\t${en.length}${en.length ? `（最近 ${Math.min(...en).toFixed(0)}）` : ''}\t${mates.length}\t${mine.join('、') || '-'}`);
    J.geom.sectors.push({ dir: DIR[k], land0: e.land[0], water0: e.water[0], land1: e.land[1], water1: e.water[1], off0: e.off[0], off1: e.off[1], enemies: en.length, enemyNearest: en.length ? Math.min(...en) : null, mates: mates.length });
  }
  const inner = sq.filter((o) => Math.hypot(o.x - geom.cx, o.y - geom.cy) < 20).map((o) => o.squad);
  if (inner.length) L.push(`  离质心不到 20 像素的我方号：${inner.join('、')}`);
  const near = others.filter((o) => !(o.team !== 0 && squadTeams.has(o.team))).map((o) => {
    let best = null, bd = Infinity;
    for (const m of sq) { const dd = Math.hypot(o.x - m.x, o.y - m.y); if (dd < bd) { bd = dd; best = m.squad; } }
    return { o, dc: Math.hypot(o.x - geom.cx, o.y - geom.cy), k: dirOf(o.x - geom.cx, o.y - geom.cy), best, bd };
  }).sort((a, b) => a.bd - b.bd).slice(0, 12);
  L.push('  离我方最近的 12 个敌方真人落点：' + near.map((n) => `${names[n.o.p].slice(0, 14)}#${n.o.p}[T${n.o.team}] ${DIR[n.k]}，离 ${n.best} ${n.bd.toFixed(0)} 像素`).join('；'));
  J.geom.nearestEnemies = near.map((n) => ({ p: n.o.p, team: n.o.team, dir: DIR[n.k], bot: n.best, dist: n.bd }));
}
fs.writeFileSync(path.join(OUT, 'voronoi.txt'), L.join('\n') + '\n');
fs.writeFileSync(path.join(OUT, 'voronoi.json'), JSON.stringify(J, null, 1) + '\n');
process.stdout.write(L.join('\n') + `\nwrote ${path.join(OUT, 'voronoi.txt')}\n`);
