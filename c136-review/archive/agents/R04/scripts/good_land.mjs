#!/usr/bin/env node
// good_land.mjs — 「好地实际抢到多少」的硬账（hub 0007 第 3 节）。真引擎重放到 1800 拍，一次算三件事：
//   1) 天然地盘（Voronoi）：按各真人的实际出生点，把全图陆地格分给「离它最近的真人」。两种算法都给：
//        欧氏：直线距离最近（不管中间是不是海）；
//        陆路：只沿陆地格走（4 邻接）步数最近；从任何真人都走不到的陆地（要坐船的岛）不分给任何人。
//      输出我方名下的天然陆地占全图的比例（对比我方人头占到场真人的比例），单号中位格数对其他真人的中位格数。
//   2) 实际拿到率：指定拍（默认 630、1500、1800）各真人的实际领土 ÷ 它名下的天然地盘；按 我方 / 同队其他真人 / 各敌队 汇总，
//      另给「我方天然地盘（欧氏）里的格子此刻在谁手里」。
//   3) 身边内置 AI 的地的去向：t0（默认 630）拍与我方号陆上接壤、或过半的格子落在我方天然地盘（欧氏）里的内置 AI，
//      它们 t0 拍占着的那批格子，到 1500 / 1800 拍在谁手里（我方 / 同队其他真人 / 敌方真人 / 原来那个 AI / 别的 AI / 无主）。
// 用法：node scripts/good_land.mjs <局号> [--ours id,id,…] [--t0 630] [--at 630,1500,1800]
// 结果另写 tmp/land/<局号>/good_land.json（跨局汇总用）。
// 重活，请用：HEAVY_QUEUE=90 timeout 118 bash ../../tools/run-heavy.sh node scripts/good_land.mjs <局号>
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { startEngine, Mirror } from './shadow.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const args = process.argv.slice(2);
const mid = args[0];
const opt = (k, d) => { const i = args.indexOf(k); return i >= 0 ? args[i + 1] : d; };
if (!mid) { console.error('用法：node scripts/good_land.mjs <局号> [--ours id,…] [--t0 630] [--at 630,1500,1800]'); process.exit(2); }
const t0 = +opt('--t0', 630);
const at = [...new Set([t0, ...(opt('--at', '630,1500,1800')).split(',').map(Number)])].sort((a, b) => a - b);
const meta = JSON.parse(fs.readFileSync(path.join(HERE, '..', 'tmp', 'truth', mid, 'meta.json'), 'utf8'));
const ours = (opt('--ours', '') ? opt('--ours').split(',').map(Number) : Object.keys(meta.ours).map(Number)).sort((a, b) => a - b);
const isOur = new Uint8Array(512); for (const p of ours) isOur[p] = 1;

const { info, api } = startEngine(mid);
let st = api.advance(1);
while (st[1] === 1 && st[2] !== 2) st = api.advance(1);
const M = new Mirror(info, api);
const g = M.g, W = g.W, H = g.H, N = g.N, type = M.map.type, ku = info.ku;
const T_LAND = 1;
const names = api.names();
const nm = (p) => (p >= ku ? 'AI#' + p : (names[p] || '').replace('[APEX] ', '') + '#' + p);
const fmt = (n) => Math.round(n).toLocaleString('en-US');
const pct = (a, b) => (b > 0 ? (100 * a / b).toFixed(1) + '%' : '—');
const med = (v) => { if (!v.length) return 0; const s = [...v].sort((a, b) => a - b); return s[s.length >> 1]; };

// 到场真人与出生点
const humans = meta.players.filter((x) => x.p < ku && x.box && x.box[0] <= x.box[2]);
const hp = humans.map((x) => x.p), hx = humans.map((x) => x.spawn[0]), hy = humans.map((x) => x.spawn[1]);
const team = (p) => g.teams[p] | 0;
const ourTeams = new Set(ours.map(team));
const counts = new Map(); for (const p of ours) counts.set(team(p), (counts.get(team(p)) || 0) + 1);
const mainTeam = [...counts.entries()].sort((a, b) => b[1] - a[1])[0][0];
const teamGame = g.teamGame && mainTeam > 0;
const cls = (p) => (isOur[p] ? '我方' : p >= ku ? (teamGame && team(p) === mainTeam ? '同队AI' : '内置AI') : (teamGame && team(p) === mainTeam ? '同队其他真人' : '敌方真人'));

// 1) 天然地盘
const vorE = new Int16Array(N).fill(-1), vorL = new Int16Array(N).fill(-1);
let land = 0;
for (let i = 0; i < N; i++) {
  if (type[i] !== T_LAND) continue;
  land++;
  const x = i % W, y = (i / W) | 0;
  let best = -1, bd = Infinity;
  for (let k = 0; k < hp.length; k++) { const dx = x - hx[k], dy = y - hy[k], d = dx * dx + dy * dy; if (d < bd) { bd = d; best = k; } }
  vorE[i] = best;
}
{
  // 多源广度优先：每个真人从离出生点最近的陆地格出发，同步一圈一圈往外走
  const q = new Int32Array(N); let h = 0, t = 0;
  for (let k = 0; k < hp.length; k++) {
    let s = hy[k] * W + hx[k];
    if (type[s] !== T_LAND) {
      let bd = Infinity, bs = -1;
      for (let dy = -12; dy <= 12; dy++) for (let dx = -12; dx <= 12; dx++) {
        const x = hx[k] + dx, y = hy[k] + dy; if (x < 0 || y < 0 || x >= W || y >= H) continue;
        const c = y * W + x; if (type[c] !== T_LAND) continue;
        const d = dx * dx + dy * dy; if (d < bd) { bd = d; bs = c; }
      }
      s = bs;
    }
    if (s >= 0 && vorL[s] < 0) { vorL[s] = k; q[t++] = s; }
  }
  while (h < t) {
    const c = q[h++], k = vorL[c], x = c % W;
    if (x > 0 && type[c - 1] === T_LAND && vorL[c - 1] < 0) { vorL[c - 1] = k; q[t++] = c - 1; }
    if (x < W - 1 && type[c + 1] === T_LAND && vorL[c + 1] < 0) { vorL[c + 1] = k; q[t++] = c + 1; }
    if (c >= W && type[c - W] === T_LAND && vorL[c - W] < 0) { vorL[c - W] = k; q[t++] = c - W; }
    if (c + W < N && type[c + W] === T_LAND && vorL[c + W] < 0) { vorL[c + W] = k; q[t++] = c + W; }
  }
}
const nE = new Float64Array(hp.length), nL = new Float64Array(hp.length);
let unreach = 0;
for (let i = 0; i < N; i++) { if (type[i] !== T_LAND) continue; nE[vorE[i]]++; if (vorL[i] >= 0) nL[vorL[i]]++; else unreach++; }
const idx = new Map(hp.map((p, k) => [p, k]));
const oursK = ours.filter((p) => idx.has(p)).map((p) => idx.get(p));
const othersK = hp.map((p, k) => k).filter((k) => !isOur[hp[k]]);
const sum = (ks, a) => ks.reduce((s, k) => s + a[k], 0);
const out = { match: mid, land, humansPresent: hp.length, ours: ours.length, t0, at, voronoi: {}, capture: {}, aiFate: {} };
console.log(`# ${mid} 好地账：陆地 ${fmt(land)} 格，到场真人 ${hp.length} 个（我方 ${oursK.length} 个 = ${pct(oursK.length, hp.length)}），人均 ${fmt(land / hp.length)} 格`);
console.log('## 1 天然地盘（按出生点把陆地分给最近的真人）');
for (const [lab, a, key] of [['欧氏', nE, 'euclid'], ['陆路', nL, 'landpath']]) {
  const so = sum(oursK, a), mo = med(oursK.map((k) => a[k])), mx = med(othersK.map((k) => a[k]));
  console.log(`  ${lab}：我方名下 ${fmt(so)} 格 = 全图陆地的 ${pct(so, land)}（人头占 ${pct(oursK.length, hp.length)}）；单号中位 ${fmt(mo)} 格，其他真人中位 ${fmt(mx)} 格（${(mo / Math.max(1, mx)).toFixed(2)} 倍）` +
    (key === 'landpath' ? `；从任何真人都走不到的陆地 ${fmt(unreach)} 格` : ''));
  console.log('    各号：' + oursK.map((k) => `${nm(hp[k])} ${fmt(a[k])}`).join('，'));
  out.voronoi[key] = { ourPx: so, ourSharePct: +(100 * so / land).toFixed(2), headSharePct: +(100 * oursK.length / hp.length).toFixed(2), ourMedian: mo, otherMedian: mx, perBot: Object.fromEntries(oursK.map((k) => [hp[k], a[k]])) };
}
out.voronoi.unreachable = unreach;

// 2)、3) 逐拍
const raw = new Uint16Array(N);
let aiSet = null, tag = null, tagN = 0, aiList = [];
for (const T of at) {
  while (st[2] !== 2 && st[0] < T) st = api.advance(Math.min(200, T - st[0]));
  M.light(); api.owners(raw);
  const t = st[0];
  console.log(`\n## 拍 ${t}`);
  // 实际领土
  const terr = (p) => g.terr[p];
  const grp = new Map(); // 组名 -> {act, e, l, n, ratiosE:[]}
  const add = (name, k) => {
    let o = grp.get(name); if (!o) grp.set(name, (o = { act: 0, e: 0, l: 0, n: 0, alive: 0, rE: [], rL: [] }));
    const p = hp[k]; o.act += terr(p); o.e += nE[k]; o.l += nL[k]; o.n++; if (g.alive[p] && terr(p) > 0) o.alive++;
    o.rE.push(terr(p) / Math.max(1, nE[k])); o.rL.push(terr(p) / Math.max(1, nL[k]));
  };
  for (let k = 0; k < hp.length; k++) {
    const p = hp[k];
    if (isOur[p]) add('我方', k);
    else if (teamGame && team(p) === mainTeam) add('同队其他真人', k);
    else add(teamGame ? `敌队${team(p)}` : '其他真人', k);
    if (!isOur[p]) add('全部其他真人', k);
  }
  console.log('  实际领土 ÷ 天然地盘（组合计；括号里是组内单号比值的中位）：');
  const cap = {};
  for (const [name, o] of [...grp.entries()].sort((a, b) => (a[0] === '我方' ? -1 : b[0] === '我方' ? 1 : a[0] < b[0] ? -1 : 1))) {
    console.log(`    ${name}（${o.n} 个，在场 ${o.alive}）：实际 ${fmt(o.act)} 格；÷ 欧氏 ${fmt(o.e)} = ${(o.act / Math.max(1, o.e)).toFixed(2)}（中位 ${med(o.rE).toFixed(2)}）；÷ 陆路 ${fmt(o.l)} = ${(o.act / Math.max(1, o.l)).toFixed(2)}（中位 ${med(o.rL).toFixed(2)}）`);
    cap[name] = { n: o.n, alive: o.alive, actual: o.act, euclid: o.e, landpath: o.l, ratioE: +(o.act / Math.max(1, o.e)).toFixed(3), ratioL: +(o.act / Math.max(1, o.l)).toFixed(3), medE: +med(o.rE).toFixed(3), medL: +med(o.rL).toFixed(3) };
  }
  console.log('    我方各号 实际 / 欧氏 / 陆路：' + oursK.map((k) => `${nm(hp[k])} ${fmt(terr(hp[k]))} / ${(terr(hp[k]) / Math.max(1, nE[k])).toFixed(2)} / ${(terr(hp[k]) / Math.max(1, nL[k])).toFixed(2)}`).join('，'));
  // 我方天然地盘（欧氏）里的格子在谁手里
  const inCell = new Map(); let cellN = 0; const takers = new Map();
  for (let i = 0; i < N; i++) {
    if (type[i] !== T_LAND) continue;
    const k = vorE[i]; if (k < 0 || !isOur[hp[k]]) continue;
    cellN++;
    const o = raw[i];
    const c = o === 65535 ? '无主' : cls(o);
    inCell.set(c, (inCell.get(c) || 0) + 1);
    if (o !== 65535 && o < ku && !isOur[o]) takers.set(o, (takers.get(o) || 0) + 1);
  }
  const order = ['我方', '同队其他真人', '敌方真人', '同队AI', '内置AI', '无主'];
  console.log(`  我方天然地盘（欧氏，${fmt(cellN)} 格）此刻的归属：` + order.filter((c) => inCell.get(c)).map((c) => `${c} ${fmt(inCell.get(c))}（${pct(inCell.get(c), cellN)}）`).join('，') +
    (takers.size ? '；其中真人拿得最多的：' + [...takers.entries()].sort((a, b) => b[1] - a[1]).slice(0, 4).map(([p, n]) => `${nm(p)}（${cls(p)}）${fmt(n)}`).join('，') : ''));
  // 我方的地有多少在自己的天然地盘之外
  let outside = 0, ourAll = 0;
  for (let i = 0; i < N; i++) { const o = raw[i]; if (o === 65535 || !isOur[o]) continue; ourAll++; const k = vorE[i]; if (k < 0 || !isOur[hp[k]]) outside++; }
  console.log(`  我方此刻的 ${fmt(ourAll)} 格里，在我方天然地盘之外的 ${fmt(outside)} 格（${pct(outside, ourAll)}）`);
  out.capture[t] = { groups: cap, ourCell: { px: cellN, owners: Object.fromEntries(inCell) }, ourOutside: outside, ourAll };

  if (T === t0) {
    // 身边的内置 AI：与我方号 4 邻接接壤，或过半格子在我方天然地盘里
    const adj = new Set(); const inside = new Map(); const size = new Map();
    for (let i = 0; i < N; i++) {
      const o = raw[i]; if (o === 65535) continue;
      if (o >= ku) {
        size.set(o, (size.get(o) || 0) + 1);
        const k = vorE[i]; if (k >= 0 && isOur[hp[k]]) inside.set(o, (inside.get(o) || 0) + 1);
        continue;
      }
      if (!isOur[o]) continue;
      const x = i % W;
      for (const c of [x > 0 ? i - 1 : -1, x < W - 1 ? i + 1 : -1, i - W, i + W]) {
        if (c < 0 || c >= N) continue;
        const ro = raw[c]; if (ro !== 65535 && ro >= ku) adj.add(ro);
      }
    }
    aiSet = new Set(adj);
    for (const [a, n] of inside) if (2 * n > size.get(a)) aiSet.add(a);
    if (teamGame) for (const a of [...aiSet]) if (team(a) === mainTeam) aiSet.delete(a); // 同队的内置 AI 打不了，不算
    tag = new Uint16Array(N).fill(65535);
    for (let i = 0; i < N; i++) { const o = raw[i]; if (o !== 65535 && aiSet.has(o)) { tag[i] = o; tagN++; } }
    aiList = [...aiSet].map((a) => [a, size.get(a) || 0]).sort((x, y) => y[1] - x[1]);
    const adjPx = [...adj].filter((a) => aiSet.has(a)).reduce((s, a) => s + (size.get(a) || 0), 0);
    let allAi = 0; for (const [a, n] of size) if (!(teamGame && team(a) === mainTeam)) allAi += n;
    console.log(`  身边的内置 AI（接壤，或过半格子在我方天然地盘里）：${aiSet.size} 个、共 ${fmt(tagN)} 格（其中与我方接壤的 ${[...adj].filter((a) => aiSet.has(a)).length} 个 ${fmt(adjPx)} 格）；全图内置 AI 此刻共 ${fmt(allAi)} 格；最大的几个：` +
      aiList.slice(0, 6).map(([a, n]) => `AI#${a} ${fmt(n)}`).join('，'));
    out.aiFate.t0 = { n: aiSet.size, px: tagN, adjacentN: [...adj].filter((a) => aiSet.has(a)).length, adjacentPx: adjPx, allAiPx: allAi };
  } else if (tag && T > t0) {
    const by = new Map(); const who = new Map(); const byBot = new Map();
    for (let i = 0; i < N; i++) {
      const a = tag[i]; if (a === 65535) continue;
      const o = raw[i];
      const c = o === 65535 ? '无主' : o === a ? '原来那个AI' : o >= ku ? (teamGame && team(o) === mainTeam ? '同队AI' : '别的AI') : cls(o);
      by.set(c, (by.get(c) || 0) + 1);
      if (o !== 65535 && o < ku) { if (isOur[o]) byBot.set(o, (byBot.get(o) || 0) + 1); else who.set(o, (who.get(o) || 0) + 1); }
    }
    const ord = ['我方', '同队其他真人', '敌方真人', '原来那个AI', '别的AI', '同队AI', '无主'];
    console.log(`  ${t0} 拍身边内置 AI 占着的 ${fmt(tagN)} 格，此刻的归属：` + ord.filter((c) => by.get(c)).map((c) => `${c} ${fmt(by.get(c))}（${pct(by.get(c), tagN)}）`).join('，'));
    console.log('    我方各号拿到：' + (ours.map((p) => `${nm(p)} ${fmt(byBot.get(p) || 0)}`).join('，')) + '；别的真人拿得最多的：' +
      ([...who.entries()].sort((a, b) => b[1] - a[1]).slice(0, 5).map(([p, n]) => `${nm(p)}（${cls(p)}）${fmt(n)}`).join('，') || '无'));
    out.aiFate[t] = { owners: Object.fromEntries(by), perBot: Object.fromEntries(ours.map((p) => [p, byBot.get(p) || 0])), topOthers: [...who.entries()].sort((a, b) => b[1] - a[1]).slice(0, 5).map(([p, n]) => ({ p, name: names[p], cls: cls(p), px: n })) };
  }
}
const dir = path.join(HERE, '..', 'tmp', 'land', mid);
fs.mkdirSync(dir, { recursive: true });
fs.writeFileSync(path.join(dir, 'good_land.json'), JSON.stringify(out));
