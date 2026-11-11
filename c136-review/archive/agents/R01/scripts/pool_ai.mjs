#!/usr/bin/env node
// pool_ai.mjs — B 组（v27-team-c110.js）“名字撞进编队名单”的账。
// c110 的 isOurSquadBot（L3973–3976）只看名字是否在 SQUAD_POOL_SET 里；analyze L440 把“受保护的兄弟”排除在邻居表之外，
// 所以名字撞池的内置 AI 和路人对本队的号是看不见的：不算邻居、不会被选成目标。本脚本量这件事在一局里的大小：
//   1) 哪些非本队席位的名字在池子里（内置 AI / 路人真人）；
//   2) 每 90 拍：这些席位的 领土/余额；和本队每个“还在场”的号接壤的边界格数（本队号的边界格里有几格贴着它）；
//   3) 这些席位名下的地最后归了谁（每个采样窗口里它丢的格按新主人累加）、它们从本队各号手里拿了几格；
//   4) 本队各号在 [t0,t1]（默认 600–1800）里“身边的 AI 地”有多少是看不见的：接壤的 AI 领土合计里撞池 AI 占几成。
// 用法（套 run-heavy.sh）：node scripts/pool_ai.mjs <局号> [--replay 同局另一个包] [--log id] [--t0 600 --t1 1800] [--every 90] [--seats a,b,c] [--tag x]
//   --seats：再加几个指定席位一起记“地归了谁”；--tag：输出文件名加后缀（不覆盖全量那一份）
// 依赖：out/<局号>/names512.json（先跑 engine_names.cjs）。输出：标准输出 + out/<局号>/pool_ai.csv、pool_ai_contact.csv、pool_ai_flow.csv
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { openMatch, readLogSnaps, P_INNER } from './resim_lib.mjs';

const args = process.argv.slice(2);
const mid = args[0];
const opt = (k, d) => (args.includes(`--${k}`) ? args[args.indexOf(`--${k}`) + 1] : d);
const rmid = opt('replay', mid);
const every = +opt('every', 90), T0 = +opt('t0', 600), T1 = +opt('t1', 1800);
const HERE = path.dirname(fileURLToPath(import.meta.url));
const OUT = path.resolve(HERE, '..', 'out', mid);
const src = fs.readFileSync('/agent/repos/c136-data/src/strategy/v27-team-c110.js', 'utf8');
const poolLine = src.slice(0, src.indexOf('\n'));
const pool = new Set(JSON.parse(poolLine.slice(poolLine.indexOf('['), poolLine.lastIndexOf(']') + 1)));
const inPool = (raw) => { const s = String(raw ?? '').trim(); return pool.has(s.toLowerCase()) || s.toUpperCase().includes('[NPL]') || s.toUpperCase().includes('[NOPE]'); };
const names = JSON.parse(fs.readFileSync(path.join(OUT, 'names512.json'), 'utf8')).names;

const m = openMatch(mid, { replay: rmid });
const { g, H } = m;
const { me } = readLogSnaps(opt('log', mid));
const sqIds = new Set(Object.values(me));
const label = Object.fromEntries(Object.entries(me).map(([b, p]) => [p, b]));
const nm = (p) => label[p] ?? (p < H ? `${names[p]}#${p}/T${g.teams[p]}` : `AI#${p}(${names[p]})`);
const hit = [];
for (let p = 0; p < names.length; p++) if (!sqIds.has(p) && inPool(names[p])) hit.push(p);
const nPool = hit.length;
// --seats a,b,c：再加几个指定席位一起记“地归了谁”（不算撞池，只借用同一套流向账；例如夹在两个本队号中间的内置 AI）
const extra = opt('seats', '') ? opt('seats', '').split(',').map(Number).filter((p) => !hit.includes(p)) : [];
for (const p of extra) hit.push(p);
const hitSet = new Set(hit);
const poolSet = new Set(hit.slice(0, nPool));
console.log(`# ${mid}（录像 ${rmid}）池子 ${pool.size} 个名字；本队 ${sqIds.size} 个席位；名字撞池的其他席位 ${nPool} 个：真人 ${hit.slice(0, nPool).filter((p) => p < H).map(nm).join('、') || '无'}；内置 AI ${hit.slice(0, nPool).filter((p) => p >= H).map((p) => `#${p} ${names[p]}`).join('、')}` + (extra.length ? `；另外指定跟踪 ${extra.map(nm).join('、')}` : ''));
// AI 名字和池子的重合度
{
  const aiNames = names.slice(H);
  const distinct = new Set(aiNames.map((s) => String(s).trim().toLowerCase()));
  let both = 0; for (const s of distinct) if (pool.has(s)) both++;
  console.log(`# 内置 AI ${aiNames.length} 个（不同名字 ${distinct.size} 个），其中名字在池子里的 ${hit.slice(0, nPool).filter((p) => p >= H).length} 个席位 / ${both} 个不同名字`);
}

const N = g.N, W = g.W, d4 = [1, -1, W, -W];
const rows = ['t,p,name,alive,terr,bal'];
const contact = ['t,bot,p,poolSeat,borderCells,botTerr,poolTerr,poolBal,aiNbTerrAll,aiNbTerrPool'];
const flow = new Map(); // key from|to -> cells ; from/to are seats
const prev = new Int16Array(N).fill(-1); // owner at previous sample for cells owned by pool seats / squad seats
const snapOwner = () => { for (let c = 0; c < N; c++) prev[c] = g.px[c] >= P_INNER ? g.own[c] : -1; };
const winSum = {}; // bot -> {allAi, poolAi, samples}
const sample = () => {
  const t = g.t;
  for (const p of hit) rows.push([t, p, JSON.stringify(names[p]), g.alive[p], g.terr[p], g.bal[p]].join(','));
  // 接壤：本队每个还在场（没离场）的号的边界格，贴着谁
  for (const p of sqIds) {
    if (!g.alive[p] || g.state[p] === 2) continue;
    const cnt = new Map();
    for (const c of g.border[p]) {
      const seen = new Set();
      for (const d of d4) {
        const n = c + d;
        if (n < 0 || n >= N || g.px[n] < P_INNER) continue;
        const o = g.own[n];
        if (o === p || seen.has(o)) continue;
        seen.add(o);
        cnt.set(o, (cnt.get(o) || 0) + 1);
      }
    }
    let allAi = 0, poolAi = 0;
    for (const [o] of cnt) if (o >= H && g.alive[o]) { allAi += g.terr[o]; if (poolSet.has(o)) poolAi += g.terr[o]; }
    for (const [o, n] of cnt) if (poolSet.has(o)) contact.push([t, JSON.stringify(label[p]), p, o, n, g.terr[p], g.terr[o], g.bal[o], allAi, poolAi].join(','));
    if (t >= T0 && t <= T1) { const w = (winSum[p] ??= { allAi: 0, poolAi: 0, n: 0, nPool: 0 }); w.allAi += allAi; w.poolAi += poolAi; w.n++; if (poolAi > 0) w.nPool++; }
  }
};
const diff = () => {
  for (let c = 0; c < N; c++) {
    const a = prev[c];
    if (a < 0) continue;
    const b = g.px[c] >= P_INNER ? g.own[c] : -1;
    if (a === b) continue;
    if (hitSet.has(a) || (hitSet.has(b) && sqIds.has(a))) { const k = a + '|' + b; flow.set(k, (flow.get(k) || 0) + 1); }
  }
};
snapOwner();
let next = every;
while (m.tick()) {
  if (g.t >= next) { diff(); sample(); snapOwner(); next += every; }
}
diff();
const sfx = opt('tag', '') ? '_' + opt('tag', '') : '';
fs.writeFileSync(path.join(OUT, `pool_ai${sfx}.csv`), rows.join('\n') + '\n');
fs.writeFileSync(path.join(OUT, `pool_ai_contact${sfx}.csv`), contact.join('\n') + '\n');
fs.writeFileSync(path.join(OUT, `pool_ai_flow${sfx}.csv`), 'from,to,cells\n' + [...flow].map(([k, v]) => k.replace('|', ',') + ',' + v).join('\n') + '\n');

console.log('== 撞池席位名下的地最后归了谁（按 90 拍采样窗口累加；-1 = 变回无主）、它从本队的号手里拿了几格');
for (const p of hit) {
  const lost = [], took = [];
  for (const [k, v] of flow) { const [a, b] = k.split('|').map(Number); if (a === p) lost.push([b, v]); if (b === p && sqIds.has(a)) took.push([a, v]); }
  lost.sort((x, y) => y[1] - x[1]); took.sort((x, y) => y[1] - x[1]);
  const tot = lost.reduce((s, x) => s + x[1], 0);
  const sqGot = lost.filter((x) => sqIds.has(x[0])).reduce((s, x) => s + x[1], 0);
  console.log(`   ${nm(p)}：共丢 ${tot} 格，其中本队的号拿到 ${sqGot} 格；去向前 4：${lost.slice(0, 4).map(([o, v]) => `${o < 0 ? '无主' : nm(o)} ${v}`).join('，') || '-'}；从本队拿走：${took.map(([o, v]) => `${nm(o)} ${v}`).join('，') || '0'}`);
}
console.log(`== 本队各号在 [${T0},${T1}] 的采样点上：接壤的内置 AI 领土合计（平均）、其中名字撞池的 AI 占几成、有几个采样点贴着撞池 AI`);
for (const [p, w] of Object.entries(winSum)) console.log(`   ${label[p]}：采样 ${w.n} 个，接壤 AI 领土平均 ${Math.round(w.allAi / w.n)} 格，其中撞池 AI ${Math.round(w.poolAi / w.n)} 格（${w.allAi ? (100 * w.poolAi / w.allAi).toFixed(1) : '0'}%），贴着撞池 AI 的采样点 ${w.nPool} 个`);
console.log(`# 已写 out/${mid}/pool_ai.csv、pool_ai_contact.csv、pool_ai_flow.csv`);
