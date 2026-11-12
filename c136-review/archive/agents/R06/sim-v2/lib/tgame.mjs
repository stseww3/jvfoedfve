// tgame.mjs — teamgate-v2 的物理底座。
//
// 在干净模拟器（/agent/repos/c136-data/src/sim/sim）的 Game 之上补齐组队局与线上引擎不一致的五处：
//   ① 组队配色（引擎 cX.aKa）：512 个席位每人只抽 1 个随机数（倒序），不是「每个内置 AI 抽 3 个」。
//      随机数序列决定内置 AI 的出生点；颜色还被船的寻路当作水体编号读（bodyId）。
//   ② 只有实际队数 = 8 的房间内置 AI 才分队（fX = 1 + p % 8）；其余房间内置 AI 的队号是 0，与所有人为敌。
//   ③ 各队总地的缓存每 32 拍才刷新一次：「领先队 ≥80% 后给 AI 派猎杀目标」「领先队 ≥90% 后 AI 提速」读的是这份旧值。
//   ④ 船落在「不是空地、也没人占」的格子（水 / 边界 / 山；单点航线会走到这里）：按引擎 acN 对像素归属位那个席位开一条
//      攻击线，没有接壤时下一次结算原数退回余额。干净模拟器在这种落点直接 return，船上的兵凭空消失。
//   ⑤ clone() 保留子类原型（干净模拟器 clone.js 写死 Game.prototype，分叉后 ③④ 的覆盖全丢）。
// 另补：真人的翻山指令（录像指令号 10，引擎 bB.qi.i2）；可选的收入记账（利息 + 地租）。
//
// ①③ 的写法取自统筹入库的 /agent/repos/c136-data/src/tools/resim.mjs（TGame），④ 取自 resim_lib_r01.mjs，
// 分队算法（引擎 dP.ee：aej → aKa → aek → ael）取自 resim.mjs 的 assignTeams，并与 R06 的 team_assign.py 逐局对过。
import path from 'node:path';

export const DATA = process.env.C136_DATA || '/agent/repos/c136-data';
export const SIM = await import(path.join(DATA, 'src/sim/sim/index.js'));
export const REPLAY_LIB = await import(path.join(DATA, 'src/sim/tools/c102-replay-lib.mjs'));
const { Game, NEUTRAL, P_INNER, MAX_PLAYERS, iV, T_LAND, T_MOUNTAIN } = SIM;
export { Game, NEUTRAL, P_INNER, MAX_PLAYERS, iV, T_LAND, T_MOUNTAIN };
export const T_WATER = SIM.T_WATER;

const AKK = [[100, 100, 100], [144, 0, 0], [0, 128, 0], [0, 0, 144], [128, 128, 0], [128, 0, 128], [0, 128, 128], [196, 196, 196], [0, 0, 0]];
const AKL = [[4, 4, 4, 20], [4, 0, 0, 27], [0, 4, 0, 31], [0, 0, 4, 27], [4, 4, 0, 31], [4, 0, 4, 31], [0, 4, 4, 31], [4, 4, 4, 14], [4, 4, 4, 13]];
const mj = (a, b) => (a >= 0 ? iV(a, b) : -iV(-a, b));

// clone() 时共享（不复制）的字段：静态数据和每次调用自己清零的草稿缓冲。前一半与干净模拟器 clone.js 相同。
const SHARED = new Set([
  'map', 'wid', 'mountainMap', 'dir4', 'dir8', 'dirRing', 'humanColors',
  'colR', 'colG', 'colB', 'colLow', 'borR', 'borG', 'borB', 'froR', 'froG', 'froB',
  'botDiff', 'botPctStep', 'cellNb',
  'cand', 'frontCopy', 'mark', 'scratchList', 'tgt', 'bfsCost', 'spawnTiles',
  'teamCtx', 'names',
]);
const LIST_OF_LISTS = new Set(['front', 'border', 'coast', 'cliff', 'cells']);
const LIST_OF_REFS = new Set(['routes', 'bRoute']);

export class TGame extends Game {
  // Game 的构造函数里就调 setup() → setupColors()，所以分队信息要在 super.setup 之前挂到实例上。
  setup(opts) {
    this.teamCtx = opts.teamCtx || null; // { aDn: Uint8Array(512) 每个席位的队伍颜色号 }
    this.online = true;
    this.names = opts.names || null;
    this.acct = null;
    this.oddLandings = 0;
    this.oddLandingTroops = 0;
    super.setup(opts);
  }

  // ---- ① 组队配色 ----------------------------------------------------------------------------
  setupColors() {
    if (!this.teamCtx) return super.setupColors();
    const rng = this.rng, P = MAX_PLAYERS;
    const R = this.colR, G = this.colG, B = this.colB;
    const aDn = this.teamCtx.aDn;
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

  // ---- ③ 各队总地的 32 拍缓存（引擎 bk：a5c，每拍末尾 ++w0 >= 32 时重算）---------------------------
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

  // bk.lR()：领先的是真队伍就返回它的地；领先的是 0 号（未入队的内置 AI）就返回 max(最大真队伍, 榜首个人)
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
  }

  // ---- ④ 船落在水 / 边界 / 山格 ---------------------------------------------------------------
  landAt(p, troops, c, at) {
    const v = this.px[c];
    if (v !== T_LAND && v < P_INNER) {
      const target = (v & 3) << 3;
      this.oddLandings++;
      this.oddLandingTroops += troops;
      if (target === p) { this.addBalance(p, troops); return; }
      if (!this.isEnemy(p, target)) {
        const room = this.receiverRoom(target, troops);
        if (room >= 1 && this.bookDonation(target, room)) this.addBalance(target, room);
        return;
      }
      if (this.hasAttack(p, target) || this.hasFreeSlot(p)) {
        this.front[p].push(at);
        this.addAttack(p, troops, target);
        this.schedule(p, true);
      }
      return;
    }
    return super.landAt(p, troops, c, at);
  }

  // ---- 真人翻山（录像指令号 10；引擎 bB.qi.i2(player, pct, 格子, 目标)）-----------------------------
  // 目标规范化 → 点的那一格必须是无主陆地或目标的地 → 那一格四邻里的山体（3..0 的顺序，同一山体只算一次）里第一个
  // 「自己的贴山边界格也挨着」的 → 已有对该目标的进攻线或还有空线 → 出兵量按 sendAll → 那格山进自己的前线表。
  mountainCmd(p, pct, tile, target) {
    if (!this.canAct(p) || p === target) return false;
    target = Math.min(target, NEUTRAL);
    if (target < NEUTRAL && this.alive[target] === 0) target = NEUTRAL;
    if (target < NEUTRAL && !this.isEnemy(p, target)) return false;
    const x = tile % this.W, y = Math.floor(tile / this.W);
    if (!(x > 0 && x < this.W - 1 && y > 0 && y < this.H - 1)) return false;
    const v = this.px[tile];
    if (v === T_LAND) target = NEUTRAL;
    else if (v >= P_INNER) { if (this.own[tile] !== target) return false; } else return false;
    const ids = [], cells = [];
    for (let k = 3; k >= 0; k--) {
      const c = tile + this.dir4[k];
      if (this.px[c] === T_MOUNTAIN && !ids.includes(this.wid[c])) { ids.push(this.wid[c]); cells.push(c); }
    }
    const C = this.cliff[p] || [];
    const touches = (id) => {
      for (let i = 0; i < C.length; i++) for (let k = 3; k >= 0; k--) { const c = C[i] + this.dir4[k]; if (this.px[c] === T_MOUNTAIN && this.wid[c] === id) return true; }
      return false;
    };
    let hit = -1;
    for (let i = 0; i < ids.length; i++) if (touches(ids[i])) { hit = cells[i]; break; }
    if (hit < 0) return false;
    if (!this.hasAttack(p, target) && !this.hasFreeSlot(p)) return false;
    const troops = this.sendAll(p, pct);
    this.front[p].push(hit);
    this.addAttack(p, troops, target);
    this.schedule(p, true);
    return true;
  }

  // ---- 收入记账（可选）：每个真人席位的利息 + 地租入账累计 ------------------------------------------
  enableAccounting() {
    if (!this.acct) this.acct = { inc: new Float64Array(this.humans), tmp: new Float64Array(this.humans) };
    return this.acct;
  }

  economyTick() {
    if (this.t % 10 !== 9) return;
    const a = this.acct;
    if (!a) return super.economyTick();
    const H = this.humans, bal = this.bal, tmp = a.tmp, inc = a.inc;
    for (let p = 0; p < H; p++) tmp[p] = bal[p];
    super.economyTick();
    for (let p = 0; p < H; p++) inc[p] += bal[p] - tmp[p];
  }

  // ---- ⑤ clone()：保留原型；多出来的字段照规则复制 -------------------------------------------------
  clone() {
    const g = Object.create(Object.getPrototypeOf(this));
    const Rng = this.rng.constructor;
    for (const k of Object.keys(this)) {
      const v = this[k];
      if (v === null || typeof v !== 'object' || SHARED.has(k)) g[k] = v;
      else if (ArrayBuffer.isView(v)) g[k] = v.slice();
      else if (LIST_OF_LISTS.has(k)) g[k] = v.map((a) => (a ? a.slice() : a));
      else if (LIST_OF_REFS.has(k)) g[k] = v.slice();
      else if (v instanceof Map) g[k] = new Map(v);
      else if (v instanceof Rng) { g[k] = new Rng(); g[k].s = v.s; }
      else if (k === 'acct') g[k] = { inc: v.inc.slice(), tmp: v.tmp.slice() };
      else throw new Error(`TGame.clone: 没处理的字段 ${k}`);
    }
    return g;
  }

  // 局面指纹（核对 clone / 两次重演是否逐格一致）：FNV-1a 过一遍主要状态数组
  fingerprint() {
    let h = 0x811c9dc5;
    const mix = (a) => {
      const u8 = new Uint8Array(a.buffer, a.byteOffset, a.byteLength);
      for (let i = 0; i < u8.length; i++) { h ^= u8[i]; h = Math.imul(h, 0x01000193); }
    };
    mix(this.px); mix(this.own); mix(this.terr); mix(this.bal); mix(this.alive); mix(this.state);
    mix(this.atkCount); mix(this.atkTarget); mix(this.atkTroops); mix(this.donQuota); mix(this.debt);
    mix(this.bTroops.subarray(0, this.boatN)); mix(this.bPos.subarray(0, this.boatN));
    h ^= this.t; h = Math.imul(h, 0x01000193);
    h ^= this.rng.s; h = Math.imul(h, 0x01000193);
    return (h >>> 0).toString(16).padStart(8, '0');
  }
}

// ---- 分队（引擎 dP.ee 的移植）-----------------------------------------------------------------------
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

// 返回 { fX: 每个真人的队号, nTeams: 实际队数, lH: 队号→颜色号, botsTeamed: 内置 AI 是否分队, clans, sizes }
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

// 把分队结果变成 TGame 的构造参数（teams / nTeams / botTeams / teamCtx）
export function teamOpts(ta, H) {
  if (!ta || !(ta.nTeams >= 2)) return {};
  const aDn = new Uint8Array(MAX_PLAYERS);
  for (let p = 0; p < MAX_PLAYERS; p++) {
    const team = p < H ? ta.fX[p] : ta.botsTeamed ? 1 + (p % ta.nTeams) : 0;
    aDn[p] = ta.lH[team];
  }
  return { teams: ta.fX, nTeams: ta.nTeams, botTeams: ta.botsTeamed, teamCtx: { aDn } };
}
