with open("/tmp/fdvg-c58/territorial-sim/strategy/pool/v27-live.js") as f:
    s = f.read()

# 0. Preserve teams and names in withoutPlayer(g, p) during spawn phase!
old_without = """    x0: g.x0, y0: g.y0, x1: g.x1, y1: g.y1,
    isBot: (o) => o >= g.humans,"""
new_without = """    x0: g.x0, y0: g.y0, x1: g.x1, y1: g.y1,
    teams: g.teams, names: g.names,
    isBot: (o) => o >= g.humans,"""
assert old_without in s, "old_without not found"
s = s.replace(old_without, new_without, 1)

# 1. Filter teammates out of analyze(g) so this.nb NEVER contains a teammate!
old_analyze = """          const o = own[c];
          if (o !== me) {
            mark[c] = st;
            if (cnt[o]++ === 0) this.nb.push(o);
          }"""

new_analyze = """          const o = own[c];
          if (o !== me && !(g.teams && g.teams[me] > 0 && g.teams[o] === g.teams[me])) {
            mark[c] = st;
            if (cnt[o]++ === 0) this.nb.push(o);
          }"""
assert old_analyze in s, "old_analyze not found"
s = s.replace(old_analyze, new_analyze, 1)

# 2. Filter teammates out of peopleOf(g, q)
old_people_of = """        if (o === q || seen[o] === st) continue;
        seen[o] = st;
        if (g.alive[o] && !g.isBot(o)) s.push(o);"""

new_people_of = """        if (o === q || seen[o] === st) continue;
        seen[o] = st;
        if (g.alive[o] && !g.isBot(o) && !(g.teams && g.teams[ this.me ] > 0 && g.teams[o] === g.teams[ this.me ])) s.push(o);"""
assert old_people_of in s, "old_people_of not found"
s = s.replace(old_people_of, new_people_of, 1)

# 3. Filter teammates out of searchWater(g)
old_search_water = """          const o = own[n];
          if (o === me || this.cnt[o] > 0 || (noBots && g.isBot(o) && !this.botOk(g, o))) continue;"""

new_search_water = """          const o = own[n];
          if (o === me || (g.teams && g.teams[me] > 0 && g.teams[o] === g.teams[me]) || this.cnt[o] > 0 || (noBots && g.isBot(o) && !this.botOk(g, o))) continue;"""
assert old_search_water in s, "old_search_water not found"
s = s.replace(old_search_water, new_search_water, 1)

# 4. Filter teammates out of doorHarvestCandidates
old_door_harvest = """              if (o !== me && o < H && g.alive[o] && g.terr[o] >= 600) {"""
new_door_harvest = """              if (o !== me && o < H && g.alive[o] && g.terr[o] >= 600 && !(g.teams && g.teams[me] > 0 && g.teams[o] === g.teams[me])) {"""
assert old_door_harvest in s, "old_door_harvest not found"
s = s.replace(old_door_harvest, new_door_harvest, 1)

# 5. Add Team + Boss-Guard + Distributed Spawn + Cash-First Rescue (10% light assist) + Auto Peace Vote!
old_helpers = """  otherHumanMedDens(g) {
    const me = this.me, H = g.humans;
    const ds = [];
    for (let p = 0; p < H; p++) {
      if (p !== me && g.alive[p] && g.terr[p] >= 100 && !g.isBot(p)) {
        ds.push(g.bal[p] / g.terr[p]);
      }
    }
    if (!ds.length) return null;
    ds.sort((a, b) => a - b);
    return ds[ds.length >> 1];
  }

  livingHumanCount(g) {
    let n = 0;
    for (let p = 0; p < g.humans; p++) {
      if (g.alive[p] && g.terr[p] >= 100 && !g.isBot(p)) n++;
    }
    return n;
  }

  topOtherHuman(g) {
    const me = this.me, H = g.humans;
    let bestP = -1, bestL = 0;
    for (let p = 0; p < H; p++) {
      if (p !== me && g.alive[p] && g.terr[p] > bestL && !g.isBot(p)) {
        bestL = g.terr[p];
        bestP = p;
      }
    }
    return bestP;
  }"""

new_helpers = """  isTeammate(g, p) {
    return !!(g.teams && g.teams[this.me] > 0 && g.teams[p] === g.teams[this.me]);
  }

  // Identify our Boss ("[NPL] npl" / "[NPL]NPL", excluding our 5 guard bot names)
  isBossNpl(g, p) {
    if (p === this.me || !g.alive[p]) return false;
    const raw = String(g.names?.[p] ?? "").trim();
    const low = raw.toLowerCase();
    if (low.includes("mishi") || low.includes("matzz") || low.includes("kiholma") || low.includes("leo_99") || low.includes("racoon")) {
      return false;
    }
    const stripped = raw.replace(/\\[[^\\]]*\\]/g, "").trim().toLowerCase();
    return stripped === "npl" || stripped.includes("npl") || low === "[npl]npl";
  }

  findBossId(g) {
    for (let p = 0; p < g.humans; p++) {
      if (this.isBossNpl(g, p) && (this.isTeammate(g, p) || !g.teams)) return p;
    }
    return -1;
  }

  isOurSquadBot(g, p) {
    const raw = String(g.names?.[p] ?? "").trim();
    const low = raw.replace(/\\[[^\\]]*\\]/g, "").trim().toLowerCase();
    return low === "mishi" || low === "matzz" || low === "kiholma" || low === "leo_99" || low === "racoon";
  }

  // Check 8 compass directions from (px0, py0) to count how many outward land expansion
  // rays are open (not blocked by water/edge and not cut off by any teammate in front).
  evalOpenExpansionCone(h, px0, py0, alliesList, ignoreP = -1) {
    const W = h.W, H = h.H, px = h.px, own = h.own, humans = h.humans;
    const DIRS = [
      [1, 0], [0.7071, 0.7071], [0, 1], [-0.7071, 0.7071],
      [-1, 0], [-0.7071, -0.7071], [0, -1], [0.7071, -0.7071]
    ];
    let openMask = 0, openCount = 0, terrainBlocked = 0;
    for (let d = 0; d < 8; d++) {
      const ux = DIRS[d][0], uy = DIRS[d][1];
      let landSteps = 0;
      for (let r = 10; r <= 58; r += 8) {
        const nx = Math.round(px0 + ux * r), ny = Math.round(py0 + uy * r);
        if (nx < 4 || ny < 4 || nx >= W - 4 || ny >= H - 4) break;
        const c = ny * W + nx;
        const v = px[c];
        if (v === T_LAND || (v >= P_INNER && own[c] >= humans)) {
          landSteps++;
        }
      }
      if (landSteps < 4) {
        terrainBlocked++;
        continue;
      }
      // Check if any teammate stands in front of this ray and cuts off its Voronoi expansion
      const tx = px0 + ux * 48, ty = py0 + uy * 48;
      let blockedByAlly = false;
      for (let i = 0; i < alliesList.length; i++) {
        const a = alliesList[i];
        if (a.p === ignoreP) continue;
        const adx = a.x - px0, ady = a.y - py0;
        const ad = Math.hypot(adx, ady);
        if (ad < 1 || ad > 96) continue;
        // If ally is closer to the ray's 48px target point than (px0, py0) is (48px), ray is blocked
        if (Math.hypot(tx - a.x, ty - a.y) < 44) {
          blockedByAlly = true;
          break;
        }
      }
      if (!blockedByAlly) {
        openMask |= (1 << d);
        openCount++;
      }
    }
    const dbl = openMask | (openMask << 8);
    let maxContig = 0, cur = 0;
    for (let i = 0; i < 16; i++) {
      if ((dbl >> i) & 1) {
        cur++;
        if (cur > maxContig) maxContig = cur;
      } else {
        cur = 0;
      }
    }
    if (maxContig > 8) maxContig = 8;
    return { openCount, maxContig, terrainBlocked, openMask };
  }

  // TEAM-SIZE-AWARE HIGH-VORONOI REGIONAL FRONTLINE SPAWN:
  // 1. Uses full 600-step Voronoi land integral (like v27 spawnVsPeople0) as the multiplicative base
  //    so we NEVER sacrifice large territory (20k~50k land) for a cramped 4k pocket!
  // 2. Enforces healthy squad spacing (minAllySep = 92~130px, ideal = 135~165px, max = 260px)
  //    so each of the 5 brothers gets a full 20k~40k expansion circle before merging borders at t=1200~1600.
  // 3. Vetoes enemy mega-team encirclements (pincer / multi-octant surround) and heavily discounts
  //    spots that are 100% walled in behind wild teammates (enemyBorder === 0).
  chooseSpawn(g, final = true) {
    const P = this.p, me = this.me;
    const h = g.terr[me] > 0 ? withoutPlayer(g, me) : g;
    const W = h.W, H = h.H, N = h.N, px = h.px, d4 = h.dir4;
    const mapScale = Math.sqrt(Math.max(10000, h.land));

    if (!this.dPeopleBuf || this.dPeopleBuf.length !== N) {
      this.dPeopleBuf = new Int32Array(N);
      this.dEnemyBuf = new Int32Array(N);
      this.dAllyBuf = new Int32Array(N);
      this.dMineBuf = new Int32Array(N).fill(-1);
      this.spawnQBuf = new Int32Array(N);
    }

    // 1. Analyze team sizes and placed human positions
    const myTeam = h.teams ? h.teams[me] : 0;
    const teamCounts = new Map();
    for (let p = 0; p < h.humans; p++) {
      const t = h.teams ? h.teams[p] : 0;
      if (t > 0) teamCounts.set(t, (teamCounts.get(t) || 0) + 1);
    }
    let maxEnemyTeamSize = 1;
    for (const [t, cnt] of teamCounts.entries()) {
      if (t !== myTeam && cnt > maxEnemyTeamSize) maxEnemyTeamSize = cnt;
    }

    // WHEN MAX ENEMY TEAM SIZE <= 10:
    // Directly run the proven original distributed Voronoi spawn (top 5 Voronoi regions from spawnVsPeople)!
    if (maxEnemyTeamSize <= 10) {
      let mySquadIdx = typeof window !== "undefined" && Number.isInteger(window.__tsbSquadSlot) ? window.__tsbSquadSlot : 0;
      let rankIdx = 0;
      for (let p = 0; p < me; p++) {
        if (this.isOurSquadBot(g, p) && !this.isBossNpl(g, p)) rankIdx++;
      }
      const slot = (rankIdx || mySquadIdx) % 5;
      const cands = this.spawnVsPeople ? this.spawnVsPeople(g, 10) : this.spawnCandidates(g, 10);
      if (cands && cands.length > 0) {
        return cands[slot % cands.length];
      }
      return super.chooseSpawn(g, final);
    }

    const enemies = [];
    const squadAllies = [];
    const wildAllies = [];
    let bossAlly = null;
    let anyHumanPlaced = false;

    for (let p = 0; p < h.humans; p++) {
      if (p === me || h.terr[p] === 0) continue;
      anyHumanPlaced = true;
      const hx = (h.x0[p] + h.x1[p]) >> 1, hy = (h.y0[p] + h.y1[p]) >> 1;
      const isBoss = this.isBossNpl(h, p);
      const isSquad = this.isOurSquadBot(h, p) && !isBoss;
      const isAlly = this.isTeammate(h, p) || isBoss || isSquad;
      if (isBoss) {
        bossAlly = { p, x: hx, y: hy, isBoss: true, isSenior: true };
      } else if (isSquad) {
        squadAllies.push({ p, x: hx, y: hy, isSquad: true, isSenior: p < me });
      } else if (isAlly) {
        wildAllies.push({ p, x: hx, y: hy, isWild: true, isSenior: false });
      } else {
        const t = h.teams ? h.teams[p] : 0;
        const tSize = t > 0 ? (teamCounts.get(t) || 1) : 1;
        enemies.push({ p, x: hx, y: hy, team: t, teamSize: tSize });
      }
    }

    if (!anyHumanPlaced) {
      return this.spawnCandidates(g, 1)[0] ?? null;
    }

    const seniorAllies = [];
    if (bossAlly) seniorAllies.push(bossAlly);
    for (const a of squadAllies) {
      if (a.isSenior) seniorAllies.push(a);
    }
    const ourSquadList = bossAlly ? [bossAlly, ...squadAllies] : squadAllies;
    const allPlacedAllies = [...ourSquadList, ...wildAllies];

    // 2. Healthy Voronoi spacing: each brother needs ~50-75px radius of personal land (15k-35k pixels)
    //    before borders merge, so center-to-center distance between squadmates is 95~240px (ideal ~140px).
    const minAllySep = Math.round(Math.max(92, Math.min(130, 0.142 * mapScale)));
    const idealAllySep = Math.round(Math.max(132, Math.min(180, 0.205 * mapScale)));
    const maxAllySep = Math.round(Math.max(220, Math.min(310, 0.340 * mapScale)));
    const minWildSep = Math.round(Math.max(54, 0.58 * minAllySep));

    // 3. BFS land distance maps:
    //    distAll: distance to ANY placed human (gives true Voronoi cell size!)
    //    dEnemy:  distance to nearest placed enemy human
    //    dAlly:   distance to nearest placed teammate human
    const distAll = Strategy.prototype.spawnDist.call(
      this, h, this.dPeopleBuf, (o) => o < h.humans && o !== me
    );
    const dEnemy = enemies.length > 0
      ? Strategy.prototype.spawnDist.call(
          this, h, this.dEnemyBuf,
          (o) => o < h.humans && o !== me && !this.isTeammate(h, o) && !this.isOurSquadBot(h, o) && !this.isBossNpl(h, o)
        )
      : null;
    const dAlly = allPlacedAllies.length > 0
      ? Strategy.prototype.spawnDist.call(
          this, h, this.dAllyBuf,
          (o) => o < h.humans && o !== me && (this.isTeammate(h, o) || this.isOurSquadBot(h, o) || this.isBossNpl(h, o))
        )
      : null;

    const comp = this.compSize ? this.compSize(h) : null;
    const minLandmass = Math.min(25000, Math.floor(0.18 * h.land));

    // Enemy mega-team encirclement & heat evaluator
    const R_surr = Math.max(145, Math.min(250, 0.32 * mapScale));
    const R_pincer = Math.max(110, Math.min(175, 0.22 * mapScale));

    const evalEnemyRisk = (x, y) => {
      if (enemies.length === 0) return { veto: false, heat: 0, minD: 999 };
      let minD = Infinity, heat = 0;
      const teamOcts = new Map();
      const near = [];

      for (let i = 0; i < enemies.length; i++) {
        const e = enemies[i];
        const dx = e.x - x, dy = e.y - y;
        const d = Math.hypot(dx, dy);
        if (d < minD) minD = d;
        const minSafeE = 40 + Math.min(26, (e.teamSize - 1) * 1.2);
        if (d < minSafeE) return { veto: true, heat: 999, minD: d };

        const tw = 1 + 0.30 * Math.min(25, e.teamSize - 1);
        heat += tw * Math.exp(-(d * d) / (2 * 125 * 125));

        if (d <= R_surr && e.team > 0) {
          const oct = Math.floor(((Math.atan2(dy, dx) + Math.PI) / (2 * Math.PI)) * 8) & 7;
          let rec = teamOcts.get(e.team);
          if (!rec) { rec = { mask: 0, cnt: 0, size: e.teamSize }; teamOcts.set(e.team, rec); }
          rec.mask |= (1 << oct);
          rec.cnt++;
        }
        if (d <= R_pincer) {
          near.push({ ux: dx / Math.max(1, d), uy: dy / Math.max(1, d), d, team: e.team, teamSize: e.teamSize });
        }
      }

      // Pincer veto: never spawn sandwiched between two enemies of a big team within R_pincer
      for (let i = 0; i < near.length; i++) {
        for (let j = i + 1; j < near.length; j++) {
          const e1 = near[i], e2 = near[j];
          const cosA = e1.ux * e2.ux + e1.uy * e2.uy;
          if (cosA < -0.45 && (e1.team === e2.team || e1.teamSize >= 6 || e2.teamSize >= 6) && e1.d < 135 && e2.d < 135) {
            return { veto: true, heat: 999, minD };
          }
        }
      }

      // Single enemy team multi-octant surround veto (>= 3 members in >= 3 octants within R_surr)
      for (const rec of teamOcts.values()) {
        let tOcts = 0;
        for (let b = 0; b < 8; b++) if ((rec.mask >> b) & 1) tOcts++;
        if (rec.cnt >= 3 && tOcts >= 3) return { veto: true, heat: 999, minD };
      }

      return { veto: false, heat, minD };
    };

    // 4. Generate candidate spots:
    //    (a) Standard v27 farthest-from-humans spots (spaced by 24px, plus islands/pockets and spawnCandidates)
    //    (b) Regional ring [minAllySep, maxAllySep] around seniorAllies (spaced by 20px)
    const far = [], cut = [];
    for (let y = 6; y < H - 7; y += 4) {
      for (let x = 6; x < W - 7; x += 4) {
        const c = y * W + x;
        if (px[c] !== T_LAND) continue;
        if (comp && comp[c] > 0 && comp[c] < minLandmass) continue;
        if (distAll[c] >= 0) far.push(c);
        else cut.push(c);
      }
    }
    far.sort((a, b) => distAll[b] - distAll[a]);
    const spaced = (list, k, gap) => {
      const out = [];
      for (const c of list) {
        if (out.length >= k) break;
        const x = c % W, y = iV(c, W);
        if (out.some((o) => Math.abs((o % W) - x) + Math.abs(iV(o, W) - y) < gap)) continue;
        out.push(c);
      }
      return out;
    };

    const candSet = new Set();
    for (const c of spaced(far, 90, 22)) candSet.add(c);
    for (const c of spaced(cut, 8, 64)) candSet.add(c);
    for (const s of this.spawnCandidates(g, 10)) candSet.add(s.y * W + s.x);

    if (seniorAllies.length > 0) {
      for (const a of seniorAllies) {
        const x0 = Math.max(8, a.x - maxAllySep), x1 = Math.min(W - 9, a.x + maxAllySep);
        const y0 = Math.max(8, a.y - maxAllySep), y1 = Math.min(H - 9, a.y + maxAllySep);
        for (let y = y0; y <= y1; y += 20) {
          for (let x = x0; x <= x1; x += 20) {
            const c = y * W + x;
            if (px[c] !== T_LAND) continue;
            if (comp && comp[c] > 0 && comp[c] < minLandmass) continue;
            const d = Math.hypot(x - a.x, y - a.y);
            if (d >= minAllySep && d <= maxAllySep && distAll[c] >= 36) candSet.add(c);
          }
        }
      }
    }

    const curPos = g.terr[me] > 0 ? ((g.y0[me] + g.y1[me]) >> 1) * W + ((g.x0[me] + g.x1[me]) >> 1) : -1;
    if (curPos >= 0 && px[curPos] === T_LAND) candSet.add(curPos);

    // 5. Evaluate full 600-step Voronoi land score (v27 spawnVsPeople0 formula) + perimeter contacts
    const dd = this.dMineBuf, q = this.spawnQBuf;
    const lam = P.spawnP || 1000000000, maxD = P.spawnMaxD || 600, M = P.spawnM || 200;

    const evalCandidate = (s) => {
      if (px[s] !== T_LAND) return null;
      if (comp && comp[s] > 0 && comp[s] < minLandmass) return null;
      const x = s % W, y = iV(s, W);

      // Enforce minimum separation from our squadmates / Boss and wild teammates
      for (const a of ourSquadList) {
        if (Math.hypot(x - a.x, y - a.y) < minAllySep) return null;
      }
      for (const w of wildAllies) {
        if (Math.hypot(x - w.x, y - w.y) < minWildSep) return null;
      }

      const eRisk = evalEnemyRisk(x, y);
      if (eRisk.veto) return null;

      const cone = this.evalOpenExpansionCone(h, x, y, allPlacedAllies, me);
      if (cone.openCount < 3 || cone.maxContig < 2) return null;

      let qh = 0, qt = 0, rawLandSc = 0, pixels = 0, enemyBorder = 0, allyBorder = 0;
      dd[s] = 0;
      q[qt++] = s;
      while (qh < qt) {
        const c = q[qh++];
        const dc = dd[c];
        pixels++;
        const w = M > 0 && distAll[c] >= 0 ? Math.min(1, (distAll[c] - dc) / M) : 1;
        rawLandSc += (w * lam) / (lam + dc);
        if (dc >= maxD) continue;
        for (let k = 0; k < 4; k++) {
          const n = c + d4[k];
          if (dd[n] >= 0 || px[n] !== T_LAND) continue;
          if (distAll[n] >= 0 && dc + 1 >= distAll[n]) {
            const deN = dEnemy ? dEnemy[n] : -1;
            const daN = dAlly ? dAlly[n] : -1;
            if (deN >= 0 && (daN < 0 || deN <= daN + 6)) enemyBorder++;
            else if (daN >= 0) allyBorder++;
            continue;
          }
          dd[n] = dc + 1;
          q[qt++] = n;
        }
      }
      for (let i = 0; i < qt; i++) dd[q[i]] = -1;

      // Never pick a tiny pocket (< 2200 Voronoi pixels) where we'd get starved!
      if (pixels < 2200) return null;

      let mult = 1.0 / (1.0 + 0.05 * eRisk.heat);

      // Anti-Wall-In & Frontline Boundary multiplier:
      // If enemies exist on this landmass, penalize spots that are 100% walled in behind wild teammates
      // (enemyBorder === 0 and allyBorder > 20), and reward spots that have both teammate support AND enemy frontline!
      const deHere = dEnemy ? dEnemy[s] : -1;
      if (deHere >= 0 && allPlacedAllies.length > 0) {
        if (enemyBorder < 6 && allyBorder > 18) {
          mult *= 0.35; // Walled in by teammates -> heavy discount!
        } else if (enemyBorder >= 10 && allyBorder >= 8) {
          mult *= 1.18; // Right on the Teammate-Enemy boundary with good Voronoi land!
        }
      }

      // Regional Squad Cohesion multiplier (only multiplicative on rawLandSc so tiny pockets NEVER win!)
      let minSenD = Infinity;
      if (seniorAllies.length > 0) {
        for (const a of seniorAllies) {
          const d = Math.hypot(x - a.x, y - a.y);
          if (d < minSenD) minSenD = d;
        }
        if (minSenD >= minAllySep && minSenD <= maxAllySep) {
          const closeness = 1.0 - Math.min(1.0, Math.abs(minSenD - idealAllySep) / (maxAllySep - minAllySep));
          mult *= (1.18 + 0.22 * closeness);
        }
      }

      if (s === curPos) mult *= 1.04;

      return { s, x, y, rawLandSc, pixels, enemyBorder, allyBorder, minSenD, finalSc: rawLandSc * mult };
    };

    const evals = [];
    let maxRawLand = 0;
    for (const c of candSet) {
      const res = evalCandidate(c);
      if (res) {
        evals.push(res);
        if (res.rawLandSc > maxRawLand) maxRawLand = res.rawLandSc;
      }
    }

    if (evals.length > 0) {
      // Hard floor on Voronoi land size: never pick a spot with < 55% of the best available Voronoi land on the map!
      const viable = evals.filter((r) => r.rawLandSc >= 0.55 * maxRawLand);
      const pool = viable.length > 0 ? viable : evals;
      pool.sort((a, b) => b.finalSc - a.finalSc);
      return { x: pool[0].x, y: pool[0].y };
    }

    return super.chooseSpawn(g, final);
  }

  otherHumanMedDens(g) {
    const me = this.me, H = g.humans;
    const ds = [];
    for (let p = 0; p < H; p++) {
      if (p !== me && !this.isTeammate(g, p) && g.alive[p] && g.terr[p] >= 100 && !g.isBot(p)) {
        ds.push(g.bal[p] / g.terr[p]);
      }
    }
    if (!ds.length) return null;
    ds.sort((a, b) => a - b);
    return ds[ds.length >> 1];
  }

  livingHumanCount(g) {
    let n = 0;
    for (let p = 0; p < g.humans; p++) {
      if (!this.isTeammate(g, p) && g.alive[p] && g.terr[p] >= 100 && !g.isBot(p)) n++;
    }
    return Math.max(1, n);
  }

  topOtherHuman(g) {
    const me = this.me, H = g.humans;
    let bestP = -1, bestL = 0;
    for (let p = 0; p < H; p++) {
      if (p !== me && !this.isTeammate(g, p) && g.alive[p] && g.terr[p] > bestL && !g.isBot(p)) {
        bestL = g.terr[p];
        bestP = p;
      }
    }
    return bestP;
  }

  // AUTO PEACE VOTE CALL & ACCEPT:
  // When our team controls >= 60% of the map (or in mop-up), press KeyP to call/accept the peace vote!
  tryPeaceVote(g) {
    if (typeof document === "undefined" || g.t < 2000 || g.t - (this.lastPeaceKeyTick ?? -999) < 35) return;
    const me = this.me;
    let ourTeamLand = g.terr[me] || 0;
    if (g.teams && g.teams[me] > 0) {
      ourTeamLand = 0;
      for (let p = 0; p < g.players; p++) {
        if (g.alive[p] && g.teams[p] === g.teams[me]) ourTeamLand += g.terr[p];
      }
    }
    if (ourTeamLand >= 0.60 * Math.max(1, g.land) || this.isMopUp(g)) {
      this.lastPeaceKeyTick = g.t;
      try {
        document.dispatchEvent(new KeyboardEvent("keydown", { code: "KeyP", key: "p", bubbles: true, cancelable: true }));
        document.dispatchEvent(new KeyboardEvent("keyup", { code: "KeyP", key: "p", bubbles: true, cancelable: true }));
      } catch {}
    }
  }

  // BOSS SUPPORT: CASH DONATION FIRST, ~10% LIGHT ASSIST SECOND!
  // "最好的解围是给钱，打人只是附和10个点左右"
  tryEmergencyBossRescue(g) {
    const me = this.me;
    if (!g.teams || !(g.teams[me] > 0) || !g.canAct(me)) return false;
    const bossId = this.findBossId(g);
    if (bossId < 0 || !g.alive[bossId] || g.terr[bossId] < 50) return false;

    const B = g.bal[me], L = Math.max(1, g.terr[me]), dMe = B / L;
    const B_boss = g.bal[bossId], L_boss = Math.max(1, g.terr[bossId]), dBoss = B_boss / L_boss;

    let bossInAtk = 0, bossOutAtk = 0;
    const bossAttackers = [];
    for (const a of g.attackersOf(bossId)) {
      if (a !== me && !this.isTeammate(g, a)) {
        const tr = g.attackTroopsOn(a, bossId);
        bossInAtk += tr;
        if (!g.isBot(a) || tr > 0.08 * B_boss) bossAttackers.push({ q: a, tr, isEnemyAtk: true });
      }
    }
    const sbB = g.slotBase(bossId);
    for (let i = 0; i < g.atkCount[bossId]; i++) {
      const tgt = g.atkTarget[sbB + i];
      if (tgt >= 0 && tgt < g.humans && !g.isBot(tgt) && !this.isTeammate(g, tgt)) {
        const tr = g.atkTroops[sbB + i];
        bossOutAtk += tr;
        if (!bossAttackers.some(x => x.q === tgt)) bossAttackers.push({ q: tgt, tr, isEnemyAtk: false });
      }
    }

    // 1. PRIMARY: Give cash (donate) to Boss npl, distinguishing PURE INLAND LOCKED vs COASTAL REAR vs FRONTLINE!
    if (typeof g.donate === "function" && g.t >= 350) {
      let myHumanInAtk = 0;
      for (const a of g.attackersOf(me)) {
        if (!g.isBot(a) && !this.isTeammate(g, a)) myHumanInAtk += g.attackTroopsOn(a, me);
      }
      const enemyHumanNbs = this.nb.filter((p) => g.alive[p] && this.person(g, p));
      const hasExposedCoast = (g.coast?.[me]?.length ?? 0) > 0;
      // Coastal rear bots MUST keep >= 68*L anti-boat-sneak-attack reserve so their back is never stolen by sea!
      const coastGuardFloor = hasExposedCoast && g.t >= 1100 ? 68 * L : 18 * L;
      const safeFloor = Math.max(coastGuardFloor, enemyHumanNbs.length > 0 ? this.safeAt(g, -1) : 0);
      const isPureInlandSafe = enemyHumanNbs.length === 0 && !hasExposedCoast && myHumanInAtk === 0;
      const isCoastalRearSafe = enemyHumanNbs.length === 0 && hasExposedCoast && myHumanInAtk === 0;
      const isUnderThreat = myHumanInAtk > 0 || B <= 1.10 * safeFloor;

      if (!isUnderThreat) {
        const underEmergencyFire = bossInAtk > 0 && (bossInAtk >= 0.03 * B_boss || dBoss < 95);
        const bossFightingHuman = bossOutAtk > 0 && dBoss < 115;
        const bossNeedsCash = g.t >= 950 && dBoss < 118;
        const boxedIn = this.nb.length === 0 && this.neutral === 0 && dBoss < 142;

        const minKeepDens = isPureInlandSafe ? (underEmergencyFire ? 15 : 22) : isCoastalRearSafe ? (underEmergencyFire ? 52 : 72) : (underEmergencyFire ? 58 : 78);
        const canAfford = dMe >= minKeepDens && B > 1.10 * safeFloor;

        const cooldown = isPureInlandSafe ? (underEmergencyFire ? 10 : 18) : (underEmergencyFire ? 15 : 25);
        if ((underEmergencyFire || bossFightingHuman || bossNeedsCash || boxedIn) && canAfford && g.t - (this.lastBossDonateTick ?? -999) >= cooldown) {
          const maxSurplus = Math.max(0, B - Math.max(safeFloor, (minKeepDens - 10) * L));
          const maxPct = Math.floor((maxSurplus * 1024) / Math.max(1, B));
          const targetPct = isPureInlandSafe
            ? (underEmergencyFire ? 350 : boxedIn ? 320 : 220)
            : isCoastalRearSafe
              ? (underEmergencyFire ? 220 : 160)
              : (underEmergencyFire ? 150 : 115);
          const pct = Math.min(maxPct, targetPct);
          if (pct >= 55 && g.donate(pct, bossId, me)) {
            this.lastDonateTick = g.t;
            this.lastBossDonateTick = g.t;
            this.cmds++;
            return true;
          }
        }
      }
    }

    // 2. SECONDARY: Light ~10%B (pct=102/1024) assist poke ONLY if we share a land border and have healthy density!
    if (bossAttackers.length > 0 && B >= 8000 && dMe >= 38) {
      bossAttackers.sort((a, b) => (b.isEnemyAtk - a.isEnemyAtk) || (b.tr - a.tr));
      for (const { q } of bossAttackers) {
        if (!g.alive[q] || g.terr[q] < 100) continue;
        if ((this.cnt[q] ?? 0) > 0 && !g.hasAttack(me, q) && g.hasFreeSlot(me)) {
          if (g.attack(102, q, me)) { // ~10.0%B light assist!
            this.cmds++;
            this.hitTo.set(q, g.t);
            return true;
          }
        }
      }
    }
    return false;
  }

  // General Teammate Donation (prioritizing Boss npl first, then frontline squad teammates)
  tryDonateToTeammate(g) {
    const me = this.me;
    if (!g.teams || !(g.teams[me] > 0) || typeof g.donate !== "function") return false;
    if (g.t < 400 || g.t - (this.lastDonateTick ?? -999) < 18) return false;
    const B = g.bal[me], L = Math.max(1, g.terr[me]), dMe = B / L;
    const boxedIn = this.nb.length === 0 && this.neutral === 0;

    let myHumanInAtk = 0;
    for (const a of g.attackersOf(me)) {
      if (!g.isBot(a) && !this.isTeammate(g, a)) myHumanInAtk += g.attackTroopsOn(a, me);
    }
    const enemyHumanNbs = this.nb.filter((p) => g.alive[p] && this.person(g, p));
    const hasExposedCoast = (g.coast?.[me]?.length ?? 0) > 0;
    const coastGuardFloor = hasExposedCoast && g.t >= 1100 ? 68 * L : 18 * L;
    const safeFloor = Math.max(coastGuardFloor, enemyHumanNbs.length > 0 ? this.safeAt(g, -1) : 0);
    const isPureInlandSafe = enemyHumanNbs.length === 0 && !hasExposedCoast && myHumanInAtk === 0;
    if (myHumanInAtk > 0 || B <= 1.10 * safeFloor) return false;

    const maxSurplus = Math.max(0, B - 1.08 * safeFloor);
    const maxSafePct = Math.floor((maxSurplus * 1024) / Math.max(1, B));
    if (maxSafePct < 55) return false;

    // 1. Always check Boss "npl" first!
    const bossId = this.findBossId(g);
    if (bossId >= 0 && g.alive[bossId] && g.terr[bossId] >= 100) {
      const dBoss = g.bal[bossId] / Math.max(1, g.terr[bossId]);
      let bossInAtk = 0, bossOutAtk = 0;
      for (const a of g.attackersOf(bossId)) bossInAtk += g.attackTroopsOn(a, bossId);
      const sbB = g.slotBase(bossId);
      for (let i = 0; i < g.atkCount[bossId]; i++) {
        if (g.atkTarget[sbB + i] !== 512) bossOutAtk += g.atkTroops[sbB + i];
      }
      const bossNeedsHelp =
        (bossInAtk > 0 && dMe >= (isPureInlandSafe ? 16 : 55)) ||
        (bossOutAtk > 0.04 * g.bal[bossId] && dBoss < 120 && dMe >= (isPureInlandSafe ? 25 : 68)) ||
        (g.t >= 900 && dBoss < 118 && dMe >= (isPureInlandSafe ? 32 : 75)) ||
        (boxedIn && isPureInlandSafe && dBoss < 142 && dMe >= 18);
      if (bossNeedsHelp && g.t - (this.lastBossDonateTick ?? -999) >= (isPureInlandSafe ? 15 : 25)) {
        const pct = Math.min(maxSafePct, isPureInlandSafe ? (bossInAtk > 0 ? 340 : 240) : 150);
        if (pct >= 55 && g.donate(pct, bossId, me)) {
          this.lastDonateTick = g.t;
          this.lastBossDonateTick = g.t;
          this.cmds++;
          return true;
        }
      }
    }

    // 2. SQUAD MUTUAL AID: Rescue any [NPL] squad brother who is under human attack or sneaky boat landing,
    //    AND lightly poke (10%B) the attacker if we border them!
    for (let p = 0; p < g.humans; p++) {
      if (p === me || !g.alive[p] || !this.isTeammate(g, p) || !this.isOurSquadBot(g, p) || g.terr[p] < 300) continue;
      const dAlly = g.bal[p] / Math.max(1, g.terr[p]);
      let inHumanAtk = 0, mainAttacker = -1, maxAtkTr = 0;
      for (const a of g.attackersOf(p)) {
        if (!g.isBot(a) && !this.isTeammate(g, a)) {
          const tr = g.attackTroopsOn(a, p);
          inHumanAtk += tr;
          if (tr > maxAtkTr) { maxAtkTr = tr; mainAttacker = a; }
        }
      }
      if (inHumanAtk > 0 && (inHumanAtk >= 0.08 * g.bal[p] || dAlly < 75)) {
        // First donate cash to save our brother (while keeping our own coastGuardFloor / safeFloor intact!)
        if (dMe >= Math.max(55, dAlly + 15)) {
          const pct = Math.min(maxSafePct, isPureInlandSafe ? 240 : 155);
          if (pct >= 55 && g.donate(pct, p, me)) {
            this.lastDonateTick = g.t;
            this.cmds++;
            return true;
          }
        }
        // Second, if we border the attacker on land and aren't already attacking them, do a ~10%B light assist poke!
        if (mainAttacker >= 0 && (this.cnt[mainAttacker] ?? 0) > 0 && !g.hasAttack(me, mainAttacker) && g.hasFreeSlot(me) && dMe >= 65) {
          if (g.attack(102, mainAttacker, me)) {
            this.cmds++;
            this.hitTo.set(mainAttacker, g.t);
            return true;
          }
        }
      }
    }

    if (!boxedIn && dMe < 112) return false;
    if (boxedIn && dMe < 55) return false;

    let bestAlly = -1, bestScore = -Infinity;
    for (let p = 0; p < g.humans; p++) {
      if (p === me || !g.alive[p] || !this.isTeammate(g, p) || (!this.isBossNpl(g, p) && !this.isOurSquadBot(g, p)) || g.terr[p] < 600) continue;
      const dAlly = g.bal[p] / Math.max(1, g.terr[p]);
      if (dAlly >= 132) continue;
      let outAtk = 0, inAtk = 0;
      const sb = g.slotBase(p);
      for (let i = 0; i < g.atkCount[p]; i++) {
        const tgt = g.atkTarget[sb + i];
        if (tgt !== 512) outAtk += g.atkTroops[sb + i];
      }
      for (const a of g.attackersOf(p)) inAtk += g.attackTroopsOn(a, p);
      const allyEnemyNbs = this.peopleOf(g, p);
      if (!allyEnemyNbs.length && outAtk === 0 && inAtk === 0 && g.t > 2200) continue;
      const isBoss = p === bossId;
      const isSquad = this.isOurSquadBot(g, p);
      const score = (isBoss ? 5000 : isSquad ? 600 : 150) + (outAtk + inAtk) / 500 + (135 - dAlly) * 3 + Math.min(150, g.terr[p] / 500);
      if (score > bestScore && (isBoss || boxedIn || outAtk + inAtk > 0.04 * g.bal[p] || (isSquad && dMe >= 120 && dAlly < 98))) {
        bestScore = score;
        bestAlly = p;
      }
    }
    if (bestAlly < 0) return false;

    const pct = boxedIn ? (dMe > 110 ? 280 : 185) : 153;
    if (g.donate(pct, bestAlly, me)) {
      this.lastDonateTick = g.t;
      this.cmds++;
      return true;
    }
    return false;
  }"""
assert old_helpers in s, "old_helpers not found"
s = s.replace(old_helpers, new_helpers, 1)

# 6. Moderate focus-fire bias in offers(g) (no reckless over-retaliation)
old_other_atk = """        let otherAtk = 0, otherAtkers = 0;
        for (const a of g.attackersOf(q)) {
          if (a !== me && !g.isBot(a)) {
            otherAtkers++;
            otherAtk += g.attackTroopsOn(a, q);
          }
        }"""

new_other_atk = """        const bossId = this.findBossId(g);
        let otherAtk = 0, otherAtkers = 0, allyAtk = 0, clanAllyAtkers = 0, bossAtkOnQ = 0;
        for (const a of g.attackersOf(q)) {
          if (a !== me && !g.isBot(a)) {
            const tr = g.attackTroopsOn(a, q);
            otherAtkers++;
            otherAtk += tr;
            if (a === bossId) bossAtkOnQ += tr;
            if (this.isTeammate(g, a)) {
              allyAtk += tr;
              clanAllyAtkers += this.isOurSquadBot(g, a) ? 2 : 1;
            }
          }
        }
        let atkOnAlly = 0, atkOnBoss = 0;
        if (g.teams && g.teams[me] > 0) {
          const sbQ = g.slotBase(q);
          for (let i = 0; i < g.atkCount[q]; i++) {
            const tgt = g.atkTarget[sbQ + i];
            if (tgt >= 0 && tgt < 512 && this.isTeammate(g, tgt)) {
              const tr = g.atkTroops[sbQ + i];
              atkOnAlly += tr;
              if (tgt === bossId) atkOnBoss += tr;
            }
          }
        }"""
assert old_other_atk in s, "old_other_atk not found"
s = s.replace(old_other_atk, new_other_atk, 1)

old_rank_mult = """        let rankMult = 1.0;"""
new_rank_mult = """        let rankMult = 1.0;
        if (atkOnBoss > 0 || bossAtkOnQ > 0) {
          // Moderate assist bias for Boss's target (10% poke already handled in tryEmergencyBossRescue)
          c *= 0.78;
          rankMult *= 0.72;
        } else if (clanAllyAtkers > 0 || allyAtk > 0.06 * Bq) {
          c *= 0.82;
          rankMult *= 0.78;
        } else if (atkOnAlly > 0.08 * Bq) {
          c *= 0.85;
          rankMult *= 0.82;
        }"""
assert old_rank_mult in s, "old_rank_mult not found"
s = s.replace(old_rank_mult, new_rank_mult, 1)

# 7. Call tryEmergencyBossRescue, tryPeaceVote, and tryDonateToTeammate in act(g)
old_early_act = """    if (g.t < P.coreFrom) {
      const before = this.cmds;"""

new_early_act = """    if (g.t < P.coreFrom) {
      this.analyze(g);
      if (this.tryEmergencyBossRescue(g) && g.online) return;
      const before = this.cmds;"""
assert old_early_act in s, "old_early_act not found"
s = s.replace(old_early_act, new_early_act, 1)

old_main_analyze = """    this.analyze(g);
    this.updateGrudges(g);
    this.updateWars(g);"""

new_main_analyze = """    this.analyze(g);
    this.tryPeaceVote(g);
    if (this.tryEmergencyBossRescue(g) && g.online) return;
    this.updateGrudges(g);
    this.updateWars(g);"""
assert old_main_analyze in s, "old_main_analyze not found"
s = s.replace(old_main_analyze, new_main_analyze, 1)

old_act_end = """    if (this.cmds === cmdsBefore) this.idleBoats(g);"""
new_act_end = """    if (this.cmds === cmdsBefore) this.tryDonateToTeammate(g);
    if (this.cmds === cmdsBefore) this.idleBoats(g);"""
assert old_act_end in s, "old_act_end not found"
s = s.replace(old_act_end, new_act_end, 1)

# 8. Team mop-up + Coastal Escape when land-locked by teammates + Multi-enemy-team frontline safeAt
old_mop = """  isMopUp(g) {
    const me = this.me;
    return this.nb.length === 0 && this.neutral === 0 && g.terr[me] >= 0.80 * g.land && this.livingHumanCount(g) <= 1;
  }"""

new_mop = """  isMopUp(g) {
    const me = this.me;
    if (g.teams && g.teams[me] > 0) {
      let enemyAlive = false;
      for (let p = 0; p < g.players; p++) {
        if (g.alive[p] && g.terr[p] > 0 && g.teams[p] !== g.teams[me]) {
          enemyAlive = true;
          break;
        }
      }
      if (!enemyAlive && this.nb.length === 0 && this.neutral === 0) return true;
    }
    return this.nb.length === 0 && this.neutral === 0 && g.terr[me] >= 0.80 * g.land && this.livingHumanCount(g) <= 1;
  }"""
assert old_mop in s, "old_mop not found"
s = s.replace(old_mop, new_mop, 1)

old_safe_at = """  safeAt(g, q) {
    let s = super.safeAt(g, q);
    const P = this.p, me = this.me, L = Math.max(1, g.terr[me]);"""

new_safe_at = """  safeAt(g, q) {
    let s = super.safeAt(g, q);
    const P = this.p, me = this.me, L = Math.max(1, g.terr[me]);
    if (g.teams && g.teams[me] > 0 && g.t >= 900) {
      // If we border >= 2 enemy humans from the SAME enemy team, guard against their coordinated focus fire
      const teamBals = new Map();
      const teamCnts = new Map();
      for (const p of this.nb) {
        if (p !== q && g.alive[p] && this.person(g, p) && !this.isTeammate(g, p)) {
          const t = g.teams[p] || 0;
          if (t > 0) {
            teamBals.set(t, (teamBals.get(t) || 0) + g.bal[p]);
            teamCnts.set(t, (teamCnts.get(t) || 0) + 1);
          }
        }
      }
      for (const [t, cnt] of teamCnts.entries()) {
        if (cnt >= 2) {
          const combBal = teamBals.get(t) || 0;
          s = Math.max(s, Math.min(112 * L, 0.38 * combBal));
        }
      }
    }"""
assert old_safe_at in s, "old_safe_at not found"
s = s.replace(old_safe_at, new_safe_at, 1)

old_search_food = """  searchFood(g) {
    if (this.isMopUp(g)) {"""

new_search_food = """  searchFood(g) {
    // If land-locked by teammates (no neutral, no enemy/bot land neighbours) but we have coast,
    // expand boat range so we can hop across water to open a new front!
    if (!this.isMopUp(g) && this.nb.length === 0 && this.neutral === 0 && (g.coast?.[this.me]?.length ?? 0) > 0 && g.t >= 450) {
      const oldRange = this.p.boatRange;
      this.p.boatRange = Math.max(oldRange, 1600);
      const hit = super.searchFood(g);
      this.p.boatRange = oldRange;
      if (hit) hit.eff = Math.min(hit.eff, this.p.botMax * 0.85);
      return hit;
    }
    if (this.isMopUp(g)) {"""
assert old_search_food in s, "old_search_food not found"
s = s.replace(old_search_food, new_search_food, 1)

with open("/tmp/v27-team-live.js", "w") as f:
    f.write(s)

print("Successfully built Cash-First + 10%-Assist + Auto-Peace-Vote /tmp/v27-team-live.js! Size:", len(s))
