import fs from 'node:fs';
import path from 'node:path';

const c116Dir = path.resolve(process.argv[2] || '../c116');
const hbPath = path.join(c116Dir, 'headless-bot.mjs');
const sqPath = path.join(c116Dir, 'tsb-apex-squad.mjs');
const v27Path = path.join(c116Dir, 'v27-team-live.js');

const BOSS_ACC_IDS = ['9JNYv'];
const BOSS_ACC_UX = 173115643; // bJ.f0.f1('9JNYv', 5) === 173115643
const PEACE_DOVE_EMOTE_ID = 1017; // ac.get(3) orders sprite tile 9 (a1s[6] -> 1024 - 13 + 6 = 1017)

for (const p of [hbPath, sqPath, v27Path]) {
  const bak = `${p}.bak-pre-boss9jnyv-20261121`;
  if (!fs.existsSync(bak)) fs.copyFileSync(p, bak);
}

function replaceOnce(src, oldStr, newStr, alreadyMarker, label) {
  if (src.includes(oldStr)) return src.replace(oldStr, newStr);
  if (alreadyMarker && src.includes(alreadyMarker)) return src;
  throw new Error(`Anchor not found: ${label}`);
}

// =========================================================================
// 1. headless-bot.mjs:
//    - Hook ag.rv(player, eI, aNa) alongside ax.iK so every incoming Peace
//      Dove emote (r5 === 1017, both broadcast eI===0 and directed eI===1)
//      records window.__doveEmoteTicks.set(player, curTick).
//    - Reset window.__doveEmoteTicks and window.__bossDoveRemoteUntilMs on
//      every new game start.
// =========================================================================
let hb = fs.readFileSync(hbPath, 'utf8').replace(/\r\n/g, '\n');

hb = replaceOnce(
  hb,
  `    if (typeof ax === "object" && ax && typeof ax.iK === "function" && !ax.__hookedPeaceCaller) {
      ax.__hookedPeaceCaller = true;
      const origIk = ax.iK.bind(ax);
      ax.iK = function(player) {
        window.__lastPeaceCaller = player;
        return origIk(player);
      };
    }`,
  `    if (typeof ax === "object" && ax && typeof ax.iK === "function" && !ax.__hookedPeaceCaller) {
      ax.__hookedPeaceCaller = true;
      const origIk = ax.iK.bind(ax);
      ax.iK = function(player) {
        window.__lastPeaceCaller = player;
        return origIk(player);
      };
    }
    if (typeof ag === "object" && ag && typeof ag.rv === "function" && !ag.__hookedDoveEmote) {
      ag.__hookedDoveEmote = true;
      window.__doveEmoteTicks = new Map();
      const origRv = ag.rv.bind(ag);
      ag.rv = function(player, eI, aNa) {
        try {
          if ((eI === 0 || eI === 1) && aNa === ${PEACE_DOVE_EMOTE_ID}) {
            const curTick = (typeof bi === "object" && bi?.kr) ? bi.kr() : 0;
            if (!window.__doveEmoteTicks) window.__doveEmoteTicks = new Map();
            window.__doveEmoteTicks.set(player, curTick);
            window.__lastDoveEmote = { player, tick: curTick, ts: Date.now(), eI };
            if (window.__hlLog && (!window.__lastDoveLogMs || Date.now() - window.__lastDoveLogMs > 1500)) {
              window.__lastDoveLogMs = Date.now();
              window.__hlLog("[HL-DOVE-RX] t=" + curTick + " player=" + player + " eI=" + eI + " r5=" + aNa);
            }
          }
        } catch {}
        return origRv(player, eI, aNa);
      };
    }`,
  `ag.__hookedDoveEmote = true;`,
  'headless-bot hook ag.rv for Peace Dove emote (1017)'
);

hb = replaceOnce(
  hb,
  `        window.__lastPeaceCaller = -1;
        window.__tsbAssignedSpawn = null;
        window.__quitPlayers = new Set();`,
  `        window.__lastPeaceCaller = -1;
        window.__doveEmoteTicks = new Map();
        window.__lastDoveEmote = null;
        window.__bossDoveRemoteUntilMs = 0;
        window.__tsbAssignedSpawn = null;
        window.__quitPlayers = new Set();`,
  `window.__doveEmoteTicks = new Map();`,
  'headless-bot reset __doveEmoteTicks on new game'
);

fs.writeFileSync(hbPath, hb, 'utf8');
console.log('Patched', hbPath, 'len=', hb.length);

// =========================================================================
// 2. v27-team-live.js:
//    - Whitelist Boss account 9JNYv (aE.data.a7z[p] === 173115643) AND
//      exact name "[APEX] ok" / "[APEX]ok" in isBossNpl(), bypassing the
//      !low.startsWith("[apex]") guard.
//    - Exclude Boss from isSquadName() and isOurSquadBot() (while keeping
//      isProtectedSquadMate() true so bots never attack Boss).
//    - Do NOT modify spawn-coordinator.mjs (no forced FLANK_GUARD around
//      Boss per admin #130357).
//    - Replace aggressive tryEmergencyBossRescue + bossDonate hijack with:
//      1) Default mode: ONLY safe rear bots gently skim a small excess
//         (5.4%..9.3%B, keeping >=82*L inland / >=88*L coastal, cooldown 75t)
//         so squad keeps normal macro focus and doesn't dump everything.
//      2) Peace Dove (r5===1017) active mode (~44s / 800t per emote):
//         ONLY safe rear bots switch to priority full non-suicidal support
//         (up to ~27%B inland keeping >=42*L, ~19.5%B coastal keeping
//         >=72*L when sea enemies exist / >=52*L otherwise; frontline bots
//         NEVER drain themselves!).
// =========================================================================
let v27 = fs.readFileSync(v27Path, 'utf8').replace(/\r\n/g, '\n');

v27 = replaceOnce(
  v27,
  `  isBossNpl(g, p) {
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
      !low.startsWith("[apex]") &&`,
  `  isBossNpl(g, p) {
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
    const accArr = (typeof window !== "undefined" && window.aE?.data?.a7z) ? window.aE.data.a7z : null;
    const accUx = accArr ? (accArr[p] >>> 0) : 0;
    const raw = String(g.names?.[p] ?? "").trim();
    const low = raw.toLowerCase();
    if (accUx === ${BOSS_ACC_UX} || low === "[apex] ok" || low === "[apex]ok") {
      if (this._bossNameCache) this._bossNameCache[p] = 2;
      return true;
    }
    let res = false;
    if (
      !low.startsWith("[apex]") &&`,
  `if (accUx === ${BOSS_ACC_UX} || low === "[apex] ok" || low === "[apex]ok")`,
  'v27 isBossNpl 9JNYv + [APEX] ok whitelist'
);

v27 = replaceOnce(
  v27,
  `  isOurSquadBot(g, p) {
    const P = this.p;`,
  `  isOurSquadBot(g, p) {
    if (p !== this.me && this.isBossNpl(g, p)) return false;
    const P = this.p;`,
  `if (p !== this.me && this.isBossNpl(g, p)) return false;`,
  'v27 isOurSquadBot exclude Boss'
);

v27 = replaceOnce(
  v27,
  `  isSquadName(g, p) {
    if (p < 0 || p >= 512) return false;`,
  `  isSquadName(g, p) {
    if (p < 0 || p >= 512) return false;
    if (p !== this.me && this.isBossNpl(g, p)) return false;`,
  `  isSquadName(g, p) {\n    if (p < 0 || p >= 512) return false;\n    if (p !== this.me && this.isBossNpl(g, p)) return false;`,
  'v27 isSquadName exclude Boss'
);

// Replace tryEmergencyBossRescue(g) with 2-mode Safe-Rear Boss Support (default light skim + Peace Dove non-suicidal full rear support)
const oldBossRescueStart = `  // "最好的解围是给钱，打人只是附和10个点左右"
  tryEmergencyBossRescue(g) {`;
const oldBossRescueEnd = `    return false;
  }

  // UNIFIED ORGANISM: JOINT DEFENSE + TROOP PRODUCTION YIELD OPTIMIZER (t >= 1500 only):`;

if (!v27.includes('isBossDoveActive(g, bossId)')) {
  const sIdx = v27.indexOf(oldBossRescueStart);
  const eIdx = v27.indexOf(oldBossRescueEnd, sIdx);
  if (sIdx < 0 || eIdx < 0) throw new Error('Anchor not found: v27 tryEmergencyBossRescue block');
  const newBossSupport = `  isBossDoveActive(g, bossId) {
    if (bossId < 0 || typeof window === "undefined") return false;
    const localTick = window.__doveEmoteTicks?.get(bossId);
    if (typeof localTick === "number" && g.t >= localTick && g.t - localTick <= 800) {
      return true;
    }
    if (typeof window.__bossDoveRemoteUntilMs === "number" && Date.now() < window.__bossDoveRemoteUntilMs) {
      return true;
    }
    return false;
  }

  // Safe-Rear Boss Support (Default light skim + Peace Dove 1017 non-suicidal rear full support)
  tryEmergencyBossRescue(g) {
    const me = this.me;
    if (!g.teams || !(g.teams[me] > 0) || !g.canAct(me) || typeof g.donate !== "function") return false;
    const bossId = this.findBossId(g);
    if (bossId < 0 || !g.alive[bossId] || g.terr[bossId] < 100) return false;
    if (typeof window !== "undefined" && window.ao?.iD && !window.ao.iD(bossId)) return false;

    const doveActive = this.isBossDoveActive(g, bossId);
    if (!doveActive && g.t < 1500) return false;
    if (doveActive && g.t < 400) return false;

    const B = g.bal[me], L = Math.max(1, g.terr[me]), dMe = B / L;
    if (doveActive ? (L < 400 || B < 15000) : (L < 1200 || B < 35000)) return false;

    // Strictly SAFE REAR ONLY: zero incoming human attack, not fighting a human, zero enemy land borders!
    let myHumanInAtk = 0, myHumanOutAtk = 0;
    for (const a of g.attackersOf(me)) {
      if (!g.isBot(a) && !this.isTeammate(g, a)) myHumanInAtk += g.attackTroopsOn(a, me);
    }
    if (myHumanInAtk > 0) return false;
    const sbMe = g.slotBase(me);
    for (let i = 0; i < g.atkCount[me]; i++) {
      const tgt = g.atkTarget[sbMe + i];
      if (tgt >= 0 && tgt < g.humans && !g.isBot(tgt) && !this.isTeammate(g, tgt)) myHumanOutAtk += g.atkTroops[sbMe + i];
    }
    if (myHumanOutAtk > 0.05 * B) return false;

    const enemyHumanNbs = this.nb.filter((p) => g.alive[p] && this.person(g, p));
    if (enemyHumanNbs.length > 0) return false;
    if (this.cnt) {
      for (let p = 0; p < g.humans; p++) {
        if (p !== me && g.alive[p] && !this.isTeammate(g, p) && (this.cnt[p] ?? 0) > 0) {
          return false;
        }
      }
    }

    const B_boss = g.bal[bossId], L_boss = Math.max(1, g.terr[bossId]), dBoss = B_boss / L_boss;
    let bossInAtk = 0;
    for (const a of g.attackersOf(bossId)) {
      if (a !== me && !this.isTeammate(g, a)) bossInAtk += g.attackTroopsOn(a, bossId);
    }

    const hasExposedCoast = (g.coast?.[me]?.length ?? 0) > 0;
    const hasSeaEnemy = hasExposedCoast && this.seaPeople(g).length > 0;
    const isPureInlandSafe = !hasExposedCoast;

    if (doveActive) {
      // Peace Dove (r5===1017): rear full support while strictly preserving non-suicidal reserve floors
      if (dBoss >= 138) return false;
      const keepFloor = isPureInlandSafe ? 42 * L : (hasSeaEnemy && g.t >= 1000 ? 72 * L : 52 * L);
      const cooldown = isPureInlandSafe ? 16 : 22;
      if (B <= 1.08 * keepFloor || g.t - (this.lastBossDonateTick ?? -999) < cooldown) return false;
      const maxPct = Math.floor(((B - keepFloor) * 1024) / Math.max(1, B));
      const targetPct = isPureInlandSafe ? 280 : 200;
      const pct = Math.min(maxPct, targetPct);
      if (pct >= 55 && this.xDonate(g, pct, bossId, 'bossDoveSupport')) {
        this.lastDonateTick = g.t;
        this.lastBossDonateTick = g.t;
        this.cmds++;
        if (typeof window !== "undefined" && window.__hlLog) {
          window.__hlLog(\`[HL-DOVE-DONATE] t=\${g.t} rear dove support pct=\${pct}/1024 -> boss=\${bossId}(\${g.names?.[bossId] || "boss"}) myBal=\${B} dMe=\${Math.round(dMe)} floor=\${Math.round(keepFloor / L)} dBoss=\${Math.round(dBoss)} inland=\${isPureInlandSafe ? 1 : 0}\`);
        }
        return true;
      }
      return false;
    }

    // Default mode: gentle rear light skim only (never drains squad macro or frontline)
    const maxBossDens = bossInAtk > 0 ? 116 : 104;
    if (dBoss >= maxBossDens) return false;
    const mySlot = typeof window !== "undefined" && Number.isInteger(window.__tsbSquadSlot) ? window.__tsbSquadSlot : (me % 10);
    if (((g.t / 5) | 0) % 5 !== (mySlot % 5)) return false;
    const keepFloor = isPureInlandSafe ? 82 * L : 88 * L;
    const cooldown = 75;
    if (B <= 1.08 * keepFloor || g.t - (this.lastBossDonateTick ?? -999) < cooldown) return false;
    const maxPct = Math.floor(((B - keepFloor) * 1024) / Math.max(1, B));
    const targetPct = isPureInlandSafe ? 95 : 75;
    const pct = Math.min(maxPct, targetPct);
    if (pct >= 55 && this.xDonate(g, pct, bossId, 'bossLightSkim')) {
      this.lastDonateTick = g.t;
      this.lastBossDonateTick = g.t;
      this.cmds++;
      return true;
    }
    return false;
  }

  // UNIFIED ORGANISM: JOINT DEFENSE + TROOP PRODUCTION YIELD OPTIMIZER (t >= 1500 only):`;
  v27 = v27.slice(0, sIdx) + newBossSupport + v27.slice(eIdx + oldBossRescueEnd.length);
}

// Replace tryPeaceVote(g) so when Boss (9JNYv / [APEX] ok) is in the match:
//   - NEVER initiate a peace vote
//   - Vote NO (hz.iN(0)) on anyone else's peace vote
//   - Vote YES (hz.iN(1)) on Boss's peace vote (regardless of crown/land)
const oldPeaceStart = `  // AUTO PEACE VOTE CALL & ACCEPT:
  tryPeaceVote(g) {`;
const oldPeaceEnd = `  isBossDoveActive(g, bossId) {`;

if (!v27.includes('voted NO on non-Boss peace call')) {
  const pStart = v27.indexOf(oldPeaceStart);
  const pEnd = v27.indexOf(oldPeaceEnd, pStart);
  if (pStart < 0 || pEnd < 0) throw new Error('Anchor not found: v27 tryPeaceVote block');
  const newPeaceBlock = `  findAnyBossInMatch(g) {
    const aliveBoss = this.findBossId(g);
    if (aliveBoss >= 0) return aliveBoss;
    const accArr = (typeof window !== "undefined" && window.aE?.data?.a7z) ? window.aE.data.a7z : null;
    for (let p = 0; p < g.humans; p++) {
      if (p === this.me) continue;
      if (typeof window !== "undefined" && window.__quitPlayers && window.__quitPlayers.has(p)) continue;
      const accUx = accArr ? (accArr[p] >>> 0) : 0;
      const low = String(g.names?.[p] ?? "").trim().toLowerCase();
      if (accUx === ${BOSS_ACC_UX} || low === "[apex] ok" || low === "[apex]ok") {
        if (!g.teams || this.isTeammate(g, p)) return p;
      }
    }
    return -1;
  }

  // AUTO PEACE VOTE CALL & ACCEPT:
  // Boss rule: when Boss is in the match, NEVER initiate peace vote; vote NO on others; vote YES on Boss!
  tryPeaceVote(g) {
    if (typeof window === "undefined" || !window.ax || !window.dictionary || g.t < 1610) return;
    const me = this.me;
    const hz = window[window.dictionary.sbCommands]?.hz;
    if (!hz) return;

    const bossAnyId = this.findAnyBossInMatch(g);
    if (bossAnyId >= 0) {
      // Boss is present in this match: NEVER initiate peace vote; YES on Boss, NO on everyone else.
      if (window.ax.iL && typeof window.ax.iM === "function" && window.ax.iM(me) && typeof hz.iN === "function") {
        if (g.t - (this._lastPeaceReplyTick ?? -999) < 25) return;
        const caller = window.__lastPeaceCaller;
        const callerIsBoss =
          Number.isInteger(caller) &&
          caller >= 0 &&
          caller < g.humans &&
          (caller === bossAnyId || this.isBossNpl(g, caller));
        this._lastPeaceReplyTick = g.t;
        if (callerIsBoss) {
          hz.iN(1);
          if (window.__hlLog) {
            window.__hlLog(\`[HL-PEACE] t=\${g.t} voted YES on Boss peace call by p=\${caller}(\${g.names?.[caller] || ""})\`);
          }
        } else {
          hz.iN(0);
          if (window.__hlLog) {
            window.__hlLog(\`[HL-PEACE] t=\${g.t} voted NO on non-Boss peace call by p=\${caller}(\${g.names?.[caller] || ""})\`);
          }
        }
      }
      return;
    }

    if (g.t < 7500) return; // Autonomous squad: allow peace vote after t>=7500 when holding crown + >=85% teamLand
    let ourTeamLand = g.terr[me] || 0;
    if (g.teams && g.teams[me] > 0) {
      ourTeamLand = 0;
      for (let p = 0; p < g.players; p++) {
        if (g.alive[p] && g.teams[p] === g.teams[me]) ourTeamLand += g.terr[p];
      }
    }
    let topPlayer = -1, topTerr = -1;
    for (let p = 0; p < g.players; p++) {
      if (g.alive[p] && g.terr[p] > topTerr) {
        topTerr = g.terr[p];
        topPlayer = p;
      }
    }
    const weHoldCrown = topPlayer >= 0 && (topPlayer === me || this.isOurSquadBot(g, topPlayer));
    const weLead = weHoldCrown && (ourTeamLand >= 0.85 * Math.max(1, g.land) || this.isMopUp(g));
    const caller = window.__lastPeaceCaller;
    const callerIsOurs =
      weHoldCrown &&
      Number.isInteger(caller) &&
      caller >= 0 &&
      caller < g.humans &&
      (caller === me || this.isOurSquadBot(g, caller));
    if (window.ax.iL && typeof window.ax.iM === "function" && window.ax.iM(me)) {
      if (callerIsOurs && typeof hz.iN === "function") {
        hz.iN(1);
        if (window.__hlLog && g.t - (this._lastPeaceVoteLog ?? -999) >= 100) {
          this._lastPeaceVoteLog = g.t;
          window.__hlLog(\`[HL-PEACE] t=\${g.t} voted YES on our squad's peace call by p=\${caller}(\${g.names?.[caller] || ""}) (teamLand=\${(100 * ourTeamLand / Math.max(1, g.land)).toFixed(1)}%)\`);
        }
      }
    } else if (!window.ax.iL && weLead && g.t - (this.lastPeaceKeyTick ?? -999) >= 105 && typeof window.ax.iO === "function" && window.ax.iO(me)) {
      this.lastPeaceKeyTick = g.t;
      window.__lastPeaceCaller = me;
      if (typeof hz.iK === "function") {
        hz.iK();
        if (window.__hlLog) window.__hlLog(\`[HL-PEACE] t=\${g.t} initiated peace vote (teamLand=\${(100 * ourTeamLand / Math.max(1, g.land)).toFixed(1)}%)\`);
      }
    }
  }

  isBossDoveActive(g, bossId) {`;
  v27 = v27.slice(0, pStart) + newPeaceBlock + v27.slice(pEnd + oldPeaceEnd.length);
}

// In tryDonateToTeammate: remove the old aggressive bossDonate hijack and instead hold rear surplus for Boss while Peace Dove is active
v27 = replaceOnce(
  v27,
  `    const bossId = this.findBossId(g);
    if (bossId >= 0 && g.alive[bossId] && g.terr[bossId] >= 100 && (!window.ao?.iD || window.ao.iD(bossId))) {
      const dBoss = g.bal[bossId] / Math.max(1, g.terr[bossId]);
      let bossInAtk = 0;
      for (const a of g.attackersOf(bossId)) bossInAtk += g.attackTroopsOn(a, bossId);
      const bossFloor = bossInAtk > 0 ? (boxedIn ? 40 * L : 72 * L) : (boxedIn ? 75 * L : 88 * L);
      if ((bossInAtk > 0 || dBoss < 112) && B > 1.15 * bossFloor) {
        const maxPct = Math.floor(((B - bossFloor) * 1024) / B);
        const pct = Math.min(maxPct, boxedIn ? 260 : 180);
        if (pct >= 120 && this.xDonate(g, pct, bossId, 'bossDonate')) {
          this.lastDonateTick = g.t;
          this.lastBossDonateTick = g.t;
          this.cmds++;
          return true;
        }
      }
    }`,
  `    const bossId = this.findBossId(g);
    if (bossId >= 0 && g.alive[bossId] && g.terr[bossId] >= 100 && !anyEnemyNb && this.isBossDoveActive(g, bossId)) {
      const dBoss = g.bal[bossId] / Math.max(1, g.terr[bossId]);
      if (dBoss < 135) {
        // Peace Dove active: safe rear bots reserve their surplus for Boss instead of diverting it elsewhere
        return false;
      }
    }`,
  `// Peace Dove active: safe rear bots reserve their surplus for Boss`,
  'v27 tryDonateToTeammate replace bossDonate hijack with dove rear reserve'
);

fs.writeFileSync(v27Path, v27, 'utf8');
console.log('Patched', v27Path, 'len=', v27.length);

// =========================================================================
// 3. tsb-apex-squad.mjs:
//    - Dedicate slot 39 (PizzaTime) as permanent Lobby Room 0 Sentinel
//      (c.isLobbySentinel = true): never enters matches, never gets kicked
//      from Room 0 while squad is in-game, prioritized first for mint/re-entry.
//    - Detect Boss account 9JNYv (uX === 173115643) AND exact name "[APEX] ok"
//      in Room 0 (bq.wZ.w1) including which room card p.wk Boss clicked, and
//      in-game (aE.data.a7z + rawPlayerNames).
//    - Relay directed Peace Dove emote (1017) across all in-game bots if Boss
//      clicks a single teammate directly.
//    - When Boss appears in Room 0:
//      1) Recall all bots currently in an unrelated match (and after 12s
//         match-start grace, recall bots if Boss left the match and stayed
//         in Room 0 >= 4s), pre-tagging them [APEX] so they re-enter tagged.
//      2) Hold all non-sentinel bots in Room 0 tagged [APEX] with select(0)
//         waiting for Boss.
//      3) When Boss clicks any room card (p.wk > 0 && !p.wv), immediately
//         follow Boss into that exact room card (team-size-aware K=6..22).
//      4) When Boss goes offline (>12s) and not in-game, resume normal
//         autonomous farming automatically while sentinel stays in Room 0.
// =========================================================================
let sq = fs.readFileSync(sqPath, 'utf8').replace(/\r\n/g, '\n');

sq = replaceOnce(
  sq,
  `const CLAN_TAG_POOL = ["APEX"];
let activeClanTag = "APEX";`,
  `const CLAN_TAG_POOL = ["APEX"];
let activeClanTag = "APEX";
const BOSS_WATCH_ACCOUNTS = ${JSON.stringify(BOSS_ACC_IDS)};
const BOSS_WATCH_UX_LIST = [${BOSS_ACC_UX}];
const BOSS_WATCH_NAMES_LOW = ["[apex] ok", "[apex]ok"];
const LOBBY_SENTINEL_SLOT = 39;`,
  `const LOBBY_SENTINEL_SLOT = 39;`,
  'squad boss watch constants'
);

sq = replaceOnce(
  sq,
  `  hc.donorChromePort = bot.donorChromePort;
  hc.baseName = bot.baseName || bot.name;
  hc.name = hc.baseName;
  clients.push(hc);`,
  `  hc.donorChromePort = bot.donorChromePort;
  hc.baseName = bot.baseName || bot.name;
  hc.isLobbySentinel = bot.slot === LOBBY_SENTINEL_SLOT;
  hc.name = hc.baseName;
  if (hc.isLobbySentinel) {
    console.log(\`[BOSS-SENTINEL] Designated slot=\${bot.slot} (\${hc.baseName}) as permanent Lobby Room 0 sentinel watching for Boss: \${BOSS_WATCH_ACCOUNTS.join(', ')} / [APEX] ok\`);
  }
  clients.push(hc);`,
  `hc.isLobbySentinel = bot.slot === LOBBY_SENTINEL_SLOT;`,
  'squad designate sentinel client'
);

// Detect Boss (account 9JNYv OR name "[APEX] ok") in Room 0 list (p.uX, p.username/aGM, p.wk, p.wv)
sq = replaceOnce(
  sq,
  `        let room0Players = 0;
        let room0NopeCount = 0;
        let bossReadyInRoom0 = false;`,
  `        let room0Players = 0;
        let room0NopeCount = 0;
        let bossReadyInRoom0 = false;
        let bossAccInRoom0 = false;
        let bossAccRoomId = 0;
        let bossAccNameInRoom0 = "";
        const bossUxSet = new Set(${JSON.stringify([BOSS_ACC_UX])});
        const bossNameLowSet = new Set(["[apex] ok", "[apex]ok"]);
        if (typeof bJ === "object" && bJ?.f0?.f1) {
          for (const accStr of ${JSON.stringify(BOSS_ACC_IDS)}) {
            try { bossUxSet.add(bJ.f0.f1(accStr, 5) >>> 0); } catch {}
          }
        }`,
  `let bossAccInRoom0 = false;`,
  'squad poll declare bossAccInRoom0'
);

sq = replaceOnce(
  sq,
  `              const raw = String((p && (p.aGM || p.aGT || p.aFN || p.username || p.name)) || "").trim();`,
  `              const raw = String((p && (p.aGM || p.aGT || p.aFN || p.username || p.name)) || "").trim();
              const isWatchedBossLobby =
                (p && typeof p.uX === "number" && bossUxSet.has(p.uX >>> 0)) ||
                bossNameLowSet.has(lowDisp) ||
                bossNameLowSet.has(raw.toLowerCase());
              if (isWatchedBossLobby) {
                bossAccInRoom0 = true;
                bossAccNameInRoom0 = String((p && (p.username || p.aGM)) || raw || "9JNYv").trim();
                if (p && p.wk > 0 && !p.wv) {
                  bossAccRoomId = p.wk | 0;
                  bossReadyInRoom0 = true;
                }
              }`,
  `const isWatchedBossLobby =`,
  'squad poll match p.uX / [APEX] ok in Room 0'
);

sq = replaceOnce(
  sq,
  `        s.room0Players = room0Players;
        s.bossReadyInRoom0 = bossReadyInRoom0;`,
  `        s.room0Players = room0Players;
        s.bossReadyInRoom0 = bossReadyInRoom0;
        s.bossAccInRoom0 = bossAccInRoom0;
        s.bossAccRoomId = bossAccRoomId;
        s.bossAccNameInRoom0 = bossAccNameInRoom0;`,
  `s.bossAccInRoom0 = bossAccInRoom0;`,
  'squad poll export bossAccInRoom0 fields'
);

// Detect Boss (account 9JNYv OR name "[APEX] ok") in-game via aE.data.a7z + rawNames, plus dove emote tick
sq = replaceOnce(
  sq,
  `          const H = (g && g[d.gHumans]) || 512;
          let bossIdx = -1;
          if (rawNames) {`,
  `          const H = (g && g[d.gHumans]) || 512;
          let bossIdx = -1;
          let bossAccInGame = false;
          const accArrInGame = (typeof aE === "object" && aE?.data?.a7z) ? aE.data.a7z : null;
          if (accArrInGame) {
            const lim = Math.min(H, accArrInGame.length);
            for (let p = 0; p < lim; p++) {
              if (bossUxSet.has(accArrInGame[p] >>> 0)) {
                bossIdx = p;
                bossAccInGame = true;
                break;
              }
            }
          }
          if (bossIdx < 0 && rawNames) {
            for (let p = 0; p < H; p++) {
              const rawB = String(rawNames[p] ?? "").trim().toLowerCase();
              if (bossNameLowSet.has(rawB)) {
                bossIdx = p;
                bossAccInGame = true;
                break;
              }
            }
          }
          if (bossIdx < 0 && rawNames) {`,
  `let bossAccInGame = false;`,
  'squad poll in-game aE.data.a7z + [APEX] ok Boss check'
);

sq = replaceOnce(
  sq,
  `          s.bossId = bossIdx;
          // ONLY trigger leave if Boss is not in this match at all (bossIdx < 0) OR Boss explicitly sent a quit/surrender/disconnect packet (r8 / rd in window.__quitPlayers)!
          // If Boss died (terr === 0 / alive === 0) without sending quit packet, NEVER leave!
          const bossExplicitQuit = !!(window.__quitPlayers && bossIdx >= 0 && window.__quitPlayers.has(bossIdx));
          s.bossActiveInGame = bossIdx >= 0 && !bossExplicitQuit;`,
  `          s.bossId = bossIdx;
          s.bossAccInGame = bossAccInGame;
          const doveTickVal = (bossIdx >= 0 && window.__doveEmoteTicks) ? window.__doveEmoteTicks.get(bossIdx) : -1;
          s.bossDoveTick = typeof doveTickVal === "number" ? doveTickVal : -1;
          // ONLY trigger leave if Boss is not in this match at all (bossIdx < 0) OR Boss explicitly sent a quit/surrender/disconnect packet (r8 / rd in window.__quitPlayers)!
          // If Boss died (terr === 0 / alive === 0) without sending quit packet, NEVER leave!
          const bossExplicitQuit = !!(window.__quitPlayers && bossIdx >= 0 && window.__quitPlayers.has(bossIdx));
          s.bossActiveInGame = bossIdx >= 0 && !bossExplicitQuit;`,
  `s.bossAccInGame = bossAccInGame;`,
  'squad poll export bossAccInGame + bossDoveTick'
);

// Boss-Sentinel presence tracking, Peace Dove relay, & immediate recall BEFORE anyMeaningfulAlive
sq = replaceOnce(
  sq,
  `  // Never reload or re-open lobby while ANY bot is alive in-game or in opening!
  const anyMeaningfulAlive = states.some((s, idx) => {`,
  `  // Boss Account Sentinel & Recall (9JNYv / [APEX] ok):
  // If Boss is spotted in Lobby Room 0 (by sentinel or any lobby bot),
  // immediately recall all bots in unrelated matches back to Room 0 to wait for Boss!
  const sentinelIdx = clients.findIndex((c) => c.isLobbySentinel);
  const sentinelClient = sentinelIdx >= 0 ? clients[sentinelIdx] : null;
  const sentinelState = sentinelIdx >= 0 ? states[sentinelIdx] : null;
  if (sentinelClient && sentinelState?.lobby?.inLobby && sentinelState.lobby.room === 0 && !sentinelClient.__loggedSentinelReady) {
    sentinelClient.__loggedSentinelReady = true;
    console.log(\`[BOSS-SENTINEL] \${sentinelClient.name} (slot=\${sentinelClient.slot}) is online in Lobby Room 0 (players=\${sentinelState.room0Players || 0}), watching for \${BOSS_WATCH_ACCOUNTS.join(', ')} / [APEX] ok\`);
  }
  if (sentinelClient && !(sentinelState?.lobby?.inLobby && sentinelState.lobby.room === 0)) {
    sentinelClient.__loggedSentinelReady = false;
  }
  // If sentinel ever accidentally entered a match, leave immediately back to Room 0
  if (sentinelClient && sentinelState?.inGame) {
    sentinelState.inGame = false;
    sentinelClient.wasInGame = false;
    sentinelClient.enteredLobbyAt = 0;
    sentinelClient.evalJs(\`(() => {
      window.__tsbSquadSyncHold = true;
      const d = window.dictionary, g = d && window[d.game];
      if (g && g[d.sbLeave] && g[d.gameState] !== 0) g[d.sbLeave](true);
    })()\`);
  }

  // Relay directed Peace Dove emote (1017) across all in-game bots in the same match
  let maxBossDoveTick = -1;
  for (let i = 0; i < states.length; i++) {
    const s = states[i];
    if (s?.inGame && s.bossAccInGame && typeof s.bossDoveTick === 'number' && s.bossDoveTick >= 0 && (s.tick || 0) - s.bossDoveTick <= 800) {
      if (s.bossDoveTick > maxBossDoveTick) maxBossDoveTick = s.bossDoveTick;
    }
  }
  if (maxBossDoveTick >= 0 && maxBossDoveTick !== globalThis.__lastRelayedBossDoveTick) {
    globalThis.__lastRelayedBossDoveTick = maxBossDoveTick;
    const untilMs = Date.now() + 44000;
    console.log(\`[BOSS-DOVE] Detected Boss Peace Dove (r5=1017) at tick=\${maxBossDoveTick} -> activating safe-rear full support across squad (~44s)!\`);
    for (let i = 0; i < clients.length; i++) {
      if (states[i]?.inGame && !clients[i].isLobbySentinel) {
        clients[i].evalJs(\`(() => { window.__bossDoveRemoteUntilMs = \${untilMs}; })()\`);
      }
    }
  } else if (maxBossDoveTick < 0 && !states.some((s) => s?.inGame)) {
    globalThis.__lastRelayedBossDoveTick = -1;
  }

  const bossAccSeenInRoom0 = inRoom0.some((s) => !!s.bossAccInRoom0);
  const bossAccPickedRoomId = inRoom0.reduce((id, s) => id || (s.bossAccRoomId || 0), 0);
  const bossAccSeenName = inRoom0.find((s) => s.bossAccNameInRoom0)?.bossAccNameInRoom0 || BOSS_WATCH_ACCOUNTS[0];
  if (bossAccSeenInRoom0) {
    if (!globalThis.__bossAccSeenLobbySince) globalThis.__bossAccSeenLobbySince = now;
    globalThis.__bossAccLastSeenLobbyAt = now;
  } else {
    globalThis.__bossAccSeenLobbySince = 0;
  }

  if (bossAccSeenInRoom0) {
    const toRecall = [];
    for (let i = 0; i < clients.length; i++) {
      const s = states[i];
      if (!s?.inGame) continue;
      if (!s.bossAccInGame) {
        toRecall.push(i);
      } else {
        // Boss was in this match, but if Boss left and has been back in Room 0 (past 12s match-start grace), recall too
        const inMatchAge = now - (clients[i].enteredGameAt || 0);
        const lobbyStayMs = globalThis.__bossAccSeenLobbySince ? (now - globalThis.__bossAccSeenLobbySince) : 0;
        if (inMatchAge >= 12000 && (!s.bossActiveInGame || lobbyStayMs >= 4000)) {
          toRecall.push(i);
        }
      }
    }
    if (toRecall.length > 0) {
      console.log(
        \`[BOSS-ACC-RECALL] Boss \${BOSS_WATCH_ACCOUNTS[0]} ("\${bossAccSeenName}") detected online in Room 0 -> exiting match for \${toRecall.length} bots to wait in Lobby!\`
      );
      globalThis.__chosenBigRoomId = 0;
      globalThis.__lastChosenCard = null;
      for (const i of toRecall) {
        states[i].inGame = false;
        clients[i].wasInGame = false;
        clients[i].lastReloadAt = 0;
        clients[i].enteredLobbyAt = 0;
        clients[i].retaggingUntil = 0;
        clients[i].retagTargetRoomId = 0;
        if (!clients[i].isLobbySentinel) {
          clients[i].name = ('[' + activeClanTag + '] ' + clients[i].baseName).slice(0, 20);
        }
        clients[i].evalJs(\`(() => {
          window.__tsbSquadSyncHold = true;
          const d = window.dictionary;
          const g = d && window[d.game];
          if (g && g[d.sbLeave] && g[d.gameState] !== 0) g[d.sbLeave](true);
        })()\`);
      }
    }
  }

  const anyBotInMatchWithBoss = states.some((s) => !!s?.inGame && !!s.bossAccInGame);
  if (anyBotInMatchWithBoss && !bossAccSeenInRoom0) {
    globalThis.__bossAccLastSeenLobbyAt = 0;
  }
  const bossWaitingInLobby =
    bossAccSeenInRoom0 ||
    (globalThis.__bossAccLastSeenLobbyAt > 0 && now - globalThis.__bossAccLastSeenLobbyAt < 12000 && !anyBotInMatchWithBoss);
  if (bossWaitingInLobby && !globalThis.__bossWaitActiveLog) {
    globalThis.__bossWaitActiveLog = true;
    console.log(\`[BOSS-WAIT] Boss \${BOSS_WATCH_ACCOUNTS[0]} ("\${bossAccSeenName}") is in Lobby Room 0 -> holding squad in Lobby (selectedRoom=\${bossAccPickedRoomId})!\`);
  } else if (!bossWaitingInLobby && globalThis.__bossWaitActiveLog) {
    globalThis.__bossWaitActiveLog = false;
    console.log(\`[BOSS-WAIT] Boss \${BOSS_WATCH_ACCOUNTS[0]} left Lobby (inMatchWithBoss=\${anyBotInMatchWithBoss}) -> releasing Lobby hold.\`);
  }

  // Never reload or re-open lobby while ANY bot is alive in-game or in opening!
  const anyMeaningfulAlive = states.some((s, idx) => {`,
  `[BOSS-ACC-RECALL]`,
  'squad boss sentinel, dove relay, and recall logic'
);

// Inside if (anyMeaningfulAlive): keep sentinel in Room 0 and auto-reconnect sentinel if needed!
sq = replaceOnce(
  sq,
  `      } else if (!st?.inGame && st?.lobby?.inLobby) {
        // Early-dead bot auto-bounced into lobby while teammates are still fighting -> close lobby & hold at menu!`,
  `      } else if (cl.isLobbySentinel) {
        // Dedicated Lobby Sentinel stays in Room 0 with select(0) while squad fights
        if (st?.lobby?.inLobby) {
          cl.evalJs(\`(() => {
            window.__tsbSquadSyncHold = true;
            if (typeof bq === "object" && bq?.sH && typeof bq.sH.select === "function" && bq.sH.wF) {
              try { bq.sH.select(0); } catch {}
            }
          })()\`);
        }
      } else if (!st?.inGame && st?.lobby?.inLobby) {
        // Early-dead bot auto-bounced into lobby while teammates are still fighting -> close lobby & hold at menu!`,
  `else if (cl.isLobbySentinel)`,
  'squad keep sentinel in Room 0 while squad in-game'
);

sq = replaceOnce(
  sq,
  `      console.log(\`[OPENING-CHECK \${inGameStates.length} bots @ tick \${maxTickNow}] \${summary}\`);
    }
    return;
  }`,
  `      console.log(\`[OPENING-CHECK \${inGameStates.length} bots @ tick \${maxTickNow}] \${summary}\`);
    }
    // Keep Lobby Sentinel connected to Room 0 even while squad is fighting in-game!
    if (sentinelClient && !(sentinelState?.lobby?.inLobby && sentinelState.lobby.room === 0) && !sentinelState?.inGame) {
      if (!sentinelClient.freshToken && !sentinelClient.minting && now - sentinelClient.lastReloadAt > 60000 && now - sentinelClient.enteredLobbyAt > 12000 && mintSlotFree(0)) {
        console.log(\`[BOSS-SENTINEL] Minting Turnstile token for Lobby Sentinel \${sentinelClient.name} while squad is in-game...\`);
        reloadClientForToken(sentinelClient);
      } else if (sentinelClient.freshToken && now - sentinelClient.enteredLobbyAt > 15000) {
        sentinelClient.enteredLobbyAt = now;
        console.log(\`[BOSS-SENTINEL] Re-entering Lobby Room 0 for sentinel \${sentinelClient.name} while squad is in-game...\`);
        sentinelClient.evalJs(\`(() => {
          try {
            localStorage.setItem("d122", \${JSON.stringify(sentinelClient.baseName)});
            localStorage.setItem("v122", "0");
            if (typeof bm === "object" && bm?.buffer?.data?.[122]) bm.buffer.data[122].value = \${JSON.stringify(sentinelClient.baseName)};
          } catch {}
          if (typeof bq === "object" && bq?.f6 === 1 && typeof b1 === "object" && b1?.z?.ef?.(1)) return "ALREADY_IN_LOBBY";
          if (typeof b1 === "object" && b1?.z?.close) b1.z.close(1, 3252);
          const ext = window.__fx?.strategyBotExtension;
          if (ext) { ext.settings.armed = true; ext.remote.state.loop = "team"; }
          window.__tsbSquadSyncHold = false;
          if (typeof b1 === "object" && b1?.z) b1.z.f7 = 1;
          window.__fx?.strategyBot?.openMultiplayer?.(0);
          setTimeout(() => { window.__tsbSquadSyncHold = true; }, 5000);
        })()\`);
      }
    }
    return;
  }`,
  `[BOSS-SENTINEL] Re-entering Lobby Room 0`,
  'squad keep sentinel reconnected during in-game'
);

// Do not retag sentinel with [APEX] after match finish
sq = replaceOnce(
  sq,
  `    for (const c of clients) {
      if (c.isHeadless) {
        c.name = ('[' + activeClanTag + '] ' + c.baseName).slice(0, 20);
        c.retaggingUntil = 0;
        c.retagTargetRoomId = 0;
      }
    }`,
  `    for (const c of clients) {
      if (c.isHeadless) {
        c.name = c.isLobbySentinel ? c.baseName : ('[' + activeClanTag + '] ' + c.baseName).slice(0, 20);
        c.retaggingUntil = 0;
        c.retagTargetRoomId = 0;
      }
    }`,
  `c.name = c.isLobbySentinel ? c.baseName`,
  'squad keep sentinel untagged post-match'
);

// Override room selection when Boss is in Lobby Room 0
sq = replaceOnce(
  sq,
  `  const targetRoomId = chosenCard ? chosenCard.id : 0;
  const minStartsIn = chosenCard ? chosenCard.wK : (inRoom0.length ? Math.min(...inRoom0.map((s) => s.lobby.startsIn || 999)) : 999);`,
  `  const bossFollowMode = bossWaitingInLobby && bossAccPickedRoomId > 0;
  if (bossWaitingInLobby) {
    if (bossAccPickedRoomId > 0) {
      const bossCard = sampleCards.find((r) => r.id === bossAccPickedRoomId) || {
        id: bossAccPickedRoomId, wK: 15, h2: 0, nS: 512, fF: 0, vz: 1, wN: 0,
      };
      if (globalThis.__lastBossFollowRoomId !== bossAccPickedRoomId) {
        globalThis.__lastBossFollowRoomId = bossAccPickedRoomId;
        console.log(\`[BOSS-FOLLOW] Boss \${BOSS_WATCH_ACCOUNTS[0]} ("\${bossAccSeenName}") picked Room id=\${bossCard.id} (mode=\${bossCard.vz < 7 ? (bossCard.vz + 2) + 'T' : 'M' + bossCard.vz}, players=\${bossCard.h2}/\${bossCard.nS}, startsIn=\${bossCard.wK}s, map=\${bossCard.fF}) -> following immediately!\`);
      }
      chosenCard = bossCard;
    } else {
      globalThis.__lastBossFollowRoomId = 0;
      chosenCard = null;
    }
  } else {
    globalThis.__lastBossFollowRoomId = 0;
  }
  const targetRoomId = chosenCard ? chosenCard.id : 0;
  const minStartsIn = chosenCard ? chosenCard.wK : (inRoom0.length ? Math.min(...inRoom0.map((s) => s.lobby.startsIn || 999)) : 999);`,
  `const bossFollowMode = bossWaitingInLobby && bossAccPickedRoomId > 0;`,
  'squad boss room selection override'
);

// Exclude sentinel from verifiedApexIndices; during bossFollowMode include unlocked Room-0 bots so they retag+select seamlessly
sq = replaceOnce(
  sq,
  `  const verifiedApexIndices = [];
  states.forEach((s, idx) => {
    const c = clients[idx];
    if (!c.isHeadless && headlessOnly) return;
    const isVerifiedInRoom0 =
      s?.lobby?.inLobby &&
      s.lobby.room === 0 &&
      typeof s.myLobbyUsername === 'string' &&
      !s.myLobbyUsername.includes('Redacted') &&
      !s.myLobbyUsername.startsWith('Player ') &&
      s.myLobbyUsername.startsWith(\`[\${activeClanTag}]\`);`,
  `  const verifiedApexIndices = [];
  states.forEach((s, idx) => {
    const c = clients[idx];
    if (c.isLobbySentinel) return;
    if (!c.isHeadless && headlessOnly) return;
    const isVerifiedInRoom0 =
      s?.lobby?.inLobby &&
      s.lobby.room === 0 &&
      typeof s.myLobbyUsername === 'string' &&
      !s.myLobbyUsername.includes('Redacted') &&
      !s.myLobbyUsername.startsWith('Player ') &&
      (bossFollowMode || s.myLobbyUsername.startsWith(\`[\${activeClanTag}]\`));`,
  `if (c.isLobbySentinel) return;`,
  'squad exclude sentinel from verifiedApexIndices + bossFollowMode unlocked'
);

// Dynamic pool sizing when bossFollowMode is active (team-size-aware K=6..22, min >= 1, bypass anti-collision)
sq = replaceOnce(
  sq,
  `  let desiredK = 0;
  if (targetRoomId > 0 && inCommitWindow && verifiedApexIndices.length >= 10) {
    const growthMult = minStartsIn > 8 ? 1.25 : 1.12;
    const idealFullTeamK = outsidersE > 0 ? Math.ceil((outsidersE * growthMult) / Math.max(1, roomTeamsT - 1)) : 14;
    const roomSpaceLeft = Math.max(0, roomCapNs - outsidersE);
    desiredK = Math.max(10, Math.min(22, verifiedApexIndices.length, roomSpaceLeft, Math.max(10, idealFullTeamK)));
    if (minStartsIn <= 6 && ourAlreadySelectedOnTarget >= 10) {
      desiredK = Math.max(desiredK, Math.min(22, verifiedApexIndices.length, ourAlreadySelectedOnTarget));
    }
  }

  const chosenBotIdxSet = new Set();
  if (!avoidC110Collision && timerSpreadOk && desiredK >= 10) {`,
  `  let desiredK = 0;
  if (bossFollowMode && targetRoomId > 0 && verifiedApexIndices.length >= 1) {
    const effectiveT = chosenCard && chosenCard.vz >= 0 && chosenCard.vz <= 6 ? Math.max(2, (chosenCard.vz | 0) + 2) : 2;
    const growthMult = minStartsIn > 8 ? 1.25 : 1.12;
    const idealFullTeamK = outsidersE > 1 ? Math.ceil(((outsidersE - 1) * growthMult) / Math.max(1, effectiveT - 1)) : 12;
    const roomSpaceLeft = Math.max(0, roomCapNs - outsidersE);
    desiredK = Math.min(22, verifiedApexIndices.length, roomSpaceLeft, Math.max(6, idealFullTeamK));
  } else if (!bossWaitingInLobby && targetRoomId > 0 && inCommitWindow && verifiedApexIndices.length >= 10) {
    const growthMult = minStartsIn > 8 ? 1.25 : 1.12;
    const idealFullTeamK = outsidersE > 0 ? Math.ceil((outsidersE * growthMult) / Math.max(1, roomTeamsT - 1)) : 14;
    const roomSpaceLeft = Math.max(0, roomCapNs - outsidersE);
    desiredK = Math.max(10, Math.min(22, verifiedApexIndices.length, roomSpaceLeft, Math.max(10, idealFullTeamK)));
    if (minStartsIn <= 6 && ourAlreadySelectedOnTarget >= 10) {
      desiredK = Math.max(desiredK, Math.min(22, verifiedApexIndices.length, ourAlreadySelectedOnTarget));
    }
  }

  const chosenBotIdxSet = new Set();
  if ((bossFollowMode && desiredK >= 1) || (!bossWaitingInLobby && !avoidC110Collision && timerSpreadOk && desiredK >= 10)) {`,
  `if (bossFollowMode && targetRoomId > 0 && verifiedApexIndices.length >= 1)`,
  'squad bossFollowMode dynamic pool sizing'
);

// Keep sentinel allowReady=false & wantTag=false; keep combat bots tagged while bossWaitingInLobby
sq = replaceOnce(
  sq,
  `      const allowReady = !isStandby && (waitMode ? bossReadyNow : chosenBotIdxSet.has(idx));
      const curLobbyStr0 = String(states[idx]?.myLobbyUsername || '');
      const hasCustomNameUnlocked = curLobbyStr0.length > 0 && !curLobbyStr0.includes('Player ') && !curLobbyStr0.includes('Redacted');
      const wantTag = !isStandby && !waitMode && (hasCustomNameUnlocked ? (allowReady && targetRoomId > 0) : true);`,
  `      const allowReady = !c.isLobbySentinel && !isStandby && (waitMode ? bossReadyNow : chosenBotIdxSet.has(idx));
      const curLobbyStr0 = String(states[idx]?.myLobbyUsername || '');
      const hasCustomNameUnlocked = curLobbyStr0.length > 0 && !curLobbyStr0.includes('Player ') && !curLobbyStr0.includes('Redacted');
      const wantTag = !c.isLobbySentinel && !isStandby && !waitMode && (bossWaitingInLobby ? true : (hasCustomNameUnlocked ? (allowReady && targetRoomId > 0) : true));`,
  `const allowReady = !c.isLobbySentinel && !isStandby`,
  'squad sentinel allowReady/wantTag and bossWaitingInLobby tag hold'
);

// Relax card filter inside evalJs when bossFollowMode is true so bots follow Boss into ANY room card Boss clicks
sq = replaceOnce(
  sq,
  `                    const cardStillThere = bq.sH.sH.find(r => r && r.id === wantId && (r.vz === 1 || r.vz === 2) && (r.nS === 0 || r.nS > 32));`,
  `                    const cardStillThere = bq.sH.sH.find(r => r && r.id === wantId && (\${bossFollowMode ? 'true' : '(r.vz === 1 || r.vz === 2) && (r.nS === 0 || r.nS > 32)'}));`,
  `bossFollowMode ? 'true' : '(r.vz === 1`,
  'squad relax cardStillThere filter for bossFollowMode'
);

// Prioritize Lobby Sentinel first in rawNeedReload minting queue
sq = replaceOnce(
  sq,
  `  const perDonorCnt = new Map();
  const needReload = [];
  const squadInGameNow = states.some((s) => !!s?.inGame);
  for (const c of rawNeedReload) {`,
  `  rawNeedReload.sort((a, b) => (b.isLobbySentinel ? 1 : 0) - (a.isLobbySentinel ? 1 : 0));
  const perDonorCnt = new Map();
  const needReload = [];
  const squadInGameNow = states.some((s) => !!s?.inGame);
  for (const c of rawNeedReload) {`,
  `rawNeedReload.sort((a, b) => (b.isLobbySentinel ? 1 : 0) - (a.isLobbySentinel ? 1 : 0));`,
  'squad prioritize sentinel minting'
);

// Faster 4s lobby re-entry retry while bossWaitingInLobby
sq = replaceOnce(
  sq,
  `      c.freshToken &&
      now - c.enteredLobbyAt > 15000`,
  `      c.freshToken &&
      now - c.enteredLobbyAt > (bossWaitingInLobby ? 4000 : 15000)`,
  `now - c.enteredLobbyAt > (bossWaitingInLobby ? 4000 : 15000)`,
  'squad fast 4s lobby retry when bossWaitingInLobby'
);

fs.writeFileSync(sqPath, sq, 'utf8');
console.log('Patched', sqPath, 'len=', sq.length);
