// arm.mjs — 一条臂：一个世界 + 一组我方席位（策略实例、页面替身）+ 指令通道 + 其余玩家（录像重放或对手原型）+ 账本。
import { Seat } from './sandbox.mjs';
import { Channel } from './channel.mjs';
import { Metrics } from './metrics.mjs';
import { execRecorded, contacts, NEUTRAL, iV } from './match.mjs';
import { hashU, hashInt } from './util.mjs';

const TAKEOVER_HOOKS = ['onTakeover', 'resetInflight', 'clearInflight', 'resetLedger'];

export class Arm {
  // cfg：{ name, world, strat, params, seats:[{p, slot}], profile, chanOpts, opts, history }
  constructor(cfg) {
    this.name = cfg.name;
    this.world = cfg.world;
    this.H = cfg.world.humans;
    this.opts = { fallback: 'cheapest', ourLeaves: 'replay', donateSubmit: 'always', keepLogs: false, aoPct: null, react: [], reactSeed: 1, inflightGuard: 'auto', takeoverHooks: TAKEOVER_HOOKS, ...(cfg.opts || {}) };
    // 桥接层的在途保护：auto = 策略文件自带补丁就按补丁（c110：8 拍且 450 ms），没有就不设；数字 = 固定拍数
    const ig = this.opts.inflightGuard;
    this.guard = ig === 'auto' || ig === undefined ? (cfg.strat.guard || null) : (+ig > 0 ? { ticks: +ig, ms: Infinity } : null);
    this.profile = cfg.profile;
    this.strat = cfg.strat;
    this.quit = new Set();
    for (let p = 0; p < this.H; p++) if (this.world.state[p] === 2) this.quit.add(p);
    this.chan = new Channel(this, cfg.profile, cfg.chanOpts || {});
    this.squad = cfg.seats.map((s) => s.p);
    this.squadSet = new Set(this.squad);
    this.metrics = new Metrics(this, this.squad);
    this.viewWrites = new Set();
    this.seats = new Map();
    this.world.teamCacheGet && this.world.teamGame && this.world.teamCacheGet();
    this.world.enableAccounting();
    for (const s of cfg.seats) this.seats.set(s.p, new Seat(this, s.p, s.slot, cfg.strat, cfg.params));
    this.seatList = [...this.seats.values()].sort((a, b) => a.p - b.p);
    this.stepper = null;
    this.actors = cfg.actors || null;
    this.history = cfg.history || null;   // 历史臂的世界（反应补丁的「变薄」触发要对照它）
    this.liveMode = false;
    this.shadowIssued = 0;
    this.other = { atk: 0, asRecorded: 0, rerouted: 0, dropped: 0, void: 0, ok: 0, boats: 0, boatsOk: 0, dons: 0, donsOk: 0 };
    this.reactQ = [];
    this.reactStat = { first: 0, thin: 0, fired: 0, ok: 0 };
    this.sampleEvery = cfg.sampleEvery || 30;
  }

  onShadow() { this.shadowIssued++; }
  onIssue(seat, cmd) { this.metrics.onIssue(cmd); }
  onDrop(seat, cmd, why) { this.metrics.onDrop(cmd, why); }

  // 一条我方指令到了执行的那一刻：交给引擎，按当时的局面校验、计价
  execOur(seat, cmd) {
    const w = this.world, p = seat.p;
    const res = { ok: false, rec: false, sent: 0, fee: 0, why: '', to: cmd.to, B0: w.bal[p] };
    const B = w.bal[p];
    switch (cmd.k) {
      case 'atk': {
        if (!w.canAct(p)) { res.why = 'cant'; break; }
        let tgt = cmd.to;
        if (tgt < NEUTRAL && w.alive[tgt] === 0) tgt = NEUTRAL;
        const firstStrike = tgt < this.H && !this.squadSet.has(tgt) && !w.hasAttack(tgt, p);
        const n0 = w.landAttacks[p];
        const ok = w.attack(cmd.pct, cmd.to, p);
        res.rec = w.landAttacks[p] !== n0;
        res.ok = ok; res.to = tgt;
        if (ok) {
          res.sent = w.attackTroopsTmp; res.fee = w.attackFeeTmp;
          if (firstStrike && this.opts.react.includes('first')) this.reactFirst(p, tgt, B);
        } else res.why = res.rec ? 'nofront' : 'invalid';
        break;
      }
      case 'boat': {
        const ok = w.boat(cmd.pct, cmd.water, cmd.dir, p);
        res.ok = res.rec = ok;
        if (ok) { res.sent = w.attackTroopsTmp; res.fee = w.attackFeeTmp; } else res.why = 'invalid';
        break;
      }
      case 'don': {
        const q = cmd.to;
        if (!w.teamGame || !w.canAct(p) || q === p || q >= NEUTRAL || !w.alive[q] || !w.isTeammate(p, q)) { res.why = 'target'; break; }
        const fee = iV(64 * B, 1024);
        let v = Math.min(iV(B * (cmd.pct + 1), 1024), B - fee);
        v = w.receiverRoom(q, v);
        if (v < 1) { res.why = 'room'; break; }
        if (!w.canReceive(q, v)) { res.why = 'quota'; break; }
        const ok = w.donate(cmd.pct, q, p);
        res.ok = res.rec = ok;
        if (ok) { res.sent = v; res.fee = fee; } else res.why = 'other';
        break;
      }
      case 'ret': res.ok = res.rec = w.retreat(cmd.to, p); break;
      case 'chase': res.ok = res.rec = w.chase(cmd.a, cmd.b, p); if (res.ok) { res.sent = w.attackTroopsTmp; res.fee = w.attackFeeTmp; } break;
      case 'recall': res.ok = res.rec = w.recall(cmd.b, p); break;
      case 'leave': {
        if (w.alive[p] && w.state[p] !== 2 && !w.spawnPhase) { w.leave(p); this.quit.add(p); seat.left = true; res.ok = res.rec = true; }
        break;
      }
      default: res.why = 'unknown';
    }
    this.metrics.onExec(cmd, res, w.t);
    return res;
  }

  // ---- 其余玩家：录像重放（接管后带兜底）---------------------------------------------------------
  attachReplay(stepper) {
    this.stepper = stepper;
    stepper.exec = (c) => this.execOther(c);
  }

  execOther(c) {
    const w = this.world, p = c.player;
    if (!this.liveMode) {
      const r = execRecorded(w, c);
      if ((c.id === 8 || c.id === 9) && p < this.H) this.quit.add(p);
      return r;
    }
    if (this.squadSet.has(p)) {
      // 接管之后我方席位的录像指令由策略替代；录像里的离场（页面掉线 / 被移出）按开关照放
      if ((c.id === 8 || c.id === 9) && this.opts.ourLeaves === 'replay') {
        const r = execRecorded(w, c);
        this.quit.add(p);
        const s = this.seats.get(p);
        if (s) s.left = true;
        return r;
      }
      return { ok: false, rec: false };
    }
    if (c.id === 8 || c.id === 9) { const r = execRecorded(w, c); if (p < this.H) this.quit.add(p); return r; }
    if (c.id === 1) {
      const o = this.other;
      o.atk++;
      if (!w.canAct(p)) { o.dropped++; return { ok: false, rec: false }; }
      const tgt = Math.min(c.dZ, NEUTRAL);
      let use = tgt;
      if (this.opts.fallback !== 'engine') {
        let valid;
        if (tgt < NEUTRAL && w.alive[tgt] && w.hasAttack(p, tgt)) valid = true;
        else {
          const adj = contacts(w, p);
          valid = tgt === NEUTRAL ? adj.has(NEUTRAL) : (w.alive[tgt] !== 0 && adj.has(tgt) && w.isEnemy(p, tgt));
          if (!valid) {
            if (this.opts.fallback === 'drop') { o.dropped++; return { ok: false, rec: false }; }
            use = cheapestSoft(w, p, adj);
            if (use < 0) { o.dropped++; return { ok: false, rec: false }; }
            o.rerouted++;
          }
        }
        if (valid) o.asRecorded++;
      }
      const ok = w.attack(c.dX, use, p);
      if (ok) o.ok++; else o.void++;
      return { ok, rec: true };
    }
    const r = execRecorded(w, c);
    if (c.id === 3) { this.other.boats++; if (r.ok) this.other.boatsOk++; }
    if (c.id === 2) { this.other.dons++; if (r.ok) this.other.donsOk++; }
    return r;
  }

  // ---- 反应补丁 ---------------------------------------------------------------------------------
  // first：我方先手打了一个真人 h（h 当时没在打这个席位）→ h 按实测概率回一个脉冲（h 的兵 ≥ 我方 2 倍：46%，否则 22%；出兵档 126/1024）
  reactFirst(s, h, Bs) {
    const w = this.world;
    if (w.state[h] === 2 || !w.alive[h]) return;
    this.reactStat.first++;
    const strong = w.bal[h] >= 2 * Bs;
    const u = hashU(this.opts.reactSeed, h, s, Math.floor(w.t / 50), 11);
    if (u < (strong ? 0.46 : 0.22)) this.reactQ.push({ t: 7 * Math.ceil((w.t + hashInt(14, 35, this.opts.reactSeed, h, s, w.t, 12)) / 7), h, s, pct: 126 });
  }

  // thin：我方席位的兵比历史同拍少了一半以上，身边有兵 ≥ 它 2 倍、还没在打它的真人 → 每 100 拍按 46% 开火一次
  reactThin() {
    const w = this.world, hist = this.history;
    if (!hist) return;
    for (const s of this.squad) {
      if (!w.alive[s] || w.state[s] === 2 || !hist.alive[s]) continue;
      if (!(w.bal[s] < 0.5 * hist.bal[s])) continue;
      const adj = contacts(w, s);
      for (const h of adj.keys()) {
        if (h >= this.H || this.squadSet.has(h) || w.state[h] === 2 || !w.isEnemy(h, s) || w.hasAttack(h, s)) continue;
        if (!(w.bal[h] >= 2 * w.bal[s])) continue;
        this.reactStat.thin++;
        if (hashU(this.opts.reactSeed, h, s, Math.floor(w.t / 100), 13) < 0.46) this.reactQ.push({ t: 7 * Math.ceil((w.t + hashInt(7, 28, this.opts.reactSeed, h, s, w.t, 14)) / 7), h, s, pct: 126 });
      }
    }
  }

  runReactions(t) {
    if (!this.reactQ.length) return;
    const rest = [];
    for (const r of this.reactQ) {
      if (r.t > t) { rest.push(r); continue; }
      this.reactStat.fired++;
      if (this.world.attack(r.pct, r.s, r.h)) this.reactStat.ok++;
    }
    this.reactQ = rest;
  }

  // ---- 接管 / 逐拍 -------------------------------------------------------------------------------
  takeover() {
    this.liveMode = true;
    for (const s of this.seatList) {
      s.live = true; s.sentAt = -1; s.shadowIssued = s.issued; s.issued = 0; s.refused = 0;
      for (const h of this.opts.takeoverHooks) {
        if (typeof s.pol[h] === 'function') { try { s.pol[h](s.view); s.hooked = h; } catch (err) { s.errors++; if (!s.firstError) s.firstError = `takeover ${h}: ${err.message}`; } }
      }
    }
    this.metrics.begin();
  }

  tickOnce() {
    const w = this.world, t = w.t, prof = this.profile, guard = this.guard, pageEnd = prof.pageEnd || null;
    // ① 各席位的页面在本机第 t 拍的局面上决策
    for (const s of this.seatList) {
      const p = s.p;
      if (!w.alive[p] || w.state[p] === 2) continue;
      if (pageEnd && t > (pageEnd.get(p) ?? Infinity)) { s.pageDead = true; continue; }
      const clock = 56 * prof.serverTick(p, t);
      if (guard && s.sentAt >= 0 && t - s.sentAt < guard.ticks && clock - s.sentClock < guard.ms) { s.guarded++; continue; }
      s.act(clock);
    }
    // ② 这一拍到点的指令：其余玩家（录像 / 对手原型）、反应补丁、我方通道
    if (this.stepper) this.stepper.step();
    if (this.actors) for (const a of this.actors) a.act(this, t);
    if (this.liveMode && this.opts.react.length) {
      if (this.opts.react.includes('thin') && t % 100 === 50) this.reactThin();
      if (t % 7 === 0) this.runReactions(t);
    }
    if (!this.chan.instant && t % 7 === 0) this.chan.settle(t);
    // ③ 引擎走一拍
    w.tick();
    if (this.liveMode && w.t % this.sampleEvery === 0) this.metrics.sample();
  }

  finish(natural, extra = {}) {
    const w = this.world;
    this.chan.flushPending();
    const errs = this.seatList.filter((s) => s.errors).map((s) => ({ p: s.p, n: s.errors, first: s.firstError }));
    const tags = {};
    for (const s of this.seatList) for (const [k, v] of s.logTags) tags[k] = (tags[k] || 0) + v;
    return this.metrics.finalize(natural, {
      arm: this.name, strategy: this.strat.name, channel: this.profile.name,
      acts: this.seatList.reduce((a, s) => a + s.acts, 0),
      stratIssued: this.seatList.reduce((a, s) => a + s.issued, 0),
      secondRefused: this.seatList.reduce((a, s) => a + s.refused, 0),
      guard: this.guard ? `${this.guard.ticks} 拍` + (Number.isFinite(this.guard.ms) ? ` 且 ${this.guard.ms} ms` : '') : '无',
      guarded: this.seatList.reduce((a, s) => a + s.guarded, 0),
      pageDead: this.seatList.filter((s) => s.pageDead).length,
      shadowIssued: this.shadowIssued,
      stratErrors: errs,
      logTags: tags,
      others: this.other,
      react: this.reactStat,
      viewWrites: [...this.viewWrites].sort(),
      hooks: [...new Set(this.seatList.map((s) => s.hooked).filter(Boolean))],
      over: !!w.over, winnerTeam: w.over ? w.winnerTeam : null,
      ...extra,
    });
  }
}

// 兜底目标：身边有无主地就打无主地；否则打身边兵最薄（兵 / 地）的内置 AI 或离场空壳；都没有返回 −1
export function cheapestSoft(w, p, adj) {
  if (adj.has(NEUTRAL)) return NEUTRAL;
  let best = -1, bd = Infinity;
  for (const o of adj.keys()) {
    if (o === NEUTRAL || !w.alive[o] || !w.isBot(o) || !w.isEnemy(p, o)) continue;
    const d = w.bal[o] / Math.max(1, w.terr[o]);
    if (d < bd) { bd = d; best = o; }
  }
  return best;
}
