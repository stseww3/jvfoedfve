import fs from 'node:fs';

// 1. In spawn-coordinator.mjs: when realBoss is null (no human Boss in match), disable Virtual Squad Anchor and cluster leash so all 10 [APEX] bots spread across the entire map to maximize Voronoi territory!
let sc = fs.readFileSync('spawn-coordinator.mjs', 'utf8').replace(/\r\n/g, '\n');

sc = sc.replace(
  'const anchorBoss = realBoss || this.findVirtualSquadAnchor(enemies, scales);',
  'const anchorBoss = realBoss;'
);

sc = sc.replace(
  'const enforceCluster = relax >= 0.60 && (anchorBoss || chosenTargets.length > 0);',
  'const enforceCluster = Boolean(realBoss) && relax >= 0.60;'
);

// Also in evaluateCandidate: only apply minClusterDist chain leash when boss (realBoss) is present!
sc = sc.replace(
  'if (pm.minClusterDist < 900000) {',
  'if (boss && pm.minClusterDist < 900000) {'
);

fs.writeFileSync('spawn-coordinator.mjs', sc, 'utf8');
console.log('Fixed spawn-coordinator.mjs: disabled Virtual Squad Anchor & cluster leash when realBoss is absent!');

// 2. In v27-team-live.js: when bossId < 0, use pure v27 distributed Voronoi spawnVsPeople(gClean) with 10 slots so each of the 10 [APEX] bots claims the biggest open territory pocket on the map!
let v27 = fs.readFileSync('v27-team-live.js', 'utf8').replace(/\r\n/g, '\n');

v27 = v27.replace(
  'const bossId = this.findBossId(g);\n    if (true) {',
  'const bossId = this.findBossId(g);\n    if (bossId >= 0) {'
);

// Also in autonomous Voronoi spawn (when bossId < 0), set minSep for 10 bots to Math.max(95, Math.min(175, 0.14 * Math.hypot(W, H))) and sample 36 candidates so all 10 bots get prime Voronoi pockets!
v27 = v27.replace(
  'const minSep = Math.max(135, Math.min(240, 0.28 * Math.hypot(W, H)));',
  'const minSep = Math.max(96, Math.min(175, 0.14 * Math.hypot(W, H)));'
);
v27 = v27.replace(
  'let rawCands = this.spawnVsPeople ? this.spawnVsPeople(gClean, 24) : [];',
  'let rawCands = this.spawnVsPeople ? this.spawnVsPeople(gClean, 36) : [];'
);

fs.writeFileSync('v27-team-live.js', v27, 'utf8');
console.log('Fixed v27-team-live.js: restored pure v27 spawnVsPeople Voronoi when Boss is absent!');
