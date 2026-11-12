#!/usr/bin/env node
// replay_dump_all.mjs — 把全部（或指定）对局包的 replay.txt 解码成逐拍命令流，供 Python 的模式检测脚本（pattern_scan.py、spawn_exec.py）读取。
//   只解码，不建地图、不跑引擎（每局几十毫秒）。解码函数来自 replay_cmds.mjs（逐字取自 c136-data/src/sim/tools/c102-replay-lib.mjs）。
// 产物（默认 /tmp/c136-r05/cmds/，与 `replay_cmds.mjs <局> --out` 同格式）：
//   <局>.tsv        tick  id  kind  player  name  a  b  targetName
//                   （id：0 出生(格号) 1 陆攻(pct,目标) 2 捐兵(pct,对象) 3 出船(pct,水格:方向) 4 追击/召回 5 撤回 8/9 离场）
//   headers.json    { <局>: { humans, players, gameMode, battleRoyaleMode, selectableSpawn, totalTicks, spawnSteps, names:[真人名…] } }
// 用法：node scripts/replay_dump_all.mjs [局…] [--out 目录]        不给局号 = bundles/ 下全部有 replay.txt 的局
import fs from 'node:fs';
import path from 'node:path';
import { loadReplay, timeline } from './replay_cmds.mjs';

const DATA = process.env.C136_DATA || '/agent/repos/c136-data';
const BUN = process.env.C136_BUNDLES || 'bundles'; // 验证集：C136_BUNDLES=validation_bundles
const KIND = { 0: 'spawn', 1: 'attack', 2: 'donate', 3: 'boat', 4: 'chase', 5: 'retreat', 6: 'c6', 7: 'c7', 8: 'leave8', 9: 'leave9', 10: 'c10' };
const args = process.argv.slice(2);
const outDir = args.includes('--out') ? args[args.indexOf('--out') + 1] : (process.env.C136_CMDS || '/tmp/c136-r05/cmds');
let ids = args.filter((a, i) => !a.startsWith('--') && args[i - 1] !== '--out');
if (!ids.length) ids = fs.readdirSync(path.join(DATA, BUN)).filter((d) => fs.existsSync(path.join(DATA, BUN, d, 'replay.txt'))).sort();
fs.mkdirSync(outDir, { recursive: true });
const hp = path.join(outDir, 'headers.json');
const headers = fs.existsSync(hp) ? JSON.parse(fs.readFileSync(hp, 'utf8')) : {};
let ok = 0, bad = 0;
for (const mid of ids) {
  try {
    const d = loadReplay(mid);
    const vu = d.vu, tl = timeline(d), H = vu.humanCount;
    const names = vu.playerNamesData ? Array.from(vu.playerNamesData.data).slice(0, H) : [];
    const nm = (p) => (p >= 512 ? 'NEUTRAL' : p < H ? (names[p] ?? `H#${p}`) : `bot#${p}`);
    const lines = ['tick\tid\tkind\tplayer\tname\ta\tb\ttargetName'];
    for (const c of tl.cmds) {
      let b = c.dZ, tn = '';
      if (c.id === 1 || c.id === 2) tn = nm(c.dZ);
      else if (c.id === 5) tn = nm(c.dX);
      else if (c.id === 3) b = `${c.dZ >> 3}:${c.dZ & 7}`;
      lines.push([c.tick, c.id, KIND[c.id] ?? ('c' + c.id), c.player, nm(c.player), c.dX, b, tn].join('\t'));
    }
    fs.writeFileSync(path.join(outDir, `${mid}.tsv`), lines.join('\n') + '\n');
    headers[mid] = { humans: H, players: vu.playerCount, gameMode: vu.gameMode, battleRoyaleMode: vu.battleRoyaleMode, selectableSpawn: vu.selectableSpawn,
      totalTicks: tl.totalTicks, spawnSteps: tl.spawnSteps, names };
    ok++;
  } catch (e) {
    headers[mid] = { error: String(e.message || e) };
    bad++;
  }
}
fs.writeFileSync(hp, JSON.stringify(headers));
console.log(`解码 ${ok} 局，失败 ${bad} 局 → ${outDir}`);
