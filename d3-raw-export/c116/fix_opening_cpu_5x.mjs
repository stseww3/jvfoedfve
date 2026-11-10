import fs from 'node:fs';

let code = fs.readFileSync('v27-team-live.js', 'utf8').replace(/\r\n/g, '\n');

const oldBlock = `    if (g.t < P.coreFrom) {
      this.analyze(g);`;

const newBlock = `    if (g.t % P.period !== 0) return;
    if (g.t < P.coreFrom) {
      this.analyze(g);`;

if (!code.includes(oldBlock)) {
  console.error('Could not find oldBlock in v27-team-live.js!');
  process.exit(1);
}

code = code.replace(oldBlock, newBlock);
fs.writeFileSync('v27-team-live.js', code, 'utf8');
console.log('Successfully added if (g.t % P.period !== 0) return; before g.t < P.coreFrom (cuts opening pixel-decode CPU by 80%!)');
