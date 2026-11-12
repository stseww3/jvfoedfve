// chan_unpaired.mjs — 通道开环核对的补充诊断：「影子认定发出、录像里没有、通道模型却判成执行」的陆攻指令都落在哪。
//
// 做法与 chan_openloop.mjs 的 ①③④ 相同（同一串决策喂给 R06 的 Channel + C2 实录阶梯，不带引擎），只是把这类指令逐条拿出来看：
//   · 离它最近的两条「真落地」指令（同席位，前一条 / 后一条）隔多远——落在一段「前后很久都没有任何指令落地」的空档里的，
//     说明那一段页面发出的指令是整段没到服务器（不是迟到），阶梯在空档里只能拿两头的落后去补，于是判成了执行
//   · 离这个席位页面寿命终点多远
// 用法：HEAVY_TIMEOUT=110 timeout 120 bash ../../tools/run-heavy.sh node scripts/ckpt/chan_unpaired.mjs <局号…>
// 输出：reports/ckpt-data/chan_unpaired.csv（每局一行）与逐局一段摘要
import fs from 'node:fs';
import path from 'node:path';
import { R01, OUT, LC, LU, loadR01, readCsv } from './common.mjs';

const o = LU.parseArgs(process.argv.slice(2));
const mids = o._;
if (!mids.length) { console.error('用法：chan_unpaired.mjs <局号…>'); process.exit(2); }
const GAP = LU.num(o.gap, 210);   // 「空档」的门槛：前后两条真落地指令的下令拍相隔超过这么多拍（缺省 30 个回合）
const q = (a, p) => { if (!a.length) return null; const b = a.slice().sort((x, y) => x - y); return b[Math.min(b.length - 1, Math.floor(p * b.length))]; };

const rows = [];
for (const mid of mids) {
  const M = loadR01(mid);
  const squad = M.squad, squadSet = new Set(squad);
  const trace = JSON.parse(fs.readFileSync(path.join(R01, 'reports', 'ckpt-data', 'traces', `${mid}.json`), 'utf8'));
  const dec = readCsv(path.join(OUT, mid, 'shadow_cmds.csv')).filter((r) => r.ok === '1' && squadSet.has(+r.p))
    .map((r) => ({ p: +r.p, W: +r.t, k: r.kind === 'attack' ? 'atk' : r.kind === 'donate' ? 'don' : 'boat', landedAt: r.landedAt === '' || r.landedAt === undefined ? null : +r.landedAt }))
    .sort((a, b) => a.W - b.W || a.p - b.p);
  const Wmax = Math.max(...dec.map((d) => d.W), 0) + 2500;
  const prof = LC.makeProfile('C2:fill=auto', { seed: 1, seats: squad, trace, seatMap: null, Wmax, pageEnd: M.pageEnd, doomed: M.doomed, ownTrace: true });
  const host = { world: { t: 0 }, onIssue() {}, onDrop(seat, cmd, why) { cmd.st = 'drop'; cmd.why = why; }, execOur(seat, cmd) { cmd.st = 'exec'; cmd.Ex = host.world.t; return { ok: true, rec: true }; } };
  const chan = new LC.Channel(host, prof, { multi: false, cap: 9, capRounds: 3, keep: 'first', order: 'lifo' });
  const seatObj = new Map(squad.map((p) => [p, { p }]));
  let i = 0;
  for (let t = 0; t <= Wmax; t++) {
    host.world.t = t;
    while (i < dec.length && dec[i].W === t) { chan.submit(seatObj.get(dec[i].p), dec[i]); i++; }
    if (t % 7 === 0) chan.settle(t);
  }
  // 每个席位真落地指令的下令拍（升序）
  const landedW = new Map(squad.map((p) => [p, []]));
  for (const d of dec) if (d.landedAt !== null) landedW.get(d.p).push(d.W);
  const ghosts = dec.filter((d) => d.k === 'atk' && d.landedAt === null && d.st === 'exec');
  let inGap = 0, afterLast = 0, nearEnd = 0, dense = 0;
  const gaps = [], lagModel = [];
  const perSeat = new Map();
  for (const d of ghosts) {
    const a = landedW.get(d.p);
    let prev = -1, next = -1;
    for (const w of a) { if (w <= d.W) prev = w; else { next = w; break; } }
    const pe = M.pageEnd ? M.pageEnd[d.p] : null;
    const gap = prev >= 0 && next >= 0 ? next - prev : null;
    if (next < 0) afterLast++;                       // 这个席位此后再没有任何指令落地
    else if (gap !== null && gap > GAP) inGap++;     // 夹在一段长空档里
    else dense++;                                     // 前后不远都有真落地的指令：单条丢失
    if (pe !== null && pe !== undefined && pe - d.W <= GAP) nearEnd++;
    if (gap !== null) gaps.push(gap);
    lagModel.push(d.Ex - d.W);
    perSeat.set(d.p, (perSeat.get(d.p) || 0) + 1);
  }
  const top = [...perSeat.entries()].sort((x, y) => y[1] - x[1]).slice(0, 3).map(([p, n]) => `席${p}:${n}`).join(' ');
  const row = {
    mid, atkUnpaired: dec.filter((d) => d.k === 'atk' && d.landedAt === null).length, ghosts: ghosts.length,
    afterLastLanded: afterLast, inLongGap: inGap, isolated: dense, nearPageEnd: nearEnd,
    gapP50: q(gaps, 0.5), gapP90: q(gaps, 0.9), modelLagP50: q(lagModel, 0.5), modelLagP90: q(lagModel, 0.9), seatsWithGhosts: perSeat.size, top3: top,
  };
  rows.push(row);
  console.log(`[unpaired] ${mid}：没配上的陆攻 ${row.atkUnpaired} 条，其中模型判成执行 ${row.ghosts} 条 = 该席位此后再无指令落地 ${afterLast} + 夹在 > ${GAP} 拍的空档里 ${inGap} + 前后不远都有真落地的 ${dense}`
    + `（离页面寿命终点 ≤ ${GAP} 拍的 ${nearEnd}）；所在空档长度 P50/P90 = ${row.gapP50}/${row.gapP90} 拍；模型给它们的落后 P50/P90 = ${row.modelLagP50}/${row.modelLagP90} 拍；涉及 ${perSeat.size} 席（${top}）`);
}
const file = path.join(R01, 'reports', 'ckpt-data', 'chan_unpaired.csv');
let old = [];
if (fs.existsSync(file)) old = readCsv(file).filter((r) => !rows.some((x) => x.mid === r.mid));
const all = [...old, ...rows];
const cols = Object.keys(rows[0]);
fs.writeFileSync(file, cols.join(',') + '\n' + all.map((r) => cols.map((c) => (/[,"]/.test(String(r[c])) ? `"${String(r[c]).replace(/"/g, '""')}"` : r[c])).join(',')).join('\n') + '\n');
console.log(`[unpaired] 已写 ${path.relative(R01, file)}（${all.length} 局）`);
