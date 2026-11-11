// resim_lib.mjs — 整局重演的公共部分：用 c136-data/src/sim 的引擎移植版 + 地图二进制 + replay.txt 逐拍重演 512 个席位。
// 相比 c102-replay-lib.makeStepper 多做的事：
//   1) 队伍：按引擎 bj.ee()（aej 颜色就近 → aKa 颜色热度排序 → aek 战队同队 → ael 补位 → aem）从录像头算出每个人类的队号；
//      队数 <8 时内置 AI 不入队（fX=0，与所有人为敌）。
//   2) 团队局颜色初始化（live ad.dk → aKa）对 512 个席位各取 1 个随机数；模拟器 setupColors 按非团队局给每个 AI 取 3 个，
//      随机数序列不同会让 AI 出生点全部错位，这里按团队局改回 512 个。
//   3) 捐款指令 id=2。
//   4) 观测钩子：每笔转账（指令捐款 / 离场号与 AI 的自动捐款 / 运兵船靠队友岸）、每次丢地（谁从谁手里拿了几格）、
//      每个人类号的阵亡与离场。
// 用法：const m = openMatch('A059'); while (m.tick()) { ...看 m.g... }
import fs from 'node:fs';
import { decodeReplay, mapOf } from '/agent/repos/c136-data/src/sim/tools/c102-replay-lib.mjs';
import { Game, loadMap, NEUTRAL, P_INNER, T_LAND, T_WATER } from '/agent/repos/c136-data/src/sim/sim/index.js';

export { NEUTRAL, P_INNER, T_LAND, T_WATER };
const BUNDLES = '/agent/repos/c136-data/bundles';

export function clanOf(username) {
  const fO = username.indexOf('[');
  if (fO < 0) return null;
  const fd = username.indexOf(']');
  if (fd - fO > 1 && fd - fO <= 8) return username.substring(fO + 1, fd).toUpperCase().trim();
  return null;
}

// Port of live bj.ee(): { fX (team 1..n per human, 0 for AI when n<8), nTeams, lH (rank -> colour index), botTeams, counts }.
export function assignTeams(vu) {
  const H = vu.humanCount;
  const aU2 = [[128, 128, 128], [255, 0, 0], [0, 255, 0], [0, 0, 255], [255, 255, 0], [255, 0, 255], [0, 255, 255], [255, 255, 255], [0, 0, 0]];
  const lH = [0, 1, 2, 3, 4, 5, 6, 7, 8];
  let a0L = vu.numberTeams;
  const colors = vu.colorsData.data ?? vu.colorsData;
  const names = Array.from(vu.playerNamesData.data ?? vu.playerNamesData);
  const fX = new Uint8Array(512);
  const a2F = new Uint8Array(H), a2G = new Uint8Array(H), aeh = new Uint16Array(8), aei = new Uint16Array(9);
  { // aej
    const fZ = 8, h = new Uint16Array(fZ);
    for (let aC = H - 1; aC >= 0; aC--) {
      const c = colors[aC];
      for (let ft = fZ; ft >= 1; ft--) h[ft - 1] = Math.abs(4 * (c >> 12) - aU2[ft][0]) + Math.abs(4 * ((c >> 6) & 63) - aU2[ft][1]) + Math.abs(4 * (c & 63) - aU2[ft][2]);
      let aer = 768;
      for (let ft = fZ - 1; ft >= 0; ft--) { const e = (ft + aC) % fZ; if (h[e] < aer) { aer = h[e]; a2F[aC] = e; } }
      aeh[a2F[aC]] += 4;
      aer = 768;
      for (let ft = fZ - 1; ft >= 0; ft--) { const e = (ft + aC) % fZ; if (h[e] < aer && e !== a2F[aC]) { aer = h[e]; a2G[aC] = e; } }
      aeh[a2G[aC]]++;
    }
  }
  { // aKa
    const fZ = 8;
    for (let aC = fZ - 1; aC >= 0; aC--) aeh[aC]++;
    for (let aC = 1; aC <= fZ; aC++) {
      let lr = 0;
      for (let ft = 1; ft < fZ; ft++) if (aeh[ft] > aeh[lr]) lr = ft;
      aeh[lr] = 0;
      lH[aC] = lr + 1;
    }
  }
  { // aek
    const aes = 8, sp = new Uint16Array(aes), aet = [], a3p = [], aev = [];
    let aeu = 0;
    loop: for (let aC = 0; aC < H; aC++) {
      const a3q = clanOf(names[aC] ?? '');
      if (a3q !== null) {
        for (let ft = a3p.length - 1; ft >= 0; ft--) {
          if (a3q === a3p[ft]) { aev[ft].push(aC); aeu = Math.max(aeu, aev[ft].length); continue loop; }
        }
        a3p.push(a3q); aet.push(false); aev.push([aC]); aeu = Math.max(aeu, 1);
      }
    }
    while (a0L > 2 && aeu > Math.floor(H / a0L)) a0L--;
    for (let ft = a3p.length - 1; ft >= 0; ft--) {
      let fc = -1;
      for (let ej = a3p.length - 1; ej >= 0; ej--) if (!aet[ej] && (fc === -1 || aev[ej].length > aev[fc].length)) fc = ej;
      for (let ej = aes - 1; ej >= 0; ej--) sp[ej] = 1;
      for (let ej = aev[fc].length - 1; ej >= 0; ej--) { sp[a2F[aev[fc][ej]]] += 3; sp[a2G[aev[fc][ej]]]++; }
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
        break;
      }
      aet[fc] = true;
    }
  }
  { // ael
    const fZ = 8;
    let border = Math.floor(H / a0L);
    if (H % a0L > 0) border++;
    const aew = new Uint8Array(fZ + 1);
    for (let ft = fZ; ft >= 1; ft--) aew[lH[ft]] = ft;
    for (let aC = 0; aC < H; aC++) { const iv = aew[a2F[aC] + 1]; if (fX[aC] === 0 && iv <= a0L && aei[iv] < border) { aei[iv]++; fX[aC] = iv; } }
    for (let aC = 0; aC < H; aC++) { const iv = aew[a2G[aC] + 1]; if (fX[aC] === 0 && iv <= a0L && aei[iv] < border) { aei[iv]++; fX[aC] = iv; } }
    for (let ft = a0L; ft >= 1; ft--) for (let aC = H - 1; aC >= 0; aC--) { if (aei[ft] >= border) break; if (fX[aC] === 0) { aei[ft]++; fX[aC] = ft; } }
  }
  const botTeams = a0L >= 8;
  return { fX, nTeams: a0L, lH, botTeams, counts: Array.from(aei.subarray(0, a0L + 1)) };
}

let TEAM_RNG_FIX = false;
const origSetupColors = Game.prototype.setupColors;
Game.prototype.setupColors = function () {
  if (!TEAM_RNG_FIX) return origSetupColors.call(this);
  const saved = this.rng.s;
  origSetupColors.call(this);
  this.rng.s = saved;
  for (let i = 0; i < 512; i++) this.rng.next();
};

// 读某个包的局内日志：号名 -> 席位号（[HL-GAME-INIT] me=），以及每条 [HL-TICK] 的 terr/bal。
export function readLogSnaps(bundleId, label = '') {
  const logp = `${BUNDLES}/${bundleId}/in_game.log`;
  const me = {}, rows = [];
  if (!fs.existsSync(logp)) return { me, rows };
  for (const line of fs.readFileSync(logp, 'utf8').split('\n')) {
    let m = line.match(/\[([^\]]+)\] \[HL-GAME-INIT\].*me=(\d+)/);
    if (m) { me[m[1]] = +m[2]; continue; }
    m = line.match(/\[([^\]]+)\] \[HL-TICK\] t=(\d+) terr=(\d+)\([^)]*\) bal=(\d+)/);
    if (m && me[m[1]] !== undefined) rows.push({ t: +m[2], bot: label + m[1], p: me[m[1]], terr: +m[3], bal: +m[4] });
  }
  return { me, rows };
}

export function openMatch(mid, { replay = mid, rngFix = true } = {}) {
  const d = decodeReplay(fs.readFileSync(`${BUNDLES}/${replay}/replay.txt`, 'utf8'));
  const vu = d.vu, H = vu.humanCount;
  const names = Array.from(vu.playerNamesData.data ?? vu.playerNamesData);
  const tm = vu.gameMode === 1 ? assignTeams(vu) : null;
  const { mapIdx, mapSeed } = mapOf(vu);
  const map = loadMap(mapIdx, mapSeed);
  const colors = vu.colorsData ? Array.from((vu.colorsData.data ?? vu.colorsData).subarray(0, H)) : [0];
  TEAM_RNG_FIX = !!tm && rngFix;
  const g = new Game({
    map, humans: H, players: vu.playerCount, difficulty: H > 1 ? 0 : vu.botDifficultyValue, spawnSeed: vu.spawningSeed,
    selectableSpawn: !!vu.selectableSpawn, battleRoyaleMode: vu.battleRoyaleMode, humanColors: colors,
    passableWater: vu.passableWater, passableMountains: vu.passableMountains,
    ...(tm ? { teams: Array.from(tm.fX.subarray(0, H)), nTeams: tm.nTeams, botTeams: tm.botTeams } : {}),
  });
  TEAM_RNG_FIX = false;
  g.me = vu.selectedPlayer;

  const m = {
    mid, replay, d, vu, H, names, tm, g, map: `${mapIdx}_${mapSeed}`,
    applied: { donate: 0, attack: 0, boat: 0 }, rejected: { donate: 0, attack: 0, boat: 0 },
    transfers: [],      // {t, from, to, pct, kind: cmd|auto|boat, fromBal, toBal, toTerr, paid, received, ok}
    events: [],         // {t, ev: died|left|landless, p, terr, bal, detail}
    lossWin: new Map(), // 'victim|attacker' -> 本窗口丢地格数（调用方自行清空）
    lossLife: new Map(),// victim -> Map(attacker -> [格数, 最后一次拍])
    onCmd: null,        // (cmd, result) => void，指令执行之后
    preCmd: null,       // (cmd) => void，指令执行之前（此时 g.bal 还没扣）
    spawn: {},          // p -> [x, y]（最后一次出生指令）
    oddLandings: [],    // 船落在“不是空地也没人占”的格子上（见 g.landAt 的说明）
  };
  let inCmd = null, curAtk = -1;

  // 钩子都挂在实例上，不动原型。
  const P = Game.prototype;
  g.expandAttack = function (p, a) { curAtk = p; return P.expandAttack.call(this, p, a); };
  g.loseTiles = function (q, cand, cnt) {
    const k = q + '|' + curAtk;
    m.lossWin.set(k, (m.lossWin.get(k) || 0) + cnt);
    let lm = m.lossLife.get(q);
    if (!lm) m.lossLife.set(q, (lm = new Map()));
    const e = lm.get(curAtk) || [0, 0];
    e[0] += cnt; e[1] = this.t;
    lm.set(curAtk, e);
    return P.loseTiles.call(this, q, cand, cnt);
  };
  g.transfer = function (p, q, troops) {
    const b0 = this.bal[p], r0 = this.bal[q], rt = this.terr[q];
    const v = P.transfer.call(this, p, q, troops);
    if (!inCmd && v > 0) m.transfers.push({ t: this.t, from: p, to: q, pct: -1, kind: 'auto', fromBal: b0, toBal: r0, toTerr: rt, paid: b0 - this.bal[p], received: this.bal[q] - r0, ok: 1 });
    return v;
  };
  g.landAt = function (p, troops, c, at) {
    const v = this.px[c];
    // 线上原文 acN（live_game_js.js，function aaM 内）：落点不是空地时一律用像素的“归属位” ad.fR 当目标，
    // 不检查这格是否真的有人占。没人占的水/边界/山，归属位 = (地形码 & 3) << 3（水 16、边界 24、山 8）。
    // 模拟器的 landAt 在这种落点直接返回（船上的兵凭空消失）；线上则是对那个席位开一条攻击线，
    // 没有接壤时下一次结算原数退回余额。单点航线（目标水格本身挨着自己的地）会让船落到像素 0 旁边的边界格，就走到这里。
    // 实证：A057 第 2485 拍 #93 的船（34,985 兵），真引擎第 2490 拍余额多回 34,985（scripts/engine_probe.cjs）。
    if (v !== T_LAND && v < P_INNER) {
      const target = (v & 3) << 3;
      m.oddLandings.push({ t: this.t, p, troops, c, v, target });
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
    const target = v >= P_INNER ? this.own[c] : -1;
    if (target >= 0 && target !== p && !this.isEnemy(p, target)) {
      const r0 = this.bal[target], rt = this.terr[target];
      const r = P.landAt.call(this, p, troops, c, at);
      m.transfers.push({ t: this.t, from: p, to: target, pct: -1, kind: 'boat', fromBal: this.bal[p], toBal: r0, toTerr: rt, paid: troops, received: this.bal[target] - r0, ok: this.bal[target] > r0 ? 1 : 0 });
      return r;
    }
    return P.landAt.call(this, p, troops, c, at);
  };
  const topAttackers = (p) => {
    const lm = m.lossLife.get(p);
    if (!lm) return '';
    return [...lm.entries()].sort((a, b) => b[1][0] - a[1][0]).slice(0, 4).map(([a, [n, t]]) => `${a}:${n}:${t}`).join('|');
  };
  g.eliminate = function (p) {
    if (p < H && this.alive[p] && !this.spawnPhase) {
      const atk = this.attackersOf(p).map((a) => `${a}:${this.attackTroopsOn(a, p)}`).join('|');
      m.events.push({ t: this.t, ev: 'died', p, terr: this.terr[p], bal: this.bal[p], detail: `atkNow=${atk};tookLife=${topAttackers(p)}` });
    }
    return P.eliminate.call(this, p);
  };
  g.collapse = function (p) {
    const hadLand = this.terr[p] > 0, wasAlive = this.alive[p];
    const r = P.collapse.call(this, p);
    if (p < H && wasAlive && this.alive[p] && hadLand && this.terr[p] === 0) m.events.push({ t: this.t, ev: 'landless', p, terr: 0, bal: this.bal[p], detail: `tookLife=${topAttackers(p)}` });
    return r;
  };

  const execCmd = (c) => {
    const { id, player, dX, dZ } = c;
    let r;
    if (m.preCmd) m.preCmd(c);
    inCmd = c;
    if (id === 0) { g.chooseSpawn(dX % g.W, Math.floor(dX / g.W), player, false); m.spawn[player] = [dX % g.W, Math.floor(dX / g.W)]; }
    else if (id === 1) { r = g.attack(dX, dZ, player); (r ? m.applied : m.rejected).attack++; }
    else if (id === 2) {
      const b0 = g.bal[player], r0 = g.bal[dZ], rt = g.terr[dZ];
      r = g.donate(dX, dZ, player);
      (r ? m.applied : m.rejected).donate++;
      m.transfers.push({ t: g.t, from: player, to: dZ, pct: dX, kind: 'cmd', fromBal: b0, toBal: r0, toTerr: rt, paid: r ? b0 - g.bal[player] : 0, received: r ? g.bal[dZ] - r0 : 0, ok: r ? 1 : 0 });
    } else if (id === 3) { r = g.boat(dX, dZ >> 3, dZ & 7, player); (r ? m.applied : m.rejected).boat++; }
    else if (id === 4) { if (dX === 849) g.recall(dZ, player); else g.chase(dX, dZ, player); }
    else if (id === 5) { if (dX !== 513) g.retreat(dX, player); }
    else if (id === 8 || id === 9) {
      if (g.spawnPhase) {
        g.eliminate(player);
        let n = g.aliveCount;
        for (let i = n - 1; i >= 0; i--) if (g.alive[g.aliveList[i]] === 0) g.aliveList[i] = g.aliveList[--n];
        g.aliveCount = n;
      } else {
        if (player < H && g.alive[player] && g.state[player] !== 2) m.events.push({ t: g.t, ev: 'left', p: player, terr: g.terr[player], bal: g.bal[player], detail: '' });
        g.leave(player);
      }
    }
    inCmd = null;
    if (m.onCmd) m.onCmd(c, r);
    return r;
  };
  let iv = 0, iw = 0, ix = 0, iy = 0;
  const step = () => {
    if (iv >= d.ja.length) return false;
    const jZ = d.ja[iv];
    if (d.jY[iv]) { for (let a1 = iw; a1 < iw + jZ; a1++) execCmd(d.cmds[a1]); iw += jZ; iv++; }
    else if (++ix >= jZ) { iv++; ix = 0; }
    return true;
  };
  const jJ = H <= 2 ? 30 : H <= 50 ? 40 : 50;
  if (vu.selectableSpawn) while (iy <= jJ) { if (!step()) break; if (iy === jJ) g.endSpawnPhase(); iy++; }

  // 推进一拍：先执行这一拍的指令，再让引擎走一拍。录像放完或游戏结束返回 false。
  m.tick = () => {
    if (g.over || !step()) return false;
    g.tick();
    return true;
  };
  m.runTo = (t, cb) => { while (g.t < t && m.tick()) if (cb) cb(g); return g.t >= t; };
  m.teamOf = (p) => g.teams[p];
  m.label = (p) => (p >= NEUTRAL ? 'NEUTRAL' : p < H ? (names[p] ?? `#${p}`) : `AI#${p}`);

  // 邻接扫描：p 的边界格四邻里别人的格子数（接触长度），以及中立地、水。
  m.neighbours = (p) => {
    const out = { players: new Map(), neutral: 0, water: 0 };
    const B = g.border[p];
    if (!B) return out;
    const px = g.px, own = g.own, d4 = g.dir4;
    for (let i = B.length - 1; i >= 0; i--) {
      const c = B[i];
      if (!(px[c] >= P_INNER && own[c] === p)) continue;
      for (let k = 0; k < 4; k++) {
        const n = c + d4[k], v = px[n];
        if (v >= P_INNER) { const o = own[n]; if (o !== p) out.players.set(o, (out.players.get(o) || 0) + 1); }
        else if (v === T_LAND) out.neutral++;
        else if (v === T_WATER) out.water++;
      }
    }
    return out;
  };
  m.atkOut = (p) => { const b = g.slotBase(p), o = []; for (let i = 0; i < g.atkCount[p]; i++) o.push([g.atkTarget[b + i], g.atkTroops[b + i]]); return o; };
  m.atkIn = (p) => g.attackersOf(p).map((a) => [a, g.attackTroopsOn(a, p)]);
  return m;
}
