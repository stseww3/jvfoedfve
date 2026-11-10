import fs from 'node:fs';

let code = fs.readFileSync('v27-team-live.js', 'utf8').replace(/\r\n/g, '\n');

const oldLoop = `    for (let p = 0; p < g.humans; p++) {
      if (p === me || !g.alive[p] || !this.isTeammate(g, p) || !this.isOurSquadBot(g, p) || g.terr[p] < 2000 || g.bal[p] < 1500) continue;
      if (typeof window !== "undefined" && window.__quitPlayers && window.__quitPlayers.has(p)) continue;
      if (typeof window !== "undefined" && window.ao?.iD && !window.ao.iD(p)) continue;`;

const newLoop = `    for (let p = 0; p < g.humans; p++) {
      if (p === me || !g.alive[p] || !this.isTeammate(g, p) || (!this.isOurSquadBot(g, p) && !this.isBossNpl(g, p)) || g.terr[p] < 2000 || g.bal[p] < 1500) continue;
      if (typeof window !== "undefined" && window.__quitPlayers && window.__quitPlayers.has(p)) continue;`;

if (!code.includes(oldLoop)) {
  console.error('Could not find oldLoop in v27-team-live.js!');
  process.exit(1);
}
code = code.replace(oldLoop, newLoop);
fs.writeFileSync('v27-team-live.js', code, 'utf8');
console.log('Successfully removed broken window.ao.iD(p) check that was blocking all donations!');
