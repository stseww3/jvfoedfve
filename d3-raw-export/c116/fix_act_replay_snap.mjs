import fs from 'node:fs';

let code = fs.readFileSync('v27-team-live.js', 'utf8').replace(/\r\n/g, '\n');

const target = `      window.__hlLog(\`[HL-TICK] t=\${g.t} terr=\${g.terr[me]}(\${(100 * g.terr[me] / Math.max(1, g.land)).toFixed(1)}%) bal=\${g.bal[me]} dens=\${(g.bal[me] / Math.max(1, g.terr[me])).toFixed(1)} nb=\${this.nb.length} neut=\${this.neutral} cmds=\${this.cmds} boats=\${this.boats}\${pfStr}\`);
    }`;

const replacement = `      window.__hlLog(\`[HL-TICK] t=\${g.t} terr=\${g.terr[me]}(\${(100 * g.terr[me] / Math.max(1, g.land)).toFixed(1)}%) bal=\${g.bal[me]} dens=\${(g.bal[me] / Math.max(1, g.terr[me])).toFixed(1)} nb=\${this.nb.length} neut=\${this.neutral} cmds=\${this.cmds} boats=\${this.boats}\${pfStr}\`);
      if (g.t >= 3960 && g.t - (window.__lastReplaySnapAt || 0) >= 1350 && typeof bC === "object" && bC?.a7s?.a2b) {
        let minAliveSquadId = me;
        for (let p = 0; p < g.humans; p++) {
          if (g.alive[p] && this.isTeammate(g, p) && this.isOurSquadBot(g, p) && p < minAliveSquadId) minAliveSquadId = p;
        }
        if (me === minAliveSquadId) {
          window.__lastReplaySnapAt = g.t;
          try {
            const repStr = bC.a7s.a2b();
            if (typeof repStr === "string" && repStr.length > 100) {
              const fullUrl = repStr.indexOf("=") >= 0 ? repStr : ("https://territorial.io/?replay=" + repStr);
              window.__hlLog("[HL-LIVE-REPLAY-URL] " + fullUrl);
            }
          } catch {}
        }
      }
    }`;

const lastIdx = code.lastIndexOf(target);
if (lastIdx === -1) {
  console.error('Could not find target in v27-team-live.js!');
  process.exit(1);
}
code = code.slice(0, lastIdx) + replacement + code.slice(lastIdx + target.length);
fs.writeFileSync('v27-team-live.js', code, 'utf8');
console.log('Successfully hooked [HL-LIVE-REPLAY-URL] directly inside Policy.prototype.act!');
