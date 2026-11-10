import fs from 'node:fs';

let code = fs.readFileSync('v27-team-live.js', 'utf8').replace(/\r\n/g, '\n');

const oldLine = `if (p === me || !g.alive[p] || !this.isTeammate(g, p) || !this.isOurSquadBot(g, p) || g.terr[p] < 1000) continue;`;
const newLine = `if (p === me || !g.alive[p] || !this.isTeammate(g, p) || !this.isOurSquadBot(g, p) || g.terr[p] < 2000 || g.bal[p] < 1500) continue;`;

if (!code.includes(oldLine)) {
  console.error('Could not find oldLine!');
  process.exit(1);
}

code = code.replace(oldLine, newLine);
fs.writeFileSync('v27-team-live.js', code, 'utf8');
console.log('Successfully added g.bal[p] >= 1500 & g.terr[p] >= 2000 guard to tryDonateToTeammate!');
