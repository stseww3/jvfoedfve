import fs from 'node:fs';

let code = fs.readFileSync('v27-team-live.js', 'utf8').replace(/\r\n/g, '\n');

// 1. Add ghost/quit squad bot filtering + Crown-sniping priority in tryDonateToTeammate
const oldLoopStart = `    let maxSquadTerr = L;
    for (let p = 0; p < g.humans; p++) {
      if (g.alive[p] && this.isTeammate(g, p) && this.isOurSquadBot(g, p) && g.terr[p] > maxSquadTerr) {
        maxSquadTerr = g.terr[p];
      }
    }
    let bestTarget = -1, bestScore = -Infinity, bestKind = "prod_opt", bestFloor = prodOptFloor;

    for (let p = 0; p < g.humans; p++) {
      if (p === me || !g.alive[p] || !this.isTeammate(g, p) || !this.isOurSquadBot(g, p) || g.terr[p] < 2000 || g.bal[p] < 1500) continue;
      if (typeof window !== "undefined" && window.ao?.iD && !window.ao.iD(p)) continue;`;

const newLoopStart = `    let maxSquadTerr = 0, topSquadId = -1, maxRandomTeamTerr = 0;
    for (let p = 0; p < g.humans; p++) {
      if (!g.alive[p] || !this.isTeammate(g, p)) continue;
      if (typeof window !== "undefined" && window.__quitPlayers && window.__quitPlayers.has(p)) continue;
      if (this.isOurSquadBot(g, p) || this.isBossNpl(g, p)) {
        if (g.terr[p] > maxSquadTerr) {
          maxSquadTerr = g.terr[p];
          topSquadId = p;
        }
      } else if (!g.isBot(p) && g.terr[p] > maxRandomTeamTerr) {
        maxRandomTeamTerr = g.terr[p];
      }
    }
    let bestTarget = -1, bestScore = -Infinity, bestKind = "prod_opt", bestFloor = prodOptFloor;

    for (let p = 0; p < g.humans; p++) {
      if (p === me || !g.alive[p] || !this.isTeammate(g, p) || !this.isOurSquadBot(g, p) || g.terr[p] < 2000 || g.bal[p] < 1500) continue;
      if (typeof window !== "undefined" && window.__quitPlayers && window.__quitPlayers.has(p)) continue;
      if (typeof window !== "undefined" && window.ao?.iD && !window.ao.iD(p)) continue;`;

if (!code.includes(oldLoopStart)) {
  console.error('Could not find oldLoopStart!');
  process.exit(1);
}
code = code.replace(oldLoopStart, newLoopStart);

// 2. Boost score for topSquadId when contesting #1 Crown against random teammates, and never feed completely idle non-coastal boxed-in bots
const oldCaseB = `      const allyHasCoast = (g.coast?.[p]?.length ?? 0) > 0;
      if (enemyNbs === 0 && inHumanAtk === 0 && outHumanAtk === 0 && (!boxedIn || !allyHasCoast || dMe < 110 || dAlly > 82)) continue;`;

const newCaseB = `      const allyHasCoast = (g.coast?.[p]?.length ?? 0) > 0;
      const isCrownContender = p === topSquadId && enemyNbs > 0 && maxRandomTeamTerr >= 0.70 * maxSquadTerr;
      if (enemyNbs === 0 && inHumanAtk === 0 && outHumanAtk === 0 && (!boxedIn || !allyHasCoast || dMe < 118 || dAlly > 82 || (g.boatCount && g.boatCount[p] === 0 && g.t > 7500))) continue;`;

if (!code.includes(oldCaseB)) {
  console.error('Could not find oldCaseB!');
  process.exit(1);
}
code = code.replace(oldCaseB, newCaseB);

const oldScoreB = `        const score = (activePush || hasPreyOpening ? 2500 : 1000) +
          (outHumanAtk / Math.max(1, Bp)) * 1200 +
          (hasBleedingPrey ? 500 : 0) +
          (100 - dAlly) * 18 +
          enemyNbs * 80 +
          Math.min(2200, Lp / 18);`;

const newScoreB = `        const score = (activePush || hasPreyOpening ? 2500 : 1000) +
          (isCrownContender ? 1800 : 0) +
          (outHumanAtk / Math.max(1, Bp)) * 1200 +
          (hasBleedingPrey ? 500 : 0) +
          (100 - dAlly) * 18 +
          enemyNbs * 80 +
          Math.min(3500, Lp / 14);`;

if (!code.includes(oldScoreB)) {
  console.error('Could not find oldScoreB!');
  process.exit(1);
}
code = code.replace(oldScoreB, newScoreB);

fs.writeFileSync('v27-team-live.js', code, 'utf8');
console.log('Successfully applied window.__quitPlayers guard + Crown-Contender priority to v27-team-live.js!');
