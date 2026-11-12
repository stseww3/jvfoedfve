// stair_logorder.mjs — 实录阶梯的独立旁证：页面日志的先后次序给出的「落后下界」。
//
// 归档的 in_game.log 每行开头是全局行号（采集端收到的先后次序）。同一局里我方各页面各自每 90 个本机拍写一行 [HL-TICK] t=…。
// 页面 p 写下本机拍 τ 的那一刻，如果别的页面早已写过本机拍 Tmax > τ，那么服务器当时至少已经到了 Tmax：
//     落后(p, τ) = S(τ) − τ ≥ Tmax − τ          （Tmax = 行号更小的所有我方日志行里最大的本机拍）
// 这只是下界（最快的那个页面自己也可能落后），但它完全不依赖「影子决策 ↔ 录像落地」的配对，是另一份实录。
// 用它检验 C2 的阶梯：traces（只收唯一定位的）/ traces-hi / traces-lo 三种口径各自在这些点上给出的落后，够不够得着下界。
//
// 不跑引擎、不跑策略；阶梯用 R06 的 lib/channel.mjs（buildC2，fill=auto）原样算。
// 用法：HEAVY_TIMEOUT=110 timeout 120 bash ../../tools/run-heavy.sh node scripts/ckpt/stair_logorder.mjs <局号…>
// 输出：reports/ckpt-data/stair_logorder.csv（每局每口径一行）与 reports/ckpt-data/logorder/<局>.csv（逐点的下界）
import fs from 'node:fs';
import path from 'node:path';
import { R01, OUT, LC, LU, loadR01, readCsv } from './common.mjs';

const o = LU.parseArgs(process.argv.slice(2));
const mids = o._;
if (!mids.length) { console.error('用法：stair_logorder.mjs <局号…>'); process.exit(2); }
const BUNDLES = '/agent/repos/c136-data/bundles';
const BEHIND = LU.num(o.behind, 90);   // 下界 ≥ 这么多拍才算「明显落后」的点（日志 90 拍一行，小于一行的差不算）
const TOL = LU.num(o.tol, 45);         // 阶梯给出的落后比下界少不超过这么多拍，算够得着
const q = (a, p) => { if (!a.length) return null; const b = a.slice().sort((x, y) => x - y); return b[Math.min(b.length - 1, Math.floor(p * b.length))]; };
const VARIANTS = [['located', 'traces'], ['hi', 'traces-hi'], ['lo', 'traces-lo']];

const rows = [];
for (const mid of mids) {
  const M = loadR01(mid);
  const squad = M.squad, squadSet = new Set(squad);
  // 标签 → 席位号
  const label = new Map();
  for (const r of readCsv(path.join(OUT, mid, 'resim_check.csv'))) if (!label.has(r.bot)) label.set(r.bot, +r.p);
  const logFile = path.join(BUNDLES, mid, 'in_game.log');
  if (!fs.existsSync(logFile)) { console.log(`[logorder] ${mid} 没有 in_game.log`); continue; }
  const pts = [];
  for (const line of fs.readFileSync(logFile, 'utf8').split('\n')) {
    const m = /^(\d+)\t\[([^\]]+)\] \[HL-TICK\] t=(\d+) /.exec(line);
    if (!m) continue;
    const p = label.get(m[2]);
    if (p === undefined || !squadSet.has(p)) continue;
    pts.push({ seq: +m[1], p, t: +m[3] });
  }
  pts.sort((a, b) => a.seq - b.seq);
  let tmax = -1;
  for (const x of pts) { x.lb = Math.max(0, tmax - x.t); if (x.t > tmax) tmax = x.t; }
  fs.mkdirSync(path.join(R01, 'reports', 'ckpt-data', 'logorder'), { recursive: true });
  const Wmax = Math.max(...pts.map((x) => x.t), 0) + 200;
  const model = {};
  for (const [name, dir] of VARIANTS) {
    const f = path.join(R01, 'reports', 'ckpt-data', dir, `${mid}.json`);
    if (!fs.existsSync(f)) continue;
    const trace = JSON.parse(fs.readFileSync(f, 'utf8'));
    const prof = LC.makeProfile('C2:fill=auto,pagedeath=0', { seed: 1, seats: squad, trace, seatMap: null, Wmax });
    model[name] = prof;
    for (const x of pts) x[name] = prof.lag(x.p, x.t);
  }
  fs.writeFileSync(path.join(R01, 'reports', 'ckpt-data', 'logorder', `${mid}.csv`),
    'seq,p,t,lowerBound,' + Object.keys(model).map((n) => `lag_${n}`).join(',') + '\n' + pts.map((x) => [x.seq, x.p, x.t, x.lb, ...Object.keys(model).map((n) => x[n])].join(',')).join('\n') + '\n');
  const behind = pts.filter((x) => x.lb >= BEHIND);
  const line = [`[logorder] ${mid}：日志点 ${pts.length} 个，其中下界 ≥ ${BEHIND} 拍的 ${behind.length} 个（下界 P50/P90/最大 = ${q(behind.map((x) => x.lb), 0.5)}/${q(behind.map((x) => x.lb), 0.9)}/${behind.length ? Math.max(...behind.map((x) => x.lb)) : null}）`];
  for (const name of Object.keys(model)) {
    const ok = behind.filter((x) => x[name] >= x.lb - TOL).length;
    const short = behind.map((x) => Math.max(0, x.lb - x[name]));
    const calm = pts.filter((x) => x.lb < BEHIND);
    const row = {
      mid, variant: name, points: pts.length, behind: behind.length, lbP50: q(behind.map((x) => x.lb), 0.5), lbP90: q(behind.map((x) => x.lb), 0.9),
      reach: ok, reachShare: behind.length ? +(ok / behind.length).toFixed(3) : '', shortfallMean: behind.length ? +(short.reduce((s, v) => s + v, 0) / behind.length).toFixed(1) : '',
      modelLagP50AtBehind: q(behind.map((x) => x[name]), 0.5), modelLagP50AtCalm: q(calm.map((x) => x[name]), 0.5), modelLagP90AtCalm: q(calm.map((x) => x[name]), 0.9),
    };
    rows.push(row);
    line.push(`  ${name.padEnd(7)}：够得着下界的 ${ok}/${behind.length}，平均差 ${row.shortfallMean} 拍；这些点上阶梯的落后中位 ${row.modelLagP50AtBehind}；其余点上阶梯的落后 P50/P90 = ${row.modelLagP50AtCalm}/${row.modelLagP90AtCalm}`);
  }
  console.log(line.join('\n'));
}
const file = path.join(R01, 'reports', 'ckpt-data', 'stair_logorder.csv');
let old = [];
if (fs.existsSync(file)) old = readCsv(file).filter((r) => !rows.some((x) => x.mid === r.mid));
if (rows.length) {
  const cols = Object.keys(rows[0]);
  fs.writeFileSync(file, cols.join(',') + '\n' + [...old, ...rows].map((r) => cols.map((c) => r[c]).join(',')).join('\n') + '\n');
  console.log(`[logorder] 已写 ${path.relative(R01, file)}`);
}
