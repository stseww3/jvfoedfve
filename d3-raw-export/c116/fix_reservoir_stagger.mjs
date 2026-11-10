import fs from 'node:fs';

let code = fs.readFileSync('v27-team-live.js', 'utf8').replace(/\r\n/g, '\n');

// 1. Lower minimum donor territory from 2500 -> 1200 so a 2283px boxed-in reservoir like riku_x NEVER rots at d=148!
code = code.replace(
  'if (g.t < 1500 || g.terr[me] < 2500 || g.bal[me] < 50000 || g.t - (this.lastDonateTick ?? -999) < 16) return false;',
  'if (g.t < 1500 || g.terr[me] < 1200 || g.bal[me] < 30000 || g.t - (this.lastDonateTick ?? -999) < 12) return false;'
);

// 2. When a donor actually dispatches (`g.donate(pct, bestTarget, me)`), record `window.__lastSquadDonateTo = { target: bestTarget, tick: g.t }` on `window` (and in shared memory if same worker, or stagger by slot `g.t % 10 === (window.__tsbSquadSlot ?? 0) % 5 * 2`) so 4 boxed-in reservoirs NEVER fire on the exact same tick `t=2490` into the same target and waste 2 of 4 donations on the 2-per-500-tick `ao.iD` anti-feeding cap!
const oldGate = 'if (g.t < 1500 || g.terr[me] < 1200 || g.bal[me] < 30000 || g.t - (this.lastDonateTick ?? -999) < 12) return false;';
const newGate = `if (g.t < 1500 || g.terr[me] < 1200 || g.bal[me] < 30000 || g.t - (this.lastDonateTick ?? -999) < 12) return false;
    const mySlot = typeof window !== "undefined" && Number.isInteger(window.__tsbSquadSlot) ? window.__tsbSquadSlot : (me % 10);
    if (!emergencyOnly && ((g.t / 5) | 0) % 5 !== (mySlot % 5)) return false;`;

if (code.includes(oldGate)) {
  code = code.replace(oldGate, newGate);
  console.log('Added slot-staggered dispatch cadence (`((g.t / 5) | 0) % 5 === mySlot % 5`) so 5 inner reservoirs never collide on the same tick and waste ao.iD quota!');
}

fs.writeFileSync('v27-team-live.js', code, 'utf8');
