import fs from 'node:fs';

let hb = fs.readFileSync('headless-bot.mjs', 'utf8').replace(/\r\n/g, '\n');

const oldErr = `      if (msg.text.includes('error 4591') || msg.text.includes('error 4215') || msg.text.includes('error 4577') || msg.text.includes('error 4229')) {
        client.freshToken = false;
        client.enteredLobbyAt = 0;
        if (msg.text.includes('error 4229')) {
          client.evalJs(\`(() => { const d = window.dictionary, g = d && window[d.game]; if (g && g[d.sbLeave] && g[d.gameState] !== 0) g[d.sbLeave](true); })()\`);
        }
      }`;

const newErr = `      if (msg.text.includes('error 4591') || msg.text.includes('error 4215') || msg.text.includes('error 4577') || msg.text.includes('error 4229')) {
        client.freshToken = false;
        client.enteredLobbyAt = 0;
        if (msg.text.includes('error 4577')) {
          client.evalJs(\`(() => {
            localStorage.setItem("d105", "");
            localStorage.setItem("d106", "");
            localStorage.setItem("v105", "0");
            localStorage.setItem("v106", "0");
            const setSetting = bm?.qq?.qr || bm?.qo?.qp;
            if (typeof bm === "object" && typeof setSetting === "function") {
              setSetting.call(bm.qq || bm.qo, 105, "");
              setSetting.call(bm.qq || bm.qo, 106, "");
            }
          })()\`);
        }
        if (msg.text.includes('error 4229')) {
          client.evalJs(\`(() => { const d = window.dictionary, g = d && window[d.game]; if (g && g[d.sbLeave] && g[d.gameState] !== 0) g[d.sbLeave](true); })()\`);
        }
      }`;

if (hb.includes(oldErr)) {
  hb = hb.replace(oldErr, newErr);
  fs.writeFileSync('headless-bot.mjs', hb, 'utf8');
  console.log('Fixed error 4577 in headless-bot.mjs: auto-clear d105/d106 account credentials to mint a fresh account!');
}
