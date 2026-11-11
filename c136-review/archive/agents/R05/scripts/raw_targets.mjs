// raw_targets.mjs — 录像里我方号每条陆攻指令的「原始目标编号」（录像字段 dZ，未经 min(dZ,512) 归并）。
//   用来核对「同拍连发批里的打中立指令，原本是不是打某个机器人的指令」：
//   录像目标 = 512 → 发出时就是打中立；> 512 → 录像里另有编码；< 512 而目标已无地 → 目标在落地前死了。
//   每条指令给出：拍、号、pct、原始 dZ、落地时目标的地与兵（真人/机器人）、是否执行成功、打出的兵；
//   --win A:B 只看这个拍段；--batch 只列同拍 ≥3 条的批；汇总：按（目标类别 × 是否成功）计数。
// 用法：node raw_targets.mjs <matchId> [--win 900:2100] [--batch] [--bots kaito9,zero_7] [--list]
import { simulate, NEUTRAL } from './sim_replay.mjs';
import { squadIds } from './match_truth.mjs';

const a = process.argv.slice(2);
const mid = a[0];
const val = (k, d) => (a.includes(k) ? a[a.indexOf(k) + 1] : d);
const [W0, W1] = String(val('--win', '0:99999')).split(':').map(Number);
const only = val('--bots', '') ? new Set(val('--bots', '').split(',')) : null;
const list = a.includes('--list'), batchOnly = a.includes('--batch');
let sq = null, H = 0;
const rows = [];
let G = null;
await simulate(mid, {
  onStart(g, info) { sq = new Map(squadIds(mid, info.names, info.H).squad); H = info.H; G = g; },
  skipCmd(c, g) {
    if (c.id !== 1 || !sq || !sq.has(c.player)) return false;
    if (g.t < W0 || g.t >= W1) return false;
    const bot = sq.get(c.player);
    if (only && !only.has(bot)) return false;
    const dZ = c.dZ;
    const cls = dZ === NEUTRAL ? '中立(512)' : dZ > NEUTRAL ? `大于512(${dZ})` : dZ < H ? '真人' : '机器人';
    const tL = dZ < NEUTRAL ? g.terr[dZ] : -1, tB = dZ < NEUTRAL ? g.bal[dZ] : -1;
    rows.push({ t: g.t, bot, p: c.player, pct: c.dX, dZ, cls, tL, tB, B0: g.bal[c.player], idx: rows.length });
    return false;
  },
  onEvent(ev) {
    if (ev.type !== 'attack' || !sq || !sq.has(ev.p)) return;
    // 与 skipCmd 里刚压进去的那一行配对（同拍、同号、同 pct，最后一条未配对的）
    for (let i = rows.length - 1; i >= 0; i--) {
      const r = rows[i];
      if (r.t === ev.t && r.p === ev.p && r.pct === ev.pct && r.ok === undefined) { r.ok = ev.ok; r.troops = ev.troops; break; }
      if (r.t < ev.t) break;
    }
  },
});
const key = (r) => r.bot + '@' + r.t;
const cnt = new Map();
for (const r of rows) cnt.set(key(r), (cnt.get(key(r)) || 0) + 1);
const sel = batchOnly ? rows.filter((r) => cnt.get(key(r)) >= 3) : rows;
const tally = new Map();
for (const r of sel) {
  const dead = r.cls === '机器人' || r.cls === '真人' ? (r.tL === 0 ? '·目标已无地' : '·目标有地') : '';
  const k = `${r.cls.replace(/\(\d+\)/, r.cls.startsWith('大于') ? '' : '(512)').replace('(512)(512)', '(512)')}${dead}｜${r.ok ? '成' : '落空'}`;
  const o = tally.get(k) || { n: 0, troops: 0 };
  o.n++; o.troops += r.troops || 0;
  tally.set(k, o);
}
console.log(`# ${mid} 我方号陆攻指令的原始目标（拍段 ${W0}–${W1}${batchOnly ? '，只算同拍 ≥3 条的批' : ''}）：共 ${sel.length} 条`);
for (const [k, o] of [...tally].sort((x, y) => y[1].n - x[1].n)) console.log(`  ${k}：${o.n} 条，打出 ${Math.round(o.troops / 1000)}k`);
const big = [...new Set(sel.filter((r) => r.dZ > NEUTRAL).map((r) => r.dZ))];
if (big.length) console.log(`  大于 512 的原始目标编号：${big.slice(0, 20).join(',')}`);
if (list) for (const r of sel) console.log(`  t=${r.t} ${r.bot} pct=${r.pct} dZ=${r.dZ}（${r.cls}${r.tL >= 0 ? `，地 ${r.tL} 兵 ${r.tB}` : ''}）${r.ok ? '成' : '落空'} 打出 ${r.troops || 0}｜批前存兵 ${r.B0}`);
