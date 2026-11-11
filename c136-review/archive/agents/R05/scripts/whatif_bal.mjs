// whatif_bal.mjs — 「差多少兵」的重放推演：在逐拍精确重放里，于某一拍给某个号加 X 个兵（走引擎 addBalance，受 150×地 的硬上限），
// 之后照旧执行录像里所有人的真实指令，看这个号在其后一段时间的地/兵和是否被除名。
// 这是一阶推演：加兵之后别人的指令不会随局面改变（真实对局里对手和队友都可能改主意），所以只看加兵后的短窗口（默认 300 拍）。
// 除名线用引擎自己的 peak（game.js aliveTick L1298-1308：地 ≤ iV(peak,4) 即除名；地低于 peak 时 peak 每拍降 max(1, iV(peak−地,1000)) 格）。
// 用法：
//   node scripts/whatif_bal.mjs <局> --bot leo_tx --at 2589 --add 0,30000,60000,100000 [--until 2900] [--watch 1,12]
//   --add 的第一项建议给 0（＝原样重放，作对照）；--watch 给玩家编号，逐档打印它们在 --until 拍的地/兵。
import { simulate, botIds } from './sim_replay.mjs';

const args = process.argv.slice(2);
const id = args[0];
const val = (k, d) => (args.includes(k) ? args[args.indexOf(k) + 1] : d);
const bot = val('--bot', null), at = +val('--at', 0), until = +val('--until', at + 300);
const adds = String(val('--add', '0')).split(',').map(Number);
const watch = String(val('--watch', '')).split(',').filter(Boolean).map(Number);
if (!id || !bot || !at) { console.error('用法见文件头'); process.exit(2); }
const k = (x) => (Math.abs(x) >= 1e6 ? (x / 1e6).toFixed(2) + 'M' : Math.round(x / 1000) + 'k');

console.log(`[差多少兵] ${id}：t=${at} 给 ${bot} 加兵（引擎 addBalance），其后照录像原样执行所有指令，看到 t=${until}`);
for (const X of adds) {
  let p = -1, added = 0, before = null, minTerr = 1e9, minT = -1, names = null, lastPeak = 0;
  const track = [];
  const R = simulate(id, {
    maxTick: until,
    onStart: (g, ctx) => { p = botIds(ctx.names, ctx.H, [bot]).get(bot); names = ctx.names; },
    onTick: (g, t) => {
      if (p < 0) return;
      if (g.alive[p]) lastPeak = g.peak[p];
      if (t === at) { before = [g.terr[p], g.bal[p], g.peak[p]]; added = X > 0 ? g.addBalance(p, X) : 0; }
      if (t >= at && g.alive[p] && g.terr[p] < minTerr) { minTerr = g.terr[p]; minT = t; }
      if (t >= at && (t - at) % 30 === 0) track.push(`${t}:${g.alive[p] ? g.terr[p] + '/' + k(g.bal[p]) : '已除名'}`);
    },
  });
  const g = R.g;
  if (p < 0) { console.log(`  找不到 ${bot}`); break; }
  const dead = R.deathT[p] >= 0 ? R.deathT[p] : -1;
  console.log(`  +${k(X)}（实际加上 ${k(added)}；加之前 ${before ? before[0] + ' 格/' + k(before[1]) + '，引擎 peak ' + before[2] + '（除名线 ' + Math.floor((before[2] + 0.5) / 4) + '）' : '-'}；末拍 peak ${lastPeak}（除名线 ${Math.floor((lastPeak + 0.5) / 4)}））→ ` +
    (dead >= 0 ? `t=${dead} 被除名` : `活到 t=${until}：${g.terr[p]} 格/${k(g.bal[p])}，其间地最低 ${minTerr}（t=${minT}）`) +
    (watch.length ? '｜' + watch.map((q) => `${String(names[q] ?? q).slice(0, 14)}#${q} ${g.alive[q] ? g.terr[q] + '/' + k(g.bal[q]) : '已除名@' + R.deathT[q]}`).join('；') : ''));
  console.log('     ' + track.join(' '));
}
