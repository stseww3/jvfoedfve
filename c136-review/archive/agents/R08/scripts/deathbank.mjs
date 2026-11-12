#!/usr/bin/env node
// deathbank.mjs — 「四分之一峰值线出局时账上还有多少兵」的真相口径原料：整局重演一遍，把每个真人席位出局那一拍、
// 引擎清零之前的状态记下来（地、账上的兵、峰值、在线还是空壳、自己在途的兵、压在它身上的兵）。
// 日志口径（xscan.py）只看得到本编队的号、而且用的是客户端最后看到的余额；这里是引擎里的真值，野人席位同一把尺子，可以当对照。
// 只读 /agent/repos/c136-data（发现集）；不跑策略，不改任何指令。
//
//   bash c136-review/tools/run-heavy.sh node c136-review/agents/R08/scripts/deathbank.mjs <局> <局> …   [--force] [--own-recording]
//   → out/_run/deathbank/<局>.json（不入库）；汇总：python3 deathbank.py → out/_cross/deathbank.txt
//   （namepool.mjs 跑 squad20 的局时顺手写同一份文件，那些局不用再跑。）
// 录像取自哪一份包：out/_run/room_pairs.json（roompairs.py 写）里列了的局，用同房另一份包更长的录像，本包的号按名字认；
//   --own-recording 强制用自己的。已有输出用的录像和现在该用的不是同一份，就重跑。
//
// 每局写出：H / land / endTick / names / teams / leftT / deathT / squad（日志标签 → 席位）/ exact（重演和日志逐行核对）
//   replayFrom（录像取自哪一份包；自己的就是 null）/ mismT（重演和本包日志第一次对不上的那一拍；全对得上是 null）
//   deaths：[t, 席位, 类别(eliminate = 除名；landless-with-boats = 陆上清场但海上有船、不除名), 出局前的地, 账上的兵, 峰值,
//            状态(0 在线 / 2 空壳), 自己在途的兵, 正在打它的人数, 压在它身上的兵, 压得最多的那个席位, 海上的船数]
//   seats：每个真人席位 [整局最大的地, 录像末拍的地, 录像末拍的兵]
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { resim } from './resim_r08.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const RUN = path.join(HERE, '..', 'out', '_run', 'deathbank');
const PAIRS_FILE = path.join(HERE, '..', 'out', '_run', 'room_pairs.json');

export function recordingOf(mid, ownOnly = false) {
  if (ownOnly) return null;
  try { return JSON.parse(fs.readFileSync(PAIRS_FILE, 'utf8'))[mid] || null; } catch { return null; }
}

export function sameRecording(file, src) {
  try { return (JSON.parse(fs.readFileSync(file, 'utf8')).replayFrom || null) === (src || null); } catch { return false; }
}

export function deathRows(X) {
  return X.deaths.map((d) => {
    let top = -1, topV = -1, sum = 0;
    for (const [a, v] of d.attackers) { sum += v; if (v > topV) { topV = v; top = a; } }
    return [d.t, d.p, d.kind, d.terr, d.bal, d.peak, d.state, d.out || 0, d.attackers.length, sum, top, d.boats];
  });
}

export function writeDeathbank(mid, X, deaths, src = null) {
  fs.mkdirSync(RUN, { recursive: true });
  const H = X.H;
  const maxTerr = new Array(H).fill(0);
  for (const row of X.snapTerr) for (let p = 0; p < H; p++) if (row[p] > maxTerr[p]) maxTerr[p] = row[p];
  const last = X.snapTerr.length - 1;
  const seats = [];
  for (let p = 0; p < H; p++) seats.push([maxTerr[p], last >= 0 ? X.snapTerr[last][p] : 0, last >= 0 ? X.snapBal[last][p] : 0]);
  const out = {
    matchId: mid, H, land: X.land, endTick: X.endTick, over: X.over, gameMode: X.gameMode, nTeams: X.nTeams,
    names: X.names.slice(0, H), teams: Array.from(X.teams).slice(0, H), leftT: X.leftT, deathT: X.deathT,
    squad: Object.fromEntries(Object.entries(X.squad).map(([b, s]) => [b, s.id])),
    exact: [X.validate.bothExact, X.validate.rows],
    replayFrom: src || null, mismT: X.validate.mism.length ? X.validate.mism[0][0] : null,
    deaths, seats,
  };
  fs.writeFileSync(path.join(RUN, `${mid}.json`), JSON.stringify(out));
  return out;
}

if (import.meta.url === `file://${process.argv[1]}`) {
  const argv = process.argv.slice(2);
  const FORCE = argv.includes('--force');
  const OWN_REC = argv.includes('--own-recording');
  // --budget <秒>：开跑下一局之前看一眼已经用掉的时间，超了就停，剩下的下一批接着跑
  const bi = argv.indexOf('--budget');
  const budget = bi >= 0 ? +argv.splice(bi, 2)[1] : Infinity;
  const tStart = Date.now();
  for (const mid of argv.filter((a) => !a.startsWith('--'))) {
    const file = path.join(RUN, `${mid}.json`);
    const src = recordingOf(mid, OWN_REC);
    if (fs.existsSync(file) && !FORCE && sameRecording(file, src)) { console.log(`${mid}: 已有，跳过`); continue; }
    if ((Date.now() - tStart) / 1000 > budget) { console.log(`${mid}: 这一批的时间预算用完，留给下一批`); break; }
    const t0 = Date.now();
    let X;
    try { X = resim(mid, { replayFrom: src || undefined }); } catch (e) { console.log(`${mid}: 重演失败：${String(e.message || e).slice(0, 160)}`); continue; }
    const deaths = deathRows(X);
    writeDeathbank(mid, X, deaths, src);
    console.log(`${mid}: H=${X.H} 到 ${X.endTick} 拍${src ? `（录像取自 ${src}）` : ''}，日志 ${X.validate.bothExact}/${X.validate.rows}，出局 ${deaths.length} 行 | ${((Date.now() - t0) / 1000).toFixed(1)}s`);
  }
}
