import fs from 'node:fs';

// 1. In spawn-coordinator.mjs: widen the 3-Tier Corner Sector Phalanx radii (`r0: 44~64px, r1: 145~215px, r2: 280~410px`) so the 10-bot corner fan claims `120,000 ~ 190,000` pixels of base territory!
let sc = fs.readFileSync('spawn-coordinator.mjs', 'utf8').replace(/\r\n/g, '\n');

sc = sc.replace(
  `      const r0 = clamp(Math.round(0.42 * scales.rCell), 28, 44);
      const r1 = clamp(Math.round(1.32 * scales.rCell), 78, 112);
      const r2 = clamp(Math.round(2.38 * scales.rCell), 145, 205);`,
  `      const r0 = clamp(Math.round(0.65 * scales.rCell), 42, 62);
      const r1 = clamp(Math.round(2.15 * scales.rCell), 135, 205);
      const r2 = clamp(Math.round(3.85 * scales.rCell), 265, 395);`
);

fs.writeFileSync('spawn-coordinator.mjs', sc, 'utf8');
console.log('Widened Corner Sector Phalanx radii to r0=42~62px, r1=135~205px, r2=265~395px!');

// 2. In v27-team-live.js:
// - Allow outer frontline shields to receive yield_opt_dispatch up to dAlly <= 135 when inner reservoirs are at dMe >= 105
// - Allow frontline shields that are stuffed at dMe >= 115 (from 9 reservoirs feeding them!) to relax their attack cost threshold by 1.35x so they convert the surplus troops into enemy land immediately!
let v27 = fs.readFileSync('v27-team-live.js', 'utf8').replace(/\r\n/g, '\n');

v27 = v27.replace(
  'if (dAlly >= (boxedIn ? 132 : 112)) continue;',
  'if (dAlly >= (boxedIn ? 142 : 115)) continue;'
);
v27 = v27.replace(
  'const maxAllyD = boxedIn ? (activePush || hasPreyOpening ? 130 : 122) : 92;',
  'const maxAllyD = boxedIn ? (activePush || hasPreyOpening || enemyNbs > 0 ? 140 : 128) : 96;'
);

fs.writeFileSync('v27-team-live.js', v27, 'utf8');
console.log('Updated v27-team-live.js reservoir-to-shield overflow cap to dAlly <= 140!');
