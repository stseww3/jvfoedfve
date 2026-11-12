#!/usr/bin/env node
// resim_r08.mjs — R08 的副本：原件是统筹分发的 /agent/repos/c136-data/src/tools/resim.mjs（逻辑未改）。
// 只改了四处：(1) 输出写到 agents/R08/out/<局>/resim.json；(2) --replay-from <局2>：录像取自同一房间的另一个对局包
// （例如 B043 自己的录像只到 t=819，同房的 A062 录到 t=6568）；(3) --peer <局2>：把同房另一支编队的号也按名字认出来，
// 写进 squad（键名前加「局2:」），这样两边的号都有在途兵、邻居、额度的逐拍明细；--peer-tag <标签>：不读对方的对局包，
// 只按本局录像里名字带的战队标签（如 APEX）认出同房另一支编队（对方的包在验证集里时用）。
// (4) resim() 的 opts.cmdFilter：返回 false 的录像指令不执行（cfprobe.mjs 的反事实探针用；不传时重演和原来逐位一样）。
// resim.mjs — 全量重放一局：用 c136-data/src/sim 的纯 JS 引擎（512 个玩家）把 replay.txt 从头跑一遍，
// 输出全场账本到 out/cache/<mid>-resim.json，并把本队每个号的地/兵与 traj.csv 逐快照核对。
//
//   bash c136-review/tools/run-heavy.sh node resim.mjs <matchId> [--until T] [--maps t1,t2,...] [--quiet]
//
// 重放得到而录像/日志里没有的东西：
//   · 每个真人的队伍（按引擎 dP.ee 的配色 + 战队标签分队算法移植，见 assignTeams）
//   · 所有真人每 10 拍的地、兵；各队总地
//   · 本队每个号每 10 拍：在外的进攻兵（对谁、多少）、压在身上的进攻兵（谁、多少）、邻居接触边数、船
//   · 逐对战损账（每 30 拍一窗）：攻方烧掉多少兵、拿到多少地、守方余额掉多少、守方反击槽掉多少
//   · 每条指令是否真的生效（no-op / 被拒）、成交兵数与手续费、捐款时受捐方的额度
//   · 每次死亡前的状态与在场攻击者
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const DATA = process.env.C136_DATA || '/agent/repos/c136-data';
const HERE = path.dirname(fileURLToPath(import.meta.url));
const OUT = path.join(HERE, '..', 'out');

const SIM = await import(path.join(DATA, 'src/sim/sim/index.js'));
const LIB = await import(path.join(DATA, 'src/sim/tools/c102-replay-lib.mjs'));
const { Game, loadMap, NEUTRAL, P_INNER, T_LAND, iV } = SIM;
const { decodeReplay, mapOf } = LIB;

// 组队局的配色（引擎 cX.aKa）：512 个玩家每人只抽 1 个随机数（倒序），而不是自由混战的「每个 AI 抽 3 个」。
// 随机数序列决定 AI 的出生点，所以必须照做；颜色本身还被船的寻路当作「水体编号」读（bodyId）。
const AKK = [[100, 100, 100], [144, 0, 0], [0, 128, 0], [0, 0, 144], [128, 128, 0], [128, 0, 128], [0, 128, 128], [196, 196, 196], [0, 0, 0]];
const AKL = [[4, 4, 4, 20], [4, 0, 0, 27], [0, 4, 0, 31], [0, 0, 4, 27], [4, 4, 0, 31], [4, 0, 4, 31], [0, 4, 4, 31], [4, 4, 4, 14], [4, 4, 4, 13]];
const mj = (a, b) => (a >= 0 ? iV(a, b) : -iV(-a, b));
let TEAM_CTX = null;
class TGame extends Game {
  // 引擎 dQ（bk）：各队总地 a5c 每 32 拍才重算一次（bk.ee 在每拍末尾 ++w0>=32 时 aYJ），
  // 「领先队占 80% 后给 AI 派猎杀目标」(jd.jp) 和「领先队占 90% 后 AI 提速」(je.ee) 读的都是这份旧值。
  teamCacheGet() {
    if (!this.teamCache) {
      this.teamCache = new Uint32Array(this.nTeams + 2);
      this.teamW0 = 0;
      for (let i = this.aliveCount - 1; i >= 0; i--) this.teamCache[this.teams[this.aliveList[i]]] += 1;
    }
    return this.teamCache;
  }

  teamCacheRefresh() {
    const a5c = this.teamCacheGet();
    a5c.fill(0);
    const list = this.aliveList, teams = this.teams, terr = this.terr;
    for (let i = this.aliveCount - 1; i >= 0; i--) a5c[teams[list[i]]] += terr[list[i]];
  }

  tick() {
    if (this.over || this.spawnPhase) return;
    super.tick();
    if (this.teamGame) {
      this.teamCacheGet();
      if (++this.teamW0 >= 32) { this.teamW0 = 0; this.teamCacheRefresh(); }
    }
  }

  teamLeadCached() {
    const a5c = this.teamCacheGet();
    let lead = 0;
    for (let t = this.nTeams; t > 0; t--) if (a5c[t] > a5c[lead]) lead = t;
    return lead;
  }

  // bk.lR()：领先的是真队伍就返回它的地；领先的是 0 号（未入队的 AI）就返回 max(最大真队伍, 榜首个人)
  teamLeadLandCached() {
    const a5c = this.teamCacheGet();
    const lead = this.teamLeadCached();
    if (lead !== 0) return a5c[lead];
    let b = -1;
    for (let t = this.nTeams; t >= 1; t--) if (b === -1 || a5c[t] > a5c[b]) b = t;
    const ea = this.terr[this.rank[0]];
    return b === -1 ? ea : Math.max(a5c[b], ea);
  }

  teamHuntTick() {
    if (!this.teamGame || this.t % 109 !== 9 || this.aliveCount < 20) return;
    if (this.teamLeadLandCached() < iV(8 * this.land, 10)) return;
    const lead = this.teamLeadCached();
    if (lead === 0) return;
    const list = this.aliveList, teams = this.teams, memo = this.boatMemo;
    const out = [];
    for (let i = 0; i < this.aliveCount; i++) if (teams[list[i]] !== lead) out.push(list[i]);
    if (out.length === 0) return;
    let k = this.rng.int(out.length);
    for (let i = 0; i < this.aliveCount; i++) {
      const p = list[i], q = out[k];
      if (this.isEnemyOf(p, q) && memo[p] === NEUTRAL) {
        memo[p] = q;
        k = (k + 1) % out.length;
      }
    }
    if (this.onHunt) this.onHunt(lead, out.length);
  }

  endgameSpeedTick() {
    if (!this.teamGame) return super.endgameSpeedTick();
    if (this.endgameFast || this.t % 30 !== 7) return;
    if (this.teamLeadLandCached() < iV(90 * this.land, 100)) return;
    this.endgameFast = 1;
    const lead = this.teamLeadCached();
    if (lead !== 0) {
      const list = this.aliveList;
      const members = [];
      for (let i = 0; i < this.aliveCount; i++) if (this.teams[list[i]] === lead) members.push(list[i]);
      if (members.length) {
        const mU = Math.min(100 + (members.length - 1) * 10, 400);
        for (const p of members) this.setBotPeriod(p, mU);
      }
    }
    this.setBotPeriod(this.rank[0], 100);
    if (this.onFast) this.onFast(lead);
  }

  setupColors() {
    if (!TEAM_CTX) return super.setupColors();
    const rng = this.rng, P = 512;
    const R = this.colR, G = this.colG, B = this.colB;
    const aDn = TEAM_CTX.aDn;
    for (let i = P - 1; i >= 0; i--) {
      const ej = aDn[i];
      const lp = iV((AKL[ej][3] + 1) * rng.next(), 32768);
      R[i] = AKK[ej][0] + lp * AKL[ej][0];
      G[i] = AKK[ej][1] + lp * AKL[ej][1];
      B[i] = AKK[ej][2] + lp * AKL[ej][2];
    }
    for (let i = P - 1; i >= 0; i--) {
      const g = iV(R[i] + G[i] + B[i], 3);
      R[i] += mj(g - R[i], 2);
      G[i] += mj(g - G[i], 2);
      B[i] += mj(g - B[i], 2);
      R[i] -= R[i] % 4;
      G[i] -= G[i] % 4;
      B[i] -= B[i] % 4;
    }
    for (let i = 0; i < P; i++) {
      R[i] += i >> 7;
      G[i] += (i >> 5) & 3;
      B[i] += (i >> 3) & 3;
      this.colLow[i] = i & 7;
    }
    for (let i = 0; i < P; i++) {
      const r = R[i], g = G[i], b = B[i];
      if (r + g + b >= 60) {
        this.borR[i] = Math.max(r - 40, r & 3);
        this.borG[i] = Math.max(g - 40, g & 3);
        this.borB[i] = Math.max(b - 40, b & 3);
      } else {
        this.borR[i] = r + 40;
        this.borG[i] = g + 40;
        this.borB[i] = b + 40;
      }
    }
    for (let i = 0; i < P; i++) {
      const r = R[i], g = G[i], b = B[i];
      if (r + g + b >= 688) {
        this.froR[i] = r - 88;
        this.froG[i] = g - 88;
        this.froB[i] = b - 88;
      } else {
        this.froR[i] = Math.min(r + 88, 252 + (r & 3));
        this.froG[i] = Math.min(g + 88, 252 + (g & 3));
        this.froB[i] = Math.min(b + 88, 252 + (b & 3));
      }
    }
  }
}

const TEAM_RGB = [[128, 128, 128], [255, 0, 0], [0, 255, 0], [0, 0, 255], [255, 255, 0], [255, 0, 255], [0, 255, 255], [255, 255, 255], [0, 0, 0]];

// 引擎 a5N.a3r：名字里第一个 [ 到第一个 ] 之间（1~7 个字符）算战队标签
export function clanOf(name) {
  const s = String(name ?? '');
  const fO = s.indexOf('[');
  if (fO < 0) return null;
  const fd = s.indexOf(']');
  if (fd - fO > 1 && fd - fO <= 8) return s.substring(fO + 1, fd).toUpperCase().trim();
  return null;
}

// 引擎 dP.ee（aej → aKa → aek → ael → aem）的移植。返回 {fX: 每个真人的队号, nTeams, lH: 队号→颜色号, botsTeamed}
export function assignTeams(names, colors, ku, nTeamsHeader) {
  const L = 9;
  let a0L = nTeamsHeader;
  const lH = Array.from({ length: L }, (_, i) => i);
  const fX = new Uint8Array(ku);
  const a2F = new Uint8Array(ku), a2G = new Uint8Array(ku);
  const aeh = new Uint16Array(8);
  const aei = new Uint16Array(L);
  {
    const fZ = L - 1;
    const h = new Uint16Array(fZ);
    for (let aC = ku - 1; aC >= 0; aC--) {
      const c = colors[aC] | 0;
      for (let ft = fZ; ft >= 1; ft--) {
        h[ft - 1] = Math.abs(4 * (c >> 12) - TEAM_RGB[ft][0]) + Math.abs(4 * ((c >> 6) & 63) - TEAM_RGB[ft][1]) + Math.abs(4 * (c & 63) - TEAM_RGB[ft][2]);
      }
      let aer = 768;
      for (let ft = fZ - 1; ft >= 0; ft--) {
        const e = (ft + aC) % fZ;
        if (h[e] < aer) { aer = h[e]; a2F[aC] = e; }
      }
      aeh[a2F[aC]] += 4;
      aer = 768;
      for (let ft = fZ - 1; ft >= 0; ft--) {
        const e = (ft + aC) % fZ;
        if (h[e] < aer && e !== a2F[aC]) { aer = h[e]; a2G[aC] = e; }
      }
      aeh[a2G[aC]]++;
    }
  }
  {
    const fZ = L - 1;
    for (let aC = fZ - 1; aC >= 0; aC--) aeh[aC]++;
    for (let aC = 1; aC <= fZ; aC++) {
      let lr = 0;
      for (let ft = 1; ft < fZ; ft++) if (aeh[ft] > aeh[lr]) lr = ft;
      aeh[lr] = 0;
      lH[aC] = lr + 1;
    }
  }
  const clans = [];
  {
    const aes = L - 1;
    const sp = new Uint16Array(aes);
    const aet = [], a3p = [], aev = [];
    let aeu = 0;
    loop: for (let aC = 0; aC < ku; aC++) {
      const a3q = clanOf(names[aC]);
      if (a3q !== null) {
        for (let ft = a3p.length - 1; ft >= 0; ft--) {
          if (a3q === a3p[ft]) { aev[ft].push(aC); aeu = Math.max(aeu, aev[ft].length); continue loop; }
        }
        a3p.push(a3q); aet.push(false); aev.push([aC]); aeu = Math.max(aeu, 1);
      }
    }
    while (a0L > 2 && aeu > iV(ku, a0L)) a0L--;
    for (let ft = a3p.length - 1; ft >= 0; ft--) {
      let fc = -1;
      for (let ej = a3p.length - 1; ej >= 0; ej--) {
        if (!aet[ej] && (fc === -1 || aev[ej].length > aev[fc].length)) fc = ej;
      }
      for (let ej = aes - 1; ej >= 0; ej--) sp[ej] = 1;
      for (let ej = aev[fc].length - 1; ej >= 0; ej--) { sp[a2F[aev[fc][ej]]] += 3; sp[a2G[aev[fc][ej]]]++; }
      let got = 0;
      for (let aC = aes - 1; aC >= 0; aC--) {
        let e = fc % aes;
        for (let ej = aes - 1; ej >= 0; ej--) if (sp[ej] > sp[e]) e = ej;
        let o7 = -1;
        for (let ej = a0L; ej > 0; ej--) if (lH[ej] === e + 1) { o7 = ej; break; }
        sp[e] = 0;
        if (o7 === -1) continue;
        let uv = 0;
        for (let ej = a0L; ej > 0; ej--) if (aei[o7] > aei[ej]) uv++;
        if (uv === a0L - 1) continue;
        for (let ej = aev[fc].length - 1; ej >= 0; ej--) { aei[o7]++; fX[aev[fc][ej]] = o7; }
        got = o7;
        break;
      }
      aet[fc] = true;
      clans.push({ tag: a3p[fc], size: aev[fc].length, team: got });
    }
  }
  {
    const fZ = L - 1;
    let border = iV(ku, a0L);
    if (ku % a0L > 0) border++;
    const aew = new Uint8Array(fZ + 1);
    for (let ft = fZ; ft >= 1; ft--) aew[lH[ft]] = ft;
    for (let aC = 0; aC < ku; aC++) {
      const iv = aew[a2F[aC] + 1];
      if (fX[aC] === 0 && iv <= a0L && aei[iv] < border) { aei[iv]++; fX[aC] = iv; }
    }
    for (let aC = 0; aC < ku; aC++) {
      const iv = aew[a2G[aC] + 1];
      if (fX[aC] === 0 && iv <= a0L && aei[iv] < border) { aei[iv]++; fX[aC] = iv; }
    }
    for (let ft = a0L; ft >= 1; ft--) {
      for (let aC = ku - 1; aC >= 0; aC--) {
        if (aei[ft] >= border) break;
        if (fX[aC] === 0) { aei[ft]++; fX[aC] = ft; }
      }
    }
  }
  return { fX: Array.from(fX), nTeams: a0L, lH, botsTeamed: a0L >= 8, clans, sizes: Array.from(aei).slice(0, a0L + 1) };
}

function readCsv(file) {
  if (!fs.existsSync(file)) return [];
  const lines = fs.readFileSync(file, 'utf8').split('\n').filter(Boolean);
  const head = lines[0].split(',');
  return lines.slice(1).map((l) => {
    const c = l.split(',');
    const o = {};
    head.forEach((h, i) => { o[h] = c[i]; });
    return o;
  });
}

export function resim(mid, opts = {}) {
  const bdir = path.join(DATA, 'bundles', mid);
  const rdir = path.join(DATA, 'bundles', opts.replayFrom || mid);
  const d = decodeReplay(fs.readFileSync(path.join(rdir, 'replay.txt'), 'utf8'));
  const vu = d.vu;
  const H = vu.humanCount;
  const names = vu.playerNamesData ? Array.from(vu.playerNamesData).slice(0, H).map((s) => String(s ?? '')) : [];
  const colors = vu.colorsData ? Array.from(vu.colorsData).slice(0, H) : new Array(H).fill(0);
  const teamGame = vu.gameMode !== 0 && vu.numberTeams >= 2;
  const ta = teamGame ? assignTeams(names, colors, H, vu.numberTeams) : { fX: new Array(H).fill(0), nTeams: 0, lH: [], botsTeamed: false, clans: [], sizes: [] };
  const { mapIdx, mapSeed } = mapOf(vu);
  const map = loadMap(mapIdx, mapSeed);
  if (teamGame) {
    const aDn = new Uint8Array(512);
    for (let p = 0; p < 512; p++) {
      const team = p < H ? ta.fX[p] : ta.botsTeamed ? 1 + (p % ta.nTeams) : 0;
      aDn[p] = ta.lH[team];
    }
    TEAM_CTX = { aDn };
  } else TEAM_CTX = null;
  const g = new TGame({
    map,
    humans: H,
    players: vu.playerCount,
    difficulty: H > 1 ? 0 : vu.botDifficultyValue,
    spawnSeed: vu.spawningSeed,
    selectableSpawn: !!vu.selectableSpawn,
    battleRoyaleMode: vu.battleRoyaleMode,
    humanColors: vu.colorsData ? Array.from(vu.colorsData.subarray(0, H)) : [0],
    teams: teamGame ? ta.fX : undefined,
    nTeams: ta.nTeams,
    botTeams: ta.botsTeamed,
  });
  g.me = vu.selectedPlayer;

  // 本队：traj.csv 里出现的名字，按名字后缀对上玩家号
  const traj = readCsv(path.join(bdir, 'traj.csv'));
  const results = readCsv(path.join(bdir, 'results.csv'));
  const botNames = [...new Set([...traj.map((r) => r.bot), ...results.map((r) => r.bot)])];
  const squad = {};
  for (const b of botNames) {
    let id = -1;
    for (let p = 0; p < H; p++) if (names[p].trim().toLowerCase().endsWith(b.toLowerCase())) { id = p; break; }
    const r = results.find((x) => x.bot === b);
    if (r && r.meId !== undefined && r.meId !== '' && +r.meId !== id) squad[b] = { id, meId: +r.meId, mismatch: true };
    else squad[b] = { id, meId: r ? +r.meId : id };
  }
  // 日志标签和录像里的名字对不上的号（B019 有 7 个）：按 facts.json 里还原出的玩家号认；认得对不对由下面的 traj 核对把关
  const factsPath = path.join(OUT, mid, 'facts.json');
  // 混了几个物理房间的包（B009）：录像只属于其中一个房间。别的房间的号玩家号会撞上录像里的陌生人，不能按玩家号硬认
  const otherRoomLabels = new Set();
  const roomsPath = path.join(DATA, 'src', 'tools', 'rooms-discovery.json');
  if (!opts.replayFrom && fs.existsSync(roomsPath)) {
    const rec = JSON.parse(fs.readFileSync(roomsPath, 'utf8')).find((m) => m.matchId === mid);
    if (rec && (rec.nRooms || 1) > 1) {
      const hits = {};
      const ends = (p, nm) => p >= 0 && p < H && names[p].trim().toLowerCase().endsWith(String(nm).toLowerCase());
      for (const r of rec.rooms) for (const b of r.bots) if (b.me != null && b.names.some((nm) => ends(b.me, nm))) hits[r.roomIdx] = (hits[r.roomIdx] || 0) + 1;
      const best = Object.entries(hits).sort((a, b) => b[1] - a[1])[0];
      if (best) for (const r of rec.rooms) if (r.roomIdx !== +best[0]) for (const b of r.bots) for (const nm of b.names) otherRoomLabels.add(nm);
    }
  }
  if (!opts.replayFrom && fs.existsSync(factsPath)) {
    const fb = Object.values(JSON.parse(fs.readFileSync(factsPath, 'utf8')).bots || {});
    const used = new Set(Object.values(squad).map((s) => s.id).filter((x) => x >= 0));
    for (const [b, s] of Object.entries(squad)) {
      if (s.id >= 0) continue;
      if (otherRoomLabels.has(b)) { s.otherRoom = true; continue; }
      const f = fb.find((x) => (x.labels || []).includes(b));
      if (!f || !(f.me >= 0 && f.me < H) || used.has(f.me)) continue;
      used.add(f.me);
      squad[b] = { id: f.me, meId: f.me, byMe: true, replayName: names[f.me] };
    }
  }
  if (opts.peer) {
    const pdir = path.join(DATA, 'bundles', opts.peer);
    const ptraj = readCsv(path.join(pdir, 'traj.csv'));
    const pres = readCsv(path.join(pdir, 'results.csv'));
    for (const b of new Set([...ptraj.map((r) => r.bot), ...pres.map((r) => r.bot)])) {
      let id = -1;
      for (let p = 0; p < H; p++) if (names[p].trim().toLowerCase().endsWith(b.toLowerCase())) { id = p; break; }
      squad[`${opts.peer}:${b}`] = { id, meId: id, peer: true };
    }
  }
  // --peer-tag <标签>：同房另一支编队的对局包不能读（验证集）时，按录像里名字带的战队标签认号
  if (opts.peerTag) {
    const tag = `[${String(opts.peerTag).toLowerCase()}]`;
    const mine = new Set(Object.values(squad).map((x) => x.id));
    for (let p = 0; p < H; p++) {
      const nm = names[p].trim();
      if (!nm.toLowerCase().includes(tag) || mine.has(p)) continue;
      const b = nm.replace(/\[[^\]]*\]\s*/g, '').trim() || `p${p}`;
      squad[`${opts.peerTag}:${b}`] = { id: p, meId: p, peer: true };
    }
  }
  const squadIds = Object.values(squad).map((s) => s.id).filter((x) => x >= 0);
  const isSquad = new Uint8Array(512);
  for (const p of squadIds) isSquad[p] = 1;

  // ---- 钩子：逐对战损账 ----
  const WIN = 30;
  let pairAcc = new Map();
  const pairLog = [];
  const proto = Game.prototype;
  g.expandAttack = function (p, a) {
    const k = this.slotBase(p) + a;
    const target = this.atkTarget[k];
    if (p >= H && target >= H) return proto.expandAttack.call(this, p, a);
    const own0 = this.totalAttackTroops(p) + this.bal[p];
    const terr0 = this.terr[p];
    let dB0 = 0, dS0 = 0;
    if (target < NEUTRAL) { dB0 = this.bal[target]; dS0 = this.attackTroopsOn(target, p); }
    proto.expandAttack.call(this, p, a);
    const burnt = own0 - (this.totalAttackTroops(p) + this.bal[p]);
    const tiles = this.terr[p] - terr0;
    let dB = 0, dS = 0;
    if (target < NEUTRAL) { dB = dB0 - this.bal[target]; dS = dS0 - this.attackTroopsOn(target, p); }
    const key = p * 1024 + target;
    let r = pairAcc.get(key);
    if (!r) { r = [0, 0, 0, 0, 0]; pairAcc.set(key, r); }
    r[0] += tiles; r[1] += burnt; r[2] += dB; r[3] += dS; r[4] += 1;
    // 无主地的来历（opts.neutralFrom = [t0, t1]）：刚吃下的格就是 this.cand[0..tiles)（expandAttack 赢的那条路把 cand 原样留着）
    if (nFrom && target === NEUTRAL && tiles > 0 && p < H && this.t > nfT0 && this.t <= nfT1) {
      const cand = this.cand;
      for (let i = 0; i < tiles; i++) {
        const c = cand[i];
        if (this.own[c] !== p) { nfBad++; continue; }
        const key2 = p * 1024 + nFrom[c];
        nfAcc.set(key2, (nfAcc.get(key2) || 0) + 1);
      }
    }
  };
  // 每一格变成无主地之前是谁的（0 = 开局就是无主地；否则 1 + 那个号）。只读引擎状态，不改任何东西。
  const nFrom = opts.neutralFrom ? new Uint16Array(g.W * g.H) : null;
  const nfT0 = opts.neutralFrom ? opts.neutralFrom[0] : 0, nfT1 = opts.neutralFrom ? opts.neutralFrom[1] : 0;
  const nfAcc = new Map();
  let nfBad = 0;
  if (nFrom) {
    g.clearTerritory = function (p) {
      if (this.terr[p]) {
        const W = this.W;
        for (let x = this.x1[p]; x >= this.x0[p]; x--) {
          for (let y = this.y1[p]; y >= this.y0[p]; y--) {
            const c = y * W + x;
            if (this.ownedBy(p, c)) nFrom[c] = p + 1;
          }
        }
      }
      proto.clearTerritory.call(this, p);
    };
  }
  const flushPairs = (t) => {
    for (const [key, r] of pairAcc) pairLog.push([t, key >> 10, key & 1023, r[0], r[1], r[2], r[3], r[4]]);
    pairAcc = new Map();
  };

  // ---- 钩子：利息/地租入账、进攻结束退回的兵 ----
  const incCum = new Float64Array(H), retCum = new Float64Array(H);
  const balTmp = new Float64Array(H);
  g.economyTick = function () {
    if (this.t % 10 !== 9) return;
    for (let p = 0; p < H; p++) balTmp[p] = this.bal[p];
    proto.economyTick.call(this);
    for (let p = 0; p < H; p++) incCum[p] += this.bal[p] - balTmp[p];
  };
  g.endAttack = function (p, a, troops) {
    if (p < H) {
      const b0 = this.bal[p];
      proto.endAttack.call(this, p, a, troops);
      retCum[p] += this.bal[p] - b0;
      return;
    }
    return proto.endAttack.call(this, p, a, troops);
  };

  const engineEvents = [];
  g.onHunt = (lead, n) => engineEvents.push([g.t, 'hunt', lead, n]);
  g.onFast = (lead) => engineEvents.push([g.t, 'fast', lead, 0]);

  // ---- 钩子：空壳（离开的真人，按内置 AI 跑）把余额交给队友（bots.js botDonate → botGive）----
  const huskGifts = [];
  g.botGive = function (p, q, dn) {
    const bp = this.bal[p], bq = this.bal[q];
    const r = proto.botGive.call(this, p, q, dn);
    if (this.bal[q] !== bq || this.bal[p] !== bp) huskGifts.push([this.t, p, q, dn, bp, bq, this.bal[q], this.bal[p], this.terr[p], this.terr[q]]);
    return r;
  };

  // ---- 钩子：死亡 ----
  const deaths = [];
  const deathT = new Int32Array(512).fill(-1);
  const noteDeath = (p, kind) => {
    if (p >= H) return;
    const atk = g.attackersOf(p).map((a) => [a, g.attackTroopsOn(a, p)]);
    deaths.push({ t: g.t, p, kind, terr: g.terr[p], bal: g.bal[p], peak: g.peak[p], state: g.state[p], attackers: atk, boats: g.boatCount ? g.boatCount[p] : 0 });
  };
  g.eliminate = function (p) {
    if (!this.spawnPhase) noteDeath(p, 'eliminate');
    if (deathT[p] < 0) deathT[p] = this.t;
    return proto.eliminate.call(this, p);
  };
  g.collapse = function (p) {
    if (p < H && this.boatCount[p] && this.terr[p] + this.peak[p]) noteDeath(p, 'landless-with-boats');
    return proto.collapse.call(this, p);
  };

  // ---- 钩子：船靠岸 ----
  const landings = [];
  g.landAt = function (p, troops, c, at) {
    if (p < H || (this.px[c] >= P_INNER && this.own[c] < H)) {
      const v = this.px[c];
      const target = v === T_LAND ? NEUTRAL : v >= P_INNER ? this.own[c] : -1;
      const b0 = target >= 0 && target < NEUTRAL ? this.bal[target] : 0;
      const q0 = target >= 0 && target < NEUTRAL ? this.donQuota[target] : 0;
      proto.landAt.call(this, p, troops, c, at);
      const got = target >= 0 && target < NEUTRAL ? this.bal[target] - b0 : 0;
      landings.push([this.t, p, target, troops, got, q0, this.donCap]);
      return;
    }
    return proto.landAt.call(this, p, troops, c, at);
  };

  // ---- 指令 ----
  const cmdLog = [];
  const leftT = new Int32Array(H).fill(-1);
  const spawnXY = new Array(H).fill(null);
  const spawnSeq = Array.from({ length: H }, () => []);   // 出生阶段每个真人落地的选点指令（按执行顺序）
  const execCmd = (c) => {
    const { id, player, dX, dZ } = c;
    if (id === 0) {
      g.chooseSpawn(dX % g.W, Math.floor(dX / g.W), player, false);
      if (player < H) { spawnXY[player] = [dX % g.W, Math.floor(dX / g.W)]; spawnSeq[player].push([iy, dX % g.W, Math.floor(dX / g.W)]); }
    } else if (id === 1) {
      const B0 = g.bal[player], L0 = g.terr[player];
      const target = Math.min(dZ, NEUTRAL);
      const had = target <= NEUTRAL ? g.attackTroopsOn(player, target) : 0;
      const ok = g.attack(dX, dZ, player);
      if (player < H) cmdLog.push([g.t, player, 1, dX, dZ, ok ? 1 : 0, ok ? g.attackTroopsTmp : 0, ok ? g.attackFeeTmp : 0, B0, L0, had]);
    } else if (id === 2) {
      const B0 = g.bal[player], L0 = g.terr[player];
      const q = Math.min(dZ, NEUTRAL);
      const q0 = q < NEUTRAL ? g.donQuota[q] : 0;
      const bq0 = q < NEUTRAL ? g.bal[q] : 0;
      const want = q < NEUTRAL ? Math.min(iV(B0 * (Math.min(1023, dX) + 1), 1024), B0 - iV(64 * B0, 1024)) : 0;
      const room = q < NEUTRAL ? g.receiverRoom(q, want) : 0;
      const cost = q < NEUTRAL && room >= 1 ? g.donationCost(q, room) : 0;
      const ok = g.donate(dX, dZ, player);
      const got = q < NEUTRAL ? g.bal[q] - bq0 : 0;
      if (player < H) cmdLog.push([g.t, player, 2, dX, dZ, ok ? 1 : 0, got, B0 - g.bal[player] - got, B0, L0, q0, g.donCap, cost, q < NEUTRAL ? g.terr[q] : 0, bq0]);
    } else if (id === 3) {
      const B0 = g.bal[player], L0 = g.terr[player];
      const water = dZ >> 3, dir = dZ & 7;
      const ok = g.boat(dX, water, dir, player);
      let dest = -1;
      if (ok) {
        const route = g.bRoute[g.boatN - 1];
        const destPix = route ? route[route.length - 1] + g.dir4[dir] : water + g.dir4[dir];
        dest = destPix >= 0 && destPix < g.N ? (g.px[destPix] >= P_INNER ? g.own[destPix] : NEUTRAL) : NEUTRAL;
      }
      if (player < H) cmdLog.push([g.t, player, 3, dX, dZ, ok ? 1 : 0, ok ? g.attackTroopsTmp : 0, ok ? g.attackFeeTmp : 0, B0, L0, dest]);
    } else if (id === 4) {
      const B0 = g.bal[player], L0 = g.terr[player];
      let ok;
      if (dX === 849) ok = g.recall(dZ, player);
      else ok = g.chase(dX, dZ, player);
      if (player < H) cmdLog.push([g.t, player, 4, dX, dZ, ok ? 1 : 0, B0 - g.bal[player], 0, B0, L0]);
    } else if (id === 5) {
      const B0 = g.bal[player], L0 = g.terr[player];
      let ok = false;
      if (dX !== 513) ok = g.retreat(dX, player);
      if (player < H) cmdLog.push([g.t, player, 5, dX, dZ, ok ? 1 : 0, g.bal[player] - B0, 0, B0, L0]);
    } else if (id === 8 || id === 9) {
      if (g.spawnPhase) {
        g.eliminate(player);
        let n = g.aliveCount;
        for (let i = n - 1; i >= 0; i--) if (g.alive[g.aliveList[i]] === 0) g.aliveList[i] = g.aliveList[--n];
        g.aliveCount = n;
        if (player < H) { deathT[player] = 0; leftT[player] = 0; }
      } else {
        if (player < H && leftT[player] < 0) leftT[player] = g.t;
        if (player < H) cmdLog.push([g.t, player, id, 0, 0, 1, 0, 0, g.bal[player], g.terr[player]]);
        g.leave(player);
      }
    } else if (player < H) {
      cmdLog.push([g.t, player, id, dX, dZ, 1, 0, 0, g.bal[player], g.terr[player]]);
    }
  };

  let iv = 0, iw = 0, ix = 0, iy = 0;
  const step = () => {
    if (iv >= d.ja.length) return false;
    const jZ = d.ja[iv];
    if (d.jY[iv]) {
      // opts.cmdFilter(指令, g)：返回 false 就不执行这条录像指令（反事实探针用；默认不传，重演和原来逐位一样）
      for (let a1 = iw; a1 < iw + jZ; a1++) {
        if (opts.cmdFilter && !opts.cmdFilter(d.cmds[a1], g)) continue;
        execCmd(d.cmds[a1]);
      }
      iw += jZ;
      iv++;
    } else if (++ix >= jZ) {
      iv++;
      ix = 0;
    }
    return true;
  };
  if (vu.selectableSpawn) {
    const jJ = H <= 2 ? 30 : H <= 50 ? 40 : 50;
    while (iy <= jJ) {
      if (!step()) break;
      if (iy === jJ) g.endSpawnPhase();
      iy++;
    }
  }

  // ---- 快照 ----
  const until = opts.until ?? Infinity;
  const snapT = [], snapTerr = [], snapBal = [], teamLand = [], botLand = [], aliveH = [];
  const snapInc = [], snapRet = [], snapOut = [], snapAi = [];
  const sq = {};
  for (const [b, s] of Object.entries(squad)) if (s.id >= 0) sq[b] = { t: [], out: [], inn: [], nb: [], box: [], boats: [], quota: [] };
  const startBox = [];
  for (let p = 0; p < H; p++) startBox.push(g.alive[p] ? [g.x0[p], g.y0[p], g.x1[p], g.y1[p]] : null);
  const mapsAt = new Set(opts.maps || []);
  const maps = {};

  const contact = (p) => {
    const m = new Map();
    const B = g.border[p];
    if (!B || !g.alive[p]) return m;
    const seen = new Set();
    const d4 = g.dir4, px = g.px, own = g.own;
    for (let i = B.length - 1; i >= 0; i--) {
      const b = B[i];
      for (let k = 0; k < 4; k++) {
        const c = b + d4[k];
        if (seen.has(c)) continue;
        if (px[c] >= P_INNER) {
          if (own[c] !== p) { seen.add(c); m.set(own[c], (m.get(own[c]) || 0) + 1); }
        } else if (px[c] === T_LAND) { seen.add(c); m.set(NEUTRAL, (m.get(NEUTRAL) || 0) + 1); }
      }
    }
    return m;
  };

  const coarseMap = () => {
    const CELL = 20;
    const cw = Math.ceil(g.W / CELL), ch = Math.ceil(g.H / CELL);
    const rows = [];
    const myTeam = squadIds.length ? g.teams[squadIds[0]] : 0;
    const sqChar = new Map(squadIds.map((p, i) => [p, String.fromCharCode(97 + i)]));
    for (let cy = 0; cy < ch; cy++) {
      let s = '';
      for (let cx = 0; cx < cw; cx++) {
        const cnt = new Map();
        let n = 0;
        for (let y = cy * CELL; y < Math.min(g.H, (cy + 1) * CELL); y += 2) {
          for (let x = cx * CELL; x < Math.min(g.W, (cx + 1) * CELL); x += 2) {
            const c = y * g.W + x;
            const v = g.px[c];
            let ch1;
            if (v >= P_INNER) {
              const o = g.own[c];
              if (sqChar.has(o)) ch1 = sqChar.get(o);
              else if (o >= H || g.state[o] === 2) ch1 = ':';
              else if (teamGame && g.teams[o] === myTeam) ch1 = '+';
              else ch1 = teamGame ? String(g.teams[o]) : '#';
            } else if (v === T_LAND) ch1 = '_';
            else ch1 = ' ';
            cnt.set(ch1, (cnt.get(ch1) || 0) + 1);
            n++;
          }
        }
        let best = ' ', bn = -1;
        for (const [k, v] of cnt) if (v > bn) { bn = v; best = k; }
        s += best;
      }
      rows.push(s);
    }
    return { cell: CELL, legend: Object.fromEntries([...sqChar].map(([p, c]) => [c, names[p]])), rows };
  };

  const snap = () => {
    const t = g.t;
    snapT.push(t);
    const a = new Array(H), b = new Array(H);
    let nAlive = 0;
    for (let p = 0; p < H; p++) { a[p] = g.terr[p]; b[p] = g.bal[p]; if (g.alive[p] && g.state[p] !== 2) nAlive++; }
    snapTerr.push(a); snapBal.push(b); aliveH.push(nAlive);
    const oo = new Array(H);
    for (let p = 0; p < H; p++) oo[p] = g.alive[p] ? g.totalAttackTroops(p) : 0;
    snapInc.push(Array.from(incCum)); snapRet.push(Array.from(retCum)); snapOut.push(oo);
    const tl = new Array(Math.max(ta.nTeams, 0) + 1).fill(0);
    let bl = 0;
    for (let i = g.aliveCount - 1; i >= 0; i--) {
      const p = g.aliveList[i];
      if (p >= H) bl += g.terr[p];
      else tl[g.teams[p]] += g.terr[p];
    }
    teamLand.push(tl); botLand.push(bl);
    if (t % 30 === 0) {
      const ai = [];
      for (let i = g.aliveCount - 1; i >= 0; i--) {
        const p = g.aliveList[i];
        if (p >= H && g.terr[p] > 0) ai.push([p, g.terr[p], g.bal[p]]);
      }
      snapAi.push([t, ai]);
    }
    for (const [bname, s] of Object.entries(squad)) {
      if (s.id < 0) continue;
      const p = s.id, o = sq[bname];
      o.t.push(t);
      const outs = [];
      const base = g.slotBase(p);
      for (let i = 0; i < g.atkCount[p]; i++) outs.push([g.atkTarget[base + i], g.atkTroops[base + i]]);
      o.out.push(outs);
      o.inn.push(g.alive[p] ? g.attackersOf(p).map((q) => [q, g.attackTroopsOn(q, p)]) : []);
      o.boats.push(g.boatCount ? [g.boatCount[p], g.boatTroops ? g.boatTroops(p) : 0] : [0, 0]);
      o.quota.push(g.donQuota[p]);
      if (t % 30 === 0) {
        o.nb.push([t, [...contact(p)].sort((x, y) => y[1] - x[1]).slice(0, 12)]);
        o.box.push([t, g.x0[p], g.y0[p], g.x1[p], g.y1[p]]);
      }
    }
  };

  // traj 核对：traj 的 t 是页面本地拍号（策略在该拍读到的状态）
  const want = new Map();
  for (const r of traj) {
    const s = squad[r.bot];
    if (!s || s.id < 0) continue;
    const t = +r.t;
    if (!want.has(t)) want.set(t, []);
    want.get(t).push({ bot: r.bot, id: s.id, terr: +r.terr, bal: +r.bal });
  }
  const val = { rows: 0, terrExact: 0, balExact: 0, bothExact: 0, mism: [] };
  const checkTraj = () => {
    const w = want.get(g.t);
    if (!w) return;
    for (const r of w) {
      val.rows++;
      const te = g.terr[r.id] === r.terr, be = g.bal[r.id] === r.bal;
      if (te) val.terrExact++;
      if (be) val.balExact++;
      if (te && be) val.bothExact++;
      else if (val.mism.length < 400) val.mism.push([g.t, r.bot, r.terr, g.terr[r.id], r.bal, g.bal[r.id]]);
    }
  };

  const perTick = opts.offsetScan ? [] : null;
  const notePerTick = () => {
    if (!perTick) return;
    const row = [];
    for (const p of squadIds) row.push(g.terr[p], g.bal[p]);
    perTick[g.t] = row;
  };
  const hookCtx = { H, names, squad, squadIds, teamGame, contact };
  if (opts.onStart) opts.onStart(g, hookCtx);
  snap();
  checkTraj();
  notePerTick();
  while (!g.over && g.t < until && step()) {
    g.tick();
    notePerTick();
    for (let p = 0; p < H; p++) if (deathT[p] < 0 && g.alive[p] === 0) deathT[p] = g.t;
    if (g.t % WIN === 0) flushPairs(g.t);
    if (g.t % 10 === 0) snap();
    checkTraj();
    if (mapsAt.has(g.t)) maps[g.t] = coarseMap();
    if (opts.onTick) opts.onTick(g, hookCtx);
  }
  flushPairs(g.t);
  snap();

  let offsetScan = null;
  if (perTick) {
    offsetScan = [];
    for (let k = -14; k <= 14; k++) {
      let n = 0, te = 0, be = 0;
      for (const [t, w] of want) {
        const row = perTick[t + k];
        if (!row) continue;
        for (const r of w) {
          const i = squadIds.indexOf(r.id);
          n++;
          if (row[2 * i] === r.terr) te++;
          if (row[2 * i + 1] === r.bal) be++;
        }
      }
      offsetScan.push([k, n, te, be]);
    }
  }
  const out = {
    offsetScan,
    matchId: mid, H, players: vu.playerCount, land: g.land, W: g.W, Hh: g.H, mapIdx, mapSeed,
    gameMode: vu.gameMode, nTeamsHeader: vu.numberTeams, nTeams: ta.nTeams, teamColor: ta.lH, botsTeamed: ta.botsTeamed,
    clans: ta.clans, teamSizes: ta.sizes, teams: ta.fX, names, colors, squad, selectedPlayer: vu.selectedPlayer,
    endTick: g.t, over: g.over, winner: g.winner, winnerTeam: g.winnerTeam,
    spawnXY, spawnSeq, spawnTurns: vu.selectableSpawn ? (H <= 2 ? 30 : H <= 50 ? 40 : 50) : 0, startBox, leftT: Array.from(leftT), deathT: Array.from(deathT.subarray(0, H)),
    validate: val,
    snapT, snapTerr, snapBal, snapInc, snapRet, snapOut, snapAi, teamLand, botLand, aliveH,
    sq, pairLog, cmdLog, deaths, landings, maps, engineEvents, huskGifts,
    neutralFrom: nFrom ? { rows: [...nfAcc].map(([k, v]) => [k >> 10, (k & 1023) - 1, v]), bad: nfBad } : null,
  };
  return out;
}

if (import.meta.url === `file://${process.argv[1]}`) {
  const args = process.argv.slice(2);
  const mid = args[0];
  if (!mid) { console.error('用法：node resim.mjs <matchId> [--until T] [--maps t1,t2] [--quiet]'); process.exit(2); }
  const opt = (k, dflt) => (args.includes(`--${k}`) ? args[args.indexOf(`--${k}`) + 1] : dflt);
  const until = opt('until', null);
  const mapsArg = opt('maps', '');
  const t0 = Date.now();
  const out = resim(mid, { until: until ? +until : undefined, maps: mapsArg ? mapsArg.split(',').map(Number) : [], offsetScan: args.includes('--offset-scan'),
    replayFrom: opt('replay-from', null), peer: opt('peer', null), peerTag: opt('peer-tag', null) });
  out.replayFrom = opt('replay-from', null) || mid;
  out.peer = opt('peer', null) || opt('peer-tag', null);
  if (out.offsetScan) console.log('  offset scan [k, rows, terr一致, bal一致]: ' + out.offsetScan.map((r) => r.join('/')).join(' '));
  fs.mkdirSync(path.join(OUT, mid), { recursive: true });
  fs.writeFileSync(path.join(OUT, mid, 'resim.json'), JSON.stringify(out));
  const v = out.validate;
  console.log(`${mid}: H=${out.H} land=${out.land} teams=${out.nTeams}(header ${out.nTeamsHeader}) sizes=${JSON.stringify(out.teamSizes)} end=${out.endTick} over=${out.over} winnerTeam=${out.winnerTeam} | ${((Date.now() - t0) / 1000).toFixed(1)}s`);
  console.log(`  clans: ${out.clans.map((c) => `${c.tag}×${c.size}→T${c.team}`).join(' ')}`);
  console.log(`  squad: ${Object.entries(out.squad).map(([b, s]) => `${b}=${s.id}${s.mismatch ? `(meId ${s.meId}!)` : ''}:T${s.id >= 0 ? out.teams[s.id] : '?'}`).join(' ')}`);
  console.log(`  traj 核对：${v.rows} 行，地一致 ${v.terrExact}，兵一致 ${v.balExact}，都一致 ${v.bothExact}`);
  console.log(`  引擎事件：${out.engineEvents.slice(0, 12).map((e) => `${e[0]}:${e[1]}(T${e[2]},${e[3]})`).join(' ')}${out.engineEvents.length > 12 ? ` …共 ${out.engineEvents.length}` : ''}`);
  if (!args.includes('--quiet')) for (const m of v.mism.slice(0, 25)) console.log(`    t=${m[0]} ${m[1]} terr traj=${m[2]} sim=${m[3]} | bal traj=${m[4]} sim=${m[5]}`);
}
