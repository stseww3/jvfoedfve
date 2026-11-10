import fs from 'node:fs';

let code = fs.readFileSync('v27-team-live.js', 'utf8').replace(/\r\n/g, '\n');

const targetStr = `  idleBoats(g) {
    const P = this.p, me = this.me;
    if (this.isMopUp(g)) {`;

const replaceStr = `  idleBoats(g) {
    const P = this.p, me = this.me;
    if (this.nb.length === 0 && this.neutral === 0 && g.teams && g.teams[me] > 0 && !this.isMopUp(g)) {
      for (let p = 0; p < g.humans; p++) {
        if (p !== me && g.alive[p] && this.isTeammate(g, p) && (this.isOurSquadBot(g, p) || this.isBossNpl(g, p)) && g.terr[p] >= 1500) {
          return;
        }
      }
    }
    if (this.isMopUp(g)) {`;

if (code.includes(targetStr)) {
  code = code.replace(targetStr, replaceStr);
  console.log('Fixed Policy.idleBoats(g) in v27-team-live.js (boxed-in reservoirs never launch boats while any frontline brother is alive)!');
} else {
  throw new Error('Policy.idleBoats not found!');
}

fs.writeFileSync('v27-team-live.js', code, 'utf8');
