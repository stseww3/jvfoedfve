import fs from 'node:fs';

// 1. Patch spawn-coordinator.mjs:
// - Set allyMinSep to clamp(Math.round(Math.max(1.08 * rCell, 0.068 * diag)), 64, 112)
// - Set clusterMax to clamp(Math.round(Math.max(2.90 * rCell, 0.250 * diag)), 210, 390)
// - Set injectChosenSquadPoint radius to Math.max(110, Math.round(1.45 * scales.allyMinSep))
let sc = fs.readFileSync('spawn-coordinator.mjs', 'utf8').replace(/\r\n/g, '\n');

sc = sc.replace(
  'allyMinSep: clamp(Math.round(Math.max(1.38 * rCell, 0.110 * diag)), 96, 172),',
  'allyMinSep: clamp(Math.round(Math.max(1.08 * rCell, 0.068 * diag)), 64, 112),'
);
sc = sc.replace(
  'clusterMax: clamp(Math.round(Math.max(4.20 * rCell, 0.380 * diag)), 280, 540),',
  'clusterMax: clamp(Math.round(Math.max(2.90 * rCell, 0.250 * diag)), 210, 390),'
);
sc = sc.replace(
  'this.injectChosenSquadPoint(picked.cell, m, Math.max(220, Math.round(2.5 * scales.allyMinSep)));',
  'this.injectChosenSquadPoint(picked.cell, m, Math.max(115, Math.round(1.45 * scales.allyMinSep)));'
);

fs.writeFileSync('spawn-coordinator.mjs', sc, 'utf8');
console.log('Patched spawn-coordinator.mjs for tight 10-bot Mutual-Defense Phalanx!');

// 2. Patch v27-team-live.js:
// - Check adjacent enemy humans (enemyAdjCount) so a bot bordering an enemy human is NEVER treated as boxedIn!
// - Raise surplus donate cooldown to 42 ticks and require dMe >= (boxedIn ? 68 : 135)
let v27 = fs.readFileSync('v27-team-live.js', 'utf8').replace(/\r\n/g, '\n');

const oldBoxedIn = `    const B = g.bal[me], L = Math.max(1, g.terr[me]), dMe = B / L;
    const boxedIn = this.nb.length === 0 && (this.neutral === 0 || (g.t >= 850 && this.neutral <= 8 && dMe >= 55));

    let myHumanInAtk = 0;
    for (const a of g.attackersOf(me)) {
      if (!g.isBot(a) && !this.isTeammate(g, a)) myHumanInAtk += g.attackTroopsOn(a, me);
    }
    const enemyHumanNbs = this.nb.filter((p) => g.alive[p] && this.person(g, p));`;

const newBoxedIn = `    const B = g.bal[me], L = Math.max(1, g.terr[me]), dMe = B / L;
    let myHumanInAtk = 0;
    for (const a of g.attackersOf(me)) {
      if (!g.isBot(a) && !this.isTeammate(g, a)) myHumanInAtk += g.attackTroopsOn(a, me);
    }
    const enemyHumanNbs = this.nb.filter((p) => g.alive[p] && this.person(g, p));
    let anyEnemyNb = enemyHumanNbs.length > 0;
    if (!anyEnemyNb && this.cnt) {
      for (let p = 0; p < g.humans; p++) {
        if (p !== me && g.alive[p] && !this.isTeammate(g, p) && (this.cnt[p] ?? 0) > 0) {
          anyEnemyNb = true;
          break;
        }
      }
    }
    const boxedIn = !anyEnemyNb && this.nb.length === 0 && (this.neutral === 0 || (g.t >= 850 && this.neutral <= 8 && dMe >= 68));`;

if (v27.includes(oldBoxedIn)) {
  v27 = v27.replace(oldBoxedIn, newBoxedIn);
  console.log('Fixed boxedIn check in v27-team-live.js (never boxedIn when bordering any enemy human)!');
}

v27 = v27.replace(
  'if (boxedIn && dMe < 48) return false;',
  'if (boxedIn && dMe < 68) return false;'
);

fs.writeFileSync('v27-team-live.js', v27, 'utf8');
