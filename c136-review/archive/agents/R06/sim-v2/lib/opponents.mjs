// opponents.mjs — arena 模式里「不是我方席位的真人」的闭环模型（对手、同队路人、空壳）。
//
// 一个 Crowd 管一条臂里全部这类席位。每个回合（7 的倍数拍）每个在场的席位按实测的指令密度得到一次出手机会，
// 再按实测的对象构成（无主地 / 内置 AI 与空壳 / 真人 / 船 / 捐款）和千分比分布出一条指令；指令直接交给引擎（即时生效，
// 真人没有我方那条锁步落后的通道）。密度、构成、千分比全部取自 tools/human_profile.mjs 对 20 局真局其余真人的统计
//（calib/human-profile.json），不凭印象。
//
// 在通用打法（G）之上，按会审总纲的六类原型加「猎食」行为，参数取自 R06 提案 §1.3 的实测画像：
//   O1 攒兵猎手    平时少打真人；身边的敌方真人兵密度掉到 35 以下、自己的兵 ≥ 对方 2 倍时，一条大比例指令收掉（补刀空仓）
//   O2 整仓喂大号  同一个战队标签的人把兵整仓（≥900‰）捐给队里地最多的那个号（3213 拍以后为主），大号按固定档连压
//   O3 固定档连压  盯住一个不还手的满仓邻居，用自己固定的千分比档（110~252‰）一条接一条地点，到对方死；对方还手够狠就换人
//   O4 梭哈客      兵 ≥ 对方 1.3 倍时一条 ≥900‰ 的全压
//   O5 跨海登陆    发船登陆不接壤的敌方真人，船上的兵不少于对方兵的一半
//   O6 分阶段抱团  同一个战队标签的人前期各自发育，1530 拍以后全队集火同一个邻居
//   IDLE 挂机      真局里整局没有下过指令的席位：一直不动
// 同队路人用同一批模型（队号和我方相同）；空壳 = 到点调用引擎的 leave（之后由内置 AI 托管）。
//
// 随机性全部来自 (种子, 席位, 拍号) 的散列：两条臂在同一拍给同一个席位的「运气」相同（配对比较用公共随机数）。
import fs from 'node:fs';
import path from 'node:path';
import { contacts, NEUTRAL, SIMV2 } from './match.mjs';
import { hashU, hashInt } from './util.mjs';

export const ARCHES = ['G', 'O1', 'O2', 'O3', 'O4', 'O5', 'O6', 'IDLE'];
export const DEFAULT_MIX = { G: 0.25, O3: 0.35, O1: 0.15, O4: 0.05, O5: 0.2 };   // 没有战队标签的人；有标签的战队一半 O2 一半 O6

// 固定档（千分比 → 引擎的 pct 单位）：提案 §1.3 量到的四档和人数比例
const TIERS = [[0.45, 112, 129], [0.27, 154, 171], [0.18, 211, 216], [0.10, 257, 257]];
const CLASSES = ['neutral', 'ai', 'hum', 'boat', 'don'];

let PROFILE = null;
export function loadProfile(file) {
  if (PROFILE && !file) return PROFILE;
  const f = file || path.join(SIMV2, 'calib', 'human-profile.json');
  if (!fs.existsSync(f)) throw new Error(`没有 ${f}：先跑 node sim-v2/tools/human_profile.mjs`);
  const raw = JSON.parse(fs.readFileSync(f, 'utf8'));
  const ph = raw.phases.map((p) => ({
    t0: p.t0, t1: p.t1, rate: p.ratePerAlive100,
    mix: CLASSES.map((c) => p.mix[c] || 0),
    neutral: p.neutral ? p.neutral.pct : null, ai: p.ai ? p.ai.pct : null, hum: p.hum ? p.hum.pct : null,
    humRatio: p.hum ? p.hum.sendRatio : null,       // 打真人时 出兵 ÷ 对方的兵 的 P25/中位/P75
    boat: p.boat ? p.boat.pct : null, don: p.don ? p.don.pct : null,
  }));
  const prof = { phases: ph, leave: raw.leave ? raw.leave.shareBefore : null, snaps: raw.snaps, matches: raw.matches };
  if (!file) PROFILE = prof;
  return prof;
}

// 分位点表 → 抽样（五点：P10/P25/P50/P75/P90；三点：P25/P50/P75；两端取平）
function sampleQ(tab, u) {
  if (!tab) return 128;
  const ks = tab.length === 5 ? [0.1, 0.25, 0.5, 0.75, 0.9] : [0.25, 0.5, 0.75];
  if (u <= ks[0]) return tab[0];
  for (let i = 1; i < ks.length; i++) if (u <= ks[i]) return Math.round(tab[i - 1] + (tab[i] - tab[i - 1]) * (u - ks[i - 1]) / (ks[i] - ks[i - 1]));
  return tab[tab.length - 1];
}

// 打真人的千分比（通用打法）：实测的千分比分布里混着大量「余额接近 0 的人连点全压」，直接照抽会让一个兵力正常的号拿三成以上的
// 余额去撞另一个真人。实测更稳的量是 出兵 ÷ 对方的兵（各阶段中位 0.14~0.20、P75 0.36~0.82），所以两者都抽、取小的那个。
function humanPct(ph, u1, u2, B, tB) {
  const byPct = sampleQ(ph.hum, u1);
  if (!ph.humRatio || !(B > 0)) return byPct;
  const ks = ph.humRatio;
  const r = u2 <= 0.25 ? ks[0] : u2 <= 0.5 ? ks[0] + (ks[1] - ks[0]) * (u2 - 0.25) / 0.25 : u2 <= 0.75 ? ks[1] + (ks[2] - ks[1]) * (u2 - 0.5) / 0.25 : ks[2];
  const byRatio = Math.ceil(Math.max(0.02, r) * tB * 1024 / B);
  return Math.max(40, Math.min(1023, Math.min(byPct, byRatio)));
}

// 标准正态（散列出的两个均匀数 → Box-Muller）
function gauss(u1, u2) { return Math.sqrt(-2 * Math.log(Math.max(1e-9, u1))) * Math.cos(2 * Math.PI * u2); }

export class Crowd {
  // cfg：{ seed, members:[{p, arche, clan}], startT, squad:[席位], rateScale, sigma, leaveAt: Map(p→拍) }
  constructor(arm, cfg) {
    this.arm = arm;
    this.seed = cfg.seed | 0;
    this.startT = cfg.startT || 0;
    this.prof = cfg.profile || loadProfile();
    this.rateScale = cfg.rateScale ?? 1;
    this.squad = new Set(cfg.squad || []);
    this.leaveAt = cfg.leaveAt || new Map();
    const sigma = cfg.sigma ?? 0.7;
    this.seats = [];
    this.clans = new Map();
    for (const m of cfg.members) {
      const p = m.p, sd = this.seed;
      const z = gauss(hashU(sd, p, 901), hashU(sd, p, 902));
      let tier = 128, acc = 0;
      const ut = hashU(sd, p, 903);
      for (const [w, a, b] of TIERS) { acc += w; if (ut <= acc) { tier = hashInt(a, b, sd, p, 904); break; } }
      const ur = hashU(sd, p, 905);
      const s = {
        p, arche: m.arche, clan: m.clan ?? -1,
        act: Math.exp(sigma * z - sigma * sigma / 2),          // 活跃度：对数正态，均值 1（实测每人指令密度 P75 ÷ 中位 ≈ 1.7）
        tier,                                                   // 打真人的固定档
        thr: ur < 0.15 ? 0.7 : ur < 0.35 ? 1.2 : 2.0,           // 开打时 自己的兵 ÷ 对方的兵 的下限（157 组围攻：<1 的 24 组，≥2 的 100 组）
        full: hashU(sd, p, 906) < 0.6,                          // 满仓型：3210 拍以后密度 ≥ 60 才打真人（出兵的 58% 来自密度 ≥ 90 的号）
        victim: -1, avoid: new Map(), lastFinish: -1e9, n: 0,
      };
      this.seats.push(s);
      if (s.clan >= 0) {
        let c = this.clans.get(s.clan);
        if (!c) this.clans.set(s.clan, (c = { id: s.clan, arche: m.arche, members: [], boss: -1, focus: -1, at: -1e9 }));
        c.members.push(s);
      }
    }
    // 账：对我方席位的陆攻 / 登陆、各原型的指令数
    this.log = { byArche: {}, onSquad: [], cmds: 0, ok: 0, byClass: { neutral: 0, ai: 0, hum: 0, boat: 0, don: 0 }, donOk: 0, donBig: 0, finish: 0, left: 0 };
    // 出手强度的账（与 tools/human_profile.mjs 同口径）：各阶段 生效指令数、出手的兵、在场人·拍、余额·拍
    this.intensity = this.prof.phases.map((p) => ({ t0: p.t0, cmds: 0, sent: 0, aliveTicks: 0, balTicks: 0 }));
  }

  phaseIdx(t) {
    const ph = this.prof.phases;
    for (let i = ph.length - 1; i >= 0; i--) if (t >= ph[i].t0) return i;
    return 0;
  }

  phase(t) {
    const ph = this.prof.phases;
    for (let i = ph.length - 1; i >= 0; i--) if (t >= ph[i].t0) return ph[i];
    return ph[0];
  }

  act(arm, t) {
    if (t % 7 !== 0 || t < this.startT) return;
    const w = arm.world;
    if (w.over) return;
    const ph = this.phase(t);
    const I = this.intensity[this.phaseIdx(t)];
    this.curI = I;
    for (const c of this.clans.values()) if (t - c.at >= 210) this.clanUpdate(c, t);
    for (const s of this.seats) {
      const p = s.p;
      if (!w.alive[p] || w.state[p] === 2) continue;
      const lv = this.leaveAt.get(p);
      if (lv !== undefined && t >= lv) { w.leave(p); arm.quit.add(p); this.log.left++; continue; }
      I.aliveTicks += 7; I.balTicks += 7 * w.bal[p];
      if (s.arche === 'IDLE') continue;
      this.decide(s, t, ph);
    }
  }

  clanUpdate(c, t) {
    const w = this.arm.world;
    c.at = t;
    let boss = -1;
    for (const s of c.members) if (w.alive[s.p] && w.state[s.p] !== 2 && (boss < 0 || w.terr[s.p] > w.terr[boss])) boss = s.p;
    c.boss = boss;
    if (c.arche !== 'O6' || t < 1530) { c.focus = -1; return; }
    // 集火对象：挨着本队人数最多的敌方真人；并列取兵最少的
    const cnt = new Map();
    for (const s of c.members) {
      if (!w.alive[s.p] || w.state[s.p] === 2) continue;
      for (const q of contacts(w, s.p).keys()) {
        if (q === NEUTRAL || !w.alive[q] || w.isBot(q) || !w.isEnemy(s.p, q)) continue;
        cnt.set(q, (cnt.get(q) || 0) + 1);
      }
    }
    let best = -1;
    for (const [q, n] of cnt) if (best < 0 || n > cnt.get(best) || (n === cnt.get(best) && w.bal[q] < w.bal[best])) best = q;
    c.focus = best;
  }

  note(s, cls, ok, extra) {
    const L = this.log;
    L.cmds++; if (ok) L.ok++;
    if (ok && cls !== 'don' && this.curI) { this.curI.cmds++; this.curI.sent += this.arm.world.attackTroopsTmp; }
    L.byClass[cls]++;
    const a = (L.byArche[s.arche] ||= { cmds: 0, ok: 0, hum: 0, onSquad: 0, sentOnSquad: 0 });
    a.cmds++; if (ok) a.ok++;
    if (cls === 'hum') a.hum++;
    if (extra && ok) { a.onSquad++; a.sentOnSquad += extra.sent; if (L.onSquad.length < 20000) L.onSquad.push(extra); }
  }

  attackHuman(s, q, pct, t, kind) {
    const w = this.arm.world, p = s.p;
    const B = w.bal[p], tB = w.bal[q], tT = w.terr[q];
    const back = w.hasAttack(q, p) ? 1 : 0;
    const ok = w.attack(pct, q, p);
    const onSq = this.squad.has(q);
    this.note(s, 'hum', ok, onSq ? { t, p, q, arche: s.arche, kind, pct, sent: ok ? w.attackTroopsTmp : 0, B, tB, tD: tT > 0 ? tB / tT : 0, D: w.terr[p] > 0 ? B / w.terr[p] : 0, back } : null);
    return ok;
  }

  decide(s, t, ph) {
    const w = this.arm.world, p = s.p, sd = this.seed;
    const B = w.bal[p], T = w.terr[p];
    if (B < 2 || T < 1) return;
    const D = B / T;
    let adj = null;

    // ---- O1：补刀空仓（每个回合都看，不受出手密度限制；同一个号 70 拍内只补一次）
    if (s.arche === 'O1' && t >= 1071 && t - s.lastFinish >= 70) {
      adj = contacts(w, p);
      let best = -1;
      for (const q of adj.keys()) {
        if (q === NEUTRAL || !w.alive[q] || w.isBot(q) || !w.isEnemy(p, q)) continue;
        const tB = w.bal[q], tT = w.terr[q];
        if (tT < 30 || tB / tT >= 35 || B < 2 * tB) continue;
        if (best < 0 || w.terr[q] > w.terr[best]) best = q;
      }
      if (best >= 0) {
        const need = Math.ceil(1.5 * (w.bal[best] + 2 * w.terr[best]) * 1024 / B);
        const pct = Math.max(307, Math.min(1023, need));
        s.lastFinish = t;
        this.log.finish++;
        this.attackHuman(s, best, pct, t, 'finish');
        return;
      }
    }

    // ---- 出手机会：实测密度 × 活跃度；顶到软上限（密度 ≥ 100）或正在围一个人时加倍
    let rate = ph.rate * s.act * this.rateScale;
    if (D >= 100) rate *= 2;
    if (s.victim >= 0) rate *= 2;
    if (hashU(sd, p, t, 1) >= rate * 0.07) return;
    adj = adj || contacts(w, p);

    const bots = [], hums = [];
    let nEnemy = 0;
    for (const [q, n] of adj) {
      if (q === NEUTRAL || !w.alive[q] || !w.isEnemy(p, q)) continue;
      nEnemy += n;
      if (w.isBot(q)) bots.push([q, n]); else hums.push([q, n]);
    }
    // 身边的无主地只剩边角（占接壤的不到 1/4）时，按比例少打无主地：真人不会对着几格空地反复出兵
    const nNeutral = adj.get(NEUTRAL) || 0;
    const fN = nNeutral / Math.max(1, nNeutral + nEnemy);
    const clan = s.clan >= 0 ? this.clans.get(s.clan) : null;
    const isBoss = clan && clan.arche === 'O2' && clan.boss === p;
    const avail = [adj.has(NEUTRAL), bots.length > 0, hums.length > 0, w.boatsAllowed(p), !!w.teamGame && t >= 357];
    const wts = ph.mix.slice();
    wts[0] *= Math.min(1, fN / 0.25);
    if (s.arche === 'O1') wts[2] *= 0.35;
    if (s.arche === 'O3' || isBoss) wts[2] *= 1.4;
    if (s.arche === 'O4') wts[2] *= 0.6;
    if (s.arche === 'O5' && t >= 1071) wts[3] *= 3;
    if (s.arche === 'O6' && t >= 1530) wts[2] *= 1.5;
    if (clan && clan.arche === 'O2' && !isBoss && clan.boss >= 0) wts[4] *= t >= 3213 ? 5 : 1.5;
    let tot = 0;
    for (let i = 0; i < 5; i++) { if (!avail[i]) wts[i] = 0; tot += wts[i]; }
    if (!(tot > 0)) return;
    let u = hashU(sd, p, t, 2) * tot, cls = 0;
    for (; cls < 4; cls++) { if (u < wts[cls]) break; u -= wts[cls]; }
    const up = hashU(sd, p, t, 3);
    s.n++;

    if (cls === 0) {
      this.note(s, 'neutral', w.attack(sampleQ(ph.neutral, up), NEUTRAL, p));
      return;
    }
    if (cls === 1) {
      // 内置 AI / 空壳：实测真人在身边的 AI 里近乎随手挑（邻居数中位 7 个时，挑中接壤最长的 25%、地最多的 18%、兵最少的 19%），
      // 这里按接壤长度的平方根加权随机挑；实测出兵 ÷ 对方的兵 中位约 5（多数是碾压），兵不够吃掉它就加码到 1.5 倍，加到 500‰ 还不够就等
      let tw = 0;
      for (const [, n] of bots) tw += Math.sqrt(n);
      let ub = hashU(sd, p, t, 9) * tw, q = bots[bots.length - 1][0];
      for (const [o, n] of bots) { ub -= Math.sqrt(n); if (ub < 0) { q = o; break; } }
      let pct = sampleQ(ph.ai, up);
      const need = Math.ceil(1.5 * w.bal[q] * 1024 / B);
      if (need > pct) { if (need > 512) return; pct = need; }
      this.note(s, 'ai', w.attack(pct, q, p));
      return;
    }
    if (cls === 2) return this.fightHuman(s, t, ph, hums, B, D, up, clan, isBoss);
    if (cls === 3) return this.sendBoat(s, t, ph, B, up);
    return this.give(s, t, ph, B, up, clan, isBoss);
  }

  fightHuman(s, t, ph, hums, B, D, up, clan, isBoss) {
    const w = this.arm.world, p = s.p, sd = this.seed;
    // 还手：有人正在打我 → 按实测概率回手（我的兵 ≥ 对方 2 倍 46%，否则 22%），回手打出兵最多的那个
    let atk = -1, atkTroops = 0;
    for (const [q] of hums) { const a = w.attackTroopsOn(q, p); if (a > atkTroops) { atkTroops = a; atk = q; } }
    if (atk >= 0 && hashU(sd, p, t, 4) < (B >= 2 * w.bal[atk] ? 0.46 : 0.22)) {
      this.attackHuman(s, atk, s.arche === 'O4' && B >= 1.3 * w.bal[atk] ? hashInt(921, 1023, sd, p, t, 5) : s.arche === 'G' || t < 1530 ? humanPct(ph, up, hashU(sd, p, t, 11), B, w.bal[atk]) : s.tier, t, 'back');
      return;
    }
    if (s.full && t >= 3210 && D < 60) return;     // 满仓型：没攒够不主动打真人

    // 集火（O6）/ 大号（O2）优先打战队选定的对象
    if (clan && clan.arche === 'O6' && clan.focus >= 0 && hums.some(([q]) => q === clan.focus)) {
      this.attackHuman(s, clan.focus, s.tier, t, 'focus');
      return;
    }
    if (s.arche === 'O4') {
      let q = -1;
      for (const [o] of hums) if (B >= 1.3 * w.bal[o] && (q < 0 || w.bal[o] < w.bal[q])) q = o;
      if (q >= 0) this.attackHuman(s, q, hashInt(921, 1023, sd, p, t, 5), t, 'allin');
      return;
    }
    if (s.arche === 'O3' || isBoss || s.arche === 'O6' || s.arche === 'O2') {
      // 盯人连压：先看手里的对象还在不在；对方还手够狠（压在我身上的兵 > 我余额的 1/4）就有一半机会放手，600 拍内不再碰它
      let q = s.victim;
      if (q >= 0 && (!w.alive[q] || w.isBot(q) || !hums.some(([o]) => o === q))) q = s.victim = -1;
      if (q >= 0 && w.attackTroopsOn(q, p) > B / 4 && hashU(sd, p, t, 6) < 0.5) { s.avoid.set(q, t + 600); q = s.victim = -1; }
      if (q < 0) {
        let best = -1, bs = -1;
        for (const [o, n] of hums) {
          if ((s.avoid.get(o) || 0) > t) continue;
          const tB = w.bal[o], tT = w.terr[o];
          if (B < s.thr * tB) continue;
          // 偏好：不在打我的、满仓的（3210 拍以后密度 ≥ 60）、接壤多的、比我弱得多的
          let sc = Math.sqrt(n) * Math.min(8, B / (tB + 1));
          if (!w.hasAttack(o, p)) sc *= 2;
          if (t >= 3210 && tT > 0 && tB / tT >= 60) sc *= 1.5;
          if (sc > bs) { bs = sc; best = o; }
        }
        q = s.victim = best;
      }
      if (q >= 0) this.attackHuman(s, q, s.tier, t, 'press');
      return;
    }
    // 通用（G、O1 平时、O5 在陆上）：实测真人在身边的敌方真人里 45%~76% 挑兵最少的那个（邻居数中位 3 个，随手挑是 1/3），
    // 接壤长短几乎不看；这里 2/3 的时候打兵最少的，其余随手挑。千分比按实测分布抽。
    let best = -1;
    if (hashU(sd, p, t, 7) < 0.67) { for (const [o] of hums) if (best < 0 || w.bal[o] < w.bal[best]) best = o; }
    else best = hums[hashInt(0, hums.length - 1, sd, p, t, 10)][0];
    if (best >= 0) this.attackHuman(s, best, humanPct(ph, up, hashU(sd, p, t, 11), B, w.bal[best]), t, 'plain');
  }

  sendBoat(s, t, ph, B, up) {
    const w = this.arm.world, p = s.p, sd = this.seed, H = w.humans;
    // 候选：随机看 10 个在场的敌方玩家（1071 拍以前内置 AI 也算），要有海岸；O5 挑不接壤、兵不到自己一半的真人
    let best = -1, bs = -1;
    const hunter = s.arche === 'O5' && t >= 1071;
    for (let k = 0; k < 10; k++) {
      const q = hunter || t >= 1530 ? hashInt(0, H - 1, sd, p, t, 20 + k) : w.aliveList[hashInt(0, Math.max(0, w.aliveCount - 1), sd, p, t, 20 + k)];
      if (q === p || !w.alive[q] || !w.isEnemy(p, q) || !w.coast[q] || !w.coast[q].length) continue;
      const tB = w.bal[q];
      let sc = Math.min(8, B / (tB + 1));
      if (hunter && (w.isBot(q) || B < 2 * tB)) continue;
      if (!hunter && B < 0.8 * tB) continue;
      sc *= 0.5 + hashU(sd, p, t, 40 + k);
      if (sc > bs) { bs = sc; best = q; }
    }
    if (best < 0) return;
    const coast = w.coast[best];
    const tile = coast[hashInt(0, coast.length - 1, sd, p, t, 60)];
    let pct = sampleQ(ph.boat, up);
    if (hunter) pct = Math.max(pct, Math.min(614, Math.ceil(0.5 * w.bal[best] * 1024 / B)));   // 大登陆：不少于对方兵的一半，封顶 600‰
    const tB = w.bal[best], tT = w.terr[best];
    const ok = w.boatTo(pct, tile, p);
    const onSq = this.squad.has(best);
    this.note(s, 'boat', ok, onSq ? { t, p, q: best, arche: s.arche, kind: 'boat', pct, sent: ok ? w.attackTroopsTmp : 0, B, tB, tD: tT > 0 ? tB / tT : 0, D: w.terr[p] > 0 ? B / w.terr[p] : 0, back: 0 } : null);
  }

  give(s, t, ph, B, up, clan, isBoss) {
    const w = this.arm.world, p = s.p, sd = this.seed, H = w.humans;
    let q = -1, pct = sampleQ(ph.don, up);
    if (clan && clan.arche === 'O2' && !isBoss && clan.boss >= 0 && w.alive[clan.boss]) {
      q = clan.boss;
      if (t >= 3213) pct = hashInt(921, 1023, sd, p, t, 8);
    } else {
      // 通用：捐给同队里地最多的在场真人
      for (let o = 0; o < H; o++) if (o !== p && w.alive[o] && w.state[o] !== 2 && w.isTeammate(p, o) && (q < 0 || w.terr[o] > w.terr[q])) q = o;
    }
    if (q < 0) return;
    const ok = w.donate(pct, q, p);
    this.note(s, 'don', ok);
    if (ok) { this.log.donOk++; if (pct >= 921) this.log.donBig++; }
  }

  // 对我方席位的进攻画像（与提案 §1.3 的实测表同口径：按兵算的千分比档、对象密度档、4284 拍以后的占比）
  summary() {
    const L = this.log, rows = L.onSquad;
    const sent = rows.reduce((a, r) => a + r.sent, 0);
    const share = (f) => (sent > 0 ? +(rows.filter(f).reduce((a, r) => a + r.sent, 0) / sent).toFixed(3) : null);
    const cshare = (f) => (rows.length ? +(rows.filter(f).length / rows.length).toFixed(3) : null);
    const pm = (r) => Math.round((r.pct + 1) * 1000 / 1024);
    return {
      cmds: L.cmds, ok: L.ok, byClass: L.byClass, byArche: L.byArche, donOk: L.donOk, donBig: L.donBig, finish: L.finish, left: L.left,
      intensity: this.intensity.map((I) => ({ t0: I.t0, cmds: I.cmds, ratePerAlive100: I.aliveTicks ? +(100 * I.cmds / I.aliveTicks).toFixed(3) : null, spendPer100: I.balTicks ? +(100 * I.sent / I.balTicks).toFixed(4) : null, sentPerCmd: I.cmds ? Math.round(I.sent / I.cmds) : null })),
      onSquad: {
        n: rows.length, sent,
        land: rows.filter((r) => r.kind !== 'boat').length, boats: rows.filter((r) => r.kind === 'boat').length,
        pctBySent: { '<100': share((r) => pm(r) < 100), '100~199': share((r) => pm(r) >= 100 && pm(r) < 200), '200~399': share((r) => pm(r) >= 200 && pm(r) < 400), '400~899': share((r) => pm(r) >= 400 && pm(r) < 900), '>=900': share((r) => pm(r) >= 900) },
        targetDensityBySent: { '<35': share((r) => r.tD < 35), '35~60': share((r) => r.tD >= 35 && r.tD < 60), '60~100': share((r) => r.tD >= 60 && r.tD < 100), '>=100': share((r) => r.tD >= 100) },
        targetDensityByCount: { '<35': cshare((r) => r.tD < 35), '>=60': cshare((r) => r.tD >= 60) },
        ratio2BySent: share((r) => r.B >= 2 * r.tB),
        fullBodyBySent: share((r) => r.D >= 90),
        after4284BySent: share((r) => r.t >= 4284),
        targetFightingBack: cshare((r) => r.back),
        byKind: Object.fromEntries(['press', 'plain', 'back', 'finish', 'allin', 'focus', 'boat'].map((k) => [k, rows.filter((r) => r.kind === k).length])),
      },
    };
  }
}

// 给一组其余真人分配原型。clans：[{ id, members:[席位] }]（人数 ≥ 2 的战队）；mix：{ 原型: 权重 }；clanArches：有标签的战队轮着用的原型
export function assignArches(seed, others, clans, mix, clanArches, idle) {
  const out = new Map();
  const inClan = new Map();
  let ci = 0;
  for (const c of clans) {
    if (!clanArches.length || c.members.length < 2) continue;
    const a = clanArches[(hashInt(0, 97, seed, c.id, 911) + ci++) % clanArches.length];
    for (const p of c.members) inClan.set(p, { arche: a, clan: c.id });
  }
  const keys = Object.keys(mix).filter((k) => mix[k] > 0);
  const tot = keys.reduce((a, k) => a + mix[k], 0);
  for (const p of others) {
    if (idle && idle.has(p)) { out.set(p, { p, arche: 'IDLE', clan: -1 }); continue; }
    if (inClan.has(p)) { out.set(p, { p, ...inClan.get(p) }); continue; }
    let u = hashU(seed, p, 912) * tot, a = keys[keys.length - 1];
    for (const k of keys) { if (u < mix[k]) { a = k; break; } u -= mix[k]; }
    out.set(p, { p, arche: a, clan: -1 });
  }
  return [...out.values()];
}

export function parseMix(spec) {
  if (!spec || spec === true) return { ...DEFAULT_MIX };
  const out = {};
  for (const part of String(spec).split(',')) {
    const [k, v] = part.split(':');
    const key = k.trim().toUpperCase();
    if (!ARCHES.includes(key)) throw new Error(`不认识的对手原型 ${k}（可用：${ARCHES.join(' ')}）`);
    out[key] = v === undefined ? 1 : +v;
  }
  return out;
}
