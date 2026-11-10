import fs from 'node:fs';

let code = fs.readFileSync('v27-team-live.js', 'utf8').replace(/\r\n/g, '\n');

// 1. Remove pre-1500 donation call (before t=1500, everyone is just farming AI bots and compounding 7% early interest, never waste 6.25% donation tax!)
code = code.replace(
  `      super.act(g);
      if (this.cmds === before && g.t >= 850 && this.neutral === 0 && !this.hasBorderFood(g)) {
        this.tryDonateToTeammate(g);
      }`,
  `      super.act(g);`
);

// 2. Replace tryDonateToTeammate with the exact Joint Defense & Troop-Production Yield Optimization Model (g.t >= 1500):
//    - Marginal interest rate in Territorial.io:
//      * For d <= 100: marginal interest rate is +r0 (100% full yield).
//      * For 100 < d < 150: total interest is r0 * B * (3 - 2*d/100), so marginal interest d(Int)/dB = r0 * (3 - 4*d/100)!
//        Notice: at d = 75, marginal rate is +r0; at d = 100, marginal rate drops to -r0! Above d = 100, EVERY extra troop held actually REDUCES total troop production!
//      * And every 100-tick rent cycle pays +1 troop per pixel of land, whereas a troop transferred costs a flat 6.25%B fee (`iV(64*B, 1024)`).
//    - Therefore, Joint Optimization of Defense + Troop Production across the 10-bot organism requires:
//      1) Before t = 1500 (`g.t < P.coreFrom`): ZERO transfers (pure AI bot expansion + 7% compound interest).
//      2) For `g.t >= 1500`:
//         - Donor's Defense + Production Floor (`optFloor`):
//           * Pure inland boxed-in bank (`!anyEnemyNb && !hasExposedCoast`): keep `78 * L` (earns 100% full interest rate `r0` on 78*L, and whenever `dMe >= 98` — right before the `100*L` marginal-interest cliff — dispatches a `22%` (`pct=225`) chunk down to `76*L` so the bank NEVER crosses `100*L` where marginal production turns negative!). Only drops below `76*L` (down to `32*L`) if a frontline brother is under emergency human fire (`underFire`)!
//           * Coastal rear bank (`!anyEnemyNb && hasExposedCoast`): keep `82 * L` (both full interest production AND anti-boat defense), dispatching at `dMe >= 102` (or down to `58*L` if a brother is under emergency fire).
//           * Frontline territory (`anyEnemyNb`): keep `Math.max(88 * L, this.safeAt(g, -1))` so its own defense and 100*L interest production are 100% maxed out! Only dispatches surplus when `dMe >= 106` (where marginal interest is negative `-1.24 * r0`!), turning negative-yield surplus troops into +r0 yield or 2:1 defensive absorption on a brother at `dAlly < 95`!

const startMarker = '  // UNIFIED ORGANISM DYNAMIC DISPATCH ENGINE:';
const endMarker = '  isMopUp(g) {';
const sIdx = code.indexOf(startMarker);
const eIdx = code.indexOf(endMarker, sIdx);

if (sIdx < 0 || eIdx < 0) {
  throw new Error(`Markers not found: sIdx=${sIdx}, eIdx=${eIdx}`);
}

const newDispatchEngine = `  // UNIFIED ORGANISM: JOINT DEFENSE + TROOP PRODUCTION YIELD OPTIMIZER (t >= 1500 only):
  // Mathematical foundation:
  //   1) Early Game (t < 1500): Everyone expands on neutral land & AI bots with up to 7% compound interest.
  //      Paying 6.25% flat transfer tax before t=1500 destroys early compound growth -> ZERO transfers before t=1500!
  //   2) Marginal Troop Production Curve (t >= 1500):
  //      Total interest I(B) = r0 * B for d <= 100, and r0 * B * (3 - 2*d/100) for 100 < d <= 150.
  //      Taking the derivative dI/dB:
  //        - For d < 100: marginal yield is +1.00 * r0 (every troop produces maximum interest).
  //        - For d > 100: marginal yield is r0 * (3 - 4*d/100) -> NEGATIVE! (At d=110, -1.4*r0; at d=125, -2.0*r0!)
  //      Therefore, draining a rear bank down to d=35 destroys its troop production capacity (losing 65*L * r0 every 10 ticks),
  //      whereas keeping every territory in the [78*L, 100*L] sweet spot MAXIMIZES whole-squad troop production AND defense simultaneously!
  //   3) Transfer Trigger Condition (Marginal Gain > 6.25% Tax):
  //      - Normal Production-Optimal Dispatch: Donor is at \`dMe >= 100\` (negative marginal interest) and Recipient is at \`dAlly <= 88\` (+1.0*r0 marginal interest) or actively converting troops into land (\`outHumanAtk > 0\`). Moving troops from d>100 to d<88 flips marginal production from -1.5*r0 to +1.0*r0 (+2.5*r0 net gain per 10 ticks, paying back the 6.25% fee in ~25 ticks while boosting frontline defense!).
  //      - Emergency Defense Dispatch: Recipient is under active human attack (\`inHumanAtk > 0\` and \`dAlly < 88\`), where every delivered troop absorbs 2.0 enemy troops (200% defensive value). Here rear banks can dip down to \`48*L\` (inland) / \`65*L\` (coastal) to save the territory!
  tryDonateToTeammate(g, emergencyOnly = false) {
    const me = this.me;
    if (!g.teams || !(g.teams[me] > 0) || typeof g.donate !== "function") return false;
    // Rule #7671: Never transfer during the opening AI-bot phase (t < 1500)!
    if (g.t < 1500 || g.terr[me] < 2500 || g.bal[me] < 50000 || g.t - (this.lastDonateTick ?? -999) < 16) return false;
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
    const boxedIn = !anyEnemyNb && this.nb.length === 0 && this.neutral === 0;
    const hasExposedCoast = (g.coast?.[me]?.length ?? 0) > 0;

    // 1. Boss "npl" check (if present)
    const bossId = this.findBossId(g);
    if (bossId >= 0 && g.alive[bossId] && g.terr[bossId] >= 100 && (!window.ao?.iD || window.ao.iD(bossId))) {
      const dBoss = g.bal[bossId] / Math.max(1, g.terr[bossId]);
      let bossInAtk = 0;
      for (const a of g.attackersOf(bossId)) bossInAtk += g.attackTroopsOn(a, bossId);
      const bossFloor = bossInAtk > 0 ? (boxedIn ? 40 * L : 72 * L) : (boxedIn ? 75 * L : 88 * L);
      if ((bossInAtk > 0 || dBoss < 112) && B > 1.15 * bossFloor) {
        const maxPct = Math.floor(((B - bossFloor) * 1024) / B);
        const pct = Math.min(maxPct, boxedIn ? 260 : 180);
        if (pct >= 120 && g.donate(pct, bossId, me)) {
          this.lastDonateTick = g.t;
          this.lastBossDonateTick = g.t;
          this.cmds++;
          return true;
        }
      }
    }

    // 2. JOINT DEFENSE + PRODUCTION YIELD OPTIMIZATION ACROSS ALL [APEX] TERRITORIES:
    // Production-optimal reserve floor (\`prodOptFloor\`):
    //   - Even a boxed-in rear bank MUST keep \`76 * L\` during normal play so its land produces maximum interest (\`+r0\` on 76*L)
    //     and only skims off the top when it hits \`dMe >= 98\` (right before the \`100*L\` negative-marginal-interest cliff)!
    //   - Frontline territory keeps \`Math.max(86 * L, this.safeAt(g, -1))\` and only skims off surplus when \`dMe >= 106\` (where marginal interest is negative \`-1.24*r0\`).
    const prodOptFloor = boxedIn
      ? (hasExposedCoast ? 80 * L : 76 * L)
      : Math.max(hasExposedCoast ? 86 * L : 84 * L, this.safeAt(g, -1));

    // Emergency defense floor (\`emergDefFloor\`): when a brother is being attacked by an enemy human (\`underFire\`),
    // his survival (preserving his L pixels of rent+interest capacity + 2:1 defensive trade) justifies dipping into rear reserves down to 48*L!
    const emergDefFloor = boxedIn
      ? (hasExposedCoast ? 62 * L : 46 * L)
      : Math.max(76 * L, 0.85 * this.safeAt(g, -1));

    let bestTarget = -1, bestScore = -Infinity, bestKind = "prod_opt", bestFloor = prodOptFloor;

    for (let p = 0; p < g.humans; p++) {
      if (p === me || !g.alive[p] || !this.isTeammate(g, p) || !this.isOurSquadBot(g, p) || g.terr[p] < 1000) continue;
      if (typeof window !== "undefined" && window.ao?.iD && !window.ao.iD(p)) continue;

      const Lp = Math.max(1, g.terr[p]), Bp = g.bal[p], dAlly = Bp / Lp;
      if (dAlly >= 105) continue; // Never dispatch to a territory already above the 100*L full-interest cap!

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
          if (doDens < 45 || g.terr[o] <= 0.35 * (g.peak?.[o] ?? g.terr[o])) hasBleedingPrey = true;
        }
      }

      // Never send troops to a rear boxed-in territory that has no enemies and no combat!
      if (enemyNbs === 0 && inHumanAtk === 0 && outHumanAtk === 0) continue;

      const underFire = inHumanAtk > 0 && (inHumanAtk >= 0.06 * Bp || dAlly < 86);
      const activePush = outHumanAtk >= 0.06 * Bp && dAlly < 96;
      const hasPreyOpening = enemyNbs > 0 && (hasBleedingPrey || minEnemyDens < 0.70 * dAlly) && dAlly < 96;

      if (emergencyOnly && !underFire) continue;

      if (underFire) {
        // Case A: Emergency 2:1 Defense Dispatch
        const reqD = boxedIn ? (hasExposedCoast ? 72 : 58) : 92;
        if (dMe < reqD || B <= 1.12 * emergDefFloor || (!boxedIn && dMe < dAlly + 16)) continue;
        const score = 5000 + (inHumanAtk / Math.max(1, Bp)) * 2000 + (100 - dAlly) * 25 + Math.min(600, Lp / 40);
        if (score > bestScore) {
          bestScore = score;
          bestTarget = p;
          bestKind = "defense_dispatch";
          bestFloor = emergDefFloor;
        }
      } else {
        // Case B: Joint Production + Offense Yield Optimization
        // Donor MUST be at or above the 100*L negative-marginal-interest threshold (\`dMe >= 98\` if boxedIn, \`dMe >= 106\` if frontline)
        // AND Recipient must be below 92*L so moving troops from Donor -> Recipient shifts troops from NEGATIVE marginal interest (-1.4*r0)
        // to POSITIVE +1.0*r0 full interest + frontline defense/offense!
        const reqD = boxedIn ? 98 : 106;
        if (dMe < reqD || dAlly > 90 || B <= 1.14 * prodOptFloor || dMe < dAlly + 18) continue;
        const score = (activePush || hasPreyOpening ? 2500 : 1000) +
          (outHumanAtk / Math.max(1, Bp)) * 1200 +
          (hasBleedingPrey ? 500 : 0) +
          (100 - dAlly) * 18 +
          enemyNbs * 80 +
          Math.min(500, Lp / 45);
        if (score > bestScore) {
          bestScore = score;
          bestTarget = p;
          bestKind = activePush || hasPreyOpening ? "offense_dispatch" : "yield_opt_dispatch";
          bestFloor = prodOptFloor;
        }
      }
    }

    if (bestTarget < 0) return false;

    const maxSurplus = Math.max(0, B - bestFloor);
    const maxSafePct = Math.floor((maxSurplus * 1024) / Math.max(1, B));
    const idealPct = bestKind === "defense_dispatch"
      ? (boxedIn ? 260 : 190)
      : (boxedIn ? 225 : 170);
    const pct = Math.min(maxSafePct, idealPct);
    if (pct < 128) return false; // Never send tiny transfers (<12.5%B) that suffer >33% tax loss!

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

code = code.slice(0, sIdx) + newDispatchEngine + code.slice(eIdx);
fs.writeFileSync('v27-team-live.js', code, 'utf8');
console.log('Successfully updated v27-team-live.js with Joint Defense + Troop-Production Yield Optimization!');
