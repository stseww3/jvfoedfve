#!/usr/bin/env node
// engdiff.mjs — 离线模拟器（src/sim + 本目录的重放器 resim_r08.mjs）对线上引擎原文（src/engine/live_game_js.js，
// 用 src/tools/engine_replay.cjs 在 Node 里原样加载）的全场逐位对账。
//
// 日志快照（traj.csv）只有我方号、每 90 拍一行；这里把同一份录像分别喂给两边，每 10 拍比一次全部 512 个玩家
// （真人、空壳、内置 AI）的地和兵，记下：
//   · 引擎 对 日志快照：一致几行（引擎是不是这局的真相）
//   · 模拟器 对 日志快照：一致几行
//   · 模拟器 对 引擎：第一处不一致在哪一拍、是哪个玩家（真人 / 空壳 / 内置 AI）、之后不一致的玩家数怎么长
// 第一处不一致找到以后，再把那 10 拍逐拍重跑一遍，定到具体的拍和玩家，并列出那一拍前后牵涉这个玩家的录像指令。
// 只读 /agent/repos/c136-data（发现集的对局包 + src）；不跑策略，不改任何指令。
//
//   bash c136-review/tools/run-heavy.sh node c136-review/agents/R08/scripts/engdiff.mjs [--until T] <局> <局> …
//   → out/_run/engdiff/<局>.json（不入库）；汇总：python3 fidabl.py → out/_cross/fidabl.txt 的 [FA-E]
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';
import { resim } from './resim_r08.mjs';

const require = createRequire(import.meta.url);
const { startReplay, loadCsv, DATA } = require('/agent/repos/c136-data/src/tools/engine_replay.cjs');

const HERE = path.dirname(fileURLToPath(import.meta.url));
const RUN = path.join(HERE, '..', 'out', '_run', 'engdiff');
fs.mkdirSync(RUN, { recursive: true });

const argv = process.argv.slice(2);
const take = (k, d) => { const i = argv.indexOf(`--${k}`); if (i < 0) return d; const v = argv[i + 1]; argv.splice(i, 2); return v; };
const until = +take('until', 0) || Infinity;
// --fid <臂>：模拟器这一侧关掉一项保真度（和 fidabl.mjs 同一组臂），看全场第一处不一致提前到哪一拍；结果写 <局>.<臂>.json
const ARMS = { nocolor: { colors: false }, aiteam: { botTeams: 'always' }, diff6: { difficulty: 6 }, nocache: { cache32: false }, noteamend: { teamEnd: false } };
const arm = take('fid', null);
if (arm && !(arm in ARMS)) { console.error(`不认识的臂：${arm}`); process.exit(2); }
const fid = arm ? ARMS[arm] : undefined;
const STEP = 10;

// 引擎走一遍：every 拍取一次全场快照；lo..hi 之间逐拍取
function engineRun(mid, lo = Infinity, hi = -Infinity, stopAt = until) {
  const { h, info, api } = startReplay(mid);
  const NP = info.players;
  const grab = h.run(`(function (buf) { var n = aE.a0E; for (var p = 0; p < n; p++) { buf[3 * p] = ah.hN[p]; buf[3 * p + 1] = ah.hb[p]; buf[3 * p + 2] = (ah.nU[p] ? 1 : 0) + 2 * ah.a6S[p]; } })`);
  const snaps = new Map();
  const names = api.names();
  let lastT = -1, over = 0;
  while (true) {
    const [t, hx, st] = api.advance(1);
    if (hx) continue;
    if (t === lastT) { if (st === 2) { over = 1; break; } continue; }
    lastT = t;
    if (t % STEP === 0 || (t >= lo && t <= hi)) {
      const buf = new Int32Array(3 * NP);
      grab(buf);
      snaps.set(t, buf);
    }
    if (st === 2) { over = 1; break; }
    if (t >= stopAt) break;
  }
  return { info, names, snaps, lastT, over, NP };
}

const force = argv.includes('--force');
if (force) argv.splice(argv.indexOf('--force'), 1);
// --budget <秒>：开跑下一局之前看一眼已经用掉的时间，超了就停（run-heavy.sh 的 110 秒上限之内尽量多跑几局；剩下的下一批接着跑）
const budget = +take('budget', 0) || Infinity;
const tStart = Date.now();
for (const mid of argv) {
  const file = path.join(RUN, `${mid}${arm ? `.${arm}` : ''}${until === Infinity ? '' : `.u${until}`}.json`);
  if (!force && fs.existsSync(file)) { console.log(`${mid}: 已有，跳过`); continue; }   // 分批跑、被超时杀掉以后可以原样重跑
  if ((Date.now() - tStart) / 1000 > budget) { console.log(`${mid}: 这一批的时间预算用完，留给下一批`); break; }
  const t0 = Date.now();
  let E;
  try { E = engineRun(mid); } catch (e) { console.log(`${mid}: 引擎重放失败：${String(e.message || e).slice(0, 160)}`); fs.writeFileSync(file, JSON.stringify({ matchId: mid, error: String(e.message || e).slice(0, 300) })); continue; }
  const tEng = Date.now() - t0;
  const H = E.info.ku, NP = E.NP;

  // 引擎 对 日志快照
  const traj = loadCsv(path.join(DATA, mid, 'traj.csv'));
  const out = { matchId: mid, arm, until: until === Infinity ? null : until, H, players: NP, engLast: E.lastT, engOver: E.over, step: STEP };

  // 模拟器走一遍，同拍对账
  const cmp = (g, buf, acc) => {
    let nH = 0, nA = 0, first = -1;
    for (let p = 0; p < NP; p++) {
      const aliveE = buf[3 * p + 2] & 1, aliveS = g.alive[p] ? 1 : 0;
      let bad = buf[3 * p] !== g.terr[p] || aliveE !== aliveS;
      if (!bad && aliveE && buf[3 * p + 1] !== g.bal[p]) bad = true;
      if (bad) { if (p < H) nH++; else nA++; if (first < 0) first = p; }
    }
    return [nH, nA, first];
  };
  let firstT = null, firstP = null, series = [], simEnd = 0, nCmp = 0, nBad = 0;
  let X;
  try {
    X = resim(mid, {
      until: Math.min(until, E.lastT), fid,
      onTick: (g) => {
        simEnd = g.t;
        const buf = E.snaps.get(g.t);
        if (!buf || g.t % STEP) return;
        nCmp++;
        const [nH, nA, first] = cmp(g, buf);
        if (nH + nA) {
          nBad++;
          if (firstT === null) { firstT = g.t; firstP = first; }
        }
        if (firstT !== null && (series.length < 400) && (g.t - firstT) % 90 === 0) series.push([g.t, nH, nA]);
      },
    });
  } catch (e) { console.log(`${mid}: 模拟器重演失败：${String(e.message || e).slice(0, 160)}`); fs.writeFileSync(file, JSON.stringify({ ...out, error: String(e.message || e).slice(0, 300) })); continue; }
  const v = X.validate;
  // 引擎 对 日志：我方号按重放器认出来的席位
  let eRows = 0, eExact = 0, eFirst = null;
  for (const r of traj) {
    const s = X.squad[r.bot];
    if (!s || s.id < 0) continue;
    const t = +r.t;
    const buf = E.snaps.get(t);
    if (!buf) continue;          // 日志行不在 10 拍格上的不比（日志行都在 90 拍格上）
    eRows++;
    if (buf[3 * s.id] === +r.terr && buf[3 * s.id + 1] === +r.bal) eExact++;
    else if (eFirst === null || t < eFirst) eFirst = t;
  }
  Object.assign(out, {
    simEnd, simOver: X.over, gameMode: X.gameMode, nTeams: X.nTeams, botsTeamed: X.botsTeamed,
    logRows: v.rows, simLogExact: v.bothExact, simLogFirst: v.mism.length ? v.mism[0][0] : null,
    engLogRows: eRows, engLogExact: eExact, engLogFirst: eFirst,
    nCmp, nBad, firstT, firstP, series,
  });

  // 第一处不一致：逐拍定位
  if (firstT !== null) {
    const lo = firstT - STEP + 1, hi = firstT;
    const E2 = engineRun(mid, lo, hi, hi);
    let exactT = null, who = [];
    resim(mid, {
      until: hi, fid,
      onTick: (g) => {
        if (exactT !== null || g.t < lo) return;
        const buf = E2.snaps.get(g.t);
        if (!buf) return;
        const list = [];
        for (let p = 0; p < NP; p++) {
          const aliveE = buf[3 * p + 2] & 1, aliveS = g.alive[p] ? 1 : 0;
          if (buf[3 * p] !== g.terr[p] || aliveE !== aliveS || (aliveE && buf[3 * p + 1] !== g.bal[p])) {
            list.push({ p, kind: p >= H ? 'AI' : X.leftT[p] >= 0 && X.leftT[p] <= g.t ? '空壳' : '真人', name: (E2.names[p] || '').trim(),
              team: X.teams ? X.teams[p] : 0, leftT: p < H ? X.leftT[p] : -1,
              terrE: buf[3 * p], terrS: g.terr[p], balE: buf[3 * p + 1], balS: g.bal[p], aliveE, aliveS, stateE: buf[3 * p + 2] >> 1, stateS: g.state[p] });
          }
        }
        if (list.length) { exactT = g.t; who = list; }
      },
    });
    out.exactT = exactT;
    out.who = who.slice(0, 12);
    out.nWho = who.length;
    // 那一拍前后（exactT-8 … exactT）牵涉这些玩家的录像指令（重放器的指令流水）
    const set = new Set(who.map((w) => w.p));
    out.cmds = X.cmdLog.filter((c) => c[0] >= exactT - 8 && c[0] <= exactT && (set.has(c[1]) || ((c[2] === 1 || c[2] === 2) && set.has(Math.min(c[4], 512))))).slice(0, 40);
    out.husk = X.huskGifts.filter((g2) => g2[0] >= exactT - 8 && g2[0] <= exactT && (set.has(g2[1]) || set.has(g2[2]))).slice(0, 20);
  }
  fs.writeFileSync(file, JSON.stringify(out));
  console.log(`${mid}${arm ? `[${arm}]` : ''}: H=${H} 引擎到 ${E.lastT} 拍${E.over ? '(终局)' : ''} | 引擎对日志 ${eExact}/${eRows}${eFirst !== null ? `@${eFirst}` : ''} | 模拟器对日志 ${v.bothExact}/${v.rows}${v.mism.length ? `@${v.mism[0][0]}` : ''} | 模拟器对引擎 ${nCmp - nBad}/${nCmp} 个断面全场一致${firstT !== null ? `，第一处 t=${out.exactT}：${out.who.slice(0, 3).map((w) => `${w.kind}#${w.p} 地 ${w.terrE}/${w.terrS} 兵 ${w.balE}/${w.balS}`).join('；')}${out.nWho > 3 ? ` …共 ${out.nWho} 个` : ''}` : ''} | ${((Date.now() - t0) / 1000).toFixed(1)}s（引擎 ${(tEng / 1000).toFixed(1)}s）`);
}
