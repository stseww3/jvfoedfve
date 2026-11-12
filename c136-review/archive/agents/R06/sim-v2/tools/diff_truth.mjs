// diff_truth.mjs — 物理底座排查：重放到指定拍，把每个真人的 领土 / 兵力 与本机 out/<局>/sim_state.json（真引擎重放逐 30 拍采样）逐人对比，列出不同的人。
// 只在有 out/<局>/sim_state.json 的机器上能跑（那份文件不随仓库走）；随仓库走的是 sim-v2/truth/ 里的指纹，由 --mode verify 核对。
// 用法：node sim-v2/tools/diff_truth.mjs <局号> <起始拍> [终止拍]
import fs from 'node:fs';
import path from 'node:path';
import { loadMatch, buildWorld, ReplayStepper, SIMV2 } from '../lib/match.mjs';

const [mid, a, b] = process.argv.slice(2);
const from = Number(a || 0), to = Number(b || from);
const st0 = JSON.parse(fs.readFileSync(path.join(SIMV2, '..', 'out', mid, 'sim_state.json'), 'utf8'));
const idx = new Map(st0.ticks.map((t, i) => [t, i]));
const M = loadMatch(mid);
const g = buildWorld(M);
const st = new ReplayStepper(M, g);
st.runSpawnPhase();
let shown = 0;
while (!g.over && g.t <= to) {
  const i = idx.get(g.t);
  if (i !== undefined && g.t >= from) {
    const bad = [];
    for (let p = 0; p < M.H; p++) {
      const tt = g.alive[p] ? g.terr[p] : 0, bb = tt > 0 ? g.bal[p] : 0;
      const et = st0.hum[p].terr[i], eb = st0.hum[p].bal[i];
      if (tt !== et || bb !== (et > 0 ? eb : 0)) bad.push(`#${p} ${M.names[p]} 队${M.ta ? M.ta.fX[p] : 0} 领土 ${tt}↔${et} 兵 ${bb}↔${eb}${g.isBot && g.isBot(p) ? ' 空壳' : ''}`);
    }
    console.log(`t=${g.t}：${bad.length ? bad.length + ' 人不同' : '全同'}`);
    for (const s of bad.slice(0, 12)) console.log('   ' + s);
    if (bad.length && ++shown >= 3) break;
  }
  if (!st.step()) break;
  g.tick();
}
