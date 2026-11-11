// replay_cmds.mjs — 把一局的 replay.txt（实况分享串）解码成「逐拍命令流」，不需要地图、不跑模拟器。
// 解码函数 decodeReplay 逐字取自 /agent/repos/c136-data/src/sim/tools/c102-replay-lib.mjs（只读引用，未改语义）。
// 输出（TSV，stdout 或 --out 文件）：tick  id  kind  player  name  a  b  targetName
//   id=0 spawn(x,y)  id=1 attack(pct,target)  id=2 donate(pct,to)  id=3 boat(pct,water<<3|dir)
//   id=4 chase/recall  id=5 retreat(target)  id=8/9 leave  其他按原值打印
// 拍号口径（与 c102-replay-lib.makeStepper / pure-node-dissect 一致）：
//   选点阶段占 jJ+1 步（真人数<=2:30，<=50:40，否则 50），之后每一步 = 一拍；
//   一个「命令块」占一步，一个「空跑块」占 ja 步。tick = 步号 - (jJ+1)。选点阶段的命令 tick 记为负数。
// 用法：
//   node replay_cmds.mjs <matchId|replay.txt 路径> [--out 文件] [--summary]
//   --summary 只打印头信息与各类命令计数（JSON）。
import fs from 'node:fs';
import path from 'node:path';

const DATA = process.env.C136_DATA || '/agent/repos/c136-data';

export function decodeReplay(raw) {
  let ga = raw.trim();
  const eq = ga.indexOf('=');
  if (eq >= 0) ga = ga.substring(eq + 1);
  ga = ga.replace(/[^a-zA-Z0-9_\-]/g, '-');
  const abv = new Uint8Array(78);
  abv[50] = 37;
  for (let i = 0; i < 10; i++) abv[i + 3] = i + 1;
  for (let i = 0; i < 26; i++) {
    abv[i + 20] = i + 11;
    abv[i + 52] = i + 38;
  }
  const aCT = new Uint8Array(ga.length);
  for (let i = 0; i < ga.length; i++) aCT[i] = abv[ga.charCodeAt(i) - 45];
  const mH = new Uint8Array((6 * aCT.length + 7) >> 3);
  let wp = 0;
  for (let i = 0; i < aCT.length; i++) {
    const v = aCT[i];
    for (let b = 5; b >= 0; b--, wp++) mH[wp >> 3] |= ((v >> b) & 1) << (7 - (wp & 7));
  }
  let a9 = 0;
  const totalBits = mH.length * 8;
  const i2 = (size) => {
    let h2 = 0;
    const bz = a9 + size - 1;
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
    const len = Math.max(fe, aZd);
    const dC = new (aY3 <= 8 ? Uint8Array : aY3 <= 16 ? Uint16Array : Uint32Array)(len);
    for (let i = 0; i < fe; i++) dC[i] = i2(aY3);
    if (dC[fe - 1]) dC.fill(dC[fe - 1], fe);
    return { n: fe, data: dC };
  };
  const aHo = (aEd, aY6, aZd) => {
    const fe = i2(aEd);
    if (!fe) return null;
    const len = Math.max(fe, aZd);
    const dC = new Array(len);
    for (let i = 0; i < fe; i++) dC[i] = aHl(aY6);
    dC.fill(dC[fe - 1], fe);
    return { n: fe, data: dC };
  };
  const version = i2(12), vs = i2(12), statedSize = i2(31);
  const vu = { version, vs, statedSize };
  vu.mapType = i2(2);
  vu.mapProceduralIndex = i2(8);
  vu.mapRealisticIndex = i2(8);
  vu.mapSeed = i2(14);
  vu.mapName = aHl(5);
  if (vu.mapType === 2) {
    const aDc = i2(30);
    a9 += 6 * aDc;
  }
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
  const ek = i2(5), aHp = i2(30), aHq = i2(30);
  const cmds = [];
  for (let i = 0; i < aHp; i++) {
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
  const jY = new Uint8Array(aHq), ja = new Uint32Array(aHq);
  for (let i = 0; i < aHq; i++) {
    jY[i] = i2(1);
    ja[i] = i2(ek);
  }
  return { vu, cmds, jY, ja, bitsUsed: a9, totalBits };
}

// 逐拍展开：返回 [{tick, id, player, dX, dZ}]，以及总拍数
export function timeline(d) {
  const H = d.vu.humanCount;
  const jJ = H <= 2 ? 30 : H <= 50 ? 40 : 50;
  const spawnSteps = d.vu.selectableSpawn ? jJ + 1 : 0;
  const out = [];
  let step = 0, iw = 0;
  for (let iv = 0; iv < d.ja.length; iv++) {
    const jZ = d.ja[iv];
    if (d.jY[iv]) {
      for (let a = iw; a < iw + jZ; a++) out.push({ tick: step - spawnSteps, ...d.cmds[a] });
      iw += jZ;
      step += 1;
    } else {
      step += Math.max(1, jZ);
    }
  }
  return { cmds: out, totalTicks: step - spawnSteps, spawnSteps, usedCmds: iw };
}

const KIND = { 0: 'spawn', 1: 'attack', 2: 'donate', 3: 'boat', 4: 'chase', 5: 'retreat', 6: 'c6', 7: 'c7', 8: 'leave8', 9: 'leave9', 10: 'c10' };

export function loadReplay(arg) {
  const p = fs.existsSync(arg) ? arg : path.join(DATA, 'bundles', arg, 'replay.txt');
  if (!fs.existsSync(p)) {
    const q = path.join(DATA, 'validation_bundles', arg, 'replay.txt');
    if (fs.existsSync(q)) return decodeReplay(fs.readFileSync(q, 'utf8'));
    throw new Error('replay not found: ' + p);
  }
  return decodeReplay(fs.readFileSync(p, 'utf8'));
}

if (import.meta.url === `file://${process.argv[1]}`) {
  const args = process.argv.slice(2);
  const id = args[0];
  const outIdx = args.indexOf('--out');
  const d = loadReplay(id);
  const vu = d.vu;
  const names = vu.playerNamesData ? vu.playerNamesData.data : [];
  const tl = timeline(d);
  const H = vu.humanCount;
  const nm = (p) => (p >= 512 ? 'NEUTRAL' : p < H ? (names[p] ?? `H#${p}`) : `bot#${p}`);
  if (args.includes('--summary')) {
    const cnt = {};
    for (const c of tl.cmds) cnt[KIND[c.id] ?? c.id] = (cnt[KIND[c.id] ?? c.id] || 0) + 1;
    const head = {};
    for (const k of Object.keys(vu)) {
      const v = vu[k];
      if (v && typeof v === 'object' && 'data' in v) head[k] = { n: v.n, first: Array.from(v.data.slice(0, Math.min(v.n, 12))) };
      else head[k] = v;
    }
    console.log(JSON.stringify({ match: id, header: head, cmdTotal: d.cmds.length, usedCmds: tl.usedCmds, totalTicks: tl.totalTicks, spawnSteps: tl.spawnSteps,
      bitsUsed: d.bitsUsed, totalBits: d.totalBits, counts: cnt, names: names.slice(0, H) }, null, 1));
  } else {
    const W = 0;
    const lines = ['tick\tid\tkind\tplayer\tname\ta\tb\ttargetName'];
    for (const c of tl.cmds) {
      let a = c.dX, b = c.dZ, tn = '';
      if (c.id === 1 || c.id === 2) tn = nm(c.dZ);
      else if (c.id === 5) tn = nm(c.dX);
      else if (c.id === 3) { a = c.dX; b = `${c.dZ >> 3}:${c.dZ & 7}`; }
      lines.push([c.tick, c.id, KIND[c.id] ?? ('c' + c.id), c.player, nm(c.player), a, b, tn].join('\t'));
    }
    const text = lines.join('\n') + '\n';
    if (outIdx >= 0) { fs.mkdirSync(path.dirname(args[outIdx + 1]), { recursive: true }); fs.writeFileSync(args[outIdx + 1], text); console.log(`wrote ${args[outIdx + 1]} cmds=${tl.cmds.length} ticks=${tl.totalTicks}`); }
    else process.stdout.write(text);
  }
}
