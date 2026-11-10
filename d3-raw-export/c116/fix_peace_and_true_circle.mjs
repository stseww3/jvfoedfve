import fs from 'node:fs';

// 1. Disable tryPeaceVote in v27-team-live.js (ONLY follow if Boss npl explicitly initiated peace!)
let v27 = fs.readFileSync('v27-team-live.js', 'utf8').replace(/\r\n/g, '\n');

const oldPeace = `  tryPeaceVote(g) {
    if (typeof window === "undefined" || !window.ax || !window.dictionary || g.t < 1610) return;`;

const newPeace = `  tryPeaceVote(g) {
    if (this.findBossId(g) < 0) return; // Never initiate or vote peace in autonomous squad mode — always conquer 100% of the map!
    if (typeof window === "undefined" || !window.ax || !window.dictionary || g.t < 1610) return;`;

if (v27.includes(oldPeace)) {
  v27 = v27.replace(oldPeace, newPeace);
  fs.writeFileSync('v27-team-live.js', v27, 'utf8');
  console.log('Disabled autonomous peace vote in v27-team-live.js!');
}

// 2. Replace greedy Voronoi scattering with a True Concentric Circle Formation (3 Inner Core + 7 Outer Shield Ring) in spawn-coordinator.mjs!
let sc = fs.readFileSync('spawn-coordinator.mjs', 'utf8').replace(/\r\n/g, '\n');

const oldSolveStart = `    for (let m = 0; m < K; m++) {
      const wantRole =
        m < targetFlankCount
          ? 'FLANK_GUARD'
          : m >= K - targetSpoilerCount
            ? 'SPOILER_BANK'
            : 'ECO_BANK';
      let picked = pickNextTarget(wantRole);`;

const newSolveStart = `    // When Boss is NOT present (!realBoss) and K >= 6, deploy a TRUE CONCENTRIC CIRCLE FORMATION:
    //   - 1 Anchor Center (Cx, Cy) deep inside the safest mainland basin (clearance >= 140px from water/edges & enemies)
    //   - 3 Inner Core Reservoirs on inner radius r1 (~44px, 120 deg apart) -> guaranteed 100% boxed-in nb=0 reservoirs!
    //   - (K - 3) Outer Shield Ring on outer radius r2 (~108px, 360/(K-3) deg apart) -> 360-degree protective wall!
    let usedConcentricCircle = false;
    if (!realBoss && K >= 6) {
      const r1 = clamp(Math.round(0.72 * scales.rCell), 38, 54);
      const r2 = clamp(Math.round(1.75 * scales.rCell), 92, 128);
      let bestCenter = null, bestCenterScore = -Infinity;
      const cStride = W * H > 900000 ? 16 : 12;
      for (let cy = r2 + 24; cy < H - r2 - 24; cy += cStride) {
        for (let cx = r2 + 24; cx < W - r2 - 24; cx += cStride) {
          const cc = cy * W + cx;
          if (!landMask[cc] || this.compSize[cc] < minViableCompSize) continue;
          const dE = distToEnemies(cx, cy);
          if (dE < r2 + 25) continue;
          // Check how many of the 10 concentric circle points land on valid mainland
          let validPts = 0, minEnemyD = dE;
          const innerN = 3, outerN = K - innerN;
          for (let i = 0; i < innerN; i++) {
            const ang = (2 * Math.PI * i) / innerN;
            const px = Math.round(cx + r1 * Math.cos(ang)), py = Math.round(cy + r1 * Math.sin(ang));
            const sc = this.snapToLand(px, py, 16);
            if (sc >= 0 && this.compId[sc] === this.compId[cc]) validPts++;
          }
          for (let j = 0; j < outerN; j++) {
            const ang = (2 * Math.PI * j) / outerN + Math.PI / outerN;
            const px = Math.round(cx + r2 * Math.cos(ang)), py = Math.round(cy + r2 * Math.sin(ang));
            const sc = this.snapToLand(px, py, 20);
            if (sc >= 0 && this.compId[sc] === this.compId[cc]) {
              validPts++;
              const sx = sc % W, sy = (sc / W) | 0;
              minEnemyD = Math.min(minEnemyD, distToEnemies(sx, sy));
            }
          }
          if (validPts < K - 1) continue;
          const centerScore = validPts * 500 + Math.min(260, minEnemyD) * 2.5 + Math.min(180, dComp[cc]);
          if (centerScore > bestCenterScore) {
            bestCenterScore = centerScore;
            bestCenter = { cx, cy, compId: this.compId[cc] };
          }
        }
      }
      if (bestCenter) {
        usedConcentricCircle = true;
        const { cx, cy, compId } = bestCenter;
        const innerN = 3, outerN = K - innerN;
        const ringSpecs = [];
        for (let i = 0; i < innerN; i++) {
          const ang = (2 * Math.PI * i) / innerN;
          ringSpecs.push({ wantX: Math.round(cx + r1 * Math.cos(ang)), wantY: Math.round(cy + r1 * Math.sin(ang)), role: 'INNER_CORE', snapR: 22 });
        }
        for (let j = 0; j < outerN; j++) {
          const ang = (2 * Math.PI * j) / outerN + Math.PI / outerN;
          ringSpecs.push({ wantX: Math.round(cx + r2 * Math.cos(ang)), wantY: Math.round(cy + r2 * Math.sin(ang)), role: 'OUTER_RING', snapR: 28 });
        }
        for (const spec of ringSpecs) {
          let sc = this.snapToLand(spec.wantX, spec.wantY, spec.snapR);
          if (sc < 0) sc = this.snapToLand(cx, cy, 40);
          if (sc >= 0) {
            const fx = sc % W, fy = (sc / W) | 0;
            chosenTargets.push({
              cell: sc,
              x: fx,
              y: fy,
              role: spec.role,
              totalScore: 1000,
              voronoiPixels: 5000,
              bossDist: -1,
              minAllyDist: chosenTargets.length ? Math.round(distToChosenSquad(fx, fy)) : r1,
              minEnemyDist: Math.round(distToEnemies(fx, fy)),
            });
          }
        }
      }
    }

    for (let m = usedConcentricCircle ? K : 0; m < K; m++) {
      const wantRole =
        m < targetFlankCount
          ? 'FLANK_GUARD'
          : m >= K - targetSpoilerCount
            ? 'SPOILER_BANK'
            : 'ECO_BANK';
      let picked = pickNextTarget(wantRole);`;

if (!sc.includes(oldSolveStart)) {
  console.error('Could not find oldSolveStart in spawn-coordinator.mjs!');
  process.exit(1);
}
sc = sc.replace(oldSolveStart, newSolveStart);
fs.writeFileSync('spawn-coordinator.mjs', sc, 'utf8');
console.log('Successfully installed True Concentric Circle Formation (3 INNER_CORE + 7 OUTER_RING) in spawn-coordinator.mjs!');
