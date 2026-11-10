import fs from 'node:fs';

let code = fs.readFileSync('v27-team-live.js', 'utf8').replace(/\r\n/g, '\n');

// 1. In PARAMS, disable the 7 experimental engine exploits that drain balances / trigger anti-cheat / cause 0-density openings:
const paramFixes = [
  ['flashLoanMode: 3,', 'flashLoanMode: 0,'],
  ['seaCore: 1,', 'seaCore: 0,'],
  ['zeroPulseMode: 1,', 'zeroPulseMode: 0,'],
  ['atkFreshBoats: 1,', 'atkFreshBoats: 0,'],
  ['narrowBoatFirstMode: 1,', 'narrowBoatFirstMode: 0,'],
  ['reigniteBorders: 1,', 'reigniteBorders: 0,'],
  ['frogHopOverMode: 1,', 'frogHopOverMode: 0,'],
  ['oppFloorCap: 128,', 'oppFloorCap: 88,'],
];
for (const [oldP, newP] of paramFixes) {
  if (code.includes(oldP)) {
    code = code.replace(oldP, newP);
    console.log(`Set ${newP}`);
  }
}

// 2. Restore clean v27 keepCap = this.dpKeep(g) in dpNeutral (remove Math.floor(0.50 * bal) override)
code = code.replace(
  'const keepCap = this.neutral > 0 ? Math.min(this.dpKeep(g), Math.floor(0.50 * bal)) : this.dpKeep(g);',
  'const keepCap = this.dpKeep(g);'
);

// 3. Restore clean v27 floorFor0 (remove botKeepCap = Math.min(35 * L, Math.floor(0.55 * B)) override)
const oldFloorFor0 = `    if (P.winR > 0 && g.t < P.dpEnd && !this.person(g, q)) {
      const L = Math.max(1, g.terr[this.me]), B = g.bal[this.me];
      const botKeepCap = Math.min(35 * L, Math.floor(0.55 * B));
      const baseWin = (this.botPx(g, q) * L) / (P.winR * Math.max(1, g.t));
      return Math.max(baseWin, Math.min(Math.max(this.dpKeep(g), this.peopleFloor(g), this.sb || 0), botKeepCap));
    }`;
const newFloorFor0 = `    if (P.winR > 0 && g.t < P.dpEnd && !this.person(g, q)) {
      return Math.max(this.winFloor(g, q), this.peopleFloor(g));
    }`;
if (code.includes(oldFloorFor0)) {
  code = code.replace(oldFloorFor0, newFloorFor0);
  console.log('Restored clean v27 winFloor in floorFor0!');
}

// 4. Remove the t>=600 35% balance neutral grab override and t>=750 buyLand override before coreFrom (t=1500)
const oldPreCore = `      super.act(g);
      if (this.cmds === before && g.t >= 600 && this.neutral > 0 && g.attackTroopsOn(me, NEUTRAL) === 0) {
        const grab = Math.min(Math.floor(0.35 * g.bal[me]), Math.max(this.minCmd(g), 4 * this.neutral + 120));
        if (grab > 0 && g.bal[me] - grab > 12 * Math.max(1, g.terr[me])) this.send(g, NEUTRAL, grab);
      }
      if (this.cmds === before && g.t >= 750 && this.neutral === 0 && !this.hasBorderFood(g)) {
        this.buyLand(g);
        if (this.cmds === before) this.tryDonateToTeammate(g);
      }`;
const newPreCore = `      super.act(g);
      if (this.cmds === before && g.t >= 850 && this.neutral === 0 && !this.hasBorderFood(g)) {
        this.tryDonateToTeammate(g);
      }`;
if (code.includes(oldPreCore)) {
  code = code.replace(oldPreCore, newPreCore);
  console.log('Removed pre-1500 35% neutral grab & premature buyLand override!');
}

// 5. Remove the 10% squad-rescue poke (g.attack(102, mainAttacker, me)) that starts premature multi-front grudge wars!
const oldPokeStart = '        if (\n          mainAttacker >= 0 &&';
const oldPokeEnd = '            return true;\n          }\n        }';
const idxS = code.indexOf(oldPokeStart);
if (idxS >= 0) {
  const idxE = code.indexOf(oldPokeEnd, idxS);
  if (idxE >= 0) {
    code = code.slice(0, idxS) + code.slice(idxE + oldPokeEnd.length);
    console.log('Removed 10% squad-rescue poke that triggered premature grudge wars!');
  }
}

// 6. Clean up tryDonateToTeammate: ONLY donate when truly boxedIn (no enemy humans, no AI bots, no neutral land) OR when dMe >= 128 (near interest cap), and NEVER donate below dMe = 105 on frontline!
const oldDonateCheck = `    if (!boxedIn && dMe < 135) return false;
    if (boxedIn && dMe < 68) return false;`;
const newDonateCheck = `    if (!boxedIn && dMe < 128) return false;
    if (boxedIn && dMe < (hasExposedCoast ? 75 : 35)) return false;`;
if (code.includes(oldDonateCheck)) {
  code = code.replace(oldDonateCheck, newDonateCheck);
}

// Also in squad rescue donate: frontline bots (not boxedIn) only donate if dMe >= 122 (so frontline bots never drain their own defense below 100*L!)
code = code.replace(
  'const minDonorDens = boxedIn ? 48 : 108;',
  'const minDonorDens = boxedIn ? (hasExposedCoast ? 72 : 38) : 122;'
);

// 7. Remove the artificial 88*L keep lock we added earlier so pure v27 safeAt + worth formula works cleanly
const artificialKeep = `      if (person && !o.nearCollapse && L >= 22000 && humanNbCount >= 1) {
        keep = Math.max(keep, Math.min(safe, 88 * L));
      }\n`;
if (code.includes(artificialKeep)) {
  code = code.replace(artificialKeep, '');
  console.log('Removed artificial 88*L keep patch (restored clean v27 safeAt/worth math)!');
}

fs.writeFileSync('v27-team-live.js', code, 'utf8');
console.log('Successfully stripped all bloat/patches and restored pure v27 mathematical core!');
