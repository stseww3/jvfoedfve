with open("/tmp/fdvg-c58/territorial-sim/strategy/pool/v33-live.js") as f:
    s = f.read()

# 0. Filter teammates out of v33's updatePokeState and tryDeterrentCounter, and disable solo tryPeaceVoteWin
old_poke_loop = """  updatePokeState(g, checkCnt = false) {
    const me = this.me, B = g.bal[me];
    if (B <= 0) return;
    for (let q = 0; q < g.humans; q++) {
      if (q === me || !g.alive[q] || g.isBot(q)) continue;"""

new_poke_loop = """  updatePokeState(g, checkCnt = false) {
    const me = this.me, B = g.bal[me];
    if (B <= 0) return;
    for (let q = 0; q < g.humans; q++) {
      if (q === me || !g.alive[q] || g.isBot(q) || (g.teams && g.teams[me] > 0 && g.teams[q] === g.teams[me])) continue;"""
assert old_poke_loop in s, "old_poke_loop not found"
s = s.replace(old_poke_loop, new_poke_loop, 1)

old_deter_loop = """    for (let q = 0; q < g.humans; q++) {
      if (q === me || !g.alive[q] || g.isBot(q)) continue;"""

new_deter_loop = """    for (let q = 0; q < g.humans; q++) {
      if (q === me || !g.alive[q] || g.isBot(q) || (g.teams && g.teams[me] > 0 && g.teams[q] === g.teams[me])) continue;"""
assert old_deter_loop in s, "old_deter_loop not found"
s = s.replace(old_deter_loop, new_deter_loop, 1)

old_solo_peace = """    if (this.tryPeaceVoteWin(g) && g.online) return;"""
assert old_solo_peace in s, "old_solo_peace not found"
s = s.replace(old_solo_peace, "", 1)

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
      low.includes("noah88") || low.includes("leo_tx")
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
      low === "ethan21" || low === "ryan_m" || low === "noah88" || low === "leo_tx"
    );
  }

  // CENTRALIZED BACKEND-COORDINATED TEAM SPAWNING (TeamSpawnCoordinator):
  // 1) Reports map terrain (once per match) + live human positions (Boss npl, enemies, allies)
  //    to the unified backend coordinator in tsb-team-squad.mjs via window.__hlSpawnReq.
  // 2) Returns the globally optimized, role-based (FLANK_GUARD / ECO_BANK) coordinate
  //    assigned by the backend via window.__tsbAssignedSpawn.
  chooseSpawn(g, final = true) {
    const me = this.me;
    const W = g.W, H = g.H;
    const squadIds = [];
    for (let p = 0; p < g.humans; p++) {
      if (p === me || (this.isOurSquadBot(g, p) && !this.isBossNpl(g, p))) {
        squadIds.push(p);
      }
    }
    const rankIdx = Math.max(0, squadIds.indexOf(me));
    const squadCount = Math.max(1, squadIds.length);
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
      let mapType = undefined;
      let packedLandB64 = undefined;
      if (needMap) {
        const rawMap = g.map?.type || g.px;
        if (typeof window.__tsbSpawnReq === "function" && rawMap) {
          const nBytes = (W * H + 7) >> 3;
          const bytes = new Uint8Array(nBytes);
          for (let i = 0; i < W * H; i++) {
            const v = rawMap[i];
            if (v === 1 || v >= 16) bytes[i >> 3] |= 1 << (i & 7);
          }
          let bin = "";
          for (let i = 0; i < nBytes; i += 4096) {
            bin += String.fromCharCode.apply(null, bytes.subarray(i, Math.min(nBytes, i + 4096)));
          }
          packedLandB64 = btoa(bin);
        } else {
          mapType = rawMap;
        }
      }
      const curX = g.terr[me] > 0 ? ((g.x0[me] + g.x1[me]) >> 1) : -1;
      const curY = g.terr[me] > 0 ? ((g.y0[me] + g.y1[me]) >> 1) : -1;
      window.__hlSpawnReq({
        matchKey: mapKey,
        W,
        H,
        land: g.land,
        me,
        slot: window.__tsbSquadSlot ?? rankIdx,
        rankIdx,
        squadCount,
        myTeam: g.teams ? (g.teams[me] | 0) : 0,
        curX,
        curY,
        humans,
        mapType,
        packedLandB64,
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
        window.__hlLog(`[HL-SPAWN-BACKEND] me=${me} slot=${res.slot ?? rankIdx} role=${res.role || "SQUAD"} -> (${res.x},${res.y}) bossDist=${res.bossDist ?? -1} minAllyDist=${res.minAllyDist ?? -1} voronoi=${res.voronoiPixels ?? -1}`);
      }
      return { x: res.x, y: res.y };
    }

    // Zero-gap synchronous fallback for Frame 1 before the 20ms backend reply arrives:
    // Deterministic multi-basin Farthest-Point sampling across the interior land grid (margin >= 18px)
    const mType = g.map?.type || g.px;
    const bossPts = [];
    const enemyPts = [];
    for (let h = 0; h < g.humans; h++) {
      if (h === me || g.terr[h] <= 0 || this.isOurSquadBot(g, h)) continue;
      const hx = (g.x0[h] + g.x1[h]) >> 1, hy = (g.y0[h] + g.y1[h]) >> 1;
      if (this.isBossNpl(g, h)) bossPts.push({ x: hx, y: hy });
      else if (!this.isTeammate(g, h)) enemyPts.push({ x: hx, y: hy });
    }
    const bossMin = Math.max(95, Math.min(165, 0.12 * Math.hypot(W, H)));
    const picked = [];
    for (let sIdx = 0; sIdx <= rankIdx; sIdx++) {
      let bestPt = null, bestScore = -Infinity;
      for (let y = 18; y < H - 18; y += 12) {
        for (let x = 18; x < W - 18; x += 12) {
          const c = y * W + x;
          if (mType[c] !== 1 && mType[c] < 16) continue;
          let bDist = 999999;
          for (const b of bossPts) bDist = Math.min(bDist, Math.hypot(x - b.x, y - b.y));
          if (bossPts.length > 0 && bDist < bossMin) continue;
          let eDist = 999999;
          for (const e of enemyPts) eDist = Math.min(eDist, Math.hypot(x - e.x, y - e.y));
          let aDist = 999999;
          for (const p of picked) aDist = Math.min(aDist, Math.hypot(x - p.x, y - p.y));
          const sc = Math.min(aDist, 320) * 1.8 + Math.min(eDist, 240) * 1.2 + (bossPts.length && sIdx < 2 ? -Math.abs(bDist - 190) * 0.6 : 0);
          if (sc > bestScore) {
            bestScore = sc;
            bestPt = { x, y };
          }
        }
      }
      if (bestPt) picked.push(bestPt);
    }
    if (picked.length > 0) {
      return picked[picked.length - 1];
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

  // AUTO PEACE VOTE CALL & ACCEPT (WITH HUMAN-LIKE JITTER DELAY):
  // ONLY initiate or vote YES on peace when ALL enemies are completely wiped out (isMopUp(g) === true)!
  // Stagger votes by 8~52 ticks (~0.5s to 2.9s) per bot so all 8 bots never vote on the exact same tick!
  tryPeaceVote(g) {
    if (typeof window === "undefined" || !window.ax || !window.dictionary || g.t < 1610) return;
    const me = this.me;
    const hz = window[window.dictionary.sbCommands]?.hz;
    if (!hz) return;
    if (!this.isMopUp(g)) {
      this._peaceReadyTick = 0;
      return;
    }
    if (!this._peaceReadyTick) {
      const slot = Number.isInteger(window.__tsbSquadSlot) ? window.__tsbSquadSlot : (me % 8);
      const jitter = 8 + ((slot * 6 + (me % 5) * 3) % 44);
      this._peaceReadyTick = g.t + jitter;
    }
    if (g.t < this._peaceReadyTick) return;
    const caller = window.__lastPeaceCaller;
    const callerIsOurs =
      Number.isInteger(caller) &&
      caller >= 0 &&
      caller < g.humans &&
      (caller === me || this.isOurSquadBot(g, caller) || this.isBossNpl(g, caller));
    if (window.ax.iL && typeof window.ax.iM === "function" && window.ax.iM(me)) {
      if (callerIsOurs && typeof hz.iN === "function") {
        hz.iN(1);
        this._peaceReadyTick = g.t + 35;
        if (window.__hlLog && g.t - (this._lastPeaceVoteLog ?? -999) >= 100) {
          this._lastPeaceVoteLog = g.t;
          window.__hlLog(`[HL-PEACE] t=${g.t} voted YES on our squad's mop-up peace call by p=${caller}(${g.names?.[caller] || ""})`);
        }
      }
    } else if (!window.ax.iL && g.t - (this.lastPeaceKeyTick ?? -999) >= 115 + (me % 7) * 5 && typeof window.ax.iO === "function" && window.ax.iO(me)) {
      this.lastPeaceKeyTick = g.t;
      window.__lastPeaceCaller = me;
      if (typeof hz.iK === "function") {
        hz.iK();
        if (window.__hlLog) window.__hlLog(`[HL-PEACE] t=${g.t} initiated mop-up peace vote (all enemies eliminated!)`);
      }
    }
  }

  // BOSS SUPPORT: CASH DONATION FIRST, ~10% LIGHT ASSIST SECOND!
  // "最好的解围是给钱，打人只是附和10个点左右"
  tryEmergencyBossRescue(g) {
    const me = this.me;
    if (!g.teams || !(g.teams[me] > 0) || !g.canAct(me)) return false;
    const bossId = this.findBossId(g);
    if (bossId < 0 || !g.alive[bossId] || g.terr[bossId] < 30) return false;

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

    // 1. PRIMARY: Give cash (donate) to Boss npl while keeping our own safe density so we never collapse ourselves!
    if (typeof g.donate === "function" && g.t >= 350) {
      let myHumanInAtk = 0;
      for (const a of g.attackersOf(me)) {
        if (!g.isBot(a) && !this.isTeammate(g, a)) myHumanInAtk += g.attackTroopsOn(a, me);
      }
      const enemyHumanNbs = this.nb.filter((p) => g.alive[p] && this.person(g, p));
      const hasExposedCoast = (g.coast?.[me]?.length ?? 0) > 0;
      const isPureInlandSafe = enemyHumanNbs.length === 0 && !hasExposedCoast && myHumanInAtk === 0;
      const isCoastalRearSafe = enemyHumanNbs.length === 0 && hasExposedCoast && myHumanInAtk === 0;

      const underEmergencyFire = bossInAtk > 0 && (bossInAtk >= 0.03 * B_boss || dBoss < 95);
      const bossFightingHuman = bossOutAtk > 0 && dBoss < 115;
      const bossNeedsCash = g.t >= 900 && dBoss < 118;
      const boxedIn = this.nb.length === 0 && this.neutral === 0 && dBoss < 142;

      // Healthy density floor so guard bots stay strong & never suicide while feeding Boss cash
      const minKeepDens = isPureInlandSafe
        ? (underEmergencyFire ? 15 : 22)
        : isCoastalRearSafe
          ? (underEmergencyFire ? 48 : 65)
          : (underEmergencyFire ? 52 : 70);
      const canAfford = myHumanInAtk === 0 && dMe >= minKeepDens && B >= 4000;

      const cooldown = isPureInlandSafe ? (underEmergencyFire ? 15 : 24) : (underEmergencyFire ? 20 : 30);
      if ((underEmergencyFire || bossFightingHuman || bossNeedsCash || boxedIn) && canAfford && g.t - (this.lastBossDonateTick ?? -999) >= cooldown) {
        const keepBal = (minKeepDens - 5) * L;
        const maxSurplus = Math.max(0, B - keepBal);
        const maxPct = Math.floor((maxSurplus * 1024) / Math.max(1, B));
        const pct = Math.min(maxPct, 51); // Strictly 5% (51/1024) per bot so guards stay strong and win even if Boss dies!
        if (pct >= 40 && g.donate(pct, bossId, me)) {
          this.lastDonateTick = g.t;
          this.lastBossDonateTick = g.t;
          this.cmds++;
          if (typeof window !== "undefined" && window.__hlLog) {
            window.__hlLog(`[HL-DONATE] t=${g.t} emergency boss donate pct=${pct}/1024 (~5%) -> boss=${bossId}(${g.names?.[bossId] || "npl"}) myBal=${B} dMe=${Math.round(dMe)} dBoss=${Math.round(dBoss)}`);
          }
          return true;
        }
      }
    }

    // 2. SECONDARY: Light ~10%B (pct=102/1024) assist poke ONLY if we share a land border and have healthy density (dMe >= 55)!
    if (bossAttackers.length > 0 && B >= 8000 && dMe >= 55) {
      bossAttackers.sort((a, b) => (b.isEnemyAtk - a.isEnemyAtk) || (b.tr - a.tr));
      for (const { q } of bossAttackers) {
        if (!g.alive[q] || g.terr[q] < 100) continue;
        if ((this.cnt[q] ?? 0) > 0 && !g.hasAttack(me, q) && g.hasFreeSlot(me)) {
          if (g.attack(102, q, me)) { // ~10.0%B light assist only!
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
    if (maxSafePct < 45) return false;

    // 1. Always check Boss "npl" first! (Strictly 5% = 51/1024 per bot)
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
        (bossInAtk > 0 && dMe >= (isPureInlandSafe ? 25 : 65)) ||
        (bossOutAtk > 0.04 * g.bal[bossId] && dBoss < 120 && dMe >= (isPureInlandSafe ? 32 : 75)) ||
        (g.t >= 900 && dBoss < 118 && dMe >= (isPureInlandSafe ? 38 : 80)) ||
        (boxedIn && isPureInlandSafe && dBoss < 142 && dMe >= 25);
      if (bossNeedsHelp && g.t - (this.lastBossDonateTick ?? -999) >= (isPureInlandSafe ? 20 : 30)) {
        const pct = Math.min(maxSafePct, 51);
        if (pct >= 40 && g.donate(pct, bossId, me)) {
          this.lastDonateTick = g.t;
          this.lastBossDonateTick = g.t;
          this.cmds++;
          if (typeof window !== "undefined" && window.__hlLog) {
            window.__hlLog(`[HL-DONATE] t=${g.t} boss donate pct=${pct}/1024 (~5%) -> boss=${bossId}(${g.names?.[bossId] || "npl"}) myBal=${B} dMe=${Math.round(dMe)}`);
          }
          return true;
        }
      }
    }

    // 2. SQUAD MUTUAL AID: Rescue any [NPL] squad brother who is under human attack or sneaky boat landing,
    //    AND lightly poke (10%B) the attacker if we border them! (Strictly 5% = 51/1024 donate)
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
        // First donate 5% cash to save our brother (while keeping our own coastGuardFloor / safeFloor intact!)
        if (dMe >= Math.max(65, dAlly + 18)) {
          const pct = Math.min(maxSafePct, 51);
          if (pct >= 40 && g.donate(pct, p, me)) {
            this.lastDonateTick = g.t;
            this.cmds++;
            if (typeof window !== "undefined" && window.__hlLog) {
              window.__hlLog(`[HL-DONATE] t=${g.t} squad rescue donate pct=${pct}/1024 (~5%) -> ally=${p}(${g.names?.[p] || ""}) myBal=${B} dMe=${Math.round(dMe)} dAlly=${Math.round(dAlly)}`);
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

    if (!boxedIn && dMe < 115) return false;
    if (boxedIn && dMe < 65) return false;

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

    const pct = 51; // Strictly 5% (51/1024)
    if (g.donate(pct, bestAlly, me)) {
      this.lastDonateTick = g.t;
      this.cmds++;
      if (typeof window !== "undefined" && window.__hlLog) {
        window.__hlLog(`[HL-DONATE] t=${g.t} surplus donate pct=${pct}/1024 (~5%) -> ally=${bestAlly}(${g.names?.[bestAlly] || ""}) boxedIn=${boxedIn} myBal=${B} dMe=${Math.round(dMe)}`);
      }
      return true;
    }
    return false;
  }"""
assert old_helpers in s, "old_helpers not found"
s = s.replace(old_helpers, new_helpers, 1)

# 6. Moderate focus-fire bias in offers(g) (no reckless over-retaliation)
old_other_atk = """        let otherAtk = 0, otherAtkers = 0, outOther = 0;
        for (const a of g.attackersOf(q)) {
          if (a !== me && !g.isBot(a)) {
            otherAtkers++;
            otherAtk += g.attackTroopsOn(a, q);
          }
        }"""

new_other_atk = """        const bossId = this.findBossId(g);
        let otherAtk = 0, otherAtkers = 0, outOther = 0, allyAtk = 0, clanAllyAtkers = 0, bossAtkOnQ = 0;
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
    this.updatePokeState(g, true);
    this.updateGrudges(g);
    this.updateWars(g);"""

new_main_analyze = """    this.analyze(g);
    this.updatePokeState(g, true);
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
s = s.replace(old_main_analyze, new_main_analyze, 1)

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

with open("/tmp/v27-team-live.js", "w") as f:
    f.write(s)

print("Successfully built Cash-First + 10%-Assist + Auto-Peace-Vote /tmp/v27-team-live.js! Size:", len(s))
