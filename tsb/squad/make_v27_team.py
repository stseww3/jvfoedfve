with open("/tmp/fdvg-c58/territorial-sim/strategy/pool/v27-live.js") as f:
    s = f.read()

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

# 4. Filter teammates out of doorHarvestCandidates, seaPeople, and bankAct
old_door_harvest = """              if (o !== me && o < H && g.alive[o] && g.terr[o] >= 600) {"""
new_door_harvest = """              if (o !== me && o < H && g.alive[o] && g.terr[o] >= 600 && !(g.teams && g.teams[me] > 0 && g.teams[o] === g.teams[me])) {"""
assert old_door_harvest in s, "old_door_harvest not found"
s = s.replace(old_door_harvest, new_door_harvest, 1)

old_sea_people = """    for (const s of seaSample(g, this.me, 64, rnd)) if (s.o >= 0 && g.alive[s.o] && this.person(g, s.o) && !out.includes(s.o)) out.push(s.o);"""
new_sea_people = """    for (const s of seaSample(g, this.me, 64, rnd)) if (s.o >= 0 && g.alive[s.o] && this.person(g, s.o) && !(g.teams && g.teams[this.me] > 0 && g.teams[s.o] === g.teams[this.me]) && !out.includes(s.o)) out.push(s.o);"""
assert old_sea_people in s, "old_sea_people not found"
s = s.replace(old_sea_people, new_sea_people, 1)

old_bank_act = """    for (const s of seaSample(g, me, 64, rnd)) {
      if (s.d < P.bankMin || s.d > P.boatRange) continue;
      const price = s.o < 0 ? 2 : this.price(g, s.o);"""
new_bank_act = """    for (const s of seaSample(g, me, 64, rnd)) {
      if (s.d < P.bankMin || s.d > P.boatRange) continue;
      if (s.o >= 0 && g.teams && g.teams[me] > 0 && g.teams[s.o] === g.teams[me]) continue;
      const price = s.o < 0 ? 2 : this.price(g, s.o);"""
assert old_bank_act in s, "old_bank_act not found"
s = s.replace(old_bank_act, new_bank_act, 1)

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

  // Identify our Boss ("[Nope]kazerd183" / "[NPL] npl", excluding our guard bot names)
  isBossNpl(g, p) {
    if (p === this.me || !g.alive[p]) return false;
    const raw = String(g.names?.[p] ?? "").trim();
    const low = raw.toLowerCase();
    if (
      low.includes("mishi") || low.includes("matzz") || low.includes("kiholma") ||
      low.includes("leo_99") || low.includes("racoon") || low.includes("zexos") ||
      low.includes("talon") || low.includes("vortex") || low.includes("kronos") || low.includes("nexus") ||
      low.includes("777") || low.includes("sayo") || low.includes("kaito") ||
      low.includes("riku") || low.includes("_alex") || low.includes("tomo") ||
      low.includes("zero_2") || low.includes("sora") ||
      low.includes("lucas94") || low.includes("dave_w") || low.includes("mark07") ||
      low.includes("kevin_k") || low.includes("ethan21") || low.includes("ryan_m") ||
      low.includes("noah88") || low.includes("leo_tx") || low.includes("jake_09") || low.includes("owen_h") ||
      low.includes("liam_c") || low.includes("mason22") || low.includes("logan_b") || low.includes("caleb14") ||
      low.includes("isaac_v") || low.includes("nolan81") || low.includes("eli_fox") || low.includes("wyatt04") ||
      low.includes("carter7") || low.includes("luke_r")
    ) {
      return false;
    }
    const stripped = raw.replace(/\\[[^\\]]*\\]/g, "").trim().toLowerCase();
    return stripped === "kazerd183" || stripped.includes("kazerd") || low.includes("kazerd183") || stripped === "npl" || stripped.includes("npl") || low === "[npl]npl";
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
    return (
      low === "mishi" || low === "matzz" || low === "kiholma" || low === "leo_99" || low === "racoon" ||
      low === "zexos" || low === "talon" || low === "vortex" || low === "kronos" || low === "nexus" ||
      low === "777" || low === "sayo" || low === "kaito" || low === "riku" ||
      low === "_alex" || low === "tomo" || low === "zero_2" || low === "sora" ||
      low === "lucas94" || low === "dave_w" || low === "mark07" || low === "kevin_k" ||
      low === "ethan21" || low === "ryan_m" || low === "noah88" || low === "leo_tx" ||
      low === "jake_09" || low === "owen_h" || low === "liam_c" || low === "mason22" ||
      low === "logan_b" || low === "caleb14" || low === "isaac_v" || low === "nolan81" ||
      low === "eli_fox" || low === "wyatt04" || low === "carter7" || low === "luke_r" ||
      raw.toUpperCase().includes("[NPL]") || raw.toUpperCase().includes("[NOPE]")
    );
  }

  // DISTRIBUTED BACKEND-COORDINATED TEAM SPAWNING:
  // 1) Reports map terrain + live human positions to the unified backend coordinator in tsb-team-squad.mjs
  //    ONLY when Boss [Nope]kazerd183 is present in the match (so 20 guards form a protective cluster around Boss).
  // 2) In autonomous 20-brother matches (without Boss), uses the original 80%-winrate distributed Voronoi
  //    spawnVsPeople(gClean) with TWO critical fixes:
  //      - Fixed slot = window.__tsbSquadSlot (0..19) so all 20 workers have deterministic, non-overlapping slots
  //        even when joining on different frames;
  //      - Erase ALL squad bots from gClean AND include gClean's human count in spawnKey so cached spawnOut
  //        never leaks a squadmate's own coordinates!
  chooseSpawn(g, final = true) {
    const me = this.me;
    const W = g.W, H = g.H;
    const mySquadIdx = typeof window !== "undefined" && Number.isInteger(window.__tsbSquadSlot) ? window.__tsbSquadSlot : 0;
    const squadIds = [];
    for (let p = 0; p < g.humans; p++) {
      if (p === me || (this.isOurSquadBot(g, p) && !this.isBossNpl(g, p))) {
        squadIds.push(p);
      }
    }
    const rankIdx = Math.max(0, squadIds.indexOf(me));
    const squadCount = Math.max(20, squadIds.length);
    const slot = mySquadIdx % 20;

    // Check if Boss [Nope]kazerd183 is in this match
    const bossId = this.findBossId(g);
    if (bossId >= 0) {
      const mapKey = `${W}x${H}_${g.land}_${g.humans}`;
      const nowMs = typeof performance !== "undefined" ? performance.now() : Date.now();
      if (typeof window !== "undefined" && window.__hlSpawnReq && (!this._lastSpawnReqAt || nowMs - this._lastSpawnReqAt > 260)) {
        this._lastSpawnReqAt = nowMs;
        const humans = [];
        for (let p = 0; p < g.humans; p++) {
          const terr = g.terr[p] | 0;
          humans.push({
            id: p,
            name: String(g.names?.[p] ?? ""),
            team: g.teams ? (g.teams[p] | 0) : 0,
            terr,
            x: terr > 0 ? ((g.x0[p] + g.x1[p]) >> 1) : -1,
            y: terr > 0 ? ((g.y0[p] + g.y1[p]) >> 1) : -1,
          });
        }
        const needMap = window.__lastSentSpawnMapKey !== mapKey;
        if (needMap) window.__lastSentSpawnMapKey = mapKey;
        const mapType = needMap ? (g.map?.type || g.px) : undefined;
        const curX = g.terr[me] > 0 ? ((g.x0[me] + g.x1[me]) >> 1) : -1;
        const curY = g.terr[me] > 0 ? ((g.y0[me] + g.y1[me]) >> 1) : -1;
        window.__hlSpawnReq({
          matchKey: mapKey, W, H, land: g.land, me, slot, rankIdx, squadCount,
          myTeam: g.teams ? (g.teams[me] | 0) : 0, curX, curY, humans, mapType,
        });
      }
      if (
        typeof window !== "undefined" &&
        window.__tsbAssignedSpawn &&
        Number.isInteger(window.__tsbAssignedSpawn.x) &&
        (!window.__tsbAssignedSpawn.mapW || (window.__tsbAssignedSpawn.mapW === W && window.__tsbAssignedSpawn.mapH === H))
      ) {
        const res = window.__tsbAssignedSpawn;
        if (window.__hlLog && (!this._lastLogSpawn || Math.hypot(res.x - this._lastLogSpawn.x, res.y - this._lastLogSpawn.y) > 4)) {
          this._lastLogSpawn = { x: res.x, y: res.y };
          window.__hlLog(`[HL-SPAWN-BACKEND] me=${me} slot=${res.slot ?? slot} role=${res.role || "SQUAD"} -> (${res.x},${res.y}) bossDist=${res.bossDist ?? -1} minAllyDist=${res.minAllyDist ?? -1} voronoi=${res.voronoiPixels ?? -1}`);
        }
        return { x: res.x, y: res.y };
      }
    }

    // Autonomous 20-brother distributed Voronoi spawn (original 36b5718 logic with fixed slot 0..19 and clean cache):
    const minSep = Math.max(85, Math.min(145, 0.14 * Math.hypot(W, H)));
    let gClean = g;
    for (const sid of squadIds) {
      if (sid !== me && gClean.terr[sid] > 0) {
        gClean = withoutPlayer(gClean, sid);
      }
    }

    // Throttle expensive spawnVsPeople BFS to at most once every 2200ms during spawnPhase so Worker never lags >3000ms!
    const nowSpawnMs = typeof performance !== "undefined" ? performance.now() : Date.now();
    if (!this._cachedSpawnCands || !this._lastSpawnCalcMs || nowSpawnMs - this._lastSpawnCalcMs > 2200 || this._cachedSpawnW !== W) {
      this._lastSpawnCalcMs = nowSpawnMs;
      this._cachedSpawnW = W;
      let rawCands = this.spawnVsPeople ? this.spawnVsPeople(gClean, 48) : [];
      if (!rawCands || rawCands.length < 32) {
        const more = this.spawnCandidates(gClean, 48) || [];
        rawCands = [...(rawCands || []), ...more];
      }
      this._cachedSpawnCands = rawCands;
    }
    let cands = this._cachedSpawnCands;
    if (cands && cands.length > 0) {
      const comp = this.compSize ? this.compSize(gClean) : null;
      const minMainLand = Math.min(18000, Math.floor(0.18 * Math.max(1, g.land)));
      const chosenSlots = [];
      for (const pos of cands) {
        const x = typeof pos === "object" ? pos.x : (pos % W);
        const y = typeof pos === "object" ? pos.y : Math.floor(pos / W);
        if (comp && comp[y * W + x] > 0 && comp[y * W + x] < minMainLand) continue;
        let tooClose = false;
        for (const prev of chosenSlots) {
          if (Math.hypot(x - prev.x, y - prev.y) < minSep) { tooClose = true; break; }
        }
        if (!tooClose) {
          chosenSlots.push({ x, y });
          if (chosenSlots.length > slot) break;
        }
      }
      // If fewer than slot+1 candidates pass minSep, relax minSep to 0.65x so slots never collide
      if (chosenSlots.length <= slot) {
        const relaxSep = minSep * 0.62;
        for (const pos of cands) {
          const x = typeof pos === "object" ? pos.x : (pos % W);
          const y = typeof pos === "object" ? pos.y : Math.floor(pos / W);
          if (comp && comp[y * W + x] > 0 && comp[y * W + x] < minMainLand) continue;
          if (chosenSlots.every((p) => Math.hypot(x - p.x, y - p.y) >= relaxSep)) {
            chosenSlots.push({ x, y });
            if (chosenSlots.length > slot) break;
          }
        }
      }
      let res = chosenSlots[slot] || cands[slot % cands.length];
      if (!chosenSlots[slot] && chosenSlots.length > 0) {
        // Fallback: Farthest-Point Sampling across the main-continent free land grid (pxArr[idx] === 1 = T_LAND) so all 10 slots are guaranteed >= 160px apart!
        const pxArr = gClean.px;
        for (let sIdx = chosenSlots.length; sIdx <= slot; sIdx++) {
          let bestPt = null, bestD = -1;
          for (let y = 18; y < H - 18; y += 16) {
            for (let x = 18; x < W - 18; x += 16) {
              const idx = y * W + x;
              if (pxArr[idx] !== 1) continue;
              if (comp && comp[idx] > 0 && comp[idx] < minMainLand) continue;
              let minD = 999999;
              for (const p of chosenSlots) minD = Math.min(minD, Math.hypot(x - p.x, y - p.y));
              for (let h = 0; h < gClean.humans; h++) {
                if (h !== me && gClean.terr[h] > 0) {
                  const hx = (gClean.x0[h] + gClean.x1[h]) >> 1, hy = (gClean.y0[h] + gClean.y1[h]) >> 1;
                  minD = Math.min(minD, Math.hypot(x - hx, y - hy) * 1.15);
                }
              }
              if (minD > bestD) {
                bestD = minD;
                bestPt = { x, y };
              }
            }
          }
          if (bestPt) chosenSlots.push(bestPt);
        }
        res = chosenSlots[slot] || res;
      }
      res = typeof res === "object" ? res : { x: res % W, y: Math.floor(res / W) };
      if (typeof window !== "undefined" && window.__hlLog && (!this._lastLogSpawn || Math.hypot(res.x - this._lastLogSpawn.x, res.y - this._lastLogSpawn.y) > 6)) {
        this._lastLogSpawn = res;
        window.__hlLog(`[HL-SPAWN] me=${me} slot=${slot} (squad=${squadIds.length},rankIdx=${rankIdx}) -> (${res.x},${res.y}) chosenSlots=${chosenSlots.length}/${cands.length} minSep=${Math.round(minSep)}`);
      }
      return res;
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
  // ONLY vote YES if the peace vote was initiated by OUR squad (or Boss npl)! Never auto-accept random players' peace votes!
  tryPeaceVote(g) {
    if (typeof window === "undefined" || !window.ax || !window.dictionary || g.t < 1610) return;
    const me = this.me;
    const hz = window[window.dictionary.sbCommands]?.hz;
    if (!hz) return;
    let ourTeamLand = g.terr[me] || 0;
    if (g.teams && g.teams[me] > 0) {
      ourTeamLand = 0;
      for (let p = 0; p < g.players; p++) {
        if (g.alive[p] && g.teams[p] === g.teams[me]) ourTeamLand += g.terr[p];
      }
    }
    const weLead = ourTeamLand >= 0.58 * Math.max(1, g.land) || this.isMopUp(g);
    const caller = window.__lastPeaceCaller;
    const callerIsOurs =
      Number.isInteger(caller) &&
      caller >= 0 &&
      caller < g.humans &&
      (caller === me || this.isOurSquadBot(g, caller) || this.isBossNpl(g, caller));
    if (window.ax.iL && typeof window.ax.iM === "function" && window.ax.iM(me)) {
      if (callerIsOurs && typeof hz.iN === "function") {
        hz.iN(1);
        if (window.__hlLog && g.t - (this._lastPeaceVoteLog ?? -999) >= 100) {
          this._lastPeaceVoteLog = g.t;
          window.__hlLog(`[HL-PEACE] t=${g.t} voted YES on our squad's peace call by p=${caller}(${g.names?.[caller] || ""}) (teamLand=${(100 * ourTeamLand / Math.max(1, g.land)).toFixed(1)}%)`);
        }
      }
    } else if (!window.ax.iL && weLead && g.t - (this.lastPeaceKeyTick ?? -999) >= 105 && typeof window.ax.iO === "function" && window.ax.iO(me)) {
      this.lastPeaceKeyTick = g.t;
      window.__lastPeaceCaller = me;
      if (typeof hz.iK === "function") {
        hz.iK();
        if (window.__hlLog) window.__hlLog(`[HL-PEACE] t=${g.t} initiated peace vote (teamLand=${(100 * ourTeamLand / Math.max(1, g.land)).toFixed(1)}%)`);
      }
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
            if (typeof window !== "undefined" && window.__hlLog) {
              window.__hlLog(`[HL-DONATE] t=${g.t} emergency boss donate pct=${pct}/1024 -> boss=${bossId}(${g.names?.[bossId] || "npl"}) myBal=${B} dMe=${Math.round(dMe)} dBoss=${Math.round(dBoss)}`);
            }
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
            if (typeof window !== "undefined" && window.__hlLog) {
              window.__hlLog(`[HL-ASSIST] t=${g.t} 10% boss-assist poke -> target=${q}(${g.names?.[q] || ""}) myBal=${B} dMe=${Math.round(dMe)}`);
            }
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
          if (typeof window !== "undefined" && window.__hlLog) {
            window.__hlLog(`[HL-DONATE] t=${g.t} boss donate pct=${pct}/1024 -> boss=${bossId}(${g.names?.[bossId] || "npl"}) myBal=${B} dMe=${Math.round(dMe)}`);
          }
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
            if (typeof window !== "undefined" && window.__hlLog) {
              window.__hlLog(`[HL-DONATE] t=${g.t} squad rescue donate pct=${pct}/1024 -> ally=${p}(${g.names?.[p] || ""}) myBal=${B} dMe=${Math.round(dMe)} dAlly=${Math.round(dAlly)}`);
            }
            return true;
          }
        }
        // Second, if we border the attacker on land and aren't already attacking them, do a ~10%B light assist poke!
        if (mainAttacker >= 0 && (this.cnt[mainAttacker] ?? 0) > 0 && !g.hasAttack(me, mainAttacker) && g.hasFreeSlot(me) && dMe >= 65) {
          if (g.attack(102, mainAttacker, me)) {
            this.cmds++;
            this.hitTo.set(mainAttacker, g.t);
            if (typeof window !== "undefined" && window.__hlLog) {
              window.__hlLog(`[HL-ASSIST] t=${g.t} 10% squad-rescue poke -> enemy=${mainAttacker}(${g.names?.[mainAttacker] || ""}) for ally=${p}(${g.names?.[p] || ""})`);
            }
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
      if (typeof window !== "undefined" && window.__hlLog) {
        window.__hlLog(`[HL-DONATE] t=${g.t} surplus donate pct=${pct}/1024 -> ally=${bestAlly}(${g.names?.[bestAlly] || ""}) boxedIn=${boxedIn} myBal=${B} dMe=${Math.round(dMe)}`);
      }
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
      if (typeof window !== "undefined" && window.__hlLog && g.t > 0 && g.t % 90 === 0 && this._lastTickLog !== g.t) {
        this._lastTickLog = g.t;
        const pf = window.__hlPerf;
        const pfStr = pf && pf.ticks > 0 ? ` avgMs=${(pf.totalMs / pf.ticks).toFixed(2)} maxMs=${pf.maxMs.toFixed(1)} skip=${pf.skippedTicks}` : "";
        window.__hlLog(`[HL-TICK] t=${g.t} terr=${g.terr[me]}(${(100 * g.terr[me] / Math.max(1, g.land)).toFixed(1)}%) bal=${g.bal[me]} dens=${(g.bal[me] / Math.max(1, g.terr[me])).toFixed(1)} nb=${this.nb.length} neut=${this.neutral} cmds=${this.cmds} boats=${this.boats}${pfStr}`);
      }
      if (this.tryEmergencyBossRescue(g) && g.online) return;
      const before = this.cmds;"""
assert old_early_act in s, "old_early_act not found"
s = s.replace(old_early_act, new_early_act, 1)

old_main_analyze = """    this.analyze(g);
    this.updateGrudges(g);
    this.updateWars(g);"""

new_main_analyze = """    this.analyze(g);
    if (typeof window !== "undefined" && window.__hlLog && g.t > 0 && g.t % 90 === 0 && this._lastTickLog !== g.t) {
      this._lastTickLog = g.t;
      const pf = window.__hlPerf;
      const pfStr = pf && pf.ticks > 0 ? ` avgMs=${(pf.totalMs / pf.ticks).toFixed(2)} maxMs=${pf.maxMs.toFixed(1)} skip=${pf.skippedTicks}` : "";
      window.__hlLog(`[HL-TICK] t=${g.t} terr=${g.terr[me]}(${(100 * g.terr[me] / Math.max(1, g.land)).toFixed(1)}%) bal=${g.bal[me]} dens=${(g.bal[me] / Math.max(1, g.terr[me])).toFixed(1)} nb=${this.nb.length} neut=${this.neutral} cmds=${this.cmds} boats=${this.boats}${pfStr}`);
    }
    this.tryPeaceVote(g);
    if (this.tryEmergencyBossRescue(g) && g.online) return;
    this.updateGrudges(g);
    this.updateWars(g);"""
assert old_main_analyze in s, "old_main_analyze not found"
s = s.replace(old_main_analyze, new_main_analyze)

old_act_end = """    if (this.cmds === cmdsBefore) this.idleBoats(g);"""
new_act_end = """    if (this.cmds === cmdsBefore) this.tryDonateToTeammate(g);
    if (this.cmds === cmdsBefore) this.idleBoats(g);"""
assert old_act_end in s, "old_act_end not found"
s = s.replace(old_act_end, new_act_end, 1)

# 8. Team mop-up & Opening DP log
old_dp_send = """    if (this.send(g, NEUTRAL, X)) this.dpCyc = cyc;"""
new_dp_send = """    if (this.send(g, NEUTRAL, X)) {
      this.dpCyc = cyc;
      if (typeof window !== "undefined" && window.__hlLog) {
        window.__hlLog(`[HL-OPENING] t=${g.t} cyc=${cyc} DP expand rings=${n} spend=${Math.round(X)}/${bal} terr=${g.terr[me]}`);
      }
    }"""
assert old_dp_send in s, "old_dp_send not found"
s = s.replace(old_dp_send, new_dp_send, 1)

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

# 9. Unlock v27 opening neutral & AI-bot expansion in crowded Team lobbies
old_dp_neutral = """    const fee = iV(12 * bal, 1024);
    const max = Math.min(P.dpSpend * bal, bal - this.dpKeep(g)) - fee;
    if (!(max > 0)) return;
    const rings = this.dpRings(g, u);
    let n = 0, sum = 0;
    for (const { r } of rings) {
      if (2 * (sum + r) + r > max) break;
      sum += r;
      n++;
    }
    if (n === 0) return;
    let later = 0;
    for (const { at } of rings) if (at + P.period <= 98) later++;
    if (later >= n) return;
    const X = 2 * sum + rings[n - 1].r;
    if (X < this.minCmd(g)) return;"""

new_dp_neutral = """    const fee = iV(12 * bal, 1024);
    const keepCap = this.neutral > 0 ? Math.min(this.dpKeep(g), Math.floor(0.50 * bal)) : this.dpKeep(g);
    const max = Math.min(P.dpSpend * bal, bal - keepCap) - fee;
    if (!(max > 0)) return;
    const rings = this.dpRings(g, u);
    let n = 0, sum = 0;
    for (const { r } of rings) {
      if (2 * (sum + r) + r > max) break;
      sum += r;
      n++;
    }
    if (n === 0) return;
    const isFinitePocket = n === rings.length && rings.length <= 8 && g.t >= 450;
    let later = 0;
    for (const { at } of rings) if (at + P.period <= 98) later++;
    if (!isFinitePocket && later >= n) return;
    const X = 2 * sum + rings[n - 1].r;
    const effMin = isFinitePocket ? Math.min(this.minCmd(g), Math.max(80, 2 * fee)) : this.minCmd(g);
    if (X < effMin) return;"""
assert old_dp_neutral in s, "old_dp_neutral not found"
s = s.replace(old_dp_neutral, new_dp_neutral, 1)

old_floor_for0 = """  floorFor0(g, q, f) {
    const P = this.p;
    if (P.winR > 0 && g.t < P.dpEnd && !this.person(g, q)) return Math.max(this.winFloor(g, q), this.peopleFloor(g));"""

new_floor_for0 = """  floorFor0(g, q, f) {
    const P = this.p;
    if (P.winR > 0 && g.t < P.dpEnd && !this.person(g, q)) {
      const L = Math.max(1, g.terr[this.me]), B = g.bal[this.me];
      const botKeepCap = Math.min(35 * L, Math.floor(0.55 * B));
      const baseWin = (this.botPx(g, q) * L) / (P.winR * Math.max(1, g.t));
      return Math.max(baseWin, Math.min(Math.max(this.dpKeep(g), this.peopleFloor(g), this.sb || 0), botKeepCap));
    }"""
assert old_floor_for0 in s, "old_floor_for0 not found"
s = s.replace(old_floor_for0, new_floor_for0, 1)

old_early_transition = """      super.act(g);
      if (this.cmds > before && g.bal[me] <= 0.75 * balBefore) {
        this.lastLandSpendTick = g.t;
      }"""

new_early_transition = """      super.act(g);
      if (this.cmds === before && g.t >= 600 && this.neutral > 0 && g.attackTroopsOn(me, NEUTRAL) === 0) {
        const grab = Math.min(Math.floor(0.35 * g.bal[me]), Math.max(this.minCmd(g), 4 * this.neutral + 120));
        if (grab > 0 && g.bal[me] - grab > 12 * Math.max(1, g.terr[me])) this.send(g, NEUTRAL, grab);
      }
      if (this.cmds === before && g.t >= 750 && this.neutral === 0 && !this.hasBorderFood(g)) {
        this.buyLand(g);
        if (this.cmds === before) this.tryDonateToTeammate(g);
      }
      if (this.cmds > before && g.bal[me] <= 0.75 * balBefore) {
        this.lastLandSpendTick = g.t;
      }"""
assert old_early_transition in s, "old_early_transition not found"
s = s.replace(old_early_transition, new_early_transition, 1)

old_safe_at = """    if (q < 0 || !this.person(g, q)) {
      s = Math.min(s, P.oppFloorCap * L);
    } else if"""

new_safe_at = """    s = Math.min(s, P.oppFloorCap * L);
    if (q < 0 || !this.person(g, q)) {
      s = Math.min(s, P.oppFloorCap * L);
    } else if"""
assert old_safe_at in s, "old_safe_at not found"
s = s.replace(old_safe_at, new_safe_at, 1)

old_over_pulse = """      keep = Math.max(keep, safe);

      const avail = B - fee - keep;
      if (avail <= 0) continue;

      if (!person) {
        const want = 1.25 * need + 3 * this.cnt[q];
        const x = Math.min(avail, want);
        if (x <= 0 || (x < want && x < P.chunk * B)) continue;
        return this.send(g, q, x);
      }

      const usePulseBlock =
        P.pulseFrac > 0 && (!over || (P.overPulseMode > 0 && (o.nearCollapse || o.bleeding || avail < P.chunk * B)));"""

new_over_pulse = """      keep = Math.max(keep, safe);
      if (dMe >= 132) {
        keep = Math.min(keep, 108 * L);
      }

      const avail = B - fee - keep;
      if (avail <= 0) continue;

      if (!person) {
        const want = 1.25 * need + 3 * this.cnt[q];
        const x = Math.min(avail, want);
        if (x <= 0 || (x < want && x < P.chunk * B)) continue;
        return this.send(g, q, x);
      }

      const usePulseBlock =
        P.pulseFrac > 0 && (!over || dMe >= 132 || (P.overPulseMode > 0 && (o.nearCollapse || o.bleeding || avail < P.chunk * B)));"""
assert old_over_pulse in s, "old_over_pulse not found"
s = s.replace(old_over_pulse, new_over_pulse, 1)

with open("/tmp/v27-team-live.js", "w") as f:
    f.write(s)

print("Successfully built Cash-First + 10%-Assist + Auto-Peace-Vote /tmp/v27-team-live.js! Size:", len(s))
