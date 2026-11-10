import fs from 'node:fs';

let sc = fs.readFileSync('spawn-coordinator.mjs', 'utf8').replace(/\r\n/g, '\n');

// 1. Add distToAnchorOrFirst(x, y) so the 10-bot squad forms a compact 2D blob around anchorBoss (radius <= 2.35 * allyMinSep) instead of a 900px 1D snake!
const oldClusterFn = `    const distToOurCluster = (x, y) => {
      let minD = 999999;
      if (anchorBoss && anchorBoss.x >= 0 && anchorBoss.y >= 0) {
        minD = Math.min(minD, Math.hypot(x - anchorBoss.x, y - anchorBoss.y));
      }
      for (const prev of chosenTargets) {
        minD = Math.min(minD, Math.hypot(x - prev.x, y - prev.y));
      }
      return minD;
    };`;

const newClusterFn = `    const distToOurCluster = (x, y) => {
      let minD = 999999;
      if (anchorBoss && anchorBoss.x >= 0 && anchorBoss.y >= 0) {
        minD = Math.min(minD, Math.hypot(x - anchorBoss.x, y - anchorBoss.y));
      }
      for (const prev of chosenTargets) {
        minD = Math.min(minD, Math.hypot(x - prev.x, y - prev.y));
      }
      return minD;
    };

    const distToClusterCore = (x, y) => {
      if (anchorBoss && anchorBoss.x >= 0 && anchorBoss.y >= 0) {
        return Math.hypot(x - anchorBoss.x, y - anchorBoss.y);
      }
      if (chosenTargets.length > 0) {
        return Math.hypot(x - chosenTargets[0].x, y - chosenTargets[0].y);
      }
      return 0;
    };`;

if (sc.includes(oldClusterFn)) {
  sc = sc.replace(oldClusterFn, newClusterFn);
}

const oldEnforce = `            } else if (enforceCluster) {
              // Keep outer wing connected to the same continent & geodesic distance from Boss
              if (distToOurCluster(x, y) > maxClusterDist) continue;
              if (realBoss && (this.dBoss[c] < 0 || this.dBoss[c] > maxClusterDist * 1.35) && relax >= 0.60) continue;
            }`;

const newEnforce = `            } else if (enforceCluster) {
              // Keep 10-bot phalanx in a compact 2D disc (not a 900px 1D snake!)
              if (distToOurCluster(x, y) > scales.allyMinSep * (2.6 - 0.8 * relax)) continue;
              if (distToClusterCore(x, y) > maxClusterDist) continue;
              if (anchorBoss && (this.dBoss[c] < 0 || this.dBoss[c] > maxClusterDist * 1.35) && relax >= 0.60) continue;
            }`;

if (sc.includes(oldEnforce)) {
  sc = sc.replace(oldEnforce, newEnforce);
  console.log('Fixed 2D disc phalanx constraint in spawn-coordinator.mjs (prevented 900px 1D snake)!')
}

// Also in evaluateCandidate: reward 2+ friendlyLinks (`if (pm.friendlyLinks >= 2) score *= 1.24; else if (pm.friendlyLinks >= 1) score *= 1.10;`) so bots form a 2D triangulated mesh instead of a 1D line!
sc = sc.replace(
  'if (pm.friendlyLinks >= 1) score *= 1.10;',
  'if (pm.friendlyLinks >= 2) score *= 1.24; else if (pm.friendlyLinks >= 1) score *= 1.10;'
);

fs.writeFileSync('spawn-coordinator.mjs', sc, 'utf8');
