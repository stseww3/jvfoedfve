#!/usr/bin/env node
// whatif_inject.mjs — 「多打一手」的重放推演：在逐拍精确重放里，于指定拍替某个我方号多下几条陆攻指令
//   （走引擎 g.attack(pct, 目标, 号)，pct 是存兵的 1024 分比，和线上一样），其余所有人的指令照录像原样执行，
//   看这个号和目标在其后一段时间的地/兵。
// 这是一阶推演：多打之后别人的指令不会随局面改变（真实对局里对手会还手、队友会改主意），
//   这个号自己后面的录像指令也照旧执行（比例不变、基数变了），所以只看短窗口（默认 300 拍）。
// 用法：
//   node scripts/whatif_inject.mjs <局> --bot kaito9 --target 23 --plan 0 --plan 1505:205 --plan 1505:123,1530:123,1555:123 [--until 1800] [--watch 5,28]
//     --plan  逗号分隔的「拍:pct」；单独一个 0 = 原样重放（对照）。可给多个 --plan，各跑一遍。
//     --watch 另外打印这些玩家编号在 --until 拍的地/兵。
import { simulate, botIds } from './sim_replay.mjs';

const args = process.argv.slice(2);
const id = args[0];
const val = (k, d) => (args.includes(k) ? args[args.indexOf(k) + 1] : d);
const all = (k) => args.map((a, i) => (a === k ? args[i + 1] : null)).filter((x) => x !== null);
const bot = val('--bot', null), target = +val('--target', -1), until = +val('--until', 0);
const plans = all('--plan');
const watch = String(val('--watch', '')).split(',').filter(Boolean).map(Number);
if (!id || !bot || target < 0 || !plans.length) { console.error('用法见文件头'); process.exit(2); }
const k = (x) => (Math.abs(x) >= 1e6 ? (x / 1e6).toFixed(2) + 'M' : Math.round(x / 1000) + 'k');

console.log(`[多打一手] ${id}：替 ${bot} 对玩家 #${target} 多下陆攻指令（引擎 g.attack），其余指令照录像原样执行`);
for (const plan of plans) {
  const steps = plan === '0' ? [] : plan.split(',').map((s) => s.split(':').map(Number));
  const last = steps.length ? Math.max(...steps.map((s) => s[0])) : 0;
  const end = until || last + 300;
  let p = -1, names = null;
  const done = [], track = [];
  const R = simulate(id, {
    maxTick: end,
    onStart: (g, ctx) => { p = botIds(ctx.names, ctx.H, [bot]).get(bot); names = ctx.names; },
    onTick: (g, t) => {
      if (p < 0) return;
      for (const [at, pct] of steps) {
        if (t !== at) continue;
        const b0 = g.bal[p], l0 = g.terr[p], tb = g.bal[target], tl = g.terr[target];
        const ok = g.alive[p] && g.alive[target] ? g.attack(pct, target, p) : false;
        done.push(`t=${at} pct=${pct}（存兵 ${k(b0)} 的 ${(pct / 10.24).toFixed(0)}% ≈ ${k((b0 * (pct + 1)) / 1024)}）${ok ? '受理' : '没受理'}；当时 ${l0} 格/${k(b0)}，目标 ${tl} 格/${k(tb)}`);
      }
      if ((steps.length ? t >= steps[0][0] - 5 : true) && t % 50 === 0 && t >= (steps.length ? steps[0][0] - 5 : end - 300)) {
        track.push(`${t}: ${g.alive[p] ? g.terr[p] + '/' + k(g.bal[p]) : '已除名'} 对 ${g.alive[target] ? g.terr[target] + '/' + k(g.bal[target]) : '已除名'}`);
      }
    },
  });
  const g = R.g;
  if (p < 0) { console.log(`  找不到 ${bot}`); break; }
  console.log(`  方案 ${plan === '0' ? '原样重放（对照）' : plan}：t=${end} ${bot} ${g.alive[p] ? g.terr[p] + ' 格/' + k(g.bal[p]) : '已除名@' + R.deathT[p]}｜目标 ${String(names[target] ?? target).slice(0, 16)}#${target} ${g.alive[target] ? g.terr[target] + ' 格/' + k(g.bal[target]) : '已除名@' + R.deathT[target]}` +
    (watch.length ? '｜' + watch.map((q) => `${String(names[q] ?? q).slice(0, 14)}#${q} ${g.alive[q] ? g.terr[q] + '/' + k(g.bal[q]) : '已除名@' + R.deathT[q]}`).join('；') : ''));
  for (const d of done) console.log('     ' + d);
  if (track.length) console.log('     ' + track.join('；'));
}
