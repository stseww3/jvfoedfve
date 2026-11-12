// dump_cmds.mjs — 列出录像里某段拍、某些席位的指令，以及本模拟器执行它们的结果（ok = 生效，rec = 真引擎会写进录像）。
// 用法：node sim-v2/tools/dump_cmds.mjs <局号> <起始拍> <终止拍> [席位,席位…]
import { loadMatch, buildWorld, ReplayStepper, execRecorded } from '../lib/match.mjs';

const [mid, a, b, who] = process.argv.slice(2);
const from = Number(a || 0), to = Number(b || from);
const only = who ? new Set(who.split(',').map(Number)) : null;
const M = loadMatch(mid);
const g = buildWorld(M);
const st = new ReplayStepper(M, g);
st.runSpawnPhase();
st.exec = (c) => {
  const w = g;
  const show = w.t >= from && w.t <= to && (!only || only.has(c.player));
  const p = c.player;
  const before = show ? { bal: w.bal[p], terr: w.terr[p] } : null;
  const r = execRecorded(w, c);
  if (show) {
    const tgt = c.id === 1 || c.id === 2 ? c.dZ : '';
    console.log(`t=${w.t} #${p} ${M.names[p]} 指令 ${c.id}（${c.dX}, ${c.dZ}）执行前 兵 ${before.bal} 领土 ${before.terr} → ok=${r.ok} rec=${r.rec} 执行后 兵 ${w.bal[p]}` +
      (typeof tgt === 'number' && tgt >= 0 && tgt < w.bal.length ? `；对象 #${tgt} ${M.names[tgt] ?? ''} 兵 ${w.bal[tgt]} 领土 ${w.terr[tgt]} 活 ${w.alive[tgt]} 空壳 ${w.isBot && w.isBot(tgt) ? 1 : 0}` : ''));
  }
  return r;
};
while (!g.over && g.t <= to) {
  if (!st.step()) break;
  g.tick();
}
