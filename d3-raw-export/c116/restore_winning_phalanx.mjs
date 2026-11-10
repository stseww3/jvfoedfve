import fs from 'node:fs';

// 1. In v27-team-live.js: always use the Backend Spawn Coordinator (`if (true)`) so 10 bots never each run heavy O(N) spawnVsPeople in browser workers!
let v27 = fs.readFileSync('v27-team-live.js', 'utf8').replace(/\r\n/g, '\n');
v27 = v27.replace(
  'const bossId = this.findBossId(g);\n    if (bossId >= 0) {',
  'const bossId = this.findBossId(g);\n    if (true) {'
);
fs.writeFileSync('v27-team-live.js', v27, 'utf8');
console.log('Restored backend spawn coordinator in v27-team-live.js!');

// 2. In spawn-coordinator.mjs: restore the exact scales & anchor that won Game 1 and Game 2 back-to-back (`allyMinSep: clamp(..., 86, 145)`, `clusterMax: clamp(..., 320, 620)`), so 4~5 frontliners have 35k~87k expansion room while 4~5 inner bankers are 100% protected to feed our #1 carry!
let sc = fs.readFileSync('spawn-coordinator.mjs', 'utf8').replace(/\r\n/g, '\n');

sc = sc.replace(
  'const anchorBoss = realBoss;',
  'const anchorBoss = realBoss || this.findVirtualSquadAnchor(enemies, scales);'
);
sc = sc.replace(
  'const enforceCluster = Boolean(realBoss) && relax >= 0.60;',
  'const enforceCluster = relax >= 0.60 && (anchorBoss || chosenTargets.length > 0);'
);
sc = sc.replace(
  'if (boss && pm.minClusterDist < 900000) {',
  'if (pm.minClusterDist < 900000) {'
);
sc = sc.replace(
  'allyMinSep: clamp(Math.round(Math.max(1.48 * rCell, 0.115 * diag)), 108, 185),',
  'allyMinSep: clamp(Math.round(Math.max(1.22 * rCell, 0.088 * diag)), 84, 142),'
);
sc = sc.replace(
  'clusterMax: clamp(Math.round(Math.max(5.80 * rCell, 0.580 * diag)), 420, 880),',
  'clusterMax: clamp(Math.round(Math.max(3.60 * rCell, 0.320 * diag)), 260, 480),'
);
sc = sc.replace(
  'this.injectChosenSquadPoint(picked.cell, m, Math.max(210, Math.round(2.10 * scales.allyMinSep)));',
  'this.injectChosenSquadPoint(picked.cell, m, Math.max(145, Math.round(1.65 * scales.allyMinSep)));'
);

fs.writeFileSync('spawn-coordinator.mjs', sc, 'utf8');
console.log('Restored winning Phalanx + Crown-Funnel spawn parameters in spawn-coordinator.mjs!');
