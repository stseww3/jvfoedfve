#!/usr/bin/env node
// spawn_order_probe.mjs — 录像块内指令顺序的敏感性检查（只读重演，不改任何数据）。
//   同一个号在同一拍落地两条出生指令时，引擎按录像块内的顺序依次执行，后一条覆盖前一条。
//   本脚本把指定的指令（按 replay_cmds 输出的全局行号，0 起）从重演里拿掉，再做一遍 [HL-TICK] 比对：
//   如果拿掉「块内后一条」之后比对从全等变成不等，说明线上那一局里生效的就是块内后一条。
// 用法：node scripts/spawn_order_probe.mjs <局> --skip 227[,i2,…] [--max 400]
//   输出：基线与变体各一行（可比条数 / terr 与 bal 全等条数 / 第一条不等），以及我方各号开局第 1 拍的领地外接框中心。
import { simulate, parseTicks, botIds } from './sim_replay.mjs';

const args = process.argv.slice(2);
const id = args[0];
const val = (k, d) => (args.includes(k) ? args[args.indexOf(k) + 1] : d);
const SKIP = new Set(String(val('--skip', '')).split(',').filter(Boolean).map(Number));
const maxTick = +val('--max', 1e9);
const ticks = parseTicks(id);
const byT = new Map();
for (const x of ticks) { if (!byT.has(x.t)) byT.set(x.t, []); byT.get(x.t).push(x); }

function run(label, skip) {
  let ids = null; const cmp = []; const pos = new Map(); const skipped = [];
  simulate(id, {
    maxTick,
    skipCmd: (c, g, a) => { if (skip.has(a)) { skipped.push(`#${a} 玩家${c.player} id=${c.id} (${c.dX % g.W},${Math.floor(c.dX / g.W)})`); return true; } return false; },
    onStart: (g, ctx) => { ids = botIds(ctx.names, ctx.H, [...new Set(ticks.map((x) => x.bot))]); },
    onTick: (g, t) => {
      if (t === 1) for (const [b, p] of ids) if (p >= 0) pos.set(b, [(g.x0[p] + g.x1[p]) >> 1, (g.y0[p] + g.y1[p]) >> 1, g.terr[p]]);
      const L = byT.get(t);
      if (L) for (const x of L) { const p = ids.get(x.bot); if (p >= 0) cmp.push({ ...x, p, sTerr: g.terr[p], sBal: g.bal[p] }); }
    },
  });
  const exact = cmp.filter((x) => x.terr === x.sTerr && x.bal === x.sBal).length;
  const bad = cmp.filter((x) => x.terr !== x.sTerr || x.bal !== x.sBal);
  const byBot = {}; for (const x of bad) byBot[x.bot] = (byBot[x.bot] || 0) + 1;
  console.log(`[${label}] 拿掉的指令：${skipped.join('；') || '无'}`);
  console.log(`   [HL-TICK] 可比 ${cmp.length} 条，terr 与 bal 全等 ${exact} 条` + (bad.length ? `；第一条不等 t=${bad[0].t} ${bad[0].bot} 日志 ${bad[0].terr}/${bad[0].bal} 重演 ${bad[0].sTerr}/${bad[0].sBal}；不等的条数按号 ${JSON.stringify(byBot)}` : ''));
  console.log('   第 1 拍各号领地外接框中心：' + [...pos].map(([b, v]) => `${b}(${v[0]},${v[1]}) ${v[2]}格`).join(' '));
}
run('基线', new Set());
if (SKIP.size) run('变体', SKIP);
