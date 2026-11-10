import fs from 'node:fs';

let code = fs.readFileSync('v27-team-live.js', 'utf8').replace(/\r\n/g, '\n');

const oldNbCheck = `      const allyNbs = this.peopleOf(g, p);
      let enemyNbs = 0, minEnemyDens = Infinity, hasBleedingPrey = false;
      for (const o of allyNbs) {
        if (o !== me && g.alive[o] && !g.isBot(o) && !this.isTeammate(g, o) && g.terr[o] > 0) {
          enemyNbs++;
          const doDens = g.bal[o] / Math.max(1, g.terr[o]);
          if (doDens < minEnemyDens) minEnemyDens = doDens;
          if (doDens < 45 || g.terr[o] <= 0.35 * (g.peak?.[o] ?? g.terr[o])) hasBleedingPrey = true;
        }
      }`;

const newNbCheck = `      const allyNbs = this.peopleOf(g, p);
      let enemyNbs = 0, botNbs = 0, minEnemyDens = Infinity, hasBleedingPrey = false;
      for (const o of allyNbs) {
        if (o !== me && g.alive[o] && !this.isTeammate(g, o) && g.terr[o] > 0) {
          const doDens = g.bal[o] / Math.max(1, g.terr[o]);
          if (!g.isBot(o)) {
            enemyNbs++;
            if (doDens < minEnemyDens) minEnemyDens = doDens;
            if (doDens < 45 || g.terr[o] <= 0.35 * (g.peak?.[o] ?? g.terr[o])) hasBleedingPrey = true;
          } else {
            botNbs++;
            if (doDens < minEnemyDens) minEnemyDens = doDens;
            if (doDens < 35) hasBleedingPrey = true;
          }
        }
      }
      if (enemyNbs === 0 && botNbs > 0) enemyNbs = botNbs;`;

if (!code.includes(oldNbCheck)) {
  console.error('Could not find oldNbCheck in v27-team-live.js!');
  process.exit(1);
}
code = code.replace(oldNbCheck, newNbCheck);
fs.writeFileSync('v27-team-live.js', code, 'utf8');
console.log('Successfully fixed peopleOf(g, p) in tryDonateToTeammate so frontline shields bordering AI bots also receive reservoir skimming!');
