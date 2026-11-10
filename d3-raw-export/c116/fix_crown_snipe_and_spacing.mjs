import fs from 'node:fs';

// 1. In spawn-coordinator.mjs: restore wide Voronoi spacing so 10 [APEX] brothers never box each other in at 25k~32k!
let sc = fs.readFileSync('spawn-coordinator.mjs', 'utf8').replace(/\r\n/g, '\n');

sc = sc.replace(
  'allyMinSep: clamp(Math.round(Math.max(1.08 * rCell, 0.068 * diag)), 64, 112),',
  'allyMinSep: clamp(Math.round(Math.max(1.48 * rCell, 0.115 * diag)), 108, 185),'
);
sc = sc.replace(
  'clusterMax: clamp(Math.round(Math.max(2.90 * rCell, 0.250 * diag)), 210, 390),',
  'clusterMax: clamp(Math.round(Math.max(5.80 * rCell, 0.580 * diag)), 420, 880),'
);
sc = sc.replace(
  'this.injectChosenSquadPoint(picked.cell, m, Math.max(115, Math.round(1.45 * scales.allyMinSep)));',
  'this.injectChosenSquadPoint(picked.cell, m, Math.max(210, Math.round(2.10 * scales.allyMinSep)));'
);

fs.writeFileSync('spawn-coordinator.mjs', sc, 'utf8');
console.log('Updated spawn-coordinator.mjs: wide Voronoi spacing (108~185px) so our 10 [APEX] bots never box each other in!');

// 2. In v27-team-live.js:
// - When evaluating offers(g), give a 0.65x cost discount to enemy human targets `q` that are currently under attack by a NON-APEX random teammate (`randomAllyAtkOnQ > 0`), so our [APEX] frontline carry ALWAYS snipes the collapse land before the random teammate steals the Crown!
// - In tryDonateToTeammate, allow donating to our largest [APEX] frontline carry up to `dAlly < 146` (instead of stopping at 132) so our carry has maximum overwhelming troop advantage to finish off every enemy!
let v27 = fs.readFileSync('v27-team-live.js', 'utf8').replace(/\r\n/g, '\n');

v27 = v27.replace(
  'if (dAlly >= 132) continue;',
  'if (dAlly >= 146) continue;'
);

const oldOtherLoop = `        let otherAtk = 0, otherAtkers = 0, allyAtk = 0, clanAllyAtkers = 0, bossAtkOnQ = 0;
        for (const a of g.attackersOf(q)) {
          if (a !== me && !g.isBot(a)) {
            const tr = g.attackTroopsOn(a, q);
            otherAtkers++;
            otherAtk += tr;
            if (a === bossId) bossAtkOnQ += tr;
            if (this.isTeammate(g, a)) {
              allyAtk += tr;
              clanAllyAtkers += this.isOurSquadBot(g, a) ? 2 : 1;
            }
          }
        }`;

const newOtherLoop = `        let otherAtk = 0, otherAtkers = 0, allyAtk = 0, clanAllyAtkers = 0, bossAtkOnQ = 0, randomTeamAtk = 0;
        for (const a of g.attackersOf(q)) {
          if (a !== me && !g.isBot(a)) {
            const tr = g.attackTroopsOn(a, q);
            otherAtkers++;
            otherAtk += tr;
            if (a === bossId) bossAtkOnQ += tr;
            if (this.isTeammate(g, a)) {
              allyAtk += tr;
              if (this.isOurSquadBot(g, a) || a === bossId) {
                clanAllyAtkers += 2;
              } else {
                randomTeamAtk += tr;
              }
            }
          }
        }`;

if (v27.includes(oldOtherLoop)) {
  v27 = v27.replace(oldOtherLoop, newOtherLoop);
  v27 = v27.replace(
    'let rankMult = 1.0;',
    'let rankMult = 1.0;\n        if (randomTeamAtk > 0) { c *= 0.68; rankMult *= 0.60; }'
  );
  console.log('Added random-teammate kill-snipe priority (c*=0.68, rankMult*=0.60) so [APEX] claims collapse land before random teammates!');
}

fs.writeFileSync('v27-team-live.js', v27, 'utf8');
