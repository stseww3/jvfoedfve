import fs from 'node:fs';

let hb = fs.readFileSync('headless-bot.mjs', 'utf8').replace(/\r\n/g, '\n');

const oldClose = `      if (msg.text.includes('socket close index 3') || msg.text.includes('socket close index 2')) {
        client.evalJs(\`(() => { const d = window.dictionary, g = d && window[d.game]; if (g && g[d.sbLeave] && g[d.gameState] !== 0) g[d.sbLeave](true); })()\`);
      }`;

const newClose = `      if (msg.text.includes('socket close index 3') || msg.text.includes('socket close index 2')) {
        const closedIdx = msg.text.includes('socket close index 3') ? 3 : 2;
        client.evalJs(\`(() => {
          const d = window.dictionary, g = d && window[d.game];
          const activeSockOpen = typeof b1 === "object" && b1?.z?.ef && (b1.z.ef(2) || b1.z.ef(3));
          if (!activeSockOpen && g && g[d.sbLeave] && g[d.gameState] !== 0) {
            g[d.sbLeave](true);
          }
        })()\`);
      }`;

if (hb.includes(oldClose)) {
  hb = hb.replace(oldClose, newClose);
  fs.writeFileSync('headless-bot.mjs', hb, 'utf8');
  console.log('Fixed delayed previous-match socket close bug in headless-bot.mjs!');
}
