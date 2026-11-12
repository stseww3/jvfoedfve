import fs from 'node:fs';
const lib = await import('/agent/repos/c136-data/src/sim/tools/c102-replay-lib.mjs');
for (const m of ['A058', 'B021', 'B023']) {
  const d = lib.decodeReplay(fs.readFileSync(`/agent/repos/c136-data/bundles/${m}/replay.txt`, 'utf8'));
  let iw = 0, multi = 0, asc = 0, desc = 0, mixed = 0, notMult7 = 0, cmdSteps = 0;
  const H = d.vu.humanCount; const jJ = H <= 2 ? 30 : H <= 50 ? 40 : 50;
  let unit = 0; const ex = [];
  for (let iv = 0; iv < d.ja.length; iv++) {
    const jZ = d.ja[iv];
    if (d.jY[iv]) {
      const cs = d.cmds.slice(iw, iw + jZ); iw += jZ;
      const tick = unit - (jJ + 1);
      if (tick >= 0) {
        cmdSteps++;
        if (tick % 7 !== 0) notMult7++;
        const ps = cs.map((c) => c.player);
        const groups = []; for (const p of ps) if (!groups.length || groups[groups.length - 1] !== p) groups.push(p);
        if (groups.length > 1) {
          multi++;
          const a = groups.every((p, i) => i === 0 || p > groups[i - 1]);
          const de = groups.every((p, i) => i === 0 || p < groups[i - 1]);
          if (a) asc++; else if (de) desc++; else { mixed++; if (ex.length < 6) ex.push(`${tick}:${ps.join(',')}`); }
        }
      }
      unit += 1;
    } else unit += jZ;
  }
  console.log(m, 'cmdSteps', cmdSteps, 'notMult7', notMult7, 'multiPlayerSteps', multi, 'asc', asc, 'desc', desc, 'mixed', mixed, ex.join(' | '));
}
