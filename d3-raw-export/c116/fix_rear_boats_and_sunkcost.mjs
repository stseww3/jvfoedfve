import fs from 'node:fs';

let code = fs.readFileSync('v27-team-live.js', 'utf8').replace(/\r\n/g, '\n');

// 1. In idleBoats(g): if we are boxedIn (`this.nb.length === 0 && this.neutral === 0`) and we have living frontline [APEX] brothers (or Boss), NEVER launch idle boats! Keep 100% of troops for Joint Yield/Defense Dispatch!
const oldIdleBoats = `  idleBoats(g) {
    const P = this.p, me = this.me;`;

const newIdleBoats = `  idleBoats(g) {
    const P = this.p, me = this.me;
    if (this.nb.length === 0 && this.neutral === 0 && g.teams && g.teams[me] > 0) {
      for (let p = 0; p < g.humans; p++) {
        if (p !== me && g.alive[p] && this.isTeammate(g, p) && (this.isOurSquadBot(g, p) || this.isBossNpl(g, p)) && g.terr[p] >= 1500) {
          return;
        }
      }
    }`;

if (code.includes(oldIdleBoats)) {
  code = code.replace(oldIdleBoats, newIdleBoats);
  console.log('Fixed idleBoats: boxed-in rear reservoirs NEVER waste troops on boats while any frontline brother is alive!');
}

// 2. In tryDonateToTeammate:
//    - For `defense_dispatch`: DO NOT dispatch into a doomed pocket that is outnumbered > 1.8x by incoming enemy troops (`inHumanAtk > 1.8 * Bp` or `Lp < 0.22 * maxSquadTerr`), Instead, channel those troops into our STRONGEST active frontline brothers (`Lp >= 0.45 * maxSquadTerr`) so they counter-push and crush the enemy!
const oldLoopStart = `    let bestTarget = -1, bestScore = -Infinity, bestKind = "prod_opt", bestFloor = prodOptFloor;

    for (let p = 0; p < g.humans; p++) {`;

const newLoopStart = `    let maxSquadTerr = L;
    for (let p = 0; p < g.humans; p++) {
      if (g.alive[p] && this.isTeammate(g, p) && this.isOurSquadBot(g, p) && g.terr[p] > maxSquadTerr) {
        maxSquadTerr = g.terr[p];
      }
    }
    let bestTarget = -1, bestScore = -Infinity, bestKind = "prod_opt", bestFloor = prodOptFloor;

    for (let p = 0; p < g.humans; p++) {`;

if (code.includes(oldLoopStart)) {
  code = code.replace(oldLoopStart, newLoopStart);
}

const oldUnderFire = `      const underFire = inHumanAtk > 0 && (inHumanAtk >= 0.06 * Bp || dAlly < 86);`;
const newUnderFire = `      const isDoomedPocket = inHumanAtk > 1.65 * Bp || (g.t >= 4500 && Lp < 0.22 * maxSquadTerr && inHumanAtk > 0.45 * Bp);
      if (isDoomedPocket) continue;
      const underFire = inHumanAtk > 0 && (inHumanAtk >= 0.06 * Bp || dAlly < 88);`;

if (code.includes(oldUnderFire)) {
  code = code.replace(oldUnderFire, newUnderFire);
  console.log('Added anti-sunk-cost filter (`isDoomedPocket`) so rear reservoirs never pour millions into a collapsing pocket!');
}

// Also weight target territory `Lp` much more strongly in both defense_dispatch and offense_dispatch so our main frontline pillars (like 55k kaito9) get priority ammo!
code = code.replace(
  'const score = 5000 + (inHumanAtk / Math.max(1, Bp)) * 2000 + (100 - dAlly) * 25 + Math.min(600, Lp / 40);',
  'const score = 5000 + (inHumanAtk / Math.max(1, Bp)) * 1200 + (105 - dAlly) * 20 + Math.min(2200, Lp / 18);'
);
code = code.replace(
  'Math.min(500, Lp / 45);',
  'Math.min(2200, Lp / 18);'
);

fs.writeFileSync('v27-team-live.js', code, 'utf8');
