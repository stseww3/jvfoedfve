// whatif_drop.mjs — 「同一个决定只落地一次」的重放推演：在逐拍精确重放里，把某个号在某一拍执行的陆攻/出船指令只留前 N 条、
// 其余丢掉（skipCmd），之后照旧执行录像里所有人的真实指令，看这个号其后的地/兵和是否被除名。
// 这是一阶推演：丢掉指令之后别人的指令不会随局面改变，该号自己后面的指令也照录像原样执行（按比例出兵的指令会因为存兵变多而出得更多）。
// 所以只看丢掉之后的短窗口，并且只用来回答「同一批里重复的那几条到底花掉了什么」。
// 用法：
//   node scripts/whatif_drop.mjs <局> --drop kaito9:1533:1,kaito9:1540:0 [--until 2400] [--watch 66,63] [--step 100]
//   --drop 号:拍:保留条数（该号在该拍执行的 陆攻(id=1)/出船(id=3) 指令按执行顺序只留前 N 条）
import { simulate, botIds } from './sim_replay.mjs';

const args = process.argv.slice(2);
const id = args[0];
const val = (k, d) => (args.includes(k) ? args[args.indexOf(k) + 1] : d);
const drops = String(val('--drop', '')).split(',').filter(Boolean).map((s) => { const [bot, t, keep] = s.split(':'); return { bot, t: +t, keep: +keep }; });
const until = +val('--until', Math.max(...drops.map((d) => d.t)) + 600);
const watch = String(val('--watch', '')).split(',').filter(Boolean).map(Number);
const STEP = +val('--step', 100);
if (!id || !drops.length) { console.error('用法见文件头'); process.exit(2); }
const k = (x) => (Math.abs(x) >= 1e6 ? (x / 1e6).toFixed(2) + 'M' : Math.round(x / 1000) + 'k');
const bots = [...new Set(drops.map((d) => d.bot))];
const t0 = Math.min(...drops.map((d) => d.t));

console.log(`[只落地一次] ${id}：${drops.map((d) => `${d.bot} t=${d.t} 只留前 ${d.keep} 条`).join('；')}，其后照录像原样执行所有指令，看到 t=${until}`);
for (const mode of ['原样', '丢掉重复']) {
  let pid = null, names = null;
  const seen = new Map(); // `${p}|${t}` → 已执行条数
  let dropped = 0, droppedTroops = 0;
  const track = new Map(bots.map((b) => [b, []]));
  const R = simulate(id, {
    maxTick: until,
    onStart: (g, ctx) => { pid = botIds(ctx.names, ctx.H, bots); names = ctx.names; },
    skipCmd: (c, g) => {
      if (mode === '原样' || !pid) return false;
      if (c.id !== 1 && c.id !== 3) return false;
      for (const d of drops) {
        if (g.t !== d.t || pid.get(d.bot) !== c.player) continue;
        const key = `${c.player}|${g.t}`;
        const n = seen.get(key) || 0;
        seen.set(key, n + 1);
        if (n >= d.keep) { dropped++; return true; }
      }
      return false;
    },
    onTick: (g, t) => {
      if (!pid || t < t0 - 1) return;
      if ((t - t0) % STEP === 0 || t === until) for (const b of bots) { const p = pid.get(b); track.get(b).push(`${t}:${g.alive[p] ? g.terr[p] + '/' + k(g.bal[p]) : '已除名'}`); }
    },
  });
  const g = R.g;
  console.log(`  【${mode}】${mode === '原样' ? '' : `丢掉 ${dropped} 条｜`}` + bots.map((b) => { const p = pid.get(b); return `${b} ${R.deathT[p] >= 0 ? '除名@' + R.deathT[p] : g.terr[p] + ' 格/' + k(g.bal[p])}`; }).join('；') +
    (watch.length ? '｜' + watch.map((q) => `${String(names[q] ?? q).slice(0, 14)}#${q} ${g.alive[q] ? g.terr[q] + '/' + k(g.bal[q]) : '已除名@' + R.deathT[q]}`).join('；') : ''));
  for (const b of bots) console.log(`     ${b}: ` + track.get(b).join(' '));
}
