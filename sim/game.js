// Single-player Territorial.io (2.16.65) game core: state, setup, tick order,
// economy, expansion/attack resolution, leaderboard, elimination and the
// human command set. Bots and boats live in bots.js and boats.js.
import { Rng } from './rng.js';
import { T_LAND, T_WATER, T_MOUNTAIN } from './map.js';

export const MAX_PLAYERS = 512;
export const NEUTRAL = MAX_PLAYERS;

// Pixel state codes for owned pixels (unowned pixels keep their terrain code).
export const P_INNER = 16;
export const P_BORDER = 17;
export const P_FRONT = 18;

const SPAWN_CELL = 10;
const SPAWN_BLOCK = 6;
const FRONT_CAP = 2048;
const HUMAN_START_BALANCE = 512;
const BOT_START_BALANCE = [60, 74, 112, 200, 256, 512, 512];

export const DIFFICULTY = {
  timerSpeed: [97, 94, 70, 40, 20, 0, 100],
  boatPct: [500, 450, 400, 300, 80, 50, 100],
  weakestPct: [0, 0, 5, 25, 50, 100, 0],
  boatLimit: [1, 2, 3, 4, 6, 8, 1],
  mountainPct: [500, 450, 400, 300, 80, 50, 100],
  interceptPermille: [100, 150, 250, 400, 600, 1000, 100],
};

export const iV = (a, b) => Math.floor((a + 0.5) / b);
const mj = (a, b) => (a >= 0 ? iV(a, b) : -iV(-a, b));

function mn(h, cs) {
  let a = iV(h + 1, 2);
  for (let i = 0; i < cs; i++) a = iV(a + iV(h, a), 2);
  return a;
}
const mo = (h, cs) => (h < 1 ? 0 : mn(h, cs));

const INTEREST_TABLE = new Uint16Array(MAX_PLAYERS);
for (let i = 0; i < MAX_PLAYERS; i++) INTEREST_TABLE[i] = 100 + mo(iV(25600 * i, MAX_PLAYERS - 4), 9);

export class Game {
  constructor(opts) {
    const map = opts.map;
    this.map = map;
    this.W = map.w;
    this.H = map.h;
    this.N = map.w * map.h;
    this.mountainMap = map.mountains;
    this.passableWater = opts.passableWater ?? 1;
    this.passableMountains = opts.passableMountains ?? 1;
    this.humans = opts.humans ?? 1;
    this.players = Math.max(opts.players ?? 512, this.humans);
    this.bots = this.players - this.humans;
    this.difficulty = opts.difficulty ?? 5;
    this.selectableSpawn = opts.selectableSpawn ? 1 : 0;
    this.me = 0;
    this.land = 0;
    this.t = 0;
    this.over = 0;
    this.winner = -1;
    this.rng = new Rng();

    const N = this.N;
    const W = this.W;
    this.px = new Uint8Array(N);
    this.own = new Uint16Array(N);
    this.wid = new Uint16Array(N);
    this.dir4 = new Int32Array([-W, 1, W, -1]);
    this.dir8 = new Int32Array([-W - 1, -W, -W + 1, -1, 1, W - 1, W, W + 1]);
    this.dirRing = new Int32Array([-W, 1 - W, 1, W + 1, W, W - 1, -1, -W - 1]);

    const P = MAX_PLAYERS;
    this.alive = new Uint8Array(P);
    this.state = new Uint8Array(P);
    this.x0 = new Uint16Array(P);
    this.y0 = new Uint16Array(P);
    this.x1 = new Uint16Array(P);
    this.y1 = new Uint16Array(P);
    this.terr = new Uint32Array(P);
    this.peak = new Uint32Array(P);
    this.bal = new Uint32Array(P);
    this.debt = new Uint16Array(P);
    this.landAttacks = new Uint16Array(P);
    this.big = new Uint8Array(P);
    this.front = new Array(P);
    this.border = new Array(P);
    this.coast = new Array(P);
    this.cliff = new Array(P);

    this.colR = new Uint8Array(P);
    this.colG = new Uint8Array(P);
    this.colB = new Uint8Array(P);
    this.colLow = new Uint8Array(P);
    this.borR = new Uint8Array(P);
    this.borG = new Uint8Array(P);
    this.borB = new Uint8Array(P);
    this.froR = new Uint8Array(P);
    this.froG = new Uint8Array(P);
    this.froB = new Uint8Array(P);
    this.humanColors = opts.humanColors || [opts.humanColor ?? 0];

    this.slotsHuman = this.humans < 16 ? 12 : 8;
    this.slotsBot = 4;
    const slots = this.slotBase(P);
    this.atkCount = new Uint8Array(P);
    this.atkTarget = new Uint16Array(slots);
    this.atkTroops = new Uint32Array(slots);
    this.atkFresh = new Uint8Array(slots);
    this.recentWar = new Uint8Array(P);

    this.schedCount = 0;
    this.schedList = new Uint16Array(P);
    this.schedWait = new Uint8Array(P);

    this.rank = new Uint16Array(P);
    this.rankOf = new Uint16Array(P);
    this.rankCount = P;

    this.aliveList = null;
    this.aliveCount = 0;

    this.cand = new Uint32Array(4 * FRONT_CAP);
    this.frontCopy = new Uint32Array(FRONT_CAP);
    this.mark = new Uint8Array(N);
    this.scratchList = new Uint16Array(16);
    this.scratchCount = 0;
    this.attackTroopsTmp = 0;
    this.attackFeeTmp = 0;
    this.targetTmp = 0;
    this.frontLenTmp = 0;
    this.leaderLand = 0;

    this.initBots();
    this.initBoats();
    this.setup(opts);
  }

  slotBase(p) {
    return p < this.humans ? this.slotsHuman * p : this.slotsHuman * this.humans + this.slotsBot * (p - this.humans);
  }

  // ---- pixel predicates -------------------------------------------------

  owned(p) {
    return this.px[p] >= P_INNER;
  }

  passable(p) {
    const v = this.px[p];
    return v >= P_INNER || v === T_LAND;
  }

  hostileTo(p, player) {
    const v = this.px[p];
    return v === T_LAND || (v >= P_INNER && this.own[p] !== player);
  }

  ownedBy(player, p) {
    return this.px[p] >= P_INNER && this.own[p] === player;
  }

  blocked(p) {
    const v = this.px[p];
    return v >= 3 && v < P_INNER;
  }

  bodyId(p) {
    const v = this.px[p];
    if (v < P_INNER) return this.wid[p];
    const o = this.own[p];
    if (v === P_INNER) return ((this.colR[o] >> 1) << 8) + this.colG[o];
    if (v === P_BORDER) return ((this.borR[o] >> 1) << 8) + this.borG[o];
    return ((this.froR[o] >> 1) << 8) + this.froG[o];
  }

  setInner(p, player) {
    this.px[p] = P_INNER;
    this.own[p] = player;
  }

  setBorder(p, player) {
    this.px[p] = P_BORDER;
    this.own[p] = player;
  }

  setFront(p, player) {
    this.px[p] = P_FRONT;
    this.own[p] = player;
  }

  setNeutral(p) {
    this.px[p] = T_LAND;
    this.own[p] = 8;
  }

  isBot(p) {
    return p >= this.humans || this.state[p] === 2;
  }

  isAlive(p) {
    return this.alive[p] !== 0 && this.state[p] !== 2;
  }

  // ---- setup -------------------------------------------------------------

  setup(opts) {
    const rng = this.rng;
    rng.seed(opts.spawnSeed ?? 0);
    const N = this.N;
    const type = this.map.type;
    for (let p = 0; p < N; p++) {
      const v = type[p];
      this.px[p] = v;
      this.wid[p] = v === T_WATER || v === T_MOUNTAIN ? this.map.id[p] : 0;
      this.own[p] = (v & 3) << 3;
      if (v === T_LAND) this.land++;
    }
    for (let p = 0; p < MAX_PLAYERS; p++) {
      this.front[p] = undefined;
      this.border[p] = undefined;
      this.coast[p] = undefined;
      this.cliff[p] = undefined;
    }
    this.setupColors();
    this.setupBots();
    rng.next();
    this.setupSpawns();
    for (let p = 0; p < this.humans; p++) this.bal[p] = HUMAN_START_BALANCE;
    for (let p = this.humans; p < this.players; p++) this.bal[p] = BOT_START_BALANCE[this.botDiff[p]];
    this.aliveCount = 0;
    for (let p = MAX_PLAYERS - 1; p >= 0; p--) if (this.alive[p] !== 0) this.aliveCount++;
    this.aliveList = new Uint16Array(this.aliveCount);
    let k = 0;
    for (let p = 0; p < MAX_PLAYERS; p++) if (this.alive[p] !== 0) this.aliveList[k++] = p;
    for (let p = MAX_PLAYERS - 1; p >= 0; p--) {
      this.rank[p] = p;
      this.rankOf[p] = p;
    }
    this.botList = new Uint16Array(MAX_PLAYERS);
    this.botCount = this.bots;
    for (let i = this.bots - 1; i >= 0; i--) this.botList[i] = this.humans + i;
    this.spawnPhase = this.selectableSpawn;
  }

  setupColors() {
    const rng = this.rng;
    const P = MAX_PLAYERS;
    const R = this.colR, G = this.colG, B = this.colB;
    for (let i = 0; i < this.humans; i++) {
      const c = this.humanColors[i] ?? 0;
      R[i] = 4 * (c >> 12);
      G[i] = 4 * ((c >> 6) & 63);
      B[i] = 4 * (c & 63);
    }
    for (let i = this.humans; i < P; i++) {
      R[i] = iV(64 * rng.next(), 32768) << 2;
      G[i] = iV(64 * rng.next(), 32768) << 2;
      B[i] = iV(64 * rng.next(), 32768) << 2;
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

  // ---- spawns ------------------------------------------------------------

  setupSpawns() {
    const W = this.W, H = this.H;
    this.spawnTiles = new Array(12);
    this.gridW = iV(W, SPAWN_CELL);
    this.gridH = iV(H, SPAWN_CELL);
    this.gridX0 = iV(W - SPAWN_CELL * this.gridW, 2);
    this.gridY0 = iV(H - SPAWN_CELL * this.gridH, 2);
    if (this.selectableSpawn) {
      for (let i = 0; i < this.humans; i++) {
        this.clearPlayer(i);
        this.alive[i] = 1;
      }
    }
    const dl = this.players;
    for (let p = dl; p < MAX_PLAYERS; p++) this.clearPlayer(p);
    for (let p = this.selectableSpawn ? this.humans : 0; p < dl; p++) {
      if (!this.findSpawnCell()) {
        for (let q = p; q < dl; q++) this.clearPlayer(q);
        return;
      }
      this.placeSpawn(p, this.gridX0 + this.cellX * SPAWN_CELL + iV(SPAWN_CELL, 2), this.gridY0 + this.cellY * SPAWN_CELL + iV(SPAWN_CELL, 2));
    }
  }

  clearPlayer(p) {
    this.alive[p] = 0;
    this.terr[p] = this.peak[p] = 0;
    this.front[p] = [];
    this.border[p] = [];
    this.coast[p] = [];
    this.cliff[p] = [];
    this.x0[p] = this.y0[p] = this.x1[p] = this.y1[p] = 0;
  }

  findSpawnCell() {
    const rng = this.rng;
    for (let i = 0; i < 8; i++) {
      this.cellX = iV(this.gridW * rng.next(), 32768);
      this.cellY = iV(this.gridH * rng.next(), 32768);
      if (this.cellFree()) return true;
    }
    const ex = iV(this.gridW * rng.next(), 32768);
    const ey = iV(this.gridH * rng.next(), 32768);
    for (let bN = 40; bN >= 1; bN--) {
      for (let fc = this.gridH - bN; fc >= 0; fc -= 40) {
        this.cellY = (fc + ey) % this.gridH;
        for (let fv = 40; fv >= 1; fv--) {
          for (let fb = this.gridW - fv; fb >= 0; fb -= 40) {
            this.cellX = (fb + ex) % this.gridW;
            if (this.cellFree()) return true;
          }
        }
      }
    }
    return false;
  }

  cellFree() {
    const gap = iV(SPAWN_CELL - SPAWN_BLOCK, 2);
    const y0 = this.gridY0 + this.cellY * SPAWN_CELL + gap;
    const x0 = this.gridX0 + this.cellX * SPAWN_CELL + gap;
    for (let y = y0 + SPAWN_BLOCK - 1; y >= y0; y--) {
      for (let x = x0 + SPAWN_BLOCK - 1; x >= x0; x--) {
        const p = y * this.W + x;
        if (!this.passable(p) || this.px[p] === P_BORDER) return false;
      }
    }
    return true;
  }

  placeSpawn(p, cx, cy) {
    this.clearPlayer(p);
    this.claimSpawn(p, cx - 2, cy - 2);
  }

  claimSpawn(pl, fb, fc) {
    const W = this.W;
    const tiles = this.spawnTiles;
    this.alive[pl] = 1;
    this.x0[pl] = fb + 10;
    this.y0[pl] = fc + 10;
    this.y1[pl] = this.x1[pl] = 0;
    for (let x = fb; x < fb + 4; x++) {
      for (let y = fc; y < fc + 4; y++) {
        if (!((fb < x && x < fb + 3) || (fc < y && y < fc + 3))) continue;
        const p = y * W + x;
        if (!this.passable(p)) continue;
        this.x0[pl] = Math.min(x, this.x0[pl]);
        this.x1[pl] = Math.max(x, this.x1[pl]);
        this.y0[pl] = Math.min(y, this.y0[pl]);
        this.y1[pl] = Math.max(y, this.y1[pl]);
        tiles[this.terr[pl]] = p;
        this.terr[pl]++;
        this.setInner(p, pl);
      }
    }
    this.peak[pl] = this.terr[pl];
    const d = this.dir4;
    for (let i = this.terr[pl] - 1; i >= 0; i--) {
      const p = tiles[i];
      if (this.hostileTo(p + d[0], pl) || this.hostileTo(p + d[1], pl) || this.hostileTo(p + d[2], pl) || this.hostileTo(p + d[3], pl)) {
        this.setBorder(p, pl);
        this.border[pl].push(p);
      } else if (this.px[p + d[3]] === T_WATER || this.px[p + d[2]] === T_WATER || this.px[p + d[1]] === T_WATER || this.px[p + d[0]] === T_WATER) {
        this.setBorder(p, pl);
        this.coast[pl].push(p);
      } else if (this.blocked(p + d[0]) || this.blocked(p + d[1]) || this.blocked(p + d[2]) || this.blocked(p + d[3])) {
        this.setBorder(p, pl);
        this.cliff[pl].push(p);
      }
    }
  }

  // Human spawn choice during the spawn phase (selectable spawn games). In
  // single player the first choice starts the game; with several humans the
  // phase lasts until endSpawnPhase().
  chooseSpawn(x, y, player = this.me, end = true) {
    if (!this.spawnPhase || !this.isAlive(player)) return false;
    if (!(x > 0 && x < this.W - 1 && y > 0 && y < this.H - 1)) return false;
    this.placeSpawnNear(player, x, y);
    if (end) this.endSpawnPhase();
    return true;
  }

  // End of the spawn phase (also what happens when the countdown runs out):
  // humans without land get a random spawn.
  endSpawnPhase() {
    if (!this.spawnPhase) return;
    this.spawnPhase = 0;
    for (let i = 0; i < this.humans; i++) {
      if (this.alive[i] !== 0 && this.terr[i] === 0) {
        if (this.findSpawnCell()) this.placeSpawn(i, this.gridX0 + this.cellX * SPAWN_CELL + iV(SPAWN_CELL, 2), this.gridY0 + this.cellY * SPAWN_CELL + iV(SPAWN_CELL, 2));
        else this.clearPlayer(i);
      }
    }
  }

  placeSpawnNear(pl, cx, cy) {
    const W = this.W, H = this.H;
    for (let r = 0; r < 20; r++) {
      for (let fb = cx + r; fb >= cx - r; fb--) {
        for (let fc = cy + r; fc >= cy - r; fc--) {
          if (!(fb === cx + r || fb === cx - r || fc === cy + r || fc === cy - r)) continue;
          if (!(fb > 3 && fb < W - 5 && fc > 3 && fc < H - 5)) continue;
          if (!this.passable(fc * W + fb) || !this.spawnAreaFree(pl, fb + 3, fc + 3)) continue;
          if (this.terr[pl] > 0) {
            for (let x = this.x1[pl]; x >= this.x0[pl]; x--) {
              for (let y = this.y1[pl]; y >= this.y0[pl]; y--) {
                const p = y * W + x;
                if (this.ownedBy(pl, p)) {
                  this.setNeutral(p);
                  this.terr[pl]--;
                }
              }
            }
            this.clearPlayer(pl);
          }
          this.claimSpawn(pl, fb - 1, fc - 1);
          return true;
        }
      }
    }
    return false;
  }

  spawnAreaFree(pl, fb, fc) {
    for (let y = fc; y > fc - 6; y--) {
      for (let x = fb; x > fb - 6; x--) {
        const p = y * this.W + x;
        if (this.px[p] === P_BORDER && this.own[p] !== pl) return false;
      }
    }
    return true;
  }

  // ---- tick ----------------------------------------------------------------

  tick() {
    if (this.over || this.spawnPhase) return;
    this.botsTick();
    this.economyTick();
    this.expandTick();
    this.endgameSpeedTick();
    this.scanTick();
    this.boatsTick();
    this.aliveTick();
    this.leaderboardTick();
    this.victoryTick();
    this.t++;
  }

  // ---- economy -------------------------------------------------------------

  interestRate(p) {
    if (p < this.humans && this.state[p] === 2) return 0;
    let n1 = INTEREST_TABLE[iV((MAX_PLAYERS - 1) * this.terr[p], this.land)];
    if (this.t < 1920) n1 = Math.max(iV(100 * (13440 - 6 * this.t), 1920), n1);
    const cap = this.softCap(p);
    if (this.bal[p] > cap) n1 -= iV(2 * n1 * (this.bal[p] - cap), cap);
    return Math.min(Math.max(n1, 0), 700);
  }

  softCap(p) {
    return Math.min(100 * this.terr[p], 1e9);
  }

  addBalance(p, v) {
    const lG = this.bal[p];
    v = Math.min(v, this.terr[p] * 150 - lG);
    v = Math.min(v, 1.5e9 - lG);
    v = Math.max(v, 0);
    this.bal[p] += v;
    if (this.debt[p]) {
      const m = Math.min(this.debt[p], this.bal[p]);
      this.debt[p] -= m;
      this.bal[p] -= m;
    }
    return v;
  }

  takeBalance(p, v) {
    const have = this.bal[p];
    if (v <= have) {
      this.bal[p] -= v;
    } else {
      this.bal[p] = 0;
      const d = this.debt[p] + 5 * ((v - have) >> 2);
      this.debt[p] = d <= 5e4 ? d : 5e4;
    }
    return v;
  }

  economyTick() {
    if (this.t % 10 !== 9) return;
    const list = this.aliveList, bal = this.bal;
    for (let i = this.aliveCount - 1; i >= 0; i--) {
      const p = list[i];
      this.addBalance(p, Math.max(iV(this.interestRate(p) * bal[p], 1e4), 1));
    }
    if (this.t % 100 === 99) {
      for (let i = this.aliveCount - 1; i >= 0; i--) {
        const p = list[i];
        this.addBalance(p, iV(32 * this.terr[p], 32));
      }
    }
  }

  // ---- attack slots ---------------------------------------------------------

  hasAttack(p, target) {
    const b = this.slotBase(p);
    for (let i = this.atkCount[p] - 1; i >= 0; i--) if (this.atkTarget[b + i] === target) return true;
    return false;
  }

  hasFreeSlot(p) {
    return this.atkCount[p] < (p < this.humans ? this.slotsHuman : this.slotsBot);
  }

  attackTroopsOn(p, target) {
    const b = this.slotBase(p);
    for (let i = this.atkCount[p] - 1; i >= 0; i--) if (this.atkTarget[b + i] === target) return this.atkTroops[b + i];
    return 0;
  }

  totalAttackTroops(p) {
    const b = this.slotBase(p);
    let s = 0;
    for (let i = this.atkCount[p] - 1; i >= 0; i--) s += this.atkTroops[b + i];
    return s;
  }

  setAttackTroopsOn(p, target, v) {
    const b = this.slotBase(p);
    for (let i = this.atkCount[p] - 1; i >= 0; i--) if (this.atkTarget[b + i] === target) this.atkTroops[b + i] = v;
  }

  addAttack(p, troops, target) {
    this.recentWar[p] = 8;
    if (target < MAX_PLAYERS) this.recentWar[target] = 8;
    const b = this.slotBase(p);
    for (let i = this.atkCount[p] - 1; i >= 0; i--) {
      if (this.atkTarget[b + i] === target) {
        const v = this.atkTroops[b + i] + troops;
        this.atkTroops[b + i] = v > 1.5e9 ? 1.5e9 : v;
        return;
      }
    }
    const k = b + this.atkCount[p];
    this.atkTarget[k] = target;
    this.atkTroops[k] = troops;
    this.atkFresh[k] = 1;
    this.atkCount[p]++;
  }

  removeAttack(p, idx) {
    if (this.atkCount[p] === 0) return;
    const b = this.slotBase(p);
    this.atkCount[p]--;
    for (let i = idx; i < this.atkCount[p]; i++) {
      this.atkTarget[b + i] = this.atkTarget[b + i + 1];
      this.atkTroops[b + i] = this.atkTroops[b + i + 1];
      this.atkFresh[b + i] = this.atkFresh[b + i + 1];
    }
  }

  cancelAttack(p, target) {
    const v = this.attackTroopsOn(p, target);
    this.setAttackTroopsOn(p, target, 0);
    this.addBalance(p, v);
  }

  redirectAttackToNeutral(p, target) {
    const b = this.slotBase(p);
    let idx = this.atkCount[p];
    for (let i = this.atkCount[p] - 1; i >= 0; i--) {
      if (this.atkTarget[b + i] === target) {
        idx = i;
        break;
      }
    }
    if (idx !== this.atkCount[p]) {
      const v = this.atkTroops[b + idx];
      this.removeAttack(p, idx);
      this.addAttack(p, v, NEUTRAL);
    }
  }

  attackersOf(target) {
    const out = [];
    for (let i = this.aliveCount - 1; i >= 0; i--) {
      const p = this.aliveList[i];
      const b = this.slotBase(p);
      for (let k = this.atkCount[p] - 1; k >= 0; k--) {
        if (this.atkTarget[b + k] === target) {
          out.push(p);
          break;
        }
      }
    }
    return out;
  }

  // ---- expansion scheduler --------------------------------------------------

  schedule(p, fromBoat) {
    for (let i = this.schedCount - 1; i >= 0; i--) if (this.schedList[i] === p) return;
    this.schedList[this.schedCount++] = p;
    this.schedWait[p] = fromBoat ? 2 : 64;
  }

  unschedule(p) {
    for (let i = this.schedCount - 1; i >= 0; i--) {
      if (this.schedList[i] === p) {
        this.schedCount--;
        for (let k = i; k < this.schedCount; k++) this.schedList[k] = this.schedList[k + 1];
        return;
      }
    }
  }

  resetWait(p) {
    if (this.schedWait[p] === 64) {
      this.schedWait[p] = 6;
    } else {
      const t = this.terr[p];
      this.schedWait[p] = t < 1e3 ? 3 : t < 1e4 ? 2 : t < 6e4 ? 1 : 0;
    }
  }

  expandTick() {
    for (let i = this.schedCount - 1; i >= 0; i--) {
      const p = this.schedList[i];
      if (this.schedWait[p] === 64) {
        this.resetWait(p);
      } else if (this.schedWait[p]-- === 0) {
        this.resetWait(p);
        this.expand(p);
      }
    }
    const lead = this.terr[this.rank[0]];
    if (lead >= 16e4) {
      this.expandBig(16e4);
      if (this.terr[this.rank[0]] >= 3e5) this.expandBig(3e5);
    }
  }

  expandBig(min) {
    for (let i = this.schedCount - 1; i >= 0; i--) {
      const p = this.schedList[i];
      if (this.schedWait[p] === 0 && this.terr[p] >= min) this.expand(p);
    }
  }

  // One expansion step of every attack of player p.
  expand(p) {
    const S = this.front[p];
    const cs = Math.min(S.length, FRONT_CAP);
    const fc = this.frontCopy;
    let n = 0;
    for (let i = cs - 1; i >= 0; i--) fc[n++] = S[i];
    this.frontCopyLen = n;
    for (let i = S.length - 1; i >= 0; i--) if (this.passable(S[i])) this.setBorder(S[i], p);
    this.front[p] = [];
    this.conquered = false;
    for (let a = this.atkCount[p] - 1; a >= 0; a--) this.expandAttack(p, a);
    if (this.conquered) {
      this.refreshFront(p);
      this.refreshBorder(p);
    }
  }

  expandAttack(p, a) {
    const k = this.slotBase(p) + a;
    const target = this.atkTarget[k];
    let troops = this.atkTroops[k];
    const fresh = this.atkFresh[k];
    const cand = this.cand, mark = this.mark, fc = this.frontCopy, d = this.dir4;
    const px = this.px, own = this.own;
    const fn = this.frontCopyLen;
    let cnt = 0;
    if (target === NEUTRAL) {
      for (let g = 3; g >= 0; g--) {
        const dd = d[g];
        for (let i = fn - 1; i >= 0; i--) {
          const c = fc[i] + dd;
          if (mark[c] === 0 && px[c] === T_LAND) {
            mark[c] = 1;
            cand[cnt++] = c;
          }
        }
      }
    } else {
      for (let g = 3; g >= 0; g--) {
        const dd = d[g];
        for (let i = fn - 1; i >= 0; i--) {
          const c = fc[i] + dd;
          if (mark[c] === 0 && px[c] >= P_INNER && own[c] === target) {
            mark[c] = 1;
            cand[cnt++] = c;
          }
        }
      }
    }
    if (cnt !== 0) {
      for (let i = cnt - 1; i >= 0; i--) mark[cand[i]] = 0;
      let per = iV(troops, cnt);
      let ok = true;
      if (!(per > 2)) {
        if (!fresh) ok = false;
        else {
          troops += this.takeBalance(p, cnt * 3 - troops);
          per = iV(troops, cnt);
        }
      }
      if (ok) {
        let win;
        if (target === NEUTRAL) {
          troops -= cnt * 2;
          win = true;
        } else {
          const base = cnt * 2;
          const def = iV(cnt * this.bal[target], 1 + iV(10 * this.terr[target], 16));
          const counter = this.attackTroopsOn(target, p);
          const cost = base + 2 * def + counter;
          let avail = per * cnt;
          if (cost < avail) {
            troops -= cost;
            this.damage(p, target, cost - base, counter);
            win = true;
          } else if (fresh && counter === 0) {
            troops -= avail;
            avail += this.takeBalance(p, cost - avail + 1);
            this.damage(p, target, avail - base, 0);
            win = true;
          } else {
            troops -= avail;
            this.damage(p, target, avail - base, counter);
            win = false;
          }
        }
        if (win) {
          this.conquered = true;
          this.atkTroops[k] = Math.max(troops, 0);
          this.atkFresh[k] = 0;
          this.terr[p] += cnt;
          let x0 = this.x0[p], y0 = this.y0[p], x1 = this.x1[p], y1 = this.y1[p];
          const W = this.W;
          for (let i = cnt - 1; i >= 0; i--) {
            const c = cand[i];
            const x = c % W, y = Math.floor(c / W);
            if (x < x0) x0 = x;
            if (y < y0) y0 = y;
            if (x > x1) x1 = x;
            if (y > y1) y1 = y;
          }
          this.x0[p] = x0;
          this.y0[p] = y0;
          this.x1[p] = x1;
          this.y1[p] = y1;
          const S = this.front[p], B = this.border[p];
          for (let i = cnt - 1; i >= 0; i--) {
            const c = cand[i];
            S.push(c);
            B.push(c);
            px[c] = P_BORDER;
            own[c] = p;
          }
          if (target !== NEUTRAL) this.loseTiles(target, cand, cnt);
          return;
        }
      }
    }
    this.endAttack(p, a, troops);
  }

  damage(p, target, dmg, counter) {
    if (counter > 0) {
      if (dmg <= counter) {
        this.setAttackTroopsOn(target, p, counter - dmg);
        return;
      }
      this.setAttackTroopsOn(target, p, 0);
      dmg -= counter;
    }
    dmg = iV(dmg, 2);
    dmg = Math.min(this.bal[target], dmg);
    this.bal[target] -= dmg;
  }

  endAttack(p, a, troops) {
    if (this.atkCount[p] === 1) this.unschedule(p);
    this.addBalance(p, troops);
    this.removeAttack(p, a);
  }

  // Border bookkeeping of a player that just lost cand[0..cnt) tiles.
  loseTiles(q, cand, cnt) {
    this.terr[q] -= cnt;
    this.keepOwned(q, this.border[q]);
    this.keepOwned(q, this.coast[q]);
    if (this.mountainMap) this.keepOwned(q, this.cliff[q]);
    const S = this.front[q];
    for (let i = S.length - 1; i >= 0; i--) {
      if (!this.ownedBy(q, S[i]) && this.passable(S[i])) {
        S[i] = S[S.length - 1];
        S.pop();
      }
    }
    this.promoteToBorder(q, this.coast[q]);
    this.promoteToBorder(q, this.cliff[q]);
    const d = this.dir4, B = this.border[q], px = this.px, own = this.own;
    for (let i = cnt - 1; i >= 0; i--) {
      for (let g = 3; g >= 0; g--) {
        const c = cand[i] + d[g];
        if (own[c] === q && px[c] === P_INNER) {
          B.push(c);
          px[c] = P_BORDER;
        }
      }
    }
    this.shrinkBox(q);
  }

  keepOwned(q, list) {
    for (let i = list.length - 1; i >= 0; i--) {
      if (!this.ownedBy(q, list[i])) {
        list[i] = list[list.length - 1];
        list.pop();
      }
    }
  }

  promoteToBorder(q, list) {
    const d = this.dir4;
    for (let i = list.length - 1; i >= 0; i--) {
      for (let g = 3; g >= 0; g--) {
        if (this.hostileTo(list[i] + d[g], q)) {
          this.border[q].push(list[i]);
          list[i] = list[list.length - 1];
          list.pop();
          break;
        }
      }
    }
  }

  shrinkBox(q) {
    const W = this.W;
    outer: while (this.y0[q] < this.y1[q]) {
      for (let x = this.x1[q]; x >= this.x0[q]; x--) if (this.ownedBy(q, this.y0[q] * W + x)) break outer;
      this.y0[q]++;
    }
    outer: while (this.y0[q] < this.y1[q]) {
      for (let x = this.x1[q]; x >= this.x0[q]; x--) if (this.ownedBy(q, this.y1[q] * W + x)) break outer;
      this.y1[q]--;
    }
    outer: while (this.x0[q] < this.x1[q]) {
      for (let y = this.y1[q]; y >= this.y0[q]; y--) if (this.ownedBy(q, y * W + this.x0[q])) break outer;
      this.x0[q]++;
    }
    outer: while (this.x0[q] < this.x1[q]) {
      for (let y = this.y1[q]; y >= this.y0[q]; y--) if (this.ownedBy(q, y * W + this.x1[q])) break outer;
      this.x1[q]--;
    }
  }

  refreshFront(p) {
    const S = this.front[p], d = this.dir4;
    let cs = S.length;
    outer: for (let i = cs - 1; i >= 0; i--) {
      for (let g = 3; g >= 0; g--) {
        const c = S[i] + d[g];
        if (this.hostileTo(c, p)) {
          this.setFront(S[i], p);
          continue outer;
        }
      }
      S[i] = S[cs - 1];
      S.pop();
      cs--;
    }
  }

  refreshBorder(p) {
    const B = this.border[p], d = this.dir4, px = this.px;
    let cs = B.length;
    outer: for (let i = cs - 1; i >= 0; i--) {
      let water = false, wall = false;
      for (let g = 3; g >= 0; g--) {
        const c = B[i] + d[g];
        if (this.hostileTo(c, p)) continue outer;
        const v = px[c];
        water = water || v === T_WATER;
        wall = wall || (v >= 3 && v < P_INNER);
      }
      if (water) this.coast[p].push(B[i]);
      else if (wall) this.cliff[p].push(B[i]);
      else this.setInner(B[i], p);
      B[i] = B[cs - 1];
      B.pop();
      cs--;
    }
  }

  // ---- attack targeting helpers (used by human commands and bots) ----------

  markFront(p, from) {
    const S = this.front[p];
    for (let i = S.length - 1; i >= from; i--) this.setFront(S[i], p);
  }

  addFrontAgainst(p, target) {
    const B = this.border[p], S = this.front[p], d = this.dir4, px = this.px, own = this.own;
    for (let i = B.length - 1; i >= 0; i--) {
      const b = B[i];
      if (px[b] !== P_BORDER) continue;
      for (let g = 3; g >= 0; g--) {
        const c = b + d[g];
        if (px[c] >= P_INNER && own[c] === target) {
          S.push(b);
          break;
        }
      }
    }
  }

  addFrontNeutral(p) {
    const B = this.border[p], S = this.front[p], d = this.dir4, px = this.px;
    for (let i = B.length - 1; i >= 0; i--) {
      const b = B[i];
      if (px[b] !== P_BORDER) continue;
      for (let g = 3; g >= 0; g--) {
        if (px[b + d[g]] === T_LAND) {
          S.push(b);
          break;
        }
      }
    }
  }

  // Bot-style commit: fee of 12/1024 of the balance, folded into the troops
  // when sending at least half of the balance.
  commitAttack(p, target, from, troops) {
    const fee = iV(12 * this.bal[p], 1024);
    troops -= troops >= iV(this.bal[p], 2) ? fee : 0;
    this.markFront(p, from);
    this.addAttack(p, troops, target);
    this.bal[p] -= troops + fee;
    this.schedule(p, false);
  }

  // dF[0]/dF[1] of the game: troops and fee for sending (pct+1)/1024.
  quote(p, pct, feeK) {
    const lG = this.bal[p];
    let troops = iV(lG * (pct + 1), 1024);
    const fee = iV(feeK * lG, 1024);
    troops = Math.min(troops, lG - fee);
    this.attackTroopsTmp = troops;
    this.attackFeeTmp = fee;
    return troops;
  }

  payQuote(p) {
    this.bal[p] -= this.attackTroopsTmp + this.attackFeeTmp;
  }

  // ---- human commands -------------------------------------------------------

  canAct(p) {
    return !this.over && !this.spawnPhase && this.isAlive(p);
  }

  // Land attack with (pct+1)/1024 of the balance on target (NEUTRAL = unowned land).
  attack(pct, target, p = this.me) {
    if (!this.canAct(p) || p === target) return false;
    pct = Math.max(0, Math.min(1023, pct | 0));
    if (!(this.quote(p, pct, 12) >= 0)) return false;
    target = Math.min(target, NEUTRAL);
    if (target < NEUTRAL && this.alive[target] === 0) target = NEUTRAL;
    const already = this.hasAttack(p, target);
    if (!already && !this.hasFreeSlot(p)) return false;
    this.landAttacks[p]++;
    const before = this.front[p].length;
    if (target === NEUTRAL) this.addFrontNeutral(p);
    else this.addFrontAgainst(p, target);
    const after = this.front[p].length;
    if (before === 0 && after === 0) return false;
    if (!already && before === after) return false;
    this.payQuote(p);
    this.markFront(p, before);
    this.addAttack(p, this.attackTroopsTmp, target);
    this.schedule(p, false);
    return true;
  }

  // Retreat: troops of the attack on target return to the balance.
  retreat(target, p = this.me) {
    if (!this.canAct(p)) return false;
    target = Math.min(target, NEUTRAL);
    if (!this.hasAttack(p, target)) return false;
    this.cancelAttack(p, target);
    return true;
  }

  // ---- alive list, elimination ------------------------------------------------

  aliveTick() {
    const list = this.aliveList;
    for (let i = this.aliveCount - 1; i >= 0; i--) {
      const p = list[i];
      const bx = this.terr[p], jP = this.peak[p];
      if (bx <= iV(jP, 4)) this.collapse(p);
      else if (jP <= bx) {
        this.peak[p] = bx;
        if (bx >= 250) this.big[p] = 1;
      } else this.peak[p] = jP - Math.max(1, iV(jP - bx, 1e3));
    }
    let n = this.aliveCount;
    for (let i = n - 1; i >= 0; i--) if (this.alive[list[i]] === 0) list[i] = list[--n];
    this.aliveCount = n;
  }

  collapse(p) {
    const bx = this.terr[p] + this.peak[p];
    if (this.boatCount[p]) {
      if (bx) {
        const atk = this.attackersOf(p);
        for (let i = atk.length - 1; i >= 0; i--) this.redirectAttackToNeutral(atk[i], p);
        this.clearTerritory(p);
        this.unschedule(p);
        this.atkCount[p] = 0;
        this.bal[p] = 0;
        this.debt[p] = 0;
        this.peak[p] = 0;
        this.front[p] = [];
        this.border[p] = [];
        this.coast[p] = [];
        this.cliff[p] = [];
      }
    } else if (!(!bx && this.front[p].length)) {
      this.eliminate(p);
    }
  }

  eliminate(p) {
    const atk = this.attackersOf(p);
    for (let i = atk.length - 1; i >= 0; i--) this.redirectAttackToNeutral(atk[i], p);
    this.clearTerritory(p);
    this.bal[p] = 0;
    this.debt[p] = 0;
    this.alive[p] = 0;
    this.front[p] = null;
    this.border[p] = null;
    this.coast[p] = null;
    this.cliff[p] = null;
    this.unschedule(p);
    this.atkCount[p] = 0;
    this.removeBoatsOf(p);
  }

  clearTerritory(p) {
    const W = this.W;
    if (this.terr[p]) {
      this.terr[p] = 0;
      for (let x = this.x1[p]; x >= this.x0[p]; x--) {
        for (let y = this.y1[p]; y >= this.y0[p]; y--) {
          const c = y * W + x;
          if (this.ownedBy(p, c)) this.setNeutral(c);
        }
      }
    }
    this.x1[p] = this.y1[p] = 0;
    this.x0[p] = this.y0[p] = Math.max(this.W, this.H);
  }

  // ---- leaderboard, end of game -----------------------------------------------

  leaderboardTick() {
    const R = this.rank, S = this.rankOf;
    for (let i = this.rankCount - 1; i >= 0; i--) {
      if (this.alive[R[i]] === 0) {
        const c = R[i];
        this.rankCount--;
        for (let k = i; k < this.rankCount; k++) {
          R[k] = R[k + 1];
          S[R[k]] = k;
        }
        R[this.rankCount] = c;
        S[c] = this.rankCount;
      }
    }
    const terr = this.terr;
    for (let i = 0, e = this.rankCount - 1; i < e; i++) {
      if (terr[R[i]] < terr[R[i + 1]]) {
        const a = R[i];
        R[i] = R[i + 1];
        R[i + 1] = a;
        S[R[i]] = i;
        S[R[i + 1]] = i + 1;
      }
    }
  }

  victoryTick() {
    this.leaderLand = this.terr[this.rank[0]];
    if (this.leaderLand < this.land) return;
    for (let i = this.aliveCount - 1; i >= 0; i--) if (this.front[this.aliveList[i]].length > 0) return;
    if (this.enemyBoatsOf(this.rank[0]) > 0) return;
    this.over = 1;
    this.winner = this.rank[0];
  }

  leaderHas(pct) {
    return this.terr[this.rank[0]] >= iV(pct * this.land, 100);
  }
}
