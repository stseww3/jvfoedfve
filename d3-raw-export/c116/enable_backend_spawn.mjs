import fs from 'node:fs';

let v27 = fs.readFileSync('v27-team-live.js', 'utf8');

const oldChooseSpawn = `    // Check if Boss [Nope]kazerd183 is in this match
    const bossId = this.findBossId(g);
    if (bossId >= 0) {`;

const newChooseSpawn = `    // ALWAYS use the Unified Backend Spawn Coordinator (:8299) so all 5 [APEX] brothers
    // spawn on the #1 Main Continent with geodesic Voronoi spacing and NEVER stack on the same point!
    const bossId = this.findBossId(g);
    if (true) {`;

if (v27.includes(oldChooseSpawn)) {
  v27 = v27.replace(oldChooseSpawn, newChooseSpawn);
  fs.writeFileSync('v27-team-live.js', v27, 'utf8');
  console.log('Enabled Backend Spawn Coordinator for all [APEX] matches! Size:', v27.length);
} else {
  console.log('Pattern not found!');
}

// Also upgrade spawn-coordinator.mjs in c116 with S01/S02 fixes:
// - minAnchorContSize = 0.75 * maxCompSize (strictly #1 main continent)
// - allyMinSep = clamp(..., 96, 172), clusterMax = clamp(..., 280, 540)
let sc = fs.readFileSync('spawn-coordinator.mjs', 'utf8').replace(/\r\n/g, '\n');
sc = sc.replace(
  'const minAnchorContSize = Math.max(25000, Math.round(0.45 * (maxCompSize || 0)));',
  'const minAnchorContSize = Math.max(25000, Math.round(0.75 * (maxCompSize || 0)));'
);
sc = sc.replace(
  'allyMinSep: clamp(Math.round(Math.max(1.05 * rCell, 0.075 * diag)), 62, 112),',
  'allyMinSep: clamp(Math.round(Math.max(1.38 * rCell, 0.110 * diag)), 96, 172),'
);
sc = sc.replace(
  'clusterMax: clamp(Math.round(Math.max(3.0 * rCell, 0.25 * diag)), 195, 350),',
  'clusterMax: clamp(Math.round(Math.max(4.20 * rCell, 0.380 * diag)), 280, 540),'
);
fs.writeFileSync('spawn-coordinator.mjs', sc, 'utf8');
console.log('Updated c116/spawn-coordinator.mjs with S01/S02 main-continent & spacing parameters!');
