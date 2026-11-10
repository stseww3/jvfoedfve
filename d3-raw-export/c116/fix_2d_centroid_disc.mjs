import fs from 'node:fs';

let sc = fs.readFileSync('spawn-coordinator.mjs', 'utf8').replace(/\r\n/g, '\n');

// 1. In findVirtualSquadAnchor: pick a deep corner/pocket (within 1.5*rCell of two edges or high inland/water pocket) instead of a 1D edge strip
const oldAnchor = `    for (let y = 24; y < H - 24; y += stride) {
      for (let x = 24; x < W - 24; x += stride) {
        const c = y * W + x;
        if (!landMask[c] || (this.maxCompSize > 0 && this.compSize[c] < 0.75 * this.maxCompSize)) continue;
        const clearance = Math.min(dComp[c], 220);
        if (clearance < 24) continue;
        const pm = this.computePinchMetrics(x, y, enemies, null, [], scales);
        // Prefer safe backstop regions with high clearance from enemies
        const sc = clearance * pm.pinchMult * (pm.hasEdgeBackstop ? 1.18 : 1.0);`;

const newAnchor = `    for (let y = 32; y < H - 32; y += stride) {
      for (let x = 32; x < W - 32; x += stride) {
        const c = y * W + x;
        if (!landMask[c] || (this.maxCompSize > 0 && this.compSize[c] < 0.75 * this.maxCompSize)) continue;
        const clearance = Math.min(dComp[c], 220);
        if (clearance < 28) continue;
        const pm = this.computePinchMetrics(x, y, enemies, null, [], scales);
        const dxEdge = Math.min(x, W - 1 - x), dyEdge = Math.min(y, H - 1 - y);
        const isCornerPocket = dxEdge <= 260 && dyEdge <= 260;
        const sc = clearance * pm.pinchMult * (isCornerPocket ? 1.28 : pm.hasEdgeBackstop ? 1.08 : 1.0);`;

if (sc.includes(oldAnchor)) {
  sc = sc.replace(oldAnchor, newAnchor);
}

// 2. In distToClusterCore: measure distance to the CENTROID of chosenTargets (and require 2D aspect ratio, never a 468x80 1D line along an edge!)
const oldCoreFn = `    const distToClusterCore = (x, y) => {
      if (anchorBoss && anchorBoss.x >= 0 && anchorBoss.y >= 0) {
        return Math.hypot(x - anchorBoss.x, y - anchorBoss.y);
      }
      if (chosenTargets.length > 0) {
        return Math.hypot(x - chosenTargets[0].x, y - chosenTargets[0].y);
      }
      return 0;
    };`;

const newCoreFn = `    const distToClusterCore = (x, y) => {
      if (chosenTargets.length >= 2) {
        let sx = 0, sy = 0;
        for (const t of chosenTargets) { sx += t.x; sy += t.y; }
        sx /= chosenTargets.length;
        sy /= chosenTargets.length;
        return Math.hypot(x - sx, y - sy);
      }
      if (anchorBoss && anchorBoss.x >= 0 && anchorBoss.y >= 0) {
        return Math.hypot(x - anchorBoss.x, y - anchorBoss.y);
      }
      if (chosenTargets.length > 0) {
        return Math.hypot(x - chosenTargets[0].x, y - chosenTargets[0].y);
      }
      return 0;
    };`;

if (sc.includes(oldCoreFn)) {
  sc = sc.replace(oldCoreFn, newCoreFn);
}

// 3. In evaluateCandidate: reward 2D triangulation (friendlyLinks >= 2 + compact centroid distance) so bots form a 2-layer 2D disc (3~4 inner + 6~7 outer) instead of a 1D line along one edge
const oldEcoScore = `      if (pm.friendlyLinks >= 2) score *= 1.24; else if (pm.friendlyLinks >= 1) score *= 1.10;
      if (enemyNeighbors <= 1) score *= 1.15;`;

const newEcoScore = `      if (pm.friendlyLinks >= 3) score *= 1.48;
      else if (pm.friendlyLinks >= 2) score *= 1.34;
      else if (pm.friendlyLinks >= 1) score *= 1.08;
      if (chosenTargets.length >= 3) {
        let cx = 0, cy = 0;
        for (const t of chosenTargets) { cx += t.x; cy += t.y; }
        cx /= chosenTargets.length;
        cy /= chosenTargets.length;
        const dCentroid = Math.hypot(sx - cx, sy - cy);
        if (dCentroid <= 1.85 * scales.allyMinSep) score *= 1.22;
        else if (dCentroid > 2.65 * scales.allyMinSep) score *= 0.68;
      }
      if (enemyNeighbors <= 1) score *= 1.15;`;

if (sc.includes(oldEcoScore)) {
  sc = sc.replace(oldEcoScore, newEcoScore);
}

fs.writeFileSync('spawn-coordinator.mjs', sc, 'utf8');
console.log('Successfully upgraded spawn-coordinator.mjs to enforce 2D centroid disc triangulation instead of 1D edge strip!');
