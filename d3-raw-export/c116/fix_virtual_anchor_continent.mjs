import fs from 'node:fs';

let sc = fs.readFileSync('spawn-coordinator.mjs', 'utf8').replace(/\r\n/g, '\n');

// 1. In findVirtualSquadAnchor: ONLY pick a pixel on the #1 largest continent (`this.compSize[c] === this.maxCompSize`)!
const oldAnchorLoop = `      for (let x = 24; x < W - 24; x += stride) {
        const c = y * W + x;
        if (!landMask[c]) continue;`;

const newAnchorLoop = `      for (let x = 24; x < W - 24; x += stride) {
        const c = y * W + x;
        if (!landMask[c] || (this.maxCompSize > 0 && this.compSize[c] < 0.75 * this.maxCompSize)) continue;`;

if (sc.includes(oldAnchorLoop)) {
  sc = sc.replace(oldAnchorLoop, newAnchorLoop);
  console.log('Fixed findVirtualSquadAnchor: only anchor on the #1 largest continent!');
}

// 2. In pickNextTarget: when realBoss is null, NEVER restrict to bossCompId unless bossContinentSize >= 0.65 * this.maxCompSize, and NEVER allow any seed on a small island (< minViableCompSize)!
const oldCompCheck = `            // Strictly keep ALL squad bots on Boss's continent whenever Boss is on a viable continent!
            if (bossCompId >= 0 && bossContinentSize >= 15000 && relax >= 0.55) {
              if (this.compId[c] !== bossCompId) continue;
            } else if (relax >= 0.60 && this.compSize[c] < minViableCompSize) {
              continue;
            }`;

const newCompCheck = `            // Strictly keep ALL squad bots on the main continent (never on small islands)!
            if (this.compSize[c] < minViableCompSize) continue;
            if (realBoss && bossCompId >= 0 && bossContinentSize >= 15000 && relax >= 0.55) {
              if (this.compId[c] !== bossCompId) continue;
            }`;

if (sc.includes(oldCompCheck)) {
  sc = sc.replace(oldCompCheck, newCompCheck);
  console.log('Fixed pickNextTarget: strictly enforce minViableCompSize on ALL relax passes!');
}

// 3. Also in pickNextTarget: only enforce dBoss geodesic leash when realBoss is present (`if (realBoss && (this.dBoss[c] < 0 ...))`)!
sc = sc.replace(
  'if (anchorBoss && (this.dBoss[c] < 0 || this.dBoss[c] > maxClusterDist * 1.35) && relax >= 0.60) continue;',
  'if (realBoss && (this.dBoss[c] < 0 || this.dBoss[c] > maxClusterDist * 1.35) && relax >= 0.60) continue;'
);

fs.writeFileSync('spawn-coordinator.mjs', sc, 'utf8');
