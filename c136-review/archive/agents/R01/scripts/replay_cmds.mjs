// replay_cmds.mjs — 把录像指令流展开成 CSV（不模拟）：
//   node replay_cmds.mjs <matchId> [--replay 同局另一个包]   → out/<matchId>/replay_cmds.csv + 概要打印
// 列：step,tick,id,kind,player,pname,dX,dZ,tname
//   tick = step - (spawnSteps+1)；联机指令按服务器回合（7 拍）成包到达，执行拍通常比策略发令拍晚 ~7-14 拍。
//   引擎只在通过前置校验后才把指令写入录像：捐款(id=2)要过余额/上限/配额(ao.ei)全部校验才记录（live_game_js.js qj.qv），
//   所以录像里的捐款 = 引擎实际接受的捐款；陆攻(id=1)在付款与战线生成之前记录（qj.i6）。
import fs from 'node:fs';
import path from 'node:path';
import { loadReplay } from './replay_decode.mjs';

const KIND = { 0: 'spawn', 1: 'attack', 2: 'donate', 3: 'boat', 4: 'chase', 5: 'retreat', 6: 'emoji', 7: 'vote', 8: 'surrender', 9: 'leave', 10: 'mtn' };
const mid = process.argv[2];
// --replay <别的局号>：B 组包自己的 replay.txt 是截断的（只有出生阶段），用同局 A 包的录像，结果仍写到 out/<matchId>/
const rmid = process.argv.includes('--replay') ? process.argv[process.argv.indexOf('--replay') + 1] : mid;
const { d, H, jJ, cmds, steps } = loadReplay(rmid);
const names = Array.from(d.vu.playerNamesData || []);
const nm = (p) => (p === 512 ? 'NEUTRAL' : p < H ? (names[p] ?? `H${p}`) : `bot#${p}`);
const outDir = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..', 'out', mid);
fs.mkdirSync(outDir, { recursive: true });
const rows = ['step,tick,id,kind,player,pname,dX,dZ,tname'];
const q = (s) => '"' + String(s).replace(/"/g, '""') + '"';
for (const c of cmds) {
  const tick = c.step - (jJ + 1);
  let tname = '';
  if (c.id === 1 || c.id === 2) tname = nm(c.dZ);
  if (c.id === 5 && c.dX !== 513) tname = nm(Math.min(c.dX, 512));
  if (c.id === 10) tname = nm(c.dX % 1024);
  rows.push([c.step, tick, c.id, KIND[c.id] ?? '?', c.player, q(nm(c.player)), c.dX, c.dZ, q(tname)].join(','));
}
fs.writeFileSync(path.join(outDir, 'replay_cmds.csv'), rows.join('\n') + '\n');
fs.writeFileSync(path.join(outDir, 'replay_meta.json'), JSON.stringify({ matchId: mid, replayOf: rmid, humans: H, players: d.vu.playerCount, numberTeams: d.vu.numberTeams,
  spawnSteps: jJ, totalSteps: steps, lastTick: steps - (jJ + 1), cmds: cmds.length, selectedPlayer: d.vu.selectedPlayer, names: names.slice(0, H) }, null, 1));
console.log(`${mid}: humans=${H} teams=${d.vu.numberTeams} steps=${steps} lastTick=${steps - (jJ + 1)} cmds=${cmds.length} -> ${outDir}/replay_cmds.csv`);
