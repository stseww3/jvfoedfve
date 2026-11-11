// match_truth.mjs — 在逐拍重演（sim_replay.mjs，已与日志 [HL-TICK] 逐条全等校验）上加记账钩子，导出一局的「真账」JSON。
// 记的东西（全部来自重演出来的引擎状态，不是日志估算）：
//   players   每个真人：队伍、是否我方号、出生点、阵亡拍/离场拍、峰值地、进攻/船/捐兵笔数与兵量、从中立/机器人/真人手里拿的地、被拿走的地
//   T30       每 30 拍：各队（0=机器人/无队，1..T=真人队）总地、总兵、存活真人数、在场真人数（没离场）；我方号合计
//   S10       每 10 拍、每个我方号：地、兵、在外进攻兵、正在打它的真人兵/机器人兵、船数、已用捐兵配额
//   C30       每 30 拍、每个我方号：边界接触像素按对象分类（中立地 / 在场敌方真人 / 已离场敌方真人 / 机器人 / 我方号 / 路人队友）与前两名敌邻
//   F30       每 30 拍、每个我方号：兵力收支累计（利息+地租 / 打中立 / 打机器人 / 打真人 / 出船 / 捐出 / 收到捐兵 / 进攻兵退回 / 被打掉 / 开火补兵 / 船靠岸 / 其它），差分即任意窗口的收支分解
//   events    与我方号有关的全部指令（我方发的；别人打我方、捐给我方的），带执行前后的兵与地
//   pairs     与我方号有关的两两战账：谁向谁投了多少兵、拿了多少地、打掉对方多少兵；pairsW 为 100 拍窗口版
//   teamFlow  每 300 拍：哪队从哪队（或中立）手里拿了多少地
//   dispatch  日志里每条 [HL-DISPATCH] 与录像对账：录像里是否有对应的已执行捐兵；没有的话，在日志拍 +0/+7/+14/+21 拍处用引擎规则试算会不会被拒以及原因
// 用法：node match_truth.mjs <matchId> [--out /tmp/c136-r05/truth]   → 写 <out>/<matchId>.json，并打印一行摘要
import fs from 'node:fs';
import path from 'node:path';
import { simulate, parseTicks, botIds, bare, Game, NEUTRAL, P_INNER, iV, DATA, TEAM_COLOR_NAME } from './sim_replay.mjs';

const T_LAND = 1;
const CAT = ['eco', 'atkNeutral', 'atkBot', 'atkHuman', 'boat', 'donOut', 'donIn', 'ret', 'dmg', 'topup', 'boatLand', 'other'];
const C = Object.fromEntries(CAT.map((k, i) => [k, i]));
const NC = CAT.length;

const REC = { on: false };
const P = Game.prototype;
const wrap = (name, f) => { const o = P[name]; P[name] = f(o); };
const addFlow = (p, cat, v) => { if (REC.on && p < REC.H) REC.flow[p * NC + cat] += v; };
const pairGet = (a, b) => { const k = a * 1024 + b; let r = REC.pair.get(k); if (!r) { r = [0, 0, 0, 0, 0, 0]; REC.pair.set(k, r); } return r; };
const pairWGet = (a, b) => { const k = REC.w100 * 1048576 + a * 1024 + b; let r = REC.pairW.get(k); if (!r) { r = [0, 0, 0]; REC.pairW.set(k, r); } return r; };
const tracked = (a, b) => REC.isSquad[a] || (b < 512 && REC.isSquad[b]);

wrap('economyTick', (o) => function () {
  if (!REC.on) return o.call(this);
  if (this.t % 10 === 9) {
    // 软上限罚息：存兵超过 100×地 后利率按超出比例打折（到 150×地 归零）。这里把「如果存兵正好在软上限以内本该拿到的利息」与实际利息之差累计下来。
    for (const p of REC.squadList) {
      if (!this.alive[p] || this.state[p] === 2) continue;
      const b = this.bal[p], cap = this.softCap(p);
      if (b <= cap) continue;
      const actual = Math.max(iV(this.interestRate(p) * b, 1e4), 1);
      this.bal[p] = cap; const r0 = this.interestRate(p); this.bal[p] = b;
      const room = Math.max(this.terr[p] * 150 - b, 0);
      REC.capLoss[p] += Math.max(iV(r0 * b, 1e4), 1) - Math.min(actual, room);
    }
  }
  const c = REC.ctx; REC.ctx = C.eco; o.call(this); REC.ctx = c;
});
wrap('addBalance', (o) => function (p, v) { if (!REC.on) return o.call(this, p, v); const b = this.bal[p]; const r = o.call(this, p, v); addFlow(p, REC.ctx, this.bal[p] - b); return r; });
wrap('takeBalance', (o) => function (p, v) { if (!REC.on) return o.call(this, p, v); const b = this.bal[p]; const r = o.call(this, p, v); addFlow(p, C.topup, this.bal[p] - b); return r; });
wrap('endAttack', (o) => function (p, a, troops) {
  if (!REC.on) return o.call(this, p, a, troops);
  const tgt = this.atkTarget[this.slotBase(p) + a];
  const c = REC.ctx; REC.ctx = C.ret; const b = this.bal[p]; o.call(this, p, a, troops); REC.ctx = c;
  if (tracked(p, tgt)) pairGet(p, tgt)[5] += this.bal[p] - b;
});
wrap('cancelAttack', (o) => function (p, target) { if (!REC.on) return o.call(this, p, target); const c = REC.ctx; REC.ctx = C.ret; o.call(this, p, target); REC.ctx = c; });
wrap('landAt', (o) => function (p, troops, c2, at) { if (!REC.on) return o.call(this, p, troops, c2, at); const c = REC.ctx; REC.ctx = C.boatLand; REC.fromBoat = 1; o.call(this, p, troops, c2, at); REC.fromBoat = 0; REC.ctx = c; });
wrap('damage', (o) => function (p, target, dmg, counter) {
  if (!REC.on) return o.call(this, p, target, dmg, counter);
  const b = this.bal[target];
  o.call(this, p, target, dmg, counter);
  const lost = b - this.bal[target];
  addFlow(target, C.dmg, -lost);
  if (tracked(p, target)) { const r = pairGet(p, target); r[3] += lost; r[4] += counter > 0 ? Math.min(dmg, counter) : 0; pairWGet(p, target)[2] += lost; }
});
wrap('addAttack', (o) => function (p, troops, target) {
  if (REC.on && !REC.redirect) {
    const cls = target >= 512 ? 0 : (target >= REC.H ? 1 : 2);
    REC.sent[p * 3 + cls] += troops;
    if (tracked(p, target)) { const r = pairGet(p, target); r[0] += troops; r[1]++; pairWGet(p, target)[0] += troops; }
    if (REC.fromBoat && (REC.isSquad[p] || (target < 512 && REC.isSquad[target]))) REC.events.push({ t: this.t, type: 'boat-land', p, q: target, troops });
  }
  return o.call(this, p, troops, target);
});
wrap('redirectAttackToNeutral', (o) => function (p, target) { if (!REC.on) return o.call(this, p, target); REC.redirect = 1; o.call(this, p, target); REC.redirect = 0; });
wrap('expandAttack', (o) => function (p, a) {
  if (!REC.on) return o.call(this, p, a);
  const tgt = this.atkTarget[this.slotBase(p) + a];
  const L0 = this.terr[p];
  o.call(this, p, a);
  const got = this.terr[p] - L0;
  if (got > 0) {
    const cls = tgt >= 512 ? 0 : (tgt >= REC.H ? 1 : 2);
    REC.tiles[p * 3 + cls] += got;
    if (tgt < 512) REC.lost[tgt] += got;
    const ta = REC.teams[p], tb = tgt >= 512 ? REC.nT + 1 : REC.teams[tgt];
    const k = REC.w300 * 10000 + ta * 100 + tb;
    REC.teamFlow.set(k, (REC.teamFlow.get(k) || 0) + got);
    if (tracked(p, tgt)) { pairGet(p, tgt)[2] += got; pairWGet(p, tgt)[1] += got; }
    if (p < REC.H) { const kk = p * 1024 + (tgt >= 512 ? 512 : tgt >= REC.H ? 600 : tgt); const w = Math.floor(this.t / 600); const k2 = w * 1048576 + kk; REC.pairAll.set(k2, (REC.pairAll.get(k2) || 0) + got); }
  }
});

function parseDispatch(matchId) {
  const out = [];
  const re = /\[([^\]]+)\] \[HL-DISPATCH\] t=(\d+) (\w+) pct=(\d+)\/1024 -> ally=(\d+)\((.*?)\) boxedIn=(\w+) myBal=(\d+) dMe=([\d.]+) dAlly=([\d.]+)/;
  for (const line of fs.readFileSync(path.join(DATA, 'bundles', matchId, 'in_game.log'), 'utf8').split('\n')) {
    const m = re.exec(line);
    if (m) out.push({ bot: m[1], t: +m[2], kind: m[3], pct: +m[4], q: +m[5], qName: m[6], boxed: m[7] === 'true', myBal: +m[8], dMe: +m[9], dAlly: +m[10] });
  }
  return out;
}

// 同房间的另一支编队（card.sameMatchPeer）：按 identity-map-discovery.csv 的 me 列找出它在本盘录像里的玩家号
export function peerBots(matchId, names, H) {
  try {
    const card = JSON.parse(fs.readFileSync(path.join(DATA, 'bundles', matchId, 'card.json'), 'utf8'));
    const peerId = card.sameMatchPeer && card.sameMatchPeer.peerMatchId;
    if (!peerId) return { matchId: null, cohort: null, bots: [] };
    const lines = fs.readFileSync(path.join(DATA, 'src/tools/identity-map-discovery.csv'), 'utf8').split('\n');
    const hdr = lines[0].split(',');
    const ci = (k) => hdr.indexOf(k);
    const bots = [];
    for (const ln of lines.slice(1)) {
      const c = ln.split(',');
      if (c[ci('matchId')] !== peerId) continue;
      const me = +c[ci('me')];
      if (!(me >= 0 && me < H)) continue;
      const chain = (c[ci('nameChain')] || '').split('→');
      const nmReplay = String(names[me] || '');
      bots.push({ p: me, name: nmReplay, logTeam: c[ci('team')] ? +c[ci('team')] : null, event: c[ci('event')] || '', resultTick: c[ci('resultTick')] ? +c[ci('resultTick')] : null, nameOk: chain.some((x) => x && nmReplay.includes(x)) });
    }
    return { matchId: peerId, cohort: card.sameMatchPeer.peerCohort, bots };
  } catch (e) { return { matchId: null, cohort: null, bots: [], err: e.message }; }
}

export function squadIds(matchId, names, H) {
  // 我方号：日志前缀（号名）在录像名单里「去标签后全等且唯一」的那些；B 系前缀会轮换，另用 [HL-GAME-INIT] 的 me= 兜底（me 处名字需与前缀相等才算）。
  const log = fs.readFileSync(path.join(DATA, 'bundles', matchId, 'in_game.log'), 'utf8');
  const prefixes = new Set();
  const me = new Map();
  for (const line of log.split('\n')) {
    const m = /^\d+\t\[([^\]]+)\] \[HL-/.exec(line);
    if (!m) continue;
    prefixes.add(m[1]);
    const g = /\[HL-GAME-INIT\].* me=(\d+)/.exec(line);
    if (g) me.set(m[1], +g[1]);
  }
  const ids = botIds(names, H, [...prefixes]);
  const out = new Map();
  for (const [b, p] of ids) if (p >= 0) out.set(p, b);
  return { squad: out, prefixes: [...prefixes], me };
}

export function truth(matchId) {
  const ticks = parseTicks(matchId);
  const disp = parseDispatch(matchId);
  const dispByT = new Map();
  let sq = null, S10 = {}, C30 = {}, F30 = {}, T30 = null, ctx0 = null, HS = null;
  const players = [];
  const preEvents = [];
  const LAGS = [0, 7, 14, 21];
  const R = simulate(matchId, {
    onStart: (g, ctx) => {
      ctx0 = ctx;
      const H = ctx.H;
      sq = squadIds(matchId, ctx.names, H);
      Object.assign(REC, {
        on: true, g, H, ctx: C.other, fromBoat: 0, redirect: 0, w100: 0, w300: 0, nT: ctx.T ? ctx.T.humanTeams : 0,
        teams: g.teams, isSquad: new Uint8Array(512), flow: new Float64Array(H * NC), sent: new Float64Array(512 * 3), tiles: new Float64Array(512 * 3), lost: new Float64Array(512),
        pair: new Map(), pairW: new Map(), teamFlow: new Map(), events: [], allDon: [], pairAll: new Map(), capLoss: new Float64Array(512), squadList: [...sq.squad.keys()],
      });
      for (const p of sq.squad.keys()) REC.isSquad[p] = 1;
      for (let p = 0; p < H; p++) {
        let sx = -1, sy = -1;
        if (g.alive[p] && g.terr[p] > 0) { sx = (g.x0[p] + g.x1[p]) >> 1; sy = (g.y0[p] + g.y1[p]) >> 1; }
        players.push({ id: p, name: ctx.names[p], team: g.teams[p], squad: REC.isSquad[p] === 1, spawn: [sx, sy], deathT: -1, leftT: -1, peakTerr: 0, peakT: 0, nAtk: 0, nBoat: 0, donOutN: 0, donOutV: 0, donOutFee: 0, donInN: 0, donInV: 0 });
      }
      for (const p of sq.squad.keys()) {
        S10[p] = { t: [], terr: [], bal: [], out: [], inH: [], inB: [], boats: [], quota: [] };
        C30[p] = { t: [], neut: [], eh: [], el: [], bot: [], mateS: [], mateO: [], nEnemy: [], top: [] };
        F30[p] = { t: [], flows: [], capLoss: [] };
      }
      const nT = REC.nT;
      T30 = { t: [], land: [], bal: [], alive: [], active: [], squadLand: [], squadBal: [], squadActive: [], squadAlive: [], cap: [], top: [] };
      HS = { t: [], terr: [], bal: [] };
      for (const e of preEvents) if (REC.isSquad[e.p] || (e.q >= 0 && e.q < 512 && REC.isSquad[e.q])) REC.events.push(e);
      for (const d of disp) {
        const p = [...sq.squad.entries()].find(([, b]) => b === d.bot)?.[0];
        d.p = p ?? -1;
        d.sim = [];
        if (p === undefined) continue;
        for (const lag of LAGS) { const t = d.t + lag; if (!dispByT.has(t)) dispByT.set(t, []); dispByT.get(t).push([d, lag]); }
      }
    },
    onEvent: (e) => {
      // 选点阶段（onStart 之前）就发生的事件（如选点期离线）：先暂存，开局后补记
      if (!ctx0) { preEvents.push(e); return; }
      const g = REC.g, H = REC.H;
      const p = e.p, q = e.q;
      if (p < H) {
        const d = g.bal[p] - e.B0;
        if (e.type === 'attack') { players[p].nAtk++; if (e.ok) addFlow(p, q >= 512 ? C.atkNeutral : (q >= H ? C.atkBot : C.atkHuman), d); } else if (e.type === 'boat') { players[p].nBoat++; if (e.ok) addFlow(p, C.boat, d); } else if (e.type === 'donate' && e.ok) {
          addFlow(p, C.donOut, d);
          // 收款方的入账已由 addBalance 记到 other，这里改记到 donIn
          if (q < H) { REC.flow[q * NC + C.other] -= e.got; REC.flow[q * NC + C.donIn] += e.got; }
          players[p].donOutN++; players[p].donOutV += e.got; players[p].donOutFee += e.fee;
          if (q < H) { players[q].donInN++; players[q].donInV += e.got; }
        } else if (e.type === 'chase' || e.type === 'recall') addFlow(p, C.boat, d);
      }
      if (e.type === 'donate') { e.quotaAfter = q < 512 ? g.donQuota[q] : 0; e.cap = g.donCap; if (e.ok) REC.allDon.push([e.t, p, q, e.got, e.fee]); }
      if (REC.isSquad[p] || (q >= 0 && q < 512 && REC.isSquad[q])) REC.events.push(e);
    },
    onTick: (g, t) => {
      const H = REC.H;
      REC.w100 = Math.floor(t / 100); REC.w300 = Math.floor(t / 300);
      for (let p = 0; p < H; p++) {
        const pl = players[p];
        if (pl.deathT < 0 && g.alive[p] === 0) { pl.deathT = t; if (pl.squad) REC.events.push({ t, type: 'died', p, q: -1 }); }
        if (pl.leftT < 0 && g.state[p] === 2) pl.leftT = t;
        if (g.terr[p] > pl.peakTerr) { pl.peakTerr = g.terr[p]; pl.peakT = t; }
      }
      const L = dispByT.get(t);
      if (L) for (const [d, lag] of L) {
        const p = d.p, q = d.q;
        let reason = 'ok', v = 0, extra = null;
        if (!g.canAct(p)) reason = 'donor-out';
        else if (q >= 512 || g.alive[q] === 0) reason = 'ally-dead';
        else if (!g.isTeammate(p, q)) reason = 'not-teammate';
        else {
          const B = g.bal[p], fee = iV(64 * B, 1024);
          const v0 = Math.min(iV(B * (d.pct + 1), 1024), B - fee);
          const room = g.receiverRoom(q, v0);
          if (room < 1) reason = 'no-room';
          else if (!g.canReceive(q, room)) { reason = 'quota'; extra = { used: g.donQuota[q], cost: g.donationCost(q, room), cap: g.donCap, want: room }; } else v = room;
        }
        d.sim.push({ lag, reason, v, extra, B: g.bal[p], L: g.terr[p], qB: q < 512 ? g.bal[q] : 0, qL: q < 512 ? g.terr[q] : 0 });
      }
      if (t % 10 === 0) {
        for (const p of sq.squad.keys()) {
          if (!g.alive[p]) continue;
          const s = S10[p];
          let inH = 0, inB = 0;
          const atk = g.attackersOf(p);
          for (const a of atk) { const v = g.attackTroopsOn(a, p); if (a < H && g.state[a] !== 2) inH += v; else inB += v; }
          s.t.push(t); s.terr.push(g.terr[p]); s.bal.push(g.bal[p]); s.out.push(g.totalAttackTroops(p)); s.inH.push(inH); s.inB.push(inB); s.boats.push(g.boatCount[p]); s.quota.push(g.donQuota[p]);
        }
      }
      if (t % 30 === 0) {
        const nT = REC.nT;
        const land = new Array(nT + 1).fill(0), bal = new Array(nT + 1).fill(0), alive = new Array(nT + 1).fill(0), active = new Array(nT + 1).fill(0);
        for (let i = 0; i < g.aliveCount; i++) {
          const p = g.aliveList[i], tm = g.teams[p];
          land[tm] += g.terr[p]; bal[tm] += g.bal[p];
          if (p < H) { alive[tm]++; if (g.state[p] !== 2) active[tm]++; } else alive[0]++;
        }
        let sl = 0, sb = 0, sa = 0, sv = 0;
        for (const p of sq.squad.keys()) if (g.alive[p]) { sl += g.terr[p]; sb += g.bal[p]; sv++; if (g.state[p] !== 2) sa++; }
        T30.t.push(t); T30.land.push(land); T30.bal.push(bal); T30.alive.push(alive); T30.active.push(active); T30.squadLand.push(sl); T30.squadBal.push(sb); T30.squadActive.push(sa); T30.squadAlive.push(sv); T30.cap.push(g.donCap);
        { const top = []; for (let i = 0; i < Math.min(6, g.rankCount); i++) { const p = g.rank[i]; if (g.alive[p]) top.push([p, g.terr[p], g.bal[p]]); } T30.top.push(top); }
        if (t % 300 === 0) { HS.t.push(t); HS.terr.push(Array.from(g.terr.subarray(0, H))); HS.bal.push(Array.from(g.bal.subarray(0, H))); }
        const d4 = g.dir4, px = g.px, own = g.own;
        for (const p of sq.squad.keys()) {
          if (!g.alive[p]) continue;
          const f = F30[p]; f.t.push(t); f.flows.push(Array.from(REC.flow.subarray(p * NC, p * NC + NC))); f.capLoss.push(REC.capLoss[p]);
          const c = C30[p];
          let neut = 0, eh = 0, el = 0, bot = 0, mateS = 0, mateO = 0;
          const cnt = new Map();
          const seen = new Set();
          for (const list of [g.border[p], g.front[p]]) {
            if (!list) continue;
            for (let i = list.length - 1; i >= 0; i--) {
              const b = list[i];
              if (!(px[b] >= P_INNER && own[b] === p)) continue;
              for (let k = 0; k < 4; k++) {
                const x = b + d4[k];
                if (seen.has(x)) continue;
                const v = px[x];
                if (v === T_LAND) { seen.add(x); neut++; } else if (v >= P_INNER && own[x] !== p) {
                  seen.add(x);
                  const o = own[x];
                  if (g.teams[o] !== 0 && g.teams[o] === g.teams[p]) { if (REC.isSquad[o]) mateS++; else mateO++; } else if (o >= H) bot++; else { if (g.state[o] === 2) el++; else eh++; cnt.set(o, (cnt.get(o) || 0) + 1); }
                }
              }
            }
          }
          const top = [...cnt.entries()].sort((a, b) => b[1] - a[1]).slice(0, 2);
          c.t.push(t); c.neut.push(neut); c.eh.push(eh); c.el.push(el); c.bot.push(bot); c.mateS.push(mateS); c.mateO.push(mateO); c.nEnemy.push(cnt.size); c.top.push(top);
        }
      }
    },
  });
  REC.on = false;
  const g = R.g, H = R.H;
  for (let p = 0; p < H; p++) {
    const pl = players[p];
    pl.endTerr = g.terr[p]; pl.endBal = g.bal[p]; pl.alive = g.alive[p]; pl.state = g.state[p];
    pl.sentN = REC.sent[p * 3]; pl.sentB = REC.sent[p * 3 + 1]; pl.sentH = REC.sent[p * 3 + 2];
    pl.tilesN = REC.tiles[p * 3]; pl.tilesB = REC.tiles[p * 3 + 1]; pl.tilesH = REC.tiles[p * 3 + 2]; pl.tilesLost = REC.lost[p];
    pl.flows = Array.from(REC.flow.subarray(p * NC, p * NC + NC));
  }
  // 日志调度 ↔ 录像已执行捐兵 一对一配对：按执行时间顺序，每笔已执行捐兵配「同捐出方、同收款方、同 pct、日志拍 ≤ 执行拍、相隔 ≤ 600 拍」里最晚的那条未配日志
  const execs = REC.events.filter((e) => e.type === 'donate' && e.ok && REC.isSquad[e.p]);
  for (const d of disp) d.exec = null;
  for (const e of execs) {
    let best = null;
    for (const d of disp) if (!d.exec && d.p === e.p && d.q === e.q && d.pct === e.pct && d.t <= e.t && e.t - d.t <= 600 && (!best || d.t > best.t)) best = d;
    if (best) best.exec = { t: e.t, got: e.got, fee: e.fee, B0: e.B0, qB0: e.qB0, qL0: e.qL0 };
    e.logT = best ? best.t : -1; e.logKind = best ? best.kind : '';
  }
  const pairs = [...REC.pair.entries()].map(([k, r]) => ({ a: Math.floor(k / 1024), b: k % 1024, sent: r[0], n: r[1], tiles: r[2], balDmg: r[3], ck: r[4], ret: r[5] }));
  const pairsW = [...REC.pairW.entries()].map(([k, r]) => ({ w: Math.floor(k / 1048576), a: Math.floor((k % 1048576) / 1024), b: k % 1024, sent: r[0], tiles: r[1], balDmg: r[2] }));
  const teamFlow = [...REC.teamFlow.entries()].map(([k, v]) => ({ w: Math.floor(k / 10000), from: Math.floor((k % 10000) / 100), to: k % 100, tiles: v })).sort((a, b) => a.w - b.w || b.tiles - a.tiles);
  const nameOf = (p) => (p >= 512 ? '中立' : p >= H ? `机器人#${p}` : ctx0.names[p]);
  return {
    matchId, map: { idx: R.mapIdx, seed: R.mapSeed, W: g.W, H: g.H, land: g.land }, humans: H, humanTeams: R.T ? R.T.humanTeams : 0, teamSizes: R.T ? R.T.counts : [],
    teamColor: R.T ? Array.from({ length: R.T.humanTeams + 1 }, (_, i) => TEAM_COLOR_NAME[R.T.lH[i]]) : [], headerTeams: R.vu.numberTeams,
    ourTeam: sq.squad.size ? g.teams[[...sq.squad.keys()][0]] : 0, squad: [...sq.squad.entries()].map(([p, b]) => ({ p, bot: b, team: g.teams[p] })), logBots: sq.prefixes,
    endTick: R.endTick, overAt: R.overAt, stats: R.stats, cats: CAT, tickLines: ticks.length,
    players, T30, HS, S10, C30, F30, events: REC.events, allDon: REC.allDon,
    pairAll: [...REC.pairAll.entries()].map(([k, v]) => [Math.floor(k / 1048576), Math.floor((k % 1048576) / 1024), k % 1024, v]), pairs, pairsW, teamFlow, dispatch: disp,
    peer: peerBots(matchId, R.names, H),
    botNames: Object.fromEntries(pairs.flatMap((r) => [r.a, r.b]).filter((x) => x < 512).map((x) => [x, nameOf(x)])),
  };
}

if (import.meta.url === `file://${process.argv[1]}`) {
  const args = process.argv.slice(2);
  const outDir = args.includes('--out') ? args[args.indexOf('--out') + 1] : '/tmp/c136-r05/truth';
  fs.mkdirSync(outDir, { recursive: true });
  for (const id of args.filter((a) => /^[A-Z]\d{3}$/.test(a))) {
    const t0 = Date.now();
    const J = truth(id);
    fs.writeFileSync(path.join(outDir, `${id}.json`), JSON.stringify(J));
    const ex = J.dispatch.filter((d) => d.exec).length;
    console.log(`${id} 真人=${J.humans} 真人队=${J.humanTeams}(${J.teamSizes.join('/')}) 我方队=${J.ourTeam} 我方号在本盘=${J.squad.length} 重演到=${J.endTick} 事件=${J.events.length} 调度日志=${J.dispatch.length} 已执行=${ex} 用时=${Date.now() - t0}ms → ${outDir}/${id}.json`);
  }
}
