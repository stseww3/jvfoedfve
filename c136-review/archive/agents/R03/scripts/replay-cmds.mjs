#!/usr/bin/env node
// replay-cmds.mjs — 把对局包里的 replay.txt 解码成「逐拍指令表」（不重放地图，只解码指令流）。
//
// 用法：node replay-cmds.mjs <matchId> [...]        输出到 ../out/cache/<matchId>-replay.json
//       node replay-cmds.mjs --all-r03               R03 的 14 局
// 解码器直接用 c136-data 镜像里的 src/sim/tools/c102-replay-lib.mjs（decodeReplay），本脚本只做拍号换算。
//
// 拍号换算（与 c102-replay-lib.mjs 的 makeStepper 一致）：
//   录像按「步」记录；前 jJ+1 步是选点阶段（真人数 H<=2:30，<=50:40，否则 50），之后每一步 = 一拍，
//   指令在该拍的 n8() 之前执行。所以 第 s 步（s>=jJ+1）的指令执行于局内拍 t = s-(jJ+1)。
//
// 录像只收「通过了引擎校验」的指令（qj.* 里的 bC.rg.rh 调用点）：
//   id=1 陆攻：通过了存活/目标/报价/空槽校验（但可能在其后的战线生成 jt 处失败，那种情况不扣兵）
//   id=2 捐款：通过了全部校验（含受捐额度 ao.ei）→ 录像里的捐款 = 实际到账的捐款
//   id=3 发船、id=4 追船(849=召回)、id=5 撤回(513=发起和平投票)、id=6 表情、id=7 和平投票、
//   id=8 投降离开、id=9 掉线离开、id=10 翻山进攻、id=0 选点
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const DATA = process.env.C136_DATA || '/agent/repos/c136-data';
const { decodeReplay } = await import(path.join(DATA, 'src/sim/tools/c102-replay-lib.mjs'));
const HERE = path.dirname(fileURLToPath(import.meta.url));
const OUT = path.join(HERE, '..', 'out', 'cache');
fs.mkdirSync(OUT, { recursive: true });

const R03 = ['A051', 'A087', 'A066', 'A025', 'A045', 'A067', 'A071', 'A090', 'A042', 'A046', 'A041', 'A010', 'A011', 'B038'];
let ids = process.argv.slice(2);
if (ids[0] === '--all-r03') ids = R03;
if (!ids.length) {
  console.log('用法：node replay-cmds.mjs <matchId> [...] | --all-r03');
  process.exit(1);
}

for (const mid of ids) {
  const file = path.join(DATA, 'bundles', mid, 'replay.txt');
  if (!fs.existsSync(file)) {
    console.log(`${mid}: 没有 replay.txt`);
    continue;
  }
  const d = decodeReplay(fs.readFileSync(file, 'utf8'));
  const vu = d.vu;
  const H = vu.humanCount;
  const jJ = H <= 2 ? 30 : H <= 50 ? 40 : 50;
  const cmds = [];
  let step = 0;
  let iw = 0;
  for (let iv = 0; iv < d.ja.length; iv++) {
    const n = d.ja[iv];
    if (d.jY[iv]) {
      const t = step - (jJ + 1);
      for (let k = iw; k < iw + n; k++) {
        const c = d.cmds[k];
        cmds.push([t, c.id, c.player, c.dX, c.dZ]);
      }
      iw += n;
      step += 1;
    } else {
      step += n;
    }
  }
  const byId = {};
  for (const c of cmds) byId[c[1]] = (byId[c[1]] || 0) + 1;
  const out = {
    matchId: mid,
    humans: H,
    players: vu.playerCount,
    numberTeams: vu.numberTeams,
    gameMode: vu.gameMode,
    playerMode: vu.playerMode,
    selectedPlayer: vu.selectedPlayer,
    mapType: vu.mapType,
    mapRealisticIndex: vu.mapRealisticIndex,
    mapProceduralIndex: vu.mapProceduralIndex,
    mapSeed: vu.mapSeed,
    spawnSteps: jJ + 1,
    totalTicks: step - (jJ + 1),
    names: vu.playerNamesData ? Array.from(vu.playerNamesData).slice(0, H) : [],
    colors: vu.colorsData ? Array.from(vu.colorsData).slice(0, H) : [],
    cmdCountById: byId,
    cmds,
  };
  fs.writeFileSync(path.join(OUT, `${mid}-replay.json`), JSON.stringify(out));
  console.log(`${mid}: H=${H} players=${vu.playerCount} teams=${vu.numberTeams} ticks=${out.totalTicks} cmds=${cmds.length} byId=${JSON.stringify(byId)}`);
}
