#!/usr/bin/env node
// rules_header.mjs — 每局录像头里的规则开关：对局模式、是否「禁全兵」（引擎 noFullSend：game.js L58，
//   = opts.noFullSend 或 battleRoyaleMode===1）、真人数、玩家数、队伍数。只建局不重放（maxTick=-1e9）。
//   用途：核对策略里的 isNoFullSend（Policy.updateShadowQuota 的推断）与引擎真实规则是否一致。
// 用法：node scripts/rules_header.mjs A014 A021 …  [--json FILE]      （B 组前面加 C136_DATA=/tmp/c136-r05/overlay）
import fs from 'node:fs';
import { simulate } from './sim_replay.mjs';

const args = process.argv.slice(2);
const jo = args.includes('--json') ? args[args.indexOf('--json') + 1] : null;
const ids = args.filter((a, i) => !a.startsWith('--') && args[i - 1] !== '--json');
const out = {};
for (const mid of ids) {
  try {
    simulate(mid, {
      maxTick: -1e9,
      onStart(g, { d, T, H }) {
        const vu = d.vu;
        out[mid] = {
          gameMode: vu.gameMode, battleRoyaleMode: vu.battleRoyaleMode, engineNoFullSend: g.noFullSend, humans: H, players: vu.playerCount,
          teams: T ? T.nTeamsEngine : 0, selectableSpawn: !!vu.selectableSpawn, isZombieMode: !!vu.isZombieMode,
        };
      },
    });
  } catch (e) {
    out[mid] = { error: String(e.message || e) };
  }
  console.log(mid, JSON.stringify(out[mid]));
}
if (jo) fs.writeFileSync(jo, JSON.stringify(out));
