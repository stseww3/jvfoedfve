// ============================================================================
// UNIFIED TEAM SPAWN COORDINATOR BACKEND (tsb/squad/spawn-coordinator.mjs)
// ============================================================================
// Centralizes spawn-phase decision making for all 5~10 squad bots in Team Mode:
//   1. Single source of truth for map terrain (W, H, landMask) & live human positions.
//   2. Carves out an exclusive opening growth zone (R_boss_excl) around Boss [NPL] npl
//      so guard bots NEVER steal Boss's early neutral land or AI bots.
//   3. Deploys a role-based team formation:
//      - 1~2 FLANK_GUARD bots on Boss's outer ring [R_boss_excl, R_flank_max],
//        preferring sectors that shield Boss from nearby enemy humans.
//      - (K - K_flank) ECO_BANK bots across the largest disjoint Voronoi basins
//        of the map via Sequential Geodesic BFS Distance-Field Injection.
//   4. Assigns the K target coordinates to the K active bots via exact O(K * 2^K)
//      bitmask DP minimum-displacement matching to prevent countdown jitter.
// ============================================================================

import http from 'node:http';

export const T_LAND = 1;
export const T_WATER = 2;
export const T_EDGE = 3;
export const T_MOUNTAIN = 5;

const KIND_NONE = 0;
const KIND_ENEMY = 1;
const KIND_RANDOM_ALLY = 2;
const KIND_BOSS = 3;
const KIND_SQUAD = 4;

const SQUAD_SHORT_NAMES = new Set([
  'mishi', 'matzz', 'kiholma', 'leo_99', 'racoon',
  'zexos', 'talon', 'vortex', 'kronos', 'nexus',
]);

export function normalizePlayerName(raw) {
  return String(raw ?? '').trim();
}

export function stripClanTag(raw) {
  return normalizePlayerName(raw).replace(/\[[^\]]*\]/g, '').trim().toLowerCase();
}

export function isSquadBotName(raw) {
  const s = stripClanTag(raw);
  return SQUAD_SHORT_NAMES.has(s);
}

export function isBossNplName(raw) {
  const norm = normalizePlayerName(raw);
  if (!norm) return false;
  if (isSquadBotName(norm)) return false;
  const s = stripClanTag(norm);
  const low = norm.toLowerCase();
  return s === 'npl' || s.includes('npl') || low === '[npl]npl';
}

function clamp(v, lo, hi) {
  return v < lo ? lo : v > hi ? hi : v;
}

export class TeamSpawnCoordinator {
  constructor(opts = {}) {
    this.port = opts.port ?? 8198;
    this.host = opts.host ?? '127.0.0.1';
    this.matchKey = null;
    this.W = 0;
    this.H = 0;
    this.N = 0;
    this.land = 0;
    this.landMask = null; // Uint8Array(N): 1 if passable land, 0 otherwise
    this.waterMask = null; // Uint8Array(N): 1 if water, 0 otherwise
    this.dir4 = null;

    // Scratch buffers allocated per map size N
    this.dComp = null;      // Int32Array(N): geodesic land distance to nearest competitor/chosen slot
    this.whoKind = null;    // Uint8Array(N): KIND_* of nearest source in dComp
    this.whoId = null;      // Int16Array(N): player id of nearest source in dComp
    this.dBoss = null;      // Int32Array(N): geodesic land distance from Boss npl
    this.dScratch = null;   // Int32Array(N): local BFS distance scratch (kept at -1)
    this.bfsQ = null;       // Int32Array(N): BFS queue

    // Live match state
    this.lastPlan = null;
    this.lastSolveMs = 0;
    this.lastSolvedAt = 0;
    this.solveCount = 0;
    this.prevBotTargets = new Map(); // slot -> { x, y, role }
    this.server = null;
  }

  ensureBuffers(W, H) {
    const N = W * H;
    if (this.W === W && this.H === H && this.N === N && this.dComp) return;
    this.W = W;
    this.H = H;
    this.N = N;
    this.dir4 = new Int32Array([-W, 1, W, -1]);
    this.dComp = new Int32Array(N);
    this.whoKind = new Uint8Array(N);
    this.whoId = new Int16Array(N);
    this.dBoss = new Int32Array(N);
    this.dScratch = new Int32Array(N).fill(-1);
    this.bfsQ = new Int32Array(N);
  }

  /**
   * Set or update the current match's static terrain map.
   * Accepts either:
   *   - mapType: Uint8Array(W*H) where 1 === T_LAND, 2 === T_WATER
   *   - packedLandB64: base64-encoded bitpack of landMask (1 bit per pixel)
   */
  setMap({ matchKey, W, H, land, mapType, packedLandB64 }) {
    if (!W || !H || W <= 0 || H <= 0) return false;
    const N = W * H;
    const key = matchKey || `${W}x${H}_${land || 0}`;
    if (this.matchKey === key && this.landMask && this.N === N) {
      return true;
    }
    this.ensureBuffers(W, H);
    this.matchKey = key;
    this.landMask = new Uint8Array(N);
    this.waterMask = new Uint8Array(N);

    let landCount = 0;
    if (mapType && mapType.length === N) {
      for (let i = 0; i < N; i++) {
        const t = mapType[i];
        if (t === T_LAND || t >= 16) {
          this.landMask[i] = 1;
          landCount++;
        } else if (t === T_WATER) {
          this.waterMask[i] = 1;
        }
      }
    } else if (typeof packedLandB64 === 'string' && packedLandB64.length > 0) {
      const buf = Buffer.from(packedLandB64, 'base64');
      for (let i = 0; i < N; i++) {
        const bit = (buf[i >> 3] >> (i & 7)) & 1;
        if (bit) {
          this.landMask[i] = 1;
          landCount++;
        }
      }
    } else {
      return false;
    }

    this.land = land || landCount;
    this.prevBotTargets.clear();
    this.lastPlan = null;
    this.solveCount = 0;
    return true;
  }

  /**
   * Find nearest valid passable land pixel to (x, y) within radius maxR.
   */
  snapToLand(x, y, maxR = 24) {
    const { W, H, landMask } = this;
    x = clamp(Math.round(x), 2, W - 3);
    y = clamp(Math.round(y), 2, H - 3);
    const c0 = y * W + x;
    if (landMask[c0]) return c0;
    for (let r = 1; r <= maxR; r++) {
      const yMin = Math.max(2, y - r), yMax = Math.min(H - 3, y + r);
      const xMin = Math.max(2, x - r), xMax = Math.min(W - 3, x + r);
      for (let yy = yMin; yy <= yMax; yy++) {
        for (let xx = xMin; xx <= xMax; xx++) {
          if (Math.abs(xx - x) !== r && Math.abs(yy - y) !== r) continue;
          const c = yy * W + xx;
          if (landMask[c]) return c;
        }
      }
    }
    return -1;
  }

  /**
   * Compute multi-source 4-neighbour geodesic land distance field dComp[N]
   * from enemies, random teammates, and Boss npl.
   */
  buildInitialDistanceFields(enemies, randomAllies, boss, botSpawnPoints = []) {
    const { W, H, N, landMask, dir4, dComp, whoKind, whoId, dBoss, bfsQ } = this;
    const INF = 1_000_000;
    dComp.fill(INF);
    whoKind.fill(KIND_NONE);
    whoId.fill(-1);

    // 1. If Boss is present and placed on the map, compute exact geodesic dBoss[N]
    dBoss.fill(-1);
    if (boss && boss.x >= 0 && boss.y >= 0) {
      const bc = this.snapToLand(boss.x, boss.y, 16);
      if (bc >= 0) {
        let qh = 0, qt = 0;
        dBoss[bc] = 0;
        bfsQ[qt++] = bc;
        while (qh < qt) {
          const c = bfsQ[qh++];
          const dc = dBoss[c] + 1;
          for (let k = 0; k < 4; k++) {
            const n = c + dir4[k];
            if (n >= 0 && n < N && landMask[n] && dBoss[n] < 0) {
              dBoss[n] = dc;
              bfsQ[qt++] = n;
            }
          }
        }
      }
    }

    // 2. Seed multi-source bucket/offset BFS for dComp:
    //    - Enemy humans start at dist = 0 (strongest rival)
    //    - Boss starts at dist = 0 (we must never steal Boss's Voronoi land)
    //    - Random allies start at dist = 12 (compete for neutral land, but non-hostile)
    const delayedSeeds = [];
    let qh = 0, qt = 0;

    for (const e of enemies) {
      const c = this.snapToLand(e.x, e.y, 12);
      if (c >= 0 && dComp[c] > 0) {
        dComp[c] = 0;
        whoKind[c] = KIND_ENEMY;
        whoId[c] = e.id;
        bfsQ[qt++] = c;
      }
    }

    if (boss && boss.x >= 0 && boss.y >= 0) {
      const bc = this.snapToLand(boss.x, boss.y, 12);
      if (bc >= 0 && dComp[bc] > 0) {
        dComp[bc] = 0;
        whoKind[bc] = KIND_BOSS;
        whoId[bc] = boss.id ?? 999;
        bfsQ[qt++] = bc;
      }
    }

    for (const a of randomAllies) {
      const c = this.snapToLand(a.x, a.y, 12);
      if (c >= 0) {
        delayedSeeds.push({ c, delay: 12, kind: KIND_RANDOM_ALLY, id: a.id });
      }
    }

    // If no humans have placed a spawn marker yet, seed lightly from AI bots or map border
    if (qt === 0 && delayedSeeds.length === 0 && botSpawnPoints.length > 0) {
      for (const b of botSpawnPoints) {
        const c = this.snapToLand(b.x, b.y, 6);
        if (c >= 0 && dComp[c] > 0) {
          dComp[c] = 0;
          whoKind[c] = KIND_NONE;
          whoId[c] = -1;
          bfsQ[qt++] = c;
        }
      }
    }

    delayedSeeds.sort((a, b) => a.delay - b.delay);
    let dsIdx = 0;

    while (qh < qt || dsIdx < delayedSeeds.length) {
      if (qh >= qt && dsIdx < delayedSeeds.length) {
        const s = delayedSeeds[dsIdx++];
        if (s.delay < dComp[s.c]) {
          dComp[s.c] = s.delay;
          whoKind[s.c] = s.kind;
          whoId[s.c] = s.id;
          bfsQ[qt++] = s.c;
        }
        continue;
      }
      const curDist = dComp[bfsQ[qh]];
      while (dsIdx < delayedSeeds.length && delayedSeeds[dsIdx].delay <= curDist) {
        const s = delayedSeeds[dsIdx++];
        if (s.delay < dComp[s.c]) {
          dComp[s.c] = s.delay;
          whoKind[s.c] = s.kind;
          whoId[s.c] = s.id;
          bfsQ[qt++] = s.c;
        }
      }
      const c = bfsQ[qh++];
      const nextD = dComp[c] + 1;
      const knd = whoKind[c];
      const wid = whoId[c];
      for (let k = 0; k < 4; k++) {
        const n = c + dir4[k];
        if (n >= 0 && n < N && landMask[n] && nextD < dComp[n]) {
          dComp[n] = nextD;
          whoKind[n] = knd;
          whoId[n] = wid;
          bfsQ[qt++] = n;
        }
      }
    }
  }

  /**
   * Incrementally inject a newly chosen squad spawn point `seedCell` into dComp[N].
   * This immediately claims its Voronoi basin so subsequent squad slots NEVER
   * evaluate that same basin as empty/available!
   */
  injectChosenSquadPoint(seedCell, slotId, maxInjectRadius = 260) {
    const { N, landMask, dir4, dComp, whoKind, whoId, bfsQ } = this;
    if (seedCell < 0 || !landMask[seedCell]) return;
    let qh = 0, qt = 0;
    dComp[seedCell] = 0;
    whoKind[seedCell] = KIND_SQUAD;
    whoId[seedCell] = slotId;
    bfsQ[qt++] = seedCell;

    while (qh < qt) {
      const c = bfsQ[qh++];
      const dc = dComp[c];
      if (dc >= maxInjectRadius) continue;
      const nextD = dc + 1;
      for (let k = 0; k < 4; k++) {
        const n = c + dir4[k];
        if (n >= 0 && n < N && landMask[n] && nextD < dComp[n]) {
          dComp[n] = nextD;
          whoKind[n] = KIND_SQUAD;
          whoId[n] = slotId;
          bfsQ[qt++] = n;
        }
      }
    }
  }

  /**
   * Effective distance from pixel c = (x, y) to Boss npl, combining geodesic land
   * steps and Euclidean distance (so narrow rivers don't trick a bot into spawning
   * 30px away from Boss).
   */
  effectiveBossDist(c, boss) {
    if (!boss || boss.x < 0 || boss.y < 0) return 999999;
    const x = c % this.W;
    const y = (c / this.W) | 0;
    const euclid = Math.hypot(x - boss.x, y - boss.y);
    const geo = this.dBoss[c];
    if (geo >= 0) {
      // Must respect BOTH Euclidean clearance and geodesic land distance
      return Math.min(geo, 1.35 * euclid);
    }
    return 1.25 * euclid;
  }

  /**
   * Evaluate a candidate pixel `s` against the current dynamic `dComp` field.
   * Returns { totalScore, voronoiPixels, weightedArea, enemyNeighbors, enemyBorder, allyBorder }.
   */
  evaluateCandidate(s, role, boss, enemies, scales) {
    const { W, H, N, landMask, waterMask, dir4, dComp, whoKind, whoId, dScratch, bfsQ } = this;
    if (s < 0 || s >= N || !landMask[s]) return null;
    const sx = s % W, sy = (s / W) | 0;
    if (sx < 16 || sy < 16 || sx >= W - 16 || sy >= H - 16) return null;

    const maxD = 112;
    const lam = 48;
    const M = 28;
    let qh = 0, qt = 0;
    let voronoiPixels = 0;
    let weightedArea = 0;
    let coastPixels = 0;
    let enemyBorder = 0;
    let allyBorder = 0;
    const seenEnemies = [];

    dScratch[s] = 0;
    bfsQ[qt++] = s;

    while (qh < qt) {
      const c = bfsQ[qh++];
      const dc = dScratch[c];
      const compD = dComp[c];
      voronoiPixels++;

      const margin = compD < 500000 ? Math.min(1, Math.max(0.15, (compD - dc) / M)) : 1;
      weightedArea += (margin * lam) / (lam + dc);

      if (dc >= 16) {
        for (let k = 0; k < 4; k++) {
          const wn = c + dir4[k];
          if (wn >= 0 && wn < N && waterMask[wn]) {
            coastPixels++;
            break;
          }
        }
      }

      if (dc >= maxD) continue;

      let hitEnemyEdge = false;
      let hitAllyEdge = false;
      for (let k = 0; k < 4; k++) {
        const n = c + dir4[k];
        if (n < 0 || n >= N || dScratch[n] >= 0 || !landMask[n]) continue;
        if (dc + 1 >= dComp[n]) {
          const knd = whoKind[n];
          if (knd === KIND_ENEMY) {
            hitEnemyEdge = true;
            const eid = whoId[n];
            if (eid >= 0 && !seenEnemies.includes(eid)) seenEnemies.push(eid);
          } else if (knd === KIND_BOSS || knd === KIND_SQUAD || knd === KIND_RANDOM_ALLY) {
            hitAllyEdge = true;
          }
          continue;
        }
        dScratch[n] = dc + 1;
        bfsQ[qt++] = n;
      }
      if (hitEnemyEdge) enemyBorder++;
      if (hitAllyEdge) allyBorder++;
    }

    // Reset dScratch for visited nodes in O(qt)
    for (let i = 0; i < qt; i++) {
      dScratch[bfsQ[i]] = -1;
    }

    // Reject tiny cramped pockets (islands < 450 px, or < 3200 px for FLANK_GUARD)
    const minVoronoi =
      role === 'FLANK_GUARD'
        ? Math.min(3200, this.land * 0.012)
        : Math.min(450, this.land * 0.004);
    if (voronoiPixels < minVoronoi) {
      return null;
    }

    const enemyNeighbors = seenEnemies.length;
    // Penalize multi-front exposure to enemy humans, while NOT penalizing friendly borders!
    const coastBonus = Math.min(18, coastPixels * 0.06);
    let score =
      (weightedArea + coastBonus - 0.16 * enemyBorder) /
      (1 + 0.20 * Math.max(0, enemyNeighbors - 1));

    // Role-specific tactical shaping
    if (role === 'FLANK_GUARD' && boss && boss.x >= 0 && boss.y >= 0) {
      const bDist = this.effectiveBossDist(s, boss);
      const idealFlankDist = 0.55 * scales.bossExcl + 0.45 * scales.flankMax;
      const ringFit = Math.max(
        0.65,
        1.18 - 0.55 * Math.abs(bDist - idealFlankDist) / Math.max(40, scales.flankMax - scales.bossExcl)
      );
      score *= ringFit;

      // Bonus for interposing on the threat vector between Boss and nearby enemy humans
      const vx = sx - boss.x, vy = sy - boss.y;
      const vLen = Math.hypot(vx, vy) || 1;
      let maxThreatCos = 0;
      for (const e of enemies) {
        const ex = e.x - boss.x, ey = e.y - boss.y;
        const eLen = Math.hypot(ex, ey);
        if (eLen > 20 && eLen < scales.flankMax * 2.2) {
          const cos = (vx * ex + vy * ey) / (vLen * eLen);
          if (cos > maxThreatCos) maxThreatCos = cos;
        }
      }
      if (maxThreatCos > 0.25) {
        score *= 1.0 + 0.25 * maxThreatCos;
      }
    } else if (role === 'ECO_BANK') {
      // Deep eco banks love fewer enemy neighbors (0 or 1 enemy front) and huge land pockets
      if (enemyNeighbors <= 1) score *= 1.12;
    }

    return {
      cell: s,
      x: sx,
      y: sy,
      totalScore: score,
      voronoiPixels,
      weightedArea,
      enemyNeighbors,
      enemyBorder,
      allyBorder,
    };
  }

  /**
   * Solve the globally optimal K spawn coordinates for the current match & squad.
   *
   * @param {Object} params
   * @param {Array}  params.squadBots    [{ slot, port, name, meId, curX, curY }]
   * @param {Array}  params.humans       [{ id, name, team, terr, x, y, alive }]
   * @param {number} params.myTeam       Team ID of our squad (if known)
   * @param {Object} params.bossOverride Optional explicit { id, x, y } for Boss npl
   */
  solve({ squadBots = [], humans = [], myTeam = 0, bossOverride = null }) {
    const t0 = performance.now();
    const { W, H, N, land, landMask, dComp } = this;
    if (!landMask || N <= 0 || squadBots.length === 0) {
      return { ok: false, error: 'Map not initialized or empty squad', assignments: {} };
    }

    // 1. Identify our squad member player IDs so we NEVER treat our own bots as enemies
    const squadMeIds = new Set();
    for (const b of squadBots) {
      if (Number.isInteger(b.meId) && b.meId >= 0) squadMeIds.add(b.meId);
    }

    let boss = bossOverride && bossOverride.x >= 0 ? { ...bossOverride } : null;
    const enemies = [];
    const randomAllies = [];

    // Infer our team ID if not explicitly passed
    let teamId = myTeam;
    if (!(teamId > 0)) {
      for (const h of humans) {
        if ((squadMeIds.has(h.id) || isSquadBotName(h.name) || isBossNplName(h.name)) && h.team > 0) {
          teamId = h.team;
          break;
        }
      }
    }

    for (const h of humans) {
      if (!h || h.id < 0) continue;
      if (squadMeIds.has(h.id) || isSquadBotName(h.name)) {
        continue; // Our own squad guard bot — erased from competitor field!
      }
      if (isBossNplName(h.name)) {
        if (!boss && h.terr > 0 && h.x >= 0 && h.y >= 0) {
          boss = { id: h.id, x: h.x, y: h.y, name: h.name };
        }
        continue;
      }
      if (h.terr <= 0 || h.x < 0 || h.y < 0) continue;
      const isSameTeam = teamId > 0 && h.team === teamId;
      if (isSameTeam) {
        randomAllies.push({ id: h.id, x: h.x, y: h.y, name: h.name });
      } else {
        enemies.push({ id: h.id, x: h.x, y: h.y, name: h.name });
      }
    }

    const K = squadBots.length;
    const totalActiveHumans = Math.max(8, enemies.length + randomAllies.length + (boss ? 1 : 0) + K);
    const rCell = Math.sqrt(Math.max(10000, land) / (Math.PI * totalActiveHumans));
    const diag = Math.hypot(W, H);

    const scales = {
      rCell: Math.round(rCell),
      bossExcl: clamp(Math.round(Math.max(1.50 * rCell, 0.115 * diag)), 82, 160),
      flankMax: clamp(Math.round(Math.max(2.90 * rCell, 0.235 * diag)), 155, 285),
      allyMinSep: clamp(Math.round(Math.max(1.52 * rCell, 0.125 * diag)), 74, 185),
      enemyMinClearance: clamp(Math.round(0.65 * rCell), 36, 75),
    };

    // 2. Build initial multi-source geodesic distance fields (dComp, dBoss)
    this.buildInitialDistanceFields(enemies, randomAllies, boss);

    // 3. Determine how many FLANK_GUARD vs ECO_BANK slots to allocate
    const targetFlankCount = boss ? (K >= 4 ? 2 : K >= 2 ? 1 : 0) : 0;
    const chosenTargets = []; // [{ x, y, cell, role, voronoiPixels, score, bossDist, minAllyDist, minEnemyDist }]

    const distToChosenSquad = (x, y) => {
      let minD = 999999;
      for (const prev of chosenTargets) {
        const d = Math.hypot(x - prev.x, y - prev.y);
        if (d < minD) minD = d;
      }
      return minD;
    };

    const distToEnemies = (x, y) => {
      let minD = 999999;
      for (const e of enemies) {
        const d = Math.hypot(x - e.x, y - e.y);
        if (d < minD) minD = d;
      }
      return minD;
    };

    // Helper to pick the next optimal target point for a given role
    const pickNextTarget = (wantRole) => {
      // Try strict separation first, then gracefully relax if map is very small/crowded
      const relaxFactors = [1.0, 0.78, 0.58, 0.38];
      for (const relax of relaxFactors) {
        const reqAllySep = scales.allyMinSep * relax;
        const reqBossExcl = scales.bossExcl * Math.max(0.72, relax);
        const reqEnemyClear = scales.enemyMinClearance * Math.max(0.6, relax);

        const stride = W * H > 900000 ? 8 : 6;
        const rawSeeds = [];
        for (let y = 16; y < H - 16; y += stride) {
          for (let x = 16; x < W - 16; x += stride) {
            const c = y * W + x;
            if (!landMask[c]) continue;
            if (distToChosenSquad(x, y) < reqAllySep) continue;
            if (distToEnemies(x, y) < reqEnemyClear) continue;

            const bDist = boss ? this.effectiveBossDist(c, boss) : 999999;
            if (boss && bDist < reqBossExcl) continue;

            if (wantRole === 'FLANK_GUARD') {
              // Must be on the SAME landmass as Boss (dBoss[c] > 0) and within flank ring!
              const geoBoss = this.dBoss[c];
              const maxRing = scales.flankMax * (2 - relax * 0.8);
              if (geoBoss < reqBossExcl || geoBoss > maxRing || bDist > maxRing) continue;
              // If we already picked 1 flank guard, require the 2nd flank guard to be on a different angular sector (>= 55 deg)
              const prevFlank = chosenTargets.find((t) => t.role === 'FLANK_GUARD');
              if (prevFlank && boss) {
                const v1x = prevFlank.x - boss.x, v1y = prevFlank.y - boss.y;
                const v2x = x - boss.x, v2y = y - boss.y;
                const cos = (v1x * v2x + v1y * v2y) / ((Math.hypot(v1x, v1y) || 1) * (Math.hypot(v2x, v2y) || 1));
                if (cos > 0.57) continue; // < ~55 degrees apart around Boss
              }
            }

            const clearance = Math.min(dComp[c], 220);
            if (clearance < 12 * relax) continue;
            rawSeeds.push({ c, x, y, clearance, bDist });
          }
        }

        if (rawSeeds.length === 0) {
          if (wantRole === 'FLANK_GUARD') break; // Degrade to ECO_BANK if flank ring is full/water
          continue;
        }

        // Sort raw seeds by clearance descending and pick up to 14 spatially diverse seeds
        rawSeeds.sort((a, b) => b.clearance - a.clearance);
        const diverseSeeds = [];
        const seedGap = Math.max(24, Math.round(0.42 * scales.allyMinSep));
        for (const item of rawSeeds) {
          if (diverseSeeds.length >= 14) break;
          if (diverseSeeds.some((o) => Math.abs(o.x - item.x) + Math.abs(o.y - item.y) < seedGap)) continue;
          diverseSeeds.push(item);
        }

        let bestEval = null;
        for (const item of diverseSeeds) {
          const ev = this.evaluateCandidate(item.c, wantRole, boss, enemies, scales);
          if (ev && (!bestEval || ev.totalScore > bestEval.totalScore)) {
            bestEval = ev;
          }
        }

        if (!bestEval) {
          if (wantRole === 'FLANK_GUARD') break;
          continue;
        }

        // Fast local hill-climb refinement (steps 8, 4) respecting separation constraints
        for (const step of [8, 4]) {
          let improved = true;
          let guard = 0;
          while (improved && guard++ < 3) {
            improved = false;
            const cx = bestEval.x, cy = bestEval.y;
            for (const [dx, dy] of [[step, 0], [-step, 0], [0, step], [0, -step]]) {
              const nx = cx + dx, ny = cy + dy;
              if (nx < 16 || ny < 16 || nx >= W - 16 || ny >= H - 16) continue;
              const nc = ny * W + nx;
              if (!landMask[nc]) continue;
              if (distToChosenSquad(nx, ny) < reqAllySep) continue;
              if (distToEnemies(nx, ny) < reqEnemyClear) continue;
              if (boss && this.effectiveBossDist(nc, boss) < reqBossExcl) continue;
              if (wantRole === 'FLANK_GUARD' && (this.dBoss[nc] < reqBossExcl || this.dBoss[nc] > scales.flankMax * 1.4)) continue;
              const ev = this.evaluateCandidate(nc, wantRole, boss, enemies, scales);
              if (ev && ev.totalScore > bestEval.totalScore) {
                bestEval = ev;
                improved = true;
              }
            }
          }
        }

        return {
          ...bestEval,
          role: wantRole,
          bossDist: boss ? Math.round(this.effectiveBossDist(bestEval.cell, boss)) : -1,
          minAllyDist: chosenTargets.length ? Math.round(distToChosenSquad(bestEval.x, bestEval.y)) : -1,
          minEnemyDist: enemies.length ? Math.round(distToEnemies(bestEval.x, bestEval.y)) : -1,
        };
      }
      return null;
    };

    for (let m = 0; m < K; m++) {
      const wantRole = m < targetFlankCount ? 'FLANK_GUARD' : 'ECO_BANK';
      let picked = pickNextTarget(wantRole);
      if (!picked && wantRole === 'FLANK_GUARD') {
        picked = pickNextTarget('ECO_BANK');
      }
      if (!picked) {
        // Ultimate safety fallback: farthest land pixel from all existing chosenTargets & Boss
        let bestC = -1, bestMinD = -1;
        for (let y = 8; y < H - 8; y += 6) {
          for (let x = 8; x < W - 8; x += 6) {
            const c = y * W + x;
            if (!landMask[c]) continue;
            const dA = distToChosenSquad(x, y);
            const dB = boss ? Math.hypot(x - boss.x, y - boss.y) : 999999;
            const dMin = Math.min(dA, dB);
            if (dMin > bestMinD) {
              bestMinD = dMin;
              bestC = c;
            }
          }
        }
        if (bestC >= 0) {
          const fx = bestC % W, fy = (bestC / W) | 0;
          picked = {
            cell: bestC,
            x: fx,
            y: fy,
            role: 'ECO_BANK',
            totalScore: 1,
            voronoiPixels: 500,
            weightedArea: 100,
            enemyNeighbors: 0,
            bossDist: boss ? Math.round(Math.hypot(fx - boss.x, fy - boss.y)) : -1,
            minAllyDist: chosenTargets.length ? Math.round(distToChosenSquad(fx, fy)) : -1,
            minEnemyDist: enemies.length ? Math.round(distToEnemies(fx, fy)) : -1,
          };
        }
      }
      if (picked) {
        chosenTargets.push(picked);
        // CRITICAL: Immediately inject this chosen point into dComp[N] so the next
        // squad bot sees this entire basin as already claimed!
        this.injectChosenSquadPoint(picked.cell, m, Math.max(220, Math.round(2.5 * scales.allyMinSep)));
      }
    }

    // Recompute true mutual minAllyDist across all K chosen targets for diagnostics
    for (let i = 0; i < chosenTargets.length; i++) {
      let minD = 999999;
      for (let j = 0; j < chosenTargets.length; j++) {
        if (i === j) continue;
        const d = Math.hypot(chosenTargets[i].x - chosenTargets[j].x, chosenTargets[i].y - chosenTargets[j].y);
        if (d < minD) minD = d;
      }
      chosenTargets[i].minAllyDist = minD < 900000 ? Math.round(minD) : -1;
    }

    // 4. Match K bots to K chosenTargets via exact Bitmask DP Minimum-Displacement Matching
    //    so bots don't swap across the map during the 6-second spawn countdown!
    const sortedBots = squadBots.slice().sort((a, b) => (a.slot ?? 0) - (b.slot ?? 0));
    const M = chosenTargets.length;
    const matchOrder = this.matchBotsToTargets(sortedBots, chosenTargets);

    const assignments = {};
    const byMeId = {};
    const list = [];

    for (let i = 0; i < sortedBots.length; i++) {
      const bot = sortedBots[i];
      const tIdx = matchOrder[i] ?? (i % Math.max(1, M));
      const tgt = chosenTargets[tIdx];
      if (!tgt) continue;

      let finalX = tgt.x;
      let finalY = tgt.y;
      const prev = this.prevBotTargets.get(bot.slot);
      // Anti-jitter hysteresis: if previous assigned spot is within 6px and valid, hold steady
      if (
        prev &&
        Math.hypot(prev.x - finalX, prev.y - finalY) <= 6 &&
        this.landMask[prev.y * W + prev.x]
      ) {
        finalX = prev.x;
        finalY = prev.y;
      }
      this.prevBotTargets.set(bot.slot, { x: finalX, y: finalY, role: tgt.role });

      const entry = {
        slot: bot.slot,
        port: bot.port,
        name: bot.name,
        meId: bot.meId ?? -1,
        x: finalX,
        y: finalY,
        mapW: W,
        mapH: H,
        role: tgt.role,
        voronoiPixels: tgt.voronoiPixels,
        score: Math.round(tgt.totalScore * 10) / 10,
        bossDist: tgt.bossDist,
        minAllyDist: tgt.minAllyDist,
        minEnemyDist: tgt.minEnemyDist,
        enemyNeighbors: tgt.enemyNeighbors,
      };
      assignments[bot.slot] = entry;
      if (Number.isInteger(bot.meId) && bot.meId >= 0) {
        byMeId[bot.meId] = entry;
      }
      list.push(entry);
    }

    const elapsedMs = Math.round((performance.now() - t0) * 100) / 100;
    this.lastSolveMs = elapsedMs;
    this.lastSolvedAt = Date.now();
    this.solveCount++;

    const minPairwiseDist = list.reduce(
      (acc, x) => (x.minAllyDist >= 0 && x.minAllyDist < acc ? x.minAllyDist : acc),
      999999
    );

    this.lastPlan = {
      ok: true,
      matchKey: this.matchKey,
      solveCount: this.solveCount,
      elapsedMs,
      map: { W, H, land },
      scales,
      boss: boss || null,
      enemyCount: enemies.length,
      randomAllyCount: randomAllies.length,
      squadCount: list.length,
      minPairwiseDist: minPairwiseDist < 900000 ? minPairwiseDist : -1,
      assignments,
      byMeId,
      list,
    };

    return this.lastPlan;
  }

  /**
   * Exact O(K * 2^K) bitmask DP minimum-cost bipartite matching between bots and targets.
   * For bots that already have a live position (curX, curY) or previous target, minimizes
   * total movement distance so bots stay anchored to their nearest target basin.
   */
  matchBotsToTargets(bots, targets) {
    const K = bots.length;
    const M = targets.length;
    if (K === 0 || M === 0) return [];
    if (K !== M || K > 12) {
      return bots.map((_, i) => i % M);
    }

    // Check if any bot has a known reference position (curX/curY or prevBotTargets)
    const refs = bots.map((b) => {
      const prev = this.prevBotTargets.get(b.slot);
      if (Number.isFinite(b.curX) && Number.isFinite(b.curY) && b.curX > 0 && b.curY > 0) {
        return { x: b.curX, y: b.curY, hasRef: true };
      }
      if (prev) {
        return { x: prev.x, y: prev.y, hasRef: true };
      }
      return { x: 0, y: 0, hasRef: false };
    });

    if (!refs.some((r) => r.hasRef)) {
      return bots.map((_, i) => i);
    }

    const totalMasks = 1 << K;
    const dp = new Float64Array(totalMasks).fill(1e18);
    const parentTarget = new Int8Array(totalMasks).fill(-1);
    dp[0] = 0;

    // Precompute popcount order
    for (let mask = 0; mask < totalMasks - 1; mask++) {
      const baseCost = dp[mask];
      if (baseCost >= 1e17) continue;
      // Count bits in mask = bot index i
      let m = mask, botIdx = 0;
      while (m) {
        m &= m - 1;
        botIdx++;
      }
      if (botIdx >= K) continue;
      const ref = refs[botIdx];
      for (let t = 0; t < K; t++) {
        if (mask & (1 << t)) continue;
        const nmask = mask | (1 << t);
        const cost = ref.hasRef
          ? Math.hypot(ref.x - targets[t].x, ref.y - targets[t].y)
          : t * 0.1;
        const cand = baseCost + cost;
        if (cand < dp[nmask]) {
          dp[nmask] = cand;
          parentTarget[nmask] = t;
        }
      }
    }

    const result = new Array(K);
    let curMask = totalMasks - 1;
    for (let botIdx = K - 1; botIdx >= 0; botIdx--) {
      const t = parentTarget[curMask];
      if (t < 0) {
        return bots.map((_, i) => i);
      }
      result[botIdx] = t;
      curMask ^= 1 << t;
    }
    return result;
  }

  /**
   * Optional HTTP status & control server on 127.0.0.1:8198 so external tools,
   * browser tabs, or operators can inspect or trigger the live spawn coordinator.
   */
  startHttpServer() {
    if (this.server) return this.server;
    const cors = {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type',
      'Cache-Control': 'no-store',
    };

    this.server = http.createServer((req, res) => {
      if (req.method === 'OPTIONS') {
        res.writeHead(204, cors);
        res.end();
        return;
      }
      const u = new URL(req.url, `http://${this.host}:${this.port}`);
      if (req.method === 'GET' && (u.pathname === '/status' || u.pathname === '/plan' || u.pathname === '/')) {
        res.writeHead(200, { ...cors, 'Content-Type': 'application/json; charset=utf-8' });
        res.end(
          JSON.stringify({
            ok: true,
            service: 'tsb-team-spawn-coordinator',
            matchKey: this.matchKey,
            solveCount: this.solveCount,
            lastSolveMs: this.lastSolveMs,
            lastSolvedAt: this.lastSolvedAt,
            plan: this.lastPlan,
          })
        );
        return;
      }
      if (req.method === 'POST' && u.pathname === '/solve') {
        let body = '';
        req.on('data', (c) => (body += c));
        req.on('end', () => {
          try {
            const payload = JSON.parse(body || '{}');
            if (payload.map) this.setMap(payload.map);
            const plan = this.solve(payload);
            res.writeHead(200, { ...cors, 'Content-Type': 'application/json; charset=utf-8' });
            res.end(JSON.stringify(plan));
          } catch (err) {
            res.writeHead(400, { ...cors, 'Content-Type': 'application/json; charset=utf-8' });
            res.end(JSON.stringify({ ok: false, error: err?.message || String(err) }));
          }
        });
        return;
      }
      res.writeHead(404, cors);
      res.end('Not found');
    });

    this.server.on('error', (err) => {
      console.error(`[SPAWN-COORD] HTTP server error on :${this.port}:`, err.message);
    });

    this.server.listen(this.port, this.host, () => {
      console.log(`[SPAWN-COORD] Unified Team Spawn Coordinator listening on http://${this.host}:${this.port}`);
    });
    return this.server;
  }
}
