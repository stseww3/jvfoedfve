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

  // TEAM-SIZE-AWARE ARC CLUSTERING SPAWN:
  // 1. Evaluates enemy team sizes (e.g. 20-player enemy mega-team) and vetoes any spot inside
  //    an enemy pincer/surround or multi-octant cluster ("不要在人家20人中间生成").
  // 2. Dynamically scales squad clustering spacing based on enemy team size & total human count.
  // 3. Forms a 1-layer arc/crescent anchored on Boss [NPL]NPL or senior squadmate (p < me),
  //    enforcing >= 3 open compass rays (135°~180°+ outward expansion) for BOTH self and every
  //    teammate so nobody is EVER boxed in between teammates ("也别卡在队友中间出不去").
  chooseSpawn(g, final = true) {
    const me = this.me;
    const h = g.terr[me] > 0 ? withoutPlayer(g, me) : g;
    const W = h.W, H = h.H, N = h.N, px = h.px, d4 = h.dir4;
    const mapScale = Math.sqrt(Math.max(10000, h.land));

    if (!this.dEnemyBuf || this.dEnemyBuf.length !== N) {
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

    const enemies = [];
    const squadAllies = [];
    const wildAllies = [];
    let bossAlly = null;

    for (let p = 0; p < h.humans; p++) {
      if (p === me || h.terr[p] === 0) continue;
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

    const seniorAllies = [];
    if (bossAlly) seniorAllies.push(bossAlly);
    for (const a of squadAllies) {
      if (a.isSenior) seniorAllies.push(a);
    }
    const allPlacedAllies = [
      ...(bossAlly ? [bossAlly] : []),
      ...squadAllies,
      ...wildAllies
    ];

    // Precompute existing open cones for our placed squadmates & Boss so we never choke them
    const seniorBaseCones = new Map();
    for (const a of (bossAlly ? [bossAlly, ...squadAllies] : squadAllies)) {
      seniorBaseCones.set(a.p, this.evalOpenExpansionCone(h, a.x, a.y, allPlacedAllies, a.p));
    }

    // 2. Dynamic spacing based on enemy team size & human count
    let minAllySep, idealAllySep, maxAllySep;
    if (maxEnemyTeamSize >= 10 || h.humans >= 20) {
      // High-density / mega-team battle: tight arc clustering so 5 brothers fuse into a solid wall fast
      minAllySep = Math.round(Math.max(36, 0.060 * mapScale));
      idealAllySep = Math.round(Math.max(52, 0.086 * mapScale));
      maxAllySep = Math.round(Math.max(86, 0.140 * mapScale));
    } else if (maxEnemyTeamSize >= 5 || h.humans >= 12) {
      minAllySep = Math.round(Math.max(44, 0.072 * mapScale));
      idealAllySep = Math.round(Math.max(64, 0.104 * mapScale));
      maxAllySep = Math.round(Math.max(104, 0.168 * mapScale));
    } else {
      minAllySep = Math.round(Math.max(52, 0.085 * mapScale));
      idealAllySep = Math.round(Math.max(76, 0.125 * mapScale));
      maxAllySep = Math.round(Math.max(124, 0.195 * mapScale));
    }
    const minWildSep = Math.round(Math.max(30, 0.72 * minAllySep));

    // 3. BFS land distance maps to Enemies and to Teammates
    const dEnemy = enemies.length > 0
      ? Strategy.prototype.spawnDist.call(
          this,
          h,
          this.dEnemyBuf,
          (o) => o < h.humans && o !== me && !this.isTeammate(h, o) && !this.isOurSquadBot(h, o) && !this.isBossNpl(h, o)
        )
      : null;

    const dAlly = allPlacedAllies.length > 0
      ? Strategy.prototype.spawnDist.call(
          this,
          h,
          this.dAllyBuf,
          (o) => o < h.humans && o !== me && (this.isTeammate(h, o) || this.isOurSquadBot(h, o) || this.isBossNpl(h, o))
        )
      : null;

    const comp = this.compSize ? this.compSize(h) : null;
    const minLandmass = Math.min(25000, Math.floor(0.18 * h.land));

    // Enemy surround / pincer / mega-team heat evaluator
    const R_surr = Math.max(135, Math.min(240, 0.30 * mapScale));
    const R_pincer = Math.max(105, Math.min(175, 0.22 * mapScale));

    const evalEnemyRisk = (x, y) => {
      if (enemies.length === 0) return { veto: false, penalty: 0, minD: 999 };
      let minD = Infinity, heat = 0, octMask = 0;
      const teamOcts = new Map();
      const near = [];

      for (let i = 0; i < enemies.length; i++) {
        const e = enemies[i];
        const dx = e.x - x, dy = e.y - y;
        const d = Math.hypot(dx, dy);
        if (d < minD) minD = d;
        const minSafeE = 34 + Math.min(30, (e.teamSize - 1) * 1.4);
        if (d < minSafeE) return { veto: true, penalty: 1e9, minD: d };

        const tw = 1 + 0.35 * Math.min(25, e.teamSize - 1);
        heat += tw * Math.exp(-(d * d) / (2 * 115 * 115));

        if (d <= R_surr) {
          const oct = Math.floor(((Math.atan2(dy, dx) + Math.PI) / (2 * Math.PI)) * 8) & 7;
          octMask |= (1 << oct);
          if (e.team > 0) {
            let rec = teamOcts.get(e.team);
            if (!rec) { rec = { mask: 0, cnt: 0, size: e.teamSize }; teamOcts.set(e.team, rec); }
            rec.mask |= (1 << oct);
            rec.cnt++;
          }
        }
        if (d <= R_pincer) {
          near.push({ ux: dx / Math.max(1, d), uy: dy / Math.max(1, d), d, team: e.team, teamSize: e.teamSize });
        }
      }

      // Pincer / sandwich check: never spawn between two enemies!
      for (let i = 0; i < near.length; i++) {
        for (let j = i + 1; j < near.length; j++) {
          const e1 = near[i], e2 = near[j];
          const cosA = e1.ux * e2.ux + e1.uy * e2.uy;
          if (cosA < -0.38 && (e1.team === e2.team || e1.teamSize >= 5 || e2.teamSize >= 5 || (e1.d < 115 && e2.d < 115))) {
            return { veto: true, penalty: 1e9, minD };
          }
        }
      }

      // Multi-octant surround check
      let octCnt = 0;
      for (let b = 0; b < 8; b++) if ((octMask >> b) & 1) octCnt++;
      if (octCnt >= 4) return { veto: true, penalty: 1e9, minD };

      for (const rec of teamOcts.values()) {
        let tOcts = 0;
        for (let b = 0; b < 8; b++) if ((rec.mask >> b) & 1) tOcts++;
        if (rec.cnt >= 3 && tOcts >= 3) return { veto: true, penalty: 1e9, minD };
      }

      return { veto: false, penalty: heat * 170, minD };
    };

    // 4. Generate candidate positions:
    //    (a) Dense arc ring around seniorAllies (so followers always find the exact 45~90px frontline arc spots)
    //    (b) Teammate-Enemy Frontline Boundary candidates (50 <= dEnemy <= 195 and not buried behind wild teammates!)
    //    (c) Global open-land candidates (for small games or before enemies place)
    const candSet = new Set();
    const addCand = (x, y) => {
      if (x < 6 || y < 6 || x >= W - 6 || y >= H - 6) return;
      const c = y * W + x;
      if (px[c] !== T_LAND) return;
      if (comp && comp[c] > 0 && comp[c] < minLandmass) return;
      candSet.add(c);
    };

    const curPos = g.terr[me] > 0 ? ((g.y0[me] + g.y1[me]) >> 1) * W + ((g.x0[me] + g.x1[me]) >> 1) : -1;
    if (curPos >= 0) addCand(curPos % W, Math.floor(curPos / W));

    if (seniorAllies.length > 0) {
      const ringMax = maxAllySep + 32;
      for (const a of seniorAllies) {
        const x0 = Math.max(6, a.x - ringMax), x1 = Math.min(W - 7, a.x + ringMax);
        const y0 = Math.max(6, a.y - ringMax), y1 = Math.min(H - 7, a.y + ringMax);
        for (let y = y0; y <= y1; y += 8) {
          for (let x = x0; x <= x1; x += 8) {
            const d = Math.hypot(x - a.x, y - a.y);
            if (d >= minAllySep && d <= ringMax) addCand(x, y);
          }
        }
      }
    }

    const frontlineCands = [];
    const globalFar = [];
    for (let y = 8; y < H - 8; y += 10) {
      for (let x = 8; x < W - 8; x += 10) {
        const c = y * W + x;
        if (px[c] !== T_LAND) continue;
        if (comp && comp[c] > 0 && comp[c] < minLandmass) continue;
        const de = dEnemy ? dEnemy[c] : -1;
        const da = dAlly ? dAlly[c] : -1;
        if (de >= 48 && de <= 210 && (da < 0 || de <= da + 85)) {
          frontlineCands.push(c);
        } else if (de < 0 || de >= 45) {
          globalFar.push(c);
        }
      }
    }
    // Sort frontline candidates to prefer the sweet-spot buffer (~95px from enemy, close to ally support)
    if (dEnemy) {
      frontlineCands.sort((a, b) => {
        const scoreA = Math.abs(dEnemy[a] - 95) + (dAlly && dAlly[a] >= 0 ? Math.abs(dAlly[a] - 65) * 0.6 : 0);
        const scoreB = Math.abs(dEnemy[b] - 95) + (dAlly && dAlly[b] >= 0 ? Math.abs(dAlly[b] - 65) * 0.6 : 0);
        return scoreA - scoreB;
      });
      globalFar.sort((a, b) => (dEnemy[b] < 0 ? 400 : dEnemy[b]) - (dEnemy[a] < 0 ? 400 : dEnemy[a]));
    }
    for (let i = 0; i < Math.min(90, frontlineCands.length); i++) {
      const c = frontlineCands[i];
      addCand(c % W, Math.floor(c / W));
    }
    for (let i = 0; i < Math.min(35, globalFar.length); i++) {
      const c = globalFar[i];
      addCand(c % W, Math.floor(c / W));
    }
    for (const s of this.spawnCandidates(g, 10)) addCand(s.x, s.y);

    // 5. Score candidates with strict True-Voronoi Frontline Boundary & Non-Enclosure Rules
    const dd = this.dMineBuf, q = this.spawnQBuf;
    const scoreSpot = (s, strictCluster, requireFrontline) => {
      if (px[s] !== T_LAND) return -1e9;
      if (comp && comp[s] > 0 && comp[s] < minLandmass) return -1e9;
      const x = s % W, y = Math.floor(s / W);

      // Check minimum distance to all placed allies
      for (const a of (bossAlly ? [bossAlly, ...squadAllies] : squadAllies)) {
        if (Math.hypot(x - a.x, y - a.y) < minAllySep) return -1e9;
      }
      for (const w of wildAllies) {
        if (Math.hypot(x - w.x, y - w.y) < minWildSep) return -1e9;
      }

      // Check distance to seniorAllies when clustering
      let minSenD = Infinity;
      if (seniorAllies.length > 0) {
        for (const a of seniorAllies) {
          const d = Math.hypot(x - a.x, y - a.y);
          if (d < minSenD) minSenD = d;
        }
        if (strictCluster && minSenD > maxAllySep + 32) return -1e9;
      }

      // Check Enemy Mega-Team Risk & Surround Veto
      const eRisk = evalEnemyRisk(x, y);
      if (eRisk.veto) return -1e9;

      // Never step directly between a senior squadmate/Boss and their nearest enemy (which would wall them into the rear!)
      if (enemies.length > 0) {
        for (const a of (bossAlly ? [bossAlly, ...squadAllies] : squadAllies)) {
          const distAS = Math.hypot(x - a.x, y - a.y);
          if (distAS > 110) continue;
          let nearE = null, minED = Infinity;
          for (const e of enemies) {
            const de = Math.hypot(e.x - a.x, e.y - a.y);
            if (de < minED) { minED = de; nearE = e; }
          }
          if (nearE && minED < 260) {
            const ex = (nearE.x - a.x) / Math.max(1, minED), ey = (nearE.y - a.y) / Math.max(1, minED);
            const sx = (x - a.x) / Math.max(1, distAS), sy = (y - a.y) / Math.max(1, distAS);
            // If we spawn in a narrow 50° cone directly in front of ally 'a' toward their nearest enemy, veto!
            if (ex * sx + ey * sy > 0.68 && Math.hypot(nearE.x - x, nearE.y - y) < minED) {
              return -1e9;
            }
          }
        }
      }

      // Check No-Sandwich & Open Expansion Cone for SELF
      const selfCone = this.evalOpenExpansionCone(h, x, y, allPlacedAllies, me);
      if (selfCone.openCount < 3 || selfCone.maxContig < 2) return -1e9;

      // Check that we do NOT sandwich ourselves between two close allies
      const closeAllies = [];
      for (const a of allPlacedAllies) {
        const dx = a.x - x, dy = a.y - y;
        const d = Math.hypot(dx, dy);
        if (d <= 98) closeAllies.push({ ...a, ux: dx / Math.max(1, d), uy: dy / Math.max(1, d), d });
      }
      for (let i = 0; i < closeAllies.length; i++) {
        for (let j = i + 1; j < closeAllies.length; j++) {
          const a1 = closeAllies[i], a2 = closeAllies[j];
          if (a1.ux * a2.ux + a1.uy * a2.uy < -0.55 && a1.d < 88 && a2.d < 88 && selfCone.openCount < 4) {
            return -1e9;
          }
        }
      }

      // Check that placing at (x, y) does NOT box in Boss or any placed squadmate!
      const withMe = [...allPlacedAllies, { p: me, x, y }];
      let allyChokePenalty = 0;
      for (const a of (bossAlly ? [bossAlly, ...squadAllies] : squadAllies)) {
        const d = Math.hypot(x - a.x, y - a.y);
        if (d > 105) continue;
        const before = seniorBaseCones.get(a.p);
        const after = this.evalOpenExpansionCone(h, a.x, a.y, withMe, a.p);
        const minReq = a.isBoss ? Math.min(4, before ? before.openCount : 4) : Math.min(3, before ? before.openCount : 3);
        if (after.openCount < minReq || after.maxContig < 2) return -1e9;
        if (before && after.openCount < before.openCount) {
          allyChokePenalty += (before.openCount - after.openCount) * 140;
        }
      }

      // True Voronoi BFS (stopping at BOTH enemy Voronoi cells AND teammate Voronoi cells!):
      // Measures exact personal land `truePixels`, enemy frontline contact `enemyFront`, and teammate border `allyFront`.
      let qh = 0, qt = 0, landSc = 0;
      let truePixels = 0, enemyFront = 0, allyFront = 0;
      dd[s] = 0;
      q[qt++] = s;
      while (qh < qt) {
        const c = q[qh++];
        const dc = dd[c];
        truePixels++;
        const de = dEnemy ? dEnemy[c] : -1;
        const da = dAlly ? dAlly[c] : -1;
        const wE = de >= 0 ? Math.min(1, (de - dc) / 130) : 1;
        landSc += (wE * 420) / (240 + dc);
        if (dc >= 135) {
          if (de >= 0 && (da < 0 || de <= da + 25)) enemyFront++;
          else if (da >= 0) allyFront++;
          continue;
        }
        for (let k = 0; k < 4; k++) {
          const n = c + d4[k];
          if (dd[n] >= 0 || px[n] !== T_LAND) continue;
          const deN = dEnemy ? dEnemy[n] : -1;
          const daN = dAlly ? dAlly[n] : -1;
          const hitEnemy = deN >= 0 && dc + 1 >= deN;
          const hitAlly = daN >= 0 && dc + 1 >= daN;
          if (hitEnemy || hitAlly) {
            if (hitEnemy && (!hitAlly || deN <= daN + 6)) enemyFront++;
            else allyFront++;
            continue;
          }
          dd[n] = dc + 1;
          q[qt++] = n;
        }
      }
      for (let i = 0; i < qt; i++) dd[q[i]] = -1;

      // Never pick a tiny pocket boxed in by teammates/enemies/water!
      if (truePixels < 360) return -1e9;

      // FRONTLINE BOUNDARY ENFORCEMENT ("最好都在队友和敌人的边界处，不要完全被队友围住"):
      // If enemies exist on this landmass, we MUST have a direct Voronoi frontline facing the enemies (`enemyFront >= 12`)
      // rather than being 100% walled in behind wild teammates (`enemyFront === 0`)!
      const deHere = dEnemy ? dEnemy[s] : -1;
      const daHere = dAlly ? dAlly[s] : -1;
      if (deHere >= 0 && allPlacedAllies.length > 0) {
        if (requireFrontline && enemyFront < 12) return -1e9;
      }

      let total = landSc - eRisk.penalty - allyChokePenalty;
      total += selfCone.openCount * 95 + selfCone.maxContig * 75;

      // Frontline Boundary Bonus: reward spots right on the Teammate-Enemy interface!
      if (deHere >= 0) {
        if (enemyFront < 12) {
          // Heavily penalize being walled behind teammates with no path to enemies
          total -= 3200;
        } else {
          // Ideal frontline exposure: direct enemy contact on the front + ally contact on the rear/flank
          const frontScore = Math.min(450, enemyFront * 9);
          const supportScore = allyFront >= 8 ? 380 : 0;
          // Ideal buffer distance to nearest enemy on land: ~60..165 steps
          const distBonus = deHere >= 52 && deHere <= 175
            ? 620 - 4 * Math.abs(deHere - 100)
            : deHere > 175
              ? -Math.min(1400, (deHere - 175) * 8)
              : -600;
          // Ensure we are NOT deeper in the rear than our wild teammates (deHere <= daHere + 75)
          const notInRearBonus = (daHere >= 0 && deHere > daHere + 90) ? -1200 : 260;
          total += frontScore + supportScore + distBonus + notInRearBonus;
        }
      }

      // Safe backstop bonus: having 1~3 sectors backed by sea/map edge while >= 4 sectors are open land
      if (selfCone.terrainBlocked >= 1 && selfCone.terrainBlocked <= 3 && selfCone.openCount >= 4) {
        total += 190;
      }

      // Arc Cohesion Bonus around seniorAllies (lining up shoulder-to-shoulder along the frontline)
      if (seniorAllies.length > 0 && Number.isFinite(minSenD)) {
        if (minSenD <= maxAllySep + 32) {
          total += 1900 - 14 * Math.abs(minSenD - idealAllySep);
        } else {
          total -= (minSenD - maxAllySep) * 18;
        }
      }

      // Hysteresis stability bonus for current spot (only if it still has frontline!)
      if (s === curPos && (deHere < 0 || enemyFront >= 12)) total += 135;

      return total;
    };

    let bestS = -1, bestVal = -1e9;
    const useStrictCluster = seniorAllies.length > 0;
    // Pass 1: Strict cluster + strict frontline boundary (both beside squadmates AND facing enemies!)
    for (const c of candSet) {
      const v = scoreSpot(c, useStrictCluster, true);
      if (v > bestVal) {
        bestVal = v;
        bestS = c;
      }
    }

    // Pass 2: If seniorAllies spawned buried in the rear where no cluster spot has frontline,
    // break out to the nearest true Frontline Boundary spot!
    if (bestS < 0) {
      for (const c of candSet) {
        const v = scoreSpot(c, false, true);
        if (v > bestVal) {
          bestVal = v;
          bestS = c;
        }
      }
    }

    // Pass 3: Fallback if no enemies on landmass yet
    if (bestS < 0) {
      for (const c of candSet) {
        const v = scoreSpot(c, false, false);
        if (v > bestVal) {
          bestVal = v;
          bestS = c;
        }
      }
    }

    if (bestS >= 0) {
      // Fine local refinement (step 4, then 2) preserving frontline & non-enclosure vetoes
      for (const step of [4, 2]) {
        let improved = true;
        while (improved) {
          improved = false;
          const bx = bestS % W, by = Math.floor(bestS / W);
          for (const [dx, dy] of [[step, 0], [-step, 0], [0, step], [0, -step]]) {
            const nx = bx + dx, ny = by + dy;
            if (nx < 6 || ny < 6 || nx >= W - 6 || ny >= H - 6) continue;
            const nc = ny * W + nx;
            const v = scoreSpot(nc, false, true);
            if (v > bestVal) {
              bestVal = v;
              bestS = nc;
              improved = true;
            }
          }
        }
      }
      return { x: bestS % W, y: Math.floor(bestS / W) };
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
