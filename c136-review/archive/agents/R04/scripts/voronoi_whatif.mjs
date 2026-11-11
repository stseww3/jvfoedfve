#!/usr/bin/env node
// voronoi_whatif.mjs — 天然地盘的「换个出生点」对照：把我方某几个号的出生点换成别的坐标，重新按「离谁最近归谁」分全图陆地，
// 和实际出生点的分法并排给出（欧氏 + 陆路两种算法，定义同 good_land.mjs）。别的真人的出生点不动。
// 用法：node scripts/voronoi_whatif.mjs <局号> [--ours id,…] [--move id:x:y,id:x:y,…] [--assigned]
//   --assigned  把我方每个号换到日志里协调器最后一次给它的点（[HL-SPAWN-BACKEND] me=<id> … -> (x,y) 的最后一行）；
//               没有协调器日志的号不动。回答的是「如果协调器最后一轮的点全部落地，天然地盘是多少」。
//   --move      手工指定。两个开关可以一起用（--move 覆盖 --assigned）。
// 只把引擎推进到出生阶段结束（读地图用），不重放对局。结果另写 tmp/land/<局号>/voronoi_whatif.json。
// 重活，请用：HEAVY_QUEUE=90 timeout 118 bash ../../tools/run-heavy.sh node scripts/voronoi_whatif.mjs <局号> --assigned
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { startEngine, Mirror } from './shadow.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const args = process.argv.slice(2);
const mid = args[0];
const opt = (k, d) => { const i = args.indexOf(k); return i >= 0 ? args[i + 1] : d; };
if (!mid) { console.error('用法：node scripts/voronoi_whatif.mjs <局号> [--ours id,…] [--move id:x:y,…] [--assigned]'); process.exit(2); }
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
const nm = (p) => (names[p] || '').replace('[APEX] ', '') + '#' + p;
const fmt = (n) => Math.round(n).toLocaleString('en-US');
const med = (v) => { if (!v.length) return 0; const s = [...v].sort((a, b) => a - b); return s[s.length >> 1]; };

const humans = meta.players.filter((x) => x.p < ku && x.box && x.box[0] <= x.box[2]);
const hp = humans.map((x) => x.p);
const actual = new Map(humans.map((x) => [x.p, [x.spawn[0], x.spawn[1]]]));
const moved = new Map([...actual.entries()].map(([p, xy]) => [p, [...xy]]));
const why = new Map();
if (args.includes('--assigned')) {
  const fp = path.join(HERE, '..', '..', '..', '..', '..', 'c136-data', 'bundles', mid, 'in_game.log');
  const re = /\[HL-SPAWN-BACKEND\] me=(\d+) .*?-> \((-?\d+),(-?\d+)\)/;
  for (const line of fs.readFileSync(fp, 'utf8').split('\n')) {
    const m = re.exec(line);
    if (!m) continue;
    const p = +m[1];
    if (isOur[p] && moved.has(p)) { moved.set(p, [+m[2], +m[3]]); why.set(p, '协调器最后给的点'); }
  }
}
for (const s of (opt('--move', '') || '').split(',').filter(Boolean)) {
  const [p, x, y] = s.split(':').map(Number);
  if (moved.has(p)) { moved.set(p, [x, y]); why.set(p, '手工指定'); }
}

function voronoi(pts) {
  const hx = hp.map((p) => pts.get(p)[0]), hy = hp.map((p) => pts.get(p)[1]);
  const nE = new Float64Array(hp.length), nL = new Float64Array(hp.length);
  const vorL = new Int16Array(N).fill(-1);
  let land = 0;
  for (let i = 0; i < N; i++) {
    if (type[i] !== T_LAND) continue;
    land++;
    const x = i % W, y = (i / W) | 0;
    let best = -1, bd = Infinity;
    for (let k = 0; k < hp.length; k++) { const dx = x - hx[k], dy = y - hy[k], d = dx * dx + dy * dy; if (d < bd) { bd = d; best = k; } }
    nE[best]++;
  }
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
  for (let i = 0; i < N; i++) if (type[i] === T_LAND && vorL[i] >= 0) nL[vorL[i]]++;
  return { land, nE, nL };
}

const oursK = hp.map((p, k) => k).filter((k) => isOur[hp[k]]);
const othersK = hp.map((p, k) => k).filter((k) => !isOur[hp[k]]);
const sum = (ks, a) => ks.reduce((s, k) => s + a[k], 0);
const out = { match: mid, humansPresent: hp.length, ours: oursK.length, moved: [], cases: {} };
const movedList = hp.filter((p) => isOur[p] && (moved.get(p)[0] !== actual.get(p)[0] || moved.get(p)[1] !== actual.get(p)[1]));
console.log(`# ${mid} 天然地盘对照：到场真人 ${hp.length} 个，我方 ${oursK.length} 个（人头占 ${(100 * oursK.length / hp.length).toFixed(1)}%）`);
console.log('  换了出生点的号：' + (movedList.length ? movedList.map((p) => {
  const a = actual.get(p), b = moved.get(p);
  out.moved.push({ p, from: a, to: b, dist: Math.round(Math.hypot(a[0] - b[0], a[1] - b[1])), why: why.get(p) || '' });
  return `${nm(p)} (${a[0]},${a[1]})→(${b[0]},${b[1]})（相隔 ${Math.round(Math.hypot(a[0] - b[0], a[1] - b[1]))} 像素）`;
}).join('；') : '没有'));
for (const [lab, pts, key] of [['实际出生点', actual, 'actual'], ['换点以后', moved, 'moved']]) {
  const v = voronoi(pts);
  const row = {};
  for (const [nm2, a, k2] of [['欧氏', v.nE, 'euclid'], ['陆路', v.nL, 'landpath']]) {
    const so = sum(oursK, a), mo = med(oursK.map((k) => a[k])), mx = med(othersK.map((k) => a[k]));
    console.log(`  ${lab}｜${nm2}：我方名下 ${fmt(so)} 格 = 全图陆地的 ${(100 * so / v.land).toFixed(1)}%；单号中位 ${fmt(mo)} 格，其他真人中位 ${fmt(mx)} 格（${(mo / Math.max(1, mx)).toFixed(2)} 倍）`);
    console.log('      各号：' + oursK.map((k) => `${nm(hp[k])} ${fmt(a[k])}`).join('，'));
    row[k2] = { ourPx: so, ourSharePct: +(100 * so / v.land).toFixed(2), ourMedian: mo, otherMedian: mx, perBot: Object.fromEntries(oursK.map((k) => [hp[k], a[k]])) };
  }
  out.cases[key] = row;
}
const dir = path.join(HERE, '..', 'tmp', 'land', mid);
fs.mkdirSync(dir, { recursive: true });
fs.writeFileSync(path.join(dir, 'voronoi_whatif.json'), JSON.stringify(out));
process.exit(0);
