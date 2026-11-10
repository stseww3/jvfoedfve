import fs from 'node:fs';

let code = fs.readFileSync('v27-team-live.js', 'utf8').replace(/\r\n/g, '\n');

const oldSnap = `if (typeof window !== "undefined" && typeof bC === "object" && bC?.a7s?.a2b && window.__hlLog && window.__lastSnapTick !== (typeof bi === "object" && bi?.kr ? bi.kr() : -1)) {
  const curT = typeof bi === "object" && bi?.kr ? bi.kr() : -1;
  if (curT >= 5500 && !window.__dumpedReplay6000) {
    window.__dumpedReplay6000 = true;
    try {
      const repStr = bC.a7s.a2b();
      if (typeof repStr === "string" && repStr.length > 100) {
        const fullUrl = repStr.indexOf("=") >= 0 ? repStr : ("https://territorial.io/?replay=" + repStr);
        window.__hlLog("[HL-LIVE-REPLAY-URL] " + fullUrl);
      }
    } catch (e) {
      window.__hlLog("[HL-LIVE-REPLAY-ERR] " + (e?.message || e));
    }
  }
}`;

const newSnap = `if (typeof window !== "undefined" && typeof bC === "object" && bC?.a7s?.a2b && window.__hlLog && window.__tsbSquadSlot === 2) {
  const curT = typeof bi === "object" && bi?.kr ? bi.kr() : -1;
  if (curT < 500) window.__lastReplayDumpTick = 0;
  if (curT >= 4500 && curT - (window.__lastReplayDumpTick || 0) >= 1500) {
    window.__lastReplayDumpTick = curT;
    try {
      const repStr = bC.a7s.a2b();
      if (typeof repStr === "string" && repStr.length > 100) {
        const fullUrl = repStr.indexOf("=") >= 0 ? repStr : ("https://territorial.io/?replay=" + repStr);
        window.__hlLog("[HL-LIVE-REPLAY-URL] " + fullUrl);
      }
    } catch {}
  }
}`;

if (code.includes(oldSnap)) {
  code = code.replace(oldSnap, newSnap);
  fs.writeFileSync('v27-team-live.js', code, 'utf8');
  console.log('Updated v27-team-live.js to auto-dump full replay URL every 1500 ticks after t=4500 across all matches!');
}
