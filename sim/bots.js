// Bot AI: decision timers, land attack targeting, boat and mountain attacks,
// boat interception, neutral-land scanner and endgame speed-up.
import { Game, MAX_PLAYERS, NEUTRAL, P_INNER, P_BORDER, DIFFICULTY, iV } from './game.js';
import { T_LAND, T_WATER, T_MOUNTAIN } from './map.js';

const sq = (v) => v * v;

Object.assign(Game.prototype, {
  initBots() {
    const P = MAX_PLAYERS;
    this.botTimer = new Uint8Array(P);
    this.botPct = new Uint16Array(P);
    this.botPctGoal = new Uint16Array(P);
    this.botPctStep = new Uint8Array(P);
    this.botDiff = new Uint8Array(P);
    this.botPeriod = new Uint16Array(P);
    this.botPeriodGoal = new Uint16Array(P);
    this.tgt = new Uint16Array(8);
    this.tgtCount = 0;
    this.boatMemo = new Uint16Array(P);
    this.endgameFast = 0;
    this.scanBuf = new Uint32Array(512);
    this.scanLen = 0;
    this.scanPass = 0;
    this.scanPos = 0;
    this.scanSeen = 0;
  },

  setupBots() {
    const rng = this.rng;
    const P = MAX_PLAYERS;
    // difficulty -1: the lobby's "mixed" setting (botDifficultyType 1), bot i gets i % 7
    const mixed = this.difficulty < 0;
    for (let i = this.bots - 1; i >= 0; i--) this.botDiff[i + this.humans] = mixed ? i % 7 : this.difficulty;
    for (let i = 0; i < this.humans; i++) this.botDiff[i] = 6;
    for (let i = 0; i < P; i++) {
      const d = this.botDiff[i];
      if (d <= 2) {
        this.botPctStep[i] = 5;
        this.botPeriod[i] = this.botPeriodGoal[i] = 1040;
        if (d === 0) {
          this.botPct[i] = 980;
          this.botPctGoal[i] = 980;
        } else if (d === 1) {
          this.botPct[i] = 980;
          this.botPctGoal[i] = 920;
          this.botPeriod[i] = this.botPeriodGoal[i] = 1100;
        } else {
          this.botPct[i] = 825;
          this.botPctGoal[i] = 750;
        }
      } else if (d <= 4) {
        this.botPctStep[i] = 1 + rng.int(20);
        if (d === 3) {
          this.botPct[i] = this.botPctGoal[i] = 500;
          this.botPeriod[i] = this.botPeriodGoal[i] = 1000;
        } else {
          this.botPeriodGoal[i] = 250 + rng.int(1501);
          this.botPeriod[i] = 500 + rng.int(501);
          this.botPct[i] = 300 + rng.int(201);
          this.botPctGoal[i] = 100 + rng.int(201);
        }
      } else if (d <= 5) {
        this.botPeriod[i] = 1000;
        this.botPeriodGoal[i] = 1000;
        this.botPctStep[i] = 35 + rng.int(16);
        this.botPct[i] = 300 + rng.int(201);
        this.botPctGoal[i] = 50 + rng.int(101);
      } else {
        this.botPeriod[i] = this.botPeriodGoal[i] = 800;
        this.botPctStep[i] = 5;
        this.botPct[i] = 10;
        this.botPctGoal[i] = 250;
      }
      this.botTimer[i] = 1 + iV(this.botPeriod[i] * rng.next(), 327680);
    }
    this.boatMemo.fill(NEUTRAL);
  },

  botWakeWithin(p, v) {
    this.botTimer[p] = Math.min(v, this.botTimer[p]);
  },

  setBotPeriod(p, v) {
    this.botPeriod[p] = this.botPeriodGoal[p] = v;
  },

  botsTick() {
    this.interceptTick();
    for (let i = this.botCount - 1; i >= 0; i--) {
      const p = this.botList[i];
      if (this.alive[p] === 0) {
        this.botCount--;
        this.botList[i] = this.botList[this.botCount];
      } else if (--this.botTimer[p] === 0) {
        this.botDecide(p);
      }
    }
  },

  botDecide(p) {
    if (this.botPeriod[p] !== this.botPeriodGoal[p]) this.botPeriod[p] += this.botPeriod[p] < this.botPeriodGoal[p] ? 3 : -3;
    if (this.botPct[p] !== this.botPctGoal[p]) {
      this.botPct[p] += this.botPct[p] < this.botPctGoal[p] ? this.botPctStep[p] : -this.botPctStep[p];
      if (Math.abs(this.botPct[p] - this.botPctGoal[p]) <= this.botPctStep[p]) this.botPct[p] = this.botPctGoal[p];
    }
    this.botTimer[p] = iV(this.botPeriod[p], 10);
    this.botAttack(p, iV(this.botPct[p] * this.bal[p], 1e3));
  },

  botAttack(p, dn) {
    if (!this.hasFreeSlot(p)) return;
    const cap = this.softCap(p);
    const diff = this.botDiff[p];
    if (diff >= 3 && diff < 6) dn = Math.max(this.bal[p] - cap, dn);
    const nCoast = this.coast[p].length, nBorder = this.border[p].length;
    if (30 * this.terr[p] > this.land && this.rankOf[p] < 10 && 100 * nBorder <= nCoast) this.botWakeWithin(p, 10);
    const rng = this.rng;
    let tryBoat;
    if (!nBorder) tryBoat = true;
    else if (!nCoast) tryBoat = false;
    else tryBoat = (nCoast < nBorder && !rng.int(10)) || (100 * nBorder <= nCoast && rng.int(3) !== 0) || !rng.int(8);
    if (tryBoat && this.botBoat(p)) return;
    if (this.pickTargets(p, true) || this.firstTarget(p, true)) {
      if (this.dropAttacked(p)) return;
      if (this.dropNeutral()) this.botAttackNeutral(p, dn);
      else if (rng.chance(DIFFICULTY.weakestPct[diff])) this.botAttackPlayer(p, dn, this.weakestTarget(p), diff);
      else if (diff === 5) this.botAttackPlayer(p, dn, this.richestTarget(), diff);
      else {
        if (this.anyBotTarget() && rng.chance(DIFFICULTY.timerSpeed[diff])) this.keepBotTargets();
        this.botAttackPlayer(p, dn, diff === 6 ? this.randomTarget() : this.nearestTarget(p), diff);
      }
    } else {
      this.botMountain(p);
    }
  },

  botAttackPlayer(p, dn, target, diff) {
    if (diff >= 3 && diff < 6 && iV(this.bal[p], 8) > this.bal[target]) {
      dn = Math.max(iV(11 * this.bal[target], 5), iV(this.bal[p], 10));
    }
    const from = this.front[p].length;
    this.addFrontAgainst(p, target);
    this.commitAttack(p, target, from, dn);
  },

  botAttackNeutral(p, dn) {
    const from = this.front[p].length;
    this.addFrontNeutral(p);
    if (this.front[p].length !== from) this.commitAttack(p, NEUTRAL, from, dn);
  },

  // ---- target lists ----------------------------------------------------------

  pickTargets(p, any) {
    const B = this.border[p];
    const cs = B.length;
    const os = cs >= 256 ? 12 : cs >= 32 ? 6 : 1;
    const start = cs - 1 - this.rng.int(os);
    const d = this.dir4, px = this.px, own = this.own, tgt = this.tgt;
    this.tgtCount = 0;
    outer: for (let i = start; i >= 0; i -= os) {
      for (let g = 3; g >= 0; g--) {
        const c = B[i] + d[g];
        const v = px[c];
        const o = v === T_LAND ? NEUTRAL : own[c];
        if (o === NEUTRAL || (v >= P_INNER && o !== p)) {
          for (let k = this.tgtCount - 1; k >= 0; k--) if (tgt[k] === o) continue outer;
          tgt[this.tgtCount] = o;
          if (++this.tgtCount >= 8) return true;
        }
      }
    }
    return this.tgtCount > 0;
  },

  firstTarget(p, any) {
    const B = this.border[p];
    const d = this.dir4, px = this.px, own = this.own;
    this.tgtCount = 0;
    for (let i = B.length - 1; i >= 0; i--) {
      for (let g = 3; g >= 0; g--) {
        const c = B[i] + d[g];
        const v = px[c];
        const o = v === T_LAND ? NEUTRAL : own[c];
        if (o === NEUTRAL || (v >= P_INNER && o !== p)) {
          this.tgt[this.tgtCount++] = o;
          return true;
        }
      }
    }
    return false;
  },

  dropNeutral() {
    const tgt = this.tgt;
    for (let i = this.tgtCount - 1; i >= 0; i--) {
      if (tgt[i] === NEUTRAL) {
        this.tgtCount--;
        for (let k = i; k < this.tgtCount; k++) tgt[k] = tgt[k + 1];
        return true;
      }
    }
    return false;
  },

  dropAttacked(p) {
    const tgt = this.tgt;
    for (let i = this.tgtCount - 1; i >= 0; i--) {
      if (this.hasAttack(p, tgt[i])) {
        this.tgtCount--;
        for (let k = i; k < this.tgtCount; k++) tgt[k] = tgt[k + 1];
      }
    }
    return this.tgtCount === 0;
  },

  anyBotTarget() {
    for (let i = this.tgtCount - 1; i >= 0; i--) if (this.isBot(this.tgt[i])) return true;
    return false;
  },

  keepBotTargets() {
    const tgt = this.tgt;
    for (let i = this.tgtCount - 1; i >= 0; i--) if (!this.isBot(tgt[i])) tgt[i] = tgt[--this.tgtCount];
    return this.tgtCount > 0;
  },

  weakestTarget(p) {
    const tgt = this.tgt;
    let best = tgt[0];
    let bestV = this.bal[best] + this.attackTroopsOn(best, p);
    for (let i = this.tgtCount - 1; i >= 1; i--) {
      const v = this.bal[tgt[i]] + this.attackTroopsOn(tgt[i], p);
      if (v < bestV) {
        best = tgt[i];
        bestV = v;
      }
    }
    return best;
  },

  nearestTarget(p) {
    const tgt = this.tgt;
    let best = tgt[0];
    if (this.tgtCount !== 1) {
      const cx = iV(this.x1[p] + this.x0[p], 2), cy = iV(this.y1[p] + this.y0[p], 2);
      let bestD = sq(cx - iV(this.x1[best] + this.x0[best], 2)) + sq(cy - iV(this.y1[best] + this.y0[best], 2));
      for (let i = this.tgtCount - 1; i >= 1; i--) {
        const q = tgt[i];
        const dd = sq(cx - iV(this.x1[q] + this.x0[q], 2)) + sq(cy - iV(this.y1[q] + this.y0[q], 2));
        if (dd < bestD) {
          bestD = dd;
          best = q;
        }
      }
    }
    return best;
  },

  richestTarget() {
    const tgt = this.tgt;
    let best = tgt[0];
    let bestV = this.bal[best];
    for (let i = this.tgtCount - 1; i >= 1; i--) {
      const v = this.bal[tgt[i]];
      if (bestV < v) {
        best = tgt[i];
        bestV = v;
      }
    }
    return best;
  },

  randomTarget() {
    return this.tgt[this.rng.int(this.tgtCount)];
  },

  // ---- boats -------------------------------------------------------------------

  botBoat(p) {
    if (!this.boatsAllowed(p)) return false;
    const d = this.botDiff[p];
    if (this.boatCount[p] >= Math.max(3 * this.endgameFast, DIFFICULTY.boatLimit[d])) return false;
    if (!(this.quote(p, DIFFICULTY.boatPct[d], 32) >= 0)) return false;
    if (this.leaderLand === this.land) return this.botChaseBoat(p);
    if (this.knownRouteBoat(p) || this.boatToNeutral(p) || this.boatToPlayer(p)) {
      this.boatType = 4;
      this.payQuote(p);
      this.launchBoat(p);
      return true;
    }
    return false;
  },

  botChaseBoat(p) {
    const list = this.enemyBoatList(this.rank[0]);
    if (list.length === 0) return false;
    const b = list[this.rng.int(list.length)];
    const id = this.bId[b];
    if (this.isChasing(p, id)) return false;
    const at = this.subToPixel(this.bPos[b]);
    const x = at % this.W, y = iV(at, this.W);
    const dx = Math.max(x - this.x1[p], this.x0[p] - x);
    const dy = Math.max(y - this.y1[p], this.y0[p] - y);
    if (!(dx < 100 && dy < 100)) return false;
    if (!this.chaseBoat(p, id, 1)) return false;
    this.payQuote(p);
    this.launchBoat(p);
    return true;
  },

  knownRouteBoat(p) {
    const routes = this.routes;
    const cs = routes.length;
    const n = Math.min(cs, 32);
    const off = this.rng.int(cs);
    let idx = -1;
    for (let i = 0; i < n; i++) {
      const k = (i + off) % cs;
      const rb = routes[k];
      const a = rb[0], b = rb[rb.length - 1];
      if (this.touchesOwn(p, a) && this.touchesTarget(p, b)) {
        idx = k;
        break;
      }
      if (this.touchesOwn(p, b) && this.touchesTarget(p, a)) {
        const r = this.findRoute(b, a);
        idx = r >= 0 ? r : this.routes.length === 65536 ? -1 : this.addRoute(this.reversed(rb));
        break;
      }
    }
    if (idx === -1) return false;
    const route = this.routes[idx];
    if (this.hasBoatOnRoute(p, route)) return false;
    this.routeTmp = route;
    return true;
  },

  boatToNeutral(p) {
    return this.boatTowards(p, this.neutralShoreTarget(p));
  },

  neutralShoreTarget(p) {
    const cs = this.scanLen;
    if (cs === 0) return -1;
    const rng = this.rng;
    const n = Math.min(cs, this.endgameFast ? cs : 10);
    const start = iV(rng.next() * cs, 32768);
    const end = start + n;
    const fx = rng.range(this.x0[p], this.x1[p]);
    const fy = rng.range(this.y0[p], this.y1[p]);
    const W = this.W;
    let best = -1;
    let bestD = this.W * this.W + this.H * this.H;
    for (let i = start; i < end; i++) {
      const k = i % cs;
      const t = this.scanBuf[k];
      const dd = sq(fx - (t % W)) + sq(fy - iV(t, W));
      if (dd < bestD) {
        bestD = dd;
        best = k;
      }
    }
    if (best === -1) return -1;
    const t = this.scanBuf[best];
    let x = t % W, y = iV(t, W);
    let ex = fx - x, ey = fy - y;
    if (Math.abs(ex) >= Math.abs(ey)) {
      ey = 0;
      ex = Math.sign(ex);
    } else {
      ex = 0;
      ey = Math.sign(ey);
    }
    if (ex === ey) ex = 1;
    for (;;) {
      x += ex;
      y += ey;
      if (!(x > 0 && x < W - 1 && y > 0 && y < this.H - 1)) break;
      const c = y * W + x;
      if (this.px[c] === T_WATER) return c;
    }
    return -1;
  },

  boatToPlayer(p) {
    let memo = this.boatMemo[p];
    if (memo !== NEUTRAL) {
      if (!(this.alive[memo] !== 0 && this.coast[memo])) {
        this.boatMemo[p] = NEUTRAL;
        memo = NEUTRAL;
      }
    }
    const rng = this.rng;
    const list = this.aliveList, n = this.aliveCount;
    const cs = Math.min(n, n < 17 && rng.int(20) === 5 ? 1 : 16);
    const ba = rng.int(n);
    const dN = this.scratchList;
    let fe = 0;
    for (let i = 0; i < cs; i++) {
      const q = list[(i + ba) % n];
      if (q !== p && this.coast[q].length) dN[fe++] = q;
    }
    this.scratchCount = fe;
    if (fe === 0) return false;
    const aim = this.randomPointIn(p);
    let tq = this.nearestOf(p, aim);
    let shore = this.sampleShore(tq, aim);
    if (shore > 0 && this.boatTowards(p, this.waterNextTo(shore, aim))) {
      this.rememberBoatTarget(p, aim, tq, memo);
      return true;
    }
    shore = this.sampleRemembered(p, aim);
    if (shore > 0 && this.boatTowards(p, this.waterNextTo(shore, aim))) {
      this.rememberBoatTarget(p, aim, this.own[shore], memo);
      return true;
    }
    shore = this.sampleShore(memo, aim);
    return shore > 0 && this.boatTowards(p, this.waterNextTo(shore, aim));
  },

  sampleRemembered(p, aim) {
    const dN = this.scratchList;
    let ba = 0;
    for (let i = 0; i < this.scratchCount; i++) {
      const q = this.boatMemo[dN[i]];
      if (q !== NEUTRAL && this.alive[q] !== 0 && p !== q) dN[ba++] = q;
    }
    this.scratchCount = ba;
    return ba !== 0 ? this.sampleShore(this.nearestOf(p, aim), aim) : 0;
  },

  randomPointIn(p) {
    const x = this.rng.range(this.x0[p], this.x1[p]);
    const y = this.rng.range(this.y0[p], this.y1[p]);
    return y * this.W + x;
  },

  centerOf(q) {
    return ((this.y0[q] + this.y1[q]) >> 1) * this.W + ((this.x0[q] + this.x1[q]) >> 1);
  },

  dist2(a, b) {
    const W = this.W;
    return sq((a % W) - (b % W)) + sq(iV(a, W) - iV(b, W));
  },

  nearestOf(p, aim) {
    const dN = this.scratchList;
    let bestD = -1, best = NEUTRAL;
    for (let i = 0; i < this.scratchCount; i++) {
      const q = dN[i];
      const dd = this.dist2(aim, this.centerOf(q));
      if (bestD === -1 || dd < bestD) {
        bestD = dd;
        best = q;
      }
    }
    return best;
  },

  sampleShore(q, aim) {
    if (q === NEUTRAL) return 0;
    const C = this.coast[q];
    const n = C.length;
    if (n === 0) return 0;
    const cs = Math.min(n, 10);
    let mc = 0;
    let bestD = this.dist2(C[0], aim);
    for (let i = 0; i < cs; i++) {
      const k = this.rng.int(n);
      const dd = this.dist2(C[k], aim);
      if (dd < bestD) {
        bestD = dd;
        mc = k;
      }
    }
    return C[mc];
  },

  rememberBoatTarget(p, aim, q, prev) {
    if (prev === NEUTRAL || this.dist2(aim, this.centerOf(q)) < this.dist2(aim, this.centerOf(prev))) this.boatMemo[p] = q;
  },

  boatTowards(p, water) {
    return water !== -1 && this.touchesTarget(p, water) && this.findBoatRoute(p, water, 0);
  },

  // ---- mountains ------------------------------------------------------------------

  botMountain(p) {
    if (!this.mountainMap || !this.passableMountains || this.cliff[p].length === 0) return false;
    const mine = this.cliffMountain(p);
    if (mine === null) return false;
    const list = this.aliveList, n = this.aliveCount;
    const cs = Math.min(n, 12);
    const ba = this.rng.int(n);
    const dN = this.scratchList;
    let fe = 0;
    for (let i = 0; i < cs; i++) {
      const q = list[(i + ba) % n];
      if (q !== p && this.cliff[q].length) dN[fe++] = q;
    }
    this.scratchCount = fe;
    for (let i = 0; i < fe; i++) {
      const other = this.cliffMountain(dN[i]);
      if (other !== null && other.id === mine.id) {
        this.mountainAttack(p, other.tile, other.owner);
        return true;
      }
    }
    const sc = this.scanLen;
    if (sc !== 0) {
      let c = this.scanBuf[this.rng.int(sc)];
      const g = this.rng.int(4);
      const d = this.dir4[g];
      for (;;) {
        c += d;
        if (this.px[c] === T_MOUNTAIN) {
          if (this.wid[c] === mine.id) {
            this.mountainAttack(p, c, NEUTRAL);
            return true;
          }
          break;
        }
        if (this.px[c] !== T_LAND) break;
      }
    }
    return false;
  },

  cliffMountain(p) {
    const C = this.cliff[p];
    const cs = C.length;
    const step = Math.max(iV(cs, 12), 1);
    const off = this.rng.int(cs);
    const d = this.dir4;
    for (let i = 0; i < cs; i += step) {
      const b = C[(i + off) % cs];
      for (let g = 3; g >= 0; g--) {
        const c = b + d[g];
        if (this.px[c] === T_MOUNTAIN) return { tile: c, id: this.wid[c], owner: p };
      }
    }
    return null;
  },

  mountainAttack(p, tile, target) {
    const troops = this.sendAll(p, DIFFICULTY.mountainPct[this.botDiff[p]]);
    this.front[p].push(tile);
    this.addAttack(p, troops, target);
    this.schedule(p, true);
  },

  // aDS of the game: send (pct+1)/1024 keeping at least max(10%, 1000) at home.
  sendAll(p, pct) {
    const lG = this.bal[p];
    let troops = iV(lG * (pct + 1), 1024);
    let keep = Math.max(iV(lG, 10), 1e3);
    troops = Math.min(troops, lG - keep);
    if (troops < 0) {
      this.bal[p] = 0;
      keep = Math.min(1e3, lG + 5e4 - this.debt[p]);
      this.attackFeeTmp = keep;
      this.debt[p] += keep - lG;
      return 0;
    }
    this.attackFeeTmp = keep;
    this.bal[p] -= keep + troops;
    return troops;
  },

  // ---- boat interception by bots ----------------------------------------------------

  interceptTick() {
    if (this.t % 51 !== 45) return;
    const cs = this.boatN;
    for (let b = 0; b < cs; b++) {
      const type = this.bType[b];
      if (type % 64 === 6) continue;
      const rb = this.bRoute[b];
      const q = this.botNextTo(rb[rb.length - 1]);
      if (q < 0) continue;
      if (q === this.bSlot[b] >> 3) continue;
      if (this.rng.int(1e3) >= DIFFICULTY.interceptPermille[this.botDiff[q]]) continue;
      if (!this.routeLeftShort(b, rb)) continue;
      const id = this.bId[b];
      if (type >= 64 && this.isChasing(q, id)) continue;
      if (this.boatsAllowed(q) && this.quote(q, DIFFICULTY.boatPct[this.botDiff[q]], 32) >= 0) {
        this.bType[b] = 64 + (type % 64);
        this.addChase(id, this.boatNextId);
        this.routeTmp = this.reversed(rb);
        this.boatType = 6;
        this.payQuote(q);
        this.launchBoat(q);
      }
    }
  },

  routeLeftShort(b, rb) {
    const cs = rb.length - 1;
    const leg = this.bLeg[b];
    let len = 0;
    for (let i = leg + 1; i < cs; i++) len += this.pixDist(rb[i], rb[i + 1]);
    len += this.pixDist(this.subToPixel(this.bPos[b]), rb[leg + 1]);
    return len <= 60;
  },

  // ---- neutral land scanner and endgame speed-up ----------------------------------

  endgameSpeedTick() {
    if (!this.endgameFast && this.t % 30 === 7 && this.leaderHas(90)) {
      this.endgameFast = 1;
      this.setBotPeriod(this.rank[0], 100);
    }
  },

  scanTick() {
    let cs = this.scanLen;
    let go;
    if (cs === 0) go = true;
    else {
      if (this.t % 35 === 6) {
        for (let i = cs - 1; i >= 0; i--) {
          if (this.px[this.scanBuf[i]] !== T_LAND) {
            cs--;
            this.scanBuf[i] = this.scanBuf[cs];
          }
        }
        this.scanLen = cs;
      }
      go = cs < 512;
    }
    if (!go) return;
    if (300 <= this.scanPass) {
      const n = this.scanLen;
      if (n) {
        if (this.t % 350 !== 1) return;
        if (this.scanSeen !== n) {
          this.scanSeen = n;
          return;
        }
        if (!this.isBot(this.rank[0])) return;
      } else if (this.t % 12 !== 8) return;
      const second = this.aliveCount < 2 ? 0 : this.terr[this.rank[1]];
      if (!second) {
        this.scanPos = this.scanPass = 0;
        this.scanLen = 0;
        this.scanSeen = 0;
      }
    } else {
      const W = this.W;
      const iw = W - 2;
      const total = iw * (this.H - 2);
      const stride = 300;
      let jP = this.scanLen;
      const end = Math.min(this.scanPos + stride * ((1 + 19 * this.endgameFast) * 300), total);
      let i;
      for (i = this.scanPos; i < end; i += stride) {
        const c = (i % iw) + (Math.floor(i / iw) + 1) * W + 1;
        if (this.px[c] === T_LAND) {
          this.scanBuf[jP] = c;
          if (++jP === 512) {
            i += stride;
            break;
          }
        }
      }
      this.scanPos = i;
      if (i >= total) this.scanPos = ++this.scanPass;
      this.scanLen = jP;
    }
  },
});
