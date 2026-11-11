// sim_replay.mjs — 用 c136-data/src/sim（引擎的 Node 移植）+ replay.txt 把一局真实组队对局逐拍重演出来。
// 模拟器原本只按「单人/大逃杀」路径建局；真实多人组队局有两处不同，这里按引擎源码（src/engine/live_game_js.js）补上，不改 c136-data：
//   1) 队伍分配 bj.ee()：aej（每个真人按颜色选第一/第二偏好队色）→ aKa（队色按受欢迎度排序）→ aek（同战队标签 [TAG] 的人整组进同一队；
//      最大战队人数 > floor(真人数/队数) 时队数减一，直到 2）→ ael（其余人按偏好填到人数上限 ceil(真人数/队数)）→ aem（队数 <8：bot 不入队，队号 0；=8：bot 按 1+p%8 轮流入队）。
//   2) 组队局配色 ad.dk → aKa()：从 511 号到 0 号每个玩家取 1 个随机数、按队色配色（单人局是每个 bot 取 3 个随机数）；
//      随机数流的位置决定 bot 的计时器和出生点，所以必须一致。
// 录像指令：0 选点 / 1 陆攻 / 2 捐兵 / 3 出船 / 4 追船·召回 / 5 撤回 / 8、9 离场 / 10 翻山进攻（6 表情、7 投票：不改变局面，忽略）。
// 校验：把重演得到的 terr/bal 与 in_game.log 里我方每条 [HL-TICK] t= terr= bal= 逐条比对（--check）。
// 用法：
//   node sim_replay.mjs <matchId> --check                 只做校验，打印吻合度
//   node sim_replay.mjs <matchId> --snap 10 --out DIR     每 10 拍导出全部真人的 terr/bal/进出兵 到 DIR/<id>-snap.tsv，事件到 DIR/<id>-events.tsv
// 作为模块：import { simulate } from './sim_replay.mjs'; simulate(id, { onTick(g, t), onCmd(ev) })
import fs from 'node:fs';
import path from 'node:path';
import { loadReplay } from './replay_cmds.mjs';

const DATA = process.env.C136_DATA || '/agent/repos/c136-data';
const SIM = await import(path.join(DATA, 'src/sim/sim/index.js'));
const { Game, loadMap, NEUTRAL, P_INNER, iV } = SIM;
const mj = (a, b) => (a >= 0 ? iV(a, b) : -iV(-a, b));
export { Game, NEUTRAL, P_INNER, iV, SIM, DATA };

// ---- 1) 队伍分配（引擎 dP：bj.ee 路径） ----
const TEAM_RGB = [[128, 128, 128], [255, 0, 0], [0, 255, 0], [0, 0, 255], [255, 255, 0], [255, 0, 255], [0, 255, 255], [255, 255, 255], [0, 0, 0]]; // bj.aU2
export const TEAM_COLOR_NAME = ['无队(灰)', '红', '绿', '蓝', '黄', '紫', '青', '白', '黑'];
const clanOf = (name) => { // bD.tK.a3r
  const s = String(name ?? '');
  const a = s.indexOf('[');
  if (a < 0) return null;
  const b = s.indexOf(']');
  if (b - a > 1 && b - a <= 8) return s.substring(a + 1, b).toUpperCase().trim();
  return null;
};
export function assignTeams(vu) {
  const ku = vu.humanCount, P = 512;
  let a0L = vu.numberTeams;
  const lH = [0, 1, 2, 3, 4, 5, 6, 7, 8];
  const fX = new Uint8Array(P);
  const colors = vu.colorsData.data ?? vu.colorsData, names = vu.playerNamesData.data ?? vu.playerNamesData;
  const a2F = new Uint8Array(ku), a2G = new Uint8Array(ku), pop = new Uint16Array(8), cnt = new Uint16Array(9);
  { // aej(a2F, a2G, pop, 1)
    const fZ = 8, h = new Uint16Array(fZ);
    for (let p = ku - 1; p >= 0; p--) {
      const c = colors[p];
      for (let ft = fZ; ft >= 1; ft--) h[ft - 1] = Math.abs(4 * (c >> 12) - TEAM_RGB[ft][0]) + Math.abs(4 * ((c >> 6) & 63) - TEAM_RGB[ft][1]) + Math.abs(4 * (c & 63) - TEAM_RGB[ft][2]);
      let best = 768;
      for (let ft = fZ - 1; ft >= 0; ft--) { const e = (ft + p) % fZ; if (h[e] < best) { best = h[e]; a2F[p] = e; } }
      pop[a2F[p]] += 4;
      best = 768;
      for (let ft = fZ - 1; ft >= 0; ft--) { const e = (ft + p) % fZ; if (h[e] < best && e !== a2F[p]) { best = h[e]; a2G[p] = e; } }
      pop[a2G[p]]++;
    }
  }
  { // aKa(pop)
    const fZ = 8;
    for (let i = fZ; i >= 0; i--) lH[i] = i;
    for (let i = fZ - 1; i >= 0; i--) pop[i]++;
    for (let i = 1; i <= fZ; i++) {
      let lr = 0;
      for (let ft = 1; ft < fZ; ft++) if (pop[ft] > pop[lr]) lr = ft;
      pop[lr] = 0;
      lH[i] = lr + 1;
    }
  }
  const clans = [], members = [], done = [];
  let biggest = 0;
  { // aek(cnt, a2F, a2G)
    const aes = 8, sp = new Uint16Array(aes);
    loop: for (let p = 0; p < ku; p++) {
      const tag = clanOf(names[p]);
      if (tag === null) continue;
      for (let i = clans.length - 1; i >= 0; i--) if (tag === clans[i]) { members[i].push(p); biggest = Math.max(biggest, members[i].length); continue loop; }
      clans.push(tag); done.push(false); members.push([p]); biggest = Math.max(biggest, 1);
    }
    while (a0L > 2 && biggest > iV(ku, a0L)) a0L--;
    for (let n = clans.length - 1; n >= 0; n--) {
      let fc = -1;
      for (let i = clans.length - 1; i >= 0; i--) if (!done[i] && (fc === -1 || members[i].length > members[fc].length)) fc = i;
      for (let i = aes - 1; i >= 0; i--) sp[i] = 1;
      for (let i = members[fc].length - 1; i >= 0; i--) { sp[a2F[members[fc][i]]] += 3; sp[a2G[members[fc][i]]]++; }
      for (let k = aes - 1; k >= 0; k--) {
        let e = fc % aes;
        for (let i = aes - 1; i >= 0; i--) if (sp[i] > sp[e]) e = i;
        let team = -1;
        for (let i = a0L; i > 0; i--) if (lH[i] === e + 1) { team = i; break; }
        sp[e] = 0;
        if (team === -1) continue;
        let uv = 0;
        for (let i = a0L; i > 0; i--) if (cnt[team] > cnt[i]) uv++;
        if (uv === a0L - 1) continue;
        for (let i = members[fc].length - 1; i >= 0; i--) { cnt[team]++; fX[members[fc][i]] = team; }
        break;
      }
      done[fc] = true;
    }
  }
  { // ael(a2F, a2G, cnt)
    const fZ = 8;
    let border = iV(ku, a0L);
    if (ku % a0L > 0) border++;
    const aew = new Uint8Array(fZ + 1);
    for (let ft = fZ; ft >= 1; ft--) aew[lH[ft]] = ft;
    for (let p = 0; p < ku; p++) { const t = aew[a2F[p] + 1]; if (fX[p] === 0 && t <= a0L && cnt[t] < border) { cnt[t]++; fX[p] = t; } }
    for (let p = 0; p < ku; p++) { const t = aew[a2G[p] + 1]; if (fX[p] === 0 && t <= a0L && cnt[t] < border) { cnt[t]++; fX[p] = t; } }
    for (let ft = a0L; ft >= 1; ft--) for (let p = ku - 1; p >= 0; p--) { if (cnt[ft] >= border) break; if (fX[p] === 0) { cnt[ft]++; fX[p] = ft; } }
  }
  const humanTeams = a0L;
  let botTeams = false;
  if (a0L < 8) a0L++; // aem：bot 不入队（队号 0）
  else { botTeams = true; for (let p = ku; p < P; p++) fX[p] = 1 + (p % a0L); }
  const aDn = new Uint8Array(P); // aeg：每个玩家的队色下标
  for (let p = 0; p < P; p++) aDn[p] = lH[fX[p]];
  return { teams: fX, humanTeams, nTeamsEngine: a0L, botTeams, lH, aDn, counts: Array.from(cnt.subarray(1, humanTeams + 1)), clans: clans.map((c, i) => ({ tag: c, members: members[i] })) };
}

// ---- 2) 组队局配色（引擎 cX：ad.dk → aKa → aKd/aKe/aKg/aKh） ----
const aKK = [[100, 100, 100], [144, 0, 0], [0, 128, 0], [0, 0, 144], [128, 128, 0], [128, 0, 128], [0, 128, 128], [196, 196, 196], [0, 0, 0]];
const aKL = [[4, 4, 4, 20], [4, 0, 0, 27], [0, 4, 0, 31], [0, 0, 4, 27], [4, 4, 0, 31], [4, 0, 4, 31], [0, 4, 4, 31], [4, 4, 4, 14], [4, 4, 4, 13]];
let TEAM_CTX = null;
const origSetupColors = Game.prototype.setupColors;
Game.prototype.setupColors = function () {
  if (!TEAM_CTX) return origSetupColors.call(this);
  const rng = this.rng, P = 512, R = this.colR, G = this.colG, B = this.colB, aDn = TEAM_CTX.aDn;
  for (let i = P - 1; i >= 0; i--) {
    const ej = aDn[i];
    const lp = iV((aKL[ej][3] + 1) * rng.next(), 32768);
    R[i] = aKK[ej][0] + lp * aKL[ej][0];
    G[i] = aKK[ej][1] + lp * aKL[ej][1];
    B[i] = aKK[ej][2] + lp * aKL[ej][2];
  }
  for (let i = P - 1; i >= 0; i--) {
    const g = iV(R[i] + G[i] + B[i], 3);
    R[i] += mj(g - R[i], 2); G[i] += mj(g - G[i], 2); B[i] += mj(g - B[i], 2);
    R[i] -= R[i] % 4; G[i] -= G[i] % 4; B[i] -= B[i] % 4;
  }
  for (let i = 0; i < P; i++) { R[i] += i >> 7; G[i] += (i >> 5) & 3; B[i] += (i >> 3) & 3; this.colLow[i] = i & 7; }
  for (let i = 0; i < P; i++) {
    const r = R[i], g = G[i], b = B[i];
    if (r + g + b >= 60) { this.borR[i] = Math.max(r - 40, r & 3); this.borG[i] = Math.max(g - 40, g & 3); this.borB[i] = Math.max(b - 40, b & 3); } else { this.borR[i] = r + 40; this.borG[i] = g + 40; this.borB[i] = b + 40; }
  }
  for (let i = 0; i < P; i++) {
    const r = R[i], g = G[i], b = B[i];
    if (r + g + b >= 688) { this.froR[i] = r - 88; this.froG[i] = g - 88; this.froB[i] = b - 88; } else { this.froR[i] = Math.min(r + 88, 252 + (r & 3)); this.froG[i] = Math.min(g + 88, 252 + (g & 3)); this.froB[i] = Math.min(b + 88, 252 + (b & 3)); }
  }
};

export function mapOf(vu) {
  const mapIdx = vu.mapType === 1 ? (vu.mapRealisticIndex <= 9 ? 10 + vu.mapRealisticIndex : 12 + vu.mapRealisticIndex) : (vu.mapProceduralIndex <= 9 ? vu.mapProceduralIndex : 10 + vu.mapProceduralIndex);
  return { mapIdx, mapSeed: vu.mapType === 1 ? 0 : vu.mapSeed };
}

// ---- 3) 重演 ----
// opts: { onTick(g, t), onEvent(ev), maxTick, noTeamColors（调试：不用组队配色）, noTeams（调试） }
//       skipCmd(cmd, g, idx)：返回 true 的指令不执行（只给「去掉某几条指令」的一阶推演 whatif_drop.mjs 用；正常重演不传）
export function simulate(matchId, opts = {}) {
  const d = loadReplay(matchId);
  const vu = d.vu, H = vu.humanCount;
  const names = vu.playerNamesData ? (vu.playerNamesData.data ?? vu.playerNamesData) : [];
  const { mapIdx, mapSeed } = mapOf(vu);
  const map = loadMap(mapIdx, mapSeed);
  const teamGame = vu.gameMode === 1 && !vu.isZombieMode && !opts.noTeams;
  const T = teamGame ? assignTeams(vu) : null;
  TEAM_CTX = teamGame && !opts.noTeamColors ? T : null;
  const colors = vu.colorsData ? Array.from((vu.colorsData.data ?? vu.colorsData).subarray ? (vu.colorsData.data ?? vu.colorsData).subarray(0, H) : (vu.colorsData.data ?? vu.colorsData).slice(0, H)) : [0];
  const g = new Game({
    map, humans: H, players: vu.playerCount, difficulty: H > 1 ? 0 : vu.botDifficultyValue, spawnSeed: vu.spawningSeed, selectableSpawn: !!vu.selectableSpawn,
    battleRoyaleMode: vu.battleRoyaleMode, humanColors: colors, passableWater: vu.passableWater, passableMountains: vu.passableMountains,
    teams: T ? Array.from(T.teams.subarray(0, H)) : undefined, nTeams: T ? T.nTeamsEngine : 0, botTeams: T ? T.botTeams : undefined,
  });
  TEAM_CTX = null;
  g.me = vu.selectedPlayer;
  const deathT = new Int32Array(512).fill(-1), leftT = new Int32Array(H).fill(-1);
  const stats = { cmds: 0, attackOk: 0, attackFail: 0, donateOk: 0, donateFail: 0, boatOk: 0, boatFail: 0, mountain: 0, ignored: 0, retreat: 0 };
  const emit = opts.onEvent || null;
  const execCmd = (c) => {
    const { id, player, dX, dZ } = c;
    stats.cmds++;
    if (id === 0) {
      g.chooseSpawn(dX % g.W, Math.floor(dX / g.W), player, false);
    } else if (id === 1) {
      const B0 = g.bal[player], L0 = g.terr[player];
      const tgt = Math.min(dZ, NEUTRAL);
      const tB = tgt < NEUTRAL ? g.bal[tgt] : 0, tL = tgt < NEUTRAL ? g.terr[tgt] : 0;
      const ok = g.attack(dX, dZ, player);
      if (ok) stats.attackOk++; else stats.attackFail++;
      if (emit) emit({ t: g.t, type: 'attack', p: player, q: tgt, pct: dX, ok, B0, L0, troops: ok ? g.attackTroopsTmp : 0, fee: ok ? g.attackFeeTmp : 0, tB, tL });
    } else if (id === 2) {
      const B0 = g.bal[player], L0 = g.terr[player], qB0 = g.bal[dZ], qL0 = g.terr[dZ];
      const ok = g.donate(dX, dZ, player);
      if (ok) stats.donateOk++; else stats.donateFail++;
      if (emit) emit({ t: g.t, type: 'donate', p: player, q: dZ, pct: dX, ok, B0, L0, qB0, qL0, got: g.bal[dZ] - qB0, fee: ok ? iV(64 * B0, 1024) : 0 });
    } else if (id === 3) {
      const B0 = g.bal[player], L0 = g.terr[player];
      const water = dZ >> 3, dir = dZ & 7;
      const ok = g.boat(dX, water, dir, player);
      if (ok) stats.boatOk++; else stats.boatFail++;
      if (emit) {
        const route = ok ? g.bRoute[g.boatN - 1] : null;
        const dest = route ? route[route.length - 1] + g.dir4[dir] : water + g.dir4[dir];
        const owner = dest >= 0 && dest < g.N ? (g.px[dest] >= P_INNER ? g.own[dest] : NEUTRAL) : NEUTRAL;
        emit({ t: g.t, type: 'boat', p: player, q: owner, pct: dX, ok, B0, L0, troops: ok ? g.attackTroopsTmp : 0, fee: ok ? g.attackFeeTmp : 0, routeLen: route ? route.length : 0, dest });
      }
    } else if (id === 4) {
      const B0 = g.bal[player], L0 = g.terr[player];
      if (dX === 849) g.recall(dZ, player); else g.chase(dX, dZ, player);
      if (emit) emit({ t: g.t, type: dX === 849 ? 'recall' : 'chase', p: player, q: -1, pct: dX, ok: true, B0, L0 });
    } else if (id === 5) {
      if (dX !== 513) { const back = dX < 512 || dX === NEUTRAL ? g.attackTroopsOn(player, Math.min(dX, NEUTRAL)) : 0; const ok = g.retreat(dX, player); stats.retreat++; if (emit) emit({ t: g.t, type: 'retreat', p: player, q: Math.min(dX, NEUTRAL), ok, troops: back }); }
    } else if (id === 8 || id === 9) {
      if (g.spawnPhase) {
        g.eliminate(player);
        let n = g.aliveCount;
        for (let i = n - 1; i >= 0; i--) if (g.alive[g.aliveList[i]] === 0) g.aliveList[i] = g.aliveList[--n];
        g.aliveCount = n;
        deathT[player] = 0;
      } else { if (player < H && leftT[player] < 0) leftT[player] = g.t; g.leave(player); }
      if (emit) emit({ t: g.t, type: 'leave', p: player, q: -1, ok: true, L0: g.terr[player], B0: g.bal[player] });
    } else if (id === 10) {
      // 翻山进攻（引擎 qj.i2）：本项目 13 局里一条都没有；这里不重演，只计数，出现即视为重演不可信。
      stats.mountain++;
      if (emit) emit({ t: g.t, type: 'mountain-unsupported', p: player, q: dX % 1024, pct: dX >> 10, ok: false });
    } else stats.ignored++;
  };
  let iv = 0, iw = 0, ix = 0, iy = 0;
  const step = () => {
    if (iv >= d.ja.length) return false;
    const jZ = d.ja[iv];
    if (d.jY[iv]) { for (let a = iw; a < iw + jZ; a++) { if (opts.skipCmd && opts.skipCmd(d.cmds[a], g, a)) continue; execCmd(d.cmds[a]); } iw += jZ; iv++; } else if (++ix >= jZ) { iv++; ix = 0; }
    return true;
  };
  if (vu.selectableSpawn) {
    const jJ = H <= 2 ? 30 : H <= 50 ? 40 : 50;
    while (iy <= jJ) { if (!step()) break; if (iy === jJ) g.endSpawnPhase(); iy++; }
  }
  if (opts.onStart) opts.onStart(g, { d, T, names, H });
  const maxTick = opts.maxTick ?? 1e9;
  let overAt = -1;
  while (g.t < maxTick && step()) {
    const t0 = g.t;
    g.tick();
    if (g.over && overAt < 0) overAt = g.t;
    if (g.t === t0) break; // 模拟器判定结束后不再推进
    for (let i = 0; i < 512; i++) if (deathT[i] < 0 && g.alive[i] === 0 && (i < g.players)) deathT[i] = g.t;
    if (opts.onTick) opts.onTick(g, g.t);
  }
  return { g, d, vu, H, names, T, stats, deathT, leftT, overAt, endTick: g.t, mapIdx, mapSeed };
}

// ---- 4) 日志里的 [HL-TICK]（真实对局的 terr/bal 观测值） ----
export function parseTicks(matchId) {
  const out = [];
  const re = /\[([^\]]+)\] \[HL-TICK\] t=(\d+) terr=(\d+)\([^)]*\) bal=(\d+)/;
  for (const line of fs.readFileSync(path.join(DATA, 'bundles', matchId, 'in_game.log'), 'utf8').split('\n')) {
    const m = re.exec(line);
    if (m) out.push({ bot: m[1], t: +m[2], terr: +m[3], bal: +m[4] });
  }
  return out;
}
export const bare = (n) => String(n ?? '').replace(/\[[^\]]*\]/g, '').trim().toLowerCase();
export function botIds(names, H, botNames) {
  const m = new Map();
  for (const b of botNames) { const hits = []; for (let p = 0; p < H; p++) if (bare(names[p]) === b.toLowerCase()) hits.push(p); m.set(b, hits.length === 1 ? hits[0] : -1); }
  return m;
}

if (import.meta.url === `file://${process.argv[1]}`) {
  const args = process.argv.slice(2);
  const id = args[0];
  const flag = (k) => args.includes(k);
  const val = (k, d) => (args.includes(k) ? args[args.indexOf(k) + 1] : d);
  const ticks = parseTicks(id);
  const byT = new Map();
  for (const x of ticks) { if (!byT.has(x.t)) byT.set(x.t, []); byT.get(x.t).push(x); }
  let ids = null;
  const cmp = [];
  const snapEvery = +val('--snap', 0), outDir = val('--out', '/tmp/c136-r05/sim');
  const snapRows = [], evRows = [];
  const t0 = Date.now();
  const R = simulate(id, {
    maxTick: +val('--max', 1e9), noTeamColors: flag('--no-team-colors'), noTeams: flag('--no-teams'),
    onStart: (g, ctx) => { ids = botIds(ctx.names, ctx.H, [...new Set(ticks.map((x) => x.bot))]); },
    onTick: (g, t) => {
      const L = byT.get(t);
      if (L) for (const x of L) { const p = ids.get(x.bot); if (p >= 0) cmp.push({ ...x, p, sTerr: g.terr[p], sBal: g.bal[p] }); }
      if (snapEvery && t % snapEvery === 0) for (let p = 0; p < g.humans; p++) if (g.alive[p]) snapRows.push([t, p, g.terr[p], g.bal[p], g.state[p], g.totalAttackTroops(p), g.boatCount[p]].join('\t'));
    },
    onEvent: snapEvery ? (e) => evRows.push([e.t, e.type, e.p, e.q, e.pct ?? '', e.ok ? 1 : 0, e.B0 ?? '', e.L0 ?? '', e.troops ?? e.got ?? '', e.fee ?? '', e.tB ?? e.qB0 ?? '', e.tL ?? e.qL0 ?? ''].join('\t')) : null,
  });
  const exact = cmp.filter((x) => x.terr === x.sTerr && x.bal === x.sBal).length, terrOk = cmp.filter((x) => x.terr === x.sTerr).length;
  const firstBad = cmp.find((x) => x.terr !== x.sTerr || x.bal !== x.sBal);
  console.log(`# ${id} 地图 ${R.mapIdx}_${R.mapSeed} ${R.g.W}x${R.g.H} land=${R.g.land} 真人=${R.H} 队数(真人队)=${R.T ? R.T.humanTeams : 0} 各队人数=${R.T ? R.T.counts.join('/') : '-'} 重演到 t=${R.endTick}（录像 ${R.d.ja.length} 块；模拟器判定结束 t=${R.overAt}） 用时 ${Date.now() - t0}ms`);
  console.log(`# 指令统计 ${JSON.stringify(R.stats)}`);
  console.log(`# [HL-TICK] 比对：可比 ${cmp.length} 条（日志 ${ticks.length} 条），terr 与 bal 全等 ${exact} 条（${cmp.length ? (100 * exact / cmp.length).toFixed(1) : 0}%），terr 相等 ${terrOk} 条`);
  if (firstBad) console.log(`# 第一条不等：t=${firstBad.t} ${firstBad.bot}(#${firstBad.p}) 日志 terr=${firstBad.terr} bal=${firstBad.bal} / 重演 terr=${firstBad.sTerr} bal=${firstBad.sBal}`);
  if (flag('--detail')) for (const x of cmp.slice(0, +val('--n', 60))) console.log(`  t=${x.t} ${x.bot}(#${x.p}) 日志 ${x.terr}/${x.bal} 重演 ${x.sTerr}/${x.sBal} ${x.terr === x.sTerr && x.bal === x.sBal ? 'OK' : 'DIFF'}`);
  if (snapEvery) {
    fs.mkdirSync(outDir, { recursive: true });
    fs.writeFileSync(path.join(outDir, `${id}-snap.tsv`), 't\tplayer\tterr\tbal\tstate\tatkOut\tboats\n' + snapRows.join('\n') + '\n');
    fs.writeFileSync(path.join(outDir, `${id}-events.tsv`), 't\ttype\tp\tq\tpct\tok\tB0\tL0\ttroops\tfee\tqB0\tqL0\n' + evRows.join('\n') + '\n');
    console.log(`# 已写 ${outDir}/${id}-snap.tsv（${snapRows.length} 行）、${id}-events.tsv（${evRows.length} 行）`);
  }
}
