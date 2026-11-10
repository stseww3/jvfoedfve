import fs from 'node:fs';

let sc = fs.readFileSync('spawn-coordinator.mjs', 'utf8').replace(/\r\n/g, '\n');

sc = sc.replace(
  'this.injectSquadSeedIntoField(pt.cell, chosenTargets.length - 1, Math.round(1.6 * scales.allyMinSep));',
  'this.injectChosenSquadPoint(pt.cell, chosenTargets.length - 1, Math.round(1.6 * scales.allyMinSep));'
);

fs.writeFileSync('spawn-coordinator.mjs', sc, 'utf8');
console.log('Fixed injectChosenSquadPoint method name in spawn-coordinator.mjs!');
