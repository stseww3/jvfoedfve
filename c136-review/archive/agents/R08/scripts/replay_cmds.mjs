#!/usr/bin/env node
// replay_cmds.mjs — 把对局包里的 replay.txt 解码成「逐拍指令流」（不做地图模拟：数据包里没有地图 .bin）。
//
//   bash c136-review/tools/run-heavy.sh node c136-review/agents/R08/scripts/replay_cmds.mjs <matchId> [...]
//
// 输出 c136-review/agents/R08/out/<matchId>/replay_cmds.json：
//   { meta:{humanCount, numberTeams, selectedPlayer, spawnSteps, lastTick, names[]}, cmds:[[t,id,player,dX,dZ],...] }
// 拍号规则与 src/sim/tools/pure-node-dissect.mjs 一致：出生阶段 jJ+1 步（真人<=2:30，<=50:40，否则 50），
// 之后每个回放步（一批指令或一个空步）推进 1 拍；出生阶段的指令记 t=-1。
// 指令号：0 选出生点（dX=y*W+x）；1 陆攻(pct,target)；2 捐款(pct,target)；3 发船(pct, water<<3|dir)；
//         4 追船/召回；5 撤军(target)；8/9 离开。
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { decodeReplay } from '/agent/repos/c136-data/src/sim/tools/c102-replay-lib.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const OUT = path.resolve(HERE, '..', 'out');
const DATA = process.env.C136_DATA || '/agent/repos/c136-data';

for (const mid of process.argv.slice(2)) {
  const p = path.join(DATA, 'bundles', mid, 'replay.txt');
  if (!fs.existsSync(p)) {
    console.log(`${mid}: 无 replay.txt`);
    continue;
  }
  const d = decodeReplay(fs.readFileSync(p, 'utf8'));
  const vu = d.vu;
  const H = vu.humanCount;
  const jJ = H <= 2 ? 30 : H <= 50 ? 40 : 50;
  let iv = 0, iw = 0, ix = 0, iy = 0, t = -1;
  const out = [];
  const step = () => {
    if (iv >= d.ja.length) return false;
    const jZ = d.ja[iv];
    if (d.jY[iv]) {
      for (let a = iw; a < iw + jZ; a++) {
        const c = d.cmds[a];
        out.push([t, c.id, c.player, c.dX, c.dZ]);
      }
      iw += jZ;
      iv++;
    } else if (++ix >= jZ) {
      iv++;
      ix = 0;
    }
    return true;
  };
  let spawnSteps = 0;
  if (vu.selectableSpawn) {
    while (iy <= jJ) {
      if (!step()) break;
      spawnSteps++;
      iy++;
    }
  }
  t = 0;
  while (step()) t++;
  const byId = {};
  for (const c of out) byId[c[1]] = (byId[c[1]] || 0) + 1;
  const meta = {
    matchId: mid, humanCount: H, playerCount: vu.playerCount, numberTeams: vu.numberTeams,
    selectedPlayer: vu.selectedPlayer, mapType: vu.mapType, mapProceduralIndex: vu.mapProceduralIndex,
    mapRealisticIndex: vu.mapRealisticIndex, mapSeed: vu.mapSeed, spawningSeed: vu.spawningSeed,
    isContest: vu.isContest, battleRoyaleMode: vu.battleRoyaleMode, gameMode: vu.gameMode, playerMode: vu.playerMode,
    spawnSteps, lastTick: t, cmdCount: out.length, byId,
    names: vu.playerNamesData ? Array.from(vu.playerNamesData).slice(0, H) : null,
    colors: vu.colorsData ? Array.from(vu.colorsData).slice(0, H) : null,
  };
  fs.mkdirSync(path.join(OUT, mid), { recursive: true });
  fs.writeFileSync(path.join(OUT, mid, 'replay_cmds.json'), JSON.stringify({ meta, cmds: out }));
  console.log(`${mid}: humans=${H} teams=${vu.numberTeams} selected=${vu.selectedPlayer} spawnSteps=${spawnSteps} lastTick=${t} cmds=${out.length} byId=${JSON.stringify(byId)}`);
}
