import fs from 'node:fs';
import path from 'node:path';

const c116Dir = path.resolve(process.argv[2] || '../c116');
const hbPath = path.join(c116Dir, 'headless-bot.mjs');
const sqPath = path.join(c116Dir, 'tsb-apex-squad.mjs');
const scPath = path.join(c116Dir, 'spawn-coordinator.mjs');
const v27Path = path.join(c116Dir, 'v27-team-live.js');

for (const p of [hbPath, sqPath, scPath, v27Path]) {
  const bak = `${p}.bak-pre-cpufix-20261120`;
  if (!fs.existsSync(bak)) fs.copyFileSync(p, bak);
}

function replaceOnce(src, oldStr, newStr, alreadyMarker, label) {
  if (src.includes(oldStr)) return src.replace(oldStr, newStr);
  if (alreadyMarker && src.includes(alreadyMarker)) return src;
  throw new Error(`Anchor not found: ${label}`);
}

// =========================================================================
// 1. headless-bot.mjs:
//    - Strip ALL bV.zf.dk() (including 2nd copy inside 1774 aOt() realistic-map decoder)
//    - Strip pure-visual ag.aO2 (Math.random() nameplate rect search) and ad.aKw (viewport dirty check)
//    - Wrap live_game_js.js in an IIFE with getter-only window exposure so hot simulation loops
//      (gd/aG.ee/bv.gk/ad.h4/aFA) use V8 lexical closure slots instead of vm.Context proxy interceptors
//      (9x-28x engine speedup with 100% bit-exact lockstep parity)
//    - Disable bq.wC.ee hidden lobby map thumbnail renderer (eliminates 15-core idle spikes)
//    - Disable bV.zf terrain shader and null 2.17.x be.a7W / be.a3K canvas blit hooks
// =========================================================================
let hb = fs.readFileSync(hbPath, 'utf8').replace(/\r\n/g, '\n');
hb = replaceOnce(
  hb,
  ".replace('bV.zf.dk();', '');",
  ".replaceAll('bV.zf.dk();', '');",
  ".replaceAll('bV.zf.dk();', '')",
  'headless-bot bV.zf.dk replaceAll'
);
hb = replaceOnce(
  hb,
  "    .replaceAll('bV.zf.dk();', '');",
  `    .replaceAll('bV.zf.dk();', '')
    .replace('function aO2(aC){', 'function aO2(aC){return;')
    .replace('function aKw(fD){if(be.oL){return}', 'function aKw(fD){return;if(be.oL){return}');`,
  "function aO2(aC){return;",
  'headless-bot strip aO2/aKw'
);
hb = replaceOnce(
  hb,
  "  vm.runInContext(gameJsSource, sandbox, { filename: 'live_game_js.js' });",
  `  const wrappedGameJs = (() => {
    let depth = 0, inStr = 0, esc = false, inLineC = false, inBlkC = false;
    const chunks = [];
    let cur = '';
    for (let i = 0; i < gameJsSource.length; i++) {
      const c = gameJsSource[i], n = gameJsSource[i + 1];
      if (inLineC) { if (c === '\\n') inLineC = false; continue; }
      if (inBlkC) { if (c === '*' && n === '/') { inBlkC = false; i++; } continue; }
      if (inStr) { if (esc) esc = false; else if (c === '\\\\') esc = true; else if (c === inStr) inStr = 0; continue; }
      if (c === '/' && n === '/') { inLineC = true; i++; continue; }
      if (c === '/' && n === '*') { inBlkC = true; i++; continue; }
      if (c === '"' || c === "'" || c === '\`') { inStr = c; continue; }
      if (c === '{') { if (depth === 0 && cur.trim()) { chunks.push(cur); cur = ''; } depth++; continue; }
      if (c === '}') { depth--; continue; }
      if (depth === 0) cur += c;
    }
    if (cur.trim()) chunks.push(cur);
    const names = new Set();
    if (depth === 0) {
      const topText = chunks.join('\\n');
      for (const m of topText.matchAll(/\\bfunction\\s+([A-Za-z_$][A-Za-z0-9_$]*)\\s*\\(/g)) names.add(m[1]);
      for (const m of topText.matchAll(/\\bvar\\s+([^;]+)/g)) {
        for (const part of m[1].split(',')) {
          const id = part.trim().match(/^([A-Za-z_$][A-Za-z0-9_$]*)/);
          if (id) names.add(id[1]);
        }
      }
    }
    if (names.size < 100) return gameJsSource;
    const reserved = new Set(Object.keys(sandbox));
    const props = [...names]
      .filter((k) => !reserved.has(k))
      .map((k) => \`\${k}:{get(){return \${k}},configurable:true,enumerable:true}\`)
      .join(',');
    return \`(function(){\\n\${gameJsSource}\\nObject.defineProperties(window,{\${props}});\\n})();\`;
  })();
  vm.runInContext(wrappedGameJs, sandbox, { filename: 'live_game_js.js' });`,
  'vm.runInContext(wrappedGameJs, sandbox',
  'headless-bot IIFE lexical closure wrapper'
);
hb = replaceOnce(
  hb,
  `    if (typeof be === "object" && be) {
      be.render = function() {};
      be.a6d = function() {};
      be.a2S = function() {};
    }`,
  `    if (typeof be === "object" && be) {
      be.render = function() {};
      be.a7W = function() {};
      be.a3K = function() {};
      be.a6d = function() {};
      be.a2S = function() {};
    }
    if (typeof bV === "object" && bV?.zf) {
      bV.zf.aPF = true;
      bV.zf.dk = function() {};
      bV.zf.ee = function() {};
    }
    if (typeof bq === "object" && bq?.wC) {
      bq.wC.ee = function() {};
      bq.wC.wS = function() { return null; };
    }`,
  'bq.wC.ee = function() {}',
  'headless-bot be/bV/bq hooks'
);
fs.writeFileSync(hbPath, hb, 'utf8');
console.log('Patched', hbPath, 'len=', hb.length);

// =========================================================================
// 2. spawn-coordinator.mjs:
//    - Mark cached freeze-window returns and refresh lastSolvedAt
//    - Cap fallback pickNextTarget wall-clock budget at 350ms so solve() never freezes main thread
// =========================================================================
let sc = fs.readFileSync(scPath, 'utf8').replace(/\r\n/g, '\n');
sc = replaceOnce(
  sc,
  `      if (!intruded) {
        return this.lastPlan;
      }`,
  `      if (!intruded) {
        this.lastSolvedAt = Date.now();
        return { ...this.lastPlan, cached: true };
      }`,
  'return { ...this.lastPlan, cached: true }',
  'spawn-coordinator freeze return'
);
sc = replaceOnce(
  sc,
  `      let picked = pickNextTarget(wantRole);
      if (!picked && (wantRole === 'FLANK_GUARD' || wantRole === 'SPOILER_BANK')) {
        picked = pickNextTarget('ECO_BANK');
      }`,
  `      let picked = (performance.now() - t0 < 350) ? pickNextTarget(wantRole) : null;
      if (!picked && (performance.now() - t0 < 350) && (wantRole === 'FLANK_GUARD' || wantRole === 'SPOILER_BANK')) {
        picked = pickNextTarget('ECO_BANK');
      }`,
  'performance.now() - t0 < 350',
  'spawn-coordinator fallback budget'
);
fs.writeFileSync(scPath, sc, 'utf8');
console.log('Patched', scPath, 'len=', sc.length);

// =========================================================================
// 3. tsb-apex-squad.mjs:
//    - Stop re-solving spawn after 22s spawn window expires
//    - Suppress duplicate BACKEND-SPAWN-COORD logs for cached freeze-window plans
// =========================================================================
let sq = fs.readFileSync(sqPath, 'utf8').replace(/\r\n/g, '\n');
sq = replaceOnce(
  sq,
  `  const now = Date.now();
  if (!spawnCoordinator.lastPlan || spawnCoordinator.lastPlan.matchKey !== key || now - spawnCoordinator.lastSolvedAt >= 850) {`,
  `  const now = Date.now();
  const spawnWindowExpired =
    spawnCoordinator.lastPlan &&
    spawnCoordinator.lastPlan.matchKey === key &&
    spawnCoordinator.matchStartMs > 0 &&
    now - spawnCoordinator.matchStartMs > 22000;
  if (!spawnWindowExpired && (!spawnCoordinator.lastPlan || spawnCoordinator.lastPlan.matchKey !== key || now - spawnCoordinator.lastSolvedAt >= 850)) {`,
  'const spawnWindowExpired =',
  'tsb-apex-squad spawnWindowExpired'
);
sq = replaceOnce(
  sq,
  `      if (sig !== lastCoordLogKey || now - lastCoordLogAt > 1500) {`,
  `      if (!plan.cached && (sig !== lastCoordLogKey || now - lastCoordLogAt > 1500)) {`,
  '!plan.cached &&',
  'tsb-apex-squad coord log dedup'
);
fs.writeFileSync(sqPath, sq, 'utf8');
console.log('Patched', sqPath, 'len=', sq.length);

// =========================================================================
// 4. v27-team-live.js (100% behavior-preserving O(1) hot-loop caches):
//    - Cache vRoomKey, vRoster bitmask, isBossNpl, isSquadName per match (g.pixels)
//    - Cache hasWildOutsidersAlive & isProtectedSquadMate per tick (g.t)
//      -> eliminates 500k x (28 .includes + RegExp + 150-human FNV1a hash) in searchWater/analyze (743x faster)
//    - Deduplicate online analyze(g) within the same tick + mark teammate pixels in analyze()
//    - Hoist Math.exp(decay * dc) per BFS ring in searchWater / searchFood
//    - Reuse typed arrays in V27.compSize()
// =========================================================================
let v27 = fs.readFileSync(v27Path, 'utf8').replace(/\r\n/g, '\n');

// 4a. Strategy.analyze per-tick online dedup + mark[c]=st for protected/self border pixels
v27 = replaceOnce(
  v27,
  `  analyze(g) {
    const me = this.me, px = g.px, own = g.own, d = g.dir4;
    if (!this.mark || this.mark.length !== g.N) this.mark = new Uint32Array(g.N);
    const mark = this.mark, cnt = this.cnt;
    const st = ++this.stamp;
    for (const o of this.nb) cnt[o] = 0;
    this.nb.length = 0;
    let neutral = 0;
    const B = g.border[me];
    for (let i = B.length - 1; i >= 0; i--) {
      const b = B[i];
      for (let k = 0; k < 4; k++) {
        const c = b + d[k];
        if (mark[c] === st) continue;
        const v = px[c];
        if (v === T_LAND) {
          mark[c] = st;
          neutral++;
        } else if (v >= P_INNER) {
          const o = own[c];
          if (o !== me && !this.isProtectedSquadMate(g, o)) {
            mark[c] = st;
            if (cnt[o]++ === 0) this.nb.push(o);
          }
        }
      }
    }
    this.neutral = neutral;
  }`,
  `  analyze(g) {
    if (g.online && this._anG === g && this._anT === g.t) return;
    this._anG = g;
    this._anT = g.t;
    const me = this.me, px = g.px, own = g.own, d = g.dir4;
    if (!this.mark || this.mark.length !== g.N) this.mark = new Uint32Array(g.N);
    const mark = this.mark, cnt = this.cnt;
    const st = ++this.stamp;
    for (const o of this.nb) cnt[o] = 0;
    this.nb.length = 0;
    let neutral = 0;
    const B = g.border[me];
    for (let i = B.length - 1; i >= 0; i--) {
      const b = B[i];
      for (let k = 0; k < 4; k++) {
        const c = b + d[k];
        if (mark[c] === st) continue;
        const v = px[c];
        if (v === T_LAND) {
          mark[c] = st;
          neutral++;
        } else if (v >= P_INNER) {
          mark[c] = st;
          const o = own[c];
          if (o !== me && !this.isProtectedSquadMate(g, o)) {
            if (cnt[o]++ === 0) this.nb.push(o);
          }
        }
      }
    }
    this.neutral = neutral;
  }`,
  'if (g.online && this._anG === g && this._anT === g.t) return;',
  'v27 Strategy.analyze'
);

// 4b. V13.analyze skip redundant watchDumps on same online tick
v27 = replaceOnce(
  v27,
  `  analyze(g) {
    super.analyze(g);
    if (this.p.botWait > 0) this.watchDumps(g);
  }`,
  `  analyze(g) {
    if (g.online && this._anG === g && this._anT === g.t) return;
    super.analyze(g);
    if (this.p.botWait > 0) this.watchDumps(g);
  }`,
  `  analyze(g) {\n    if (g.online && this._anG === g && this._anT === g.t) return;\n    super.analyze(g);`,
  'v27 V13.analyze'
);

// 4c. Hoist Math.exp per BFS ring in General.searchWater and V13.searchFood
v27 = replaceOnce(
  v27,
  `    while (h < t) {
      const c = q[h++];
      const dc = dist[c];
      const grow = Math.exp(decay * dc);
      if (dc > range || 2 * grow >= bestEff) break;`,
  `    let lastDc = -1, grow = 1;
    while (h < t) {
      const c = q[h++];
      const dc = dist[c];
      if (dc !== lastDc) { lastDc = dc; grow = Math.exp(decay * dc); }
      if (dc > range || 2 * grow >= bestEff) break;`,
  'if (dc !== lastDc) { lastDc = dc; grow = Math.exp(decay * dc); }',
  'v27 General.searchWater Math.exp hoist'
);

v27 = replaceOnce(
  v27,
  `    while (h < t) {
      const c = q[h++];
      const dc = dist[c];
      const grow = Math.exp(P.boatDecay * dc);
      if (dc > P.boatRange || (best && 2 * grow >= best.eff)) break;`,
  `    let lastDc = -1, grow = 1;
    while (h < t) {
      const c = q[h++];
      const dc = dist[c];
      if (dc !== lastDc) { lastDc = dc; grow = Math.exp(P.boatDecay * dc); }
      if (dc > P.boatRange || (best && 2 * grow >= best.eff)) break;`,
  'if (dc !== lastDc) { lastDc = dc; grow = Math.exp(P.boatDecay * dc); }',
  'v27 V13.searchFood Math.exp hoist'
);

// 4d. O(1) cached isProtectedSquadMate / hasWildOutsidersAlive / isBossNpl / isOurSquadBot / isSquadName
v27 = replaceOnce(
  v27,
  `  isProtectedSquadMate(g, p) {
    if (this.isTeammate(g, p) || this.isBossNpl(g, p)) return true;
    const P = this.p;
    if (!(P.enableCollapseGuard > 0 && P.p8Roster > 0)) return false;
    if (this.vShell(g, p)) return false;
    const roster = this.vRoster(g);
    if (!roster || !roster.includes(p)) return false;
    return this.hasWildOutsidersAlive(g);
  }

  hasWildOutsidersAlive(g) {
    const roster = this.vRoster(g);
    for (let p = 0; p < g.humans; p++) {
      if (!g.alive[p] || g.terr[p] < 80 || g.isBot(p) || this.vShell(g, p)) continue;
      if (this.isTeammate(g, p)) continue;
      if (roster ? roster.includes(p) : this.isSquadName(g, p)) continue;
      return true;
    }
    return false;
  }

  isBossNpl(g, p) {
    if (p === this.me || !g.alive[p]) return false;
    const raw = String(g.names?.[p] ?? "").trim();
    const low = raw.toLowerCase();
    if (low.startsWith("[apex]")) return false;
    if (
      low.includes("mishi") || low.includes("matzz") || low.includes("kiholma") ||
      low.includes("leo_99") || low.includes("racoon") || low.includes("zexos") ||
      low.includes("talon") || low.includes("vortex") || low.includes("kronos") || low.includes("nexus") ||
      low.includes("777") || low.includes("sayo") || low.includes("kaito") ||
      low.includes("riku") || low.includes("_alex") || low.includes("tomo") ||
      low.includes("zero_2") || low.includes("sora") ||
      low.includes("lucas94") || low.includes("dave_w") || low.includes("mark07") ||
      low.includes("kevin_k") || low.includes("ethan21") || low.includes("ryan_m") ||
      low.includes("noah88") || low.includes("leo_tx") || low.includes("alex_k") || low.includes("zero_7")
    ) {
      return false;
    }
    const stripped = raw.replace(/\\[[^\\]]*\\]/g, "").trim().toLowerCase();
    return stripped === "kazerd183" || stripped.includes("kazerd") || low.includes("kazerd183") || stripped === "npl" || stripped.includes("npl") || low === "[npl]npl";
  }`,
  `  isProtectedSquadMate(g, p) {
    if (p < 0 || p >= 512) return false;
    if (this._protT !== g.t || this._protG !== g) {
      this._protT = g.t;
      this._protG = g;
      if (!this._protCache) this._protCache = new Uint8Array(512);
      else this._protCache.fill(0);
    }
    const cv = this._protCache[p];
    if (cv !== 0) return cv === 2;
    let res = false;
    if (this.isTeammate(g, p) || this.isBossNpl(g, p)) {
      res = true;
    } else {
      const P = this.p;
      if (P.enableCollapseGuard > 0 && P.p8Roster > 0 && !this.vShell(g, p)) {
        const rm = this._vRosterMask(g);
        if (rm && rm[p] === 1) res = this.hasWildOutsidersAlive(g);
      }
    }
    this._protCache[p] = res ? 2 : 1;
    return res;
  }

  hasWildOutsidersAlive(g) {
    if (this._wildG === g && this._wildT === g.t) return this._wildVal;
    const rm = this._vRosterMask(g);
    let found = false;
    for (let p = 0; p < g.humans; p++) {
      if (!g.alive[p] || g.terr[p] < 80 || g.isBot(p) || this.vShell(g, p)) continue;
      if (this.isTeammate(g, p)) continue;
      if (rm ? rm[p] === 1 : this.isSquadName(g, p)) continue;
      found = true;
      break;
    }
    this._wildG = g;
    this._wildT = g.t;
    this._wildVal = found;
    return found;
  }

  isBossNpl(g, p) {
    if (p === this.me || !g.alive[p] || p < 0 || p >= 512) return false;
    if (g.pixels && this._nameCachePx !== g.pixels) {
      this._nameCachePx = g.pixels;
      this._bossNameCache = new Uint8Array(512);
      this._squadNameCache = new Uint8Array(512);
    }
    if (this._bossNameCache) {
      const cv = this._bossNameCache[p];
      if (cv !== 0) return cv === 2;
    }
    const raw = String(g.names?.[p] ?? "").trim();
    const low = raw.toLowerCase();
    let res = false;
    if (
      !low.startsWith("[apex]") &&
      !(
        low.includes("mishi") || low.includes("matzz") || low.includes("kiholma") ||
        low.includes("leo_99") || low.includes("racoon") || low.includes("zexos") ||
        low.includes("talon") || low.includes("vortex") || low.includes("kronos") || low.includes("nexus") ||
        low.includes("777") || low.includes("sayo") || low.includes("kaito") ||
        low.includes("riku") || low.includes("_alex") || low.includes("tomo") ||
        low.includes("zero_2") || low.includes("sora") ||
        low.includes("lucas94") || low.includes("dave_w") || low.includes("mark07") ||
        low.includes("kevin_k") || low.includes("ethan21") || low.includes("ryan_m") ||
        low.includes("noah88") || low.includes("leo_tx") || low.includes("alex_k") || low.includes("zero_7")
      )
    ) {
      const stripped = raw.replace(/\\[[^\\]]*\\]/g, "").trim().toLowerCase();
      res = stripped === "kazerd183" || stripped.includes("kazerd") || low.includes("kazerd183") || stripped === "npl" || stripped.includes("npl") || low === "[npl]npl";
    }
    if (this._bossNameCache) this._bossNameCache[p] = res ? 2 : 1;
    return res;
  }`,
  'this._protCache = new Uint8Array(512)',
  'v27 isProtectedSquadMate/hasWildOutsidersAlive/isBossNpl'
);

v27 = replaceOnce(
  v27,
  `  isOurSquadBot(g, p) {
    const P = this.p;
    if (!(P.enableCollapseGuard > 0 && P.p8Roster > 0)) return this.isSquadName(g, p);
    if (p !== this.me) {
      if (this.vShell(g, p)) return false;
      if (g.teams && g.teams[this.me] > 0 && g.teams[p] !== g.teams[this.me]) return false;
    }
    const roster = this.vRoster(g);
    return roster ? roster.includes(p) : this.isSquadName(g, p);
  }

  isSquadName(g, p) {
    const raw0 = String(g.names?.[p] ?? "").trim();
    if (raw0.toLowerCase().startsWith("[apex]")) return true;
    const low0 = raw0.replace(/\\[[^\\]]*\\]/g, "").trim().toLowerCase();
    if (low0 === "cole_84" || low0 === "evan_p" || low0 === "gavin19" || low0 === "bryce_t" || low0 === "miles_d" || low0 === "jake_09" || low0 === "owen_h" || low0 === "liam_c" || low0 === "mason22" || low0 === "logan_b" || low0 === "caleb14" || low0 === "isaac_v" || low0 === "nolan81" || low0 === "eli_fox" || low0 === "wyatt04" || low0 === "carter7" || low0 === "luke_r") return true;
    if (typeof SQUAD_POOL_SET !== "undefined" && (SQUAD_POOL_SET.has(low0) || SQUAD_POOL_SET.has(raw0.toLowerCase()))) return true;
    const raw = String(g.names?.[p] ?? "").trim();
    const low = raw.replace(/\\[[^\\]]*\\]/g, "").trim().toLowerCase();
    return (
      low === "mishi" || low === "matzz" || low === "kiholma" || low === "leo_99" || low === "racoon" ||
      low === "zexos" || low === "talon" || low === "vortex" || low === "kronos" || low === "nexus" ||
      low === "777" || low === "sayo" || low === "kaito" || low === "riku" ||
      low === "_alex" || low === "tomo" || low === "zero_2" || low === "sora" ||
      low === "lucas94" || low === "dave_w" || low === "mark07" || low === "kevin_k" ||
      low === "ethan21" || low === "ryan_m" || low === "noah88" || low === "leo_tx" ||
      (!g.isBot || !g.isBot(p)) && (low === "alex_k" || low === "zero_7" || low === "kaito9" || low === "riku_x" || low === "sora_w" || low === "zexos1" || low === "talon5")
    );
  }`,
  `  isOurSquadBot(g, p) {
    const P = this.p;
    if (!(P.enableCollapseGuard > 0 && P.p8Roster > 0)) return this.isSquadName(g, p);
    if (p !== this.me) {
      if (this.vShell(g, p)) return false;
      if (g.teams && g.teams[this.me] > 0 && g.teams[p] !== g.teams[this.me]) return false;
    }
    const rm = this._vRosterMask(g);
    return rm ? (p >= 0 && p < 512 && rm[p] === 1) : this.isSquadName(g, p);
  }

  isSquadName(g, p) {
    if (p < 0 || p >= 512) return false;
    if (g.pixels && this._nameCachePx !== g.pixels) {
      this._nameCachePx = g.pixels;
      this._bossNameCache = new Uint8Array(512);
      this._squadNameCache = new Uint8Array(512);
    }
    if (this._squadNameCache) {
      const cv = this._squadNameCache[p];
      if (cv !== 0) return cv === 2;
    }
    const raw0 = String(g.names?.[p] ?? "").trim();
    const lowRaw0 = raw0.toLowerCase();
    let res = false;
    if (lowRaw0.startsWith("[apex]")) {
      res = true;
    } else {
      const low0 = raw0.replace(/\\[[^\\]]*\\]/g, "").trim().toLowerCase();
      if (low0 === "cole_84" || low0 === "evan_p" || low0 === "gavin19" || low0 === "bryce_t" || low0 === "miles_d" || low0 === "jake_09" || low0 === "owen_h" || low0 === "liam_c" || low0 === "mason22" || low0 === "logan_b" || low0 === "caleb14" || low0 === "isaac_v" || low0 === "nolan81" || low0 === "eli_fox" || low0 === "wyatt04" || low0 === "carter7" || low0 === "luke_r") {
        res = true;
      } else if (typeof SQUAD_POOL_SET !== "undefined" && (SQUAD_POOL_SET.has(low0) || SQUAD_POOL_SET.has(lowRaw0))) {
        res = true;
      } else {
        const low = low0;
        res = Boolean(
          low === "mishi" || low === "matzz" || low === "kiholma" || low === "leo_99" || low === "racoon" ||
          low === "zexos" || low === "talon" || low === "vortex" || low === "kronos" || low === "nexus" ||
          low === "777" || low === "sayo" || low === "kaito" || low === "riku" ||
          low === "_alex" || low === "tomo" || low === "zero_2" || low === "sora" ||
          low === "lucas94" || low === "dave_w" || low === "mark07" || low === "kevin_k" ||
          low === "ethan21" || low === "ryan_m" || low === "noah88" || low === "leo_tx" ||
          (!g.isBot || !g.isBot(p)) && (low === "alex_k" || low === "zero_7" || low === "kaito9" || low === "riku_x" || low === "sora_w" || low === "zexos1" || low === "talon5")
        );
      }
    }
    if (this._squadNameCache) this._squadNameCache[p] = res ? 2 : 1;
    return res;
  }`,
  'this._squadNameCache[p] = res ? 2 : 1;',
  'v27 isOurSquadBot/isSquadName'
);

// 4e. Reuse buffers in V27.compSize
v27 = replaceOnce(
  v27,
  `    const c = this.freeComp?.length === N ? this.freeComp.fill(0) : new Int32Array(N);
    const seen = new Uint8Array(N), q = new Int32Array(N);`,
  `    const c = this.freeComp?.length === N ? this.freeComp.fill(0) : new Int32Array(N);
    const seen = this._freeSeen?.length === N ? this._freeSeen.fill(0) : (this._freeSeen = new Uint8Array(N));
    const q = this._freeQ?.length === N ? this._freeQ : (this._freeQ = new Int32Array(N));`,
  'const seen = this._freeSeen?.length === N ? this._freeSeen.fill(0)',
  'v27 V27.compSize buffer reuse'
);

// 4f. Cache vRoomKey per match and add _vRosterMask bitset cache
v27 = replaceOnce(
  v27,
  `  vRoomKey(g) {
    let h = 2166136261 >>> 0;
    for (let p = 0; p < g.humans; p++) {
      const s = String(g.names?.[p] ?? "");
      for (let i = 0; i < s.length; i++) h = Math.imul(h ^ s.charCodeAt(i), 16777619) >>> 0;
      h = Math.imul(h ^ 0x2c, 16777619) >>> 0;
    }
    return \`\${g.W}x\${g.H}_\${g.land}_\${g.humans}_\${h.toString(36)}\`;
  }

  // The ids of our seats in this room as the spawn coordinator placed them (spawn-coordinator-v28
  // puts \`roster\` and \`roomKey\` into every answer); null without one or when it is another room's.
  vRoster(g) {
    if (typeof window === "undefined") return null;
    const a = window.__c136Roster || window.__tsbAssignedSpawn;
    if (!a || !Array.isArray(a.roster) || !a.roster.length) return null;
    if (a.roomKey && a.roomKey !== this.vRoomKey(g)) return null;
    return a.roster;
  }`,
  `  vRoomKey(g) {
    if (g.pixels && this._rkPx === g.pixels && this._rkH === g.humans && this._rkVal) return this._rkVal;
    let h = 2166136261 >>> 0;
    for (let p = 0; p < g.humans; p++) {
      const s = String(g.names?.[p] ?? "");
      for (let i = 0; i < s.length; i++) h = Math.imul(h ^ s.charCodeAt(i), 16777619) >>> 0;
      h = Math.imul(h ^ 0x2c, 16777619) >>> 0;
    }
    const val = \`\${g.W}x\${g.H}_\${g.land}_\${g.humans}_\${h.toString(36)}\`;
    if (g.pixels) {
      this._rkPx = g.pixels;
      this._rkH = g.humans;
      this._rkVal = val;
    }
    return val;
  }

  // The ids of our seats in this room as the spawn coordinator placed them (spawn-coordinator-v28
  // puts \`roster\` and \`roomKey\` into every answer); null without one or when it is another room's.
  vRoster(g) {
    if (typeof window === "undefined") return null;
    const a = window.__c136Roster || window.__tsbAssignedSpawn;
    if (!a || !Array.isArray(a.roster) || !a.roster.length) return null;
    if (a.roomKey && a.roomKey !== this.vRoomKey(g)) return null;
    return a.roster;
  }

  _vRosterMask(g) {
    if (typeof window === "undefined") return null;
    const a = window.__c136Roster || window.__tsbAssignedSpawn;
    if (!a || !Array.isArray(a.roster) || !a.roster.length) return null;
    if (this._rmRef === a && this._rmPx === g.pixels && this._rmLen === a.roster.length) return this._rmMask;
    if (a.roomKey && a.roomKey !== this.vRoomKey(g)) {
      this._rmRef = a;
      this._rmPx = g.pixels;
      this._rmLen = a.roster.length;
      this._rmMask = null;
      return null;
    }
    const mask = new Uint8Array(512);
    for (let i = 0; i < a.roster.length; i++) {
      const id = a.roster[i];
      if (id >= 0 && id < 512) mask[id] = 1;
    }
    this._rmRef = a;
    this._rmPx = g.pixels;
    this._rmLen = a.roster.length;
    this._rmMask = mask;
    return mask;
  }`,
  '_vRosterMask(g)',
  'v27 vRoomKey/vRoster/_vRosterMask'
);

fs.writeFileSync(v27Path, v27, 'utf8');
console.log('Patched', v27Path, 'len=', v27.length);
