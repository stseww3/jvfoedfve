import fs from 'node:fs';

let code = fs.readFileSync('v27-team-live.js', 'utf8').replace(/\r\n/g, '\n');

// Check where candidate loop checks alive(p) in tryDonateToTeammate
const idx = code.indexOf('if (!g.alive(p) || g.sameTeam && !g.sameTeam(id, p)) continue;');
if (idx === -1) {
  console.error('Could not find candidate loop!');
  process.exit(1);
}
console.log(code.slice(idx - 100, idx + 600));
