// 临时：各局我方席位的页面寿命 / 停摆 / 离场 / 出局拍
import fs from 'node:fs';
import { loadMatch } from '../lib/match.mjs';
const mids = fs.readFileSync(new URL('../tools/arena_calib_list20.txt', import.meta.url), 'utf8').split('\n').map((l) => l.trim().split(/\s+/)[0]).filter((x) => x && !x.startsWith('#'));
for (const mid of mids) {
  const M = loadMatch(mid);
  const rows = [];
  let doomedBy = { 630: 0, 1071: 0, 1530: 0, 2142: 0, 3210: 0, 4284: 0 };
  for (const p of M.squad) {
    const pe = M.pageEnd.get(p), dt = M.deathT ? (M.deathT[p] ?? -1) : null, lv = M.leaveT.get(p) ?? -1, lc = M.lastCmd.get(p) ?? -1;
    const dm = M.doomed.has(p);
    if (dm) for (const k of Object.keys(doomedBy)) if (pe < +k) doomedBy[k]++;
    rows.push(`${p}:${dm ? 'D' : ''}pe${pe}/lc${lc}/dt${dt}/lv${lv}`);
  }
  console.log(mid, 'H', M.H, 'squad', M.squad.length, 'ticks', M.replayTicks, 'deathT?', !!M.deathT, 'doomedBy', JSON.stringify(doomedBy));
  if (process.argv.includes('--rows')) console.log('   ', rows.join('  '));
}
