// Boats: launch, movement along cached routes, boat fights, landing,
// recall/interception chases, route finding and the human boat commands.
import { Game, MAX_PLAYERS, NEUTRAL, P_INNER, iV } from './game.js';
import { T_LAND, T_WATER } from './map.js';

const MAX_BOATS = 512;
const PLAYER_BOATS = 8;
const MAX_ROUTES = 65536;
const CELL = 32;
const FIGHT_RANGE2 = 14400;

Object.assign(Game.prototype, {
  initBoats() {
    const B = MAX_BOATS;
    this.boatN = 0;
    this.boatNextId = 0;
    this.bSlot = new Uint16Array(B);
    this.bPos = new Uint32Array(B);
    this.bProg = new Uint16Array(B);
    this.bTroops = new Uint32Array(B);
    this.bCellIdx = new Uint16Array(B);
    this.bId = new Uint16Array(B);
    this.bType = new Uint8Array(B);
    this.bHit = new Uint8Array(B);
    this.bRoute = new Array(B).fill(null);
    this.bLeg = new Uint16Array(B);
    this.boatCount = new Uint8Array(MAX_PLAYERS);
    this.boatOf = new Uint16Array(PLAYER_BOATS * MAX_PLAYERS);
    this.routes = [];
    this.routeIndex = new Map();
    this.chases = new Uint16Array(2 * B);
    this.chaseLen = 0;
    this.chaseIdx = 0;
    this.routeTmp = null;
    this.boatType = 0;
    this.sub = this.W << 4;
    this.cellCols = 1 + iV(this.W - 1, CELL);
    this.cellRows = 1 + iV(this.H - 1, CELL);
    this.cells = [];
    for (let i = this.cellCols * this.cellRows; i > 0; i--) this.cells.push([]);
    this.cellNb = new Int32Array(9);
    for (let c4 = -1; c4 <= 1; c4++) {
      for (let bp = -1; bp <= 1; bp++) this.cellNb[3 * (1 + bp) + 1 + c4] = bp * this.cellCols + c4;
    }
    this.bfsCost = null;
  },

  // ---- coordinates -------------------------------------------------------------
  // Boat positions are in 1/16 pixel units: (16y+8)*16W + 16x+8 for pixel centres.

  subPos(p) {
    const W = this.W;
    return W * iV(p, W) * 256 + ((p % W) << 4) + 8 + (W << 7);
  },

  subToPixel(a) {
    const S = this.sub;
    return this.W * (iV(a, S) >> 4) + ((a % S) >> 4);
  },

  cellOf(a) {
    const p = this.subToPixel(a);
    const W = this.W;
    return ((p % W) >> 5) + this.cellCols * (iV(p, W) >> 5);
  },

  pixDist(a, b) {
    const W = this.W;
    const dx = (a % W) - (b % W);
    const dy = iV(a, W) - iV(b, W);
    return ~~Math.sqrt(dx * dx + dy * dy + 0.5);
  },

  cellAdd(b, cell) {
    const list = this.cells[cell];
    list.push(b);
    return list.length - 1;
  },

  cellMove(idx, from, to) {
    const ic = this.cellOf(from), ie = this.cellOf(to);
    if (ic === ie) return idx;
    const list = this.cells[ic];
    const last = list.pop();
    if (list.length === idx) return this.cellAdd(last, ie);
    const me = list[idx];
    list[idx] = last;
    this.bCellIdx[last] = idx;
    return this.cellAdd(me, ie);
  },

  // ---- boat list -------------------------------------------------------------

  launchBoat(p) {
    let troops = this.attackTroopsTmp;
    const route = this.routeTmp;
    const id = this.boatNextId;
    const b = this.boatN;
    const pos = this.subPos(route[0]);
    const n = this.boatCount[p];
    const slot = (p << 3) + n;
    this.bSlot[b] = slot;
    this.bPos[b] = pos;
    this.bProg[b] = 0;
    if (troops < 60) {
      this.takeBalance(p, 60 - troops);
      troops = 60;
    }
    this.bTroops[b] = troops;
    this.bCellIdx[b] = this.cellAdd(b, this.cellOf(pos));
    this.bId[b] = id;
    this.bType[b] = this.boatType;
    this.bHit[b] = 0;
    this.bRoute[b] = route;
    this.bLeg[b] = 0;
    this.boatNextId = (id + 1) % 65536;
    this.boatCount[p] = n + 1;
    this.boatOf[slot] = b;
    this.boatN++;
  },

  removeBoat(b) {
    const last = this.boatN - 1;
    const slot = this.bSlot[b], cidx = this.bCellIdx[b], pos = this.bPos[b];
    this.boatN = last;
    this.bSlot[b] = this.bSlot[last];
    this.bPos[b] = this.bPos[last];
    this.bProg[b] = this.bProg[last];
    this.bTroops[b] = this.bTroops[last];
    this.bCellIdx[b] = this.bCellIdx[last];
    this.bId[b] = this.bId[last];
    this.bType[b] = this.bType[last];
    this.bHit[b] = this.bHit[last];
    this.bRoute[b] = this.bRoute[last];
    this.bLeg[b] = this.bLeg[last];
    this.boatOf[this.bSlot[b]] = b;
    const p = slot >> 3;
    const n = this.boatCount[p] - 1;
    const lastSlot = (p << 3) + n;
    this.boatCount[p] = n;
    if (lastSlot !== slot) {
      this.boatOf[slot] = this.boatOf[lastSlot];
      this.bSlot[this.boatOf[slot]] = slot;
    }
    this.cells[this.cellOf(this.bPos[b])][this.bCellIdx[b]] = b;
    const list = this.cells[this.cellOf(pos)];
    const moved = list.pop();
    if (cidx !== list.length) {
      list[cidx] = moved;
      this.bCellIdx[moved] = cidx;
    }
  },

  removeBoatsOf(p) {
    const base = p << 3;
    for (let i = base + this.boatCount[p] - 1; i >= base; i--) this.removeBoat(this.boatOf[i]);
  },

  findBoat(id) {
    const ids = this.bId;
    for (let b = 0, n = this.boatN; b < n; b++) if (ids[b] === id) return b;
    return -1;
  },

  playerBoat(p, id) {
    const base = p << 3;
    for (let i = base, e = base + this.boatCount[p]; i < e; i++) {
      const b = this.boatOf[i];
      if (this.bId[b] === id) return b;
    }
    return -1;
  },

  boatTroops(p) {
    const base = p << 3;
    let s = 0;
    for (let i = base, e = base + this.boatCount[p]; i < e; i++) s += this.bTroops[this.boatOf[i]];
    return s;
  },

  enemyBoatList(leader) {
    const out = [];
    for (let b = 0; b < this.boatN; b++) if (this.bSlot[b] >> 3 !== leader) out.push(b);
    return out;
  },

  enemyBoatsOf(leader) {
    let n = 0;
    for (let b = 0; b < this.boatN; b++) if (this.bSlot[b] >> 3 !== leader) n++;
    return n;
  },

  boatsAllowed(p) {
    return !!this.passableWater && this.boatN !== MAX_BOATS && this.boatCount[p] !== PLAYER_BOATS && this.coast[p].length !== 0;
  },

  canBoat(p) {
    return this.boatsAllowed(p) && !this.routesFull();
  },

  // ---- tick ------------------------------------------------------------------

  boatsTick() {
    this.landBoats();
    this.moveBoats();
    if (this.t % 2 === 1) this.fightBoats();
    if (this.t % 5 === 3) this.decayBoats();
    const troops = this.bTroops, hit = this.bHit;
    for (let b = this.boatN - 1; b >= 0; b--) {
      hit[b] >>= 1;
      if (troops[b] === 0) {
        this.endChasesOf(b);
        this.removeBoat(b);
      }
    }
  },

  landBoats() {
    for (let b = this.boatN - 1; b >= 0; b--) {
      if (this.bProg[b] !== 65535) continue;
      if (this.arrive(b, this.subToPixel(this.bPos[b]), this.bType[b] % 64)) {
        this.endChasesOf(b);
        this.removeBoat(b);
      }
    }
  },

  // Returns true when the boat is done (landed or lost).
  arrive(b, at, type) {
    if (type === 6) {
      if (this.chaseArrived(b, at)) {
        this.bLeg[b]++;
        this.bProg[b] = 0;
        return false;
      }
      return true;
    }
    const p = this.bSlot[b] >> 3;
    const troops = this.bTroops[b];
    const d = this.dir4, px = this.px, own = this.own;
    if (type < 4) {
      this.landAt(p, troops, at + d[type], at);
    } else if (type === 4) {
      for (let g = 0; g < 4; g++) if (px[at + d[g]] === T_LAND) return this.landAt(p, troops, at + d[g], at), true;
      for (let g = 0; g < 4; g++) {
        const c = at + d[g];
        if (px[c] >= P_INNER && own[c] !== p) return this.landAt(p, troops, c, at), true;
      }
      for (let g = 0; g < 4; g++) if (px[at + d[g]] >= P_INNER) return this.landAt(p, troops, at + d[g], at), true;
    } else if (type === 5) {
      for (let g = 0; g < 4; g++) {
        const c = at + d[g];
        if (px[c] >= P_INNER && own[c] === p) return this.landAt(p, troops, c, at), true;
      }
      for (let g = 0; g < 4; g++) if (px[at + d[g]] >= P_INNER) return this.landAt(p, troops, at + d[g], at), true;
      for (let g = 0; g < 4; g++) if (px[at + d[g]] === T_LAND) return this.landAt(p, troops, at + d[g], at), true;
    }
    return true;
  },

  landAt(p, troops, c, at) {
    const v = this.px[c];
    let target;
    if (v === T_LAND) target = NEUTRAL;
    else {
      if (v < P_INNER) return;
      target = this.own[c];
      if (target === p) {
        this.addBalance(p, troops);
        return;
      }
    }
    if (this.hasAttack(p, target) || this.hasFreeSlot(p)) {
      this.front[p].push(at);
      this.addAttack(p, troops, target);
      this.schedule(p, true);
    }
  },

  moveBoats() {
    const pos = this.bPos, route = this.bRoute, leg = this.bLeg, prog = this.bProg, troops = this.bTroops, hit = this.bHit, cidx = this.bCellIdx;
    const S = this.sub;
    for (let b = this.boatN - 1; b >= 0; b--) {
      const old = pos[b];
      const rb = route[b];
      const k = leg[b];
      const a = this.subPos(rb[k]);
      const e = this.subPos(rb[k + 1]);
      const ax = a % S, ay = ~~((a + 0.5) / S);
      const ex = e % S, ey = ~~((e + 0.5) / S);
      const dx = ex - ax, dy = ey - ay;
      const len = Math.max(~~Math.sqrt(dx * dx + dy * dy + 0.5), 1);
      const tr = troops[b];
      const speed = hit[b] ? 4e4 : 25e4 + Math.min(20 * tr, 3e5) + Math.min(tr >> 3, 5e4);
      const np = prog[b] + Math.max(~~((speed + 0.5) / len), 1);
      let now;
      if (np >= 65535) {
        if (k + 2 < rb.length) {
          leg[b] = k + 1;
          const f = this.subPos(rb[k + 2]);
          const fx = (f % S) - ex, fy = ~~((f + 0.5) / S) - ey;
          const len2 = Math.max(~~Math.sqrt(fx * fx + fy * fy + 0.5), 1);
          const over = Math.min(Math.floor((len * Math.min(np - 65535, 65535) + 0.5) / len2), 65534);
          prog[b] = over;
          now = ex + iV(over * fx, 65535) + S * (ey + iV(over * fy, 65535));
        } else {
          now = e;
          prog[b] = 65535;
        }
      } else {
        prog[b] = np;
        now = ax + iV(np * dx, 65535) + S * (ay + iV(np * dy, 65535));
      }
      pos[b] = now;
      cidx[b] = this.cellMove(cidx[b], old, now);
    }
  },

  fightBoats() {
    const n = this.boatN, pos = this.bPos, slot = this.bSlot, troops = this.bTroops, hit = this.bHit;
    const cells = this.cells, nCells = cells.length, nb = this.cellNb, S = this.sub;
    const ba = (n - 1) * (iV(this.t, 2) % 2);
    for (let i = 0; i < n; i++) {
      const b = Math.abs(i - ba);
      const pb = pos[b];
      const cell = this.cellOf(pb);
      const owner = slot[b] >> 3;
      const x = pb % S, y = ~~((pb + 0.5) / S);
      const mine = troops[b];
      for (let f = 0; f < 9; f++) {
        const c = cell + nb[f];
        if (c < 0 || c >= nCells) continue;
        const list = cells[c];
        for (let k = 0, m = list.length; k < m; k++) {
          const o = list[k];
          if (slot[o] >> 3 === owner) continue;
          const po = pos[o];
          const ddx = x - (po % S), ddy = y - ~~((po + 0.5) / S);
          if (ddx * ddx + ddy * ddy < FIGHT_RANGE2) {
            const v = troops[o];
            const dmg = v <= mine ? Math.max(1, iV(v + iV(mine - v, 10), 10)) : Math.max(1, iV(mine, 10));
            troops[o] = Math.max(v - dmg, 0);
            hit[o] = 4;
          }
        }
      }
    }
  },

  decayBoats() {
    const troops = this.bTroops;
    for (let b = 0, n = this.boatN; b < n; b++) {
      const v = troops[b];
      troops[b] = Math.max(v - Math.max(1, v >> 7), 0);
    }
  },

  // ---- chases (interceptors) ---------------------------------------------------
  // chase[] holds (target boat id, chaser boat id) pairs.

  addChase(target, chaser) {
    this.chases[this.chaseLen++] = target;
    this.chases[this.chaseLen++] = chaser;
  },

  isChasing(p, target) {
    const c = this.chases;
    for (let i = 0; i < this.chaseLen; i += 2) {
      if (c[i] === target) {
        const k = this.findBoat(c[i + 1]);
        if (k >= 0 && p === this.bSlot[k] >> 3) return true;
      }
    }
    return false;
  },

  // A chased boat is gone: its chasers turn back.
  endChasesOf(b) {
    if (this.bType[b] < 64) return;
    const id = this.bId[b], c = this.chases;
    let cs = this.chaseLen;
    for (let i = cs - 2; i >= 0; i -= 2) {
      if (c[i] === id) {
        const k = this.findBoat(c[i + 1]);
        if (k >= 0) this.recallBoat(k);
        c[i] = c[cs - 2];
        c[i + 1] = c[cs - 1];
        cs -= 2;
      }
    }
    this.chaseLen = cs;
  },

  recallBoat(b) {
    const type = this.bType[b];
    if (type % 64 === 5) return false;
    const rb = this.bRoute[b];
    this.bProg[b] = 65535 - this.bProg[b];
    this.bLeg[b] = rb.length - this.bLeg[b] - 2;
    this.bRoute[b] = this.reversed(rb);
    this.bType[b] = type - (type % 64) + 5;
    return true;
  },

  // An interceptor reached the end of its route: follow the chased boat's route.
  chaseArrived(b, at) {
    const myId = this.bId[b], c = this.chases;
    let target = -1;
    for (let i = 1; i < this.chaseLen; i += 2) {
      if (c[i] === myId) {
        target = c[i - 1];
        break;
      }
    }
    if (target === -1) return false;
    const t = this.findBoat(target);
    if (t < 0) return false;
    const rb = this.bRoute[t];
    if (at === rb[rb.length - 1]) {
      this.bRoute[b] = this.joinRoutes(this.bRoute[b], this.reversed(rb));
    } else {
      const k = this.legOf(rb, at);
      if (k === -1) return false;
      const tk = this.bLeg[t];
      if (k === tk) {
        const tp = this.subToPixel(this.bPos[t]);
        this.bRoute[b] = this.spliceRoute(this.bRoute[b], rb, k, at, this.pixDist(rb[k], at) > this.pixDist(rb[k], tp));
      } else {
        this.bRoute[b] = this.spliceRoute(this.bRoute[b], rb, k, at, tk < k);
      }
    }
    return true;
  },

  legOf(rb, at) {
    const W = this.W;
    const cs = rb.length - 1;
    const c4 = at % W, bp = iV(at, W);
    for (let i = 0; i < cs; i++) {
      const o5 = rb[i], o7 = rb[i + 1];
      const cU = o5 % W, y5 = iV(o5, W), cW = o7 % W, y7 = iV(o7, W);
      if ((c4 !== cU && c4 !== cW && Math.sign(c4 - cU) === Math.sign(c4 - cW)) || (bp !== y5 && bp !== y7 && Math.sign(bp - y5) === Math.sign(bp - y7))) continue;
      if (cU === cW || y5 === y7) return i;
      if (Math.abs(c4 - cU) === Math.abs(bp - y5) && Math.abs(c4 - cW) === Math.abs(bp - y7)) return i;
    }
    return -1;
  },

  joinRoutes(a, b) {
    const fe = a.length - 1;
    const out = new Uint32Array(fe + b.length);
    out.set(a, 0);
    out.set(b, fe);
    return out;
  },

  spliceRoute(wo, vg, bm, at, rev) {
    if (rev) {
      vg = this.reversed(vg);
      bm = vg.length - bm - 2;
    }
    const rest = vg.subarray(bm + 1 + (at === vg[bm + 1] ? 1 : 0));
    const out = new Uint32Array(wo.length + rest.length);
    out.set(wo, 0);
    out.set(rest, wo.length);
    return out;
  },

  // r7.rH: route for a boat of p chasing boat `id` (sets routeTmp/boatType).
  chaseBoat(p, id, limit) {
    if (!this.chaseRoute(p, id, limit)) return false;
    const k = this.chaseIdx;
    this.bType[k] = 64 + (this.bType[k] % 64);
    this.addChase(id, this.boatNextId);
    return true;
  },

  chaseRoute(p, id, limit) {
    if (!this.canBoat(p)) return false;
    const k = this.findBoat(id);
    if (k < 0) return false;
    this.chaseIdx = k;
    if (p === this.bSlot[k] >> 3) return false;
    const rb = this.bRoute[k];
    if (this.touchesOwn(p, rb[rb.length - 1])) {
      this.routeTmp = this.reversed(rb);
      this.boatType = 6;
      return true;
    }
    const at = this.subToPixel(this.bPos[k]);
    const c = this.nearestCoast(p, at);
    if (c === -1) return false;
    const dist = this.pixDist(c, at);
    if (limit && 120 < dist) return false;
    if (!this.findBoatRoute(p, this.pointAhead(k, dist, at), 1)) return false;
    this.boatType = 6;
    return true;
  },

  pointAhead(k, dist, at) {
    const rb = this.bRoute[k], leg = this.bLeg[k];
    const rf = this.pixDist(at, rb[leg + 1]);
    if (dist <= rf) return this.pointBetween(at, rb[leg + 1], rf, dist);
    let rh = dist - rf;
    const cs = rb.length - 1;
    for (let i = leg + 1; i < cs; i++) {
      const ri = this.pixDist(rb[i], rb[i + 1]);
      if (rh <= ri) return this.pointBetween(rb[i], rb[i + 1], ri, rh);
      rh -= ri;
    }
    return rb[cs];
  },

  pointBetween(a, b, len, d) {
    const W = this.W;
    const x0 = a % W, y0 = iV(a, W);
    const dx = (b % W) - x0, dy = iV(b, W) - y0;
    len = Math.max(len, 1);
    const ex = iV(Math.abs(dx) * d, len), ey = iV(Math.abs(dy) * d, len);
    return (y0 + Math.sign(dy) * ey) * W + x0 + Math.sign(dx) * ex;
  },

  // ---- routes ------------------------------------------------------------------

  routesFull() {
    return this.routes.length === MAX_ROUTES;
  },

  findRoute(a, b) {
    const k = this.routeIndex.get(a * this.N + b);
    return k === undefined ? -1 : k;
  },

  addRoute(r) {
    const k = this.routes.length;
    this.routes.push(r);
    const key = r[0] * this.N + r[r.length - 1];
    if (!this.routeIndex.has(key)) this.routeIndex.set(key, k);
    return k;
  },

  reversed(r) {
    const out = new Uint32Array(r.length);
    out.set(r);
    return out.reverse();
  },

  hasBoatOnRoute(p, rb) {
    const a = rb[0], b = rb[rb.length - 1];
    const base = p << 3;
    for (let i = base, e = base + this.boatCount[p]; i < e; i++) {
      const r = this.bRoute[this.boatOf[i]];
      if (r[0] === a && r[r.length - 1] === b) return true;
    }
    return false;
  },

  touchesOwn(p, c) {
    const d = this.dir4, px = this.px, own = this.own;
    for (let g = 0; g < 4; g++) {
      const n = c + d[g];
      if (px[n] >= P_INNER && own[n] === p) return true;
    }
    return false;
  },

  touchesTarget(p, c) {
    const d = this.dir4, px = this.px, own = this.own;
    for (let g = 0; g < 4; g++) {
      const n = c + d[g];
      const v = px[n];
      if (v === T_LAND) return true;
      if (v >= P_INNER && own[n] !== p) return true;
    }
    return false;
  },

  botNextTo(c) {
    const d = this.dir4, px = this.px, own = this.own;
    for (let g = 0; g < 4; g++) {
      const n = c + d[g];
      if (px[n] >= P_INNER && this.isBot(own[n])) return own[n];
    }
    return -1;
  },

  isShoreWater(c) {
    if (this.px[c] !== T_WATER) return false;
    const d = this.dir4;
    for (let g = 0; g < 4; g++) if (this.passable(c + d[g])) return true;
    return false;
  },

  touchesBody(c, id) {
    const d = this.dir4, px = this.px, wid = this.wid;
    for (let g = 0; g < 4; g++) {
      const n = c + d[g];
      if (px[n] === T_WATER && wid[n] === id) return true;
    }
    return false;
  },

  playerTouchesBody(p, id) {
    const C = this.coast[p];
    for (let i = 0; i < C.length; i++) if (this.touchesBody(C[i], id)) return true;
    return false;
  },

  // Water pixel next to coast pixel o5 on the body of o7, closest to o7.
  waterNextTo(o5, o7) {
    const id = this.bodyId(o7);
    const d = this.dir4;
    let best = -1;
    for (let g = 0; g < 4; g++) {
      const n = o5 + d[g];
      if (this.px[n] === T_WATER && this.wid[n] === id && (best === -1 || this.dist2(n, o7) < this.dist2(best, o7))) best = n;
    }
    return best;
  },

  // Closest coast pixel of p touching the water body of c.
  nearestCoast(p, c) {
    const C = this.coast[p], W = this.W;
    const x = c % W, y = iV(c, W);
    const id = this.bodyId(c);
    let best = -1, min = W * W + this.H * this.H;
    for (let i = 0, n = C.length; i < n; i++) {
      const o = C[i];
      const dx = x - (o % W), dy = y - ~~((0.5 + o) / W);
      const dd = dx * dx + dy * dy;
      if (dd < min && this.touchesBody(o, id)) {
        min = dd;
        best = o;
      }
    }
    return best;
  },

  // aDn.ra: route from p's coast to water pixel u9 (sets routeTmp).
  findBoatRoute(p, u9, bfs) {
    const k = this.boatRouteIndex(p, u9, bfs);
    if (k === -1) return false;
    this.routeTmp = this.routes[k];
    return true;
  },

  boatRouteIndex(p, u9, bfs) {
    let start = this.nearestCoast(p, u9);
    if (start === -1) return -1;
    start = this.waterNextTo(start, u9);
    if (start === -1) return -1;
    let k = this.findRoute(start, u9);
    if (k >= 0) return k;
    if (this.routesFull()) return -1;
    if ((k = this.findRoute(u9, start)) >= 0) return this.addRoute(this.reversed(this.routes[k]));
    if (start === u9) return this.addRoute(new Uint32Array([start, u9]));
    if ((k = this.straightRoute(start, u9)) >= 0) return k;
    return bfs ? this.searchRoute(u9, p) : -1;
  },

  waterCol(x, a, b) {
    const W = this.W, px = this.px;
    for (let y = Math.min(a, b) + 1, e = Math.max(a, b); y < e; y++) if (px[y * W + x] !== T_WATER) return false;
    return true;
  },

  waterRow(y, a, b) {
    const W = this.W, px = this.px;
    for (let x = Math.min(a, b) + 1, e = Math.max(a, b); x < e; x++) if (px[y * W + x] !== T_WATER) return false;
    return true;
  },

  diagRoute(x0, y0, x1, y1, a, b) {
    const W = this.W;
    const cs = Math.min(Math.abs(x1 - x0), Math.abs(y1 - y0));
    const ex = Math.sign(x1 - x0), ey = Math.sign(y1 - y0);
    for (let i = 0; i < cs; i++) {
      x0 += ex;
      y0 += ey;
      if (this.px[y0 * W + x0] !== T_WATER) return null;
    }
    const ok = x0 === x1 ? this.waterCol(x0, y0, y1) : this.waterRow(y0, x0, x1);
    return ok ? new Uint32Array([a, y0 * W + x0, b]) : null;
  },

  straightRoute(a, b) {
    const W = this.W;
    const x0 = a % W, y0 = iV(a, W), x1 = b % W, y1 = iV(b, W);
    let r = null;
    if (x0 === x1) {
      if (this.waterCol(x0, y0, y1)) r = new Uint32Array([a, b]);
    } else if (y0 !== y1) {
      r = this.diagRoute(x0, y0, x1, y1, a, b) || this.diagRoute(x1, y1, x0, y0, a, b);
    } else if (this.waterRow(y0, x0, x1)) {
      r = new Uint32Array([a, b]);
    }
    return r === null ? -1 : this.addRoute(r);
  },

  // Layered 8-neighbour search over water from `start` until a water pixel
  // orthogonally next to p's land is reached (human boats only).
  searchRoute(start, p) {
    const N = this.N;
    if (this.bfsCost === null) this.bfsCost = new Uint16Array(N);
    const dQ = this.bfsCost, ring = this.dirRing, px = this.px, own = this.own;
    dQ.fill(0);
    let buffer = [start];
    dQ[start] = 1;
    let nn = -1;
    let cs = buffer.length;
    while (nn === -1 && cs) {
      const next = [];
      for (let i = 0; i < cs; i++) {
        const o = buffer[i];
        const hK = dQ[o];
        for (let g = 0; g < 8; g++) {
          const n = o + ring[g];
          if (px[n] === T_WATER) {
            const old = dQ[n];
            const cost = hK + 5 + ((g & 1) << 1);
            if (old === 0) {
              next.push(n);
              dQ[n] = cost;
            } else dQ[n] = Math.min(cost, old);
          } else if (nn === -1 && (g & 1) === 0 && px[n] >= P_INNER && own[n] === p) nn = o;
        }
      }
      buffer = next;
      cs = buffer.length;
    }
    if (nn === -1) return -1;
    const dh = [];
    let at = nn, dir = 0, prev = -1;
    for (let guard = 0; at !== start; guard++) {
      if (guard > N) return -1;
      dir = this.searchStep(at, dir);
      if (dir !== prev) {
        dh.push(at);
        prev = dir;
      }
      at += ring[dir];
    }
    dh.push(start);
    const k = this.findRoute(dh[0], start);
    if (k >= 0) return k;
    return this.addRoute(new Uint32Array(dh));
  },

  searchStep(o, dir) {
    const dQ = this.bfsCost, ring = this.dirRing;
    const hK = dQ[o];
    if (hK - dQ[o + ring[dir]] !== 5 + ((dir & 1) << 1)) {
      for (let k = 0; k < 8; k++) {
        const g = (k + dir + 6) & 7;
        if (hK - dQ[o + ring[g]] === 5 + ((g & 1) << 1)) return g;
      }
    }
    return dir;
  },

  // ---- human boat commands -------------------------------------------------------

  // Boat with (pct+1)/1024 of the balance to water pixel `water`, landing on
  // the pixel next to it in direction dir (0 up, 1 right, 2 down, 3 left).
  boat(pct, water, dir, p = this.me) {
    if (!this.canAct(p)) return false;
    const W = this.W;
    const x = water % W, y = iV(water, W);
    if (!(0 < x && x < W - 1 && 0 < y && y < this.H - 1)) return false;
    if (!this.boatsAllowed(p)) return false;
    dir &= 7;
    if (!(dir < 4 && this.isShoreWater(water) && this.passable(water + this.dir4[dir]))) return false;
    pct = Math.max(0, Math.min(1023, pct | 0));
    if (!(this.quote(p, pct, 32) >= 0)) return false;
    if (!this.findBoatRoute(p, water, 1)) return false;
    this.boatType = dir;
    this.payQuote(p);
    this.launchBoat(p);
    return true;
  },

  // UI helper (nf.ng): water pixel and landing direction for a click on land
  // pixel `target`, searching up to `radius` pixels around it.
  boatSpot(target, p = this.me, radius = 32) {
    if (!this.boatsAllowed(p)) return null;
    const W = this.W, H = this.H;
    const skip = [];
    for (;;) {
      const nn = this.shoreNear(target, radius, skip, p);
      if (nn === -1) return null;
      const id = this.wid[nn];
      if (this.playerTouchesBody(p, id)) {
        const tx = target % W - nn % W, ty = iV(target, W) - iV(nn, W);
        let dir = Math.abs(tx) >= Math.abs(ty) ? 1 + 2 * (tx < 0) : 2 * (0 < ty);
        for (let i = 0; i < 4; i++) {
          if (this.hostileTo(nn + this.dir4[dir], p)) return { water: nn, dir };
          dir = (dir + 1) % 4;
        }
        return null;
      }
      skip.push(id);
      if (skip.length > W + H) return null;
    }
  },

  shoreNear(nh, nk, skip, p) {
    const W = this.W, H = this.H;
    const nu = nh % W, nw = iV(nh, W);
    const ny = W - 2, nz = H - 2;
    let best = -1;
    const pick = (o) => {
      if (o !== -1 && (best === -1 || this.dist2(o, nh) < this.dist2(best, nh))) best = o;
    };
    const ok = (c) => this.isShoreWater(c) && !skip.includes(this.wid[c]) && this.hostileAround(c, p);
    const row = (c4, cs, bp, step) => {
      if (bp < 1 || nz < bp) return -1;
      for (let i = 0; i <= cs; i++, c4 += step) if (ok(bp * W + c4)) return bp * W + c4;
      return -1;
    };
    const col = (bp, cs, c4, step) => {
      if (c4 < 1 || ny < c4) return -1;
      cs = Math.max(cs, 0);
      for (let i = 0; i <= cs; i++, bp += step) if (ok(bp * W + c4)) return bp * W + c4;
      return -1;
    };
    for (let g = 0; g < nk; g++) {
      const o1 = Math.max(nu - g, 1), o2 = Math.max(nw - g, 1);
      const o3 = Math.min(nu + g, ny), o4 = Math.min(nw + g, nz);
      pick(row(nu, o3 - nu, nw - g, 1));
      pick(row(nu - 1, nu - o1 - 1, nw - g, -1));
      pick(row(nu, o3 - nu, nw + g, 1));
      pick(row(nu - 1, nu - o1 - 1, nw + g, -1));
      pick(col(nw, o4 - nw - 1, nu - g, 1));
      pick(col(nw - 1, nw - o2 - 2, nu - g, -1));
      pick(col(nw, o4 - nw - 1, nu + g, 1));
      pick(col(nw - 1, nw - o2 - 2, nu + g, -1));
      if (best >= 0 && g * g >= this.dist2(best, nh)) return best;
    }
    return -1;
  },

  hostileAround(c, p) {
    const d = this.dir4;
    for (let g = 0; g < 4; g++) if (this.hostileTo(c + d[g], p)) return true;
    return false;
  },

  // Boat towards a land pixel, like clicking it in the game.
  boatTo(pct, target, p = this.me, radius = 32) {
    const s = this.boatSpot(target, p, radius);
    return s !== null && this.boat(pct, s.water, s.dir, p);
  },

  // Send a boat chasing enemy boat `id`.
  chase(pct, id, p = this.me) {
    if (!this.canAct(p)) return false;
    pct = Math.max(0, Math.min(1023, pct | 0));
    if (pct === 849) pct = 850;
    if (!(this.quote(p, pct, 32) >= 0)) return false;
    if (!this.chaseBoat(p, id, 0)) return false;
    this.payQuote(p);
    this.launchBoat(p);
    return true;
  },

  // Turn one of p's boats back home.
  recall(id, p = this.me) {
    if (!this.canAct(p)) return false;
    const b = this.playerBoat(p, id);
    if (b < 0 || !this.recallBoat(b)) return false;
    this.endChasesOf(b);
    return true;
  },
});
