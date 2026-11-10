import fs from 'node:fs';

let code = fs.readFileSync('v27-team-live.js', 'utf8').replace(/\r\n/g, '\n');

// 1. In tryPeaceVote: ONLY vote YES or initiate peace vote if the #1 largest player on the map (Crown) is OUR squad bot or Boss npl!
const oldPeace = `    const weLead = ourTeamLand >= 0.58 * Math.max(1, g.land) || this.isMopUp(g);
    const caller = window.__lastPeaceCaller;
    const callerIsOurs =
      Number.isInteger(caller) &&
      caller >= 0 &&
      caller < g.humans &&
      (caller === me || this.isOurSquadBot(g, caller) || this.isBossNpl(g, caller));`;

const newPeace = `    let topPlayer = -1, topTerr = -1;
    for (let p = 0; p < g.players; p++) {
      if (g.alive[p] && g.terr[p] > topTerr) {
        topTerr = g.terr[p];
        topPlayer = p;
      }
    }
    const weHoldCrown = topPlayer >= 0 && (topPlayer === me || this.isOurSquadBot(g, topPlayer) || this.isBossNpl(g, topPlayer));
    const weLead = weHoldCrown && (ourTeamLand >= 0.65 * Math.max(1, g.land) || this.isMopUp(g));
    const caller = window.__lastPeaceCaller;
    const callerIsOurs =
      weHoldCrown &&
      Number.isInteger(caller) &&
      caller >= 0 &&
      caller < g.humans &&
      (caller === me || this.isOurSquadBot(g, caller) || this.isBossNpl(g, caller));`;

if (code.includes(oldPeace)) {
  code = code.replace(oldPeace, newPeace);
  console.log('Patched tryPeaceVote: never vote peace unless our [APEX] squad or Boss holds the #1 Crown!');
}

// 2. In tryDonateToTeammate:
// - Strictly restrict donations to Boss npl OR our [APEX] squad brothers (already enforced at line 4361, verify!)
// - In the surplus donation scoring loop, give a HUGE priority bonus (+2500) to our largest [APEX] frontline brother (`maxSquadFrontlineId`) so all rear boxed-in bots funnel into ONE super-carry to seize #1 Crown!
const oldScore = `      const isBoss = p === bossId;
      const isSquad = this.isOurSquadBot(g, p);
      const score = (isBoss ? 5000 : isSquad ? 600 : 150) + (outAtk + inAtk) / 500 + (135 - dAlly) * 3 + Math.min(150, g.terr[p] / 500);`;

const newScore = `      const isBoss = p === bossId;
      const isSquad = this.isOurSquadBot(g, p);
      if (!isBoss && !isSquad) continue;
      const crownBonus = Math.min(2500, Math.floor(g.terr[p] / 12));
      const score = (isBoss ? 8000 : 600 + crownBonus) + (outAtk + inAtk) / 400 + (135 - dAlly) * 3;`;

if (code.includes(oldScore)) {
  code = code.replace(oldScore, newScore);
  console.log('Patched tryDonateToTeammate: funnel all rear donations into our largest [APEX] carry to guarantee #1 Crown!');
}

fs.writeFileSync('v27-team-live.js', code, 'utf8');
