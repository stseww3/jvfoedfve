import fs from 'node:fs';

let code = fs.readFileSync('v27-team-live.js', 'utf8').replace(/\r\n/g, '\n');

const oldLoop = `    let bestAlly = -1, bestScore = -Infinity;
    for (let p = 0; p < g.humans; p++) {
      if (p === me || !g.alive[p] || !this.isTeammate(g, p) || (!this.isBossNpl(g, p) && !this.isOurSquadBot(g, p)) || g.terr[p] < 600) continue;
      const dAlly = g.bal[p] / Math.max(1, g.terr[p]);
      if (dAlly >= 146) continue;
      let outAtk = 0, inAtk = 0;
      const sb = g.slotBase(p);
      for (let i = 0; i < g.atkCount[p]; i++) {
        const tgt = g.atkTarget[sb + i];
        if (tgt !== 512) outAtk += g.atkTroops[sb + i];
      }
      for (const a of g.attackersOf(p)) inAtk += g.attackTroopsOn(a, p);
      const allyEnemyNbs = this.peopleOf(g, p);
      if (!allyEnemyNbs.length && outAtk === 0 && inAtk === 0 && g.t > 2200) continue;
      const isBoss = p === bossId;
      const isSquad = this.isOurSquadBot(g, p);
      if (!isBoss && !isSquad) continue;
      const crownBonus = Math.min(2500, Math.floor(g.terr[p] / 12));
      const score = (isBoss ? 8000 : 600 + crownBonus) + (outAtk + inAtk) / 400 + (135 - dAlly) * 3;
      if (score > bestScore && (isBoss || boxedIn || outAtk + inAtk > 0.04 * g.bal[p] || (isSquad && dMe >= 120 && dAlly < 98))) {
        bestScore = score;
        bestAlly = p;
      }
    }`;

const newLoop = `    let bestAlly = -1, bestScore = -Infinity;
    for (let p = 0; p < g.humans; p++) {
      if (p === me || !g.alive[p] || !this.isTeammate(g, p) || (!this.isBossNpl(g, p) && !this.isOurSquadBot(g, p)) || g.terr[p] < 600) continue;
      if (typeof window !== "undefined" && window.ao?.iD && !window.ao.iD(p)) continue;
      const dAlly = g.bal[p] / Math.max(1, g.terr[p]);
      if (dAlly >= 142) continue;
      let outAtk = 0, inAtk = 0;
      const sb = g.slotBase(p);
      for (let i = 0; i < g.atkCount[p]; i++) {
        const tgt = g.atkTarget[sb + i];
        if (tgt !== 512) outAtk += g.atkTroops[sb + i];
      }
      for (const a of g.attackersOf(p)) inAtk += g.attackTroopsOn(a, p);
      const allyEnemyNbs = this.peopleOf(g, p);
      if (!allyEnemyNbs.length && outAtk === 0 && inAtk === 0 && g.t > 2200) continue;
      const isBoss = p === bossId;
      const isSquad = this.isOurSquadBot(g, p);
      if (!isBoss && !isSquad) continue;
      const crownBonus = Math.min(2500, Math.floor(g.terr[p] / 12));
      const score = (isBoss ? 8000 : 600 + crownBonus) + (outAtk + inAtk) / 400 + (135 - dAlly) * 3;
      if (score > bestScore && (isBoss || boxedIn || outAtk + inAtk > 0.04 * g.bal[p] || (isSquad && dMe >= 120 && dAlly < 98))) {
        bestScore = score;
        bestAlly = p;
      }
    }`;

if (code.includes(oldLoop)) {
  code = code.replace(oldLoop, newLoop);
  console.log('Added window.ao.iD(p) check to surplus donation loop so donations never get rejected by anti-feeding quota!');
}

fs.writeFileSync('v27-team-live.js', code, 'utf8');
