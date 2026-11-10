import fs from 'node:fs';
import path from 'node:path';

// 1. Fix c116/v27-team-live.js:
//    - Restore healthy rear-bank compound interest reserve (prodOptFloor = 76*L / 70*L, reqD = 96, emergDefFloor = 58*L / 48*L)
//    - Enforce strict `dMe >= dAlly + 15` on ALL dispatches (never let dMe=58 donate to dAlly=100!)
//    - Cap recipient dAlly <= 88 for defense_dispatch and <= 92 for yield/offense_dispatch so we never pump troops into already-dense (>95*L) territories
//    - Increase cooldown between dispatches from 12t to 24t to prevent chain-tax burn
const v27Path = path.resolve('v27-team-live.js');
let v27 = fs.readFileSync(v27Path, 'utf8');

v27 = v27.replace(
  /if \(g\.t < 1500 \|\| g\.terr\[me\] < 1200 \|\| g\.bal\[me\] < 30000 \|\| g\.t - \(this\.lastDonateTick \?\? -999\) < 12\) return false;/,
  `if (g.t < 1500 || g.terr[me] < 1200 || g.bal[me] < 35000 || g.t - (this.lastDonateTick ?? -999) < 24) return false;`
);

v27 = v27.replace(
  /const prodOptFloor = boxedIn\r?\n\s*\? \(hasExposedCoast \? 44 \* L : 34 \* L\)\r?\n\s*: Math\.max\(92 \* L, this\.safeAt\(g, -1\)\);\r?\n\r?\n\s*const emergDefFloor = boxedIn\r?\n\s*\? \(hasExposedCoast \? 32 \* L : 22 \* L\)\r?\n\s*: Math\.max\(88 \* L, this\.safeAt\(g, -1\)\);/,
  `const prodOptFloor = boxedIn\n      ? (hasExposedCoast ? 76 * L : 70 * L)\n      : Math.max(94 * L, this.safeAt(g, -1));\n\n    const emergDefFloor = boxedIn\n      ? (hasExposedCoast ? 58 * L : 48 * L)\n      : Math.max(88 * L, this.safeAt(g, -1));`
);

v27 = v27.replace(
  /if \(underFire\) \{\r?\n\s*\/\/ Case A: Emergency 2:1 Defense Dispatch\r?\n\s*const reqD = boxedIn \? \(hasExposedCoast \? 42 : 30\) : 102;\r?\n\s*if \(dMe < reqD \|\| B <= 1\.12 \* emergDefFloor \|\| \(!boxedIn && dMe < dAlly \+ 16\)\) continue;/,
  `if (underFire) {\n        // Case A: Emergency 2:1 Defense Dispatch (strictly require dAlly < 85 and dMe >= dAlly + 15!)\n        const reqD = boxedIn ? (hasExposedCoast ? 68 : 58) : 102;\n        if (dMe < reqD || dAlly >= 85 || B <= 1.12 * emergDefFloor || dMe < dAlly + 15) continue;`
);

v27 = v27.replace(
  /const reqD = boxedIn \? 58 : 108;\r?\n\s*const maxAllyD = boxedIn \? \(activePush \|\| hasPreyOpening \|\| enemyNbs > 0 \? 140 : 128\) : 96;\r?\n\s*if \(dMe < reqD \|\| dAlly > maxAllyD \|\| B <= 1\.14 \* prodOptFloor \|\| \(!boxedIn && dMe < dAlly \+ 16\)\) continue;/,
  `const reqD = boxedIn ? 96 : 108;\n        const maxAllyD = boxedIn ? (activePush || hasPreyOpening || enemyNbs > 0 ? 94 : 88) : 88;\n        if (dMe < reqD || dAlly > maxAllyD || B <= 1.14 * prodOptFloor || dMe < dAlly + 15) continue;`
);

v27 = v27.replace(
  /const idealPct = bestKind === "defense_dispatch"\r?\n\s*\? \(boxedIn \? 380 : 240\)\r?\n\s*: \(boxedIn \? 320 : 220\);\r?\n\s*const pct = Math\.min\(maxSafePct, idealPct\);\r?\n\s*if \(pct < 180\) return false;/,
  `const idealPct = bestKind === "defense_dispatch"\n      ? (boxedIn ? 260 : 190)\n      : (boxedIn ? 220 : 170);\n    const pct = Math.min(maxSafePct, idealPct);\n    if (pct < 150) return false;`
);

fs.writeFileSync(v27Path, v27, 'utf8');
console.log('Updated c116/v27-team-live.js with strict non-inversion & compound interest floor');

// 2. Fix c116/spawn-coordinator.mjs:
//    - In 10-bot Corner Sector Phalanx: use 1 Apex + 1 Inner Arc (2 total inner reservoirs instead of 4) and 8 Outer Shield Wall bots across a wider fan (PI / 2.5) with r1=1.32*rCell, r2=2.28*rCell so 8 bots expand outward on the frontline instead of 7 bots getting boxed in at nb=0!
const scPath = path.resolve('spawn-coordinator.mjs');
let sc = fs.readFileSync(scPath, 'utf8');

sc = sc.replace(
  /const r1 = clamp\(Math\.round\(1\.12 \* scales\.rCell\), Math\.max\(66, r0 \+ minReqSep\), 108\);\r?\n\s*const r2 = clamp\(Math\.round\(1\.88 \* scales\.rCell\), Math\.max\(122, r1 \+ minReqSep\), 182\);/,
  `const r1 = clamp(Math.round(1.32 * scales.rCell), Math.max(76, r0 + minReqSep), 126);\n      const r2 = clamp(Math.round(2.28 * scales.rCell), Math.max(145, r1 + minReqSep), 220);`
);

sc = sc.replace(
  /const fanHalf = Math\.PI \/ 3\.2;\r?\n\s*const innerCount = Math\.min\(3, Math\.max\(2, Math\.floor\(\(K - 1\) \* 0\.34\)\)\);/,
  `const fanHalf = Math.PI / 2.55;\n        const innerCount = Math.min(2, Math.max(1, Math.floor((K - 1) * 0.22)));`
);

fs.writeFileSync(scPath, sc, 'utf8');
console.log('Updated c116/spawn-coordinator.mjs with 2-inner + 8-outer wide frontline fan');
