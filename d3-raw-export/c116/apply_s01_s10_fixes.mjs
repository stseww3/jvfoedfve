import fs from 'node:fs';
import path from 'node:path';

// 1. Patch c116/v27-team-live.js
const v27Path = path.resolve('v27-team-live.js');
let v27 = fs.readFileSync(v27Path, 'utf8');

// V7: Align frontline retention parameters with 80% winrate / c110 baseline
v27 = v27.replace(/bleedDiscount:\s*0\.72,\s*\r?\n\s*bleedSafeCap:\s*0,\s*\r?\n\s*collapseRatio:\s*1\.40,\s*\r?\n\s*pulseFrac:\s*0\.20,\s*\r?\n\s*pulseMinShare:\s*0\.04,\s*\r?\n\s*zeroPulseMode:\s*0,\s*\r?\n\s*thinMaxTD:\s*0\.48,\s*\r?\n\s*thinDiscount:\s*0\.78,\s*\r?\n\s*pocket0Mult:\s*0\.76,\s*\r?\n\s*pocket1Rank:\s*0\.88,\s*\r?\n\s*contactStepsMax:\s*350,\s*\r?\n\s*contactPenalty:\s*0\.002,\s*\r?\n\s*oppFloorCap:\s*78,\s*\r?\n\s*focusBonus:\s*0\.78,\s*\r?\n\s*focusT:\s*350,\s*\r?\n\s*defendDiscount:\s*0\.85,\s*\r?\n\s*defendDiscountMid:\s*0\.88,\s*\r?\n\s*overHumanCap:\s*1\.12,\s*\r?\n\s*overHumanKeep:\s*0\.92,\s*\r?\n\s*soleBufferPenalty:\s*1\.15,/,
`bleedDiscount: 1.0,
  bleedSafeCap: 1,
  collapseRatio: 1.40,
  pulseFrac: 0.12,
  pulseMinShare: 0.04,
  zeroPulseMode: 0,
  thinMaxTD: 0.48,
  thinDiscount: 1.0,
  pocket0Mult: 1.0,
  pocket1Rank: 1.0,
  contactStepsMax: 350,
  contactPenalty: 0.002,
  oppFloorCap: 88,
  focusBonus: 1.0,
  focusT: 350,
  defendDiscount: 0.85,
  defendDiscountMid: 0.88,
  overHumanCap: 1.28,
  overHumanKeep: 1.12,
  soleBufferPenalty: 1.60,`);

v27 = v27.replace(/crowdedHardPenalty:\s*1\.08,\s*\r?\n\s*crowdedHardCap:\s*1\.10,\s*\r?\n\s*absorbMode:\s*0,\s*\r?\n\s*absorbWaveMin:\s*0\.04,\s*\r?\n\s*absorbMemory:\s*250,\s*\r?\n\s*counterClearMode:\s*6,\s*\r?\n\s*overPulseMode:\s*1,/,
`crowdedHardPenalty: 1.35,
  crowdedHardCap: 1.26,
  absorbMode: 0,
  absorbWaveMin: 0.04,
  absorbMemory: 250,
  counterClearMode: 6,
  overPulseMode: 0,`);

v27 = v27.replace(/leaderHardFrom:\s*0,\s*\r?\n\s*leaderMinShare:\s*0\.16,\s*\r?\n\s*siegeShrinkRatio:\s*0,/,
`leaderHardFrom: 5000,
  leaderMinShare: 0.16,
  siegeShrinkRatio: 0.72,`);

// V10: Fix 2-tick machine-gun [HL-ASSIST] 10%B drain by enforcing 36-tick cooldown and dMe >= 86
v27 = v27.replace(
  /if \(bossAttackers\.length > 0 && B >= 8000 && dMe >= 38\) \{/,
  `if (bossAttackers.length > 0 && B >= 25000 && dMe >= 86 && g.t - (this.lastAssistPokeTick ?? -999) >= 36) {`
);
v27 = v27.replace(
  /if \(g\.attack\(102, q, me\)\) \{ \/\/ ~10\.0%B light assist!\r?\n\s*this\.cmds\+\+;\r?\n\s*this\.hitTo\.set\(q, g\.t\);/,
  `if (g.attack(82, q, me)) { // ~8.0%B light assist with 36t cooldown!\n            this.cmds++;\n            this.lastAssistPokeTick = g.t;\n            this.hitTo.set(q, g.t);`
);

// V6 + Tax Optimization: Lower boxed-in rear bank reserve floor so boxed-in coastal/inland teammates pump troops to frontline, and raise transfer pct to >= 220..360 (amortizing 6.25%B flat tax)
v27 = v27.replace(
  /const prodOptFloor = boxedIn\r?\n\s*\? \(hasExposedCoast \? 72 \* L : 66 \* L\)\r?\n\s*: Math\.max\(94 \* L, this\.safeAt\(g, -1\)\);/,
  `const prodOptFloor = boxedIn\n      ? (hasExposedCoast ? 44 * L : 34 * L)\n      : Math.max(92 * L, this.safeAt(g, -1));`
);
v27 = v27.replace(
  /const reqD = boxedIn \? 82 : 108;/,
  `const reqD = boxedIn ? 58 : 108;`
);
v27 = v27.replace(
  /const idealPct = bestKind === "defense_dispatch"\r?\n\s*\? \(boxedIn \? 260 : 190\)\r?\n\s*: \(boxedIn \? 225 : 170\);\r?\n\s*const pct = Math\.min\(maxSafePct, idealPct\);\r?\n\s*if \(pct < 128\) return false;/,
  `const idealPct = bestKind === "defense_dispatch"\n      ? (boxedIn ? 380 : 240)\n      : (boxedIn ? 320 : 220);\n    const pct = Math.min(maxSafePct, idealPct);\n    if (pct < 180) return false;`
);

fs.writeFileSync(v27Path, v27, 'utf8');
console.log('Patched c116/v27-team-live.js with S01-S10 fixes');

// 2. Patch c116/spawn-coordinator.mjs (V1 main continent strict check + V2 compact corner fan radius)
const scPath = path.resolve('spawn-coordinator.mjs');
let sc = fs.readFileSync(scPath, 'utf8');

sc = sc.replace(
  /const r1 = clamp\(Math\.round\(1\.38 \* scales\.rCell\), Math\.max\(78, r0 \+ minReqSep\), 132\);\r?\n\s*const r2 = clamp\(Math\.round\(2\.35 \* scales\.rCell\), Math\.max\(142, r1 \+ minReqSep\), 225\);/,
  `const r1 = clamp(Math.round(1.12 * scales.rCell), Math.max(66, r0 + minReqSep), 108);\n      const r2 = clamp(Math.round(1.88 * scales.rCell), Math.max(122, r1 + minReqSep), 182);`
);

sc = sc.replace(
  /if \(!landMask\[c\]\) continue;\r?\n\s*const dA = distToChosenSquad\(x, y\);/,
  `if (!landMask[c]) continue;\n            if (this.largestCompId >= 0 && this.compId[c] !== this.largestCompId && this.compSize[c] < minViableCompSize) continue;\n            const dA = distToChosenSquad(x, y);`
);

fs.writeFileSync(scPath, sc, 'utf8');
console.log('Patched c116/spawn-coordinator.mjs with V1 + V2 fixes');
