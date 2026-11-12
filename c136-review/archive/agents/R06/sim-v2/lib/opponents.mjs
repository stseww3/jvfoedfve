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
  const tabOf = (x) => (x ? x.seatQ || x.pctQ || x.pct : null);
  // 各滑块档位（按人五等分，低→高）的点击密度 ÷ 五档平均：实测最低一档点得最勤（490~1071 拍是其余档的 1.3~1.8 倍）
  const relRate = (p) => {
    const g = p.byStyle && p.byStyle.groups;
    if (!g || g.length !== 5) return [1, 1, 1, 1, 1];
    const m = g.reduce((a, x) => a + x.rate, 0) / 5;
    return m > 0 ? g.map((x) => x.rate / m) : [1, 1, 1, 1, 1];
  };
  // 样本太少的类别（细阶段里开局的打 AI / 打真人只有十几条）借相邻阶段的表，免得被几条指令带偏
  const borrow = (i, c) => {
    for (let d = 0; d < raw.phases.length; d++) for (const j of [i + d, i - d]) {
      const x = raw.phases[j] && raw.phases[j][c];
      if (x && x.n >= 60) return x;
    }
    return raw.phases[i][c] || null;
  };
  const condOf = (p) => {
    const tot = Math.max(1, CLASSES.reduce((a, k) => a + (p.mix[k] || 0), 0));
    const flat = (c) => (p.okRateBy ? p.okRateBy[c] || 0 : p.ratePerAlive100 * (p.mix[c] || 0) / tot);
    const c1 = p.condRateBy || {}, c2 = p.cond2 || {};
    const hum = c1.hum ?? flat('hum');
    const farm = c2.humFarm && c2.humFarm.cmds >= 20 ? c2.humFarm.rate : hum;
    const noFarm = c2.humNoFarm && c2.humNoFarm.cmds >= 20 ? c2.humNoFarm.rate : farm * 1.3;
    // 再按「这类对象占自己接壤的几成」分四档（≤10% / 10~30% / 30~60% / >60%）：打 AI 的密度随这个占比单调上升
    //（850~1071 拍：1.05 → 1.72 → 2.56 → 2.75），所以被 AI 围着的小房间里真人打 AI 比 20 局平均勤得多。样本太少的档用不分档的条件密度。
    const byB = (k, base) => [0, 1, 2, 3].map((b) => {
      const x = p.condB && p.condB[k] && p.condB[k][b];
      return x && (x.cmds >= 20 || x.expo >= 0.02) ? x.rate : base;
    });
    const nBase = c1.neutral ?? flat('neutral'), aBase = c1.ai ?? flat('ai');
    return {
      neutral: nBase, ai: aBase, humFarm: farm, humNoFarm: noFarm,
      neutralB: byB('neutral', nBase), aiB: byB('ai', aBase), humB: byB('hum', hum),
      farmK: hum > 0 ? farm / hum : 1, noFarmK: hum > 0 ? noFarm / hum : 1,
      boat: flat('boat'), don: p.aliveTicks ? 100 * (p.mix.don || 0) / p.aliveTicks : 0,
    };
  };
  const ph = raw.phases.map((p, i) => ({
    t0: p.t0, t1: p.t1, rate: p.ratePerAlive100, relRate: relRate(p),
    mix: CLASSES.map((c) => p.mix[c] || 0),
    // 各类指令流的强度（每 100 拍几条生效指令）。陆攻三类是「身边有这类对象时」的条件密度 —— 打 AI 的总密度 1071 拍以后往下掉，
    // 主要是 AI 被吃光了（身边还有 AI 的人照样每 100 拍打 1.5~2 条），所以 AI 多的小房间里真人会一直吃到 1530 拍以后；
    // 打真人再分「身边还有无主地或 AI 可吃」和「都没有了」两种处境（后者高三成）。发船、捐款按在场人·拍算。
    cond: condOf(p),
    // 连点：实测同一个人相邻两条指令只隔 1 个回合的占 14%~36%（开局最高）。按配额均匀派单时自然出现的约 12%，
    // 差的部分用「刚出过手的席位下一个回合再点一次」补上。连点的第二下只能拿到剩下的余额，所以同样的指令数花掉的兵更少。
    // 连点主要是滑块拉满的人（开局 500 拍内最高一档的连点占比 41%~53%，其余档 15%~30%），所以按滑块五档分别给概率。
    follow: (p.byStyle && p.byStyle.groups && p.byStyle.groups.length === 5 && p.byStyle.groups.every((g) => g.seats >= 25) ? p.byStyle.groups.map((g) => g.burst7) : [0, 1, 2, 3, 4].map(() => p.burst7 ?? 0.12)).map((b) => Math.max(0, (b - 0.12) / 0.88)),
    neutral: tabOf(borrow(i, 'neutral')), ai: tabOf(borrow(i, 'ai')), hum: tabOf(borrow(i, 'hum')),
    humRatio: (borrow(i, 'hum') || {}).sendRatio || null,       // 打真人时 出兵 ÷ 对方的兵 的 P25/中位/P75
    boat: tabOf(borrow(i, 'boat')), don: tabOf(borrow(i, 'don')),
  }));
  const prof = { phases: ph, leave: raw.leave ? raw.leave.shareBefore : null, snaps: raw.snaps, matches: raw.matches, style: raw.style || null };
  if (!file) PROFILE = prof;
  return prof;
}

// 分位点表 → 抽样（21 点：0%、5%、…、100%；五点：P10/P25/P50/P75/P90；三点：P25/P50/P75；两端取平）
function sampleQ(tab, u) {
  if (!tab) return 128;
  if (tab.length === 21) {
    const x = Math.max(0, Math.min(1, u)) * 20, i = Math.min(19, Math.floor(x));
    return Math.round(tab[i] + (tab[i + 1] - tab[i]) * (x - i));
  }
  const ks = tab.length === 5 ? [0.1, 0.25, 0.5, 0.75, 0.9] : [0.25, 0.5, 0.75];
  if (u <= ks[0]) return tab[0];
  for (let i = 1; i < ks.length; i++) if (u <= ks[i]) return Math.round(tab[i - 1] + (tab[i] - tab[i - 1]) * (u - ks[i - 1]) / (ks[i] - ks[i - 1]));
  return tab[tab.length - 1];
}

// 标准正态的分布函数（Abramowitz–Stegun 7.1.26 的 erf 近似，误差 < 1.5e-7）
function Phi(z) {
  const x = Math.abs(z) / Math.SQRT2, t = 1 / (1 + 0.3275911 * x);
  const erf = 1 - (((((1.061405429 * t - 1.453152027) * t) + 1.421413741) * t - 0.284496736) * t + 0.254829592) * t * Math.exp(-x * x);
  return z >= 0 ? 0.5 * (1 + erf) : 0.5 * (1 - erf);
}

// 出手风格（千分比滑块）的个人一致性 —— tools/human_profile.mjs 实测：同一个人在同一阶段里的千分比几乎不变（组内相关 0.93~0.99），
// 跨阶段慢慢变（630 拍前后两段的个人平均分相关 0.56，1530 拍以前合并的组内相关 0.67），滑块拉得低的人点得更勤（相关 −0.28）。
// 所以每个席位的「滑块名次」= 终身分量 + 跨阶段慢变分量（一阶自回归）+ 单条指令的小抖动，再按本阶段本类别的实测分位表换成千分比。
// 每条指令独立抽（旧做法）会让每个号都隔三差五全压一次、把余额清零，开局每 10 拍 5~7% 的利息滚不起来，600 拍以后人均地少两成。
// 滑块与点击密度的关系不走相关系数，直接用各阶段「滑块五档 × 点击密度」的实测表（relRate）。
const STYLE = { life: 0.45, slow: 0.49, jitter: 0.06, phi: 0.7 };

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
    // 活跃度的个人差异：实测每人指令数 P75 ÷ P25 ≈ 2.5（对数标准差 0.68），其中计数噪声（每人每阶段只有五六条）占 0.42、
    // 滑块档位之间的密度差占 0.17，剩下个人固有的差异约 0.5
    const sigma = cfg.sigma ?? 0.5;
    this.seats = [];
    this.clans = new Map();
    for (const m of cfg.members) {
      const p = m.p, sd = this.seed;
      const zs = gauss(hashU(sd, p, 907), hashU(sd, p, 908));
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
        zs, slow: [],                                           // 滑块名次的终身分量、各阶段的慢变分量
        avN: true, avB: false, avH: false,                      // 身边有没有无主地 / 内置 AI 与空壳 / 敌方真人（每 70 拍刷新）
        bN: 3, bB: -1, bH: -1,                                  // 这三类各占自己接壤的几成（四档；-1 = 没有）
        followT: -1, followCls: 0, lastT: -1, q5: 2,
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
    this.intensity = this.prof.phases.map((p) => ({
      t0: p.t0, cmds: 0, sent: 0, aliveTicks: 0, balTicks: 0, sentBy: { neutral: 0, ai: 0, hum: 0, boat: 0 }, okBy: { neutral: 0, ai: 0, hum: 0, boat: 0 },
      byStyle: [0, 1, 2, 3, 4].map(() => ({ alive: 0, bal: 0, sent: 0, cmds: 0 })),      // 按滑块五档：在场人·拍、余额·拍、出手的兵、生效指令数
    }));
    this.aiRows = [];
    // 配额记账（把各类指令的落地数钉在实测的条件密度上）：每个回合，每个在场席位按自己此刻的处境（身边有没有这类对象）
    // 给各类指令流记「应有的条数」（实测条件密度 × 7 拍）；某一类攒满 1 条，就在此刻能打这一类的席位里按个人权重
    //（活跃度 × 滑块档位的相对密度 × 原型偏好）抽一个去打；没打成（余额不够、条件不满足）不扣账，换一个席位再试。
    // 这样模型里各种「出不了手」的情况不会把整体密度拉低（按固定概率各抽各的时，打真人和发船只有实测的一半），
    // 也不会像反馈式倍率那样滞后、过冲（试过：231~357 拍会多打三成）。
    this.gapN = 0; this.gap7 = 0;
    this.credit = [0, 0, 0, 0, 0];
    this.dropped = [0, 0, 0, 0, 0];     // 攒到封顶被丢掉的应有条数（处境允许、但全场都出不了手）
    this.availAt = -1e9;
    this.W = CLASSES.map(() => new Float64Array(this.seats.length));
  }

  // 每 70 拍刷新每个在场席位「身边有没有无主地 / 内置 AI 与空壳 / 敌方真人」（与 human_profile.mjs 的口径、节拍一致）
  refreshAvail(t) {
    const w = this.arm.world;
    this.availAt = t;
    for (const s of this.seats) {
      const p = s.p;
      if (!w.alive[p] || w.state[p] === 2) continue;
      this.setAvail(s, contacts(w, p));
    }
  }

  setAvail(s, adj) {
    const w = this.arm.world, p = s.p;
    let tot = 0, n = 0, b = 0, h = 0;
    for (const [q, c] of adj) {
      tot += c;
      if (q === NEUTRAL) n += c;
      else if (w.alive[q] && w.isEnemy(p, q)) { if (w.isBot(q)) b += c; else h += c; }
    }
    const bk = (x) => (x <= 0 ? -1 : x <= 0.1 * tot ? 0 : x <= 0.3 * tot ? 1 : x <= 0.6 * tot ? 2 : 3);
    s.avN = n > 0; s.avB = b > 0; s.avH = h > 0;
    s.bN = bk(n); s.bB = bk(b); s.bH = bk(h);
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

  // 这个席位在本阶段的滑块名次（0~1，不含单条指令的抖动）：同一阶段里不变，跨阶段慢变
  styleBase(s, t) {
    const sd = this.seed, pi = this.phaseIdx(t);
    while (s.slow.length <= pi) {
      const i = s.slow.length, e = gauss(hashU(sd, s.p, 930 + i, 1), hashU(sd, s.p, 930 + i, 2));
      s.slow.push(i === 0 ? e : STYLE.phi * s.slow[i - 1] + Math.sqrt(1 - STYLE.phi * STYLE.phi) * e);
    }
    return (Math.sqrt(STYLE.life) * s.zs + Math.sqrt(STYLE.slow) * s.slow[pi]) / Math.sqrt(STYLE.life + STYLE.slow);
  }

  // 这条指令在滑块名次上的位置（0~1）：阶段名次 + 一点抖动
  styleU(s, t) {
    const zc = gauss(hashU(this.seed, s.p, t, 12), hashU(this.seed, s.p, t, 13));
    return Phi(Math.sqrt(STYLE.life + STYLE.slow) * this.styleBase(s, t) + Math.sqrt(STYLE.jitter) * zc);
  }

  act(arm, t) {
    if (t % 7 !== 0 || t < this.startT) return;
    const w = arm.world;
    if (w.over) return;
    const ph = this.phase(t), sd = this.seed;
    const I = this.intensity[this.phaseIdx(t)];
    this.curI = I;
    for (const c of this.clans.values()) if (t - c.at >= 210) this.clanUpdate(c, t);
    if (t - this.availAt >= 70) this.refreshAvail(t);
    const cd = ph.cond, W = this.W, credit = this.credit, tot = [0, 0, 0, 0, 0];
    const n = this.seats.length, k = 0.07 * this.rateScale;
    let present = 0;
    for (let i = 0; i < n; i++) {
      const s = this.seats[i], p = s.p;
      W[0][i] = W[1][i] = W[2][i] = W[3][i] = W[4][i] = 0;
      if (!w.alive[p] || w.state[p] === 2) continue;
      const lv = this.leaveAt.get(p);
      if (lv !== undefined && t >= lv) { w.leave(p); arm.quit.add(p); this.log.left++; continue; }
      present++;
      const B = w.bal[p], T = w.terr[p];
      I.aliveTicks += 7; I.balTicks += 7 * B;
      s.q5 = Math.min(4, Math.floor(Phi(this.styleBase(s, t)) * 5));
      const Iq = I.byStyle[s.q5];
      Iq.alive += 7; Iq.bal += 7 * B;
      // 应有条数：所有在场席位都记（含挂机的、此刻没有余额的 —— 实测密度的分母就是全部在场真人）
      const b0 = s.bN >= 0 ? cd.neutralB[s.bN] : 0, b1 = s.bB >= 0 ? cd.aiB[s.bB] : 0;
      const b2 = s.bH >= 0 ? cd.humB[s.bH] * (s.avN || s.avB ? cd.farmK : cd.noFarmK) : 0;
      const b3 = cd.boat, b4 = w.teamGame && t >= 357 ? cd.don : 0;
      credit[0] += b0 * k; credit[1] += b1 * k; credit[2] += b2 * k; credit[3] += b3 * k; credit[4] += b4 * k;
      if (s.arche === 'IDLE' || B < 2 || T < 1) continue;
      // 连点：上个回合出过手、抽中了「再点一次」的席位，这个回合先出同一类
      if (s.followT === t) {
        s.followT = -1;
        if (this.perform(s, s.followCls, t, ph)) { credit[s.followCls] -= 1; this.afterOk(s, s.followCls, t, ph); }
        continue;
      }
      // O1：补刀空仓（每个回合都看；同一个号 70 拍内只补一次；补了也记在打真人的账上）
      if (s.arche === 'O1' && t >= 1071 && t - s.lastFinish >= 70 && this.finisher(s, t)) { credit[2] -= 1; continue; }
      // 个人权重：活跃度 × 滑块档位的相对密度；顶到软上限（密度 ≥ 100）加倍；正在围一个人时打真人加倍；再乘原型偏好
      let g = s.act * ph.relRate[s.q5];
      if (B >= 100 * T) g *= 2;
      const clan = s.clan >= 0 ? this.clans.get(s.clan) : null;
      const isBoss = clan && clan.arche === 'O2' && clan.boss === p;
      let h = s.victim >= 0 ? 2 : 1, bo = 1, dn = 1;
      if (s.arche === 'O1') h *= 0.35;
      if (s.arche === 'O3' || isBoss) h *= 1.4;
      if (s.arche === 'O4') h *= 0.6;
      if (s.arche === 'O5' && t >= 1071) bo *= 3;
      if (s.arche === 'O6' && t >= 1530) h *= 1.5;
      if (clan && clan.arche === 'O2' && !isBoss && clan.boss >= 0) dn *= t >= 3213 ? 5 : 1.5;
      tot[0] += (W[0][i] = b0 * g); tot[1] += (W[1][i] = b1 * g); tot[2] += (W[2][i] = b2 * g * h);
      tot[3] += (W[3][i] = b3 * g * bo); tot[4] += (W[4][i] = b4 * g * dn);
    }
    const cap = 2 + 0.03 * present;
    for (let c = 0; c < 5; c++) {
      const maxTries = 6 + 2 * Math.floor(Math.max(0, credit[c]));
      for (let tries = 0; credit[c] >= 1 && tot[c] > 1e-9 && tries < maxTries; tries++) {
        let u = hashU(sd, t, 700 + c, tries) * tot[c], pick = -1;
        const Wc = W[c];
        for (let i = 0; i < n; i++) { if (Wc[i] > 0) { pick = i; u -= Wc[i]; if (u < 0) break; } }
        if (pick < 0) break;
        const ok = this.perform(this.seats[pick], c, t, ph);
        for (let c2 = 0; c2 < 5; c2++) { tot[c2] -= W[c2][pick]; W[c2][pick] = 0; }    // 一个席位一个回合只出一条
        if (ok) { credit[c] -= 1; this.afterOk(this.seats[pick], c, t, ph); }
      }
      if (credit[c] > cap) { this.dropped[c] += credit[c] - cap; credit[c] = cap; }
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
    if (ok && cls !== 'don' && this.curI) {
      const I = this.curI, sent = this.arm.world.attackTroopsTmp;
      I.cmds++; I.sent += sent; I.sentBy[cls] += sent; I.okBy[cls]++;
      const Iq = I.byStyle[s.q5 ?? 2];
      Iq.sent += sent; Iq.cmds++;
    }
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

  // 出手落地以后：记相邻指令间隔（验收连点占比用），并按本阶段的连点概率决定下个回合要不要再点一次
  afterOk(s, cls, t, ph) {
    if (s.lastT >= 0) { this.gapN++; if (t - s.lastT <= 7) this.gap7++; }
    s.lastT = t;
    if (cls !== 4 && hashU(this.seed, s.p, t, 15) < ph.follow[s.q5]) { s.followT = t + 7; s.followCls = cls; }
  }

  // O1 的补刀：身边有地 ≥ 30、兵密度 < 35、兵不到自己一半的敌方真人 → 一条大比例指令收掉。返回是否出了手。
  finisher(s, t) {
    const w = this.arm.world, p = s.p, B = w.bal[p];
    let best = -1;
    for (const q of contacts(w, p).keys()) {
      if (q === NEUTRAL || !w.alive[q] || w.isBot(q) || !w.isEnemy(p, q)) continue;
      const tB = w.bal[q], tT = w.terr[q];
      if (tT < 30 || tB / tT >= 35 || B < 2 * tB) continue;
      if (best < 0 || w.terr[q] > w.terr[best]) best = q;
    }
    if (best < 0) return false;
    const need = Math.ceil(1.5 * (w.bal[best] + 2 * w.terr[best]) * 1024 / B);
    s.lastFinish = t;
    this.log.finish++;
    return this.attackHuman(s, best, Math.max(307, Math.min(1023, need)), t, 'finish');
  }

  // 让席位 s 出一条 cls 类的指令（0 无主地 / 1 内置 AI 与空壳 / 2 真人 / 3 船 / 4 捐款）。返回是否落地（捐款：是否下达）。
  perform(s, cls, t, ph) {
    const w = this.arm.world, p = s.p, sd = this.seed;
    const B = w.bal[p], T = w.terr[p], D = B / Math.max(1, T);
    const adj = contacts(w, p);
    this.setAvail(s, adj);
    const bots = [], hums = [];
    for (const [q, n] of adj) {
      if (q === NEUTRAL || !w.alive[q] || !w.isEnemy(p, q)) continue;
      if (w.isBot(q)) bots.push([q, n]); else hums.push([q, n]);
    }
    const clan = s.clan >= 0 ? this.clans.get(s.clan) : null;
    const isBoss = clan && clan.arche === 'O2' && clan.boss === p;
    const up = this.styleU(s, t);
    s.n++;

    if (cls === 0) {
      if (!adj.has(NEUTRAL)) return false;
      const ok = w.attack(sampleQ(ph.neutral, up), NEUTRAL, p);
      this.note(s, 'neutral', ok);
      return ok;
    }
    if (cls === 1) {
      if (!bots.length) return false;
      // 内置 AI / 空壳：实测真人在身边的 AI 里近乎随手挑（邻居数中位 7 个时，挑中接壤最长的 25%、地最多的 18%、兵最少的 19%），
      // 这里按接壤长度的平方根加权随机挑；千分比就是滑块上那一档（实测出兵 ÷ 对方的兵 中位 4~6、P25 约 2：多数是碾压，
      // 不够吃掉的那两成也照打，不按对方的兵去调滑块）
      let tw = 0;
      for (const [, n] of bots) tw += Math.sqrt(n);
      let ub = hashU(sd, p, t, 9) * tw, q = bots[bots.length - 1][0];
      for (const [o, n] of bots) { ub -= Math.sqrt(n); if (ub < 0) { q = o; break; } }
      const tB = w.bal[q], tT = w.terr[q], pctA = sampleQ(ph.ai, up);
      const okA = w.attack(pctA, q, p);
      this.note(s, 'ai', okA);
      // 打 AI 的明细（验收用，与 human_profile.mjs 的 ai 行同口径）：出兵 ÷ 对方的兵、自己的兵 ÷ 对方的兵、对方的地和密度
      if (okA && this.aiRows.length < 60000) this.aiRows.push([this.phaseIdx(t), pctA, tB > 0 ? w.attackTroopsTmp / tB : -1, tB > 0 ? B / tB : -1, tT, tT > 0 ? tB / tT : 0, bots.length]);
      return okA;
    }
    if (cls === 2) return hums.length ? !!this.fightHuman(s, t, ph, hums, B, D, up, clan, isBoss) : false;
    if (cls === 3) return w.boatsAllowed(p) ? !!this.sendBoat(s, t, ph, B, up) : false;
    return !!this.give(s, t, ph, B, up, clan, isBoss);
  }

  fightHuman(s, t, ph, hums, B, D, up, clan, isBoss) {
    const w = this.arm.world, p = s.p, sd = this.seed;
    // 还手：有人正在打我 → 按实测概率回手（我的兵 ≥ 对方 2 倍 46%，否则 22%），回手打出兵最多的那个
    let atk = -1, atkTroops = 0;
    for (const [q] of hums) { const a = w.attackTroopsOn(q, p); if (a > atkTroops) { atkTroops = a; atk = q; } }
    if (atk >= 0 && hashU(sd, p, t, 4) < (B >= 2 * w.bal[atk] ? 0.46 : 0.22)) {
      return this.attackHuman(s, atk, s.arche === 'O4' && B >= 1.3 * w.bal[atk] ? hashInt(921, 1023, sd, p, t, 5) : s.arche === 'G' || t < 1530 ? humanPct(ph, up, hashU(sd, p, t, 11), B, w.bal[atk]) : s.tier, t, 'back');
    }
    if (s.full && t >= 3210 && D < 60) return false;     // 满仓型：没攒够不主动打真人

    // 集火（O6）/ 大号（O2）优先打战队选定的对象
    if (clan && clan.arche === 'O6' && clan.focus >= 0 && hums.some(([q]) => q === clan.focus)) {
      return this.attackHuman(s, clan.focus, s.tier, t, 'focus');
    }
    if (s.arche === 'O4') {
      let q = -1;
      for (const [o] of hums) if (B >= 1.3 * w.bal[o] && (q < 0 || w.bal[o] < w.bal[q])) q = o;
      return q >= 0 ? this.attackHuman(s, q, hashInt(921, 1023, sd, p, t, 5), t, 'allin') : false;
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
      return q >= 0 ? this.attackHuman(s, q, s.tier, t, 'press') : false;
    }
    // 通用（G、O1 平时、O5 在陆上）：实测真人在身边的敌方真人里 45%~76% 挑兵最少的那个（邻居数中位 3 个，随手挑是 1/3），
    // 接壤长短几乎不看；这里 2/3 的时候打兵最少的，其余随手挑。千分比按实测分布抽。
    let best = -1;
    if (hashU(sd, p, t, 7) < 0.67) { for (const [o] of hums) if (best < 0 || w.bal[o] < w.bal[best]) best = o; }
    else best = hums[hashInt(0, hums.length - 1, sd, p, t, 10)][0];
    return best >= 0 ? this.attackHuman(s, best, humanPct(ph, up, hashU(sd, p, t, 11), B, w.bal[best]), t, 'plain') : false;
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
    if (best < 0) return false;
    const coast = w.coast[best];
    const tile = coast[hashInt(0, coast.length - 1, sd, p, t, 60)];
    let pct = sampleQ(ph.boat, up);
    if (hunter) pct = Math.max(pct, Math.min(614, Math.ceil(0.5 * w.bal[best] * 1024 / B)));   // 大登陆：不少于对方兵的一半，封顶 600‰
    const tB = w.bal[best], tT = w.terr[best];
    const ok = w.boatTo(pct, tile, p);
    const onSq = this.squad.has(best);
    this.note(s, 'boat', ok, onSq ? { t, p, q: best, arche: s.arche, kind: 'boat', pct, sent: ok ? w.attackTroopsTmp : 0, B, tB, tD: tT > 0 ? tB / tT : 0, D: w.terr[p] > 0 ? B / w.terr[p] : 0, back: 0 } : null);
    return ok;
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
    if (q < 0) return false;
    const ok = w.donate(pct, q, p);
    this.note(s, 'don', ok);
    if (ok) { this.log.donOk++; if (pct >= 921) this.log.donBig++; }
    return true;
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
      droppedCredit: this.dropped.map((x) => +x.toFixed(1)),
      burst7: this.gapN ? +(this.gap7 / this.gapN).toFixed(3) : null,
      aiAttacks: this.prof.phases.map((P, i) => {
        const rows = this.aiRows.filter((r) => r[0] === i);
        if (rows.length < 5) return null;
        const q3 = (k, d) => { const a = rows.map((r) => r[k]).filter((x) => x >= 0).sort((x, y) => x - y); return a.length ? [0.25, 0.5, 0.75].map((f) => +a[Math.min(a.length - 1, Math.floor(f * a.length))].toFixed(d)) : null; };
        return { t0: P.t0, n: rows.length, pct: q3(1, 0), sendRatio: q3(2, 2), balRatio: q3(3, 2), tT: q3(4, 0), tD: q3(5, 1), nAdj: q3(6, 0) };
      }),
      intensity: this.intensity.map((I) => ({
        t0: I.t0, cmds: I.cmds, ratePerAlive100: I.aliveTicks ? +(100 * I.cmds / I.aliveTicks).toFixed(3) : null, spendPer100: I.balTicks ? +(100 * I.sent / I.balTicks).toFixed(4) : null, sentPerCmd: I.cmds ? Math.round(I.sent / I.cmds) : null,
        spendBy: Object.fromEntries(Object.keys(I.sentBy).map((k) => [k, I.balTicks ? +(100 * I.sentBy[k] / I.balTicks).toFixed(4) : null])),
        okRateBy: Object.fromEntries(Object.keys(I.okBy).map((k) => [k, I.aliveTicks ? +(100 * I.okBy[k] / I.aliveTicks).toFixed(3) : null])),
        sent: I.sent, sentBy: I.sentBy,
        byStyle: I.byStyle.map((q) => ({ rate: q.alive ? +(100 * q.cmds / q.alive).toFixed(2) : null, spend: q.bal ? +(100 * q.sent / q.bal).toFixed(3) : null, balShare: I.balTicks ? +(q.bal / I.balTicks).toFixed(3) : null })),
      })),
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
