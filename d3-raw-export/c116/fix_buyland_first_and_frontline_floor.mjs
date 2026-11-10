import fs from 'node:fs';

let code = fs.readFileSync('v27-team-live.js', 'utf8').replace(/\r\n/g, '\n');

// 1. Remove the pre-buyLand emergencyOnly call in act(g) so every territory ALWAYS executes its own buyLand(g) (counter-attacks, eating bleeding enemies, expanding) BEFORE donating surplus!
code = code.replace(
  '    if (g.t >= 1500 && this.tryDonateToTeammate(g, true) && g.online) return;\n',
  ''
);

// 2. In tryDonateToTeammate:
//    - Frontline territories (!boxedIn) NEVER dip below `94 * L` (only donate when `dMe >= 110`, i.e., above the 100*L negative-marginal-interest threshold!)
//    - Boxed-in rear banks (boxedIn) keep `76 * L` during normal production skimming (`dMe >= 95`), or `52 * L` during emergency defense (`underFire`), so rear banks provide 100% of the emergency defensive liquidity while frontline territories NEVER paralyze their own buyLand!
const oldFloors = `    const prodOptFloor = boxedIn
      ? (hasExposedCoast ? 80 * L : 76 * L)
      : Math.max(hasExposedCoast ? 86 * L : 84 * L, this.safeAt(g, -1));

    // Emergency defense floor (\`emergDefFloor\`): when a brother is being attacked by an enemy human (\`underFire\`),
    // his survival (preserving his L pixels of rent+interest capacity + 2:1 defensive trade) justifies dipping into rear reserves down to 48*L!
    const emergDefFloor = boxedIn
      ? (hasExposedCoast ? 62 * L : 46 * L)
      : Math.max(76 * L, 0.85 * this.safeAt(g, -1));`;

const newFloors = `    const prodOptFloor = boxedIn
      ? (hasExposedCoast ? 80 * L : 76 * L)
      : Math.max(96 * L, this.safeAt(g, -1));

    const emergDefFloor = boxedIn
      ? (hasExposedCoast ? 62 * L : 48 * L)
      : Math.max(92 * L, this.safeAt(g, -1));`;

if (code.includes(oldFloors)) {
  code = code.replace(oldFloors, newFloors);
  console.log('Fixed frontline donor floors (92*L ~ 96*L) so frontline bots never drain their own buyLand capacity!');
}

code = code.replace(
  'const reqD = boxedIn ? (hasExposedCoast ? 72 : 58) : 92;',
  'const reqD = boxedIn ? (hasExposedCoast ? 72 : 58) : 108;'
);
code = code.replace(
  'const reqD = boxedIn ? 95 : 106;',
  'const reqD = boxedIn ? 95 : 112;'
);

// 3. Also in buyLand: restore clean v27 `usePulseBlock` (`overPulseMode: 0` on non-bleeding targets when `over`) so a frontline bot with `dMe >= 100` can decisively crush affordable neighbors instead of poking 16%!
code = code.replace(
  'const usePulseBlock =\n        P.pulseFrac > 0 && (!over || o.nearCollapse || o.bleeding || need > 0.32 * B || avail < P.chunk * B);',
  'const usePulseBlock =\n        P.pulseFrac > 0 && (!over || (P.overPulseMode > 0 && (o.nearCollapse || o.bleeding || avail < P.chunk * B)));'
);
code = code.replace('oppFloorCap: 96,', 'oppFloorCap: 78,');
code = code.replace('pulseFrac: 0.16,', 'pulseFrac: 0.20,');

fs.writeFileSync('v27-team-live.js', code, 'utf8');
console.log('Successfully updated v27-team-live.js: buyLand ALWAYS runs before tryDonateToTeammate, and frontline bots only donate above d=108!');
