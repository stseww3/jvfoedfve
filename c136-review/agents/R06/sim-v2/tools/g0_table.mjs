// g0_table.mjs — 把一批 checkpoint 结果文件排成 G0 自检的对照表。
// 用法（在 c136-review/agents/R06 下）：node sim-v2/tools/g0_table.mjs <结果.json …> [--md] [--arm=baseline] [--bands] [--bands-file sim-v2/calib/live-bands.json]
//   缺省：每个结果文件一行，每个签名给「模拟臂 / 这一局当年的真值」两个数。
//   --bands：每个签名再对上「实盘区间」（tools/live_table.mjs 从 --mode live 的全量扫描算出的 P25~P75；通道 C1 对 clean 档，C2/C3/C4 对 lag 档），
//            给出落在区间内（in）/ 偏低（lo）/ 偏高（hi）；区间的局数 < 4 时不判（~）。末尾按签名、按通道汇总命中数。
import fs from 'node:fs';

const args = process.argv.slice(2);
const md = args.includes('--md');
const withBands = args.includes('--bands');
const argOf = (k, d) => { const i = args.indexOf(k); return i >= 0 ? args[i + 1] : d; };
const bandsFile = argOf('--bands-file', 'sim-v2/calib/live-bands.json');
const arm = (args.find((a) => a.startsWith('--arm=')) || '--arm=baseline').slice(6);
const files = args.filter((a, i) => !a.startsWith('--') && args[i - 1] !== '--bands-file');
const pc = (v) => (v === null || v === undefined ? '-' : (100 * v).toFixed(0) + '%');
const k3 = (v) => (v === null || v === undefined ? '-' : Math.abs(v) >= 1000 ? (v / 1000).toFixed(1) + 'k' : String(Math.round(v * 1000) / 1000));
const cohortOfStrategy = (s) => (/c110/.test(s) ? 'c110' : /c116-vb/.test(s) ? 'vb' : /c116-va/.test(s) ? 'va' : /c116/.test(s) ? 'vc' : /g09/.test(s) ? 'g09' : '?');

// 签名：键（区间文件里的名字）、表头、从一条臂 / 历史臂取值、显示
const SIG = [
  ['recPerSeat', '进录像条数÷席位', (m) => m.recorded / m.seats, (v) => (v === null || v === undefined ? '-' : v.toFixed(1))],
  ['dupShare', '重复单占比', (m) => m.dupShare, pc],
  ['batchShare', '同拍批占比', (m) => m.batchShare, pc],
  ['gap0', '同回合连发占比', (m) => (m.gapShare ? m.gapShare[0] : null), pc],
  ['dumpPerSeat', '清仓批÷席位', (m) => m.dumpBatches / m.seats, (v) => (v === null || v === undefined ? '-' : v.toFixed(2))],
  ['atkVoidRate', '陆攻落空率', (m) => m.atkVoidRate, pc],
  ['rerouteRate', '目标已死改道率', (m) => m.rerouteRate, pc],
  ['atkNeutralShare', '陆攻记成无主地占比', (m) => m.atkNeutralShare, pc],
  ['donNotLanded', '捐款没成交占比', (m) => m.donNotLanded, pc],
  ['relTerr1', '窗口末人均相对领土', (m) => m.relTerr1, k3],
  ['aliveShare', '存活席位占比', (m) => m.alive1 / m.seats, pc],
];

const B = withBands && fs.existsSync(bandsFile) ? JSON.parse(fs.readFileSync(bandsFile, 'utf8')) : null;
const rows = [];
const tally = new Map();   // 签名 → {in, n}
const tallyRun = [];
for (const f of files) {
  let r;
  try { r = JSON.parse(fs.readFileSync(f, 'utf8')); } catch (e) { continue; }
  const h = r.history, b = r.arms && r.arms[arm];
  if (!b) continue;
  const strat = b.strategy.replace('v27-team-', '');
  const chan = String(r.channelSpec);
  const cls = /^C1/i.test(chan) || /^C0/i.test(chan) ? 'clean' : 'lag';
  const band = B ? (B.cohorts[`${cohortOfStrategy(b.strategy)}|${cls}|${r.t0}~${r.t1}`] || null) : null;
  const row = [r.match, `${r.t0}~${r.t1}`, strat, chan];
  let hit = 0, judged = 0;
  for (const [key, , get, show] of SIG) {
    const sv = get(b), hv = get(h);
    let cell = `${show(sv)} / ${show(hv)}`;
    if (B) {
      const bd = band && band.band[key];
      if (!bd) cell += ' ｜ -';
      else {
        let verdict = '~';
        if (bd[3] >= 4 && sv !== null && sv !== undefined && !Number.isNaN(sv)) {
          verdict = sv < bd[0] - 1e-9 ? 'lo' : sv > bd[2] + 1e-9 ? 'hi' : 'in';
          judged++; if (verdict === 'in') hit++;
          const t = tally.get(key) || { in: 0, n: 0, lo: 0, hi: 0 };
          t.n++; t[verdict]++;
          tally.set(key, t);
        }
        cell += ` ｜ ${show(bd[0])}~${show(bd[2])} ${verdict}`;
      }
    }
    row.push(cell);
  }
  if (B) { row.push(`${hit}/${judged}`); tallyRun.push({ match: r.match, win: `${r.t0}~${r.t1}`, strat, chan, hit, judged }); }
  row.push(`${b.don.arrived ? pc(b.quotaRejectRate) + '（到达 ' + b.don.arrived + '）' : '-'}`);
  rows.push(row);
}
const head = ['局', '窗口', '策略', '通道', ...SIG.map((s) => s[1]), ...(B ? ['落在实盘区间'] : []), '配额拒单率（模拟，到达结算的）'];
if (md) {
  console.log('| ' + head.join(' | ') + ' |');
  console.log('|' + head.map(() => '---').join('|') + '|');
  for (const r of rows) console.log('| ' + r.join(' | ') + ' |');
} else {
  console.log(head.join('\t'));
  for (const r of rows) console.log(r.join('\t'));
}
console.log((md ? '\n' : '') + (B ? '每格：模拟对照臂 / 这一局当年的真值 ｜ 同版本同卡顿档实盘 P25~P75 与判定（in 区间内，lo 偏低，hi 偏高，~ 区间局数不足 4 不判）' : '每格：模拟对照臂 / 这一局当年的真值'));
if (B) {
  console.log((md ? '\n' : '') + '按签名汇总（区间内 / 判过的次数；偏低、偏高各几次）：');
  for (const [key, label] of SIG) { const t = tally.get(key); if (t) console.log(`  ${label}：${t.in}/${t.n}（偏低 ${t.lo}，偏高 ${t.hi}）`); }
  const by = new Map();
  for (const t of tallyRun) { const k = `${t.strat} ${t.chan.replace(/[:←].*$/, '')} ${t.win}`; const g = by.get(k) || { hit: 0, judged: 0, runs: 0 }; g.hit += t.hit; g.judged += t.judged; g.runs++; by.set(k, g); }
  console.log((md ? '\n' : '') + '按 策略 × 通道 × 窗口 汇总：');
  for (const [k, g] of by) console.log(`  ${k}：${g.runs} 次运行，${g.hit}/${g.judged} 项落在区间内`);
}
