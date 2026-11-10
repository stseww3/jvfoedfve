import fs from 'node:fs';

let code = fs.readFileSync('v27-team-live.js', 'utf8').replace(/\r\n/g, '\n');

const liveSnapBlock = `
if (typeof window !== "undefined" && typeof bC === "object" && bC?.a7s?.a2b && window.__hlLog && window.__lastSnapTick !== (typeof bi === "object" && bi?.kr ? bi.kr() : -1)) {
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
}
`;

if (!code.includes('__dumpedReplay6000')) {
  code = code + '\n' + liveSnapBlock;
  fs.writeFileSync('v27-team-live.js', code, 'utf8');
  console.log('Appended live replay URL generator to v27-team-live.js!');
}
