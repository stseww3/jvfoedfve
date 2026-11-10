import fs from 'node:fs';

let code = fs.readFileSync('v27-team-live.js', 'utf8').replace(/\r\n/g, '\n');

const oldCap = `      const Lp = Math.max(1, g.terr[p]), Bp = g.bal[p], dAlly = Bp / Lp;
      if (dAlly >= 105) continue; // Never dispatch to a territory already above the 100*L full-interest cap!`;

const newCap = `      const Lp = Math.max(1, g.terr[p]), Bp = g.bal[p], dAlly = Bp / Lp;
      if (dAlly >= (boxedIn ? 132 : 112)) continue;`;

if (code.includes(oldCap)) {
  code = code.replace(oldCap, newCap);
  console.log('Fixed dAlly cap for boxedIn donors (132) vs frontline donors (112)!');
}

const oldCaseB = `        const reqD = boxedIn ? 98 : 106;
        if (dMe < reqD || dAlly > 90 || B <= 1.14 * prodOptFloor || dMe < dAlly + 18) continue;`;

const newCaseB = `        const reqD = boxedIn ? 95 : 106;
        const maxAllyD = boxedIn ? (activePush || hasPreyOpening ? 130 : 122) : 92;
        if (dMe < reqD || dAlly > maxAllyD || B <= 1.14 * prodOptFloor || (!boxedIn && dMe < dAlly + 16)) continue;`;

if (code.includes(oldCaseB)) {
  code = code.replace(oldCaseB, newCaseB);
  console.log('Fixed Case B: boxedIn rear banks at dMe>=95 dispatch to frontline brothers up to dAlly<=130 while keeping 76*L full-yield reservoir!');
}

fs.writeFileSync('v27-team-live.js', code, 'utf8');
