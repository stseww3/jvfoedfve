import fs from 'node:fs';

let code = fs.readFileSync('v27-team-live.js', 'utf8').replace(/\r\n/g, '\n');

// 1. Raise oppFloorCap from 68 -> 96 and set bleedSafeCap -> 0 so safeAt(g, q) is NEVER capped down to 68*L on bleeding targets!
code = code.replace('oppFloorCap: 68,', 'oppFloorCap: 96,');
code = code.replace('bleedSafeCap: 1,', 'bleedSafeCap: 0,');
code = code.replace('pulseFrac: 0.22,', 'pulseFrac: 0.16,');
code = code.replace('overPulseMode: 0,', 'overPulseMode: 1,');

// 2. Also in buyLand: when over (B > 100 * L) and attacking a person who is NOT nearCollapse (need > 0.35 * B), ALWAYS use pulseBlock (16%B) instead of dumping down to keep in one giant unretreatable wave!
const oldUsePulse = `      const usePulseBlock =
        P.pulseFrac > 0 && (!over || (P.overPulseMode > 0 && (o.nearCollapse || o.bleeding || avail < P.chunk * B)));`;

const newUsePulse = `      const usePulseBlock =
        P.pulseFrac > 0 && (!over || o.nearCollapse || o.bleeding || need > 0.32 * B || avail < P.chunk * B);`;

if (code.includes(oldUsePulse)) {
  code = code.replace(oldUsePulse, newUsePulse);
  console.log('Fixed usePulseBlock: never dump 50%~65% B in one unretreatable wave on a non-collapsing human (`need > 0.32 * B`)!');
}

fs.writeFileSync('v27-team-live.js', code, 'utf8');
