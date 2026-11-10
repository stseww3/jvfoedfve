import fs from 'node:fs';

let code = fs.readFileSync('v27-team-live.js', 'utf8').replace(/\r\n/g, '\n');

// Replace tryDonateToTeammate with the Unified Organism Dynamic Dispatch Engine:
// - Treats all 10 [APEX] territories as ONE organism with a shared troop pool.
// - Priority 1 (Emergency Defense Dispatch): Any brother under enemy human attack (`inHumanAtk > 0`) whose density drops below `92` or whose incoming wave >= 10% B immediately receives rapid-fire reinforcement from any brother with surplus (`dMe >= 82` on frontline when unattacked, `dMe >= 32` when boxed-in).
// - Priority 2 (Active Offense / Opportunity Dispatch): Instead of feeding a static giant who has no cheap targets, find the brother `p` who is CURRENTLY pushing an enemy (`outAtk > 0`) or borders the thinnest/most vulnerable enemy (`minEnemyD < 75` or `nearCollapse`) and needs ammo (`dAlly < 118`), and dispatch troops to that active front!
// - Priority 3 (Density Equalization / Cap Transfer): Any brother sitting at `dMe >= 108` with no immediate cheap attack of his own (`cmds === cmdsBefore`) or `boxedIn` (`dMe >= 35`) transfers troops to the frontline brother with the lowest density (`dAlly < 112`) or highest combat activity (`outAtk + inAtk`).

const startMarker = '  // General Teammate Donation (prioritizing Boss npl first, then frontline squad teammates)\n  tryDonateToTeammate(g) {';
const endMarker = '  isMopUp(g) {';

const sIdx = code.indexOf(startMarker);
const eIdx = code.indexOf(endMarker, sIdx);

if (sIdx < 0 || eIdx < 0) {
  throw new Error(`Markers not found: sIdx=${sIdx}, eIdx=${eIdx}`);
}

const newDonateFn = `  // UNIFIED ORGANISM DYNAMIC DISPATCH ENGINE:
  // Mid-to-late game treats all 10 [APEX] territories as ONE single organism:
  //   1) Rapid Defense Dispatch: wherever an enemy attacks ANY brother, all unattacked brothers immediately pump troops to that front.
  //   2) Opportunity Offense Dispatch: instead of blindly feeding one static giant, pump troops to whichever frontline brother is actively attacking (\`outAtk > 0\`) or borders the weakest/bleeding enemy!
  //   3) Frontline Equalization: rear boxed-in banks (\`dMe >= 32\`) and high-density brothers (\`dMe >= 98\`) continuously equalize frontline density across all active fronts.
  tryDonateToTeammate(g, emergencyOnly = false) {
    const me = this.me;
    if (!g.teams || !(g.teams[me] > 0) || typeof g.donate !== "function") return false;
    if (g.t < 400 || g.terr[me] < 2000 || g.bal[me] < 35000 || g.t - (this.lastDonateTick ?? -999) < 14) return false;
    const B = g.bal[me], L = Math.max(1, g.terr[me]), dMe = B / L;

    let myHumanInAtk = 0, myHumanOutAtk = 0;
    for (const a of g.attackersOf(me)) {
      if (!g.isBot(a) && !this.isTeammate(g, a)) myHumanInAtk += g.attackTroopsOn(a, me);
    }
    const sbMe = g.slotBase(me);
    for (let i = 0; i < g.atkCount[me]; i++) {
      const tgt = g.atkTarget[sbMe + i];
      if (tgt >= 0 && tgt < g.humans && !g.isBot(tgt) && !this.isTeammate(g, tgt)) myHumanOutAtk += g.atkTroops[sbMe + i];
    }
    // Never donate while we ourselves are under human attack or actively pushing a major offensive wave!
    if (myHumanInAtk > 0 || myHumanOutAtk > 0.08 * B) return false;

    const enemyHumanNbs = this.nb.filter((p) => g.alive[p] && this.person(g, p));
    let anyEnemyNb = enemyHumanNbs.length > 0;
    if (!anyEnemyNb && this.cnt) {
      for (let p = 0; p < g.humans; p++) {
        if (p !== me && g.alive[p] && !this.isTeammate(g, p) && (this.cnt[p] ?? 0) > 0) {
          anyEnemyNb = true;
          break;
        }
      }
    }
    const boxedIn = !anyEnemyNb && this.nb.length === 0 && (this.neutral === 0 || (g.t >= 850 && this.neutral <= 8 && dMe >= 55));
    const hasExposedCoast = (g.coast?.[me]?.length ?? 0) > 0;
    const coastGuardFloor = boxedIn ? (hasExposedCoast ? 28 * L : 16 * L) : (hasExposedCoast && g.t >= 1100 ? 64 * L : 52 * L);
    const safeFloor = boxedIn ? coastGuardFloor : Math.max(coastGuardFloor, enemyHumanNbs.length > 0 ? 0.82 * this.safeAt(g, -1) : 0);
    if (B <= 1.06 * safeFloor) return false;

    const maxSurplus = Math.max(0, B - 1.04 * safeFloor);
    const maxSafePct = Math.floor((maxSurplus * 1024) / Math.max(1, B));
    if (maxSafePct < 96) return false;

    // 1. Boss "npl" check (if present)
    const bossId = this.findBossId(g);
    if (bossId >= 0 && g.alive[bossId] && g.terr[bossId] >= 100 && (!window.ao?.iD || window.ao.iD(bossId))) {
      const dBoss = g.bal[bossId] / Math.max(1, g.terr[bossId]);
      let bossInAtk = 0, bossOutAtk = 0;
      for (const a of g.attackersOf(bossId)) bossInAtk += g.attackTroopsOn(a, bossId);
      const sbB = g.slotBase(bossId);
      for (let i = 0; i < g.atkCount[bossId]; i++) {
        if (g.atkTarget[sbB + i] !== 512) bossOutAtk += g.atkTroops[sbB + i];
      }
      if ((bossInAtk > 0 || bossOutAtk > 0.04 * g.bal[bossId] || dBoss < 118) && dMe >= (boxedIn ? 24 : 78)) {
        const pct = Math.min(maxSafePct, boxedIn ? 320 : 180);
        if (pct >= 96 && g.donate(pct, bossId, me)) {
          this.lastDonateTick = g.t;
          this.lastBossDonateTick = g.t;
          this.cmds++;
          if (typeof window !== "undefined" && window.__hlLog) {
            window.__hlLog(\`[HL-DONATE] t=\${g.t} boss dispatch pct=\${pct}/1024 -> boss=\${bossId}(\${g.names?.[bossId] || "npl"}) myBal=\${B} dMe=\${Math.round(dMe)}\`);
          }
          return true;
        }
      }
    }

    // 2. RAPID DEFENSE & ACTIVE OFFENSE DISPATCH ACROSS ALL SQUAD BROTHERS:
    // Scan every living [APEX] brother and score their immediate tactical need for troops:
    //   - Under enemy human attack (\`inHumanAtk > 0\`): highest urgency! Any unattacked brother with \`dMe >= 80\` (or boxedIn \`dMe >= 30\`) dispatches immediately!
    //   - Actively pushing an enemy (\`outHumanAtk > 0\`): high urgency! Feed the brother who is actively converting troops into enemy territory!
    //   - Bordering a thin/bleeding enemy (\`minEnemyDens < 55\`): feed the brother who has the best offensive opening right now!
    let bestTarget = -1, bestUrgency = -Infinity, bestKind = "equalize";
    for (let p = 0; p < g.humans; p++) {
      if (p === me || !g.alive[p] || !this.isTeammate(g, p) || !this.isOurSquadBot(g, p) || g.terr[p] < 800) continue;
      if (typeof window !== "undefined" && window.ao?.iD && !window.ao.iD(p)) continue;

      const Lp = Math.max(1, g.terr[p]), Bp = g.bal[p], dAlly = Bp / Lp;
      if (dAlly >= 136) continue;

      let inHumanAtk = 0, outHumanAtk = 0;
      for (const a of g.attackersOf(p)) {
        if (!g.isBot(a) && !this.isTeammate(g, a)) inHumanAtk += g.attackTroopsOn(a, p);
      }
      const sbP = g.slotBase(p);
      for (let i = 0; i < g.atkCount[p]; i++) {
        const tgt = g.atkTarget[sbP + i];
        if (tgt >= 0 && tgt < g.humans && !g.isBot(tgt) && !this.isTeammate(g, tgt)) {
          outHumanAtk += g.atkTroops[sbP + i];
        }
      }

      const allyNbs = this.peopleOf(g, p);
      let enemyNbs = 0, minEnemyDens = Infinity, hasBleedingPrey = false;
      for (const o of allyNbs) {
        if (o !== me && g.alive[o] && !g.isBot(o) && !this.isTeammate(g, o) && g.terr[o] > 0) {
          enemyNbs++;
          const doDens = g.bal[o] / Math.max(1, g.terr[o]);
          if (doDens < minEnemyDens) minEnemyDens = doDens;
          if (doDens < 42 || g.terr[o] <= 0.35 * (g.peak?.[o] ?? g.terr[o])) hasBleedingPrey = true;
        }
      }

      // A boxed-in brother in the rear never needs troops dispatched TO him!
      if (enemyNbs === 0 && inHumanAtk === 0 && outHumanAtk === 0 && g.t >= 1600) continue;

      const underFire = inHumanAtk > 0 && (inHumanAtk >= 0.05 * Bp || dAlly < 92);
      const activePush = outHumanAtk >= 0.06 * Bp && dAlly < 115;
      const hasPreyOpening = enemyNbs > 0 && (hasBleedingPrey || minEnemyDens < 0.72 * dAlly) && dAlly < 112;

      if (emergencyOnly && !underFire) continue;

      // Determine minimum donor density required for this dispatch type:
      const reqDonorDens = underFire
        ? (boxedIn ? 28 : 80)
        : (activePush || hasPreyOpening)
          ? (boxedIn ? 32 : 98)
          : (boxedIn ? 38 : 114);

      if (dMe < reqDonorDens || (!boxedIn && dMe < dAlly + 14)) continue;

      let urgency = 0;
      let kind = "equalize";
      if (underFire) {
        kind = "defense_dispatch";
        urgency = 5000 + (inHumanAtk / Math.max(1, Bp)) * 2000 + (110 - dAlly) * 22 + Math.min(600, Lp / 40);
      } else if (activePush || hasPreyOpening) {
        kind = "offense_dispatch";
        urgency = 2500 + (outHumanAtk / Math.max(1, Bp)) * 1200 + (hasBleedingPrey ? 600 : 0) + (120 - dAlly) * 14 + Math.min(500, Lp / 45);
      } else {
        kind = "front_equalize";
        urgency = 800 + (125 - dAlly) * 12 + enemyNbs * 90 + Math.min(400, Lp / 50);
      }

      if (urgency > bestUrgency) {
        bestUrgency = urgency;
        bestTarget = p;
        bestKind = kind;
      }
    }

    if (bestTarget < 0) return false;

    const targetPct = bestKind === "defense_dispatch"
      ? (boxedIn ? 300 : 200)
      : bestKind === "offense_dispatch"
        ? (boxedIn ? 260 : 175)
        : (boxedIn ? 220 : 150);
    const pct = Math.min(maxSafePct, targetPct);
    if (pct < 96) return false;

    if (g.donate(pct, bestTarget, me)) {
      this.lastDonateTick = g.t;
      this.cmds++;
      if (typeof window !== "undefined" && window.__hlLog) {
        const dTarget = Math.round(g.bal[bestTarget] / Math.max(1, g.terr[bestTarget]));
        window.__hlLog(\`[HL-DISPATCH] t=\${g.t} \${bestKind} pct=\${pct}/1024 -> ally=\${bestTarget}(\${g.names?.[bestTarget] || ""}) boxedIn=\${boxedIn} myBal=\${B} dMe=\${Math.round(dMe)} dAlly=\${dTarget}\`);
      }
      return true;
    }
    return false;
  }

`;

code = code.slice(0, sIdx) + newDonateFn + code.slice(eIdx);

// Also in act(g): BEFORE buyLand(g), run `if (g.t >= 1500 && this.tryDonateToTeammate(g, true) && g.online) return;`
// so emergency defense dispatch (`underFire`) happens IMMEDIATELY before a brother spends his tick on a minor land action!
const oldActBlock = `    const cmdsBefore = this.cmds;
    if (P.flashLoanMode > 0 && this.tryStartFlashLoan(g)) return;`;

const newActBlock = `    const cmdsBefore = this.cmds;
    if (g.t >= 1500 && this.tryDonateToTeammate(g, true) && g.online) return;
    if (P.flashLoanMode > 0 && this.tryStartFlashLoan(g)) return;`;

if (code.includes(oldActBlock)) {
  code = code.replace(oldActBlock, newActBlock);
  console.log('Wired pre-buyLand Emergency Defense Dispatch + post-buyLand Offense/Equalization Dispatch in act(g)!');
}

fs.writeFileSync('v27-team-live.js', code, 'utf8');
console.log('Successfully installed Unified Organism Dynamic Dispatch Engine in v27-team-live.js!');
