import fs from 'node:fs';

let code = fs.readFileSync('v27-team-live.js', 'utf8').replace(/\r\n/g, '\n');

const oldIdleBlock = `    if (this.nb.length === 0 && this.neutral === 0 && g.teams && g.teams[me] > 0 && !this.isMopUp(g)) {
      for (let p = 0; p < g.humans; p++) {
        if (p !== me && g.alive[p] && this.isTeammate(g, p) && (this.isOurSquadBot(g, p) || this.isBossNpl(g, p)) && g.terr[p] >= 1500) {
          return;
        }
      }
    }`;

const newIdleBlock = `    if (this.nb.length === 0 && this.neutral === 0 && g.teams && g.teams[me] > 0 && !this.isMopUp(g) && g.bal[me] < 126 * Math.max(1, g.terr[me])) {
      let activeFrontBrothers = 0;
      for (let p = 0; p < g.humans; p++) {
        if (p !== me && g.alive[p] && this.isTeammate(g, p) && (this.isOurSquadBot(g, p) || this.isBossNpl(g, p)) && g.terr[p] >= 1500) {
          const nbs = this.peopleOf(g, p);
          if (nbs.some((o) => g.alive[o] && !g.isBot(o) && !this.isTeammate(g, o))) activeFrontBrothers++;
        }
      }
      if (activeFrontBrothers >= 2) return;
    }`;

if (code.includes(oldIdleBlock)) {
  code = code.replace(oldIdleBlock, newIdleBlock);
  console.log('Fixed Policy.idleBoats: allow sea breakout when dMe >= 126 or when <2 frontline brothers remain!');
}

// Also in tryDonateToTeammate: if boxedIn and dMe >= 105, and NO frontline brother has enemyNbs > 0 (or their ao.iD is full), allow donating to a coastal brother (like talon5 or kaito9 who has dAlly < 85 and exposed coast) so that coastal brother can launch boats or expand!
const oldNoEnemyCont = `      // Never send troops to a rear boxed-in territory that has no enemies and no combat!
      if (enemyNbs === 0 && inHumanAtk === 0 && outHumanAtk === 0) continue;`;

const newNoEnemyCont = `      const allyHasCoast = (g.coast?.[p]?.length ?? 0) > 0;
      if (enemyNbs === 0 && inHumanAtk === 0 && outHumanAtk === 0 && (!boxedIn || !allyHasCoast || dMe < 110 || dAlly > 82)) continue;`;

if (code.includes(oldNoEnemyCont)) {
  code = code.replace(oldNoEnemyCont, newNoEnemyCont);
  console.log('Allowed boxed-in inland reservoirs at dMe>=110 to feed low-density coastal brothers (dAlly<=82) for sea breakout!');
}

fs.writeFileSync('v27-team-live.js', code, 'utf8');
