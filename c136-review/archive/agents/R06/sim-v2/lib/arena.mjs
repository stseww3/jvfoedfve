// arena.mjs — 模式 2：闭环多原型对抗门禁。
//
// 房间：
//   --room <局号>   真局的房间头（地图、真人数、名字与战队标签、颜色、配置队数、出生随机种子）和其余真人的真实落点；
//                    分队用引擎的算法现算。--tag same / split 给我方席位统一加上 / 去掉战队标签后重新分队（同队 vs 拆队）。
//   --room synth    离线地图上按参数生成房间（--map --humans --teams --squad --clans）。
// 我方席位：对照臂 / 处理臂各一个世界，策略文件原样装进页面替身，经同一条指令通道（C0~C4）下令，从第 0 拍起闭环。
// 其余真人：对手原型（lib/opponents.mjs），队号和我方相同的就是同队路人；真局里在场时离场的人到点变空壳（引擎托管）。
//   --others-replay-until T（只对真局房间）：前 T 拍其余真人照录像下令（目标失效的陆攻改打身边最便宜的），T 拍起交给原型。
// 两条臂用同一个种子：对手的「运气」按 (种子, 席位, 拍号) 散列，两臂相同。真局房间另把录像原样放一遍，作参照（当年真实的走势）。
import fs from 'node:fs';
import path from 'node:path';
import { loadMatch, buildWorld, ReplayStepper, execRecorded, loadMapAny, SIMV2, NEUTRAL, P_INNER, T_LAND } from './match.mjs';
import { TGame, assignTeams, teamOpts, clanOf, MAX_PLAYERS } from './tgame.mjs';
import { compileStrategy, strategyPath } from './sandbox.mjs';
import { makeProfile, loadTrace } from './channel.mjs';
import { Arm } from './arm.mjs';
import { naturalShares, PAIR_KEYS, ATK_SEG } from './metrics.mjs';
import { Crowd, assignArches, parseMix, loadProfile, DEFAULT_MIX } from './opponents.mjs';
import { chanOptsOf, armOptsOf, borrowSeats } from './checkpoint.mjs';
import { num, list, fmtN, hashU, hashInt, median, strHash } from './util.mjs';

export const CHECKPOINTS = [357, 630, 1071, 1530, 2142, 3210, 4284, 6000, 9000];
// arena 多出来的成对指标
export const ARENA_KEYS = [
  ['landShare1', '编队领土占全图陆地', 1],
  ['mainTeamShare1', '主队领土占全图陆地', 1],
  ['mainTeamLead', '结束时主队是领先队（1/0）', 1],
  ['mainTeamWin', '主队胜（1/0，没分出胜负为空）', 1],
  ['squadDead3000', '3000 拍前阵亡的我方席位', -1],
];

// c116 系 / c110 各自认的队友名字（策略文件里的名单）；生成房间时我方席位从里面取名
const POOLS = {
  c116: ['ryan_m', 'noah88', 'sora_w', 'zexos1', 'leo_tx', 'zero_7', 'talon5', 'kaito9', 'riku_x', 'alex_k', 'mishi', 'matzz', 'kiholma', 'leo_99', 'racoon', 'vortex', 'kronos', 'nexus', 'sayo', 'tomo'],
  c110: null,   // c110 按全名查 SQUAD_POOL_SET：生成房间时从策略文件里读
};
const parseJson = (s, what) => { if (s === undefined || s === true) return {}; try { return JSON.parse(s); } catch (e) { throw new Error(`${what} 不是合法的 JSON：${s}`); } };
const stripTag = (n) => String(n).replace(/\[[^\]]*\]/g, '').trim();

// ---- 房间 -----------------------------------------------------------------------------------
function realRoom(o) {
  const M = loadMatch(o.room);
  if (!M.teamGame) throw new Error(`${o.room} 不是组队局`);
  const H = M.H;
  const names = M.names.slice();
  const squad = M.squad.slice();
  const tag = o.tag || 'asis';
  const tagName = String(o['tag-name'] || 'APEX').toUpperCase();
  if (tag === 'same') for (const p of squad) names[p] = `[${tagName}] ${stripTag(names[p])}`;
  else if (tag === 'split') for (const p of squad) names[p] = stripTag(names[p]);
  else if (tag !== 'asis') throw new Error('--tag 只能是 asis / same / split');
  const nTeamsHeader = num(o.teams, M.vu.numberTeams);
  const ta = assignTeams(names, M.colors, H, nTeamsHeader);
  return {
    kind: 'real', mid: o.room, M, H, names, colors: M.colors, ta, nTeamsHeader, squad, slotOf: M.slotOf, tag,
    map: M.map, mapKey: M.mapKey, land: M.map.land,
    make: () => buildWorld({ ...M, names, ta }),
  };
}

function synthRoom(o, seed) {
  const [mi, ms] = String(o.map || '10_0').split('_').map(Number);
  const map = loadMapAny(mi, ms || 0);
  const H = num(o.humans, 40), nSquad = num(o.squad, 10), nTeamsHeader = num(o.teams, 3);
  if (nSquad >= H) throw new Error('--squad 要小于 --humans');
  const tag = o.tag || 'same';
  const tagName = String(o['tag-name'] || 'APEX').toUpperCase();
  const pool = POOLS[o.pool || 'c116'];
  if (!pool) throw new Error('生成房间只备了 c116 系的队友名单（--pool c116）；c110 请用真局房间');
  if (nSquad > pool.length) throw new Error(`生成房间的我方席位最多 ${pool.length} 个`);
  const names = new Array(MAX_PLAYERS).fill('');
  const colors = [];
  for (let p = 0; p < H; p++) { names[p] = `Player ${100 + hashInt(0, 899, seed, p, 701)}`; colors.push(hashInt(0, 262143, seed, p, 702)); }
  // 我方席位连着坐（真局里它们是一起进房的）
  const at = hashInt(0, H - nSquad, seed, 703);
  const squad = [];
  for (let i = 0; i < nSquad; i++) { const p = at + i; squad.push(p); names[p] = tag === 'same' ? `[${tagName}] ${pool[i]}` : pool[i]; }
  // 对手战队：--clans 2x4,1x6 = 两个 4 人战队 + 一个 6 人战队
  const others = [];
  for (let p = 0; p < H; p++) if (!squad.includes(p)) others.push(p);
  let k = 0, ci = 0;
  for (const part of list(o.clans === undefined ? '2x4' : o.clans)) {
    const [n, size] = part.split('x').map(Number);
    for (let c = 0; c < n; c++, ci++) for (let j = 0; j < size && k < others.length; j++, k++) names[others[k]] = `[C${ci + 1}] ${names[others[k]]}`;
  }
  const ta = assignTeams(names, colors, H, nTeamsHeader);
  const spawnSeed = hashInt(0, 16383, seed, 704);
  return {
    kind: 'synth', mid: null, M: null, H, names, colors, ta, nTeamsHeader, squad, slotOf: new Map(squad.map((p, i) => [p, i])), tag,
    map, mapKey: `${mi}_${ms || 0}`, land: map.land,
    make: () => new TGame({ map, humans: H, players: 512, difficulty: 0, spawnSeed, selectableSpawn: true, battleRoyaleMode: 0, humanColors: colors, passableWater: 1, passableMountains: 1, names, ...teamOpts(ta, H) }),
  };
}

// 生成房间里其余真人的落点：每人看 24 个随机陆地点，挑离已有落点最远的（真人倾向于找空地）
function spreadSpawn(w, others, seed) {
  const pts = [];
  for (let p = 0; p < w.players; p++) if (w.alive[p] && w.terr[p] > 0) pts.push([(w.x0[p] + w.x1[p]) >> 1, (w.y0[p] + w.y1[p]) >> 1]);
  for (const p of others) {
    let best = null, bd = -1;
    for (let k = 0; k < 24; k++) {
      const x = hashInt(12, w.W - 13, seed, p, 720 + k), y = hashInt(12, w.H - 13, seed, p, 760 + k);
      if (w.px[y * w.W + x] !== 0) continue;
      let d = 1e9;
      for (const [a, b] of pts) { const dd = Math.hypot(x - a, y - b); if (dd < d) d = dd; }
      if (d > bd) { bd = d; best = [x, y]; }
    }
    if (best && w.chooseSpawn(best[0], best[1], p, false)) pts.push(best);
  }
}

// ---- 断面快照 ----------------------------------------------------------------------------------
function snapOf(w, squad, squadSet, mainTeam) {
  const H = w.humans;
  let sqTerr = 0, sqAlive = 0, sqBal = 0, humTerr = 0, oTerr = 0, oBal = 0, oAlive = 0, oN = 0, aiTerr = 0, aiAlive = 0;
  const oList = [], dList = [];
  for (let p = 0; p < H; p++) {
    const present = w.alive[p] && w.state[p] !== 2;
    if (w.alive[p]) humTerr += w.terr[p];
    if (squadSet.has(p)) { if (present) { sqAlive++; sqTerr += w.terr[p]; sqBal += w.bal[p]; } }
    else { oN++; if (present) { oAlive++; oTerr += w.terr[p]; oBal += w.bal[p]; oList.push(w.terr[p]); if (w.terr[p] > 0) dList.push(w.bal[p] / w.terr[p]); } }
  }
  dList.sort((a, b) => a - b);
  const dq = (f) => (dList.length ? +dList[Math.min(dList.length - 1, Math.floor(f * dList.length))].toFixed(1) : 0);
  for (let p = H; p < w.players; p++) if (w.alive[p]) { aiAlive++; aiTerr += w.terr[p]; }
  const lands = w.teamGame ? Array.from(w.teamLands()) : [];
  let lead = 0;
  for (let t = 1; t < lands.length; t++) if (lands[t] > lands[lead]) lead = t;
  const r4 = (x) => +x.toFixed(4);
  oList.sort((a, b) => a - b);
  const oq = (f) => (oList.length ? oList[Math.min(oList.length - 1, Math.floor(f * oList.length))] : 0);
  return {
    othersQ: [oq(0.1), oq(0.25), oq(0.5), oq(0.75), oq(0.9), oq(1)],      // 其余在场真人的地：P10 / P25 / 中位 / P75 / P90 / 最大
    othersDQ: [dq(0.1), dq(0.25), dq(0.5), dq(0.75), dq(0.9)],            // 其余在场真人的兵密度（兵 ÷ 地）：P10 / P25 / 中位 / P75 / P90
    neutralShare: r4(1 - (humTerr + aiTerr) / w.land),
    t: w.t, squadTerr: sqTerr, squadShare: r4(sqTerr / w.land), squadAlive: sqAlive, squadDensity: sqTerr ? +(sqBal / sqTerr).toFixed(1) : 0,
    squadPerSeat: Math.round(sqTerr / Math.max(1, squad.length)),
    relTerr: humTerr > 0 ? r4((sqTerr / Math.max(1, squad.length)) / (humTerr / H)) : null,
    relOthers: oTerr > 0 && oN > 0 ? r4((sqTerr / Math.max(1, squad.length)) / (oTerr / oN)) : null,
    othersAliveShare: oN ? r4(oAlive / oN) : null, othersMedTerr: oList.length ? Math.round(median(oList)) : 0, othersPerSeat: oN ? Math.round(oTerr / oN) : 0,
    othersDensity: oTerr ? +(oBal / oTerr).toFixed(1) : 0,
    aiShare: r4(aiTerr / w.land), aiAlive,
    mainTeamShare: mainTeam > 0 && lands.length ? r4(lands[mainTeam] / w.land) : null, leadTeam: lead, teamLands: lands,
  };
}

// ---- 地的流向 -----------------------------------------------------------------------------------
// 每个陆地格在断面拍的归属：0 无主地 / 1 内置 AI / 2 其余真人（含他们变成的空壳）/ 3 我方席位；255 = 不是陆地。
// 相邻两个断面的归属两两配对，得到 4×4 的流向表 flow[从][到]（格数）：其余真人这一段从无主地、AI、我方手里各净拿了多少，
// 又被 AI、我方拿走多少。对手模型和录像的人均地差在哪一条流向上，一眼能看出来。
const FLOW_T = [357, 630, 1071, 1530, 2142, 3210];
function classMap(w, squadSet) {
  const n = w.px.length, out = new Uint8Array(n), px = w.px, own = w.own, H = w.humans;
  for (let c = 0; c < n; c++) {
    const v = px[c];
    if (v >= P_INNER) { const o = own[c]; out[c] = o >= H ? 1 : squadSet.has(o) ? 3 : 2; }
    else out[c] = v === T_LAND ? 0 : 255;
  }
  return out;
}
function flowOf(a, b) {
  const f = [[0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]];
  for (let c = 0; c < a.length; c++) { const x = a[c], y = b[c]; if (x !== 255 && y !== 255) f[x][y]++; }
  return f;
}
class FlowLog {
  constructor(squadSet) { this.squadSet = squadSet; this.prev = null; this.prevT = 0; this.out = {}; }
  at(w, t) {
    if (!FLOW_T.includes(t)) return;
    const cur = classMap(w, this.squadSet);
    if (this.prev) this.out[`${this.prevT}~${t}`] = flowOf(this.prev, cur);
    this.prev = cur; this.prevT = t;
  }
}

function cpuMs(c0) { const c = process.cpuUsage(c0); return Math.round((c.user + c.system) / 1000); }

export async function runArena(o) {
  const wall0 = Date.now(), cpu0 = process.cpuUsage();
  const seedAsked = num(o.seed, 1);
  if (!o.room) throw new Error('arena 模式要 --room <局号>（真局房间头）或 --room synth（生成房间）');
  const room = o.room === 'synth' ? synthRoom(o, seedAsked) : realRoom(o);
  // 真局房间：随机数种子再掺上局号 —— 否则同一个 --seed 下每个房间里「第 p 个席位」的出手风格、活跃度都一模一样，
  // 20 个房间等于同一次抽样重复 20 遍（验收时见过：某个种子下前 90 个席位里两头的滑块档位各只有 10 来个，中间 25 个）
  const seed = room.kind === 'real' ? hashInt(1, 2147483646, seedAsked, strHash(String(room.mid)) | 0, 799) : seedAsked;
  const { H, squad, ta } = room;
  if (!squad.length) throw new Error('房间里没有我方席位');
  const squadSet = new Set(squad);
  const len = num(o.len, 4300);
  const budgetMs = num(o['budget-ms'], 100000);
  const spawnMode = o.spawn || (room.kind === 'real' ? 'recorded' : 'policy');
  if (!['recorded', 'policy', 'random'].includes(spawnMode)) throw new Error('--spawn 只能是 recorded / policy / random');
  if (spawnMode === 'recorded' && room.kind !== 'real') throw new Error('生成房间没有录像落点：--spawn policy 或 random');
  const replayUntil = room.kind === 'real' ? num(o['others-replay-until'], 0) : 0;
  const husks = o.husks || (room.kind === 'real' ? 'real' : 'model');

  // 主队：我方席位最多的那个队
  const teamCount = new Map();
  for (const p of squad) teamCount.set(ta.fX[p], (teamCount.get(ta.fX[p]) || 0) + 1);
  const mainTeam = [...teamCount.entries()].sort((a, b) => b[1] - a[1] || a[0] - b[0])[0][0];
  const others = [];
  for (let p = 0; p < H; p++) if (!squadSet.has(p)) others.push(p);
  const mates = others.filter((p) => teamCount.has(ta.fX[p]));

  // ---- 参照：真局房间把录像原样放一遍（各断面的走势、谁在场时离场、谁整局没下过指令）
  const reality = room.kind === 'real' ? { cps: {}, leaveAlive: new Map() } : null;
  const idle = new Set();
  if (room.kind === 'real') {
    const M = room.M;
    for (const p of others) if (!M.lastCmd.has(p)) idle.add(p);
    if (room.tag === 'asis' || o['reality-any']) {
      const w = buildWorld(M);
      const st = new ReplayStepper(M, w);
      st.runSpawnPhase();
      // 这一局其余真人自己的出手强度（与 Crowd 的账同口径、同阶段划分）：对手模型按房间逐一对照用
      const RI = loadProfile().phases.map((p) => ({ t0: p.t0, cmds: 0, sent: 0, aliveTicks: 0, balTicks: 0, sentBy: { neutral: 0, ai: 0, hum: 0, boat: 0 }, okBy: { neutral: 0, ai: 0, hum: 0, boat: 0 }, onSq: 0, onSqSent: 0 }));
      const riOf = (t) => { for (let i = RI.length - 1; i >= 0; i--) if (t >= RI[i].t0) return RI[i]; return RI[0]; };
      const RS = ATK_SEG.map((a) => ({ t0: a, neutral: 0, ai: 0, hum: 0, neutralSent: 0, aiSent: 0, humSent: 0 }));
      reality.squadAtkSeg = RS;
      st.exec = (c) => {
        const p = c.player;
        if ((c.id === 8 || c.id === 9) && p < H && w.alive[p] && w.state[p] !== 2) reality.leaveAlive.set(p, w.t);
        let cls = null, onSq = false;
        if (p < H && !squadSet.has(p) && w.alive[p] && w.state[p] !== 2 && w.bal[p] >= 2) {      // 余额见底时点的空单不算（画像同口径）
          if (c.id === 1) {
            let tg = Math.min(c.dZ, NEUTRAL);
            if (tg < NEUTRAL && !w.alive[tg]) tg = NEUTRAL;
            cls = tg === NEUTRAL ? 'neutral' : tg >= H || w.state[tg] === 2 ? 'ai' : 'hum';
            onSq = cls === 'hum' && squadSet.has(tg);
          } else if (c.id === 3) cls = 'boat';
        }
        // 我方席位当年的陆攻（按时段、按落地时的对象）：与模型里我方的打法对照
        let sqCls = null;
        if (c.id === 1 && squadSet.has(p) && w.alive[p]) {
          let tg = Math.min(c.dZ, NEUTRAL);
          if (tg < NEUTRAL && !w.alive[tg]) tg = NEUTRAL;
          sqCls = tg === NEUTRAL ? 'neutral' : tg >= H ? 'ai' : 'hum';
        }
        const r = execRecorded(w, c);
        if (cls && r.ok) {
          const I = riOf(w.t);
          I.cmds++; I.sent += w.attackTroopsTmp; I.sentBy[cls] += w.attackTroopsTmp; I.okBy[cls]++;
          if (onSq) { I.onSq++; I.onSqSent += w.attackTroopsTmp; }
        }
        if (sqCls && r.ok) {
          let i = ATK_SEG.length - 1;
          while (i > 0 && w.t < ATK_SEG[i]) i--;
          RS[i][sqCls]++; RS[i][sqCls + 'Sent'] += w.attackTroopsTmp;
        }
        return r;
      };
      const end = Math.min(len, M.replayTicks - 1);
      reality.cps[0] = snapOf(w, squad, squadSet, mainTeam);
      reality.intensityRaw = RI;
      const fl = new FlowLog(squadSet);
      reality.flows = fl.out;
      while (w.t < end) {
        if (!st.step()) break;
        if (w.t % 7 === 0) {
          const I = riOf(w.t);
          for (const p of others) if (w.alive[p] && w.state[p] !== 2) { I.aliveTicks += 7; I.balTicks += 7 * w.bal[p]; }
        }
        w.tick();
        fl.at(w, w.t);
        if (CHECKPOINTS.includes(w.t)) reality.cps[w.t] = snapOf(w, squad, squadSet, mainTeam);
        if (w.over) break;
      }
      reality.t1 = w.t; reality.over = !!w.over; reality.winnerTeam = w.over ? w.winnerTeam : null;
      reality.cps.end = snapOf(w, squad, squadSet, mainTeam);
    } else {
      // 改了标签：房间重新分了队，当年的走势不再是同一个房间；只取「谁在场时离场」
      const w = buildWorld(M);
      const st = new ReplayStepper(M, w);
      st.runSpawnPhase();
      st.exec = (c) => {
        const p = c.player;
        if ((c.id === 8 || c.id === 9) && p < H && w.alive[p] && w.state[p] !== 2) reality.leaveAlive.set(p, w.t);
        return execRecorded(w, c);
      };
      const end = Math.min(len, M.replayTicks - 1);
      while (w.t < end) { if (!st.step()) break; w.tick(); if (w.over) break; }
      reality.t1 = w.t;
    }
  }
  const cpuReality = cpuMs(cpu0);

  // ---- 空壳时间表（其余真人）
  const leaveAt = new Map();
  if (husks === 'real' && reality) {
    for (const [p, t] of reality.leaveAlive) if (!squadSet.has(p)) leaveAt.set(p, t);
  } else if (husks === 'model') {
    const sh = loadProfile().leave;
    if (sh) {
      const ks = Object.keys(sh).map(Number).sort((a, b) => a - b);
      for (const p of others) {
        const u = hashU(seed, p, 731);
        let prevT = 0, prevS = 0;
        for (const t of ks) {
          if (u < sh[t]) { leaveAt.set(p, Math.round(prevT + (t - prevT) * (u - prevS) / Math.max(1e-9, sh[t] - prevS))); break; }
          prevT = t; prevS = sh[t];
        }
      }
    }
  } else if (husks !== 'off') throw new Error('--husks 只能是 real / model / off');
  // 我方空壳（席位 → [页面停摆拍, 被引擎登记离场的拍；-1 = 不登记]）：
  //   --squad-husks 2@1500   两个席位的页面在 1500 拍停摆，300 拍后登记离场；
  //   --squad-fate real      （真局房间）照当年：页面在席位还活着时就停摆的那些席位，到同一拍停摆、到同一拍登记离场。
  //                          对着同一局录像验收对手模型时要开 —— 20 局里有 5 局各有 3~13 个我方席位在 1530 拍前停摆，
  //                          不开的话模型里我方平白多出这些席位的战力（1530 拍时我方人均地是录像的 1.3~4.4 倍）。
  const squadHusk = new Map();
  if (o['squad-husks']) {
    const [n, at] = String(o['squad-husks']).split('@').map(Number);
    const order = squad.slice().sort((a, b) => hashU(seed, a, 741) - hashU(seed, b, 741));
    for (const p of order.slice(0, Math.max(0, n | 0))) squadHusk.set(p, [at || 1500, (at || 1500) + 300]);
  } else if (o['squad-fate'] === 'real') {
    if (room.kind !== 'real') throw new Error('--squad-fate real 只对真局房间有意义');
    for (const p of squad) if (room.M.doomed.has(p)) squadHusk.set(p, [room.M.pageEnd.get(p) ?? -1, room.M.leaveT.get(p) ?? -1]);
  } else if (o['squad-fate'] !== undefined && o['squad-fate'] !== 'off') throw new Error('--squad-fate 只能是 real / off');

  // ---- 对手原型
  const mix = parseMix(o.opp);
  const clanArches = o['clan-opp'] === undefined ? ['O2', 'O6'] : (o['clan-opp'] === 'off' || o['clan-opp'] === 'none' ? [] : list(o['clan-opp']).map((s) => s.toUpperCase()));
  const clanMembers = new Map();
  for (const p of others) { const c = clanOf(room.names[p]); if (c) { if (!clanMembers.has(c)) clanMembers.set(c, []); clanMembers.get(c).push(p); } }
  const clans = [...clanMembers.entries()].filter(([, m]) => m.length >= 2).map(([tag, m], i) => ({ id: i, tag, members: m }));
  const members = assignArches(seed, others, clans, mix, clanArches, idle);
  const archeCount = {};
  for (const m of members) archeCount[m.arche] = (archeCount[m.arche] || 0) + 1;

  // ---- 两条臂
  const which = o.arm || 'both';
  const specs = [];
  if (which !== 'candidate') specs.push({ name: 'baseline', file: strategyPath(o.baseline || 'vb'), params: parseJson(o['base-params'], '--base-params') });
  if (which !== 'baseline' && o.candidate) specs.push({ name: 'candidate', file: strategyPath(o.candidate), params: parseJson(o['cand-params'], '--cand-params') });
  if (!specs.length) throw new Error('没有可跑的臂：给 --baseline（缺省 vb）和 / 或 --candidate <策略文件>');
  for (const s of specs) s.strat = await compileStrategy(s.file);

  const chanSpec = o.channel || 'C1';
  const traceMid = o['trace-from'] || room.mid;
  const trace = /^c2/i.test(chanSpec) ? (traceMid ? loadTrace(SIMV2, traceMid) : null) : null;
  const seatDefs = squad.map((p) => ({ p, slot: room.slotOf.get(p) ?? p % 20 }));
  let seatMap = null;
  if (trace) seatMap = borrowSeats(trace, traceMid, squad, 0, len);

  const arms = specs.map((s) => {
    const w = room.make();
    const profile = makeProfile(chanSpec, { seed, seats: squad, trace, seatMap, Wmax: len + 2000, pageEnd: null, doomed: null, ownTrace: false });
    if (squadHusk.size) { profile.pageEnd = new Map([...squadHusk].map(([p, v]) => [p, v[0]])); profile.doomed = new Set(squadHusk.keys()); }
    const crowd = new Crowd(null, { seed, members, startT: replayUntil, squad, rateScale: num(o['opp-rate'], 1), leaveAt, rhythm: o['opp-rhythm'] ? list(o['opp-rhythm']).map(Number) : null, sigma: o['opp-sigma'] !== undefined ? num(o['opp-sigma'], 0.35) : undefined, densFrom: o['opp-dens-from'] !== undefined ? num(o['opp-dens-from'], 1530) : undefined, densRate: !!o['opp-dens-rate'], aiBy: o['opp-ai-by'] });
    const arm = new Arm({
      name: s.name, world: w, strat: s.strat, params: s.params, seats: seatDefs, profile, chanOpts: chanOptsOf(o),
      opts: { ...armOptsOf(o), ourLeaves: 'ignore' }, history: null, takeoverT: null, actors: [crowd],
    });
    crowd.arm = arm;
    arm.crowd = crowd;
    // 出生阶段
    const spawnLog = { mode: spawnMode, picks: 0, calls: 0 };
    const applyPolicy = (step, final) => {
      for (const seat of arm.seatList) {
        if (!w.alive[seat.p]) continue;
        spawnLog.calls++;
        const r = seat.chooseSpawn(140 * step, final);
        if (r && w.chooseSpawn(r.x, r.y, seat.p, false)) spawnLog.picks++;
      }
    };
    let stepper = null;
    if (room.kind === 'real') {
      stepper = new ReplayStepper(room.M, w);
      stepper.exec = (c) => {
        if (c.id === 0 && squadSet.has(c.player) && spawnMode !== 'recorded') return { ok: false, rec: false };
        if (c.id === 0 && c.player < H && !w.isAlive(c.player)) return { ok: false, rec: false };
        return execRecorded(w, c);
      };
      stepper.runSpawnPhase(spawnMode === 'policy' ? (iy, jJ) => { if (iy >= 4 && (iy % 4 === 0 || iy === jJ - 1) && iy < jJ) applyPolicy(iy, iy >= jJ - 4); } : undefined);
    } else {
      spreadSpawn(w, others, seed);
      if (spawnMode === 'policy') for (const step of [8, 16, 24, 32, 38]) applyPolicy(step, step === 38);
      w.endSpawnPhase();
    }
    w.teamCache = null;
    for (let p = 0; p < H; p++) if (w.state[p] === 2) arm.quit.add(p);
    arm.spawnLog = spawnLog;
    arm.natural = naturalShares(w);
    arm.cps = { 0: snapOf(w, squad, squadSet, mainTeam) };
    arm.flowLog = new FlowLog(squadSet);
    arm.deadAt = new Map();
    if (replayUntil > 0 && stepper) arm.attachReplay(stepper);
    arm.takeover();
    return arm;
  });
  const profile = arms[0].profile;
  const cpuSetup = cpuMs(cpu0) - cpuReality;

  // ---- 逐拍
  let t = 0, truncated = false, ended = '';
  while (t < len) {
    for (const a of arms) {
      const w = a.world;
      if (w.over) continue;
      if (a.stepper && t >= replayUntil) a.stepper = null;
      for (const [p, v] of squadHusk) if (t === v[1] && w.alive[p] && w.state[p] !== 2) { w.leave(p); a.quit.add(p); const s = a.seats.get(p); if (s) s.left = true; }
      a.tickOnce();
      if ((t & 15) === 0) for (const p of squad) if (!w.alive[p] && !a.deadAt.has(p)) a.deadAt.set(p, w.t);
    }
    t++;
    if (FLOW_T.includes(t)) for (const a of arms) if (a.world.t === t) a.flowLog.at(a.world, t);
    if (CHECKPOINTS.includes(t)) for (const a of arms) if (!a.world.over || a.world.t === t) a.cps[t] = snapOf(a.world, squad, squadSet, mainTeam);
    if (arms.every((a) => a.world.over)) { ended = '分出胜负'; break; }
    if ((t & 7) === 0 && Date.now() - wall0 > budgetMs) { truncated = true; break; }
  }

  const res = {
    mode: 'arena',
    room: {
      kind: room.kind, match: room.mid, map: room.mapKey, land: room.land, humans: H, nTeamsHeader: room.nTeamsHeader, nTeams: ta.nTeams, botsTeamed: ta.botsTeamed,
      tag: room.tag, squad, squadTeams: Object.fromEntries(teamCount), mainTeam, sameTeamStrangers: mates.length, teamSizes: ta.sizes,
      clans: clans.map((c) => ({ tag: c.tag, size: c.members.length })), idle: idle.size, husksPlanned: leaveAt.size, squadHusks: Object.fromEntries(squadHusk),
    },
    opp: { mix, clanArches, count: archeCount, replayUntil, husks, rateScale: num(o['opp-rate'], 1) },
    spawn: spawnMode, seed, seedAsked, t1: t, lenAsked: len, truncated, ended,
    channel: profile.name, channelNote: profile.note + (seatMap && traceMid !== room.mid ? `；阶梯借自 ${traceMid}` : ''), channelSpec: chanSpec,
    lagCourse: profile.instant ? [] : profile.lagCourse(squad, 0, Math.min(t, 3600), 300),
    opts: { ...armOptsOf(o), ...chanOptsOf(o) },
    arms: {},
  };
  if (reality) {
    res.reality = { cps: reality.cps, t1: reality.t1, over: reality.over ?? null, winnerTeam: reality.winnerTeam ?? null, leftAlive: reality.leaveAlive.size, squadAtkSeg: reality.squadAtkSeg || null, flows: reality.flows || null };
    if (reality.intensityRaw) {
      res.reality.intensity = reality.intensityRaw.map((I) => ({
        t0: I.t0, cmds: I.cmds, sent: I.sent, ratePerAlive100: I.aliveTicks ? +(100 * I.cmds / I.aliveTicks).toFixed(3) : null, spendPer100: I.balTicks ? +(100 * I.sent / I.balTicks).toFixed(4) : null, sentPerCmd: I.cmds ? Math.round(I.sent / I.cmds) : null,
        spendBy: Object.fromEntries(Object.keys(I.sentBy).map((k) => [k, I.balTicks ? +(100 * I.sentBy[k] / I.balTicks).toFixed(4) : null])),
        okRateBy: Object.fromEntries(Object.keys(I.okBy).map((k) => [k, I.aliveTicks ? +(100 * I.okBy[k] / I.aliveTicks).toFixed(3) : null])),
        sentBy: I.sentBy, onSq: I.onSq, onSqSent: I.onSqSent,
      }));
    }
  }
  for (const a of arms) {
    const w = a.world;
    for (const p of squad) if (!w.alive[p] && !a.deadAt.has(p)) a.deadAt.set(p, w.t);
    const end = snapOf(w, squad, squadSet, mainTeam);
    a.cps.end = end;
    const m = a.finish(a.natural, { file: a.strat.file });
    m.cps = a.cps;
    m.flows = a.flowLog.out;
    m.spawn = a.spawnLog;
    m.mainTeamShare1 = end.mainTeamShare;
    m.mainTeamLead = end.leadTeam === mainTeam ? 1 : 0;
    m.mainTeamWin = w.over ? (w.winnerTeam === mainTeam ? 1 : 0) : null;
    m.squadDead3000 = [...a.deadAt.values()].filter((x) => x < 3000).length;
    m.deadAt = [...a.deadAt.entries()].sort((x, y) => x[1] - y[1]);
    m.crowd = a.crowd.summary();
    res.arms[a.name] = m;
  }
  if (res.arms.baseline && res.arms.candidate) {
    const d = {};
    for (const [k] of [...PAIR_KEYS, ...ARENA_KEYS]) {
      const x = res.arms.baseline[k], y = res.arms.candidate[k];
      d[k] = typeof x === 'number' && typeof y === 'number' ? +(y - x).toFixed(4) : null;
    }
    res.delta = d;
  }
  res.cpuMs = cpuMs(cpu0); res.wallMs = Date.now() - wall0; res.cpuRealityMs = cpuReality; res.cpuSetupMs = cpuSetup;
  res.heapMB = Math.round(process.memoryUsage().heapUsed / 1048576);

  if (o.quiet) console.log(`[arena] ${room.mid || 'synth ' + room.mapKey} ${chanSpec} ${specs.map((s) => s.strat.name).join(' ↔ ')} → t=${t}${truncated ? '（时间预算截断）' : ''}：CPU ${res.cpuMs} ms`);
  else printArena(res);
  if (o['dump-onsquad']) {
    fs.mkdirSync(path.dirname(path.resolve(o['dump-onsquad'])), { recursive: true });
    fs.writeFileSync(o['dump-onsquad'], JSON.stringify(Object.fromEntries(arms.map((a) => [a.name, a.crowd.log.onSquad]))));
  }
  if (o.out) {
    fs.mkdirSync(path.dirname(path.resolve(o.out)), { recursive: true });
    fs.writeFileSync(o.out, JSON.stringify(res));
  }
  return res;
}

const show = (v) => (v === null || v === undefined ? '-' : typeof v === 'number' ? (Number.isInteger(v) ? fmtN(v) : Math.abs(v) < 10 ? v.toFixed(3) : fmtN(v)) : String(v));
function cjk(s) { let n = 0; for (const ch of s) if (ch.charCodeAt(0) > 0x2e80) n++; return n; }
const pc = (v) => (v === null || v === undefined ? '-' : Math.round(100 * v) + '%');

export function printArena(res) {
  const r = res.room, b = res.arms.baseline, c = res.arms.candidate;
  console.log(`[arena] 房间 ${r.kind === 'real' ? r.match + '（真局房间头）' : '生成'}：地图 ${r.map}，真人 ${r.humans}，配置 ${r.nTeamsHeader} 队 → 实际 ${r.nTeams} 队（各队人数 ${r.teamSizes.slice(1).join('/')}），内置 AI ${r.botsTeamed ? '分队' : '不分队'}；标签 ${r.tag}`);
  console.log(`  我方 ${r.squad.length} 席，分在队 ${Object.entries(r.squadTeams).map(([t, n]) => `${t}(${n})`).join(' ')}，主队 ${r.mainTeam}，同队路人 ${r.sameTeamStrangers}；其余真人原型 ${Object.entries(res.opp.count).map(([k, n]) => `${k}:${n}`).join(' ')}；计划变空壳 ${r.husksPlanned} 人；落点 ${res.spawn}` + (res.opp.replayUntil ? `；其余真人前 ${res.opp.replayUntil} 拍照录像` : ''));
  console.log(`  通道 ${res.channelNote}；跑到 t=${res.t1}${res.truncated ? '（时间预算截断）' : ''}${res.ended ? `（${res.ended}）` : ''}`);
  const cols = [];
  if (res.reality && res.reality.cps && res.reality.cps[0]) cols.push(['真局(录像)', res.reality.cps, null]);
  if (b) cols.push([`对照 ${b.strategy}`, b.cps, b]);
  if (c) cols.push([`处理 ${c.strategy}`, c.cps, c]);
  console.log('  各断面：我方人均地 ÷ 其余真人人均地 ｜ 我方在场 ｜ 其余真人在场占比 / 人均地 / 密度 ｜ 内置 AI 占陆地');
  for (const t of [...CHECKPOINTS, 'end']) {
    const parts = [];
    for (const [n, cps] of cols) {
      const s = cps[t];
      if (!s) continue;
      parts.push(`${n}：${show(s.relOthers)} ｜ ${s.squadAlive} ｜ ${pc(s.othersAliveShare)} / ${s.othersPerSeat} / ${s.othersDensity} ｜ ${pc(s.aiShare)}`);
    }
    if (parts.length) console.log(`    t=${t === 'end' ? res.t1 : t}  ` + parts.join('   '));
  }
  const arms = cols.filter((x) => x[2]);
  const head = ['指标'.padEnd(26), ...arms.map(([n]) => n.padStart(22)), ...(res.delta ? ['Δ(处理−对照)'.padStart(14)] : [])];
  console.log('  ' + head.join(' '));
  for (const [k, label] of [...ARENA_KEYS, ...PAIR_KEYS]) {
    const row = [label.padEnd(26 - Math.max(0, cjk(label))), ...arms.map(([, , m]) => show(m[k]).padStart(22)), ...(res.delta ? [show(res.delta[k]).padStart(14)] : [])];
    console.log('  ' + row.join(' '));
  }
  for (const [n, , m] of arms) {
    const cr = m.crowd, os = cr.onSquad;
    console.log(`  ${n}：落点 ${m.spawn.mode}${m.spawn.calls ? `（策略选点 ${m.spawn.picks}/${m.spawn.calls} 次生效）` : ''}；发出 ${m.issued} → 进录像 ${m.recorded}；阵亡拍 ${m.deadAt.map(([p, t]) => `${p}@${t}`).join(' ') || '无'}；` +
      `结束时领先队 ${m.cps.end.leadTeam}${m.over ? `，胜者队 ${m.winnerTeam}` : ''}；策略报错的席位 ${m.stratErrors.length}${m.stratErrors.length ? `（${m.stratErrors[0].first}）` : ''}`);
    console.log(`    对手：指令 ${cr.cmds}（生效 ${cr.ok}；无主地 ${cr.byClass.neutral} / AI ${cr.byClass.ai} / 真人 ${cr.byClass.hum} / 船 ${cr.byClass.boat} / 捐 ${cr.byClass.don}），补刀 ${cr.finish}，整仓捐款 ${cr.donBig}，变空壳 ${cr.left}；` +
      `打我方 ${os.n} 条（陆 ${os.land} / 船 ${os.boats}）、${fmtN(os.sent)} 兵：按兵 100~199‰ ${pc(os.pctBySent['100~199'])}、200~399‰ ${pc(os.pctBySent['200~399'])}、≥900‰ ${pc(os.pctBySent['>=900'])}；` +
      `对象密度 ≥100 ${pc(os.targetDensityBySent['>=100'])}、60~100 ${pc(os.targetDensityBySent['60~100'])}、<35 ${pc(os.targetDensityBySent['<35'])}（按条 ${pc(os.targetDensityByCount['<35'])}）；兵力 ≥2 倍 ${pc(os.ratio2BySent)}；4284 拍后 ${pc(os.after4284BySent)}`);
  }
  console.log(`  计时：CPU ${res.cpuMs} ms（真局参照 ${res.cpuRealityMs}、建房与出生 ${res.cpuSetupMs}），墙钟 ${res.wallMs} ms，堆 ${res.heapMB} MB`);
}
