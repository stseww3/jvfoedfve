#!/usr/bin/env node
// verify_tail.mjs — verify 里「与真引擎重放没有一致到最后」的局，分歧出现之前那一拍场上是什么局面。
//
// 读 sim-v2/calib/verify/<局>.json，找出 truth.firstBadT ≥ 0 的局；把这一局的录像重放到最后一个一致的采样拍（truth.lastOkT），
// 记下：地最多的一队占全图陆地的几成、还在场的真人和已离场由内置 AI 托管的席位各几个、我方席位还在场几个。
// 写 sim-v2/calib/verify-tail.json（g0_report.mjs 的 verify 一节读它）。
// 用法（在 c136-review/agents/R06 下，经重计算闸门）：node sim-v2/tools/verify_tail.mjs
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { loadMatch, buildWorld, ReplayStepper } from '../lib/match.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const CALIB = path.resolve(HERE, '..', 'calib');
const out = {};
for (const f of fs.readdirSync(path.join(CALIB, 'verify')).sort()) {
  if (!f.endsWith('.json')) continue;
  const v = JSON.parse(fs.readFileSync(path.join(CALIB, 'verify', f), 'utf8'));
  if (!v.truth || !(v.truth.firstBadT >= 0)) continue;
  const mid = f.slice(0, -5), T = v.truth.lastOkT;
  const M = loadMatch(mid);
  const g = buildWorld(M);
  const st = new ReplayStepper(M, g);
  st.runSpawnPhase();
  while (g.t < T) { if (!st.step()) break; g.tick(); }
  const H = M.H, teamLand = new Map();
  let humansPresent = 0, humansHusk = 0, owned = 0;
  for (let p = 0; p < g.terr.length; p++) {
    if (!g.alive[p]) continue;
    owned += g.terr[p];
    const tm = g.teams ? g.teams[p] : 0;
    teamLand.set(tm, (teamLand.get(tm) || 0) + g.terr[p]);
    if (p < H) { if (g.state[p] === 2) humansHusk++; else humansPresent++; }
  }
  const [leadTeam, leadLand] = [...teamLand.entries()].sort((a, b) => b[1] - a[1])[0];
  const squadPresent = M.squad.filter((p) => g.alive[p] && g.state[p] !== 2).length;
  out[mid] = {
    t: g.t, replayTicks: M.replayTicks, firstBadT: v.truth.firstBadT, land: M.map.land, owned, leadTeam, leadLand,
    leadShareOfLand: +(leadLand / M.map.land).toFixed(4), leadShareOfOwned: +(leadLand / owned).toFixed(4),
    humansPresent, humansHusk, squadPresent, squad: M.squad.length, over: !!g.over,
  };
  console.log(`${mid}：t=${g.t}（录像 ${M.replayTicks} 拍，第一处不同 t=${v.truth.firstBadT}）地最多的队 ${leadTeam} 占全图陆地 ${(100 * leadLand / M.map.land).toFixed(1)}%、占已有主的地 ${(100 * leadLand / owned).toFixed(1)}%；在场真人 ${humansPresent}，离场托管 ${humansHusk}；我方在场 ${squadPresent}/${M.squad.length}`);
}
fs.writeFileSync(path.join(CALIB, 'verify-tail.json'), JSON.stringify(out, null, 1) + '\n');
console.log(`写入 sim-v2/calib/verify-tail.json（${Object.keys(out).length} 局）`);
