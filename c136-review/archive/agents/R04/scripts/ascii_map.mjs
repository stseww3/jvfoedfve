#!/usr/bin/env node
// ascii_map.mjs — 真引擎重放到指定拍，打印「谁在哪块陆地上」：
//   1) 每个我方号 / 其他真人的领土按「陆块」（地图上连成一片的陆地）拆开：在每块陆块上有多少格；
//   2) 两两之间的陆上接壤像素数（我方号 ↔ 其他真人；我方号 ↔ 内置 AI 合计）；
//   3) （加 --map）一张粗网格图：每格取占格最多的归属（A~J = 我方号按引擎编号顺序，x = 其他真人，o = 内置 AI，: = 无主陆地，空格 = 水/山）。
// 用法：node scripts/ascii_map.mjs <局号> --at t1,t2,... [--ours id,id,...] [--map] [--cell 24] [--top 4] [--also 号,号] [--heads] [--brief]
//   --heads  对我方号所在的每块陆块（≥2000 格的），列出主体在这块陆块上的真人：我方号 / 其他真人各几个、各自总领土的中位与合计，以及其他真人的名单
//   --brief  不打印逐号的接壤明细，只留陆块归属（配合 --heads 用）
//   --also 304,154  另外打印这些玩家（通常是内置 AI）在各陆块上的格数和外接框
// 口径：陆块 = 地图静态地形里 4 邻接连通的陆地像素（山、水不算）；接壤 = 我方像素的 4 邻格属于对方。
// 重活，请用：HEAVY_QUEUE=90 timeout 118 bash ../../tools/run-heavy.sh node scripts/ascii_map.mjs ...
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { startEngine, Mirror } from './shadow.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const args = process.argv.slice(2);
const mid = args[0];
const opt = (k, d) => { const i = args.indexOf(k); return i >= 0 ? args[i + 1] : d; };
const at = (opt('--at', '') || '').split(',').filter(Boolean).map(Number).sort((a, b) => a - b);
const cell = +opt('--cell', 24), top = +opt('--top', 4);
const wantMap = args.includes('--map');
const wantHeads = args.includes('--heads'), brief = args.includes('--brief');
const also = (opt('--also', '') || '').split(',').filter(Boolean).map(Number);
if (!mid || !at.length) { console.error('用法：node scripts/ascii_map.mjs <局号> --at t1,t2,... [--ours id,...] [--map] [--cell 24]'); process.exit(2); }

const meta = JSON.parse(fs.readFileSync(path.join(HERE, '..', 'tmp', 'truth', mid, 'meta.json'), 'utf8'));
const ours = (opt('--ours', '') ? opt('--ours').split(',').map(Number) : Object.keys(meta.ours).map(Number)).sort((a, b) => a - b);
const { info, api } = startEngine(mid);
const names = api.names();
const nm = (p) => (p >= info.ku ? 'AI#' + p : (names[p] || '').replace('[APEX] ', '') + '#' + p);
let st = api.advance(1);
while (st[1] === 1 && st[2] !== 2) st = api.advance(1);
const M = new Mirror(info, api);
const g = M.g, W = g.W, H = g.H, N = g.N, type = M.map.type;
const T_LAND = 1;
// 静态陆块
const mass = new Int32Array(N).fill(-1);
const massSize = [];
{
  const q = new Int32Array(N);
  for (let s = 0; s < N; s++) {
    if (type[s] !== T_LAND || mass[s] >= 0) continue;
    const id = massSize.length; let h = 0, t = 0, n = 0;
    q[t++] = s; mass[s] = id;
    while (h < t) {
      const c = q[h++]; n++;
      const x = c % W;
      if (x > 0 && type[c - 1] === T_LAND && mass[c - 1] < 0) { mass[c - 1] = id; q[t++] = c - 1; }
      if (x < W - 1 && type[c + 1] === T_LAND && mass[c + 1] < 0) { mass[c + 1] = id; q[t++] = c + 1; }
      if (c >= W && type[c - W] === T_LAND && mass[c - W] < 0) { mass[c - W] = id; q[t++] = c - W; }
      if (c + W < N && type[c + W] === T_LAND && mass[c + W] < 0) { mass[c + W] = id; q[t++] = c + W; }
    }
    massSize.push(n);
  }
}
const order = massSize.map((n, i) => [n, i]).sort((a, b) => b[0] - a[0]);
const rank = new Map(order.map(([n, i], k) => [i, k + 1]));
console.log(`# ${mid} 地图 ${W}x${H}，陆地 ${info.ke} 格，陆块 ${massSize.length} 个；最大的几块（编号按大小排）：` + order.slice(0, 8).map(([n, i], k) => `L${k + 1}=${n}`).join(' '));

const raw = M.ownRaw;
for (const T of at) {
  while (st[2] !== 2 && st[0] < T) st = api.advance(Math.min(200, T - st[0]));
  M.light(); M.pixels();
  const t = st[0];
  const humans = [];
  for (let p = 0; p < info.ku; p++) if (g.alive[p] && g.terr[p] > 0) humans.push(p);
  const per = new Map(); // p -> Map(mass -> px)
  const touch = new Map(); // 'p>q' -> 接壤像素数（p 的像素挨着 q）
  const aiOn = new Map(); // mass -> AI 像素
  const neutOn = new Map();
  for (let i = 0; i < N; i++) {
    if (type[i] !== T_LAND) continue;
    const o = raw[i], m = mass[i];
    if (o === 65535) { neutOn.set(m, (neutOn.get(m) || 0) + 1); continue; }
    if (o >= info.ku) { aiOn.set(m, (aiOn.get(m) || 0) + 1); continue; }
    let mp = per.get(o); if (!mp) per.set(o, (mp = new Map()));
    mp.set(m, (mp.get(m) || 0) + 1);
    const x = i % W;
    const nb = [x > 0 ? i - 1 : -1, x < W - 1 ? i + 1 : -1, i - W, i + W];
    let seen = null;
    for (const c of nb) {
      if (c < 0 || c >= N) continue;
      const ro = raw[c];
      if (ro === 65535 || ro === o) continue;
      const key = ro >= info.ku ? 'AI' : ro;
      if (seen && seen.includes(key)) continue;
      (seen ??= []).push(key);
      const k2 = o + '>' + key;
      touch.set(k2, (touch.get(k2) || 0) + 1);
    }
  }
  console.log(`\n== 拍 ${t} ==`);
  for (const p of humans) {
    if (brief) break;
    const mp = per.get(p) || new Map();
    const parts = [...mp.entries()].sort((a, b) => b[1] - a[1]);
    const mine = ours.includes(p);
    if (!mine && !ours.some((o) => touch.has(o + '>' + p) || touch.has(p + '>' + o)) && humans.length > 12) continue;
    const tl = [];
    for (const q of humans) if (q !== p && touch.get(p + '>' + q)) tl.push(`${nm(q)} ${touch.get(p + '>' + q)}`);
    if (touch.get(p + '>AI')) tl.push(`内置AI ${touch.get(p + '>AI')}`);
    console.log(`  ${mine ? '我方' : '其他'} ${nm(p)} 领土 ${g.terr[p]} 余额 ${g.bal[p]}：` +
      parts.slice(0, top).map(([m, n]) => `L${rank.get(m)}(${massSize[m]}格) 上 ${n}`).join('，') + (parts.length > top ? `，另 ${parts.length - top} 块共 ${parts.slice(top).reduce((s, x) => s + x[1], 0)}` : '') +
      `；接壤像素：${tl.length ? tl.join('，') : '无'}`);
  }
  for (const p of also) {
    if (!g.alive[p] || !g.terr[p]) { console.log(`  另看 ${nm(p)}：已不在场`); continue; }
    const mp = new Map();
    let x0 = W, y0 = H, x1 = 0, y1 = 0;
    for (let i = 0; i < N; i++) if (raw[i] === p) { mp.set(mass[i], (mp.get(mass[i]) || 0) + 1); const x = i % W, y = (i / W) | 0; if (x < x0) x0 = x; if (x > x1) x1 = x; if (y < y0) y0 = y; if (y > y1) y1 = y; }
    const parts = [...mp.entries()].sort((a, b) => b[1] - a[1]);
    console.log(`  另看 ${nm(p)} 领土 ${g.terr[p]} 余额 ${g.bal[p]}：` + parts.slice(0, top).map(([m, n]) => `L${rank.get(m)}(${massSize[m]}格) 上 ${n}`).join('，') + `；外接框 x ${x0}~${x1} y ${y0}~${y1}`);
  }
  const used = new Set();
  for (const p of humans) if (ours.includes(p)) for (const m of (per.get(p) || new Map()).keys()) used.add(m);
  const rows = [...new Set([...used, ...order.slice(0, 6).map((x) => x[1])])].sort((a, b) => rank.get(a) - rank.get(b)).slice(0, 14);
  console.log('  陆块上的归属（我方号 / 其他真人 / 内置AI / 无主）：' + rows.map((m) => {
    let a = 0, b = 0;
    for (const p of humans) { const n = (per.get(p) || new Map()).get(m) || 0; if (ours.includes(p)) a += n; else b += n; }
    return `L${rank.get(m)} ${a}/${b}/${aiOn.get(m) || 0}/${neutOn.get(m) || 0}`;
  }).join('；'));
  if (wantHeads) {
    const med = (a) => { if (!a.length) return 0; const b = [...a].sort((x, y) => x - y); return b[(b.length - 1) >> 1]; };
    for (const m of rows) {
      if (massSize[m] < 2000) continue;
      const a = [], b = [];
      for (const p of humans) {
        const mp = per.get(p); if (!mp) continue;
        const parts = [...mp.entries()].sort((x, y) => y[1] - x[1]);
        if (parts[0][0] !== m) continue;      // 主体不在这块陆块上
        (ours.includes(p) ? a : b).push(p);
      }
      const sum = (l) => l.reduce((s2, p) => s2 + g.terr[p], 0), sb = (l) => l.reduce((s2, p) => s2 + g.bal[p], 0);
      console.log(`  主体在 L${rank.get(m)} 上的真人：我方号 ${a.length} 个，领土合计 ${sum(a)}、中位 ${med(a.map((p) => g.terr[p]))}、余额合计 ${sb(a)}；其他真人 ${b.length} 个，领土合计 ${sum(b)}、中位 ${med(b.map((p) => g.terr[p]))}、余额合计 ${sb(b)}`);
      console.log('    其他真人：' + b.sort((x, y) => g.terr[y] - g.terr[x]).map((p) => `${nm(p)}(队${g.teams ? g.teams[p] : '?'}) ${g.terr[p]}/${g.bal[p]}`).join('；'));
    }
  }
  if (wantMap) {
    const letter = new Map(ours.map((p, k) => [p, String.fromCharCode(65 + k)]));
    console.log('  图例：' + ours.map((p) => `${letter.get(p)}=${nm(p)}`).join(' ') + ' x=其他真人 o=内置AI :=无主陆地');
    for (let cy = 0; cy < H; cy += cell) {
      let line = '  ';
      for (let cx = 0; cx < W; cx += cell) {
        const cnt = new Map(); let land = 0;
        for (let y = cy; y < Math.min(H, cy + cell); y += 2) for (let x = cx; x < Math.min(W, cx + cell); x += 2) {
          const i = y * W + x;
          if (type[i] !== T_LAND) continue;
          land++;
          const o = raw[i];
          const k = o === 65535 ? ':' : o >= info.ku ? 'o' : letter.get(o) || 'x';
          cnt.set(k, (cnt.get(k) || 0) + 1);
        }
        if (land * 4 < (cell / 2) * (cell / 2)) { line += land ? '.' : ' '; continue; }
        let best = ' ', bn = 0;
        for (const [k, n] of cnt) if (n > bn) { bn = n; best = k; }
        line += best;
      }
      console.log(line);
    }
  }
}
