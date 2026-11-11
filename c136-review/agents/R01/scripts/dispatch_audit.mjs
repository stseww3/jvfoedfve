// dispatch_audit.mjs — 逐条核对日志里的捐款调度（[HL-DISPATCH]/[HL-ASSIST]/[HL-DONATE] 等带 "pct=…/1024 -> ally=id" 的行）：
// 引擎在那一拍会不会接受？不接受是卡在配额、受赠者上限还是对象已死/已离场？录像里实际有没有落地？
//   node dispatch_audit.mjs <matchId> [--replay other] [--log bundleId]
// 做法：整局重演到日志行的拍 t（本地拍 = 同一拍的全局状态），按引擎公式算：
//   名义额 v=min(floor(B*(pct+1)/1024), B-fee)，fee=floor(64B/1024)；受赠者余量 room=min(150*terr-bal, 1.5e9-bal)；
//   配额成本 cost（t<357/714/1071/2142/3213 五档，>=3213 为 4+floor(100v/softCap)）；已用 used、上限 cap；t>=4284 或对象是离场/AI 时不设配额。
// 再与录像里的捐款指令配对（同捐出方、同受赠方、同 pct，执行拍在 [t, t+600] 内最早一条未配对的）。
// 输出 out/<matchId>/dispatch_audit.csv 和汇总。
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { openMatch } from './resim_lib.mjs';

const args = process.argv.slice(2);
const mid = args[0];
const opt = (k, d) => (args.includes(`--${k}`) ? args[args.indexOf(`--${k}`) + 1] : d);
const HERE = path.dirname(fileURLToPath(import.meta.url));
const OUT = path.resolve(HERE, '..', 'out', mid);
fs.mkdirSync(OUT, { recursive: true });
const logId = opt('log', mid);

const me = {}, rows = [];
for (const line of fs.readFileSync(`/agent/repos/c136-data/bundles/${logId}/in_game.log`, 'utf8').split('\n')) {
  let x = line.match(/\[([^\]]+)\] \[HL-GAME-INIT\].*me=(\d+)/);
  if (x) { me[x[1]] = +x[2]; continue; }
  x = line.match(/\[([^\]]+)\] \[(HL-[A-Z-]+)\] t=(\d+) (\S+) pct=(\d+)\/1024 -> ally=(\d+)\(([^)]*)\)(.*)$/);
  if (x && me[x[1]] !== undefined) {
    const rest = x[8];
    const f = (k) => { const r = rest.match(new RegExp(k + '=([\\d.]+)')); return r ? +r[1] : null; };
    rows.push({ bot: x[1], p: me[x[1]], tag: x[2], t: +x[3], kind: x[4], pct: +x[5], to: +x[6], toName: x[7], myBal: f('myBal'), dMe: f('dMe'), dAlly: f('dAlly'), boxedIn: /boxedIn=true/.test(rest) });
  }
}
rows.sort((a, b) => a.t - b.t);

const m = openMatch(mid, { replay: opt('replay', mid) });
const { g } = m;
const iV = (a, b) => Math.floor((a + 0.5) / b);
let i = 0;
const evalRow = (r) => {
  const B = g.bal[r.p], q = r.to;
  const fee = iV(64 * B, 1024);
  const v0 = Math.min(iV(B * (r.pct + 1), 1024), B - fee);
  const room = g.alive[q] ? Math.min(150 * g.terr[q] - g.bal[q], 1.5e9 - g.bal[q]) : 0;
  const v = Math.max(0, Math.min(v0, room));
  const free = g.donationFree(q);
  const cost = v >= 1 ? g.donationCost(q, v) : 0;
  const used = g.donQuota[q], cap = g.donCap;
  let would = 'accept';
  if (!g.alive[q]) would = 'dead';
  else if (!g.alive[r.p] || g.state[r.p] === 2) would = 'donor-gone';
  else if (v < 1) would = 'room';
  else if (!free && used + cost > cap) would = 'quota';
  Object.assign(r, { simBal: B, nominal: v0, room, cost, used, cap, free: free ? 1 : 0, would, toState: g.state[q], toTerr: g.terr[q], toBal: g.bal[q],
    maxByQuota: free ? -1 : quotaMax(q, cap - used) });
};
// 配额还能放进多少兵（成本公式反推，取使 used+cost<=cap 的最大 v）
function quotaMax(q, left) {
  if (left < 2) return 0;
  let lo = 0, hi = 2e9;
  while (lo < hi) { const md = Math.floor((lo + hi + 1) / 2); if (g.donationCost(q, md) <= left) lo = md; else hi = md - 1; }
  return lo;
}
while (true) {
  while (i < rows.length && rows[i].t <= g.t) { evalRow(rows[i]); i++; }
  if (!m.tick()) break;
}
while (i < rows.length) { rows[i].would = 'after-replay'; i++; }

// 与录像落地的捐款配对。
// 同一个号的指令按发出的先后到达，所以配对必须保序；同一条调度会连发很多遍（每 25 拍一遍、pct 相同），没过引擎校验的不进录像。
// 做法：每个捐出方单独做一次保序匹配（动态规划），可配条件：受赠方、pct 相同，延迟 = 落地拍 - 决策拍 在 [6, 600]；
//   代价 = 延迟之和（即尽量配给离落地最近的那一次决策）；落地指令配不上记 1e9。
// 注意：校验发生在指令到达引擎的那一拍，不是决策拍。配额上限每逢 t%100==99 上调，所以“决策拍算出来会被拒”的调度
//   也可能落地（例：A055 zero_7 3695 拍决策时 248+10>249，3699 拍上限升到 259，3703 拍落地）。
const cmds = m.transfers.filter((x) => x.kind === 'cmd');
for (const r of rows) r.exec = null;
const donors = [...new Set(rows.map((r) => r.p))];
for (const p of donors) {
  const R = rows.filter((r) => r.p === p), E = cmds.filter((c) => c.from === p).sort((x, y) => x.t - y.t);
  const n = R.length, k = E.length;
  if (!k) continue;
  const INF = 1e15;
  const dp = Array.from({ length: n + 1 }, () => new Float64Array(k + 1).fill(INF));
  const ch = Array.from({ length: n + 1 }, () => new Int8Array(k + 1)); // 0 跳过日志行 1 配对 2 跳过落地指令
  for (let i2 = 0; i2 <= n; i2++) dp[i2][0] = 0;
  for (let j = 1; j <= k; j++) { dp[0][j] = dp[0][j - 1] + 1e9; ch[0][j] = 2; }
  for (let i2 = 1; i2 <= n; i2++) {
    for (let j = 1; j <= k; j++) {
      let best = dp[i2 - 1][j], c = 0;
      const r = R[i2 - 1], e = E[j - 1], lag = e.t - r.t;
      if (e.to === r.to && e.pct === r.pct && lag >= 6 && lag <= 600) {
        const v = dp[i2 - 1][j - 1] + lag;
        if (v < best) { best = v; c = 1; }
      }
      const v2 = dp[i2][j - 1] + 1e9;
      if (v2 < best) { best = v2; c = 2; }
      dp[i2][j] = best; ch[i2][j] = c;
    }
  }
  let i2 = n, j = k;
  while (j > 0) {
    const c = ch[i2][j];
    if (c === 1) { R[i2 - 1].exec = E[j - 1]; i2--; j--; } else if (c === 2) j--; else i2--;
  }
}
const out = ['t,bot,tag,kind,pct,to,toName,logBal,simBal,dMe,dAlly,nominal,room,cost,used,cap,free,maxByQuota,would,executed,execTick,lag,received,paid'];
const sum = {};
for (const r of rows) {
  const ex = r.exec;
  out.push([r.t, r.bot, r.tag, r.kind, r.pct, r.to, JSON.stringify(r.toName), r.myBal, r.simBal, r.dMe, r.dAlly, r.nominal, r.room, r.cost, r.used, r.cap, r.free, r.maxByQuota, r.would,
    ex ? 1 : 0, ex ? ex.t : '', ex ? ex.t - r.t : '', ex ? ex.received : '', ex ? ex.paid : ''].join(','));
  const era = r.t < 2142 ? '<2142' : r.t < 3213 ? '2142-3212' : r.t < 4284 ? '3213-4283' : '>=4284';
  const k = `${era} | ${r.kind} | would=${r.would} | executed=${ex ? 1 : 0}`;
  sum[k] = (sum[k] || 0) + 1;
}
fs.writeFileSync(path.join(OUT, 'dispatch_audit.csv'), out.join('\n') + '\n');
const nEx = rows.filter((r) => r.exec).length;
console.log(`${mid}: 日志调度 ${rows.length} 条，录像落地 ${nEx} 条，未落地 ${rows.length - nEx} 条；录像里本队捐款指令共 ${cmds.filter((c) => Object.values(me).includes(c.from)).length} 条`);
for (const k of Object.keys(sum).sort()) console.log(`  ${k}: ${sum[k]}`);
const rej = rows.filter((r) => !r.exec);
const byReason = {};
for (const r of rej) byReason[r.would] = (byReason[r.would] || 0) + 1;
console.log('  未落地按“那一拍引擎会怎样”: ' + JSON.stringify(byReason));
const q = rej.filter((r) => r.would === 'quota');
if (q.length) {
  const over = q.map((r) => r.nominal / Math.max(1, r.maxByQuota));
  over.sort((a, b) => a - b);
  console.log(`  配额拒绝 ${q.length} 条：名义额/配额还能放的量 中位 ${over[Math.floor(over.length / 2)].toFixed(1)} 倍（最小 ${over[0].toFixed(1)}，最大 ${over[over.length - 1].toFixed(1)}）；其中配额余量为 0 的 ${q.filter((r) => r.maxByQuota === 0).length} 条`);
  const byTo = {};
  for (const r of q) byTo[r.toName] = (byTo[r.toName] || 0) + 1;
  console.log('  配额拒绝按受赠者: ' + JSON.stringify(byTo));
}
