#!/usr/bin/env node
// replay_decode.mjs — 把对局包里的 replay.txt 解码成结构化 JSON（只解码，不重放、不需要地图文件）。
//
// 用法：
//   bash c136-review/tools/run-heavy.sh node c136-review/agents/R06/scripts/replay_decode.mjs <matchId> [outDir]
// 读  /agent/repos/c136-data/bundles/<matchId>/replay.txt
// 写  <outDir>/<matchId>/replay_decoded.json   （默认 outDir = c136-review/agents/R06/out）
//
// 解码器与 /agent/repos/c136-data/src/sim/tools/c102-replay-lib.mjs 的 decodeReplay 同构（位流格式一致），
// 这里只多做一件事：按 makeStepper 的步进规则给每条指令标上「局内拍号」。
//   - 出生阶段：前 jJ+1 步（H<=2:30；H<=50:40；否则 50）记为 phase="spawn"，step=0..jJ
//   - 之后每一步对应一拍：第 k 步（从 0 起）里的指令在 g.t=k 时执行
// 指令 id：0 选点(dX=像素下标)；1 陆攻(dX=pct,dZ=目标,512=无主地)；2 捐款(dX=pct,dZ=收款人)；
//          3 发船(dX=pct,dZ=水格<<3|方向)；4 追船/召回(dX=849 为召回)；5 撤回(dX=目标)；8/9 离开；其余原样保留。
import fs from 'node:fs';
import path from 'node:path';

const DATA = '/agent/repos/c136-data/bundles';

export function decodeReplay(raw) {
  let ga = raw.trim();
  const eq = ga.indexOf('=');
  if (eq >= 0) ga = ga.substring(eq + 1);
  ga = ga.replace(/[^a-zA-Z0-9_\-]/g, '-');
  const abv = new Uint8Array(78);
  abv[50] = 37;
  for (let i = 0; i < 10; i++) abv[i + 3] = i + 1;
  for (let i = 0; i < 26; i++) { abv[i + 20] = i + 11; abv[i + 52] = i + 38; }
  const aCT = new Uint8Array(ga.length);
  for (let i = 0; i < ga.length; i++) aCT[i] = abv[ga.charCodeAt(i) - 45];
  const totalBits = 6 * aCT.length;
  const mH = new Uint8Array((totalBits + 7) >> 3);
  let wp = 0;
  for (let i = 0; i < aCT.length; i++) {
    const v = aCT[i];
    for (let b = 5; b >= 0; b--, wp++) mH[wp >> 3] |= ((v >> b) & 1) << (7 - (wp & 7));
  }
  let a9 = 0;
  let overrun = false;
  const i2 = (size) => {
    let h2 = 0;
    const bz = a9 + size - 1;
    if (bz >= totalBits) overrun = true;
    for (let a1 = a9; a1 <= bz; a1++) h2 = (h2 * 2) + ((mH[a1 >> 3] >> (7 - (a1 & 7))) & 1);
    a9 += size;
    return h2 >>> 0;
  };
  const aHl = (aEd) => {
    const len = i2(aEd);
    let s = '';
    for (let i = 0; i < len; i++) s += String.fromCharCode(i2(16));
    return s;
  };
  const aHn = (aEd, aY3, aZd) => {
    const fe = i2(aEd);
    if (!fe) return null;
    const dC = [];
    for (let i = 0; i < fe; i++) dC.push(i2(aY3));
    return { stated: fe, padTo: aZd, data: dC };
  };
  const aHo = (aEd, aY6, aZd) => {
    const fe = i2(aEd);
    if (!fe) return null;
    const dC = [];
    for (let i = 0; i < fe; i++) dC.push(aHl(aY6));
    return { stated: fe, padTo: aZd, data: dC };
  };
  const version = i2(12), vs = i2(12), statedSize = i2(31);
  const vu = { version, vs, statedSize };
  vu.mapType = i2(2);
  vu.mapProceduralIndex = i2(8);
  vu.mapRealisticIndex = i2(8);
  vu.mapSeed = i2(14);
  vu.mapName = aHl(5);
  if (vu.mapType === 2) { const aDc = i2(30); a9 += 6 * aDc; }
  vu.passableWater = i2(1);
  vu.passableMountains = i2(1);
  vu.playerCount = i2(10);
  vu.humanCount = i2(10);
  vu.selectedPlayer = i2(9);
  vu.gameMode = i2(1);
  vu.playerMode = i2(2);
  vu.battleRoyaleMode = i2(2);
  vu.numberTeams = i2(4);
  vu.isZombieMode = i2(1);
  vu.isContest = i2(1);
  vu.isReplay = i2(1);
  vu.elo = aHn(2, 14, 2);
  vu.colorsType = i2(1);
  vu.colorsPersonalized = i2(1);
  vu.colorsData = aHn(10, 18, 512);
  vu.selectableColor = i2(1);
  vu.teamPlayerCount = aHn(4, 10, 9);
  vu.neutralBots = i2(1);
  vu.botDifficultyType = i2(2);
  vu.botDifficultyValue = i2(4);
  vu.botDifficultyTeam = aHn(4, 4, 9);
  vu.botDifficultyData = aHn(10, 4, 512);
  vu.spawningType = i2(2);
  vu.spawningSeed = i2(14);
  vu.spawningData = aHn(11, 12, 1024);
  vu.selectableSpawn = i2(1);
  vu.playerNamesType = i2(2);
  vu.playerNamesData = aHo(10, 5, 512);
  vu.selectableName = i2(1);
  vu.aIncomeType = i2(2); vu.aIncomeValue = i2(8); vu.aIncomeData = aHn(10, 8, 512);
  vu.tIncomeType = i2(2); vu.tIncomeValue = i2(8); vu.tIncomeData = aHn(10, 8, 512);
  vu.iIncomeType = i2(2); vu.iIncomeValue = i2(8); vu.iIncomeData = aHn(10, 8, 512);
  vu.sResourcesType = i2(2); vu.sResourcesValue = i2(11); vu.sResourcesData = aHn(10, 11, 512);
  vu.nA = aHn(10, 30, 0);
  const headerBits = a9;
  const ek = i2(5), aHp = i2(30), aHq = i2(30);
  const cmds = [];
  for (let i = 0; i < aHp && !overrun; i++) {
    const id = i2(4), player = i2(9);
    let dX = 0, dZ = 0;
    if (id === 0) dX = i2(22);
    else if (id === 1) { dX = i2(10); dZ = i2(10); }
    else if (id === 2) { dX = i2(10); dZ = i2(9); }
    else if (id === 3) { dX = i2(10); dZ = i2(27); }
    else if (id === 4) { dX = i2(10); dZ = i2(16); }
    else if (id === 5 || id === 6) dX = i2(10);
    else if (id === 7) dX = i2(1);
    else if (id === 10) { dX = i2(20); dZ = i2(22); }
    cmds.push({ id, player, dX, dZ });
  }
  const cmdBitsEnd = a9;
  const jY = [], ja = [];
  for (let i = 0; i < aHq && !overrun; i++) {
    jY.push(i2(1));
    ja.push(i2(ek));
  }
  return { vu, ek, statedCmds: aHp, statedSteps: aHq, cmds, jY, ja, bits: { total: totalBits, header: headerBits, cmdEnd: cmdBitsEnd, end: a9, overrun } };
}

// 给每条指令标拍号（与 makeStepper.step / runSpawnPhase 同步）。
export function timeline(d) {
  const H = d.vu.humanCount;
  const jJ = H <= 2 ? 30 : H <= 50 ? 40 : 50;
  const out = [];
  let iv = 0, iw = 0, ix = 0;
  const step = (tag) => {
    if (iv >= d.ja.length) return false;
    const jZ = d.ja[iv];
    if (d.jY[iv]) {
      for (let a1 = iw; a1 < iw + jZ && a1 < d.cmds.length; a1++) out.push({ ...tag, ...d.cmds[a1], idx: a1 });
      iw += jZ;
      iv++;
    } else if (++ix >= jZ) {
      iv++;
      ix = 0;
    }
    return true;
  };
  let spawnSteps = 0;
  if (d.vu.selectableSpawn) {
    for (let iy = 0; iy <= jJ; iy++) {
      if (!step({ phase: 'spawn', step: iy, t: 0 })) break;
      spawnSteps++;
    }
  }
  let t = 0;
  while (step({ phase: 'game', t })) t++;
  return { cmds: out, lastTick: t, spawnSteps, consumedCmds: iw };
}

function main() {
  const matchId = process.argv[2];
  if (!matchId) {
    console.error('用法：node replay_decode.mjs <matchId> [outDir]');
    process.exit(2);
  }
  const outRoot = process.argv[3] || path.resolve(path.dirname(new URL(import.meta.url).pathname), '..', 'out');
  const src = path.join(DATA, matchId, 'replay.txt');
  if (!fs.existsSync(src)) {
    console.log(`${matchId}: 没有 replay.txt`);
    process.exit(0);
  }
  const raw = fs.readFileSync(src, 'utf8');
  const d = decodeReplay(raw);
  const tl = timeline(d);
  const names = d.vu.playerNamesData ? d.vu.playerNamesData.data : [];
  const byId = {};
  for (const c of tl.cmds) byId[c.id] = (byId[c.id] || 0) + 1;
  const res = {
    matchId,
    replayChars: raw.trim().length,
    bits: d.bits,
    settings: {
      version: d.vu.version, vs: d.vu.vs, statedSize: d.vu.statedSize,
      mapType: d.vu.mapType, mapProceduralIndex: d.vu.mapProceduralIndex, mapRealisticIndex: d.vu.mapRealisticIndex,
      mapSeed: d.vu.mapSeed, mapName: d.vu.mapName,
      playerCount: d.vu.playerCount, humanCount: d.vu.humanCount, selectedPlayer: d.vu.selectedPlayer,
      gameMode: d.vu.gameMode, playerMode: d.vu.playerMode, battleRoyaleMode: d.vu.battleRoyaleMode,
      numberTeams: d.vu.numberTeams, isReplay: d.vu.isReplay,
      teamPlayerCount: d.vu.teamPlayerCount, spawningType: d.vu.spawningType, spawningSeed: d.vu.spawningSeed,
      selectableSpawn: d.vu.selectableSpawn, playerNamesType: d.vu.playerNamesType,
      botDifficultyType: d.vu.botDifficultyType, botDifficultyValue: d.vu.botDifficultyValue,
      neutralBots: d.vu.neutralBots,
      elo: d.vu.elo, nA: d.vu.nA,
      spawningDataStated: d.vu.spawningData ? d.vu.spawningData.stated : 0,
      colorsDataStated: d.vu.colorsData ? d.vu.colorsData.stated : 0,
    },
    names,
    colors: d.vu.colorsData ? d.vu.colorsData.data : [],
    colorsType: d.vu.colorsType, colorsPersonalized: d.vu.colorsPersonalized,
    statedCmds: d.statedCmds, statedSteps: d.statedSteps, decodedCmds: d.cmds.length,
    consumedCmds: tl.consumedCmds, spawnSteps: tl.spawnSteps, lastTick: tl.lastTick,
    cmdCountById: byId,
    cmds: tl.cmds,
  };
  const outDir = path.join(outRoot, matchId);
  fs.mkdirSync(outDir, { recursive: true });
  fs.writeFileSync(path.join(outDir, 'replay_decoded.json'), JSON.stringify(res));
  console.log(`${matchId}: chars=${res.replayChars} bits=${JSON.stringify(d.bits)} humans=${d.vu.humanCount} players=${d.vu.playerCount} teams=${d.vu.numberTeams} names=${names.length} statedCmds=${d.statedCmds} decoded=${d.cmds.length} steps=${d.statedSteps} lastTick=${tl.lastTick} byId=${JSON.stringify(byId)}`);
}

if (import.meta.url === `file://${process.argv[1]}`) main();
