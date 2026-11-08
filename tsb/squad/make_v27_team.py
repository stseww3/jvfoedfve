import os, re, json

with open("/tmp/fdvg-c58/territorial-sim/strategy/pool/v27-live.js") as f:
    s = f.read()

pool_js = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "name-pool.mjs"), encoding="utf-8").read()
pool_names = [m.group(1).strip().lower() for m in re.finditer(r'"([^"]+)"', pool_js)]
pool_set_js = """const SQUAD_POOL_SET = new Set(""" + json.dumps(sorted(list(set(pool_names)))) + """);
try {
  if (typeof window === "object") {
    if (typeof window.be === "object" && window.be) {
      window.be.render = function() {};
      window.be.a7W = function() {};
      window.be.a3K = function() {};
    }
    if (typeof window.nF === "function") window.nF = function() {};
    if (typeof window.a1C === "function") window.a1C = function() {};
    const sb = window.__fx?.strategyBot;
    if (sb && typeof sb.afterTick === "function" && !sb.__fixedInflight450) {
      sb.__fixedInflight450 = true;
      const prevAfterTick = sb.afterTick.bind(sb);
      sb.afterTick = function() {
        const curT = typeof window.bi === "object" && window.bi?.kr ? window.bi.kr() : -1;
        if (this.inflight !== null && performance.now() - this.inflight < 450 && curT >= 0 && curT - (this.inflightTick ?? 0) < 8) {
          this.afterQueued = false;
          return;
        }
        return prevAfterTick();
      };
    }
    const patchLoop = (loopObj) => {
      if (!loopObj || loopObj.__patchedFast42) return;
      loopObj.__patchedFast42 = true;
      loopObj.aXQ = function(aD) {
        if (window.aE?.hx) { this.aEZ(aD); return; }
        this.af3.push(aD);
        if (window.aE?.a38 === 1 && !window.aE.hx) {
          window.bi.eZ = performance.now();
          if (this.eZ > window.bi.eZ) this.eZ = window.bi.eZ;
          this.ee();
          return;
        }
        if (window.aE?.a38 === 2) {
          for (var aC = 0; aC < this.af3.length; aC++) { window.bB.qk.ee(this.af3[aC]); }
          this.af3 = [];
        }
      };
      loopObj.ee = function() {
        if (typeof window.i?.ee === "function") window.i.ee();
        if (window.aE?.hx) {
          if (window.__fx?.strategyBot?.beforeFrame) window.__fx.strategyBot.beforeFrame();
          window.bi.ds = window.aX.aEZ(-1) || window.bi.ds;
          window.nI();
        } else {
          if (this.af1 === this.aK3 * 7 && this.af3.length === 0) {
            this.eZ = window.bi.eZ;
            window.n6();
          } else {
            var _steps = 0;
            while (window.bi.eZ >= this.eZ && _steps++ < 35) {
              this.eZ += 42;
              if (window.aE?.a38 === 2) { window.n6(); break; }
              this.af6();
              if (this.af1 === this.aK3 * 7 && this.af3.length === 0) {
                this.eZ = window.bi.eZ;
                break;
              }
            }
            if (window.bi.eZ >= this.eZ) this.eZ = window.bi.eZ;
          }
          this.eI = 0;
        }
        window.nD();
        if (window.bi) {
          if (window.bi.ds) window.bi.ds = false;
          this.af5 = window.bi.eZ;
        }
      };
    };
    if (window.bi?.a3I && Array.isArray(window.bi.a3I.af3)) patchLoop(window.bi.a3I);
    if (window.bi && typeof window.bi.a7m === "function" && !window.bi.__patchedA7m) {
      window.bi.__patchedA7m = true;
      const origA7m = window.bi.a7m.bind(window.bi);
      window.bi.a7m = function() {
        origA7m();
        if (this.a3I && Array.isArray(this.a3I.af3)) patchLoop(this.a3I);
      };
    }
    const isBossReadyInLobby = () => {
      const w1 = window.bq?.wZ?.w1;
      const wa = window.bq?.wZ?.wa | 0;
      if (!Array.isArray(w1) || wa <= 0) return false;
      for (let i = 0; i < Math.min(wa, w1.length); i++) {
        const p = w1[i];
        if (!p) continue;
        const raw = String(p.aGT || p.aGM || p.aFN || p.username || p.name || "").trim();
        const low = raw.toLowerCase();
        if (!low || SQUAD_POOL_SET.has(low)) continue;
        const stripped = raw.replace(/\\[[^\\]]*\\]/g, "").trim().toLowerCase();
        if (SQUAD_POOL_SET.has(stripped)) continue;
        if (
          stripped === "kazerd183" || stripped.includes("kazerd") ||
          low.includes("kazerd") || stripped === "npl" ||
          low === "[npl]npl" || low.includes("auouf")
        ) {
          return true;
        }
      }
      return false;
    };
    const ensureLobbyHook = () => {
      const sH = window.bq?.sH;
      if (!sH || typeof sH.select !== "function") return;
      if (!sH.__origSelect) {
        sH.__origSelect = sH.select.bind(sH);
        sH.select = function(id) {
          if (id > 0) {
            if (!isBossReadyInLobby()) {
              if (this.wF > 0) return this.__origSelect(0);
              return;
            }
            const firstId = this.sH?.[0]?.id || id;
            if (this.wF === firstId) return;
            return this.__origSelect(firstId);
          }
          if (this.wF > 0) return this.__origSelect(0);
        };
      }
      if (window.bq?.f6 !== 1) return;
      const bossReady = isBossReadyInLobby();
      if ((window.__tsbSquadSlot | 0) === 0 && window.__hlLog && (!window.__lastLobbyWaitLog || Date.now() - window.__lastLobbyWaitLog > 8000)) {
        window.__lastLobbyWaitLog = Date.now();
        const w1 = window.bq?.wZ?.w1 || [];
        const wa = window.bq?.wZ?.wa | 0;
        const rdyNames = w1.slice(0, Math.min(wa, 25)).map(p => `${String(p?.aGT || p?.aGM || p?.username || "").trim()}(c=${p?.color})`).join(", ");
        const bossInAll = w1.find(p => {
          const r = String(p?.aGT || p?.aGM || p?.username || "").trim().toLowerCase();
          return r.includes("kazerd") || r.includes("npl") || r.includes("auouf");
        });
        window.__hlLog(`[LOBBY-WAIT] total=${w1.length} ready=${wa} bossReady=${bossReady} bossFound=${bossInAll ? (bossInAll.aGM || bossInAll.username) : "none"} rdyList=[${rdyNames}]`);
      }
      const firstId = sH.sH?.[0]?.id || 0;
      if (bossReady && firstId > 0 && sH.wF !== firstId && !sH.__joiningBoss) {
        sH.__joiningBoss = true;
        const slot = window.__tsbSquadSlot | 0;
        setTimeout(() => {
          sH.__joiningBoss = false;
          if (window.bq?.f6 === 1 && isBossReadyInLobby() && sH.sH?.[0]?.id > 0 && sH.wF !== sH.sH[0].id) {
            sH.__origSelect(sH.sH[0].id);
          }
        }, 40 + slot * 35);
      } else if (!bossReady && sH.wF > 0) {
        sH.__origSelect(0);
      }
    };
    if (window.__bossLobbyWatcher) clearInterval(window.__bossLobbyWatcher);
    window.__bossLobbyWatcher = setInterval(ensureLobbyHook, 200);
    ensureLobbyHook();
  }
} catch {}
"""
s = pool_set_js + s

# 1. Filter teammates AND (while wild outsiders are still alive) our own 20 squad brothers out of analyze(g)!
old_analyze = """          const o = own[c];
          if (o !== me) {
            mark[c] = st;
            if (cnt[o]++ === 0) this.nb.push(o);
          }"""

new_analyze = """          const o = own[c];
          if (o !== me && !this.isProtectedSquadMate(g, o)) {
            mark[c] = st;
            if (cnt[o]++ === 0) this.nb.push(o);
          }"""
assert old_analyze in s, "old_analyze not found"
s = s.replace(old_analyze, new_analyze, 1)

# 2. Filter teammates AND squad brothers out of peopleOf(g, q)
old_people_of = """        if (o === q || seen[o] === st) continue;
        seen[o] = st;
        if (g.alive[o] && !g.isBot(o)) s.push(o);"""

new_people_of = """        if (o === q || seen[o] === st) continue;
        seen[o] = st;
        if (g.alive[o] && !g.isBot(o) && !this.isProtectedSquadMate(g, o)) s.push(o);"""
assert old_people_of in s, "old_people_of not found"
s = s.replace(old_people_of, new_people_of, 1)

# 3. Filter teammates AND squad brothers out of searchWater(g)
old_search_water = """          const o = own[n];
          if (o === me || this.cnt[o] > 0 || (noBots && g.isBot(o) && !this.botOk(g, o))) continue;"""

new_search_water = """          const o = own[n];
          if (o === me || this.isProtectedSquadMate(g, o) || this.cnt[o] > 0 || (noBots && g.isBot(o) && !this.botOk(g, o))) continue;"""
assert old_search_water in s, "old_search_water not found"
s = s.replace(old_search_water, new_search_water, 1)

# 4. Filter teammates AND squad brothers out of doorHarvestCandidates, seaPeople, and bankAct
old_door_harvest = """              if (o !== me && o < H && g.alive[o] && g.terr[o] >= 600) {"""
new_door_harvest = """              if (o !== me && o < H && g.alive[o] && g.terr[o] >= 600 && !(g.teams && g.teams[me] > 0 && g.teams[o] === g.teams[me]) && !(g._wildAlive && SQUAD_POOL_SET.has(String(g.names?.[o] ?? "").trim().toLowerCase()))) {"""
assert old_door_harvest in s, "old_door_harvest not found"
s = s.replace(old_door_harvest, new_door_harvest, 1)

old_sea_people = """    for (const s of seaSample(g, this.me, 64, rnd)) if (s.o >= 0 && g.alive[s.o] && this.person(g, s.o) && !out.includes(s.o)) out.push(s.o);"""
new_sea_people = """    for (const s of seaSample(g, this.me, 64, rnd)) if (s.o >= 0 && g.alive[s.o] && this.person(g, s.o) && !this.isProtectedSquadMate(g, s.o) && !out.includes(s.o)) out.push(s.o);"""
assert old_sea_people in s, "old_sea_people not found"
s = s.replace(old_sea_people, new_sea_people, 1)

old_bank_act = """    for (const s of seaSample(g, me, 64, rnd)) {
      if (s.d < P.bankMin || s.d > P.boatRange) continue;
      const price = s.o < 0 ? 2 : this.price(g, s.o);"""
new_bank_act = """    for (const s of seaSample(g, me, 64, rnd)) {
      if (s.d < P.bankMin || s.d > P.boatRange) continue;
      if (s.o >= 0 && this.isProtectedSquadMate(g, s.o)) continue;
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
    const stripped = raw.replace(/\\[[^\\]]*\\]/g, "").trim().toLowerCase();
    if (SQUAD_POOL_SET.has(stripped) || SQUAD_POOL_SET.has(low)) return false;
    return stripped === "kazerd183" || stripped.includes("kazerd") || low.includes("kazerd183") || stripped === "npl" || low === "[npl]npl" || low.includes("auouf");
  }

  hasBossInMatch(g) {
    if (this._bossEnteredMatch) return true;
    for (let p = 0; p < g.humans; p++) {
      const raw = String(g.names?.[p] ?? "").trim();
      const low = raw.toLowerCase();
      const stripped = raw.replace(/\\[[^\\]]*\\]/g, "").trim().toLowerCase();
      if (SQUAD_POOL_SET.has(stripped) || SQUAD_POOL_SET.has(low)) continue;
      if (stripped === "kazerd183" || stripped.includes("kazerd") || low.includes("kazerd183") || stripped === "npl" || low === "[npl]npl" || low.includes("auouf")) {
        this._bossEnteredMatch = true;
        return true;
      }
    }
    return false;
  }

  findBossId(g) {
    for (let p = 0; p < g.humans; p++) {
      if (this.isBossNpl(g, p) && (this.isTeammate(g, p) || !g.teams)) return p;
    }
    return -1;
  }

  isOurSquadBot(g, p) {
    const raw = String(g.names?.[p] ?? "").trim();
    return SQUAD_POOL_SET.has(raw.toLowerCase()) || raw.toUpperCase().includes("[NPL]") || raw.toUpperCase().includes("[NOPE]");
  }

  hasWildOutsidersAlive(g) {
    if (g._wildCheckTick === g.t) return g._wildAlive;
    g._wildCheckTick = g.t;
    for (let p = 0; p < g.humans; p++) {
      if (g.alive[p] && g.terr[p] >= 80 && !g.isBot(p) && !this.isOurSquadBot(g, p) && !this.isBossNpl(g, p)) {
        g._wildAlive = true;
        return true;
      }
    }
    g._wildAlive = false;
    return false;
  }

  // While wild outsiders are alive on the map, protect all 20 squad brothers across teams so they cooperate;
  // Once all wild outsiders are dead (#7821), lift cross-team protection so only 1 team survives!
  isProtectedSquadMate(g, p) {
    if (this.isTeammate(g, p) || this.isBossNpl(g, p)) return true;
    return this.hasWildOutsidersAlive(g) && this.isOurSquadBot(g, p);
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
      if (p !== me && !this.isProtectedSquadMate(g, p) && g.alive[p] && g.terr[p] >= 100 && !g.isBot(p)) {
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
      if (!this.isProtectedSquadMate(g, p) && g.alive[p] && g.terr[p] >= 100 && !g.isBot(p)) n++;
    }
    return Math.max(1, n);
  }

  topOtherHuman(g) {
    const me = this.me, H = g.humans;
    let bestP = -1, bestL = 0;
    for (let p = 0; p < H; p++) {
      if (p !== me && !this.isProtectedSquadMate(g, p) && g.alive[p] && g.terr[p] > bestL && !g.isBot(p)) {
        bestL = g.terr[p];
        bestP = p;
      }
    }
    return bestP;
  }

  // PRIVATELY SEND SCALES EMOJI (r5 = 1015) TO BOSS EVERY 10s (180 ticks) (#8051):
  // Uses directed private emoji packet b1.qo.rK(1015, bossId) directly (bypassing aO.r4 canvas draw),
  // so ONLY Boss sees the scales icon above all 20 undercover brothers on the map!
  tryPrivateBossEmoji(g) {
    if (typeof window === "undefined" || !g.online) return;
    const me = this.me;
    if (!g.alive[me] || g.terr[me] <= 0) return;
    const slot = ((typeof window.__tsbSquadSlot === "number" ? window.__tsbSquadSlot : me) | 0) % 20;
    if (g.t < 25 + slot * 4) return;
    if (g.t - (this._lastBossEmojiTick ?? -999) < 180) return;
    let bossId = -1;
    for (let p = 0; p < g.humans; p++) {
      if (this.isBossNpl(g, p) && g.alive[p] && g.terr[p] > 0) {
        bossId = p;
        break;
      }
    }
    if (bossId < 0) return;
    this._lastBossEmojiTick = g.t;
    try {
      const d = window.dictionary;
      const b1Net = (d && window[d.sbNet]) || window.b1;
      if (b1Net?.qo && typeof b1Net.qo.rK === "function") {
        b1Net.qo.rK(1015, bossId);
        if (slot === 0 && window.__hlLog) {
          window.__hlLog(`[HL-EMOJI] t=${g.t} sent private scales emoji (1015) -> boss=${bossId}(${g.names?.[bossId] || ""})`);
        }
      }
    } catch (e) {
      if (slot === 0 && window.__hlLog) {
        window.__hlLog(`[HL-EMOJI-ERR] ${e?.message || e}`);
      }
    }
  }

  // AUTO PEACE VOTE CALL & ACCEPT:
  // ONLY call or vote YES on peace once only 1 team remains alive (or while wild outsiders are still alive and our own team has >=58% land)!
  tryPeaceVote(g) {
    if (typeof window === "undefined" || !window.ax || !window.dictionary || g.t < 1610) return;
    const me = this.me;
    const hz = window[window.dictionary.sbCommands]?.hz;
    if (!hz) return;
    let ourTeamLand = g.terr[me] || 0;
    let otherTeamAlive = false;
    if (g.teams && g.teams[me] > 0) {
      ourTeamLand = 0;
      for (let p = 0; p < g.players; p++) {
        if (g.alive[p] && g.terr[p] > 0) {
          if (g.teams[p] === g.teams[me]) ourTeamLand += g.terr[p];
          else if (g.terr[p] >= 80) otherTeamAlive = true;
        }
      }
    }
    // Rule #7821: If wild outsiders are all dead, fight until only 1 team remains (!otherTeamAlive) before voting peace!
    const wildAlive = this.hasWildOutsidersAlive(g);
    if (!wildAlive && otherTeamAlive) return;
    const weLead = (!otherTeamAlive) || (wildAlive && ourTeamLand >= 0.58 * Math.max(1, g.land)) || this.isMopUp(g);
    const caller = window.__lastPeaceCaller;
    const callerIsOurs =
      Number.isInteger(caller) &&
      caller >= 0 &&
      caller < g.humans &&
      (caller === me || this.isOurSquadBot(g, caller) || this.isBossNpl(g, caller));
    if (window.ax.iL && typeof window.ax.iM === "function" && window.ax.iM(me)) {
      if (callerIsOurs && (!otherTeamAlive || wildAlive) && typeof hz.iN === "function") {
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

    // 2. SQUAD MUTUAL AID: Rescue any squad brother who is under human attack or sneaky boat landing,
    //    AND lightly poke (10%B) the attacker if we border them!
    const wildOutsidersAlive = this.hasWildOutsidersAlive(g);
    for (let p = 0; p < g.humans; p++) {
      if (p === me || !g.alive[p] || !this.isOurSquadBot(g, p) || (!wildOutsidersAlive && !this.isTeammate(g, p)) || g.terr[p] < 300) continue;
      const dAlly = g.bal[p] / Math.max(1, g.terr[p]);
      let inHumanAtk = 0, mainAttacker = -1, maxAtkTr = 0;
      for (const a of g.attackersOf(p)) {
        if (!g.isBot(a) && !this.isProtectedSquadMate(g, a)) {
          const tr = g.attackTroopsOn(a, p);
          inHumanAtk += tr;
          if (tr > maxAtkTr) { maxAtkTr = tr; mainAttacker = a; }
        }
      }
      if (inHumanAtk > 0 && (inHumanAtk >= 0.08 * g.bal[p] || dAlly < 75)) {
        // First donate cash to save our brother (if on same team, while keeping our own coastGuardFloor / safeFloor intact!)
        if (this.isTeammate(g, p) && dMe >= Math.max(55, dAlly + 15)) {
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
        // Second, if we border the attacker on land and aren't already attacking them, do a ~10%B light assist poke (even across teams)!
        if (mainAttacker >= 0 && !this.isTeammate(g, mainAttacker) && (this.cnt[mainAttacker] ?? 0) > 0 && !g.hasAttack(me, mainAttacker) && g.hasFreeSlot(me) && dMe >= 65 && g.t - (this.lastAssistPokeTick ?? -999) >= 25) {
          this.lastAssistPokeTick = g.t;
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
            if (this.isProtectedSquadMate(g, a)) {
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
            if (tgt >= 0 && tgt < 512 && this.isProtectedSquadMate(g, tgt)) {
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

new_early_act = """    if (g.t >= 15 && g.t <= 90 && !this.hasBossInMatch(g)) {
      try {
        const d = window.dictionary, gm = d && window[d.game];
        if (gm && gm[d.gameState] !== 0 && typeof gm[d.sbLeave] === "function") gm[d.sbLeave](true);
      } catch {}
      return;
    }
    this.tryPrivateBossEmoji(g);
    if (g.t < P.coreFrom) {
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

old_bot_buy = """      const avail = B - fee - keep;
      if (avail <= 0) continue;

      if (!person) {
        const want = 1.25 * need + 3 * this.cnt[q];
        const x = Math.min(avail, want);
        if (x <= 0 || (x < want && x < P.chunk * B)) continue;
        return this.send(g, q, x);
      }"""

new_bot_buy = """      const avail = B - fee - keep;
      if (avail <= 0) continue;

      if (!person) {
        if (g.hasAttack(me, q) && (!g.hasAttack(q, me) || g.attackTroopsOn(me, q) >= 0.35 * need)) continue;
        const want = 1.25 * need + 3 * this.cnt[q];
        const x = Math.min(avail, want);
        if (x < this.minCmd(g) || (x < want && x < P.chunk * B)) continue;
        return this.send(g, q, x);
      }"""
assert old_bot_buy in s, "old_bot_buy not found"
s = s.replace(old_bot_buy, new_bot_buy, 1)

# Also guard Style.prototype.pickTarget, V17.prototype.buyLand, and General.prototype.send against <P.coreFrom (t=550..1500) bot top-up spam!
old_style_pick = """      const need = this.elimCost(g, q) + g.attackTroopsOn(q, me) - g.attackTroopsOn(me, q);
      if (need <= 0) continue;"""
new_style_pick = """      const need = this.elimCost(g, q) + g.attackTroopsOn(q, me) - g.attackTroopsOn(me, q);
      if (need <= 0) continue;
      if (!this.person(g, q) && g.hasAttack(me, q) && (!g.hasAttack(q, me) || g.attackTroopsOn(me, q) >= 0.35 * need)) continue;"""
assert old_style_pick in s, "old_style_pick not found"
s = s.replace(old_style_pick, new_style_pick, 1)

old_v17_buy = """      const want = 1.25 * need + 3 * this.cnt[q];
      const x = Math.min(B - fee - keep, want);
      if (x <= 0 || (x < want && (x < P.chunk * B || (P.pplKill > 0 && person)))) continue;"""
new_v17_buy = """      if (!person && g.hasAttack(me, q) && (!g.hasAttack(q, me) || g.attackTroopsOn(me, q) >= 0.35 * need)) continue;
      const want = 1.25 * need + 3 * this.cnt[q];
      const x = Math.min(B - fee - keep, want);
      if (x < this.minCmd(g) || (x < want && (x < P.chunk * B || (P.pplKill > 0 && person)))) continue;"""
assert old_v17_buy in s, "old_v17_buy not found"
s = s.replace(old_v17_buy, new_v17_buy, 1)

old_gen_send = """  send(g, target, troops) {
    const bal = g.bal[this.me];
    if (bal <= 0 || troops <= 0) return false;"""
new_gen_send = """  send(g, target, troops) {
    const bal = g.bal[this.me];
    if (bal <= 0 || troops <= 0) return false;
    if (g.online && target !== NEUTRAL) {
      if (!this._lastTargetSendTick) this._lastTargetSendTick = new Map();
      if (g.t - (this._lastTargetSendTick.get(target) ?? -999) < 15) return false;
      this._lastTargetSendTick.set(target, g.t);
    }"""
assert old_gen_send in s, "old_gen_send not found"
s = s.replace(old_gen_send, new_gen_send, 1)

old_zero_pulse = """        const canZeroPulse = (amt) =>
          P.zeroPulseMode > 0 &&"""
new_zero_pulse = """        const canZeroPulse = (amt) =>
          !g.online && P.zeroPulseMode > 0 &&"""
assert old_zero_pulse in s, "old_zero_pulse not found"
s = s.replace(old_zero_pulse, new_zero_pulse, 1)

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

with open("/tmp/v27-team-live.js", "w") as f:
    f.write(s)

print("Successfully built Cash-First + 10%-Assist + Auto-Peace-Vote /tmp/v27-team-live.js! Size:", len(s))
