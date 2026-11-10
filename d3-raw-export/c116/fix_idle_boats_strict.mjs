import fs from 'node:fs';

let code = fs.readFileSync('v27-team-live.js', 'utf8').replace(/\r\n/g, '\n');

const oldIdle = `    if (this.nb.length === 0 && this.neutral === 0 && g.teams && g.teams[me] > 0 && !this.isMopUp(g) && g.bal[me] < 126 * Math.max(1, g.terr[me])) {
      let activeFrontBrothers = 0;
      for (let p = 0; p < g.humans; p++) {
        if (p !== me && g.alive[p] && this.isTeammate(g, p) && (this.isOurSquadBot(g, p) || this.isBossNpl(g, p)) && g.terr[p] >= 1500) {
          const nbs = this.peopleOf(g, p);
          if (nbs.some((o) => g.alive[o] && !g.isBot(o) && !this.isTeammate(g, o))) activeFrontBrothers++;
        }
      }
      if (activeFrontBrothers >= 2) return;
    }`;

const newIdle = `    if (this.nb.length === 0 && this.neutral === 0 && g.teams && g.teams[me] > 0 && !this.isMopUp(g) && g.bal[me] < 138 * Math.max(1, g.terr[me])) {
      let aliveSquadBrothers = 0;
      for (let p = 0; p < g.humans; p++) {
        if (p !== me && g.alive[p] && this.isTeammate(g, p) && (this.isOurSquadBot(g, p) || this.isBossNpl(g, p)) && g.terr[p] >= 2000 && g.bal[p] >= 1500) {
          if (!(typeof window !== "undefined" && window.__quitPlayers && window.__quitPlayers.has(p))) aliveSquadBrothers++;
        }
      }
      if (aliveSquadBrothers >= 1) return;
    }`;

if (!code.includes(oldIdle)) {
  console.error('Could not find oldIdle!');
  process.exit(1);
}

code = code.replace(oldIdle, newIdle);
fs.writeFileSync('v27-team-live.js', code, 'utf8');
console.log('Successfully locked idleBoats for boxed-in reservoirs whenever >= 1 squad brother is alive!');
