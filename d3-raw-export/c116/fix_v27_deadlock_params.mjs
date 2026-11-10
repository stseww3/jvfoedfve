import fs from 'node:fs';

let code = fs.readFileSync('v27-team-live.js', 'utf8').replace(/\r\n/g, '\n');

// 1. In PARAMS, restore proven v27 offensive parameters so bots don't freeze at d=145~150!
const fixes = [
  ['bleedDiscount: 1.0,', 'bleedDiscount: 0.72,'],
  ['thinDiscount: 1.0,', 'thinDiscount: 0.78,'],
  ['focusBonus: 1.0,', 'focusBonus: 0.78,'],
  ['pocket0Mult: 1.0,', 'pocket0Mult: 0.76,'],
  ['pocket1Rank: 1.0,', 'pocket1Rank: 0.88,'],
  ['oppFloorCap: 88,', 'oppFloorCap: 68,'],
  ['overHumanCap: 1.28,', 'overHumanCap: 1.12,'],
  ['overHumanKeep: 1.12,', 'overHumanKeep: 0.92,'],
  ['crowdedHardPenalty: 1.35,', 'crowdedHardPenalty: 1.08,'],
  ['crowdedHardCap: 1.26,', 'crowdedHardCap: 1.10,'],
  ['soleBufferPenalty: 1.60,', 'soleBufferPenalty: 1.15,'],
  ['leaderHardFrom: 5000,', 'leaderHardFrom: 0,'],
  ['siegeShrinkRatio: 0.72,', 'siegeShrinkRatio: 0,'],
  ['a06AloneSafe: 1,', 'a06AloneSafe: 0,'],
  ['a06AggMemGate: 1,', 'a06AggMemGate: 0,'],
  ['pulseFrac: 0.12,', 'pulseFrac: 0.22,'],
];

for (const [oldS, newS] of fixes) {
  if (code.includes(oldS)) {
    code = code.replace(oldS, newS);
    console.log(`Updated ${newS}`);
  }
}

// 2. Also in buyLand: remove hardCapMult = 1.50 override so bots never freeze up to d=150!
code = code.replace(
  'const hardCapMult = o.isCrowdedHard && c >= 2.15 * worth && g.bal[q] >= 0.55 * B ? 1.50 : P.crowdedHardCap;',
  'const hardCapMult = P.crowdedHardCap;'
);

// 3. When dMe >= 118 (above soft cap where interest decays rapidly toward 0 at 150),
// allow attacking the best target in offers(g) keeping 85 * L (just like V13/V17 idle push)!
const oldOverKeep = `      if (over) {
        const overKeepMult = isSoleHealthyBuffer
          ? P.overHumanKeep
          : isSiegeShrink
            ? P.siegeOverKeep
            : o.isCrowdedHard
              ? 1.08
              : P.hold;
        keep = Math.min(keep, overKeepMult * 100 * L);
      }`;

const newOverKeep = `      if (over) {
        const overKeepMult = dMe >= 122 ? 0.82 : isSoleHealthyBuffer ? P.overHumanKeep : P.hold;
        keep = Math.min(keep, overKeepMult * 100 * L);
      }`;

if (code.includes(oldOverKeep)) {
  code = code.replace(oldOverKeep, newOverKeep);
  console.log('Fixed overKeepMult so bots above d=122 convert surplus troops into territory instead of rotting at d=150!');
}

fs.writeFileSync('v27-team-live.js', code, 'utf8');
