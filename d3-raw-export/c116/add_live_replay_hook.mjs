import fs from 'node:fs';

let code = fs.readFileSync('v27-team-live.js', 'utf8').replace(/\r\n/g, '\n');

const hookBlock = `
if (typeof window !== "undefined" && typeof window.__fx === "object" && window.__fx?.strategyBot && !window.__fx.strategyBot.__hookedReplayLog) {
  window.__fx.strategyBot.__hookedReplayLog = true;
  const origReplay = window.__fx.strategyBot.replay ? window.__fx.strategyBot.replay.bind(window.__fx.strategyBot) : null;
  window.__fx.strategyBot.replay = function(text) {
    try {
      if (typeof text === "string" && text.length > 50 && window.__hlLog) {
        const prefix = text.indexOf("=") >= 0 ? text : ("https://territorial.io/?replay=" + text);
        window.__hlLog("[HL-REPLAY-RAW] " + prefix);
      }
    } catch {}
    if (origReplay) return origReplay(text);
  };
}
`;

if (!code.includes('__hookedReplayLog')) {
  code = code + '\n' + hookBlock;
  fs.writeFileSync('v27-team-live.js', code, 'utf8');
  console.log('Successfully appended live [HL-REPLAY-RAW] hook to v27-team-live.js!');
} else {
  console.log('Already appended!');
}
