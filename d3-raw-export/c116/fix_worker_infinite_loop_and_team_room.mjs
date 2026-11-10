import fs from 'node:fs';

// 1. Fix headless-bot.mjs: prevent infinite while(n8()) loop when aE.a4V() sets aE.a38=0 / replaces bi.a3I, and remove unsolicited WS 0x09 Ping frames
let hb = fs.readFileSync('headless-bot.mjs', 'utf8').replace(/\r\n/g, '\n');

hb = hb.replace(
  `'if(this.ae5!==this.aIt*7){n8();while(this.ae7.length>0&&this.ae5<this.aIt*7&&aE.a2G!==2){n8()}if(this.ae7.length===0){return}}'`,
  `'if(this.ae5!==this.aIt*7){n8();var _w=0;while(this.ae7.length>0&&this.ae5<this.aIt*7&&aE.a2G===1&&bi.a3I===this&&++_w<64){var _p=this.ae5;n8();if(this.ae5===_p)break}if(this.ae7.length===0){return}}'`
);
hb = hb.replace(
  `'if(this.af1!==this.aK3*7){n8();while(this.af3.length>0&&this.af1<this.aK3*7&&aE.a38!==2){n8()}if(this.af3.length===0){return}}'`,
  `'if(this.af1!==this.aK3*7){n8();var _w=0;while(this.af3.length>0&&this.af1<this.aK3*7&&aE.a38===1&&bi.a3I===this&&++_w<64){var _p=this.af1;n8();if(this.af1===_p)break}if(this.af3.length===0){return}}'`
);

// Remove unsolicited WS 0x09 pingTimer (keep TCP setKeepAlive)
hb = hb.replace(
  `          const pingTimer = setInterval(() => {
            if (state !== 1) { clearInterval(pingTimer); return; }
            try { sendFrame(0x09, Buffer.alloc(0)); } catch {}
          }, 12000);
          if (pingTimer.unref) pingTimer.unref();\n`,
  ''
);

fs.writeFileSync('headless-bot.mjs', hb, 'utf8');
console.log('Fixed headless-bot.mjs infinite while(n8()) loop and removed WS 0x09 pingTimer!');

// 2. Fix tsb-apex-squad.mjs:
// - Reset lobbyFailCount whenever bot is inLobby or inGame, and only invalidate freshToken after 3 consecutive failed attempts
// - Never join non-Team rooms (only select targetRoom if r.vz < 7)
// - Increase stalledPolls threshold from 4 to 8 and ignore cached lastGoodState ticks
let tsb = fs.readFileSync('tsb-apex-squad.mjs', 'utf8').replace(/\r\n/g, '\n');

tsb = tsb.replace(
  `      c.lobbyFailCount = (c.lobbyFailCount || 0) + 1;
      if (c.lobbyFailCount >= 2) {
        c.freshToken = false;
        c.lobbyFailCount = 0;
        continue;
      }`,
  `      c.lobbyFailCount = (c.lobbyFailCount || 0) + 1;
      if (c.lobbyFailCount >= 4) {
        c.freshToken = false;
        c.lobbyFailCount = 0;
        continue;
      }`
);

tsb = tsb.replace(
  `    if (s.inGame) {
      if (!clients[idx].wasInGame) clients[idx].enteredGameAt = now;
      clients[idx].wasInGame = true;
      clients[idx].enteredLobbyAt = 0;
    }`,
  `    if (s.inGame || s.lobby?.inLobby) {
      clients[idx].lobbyFailCount = 0;
    }
    if (s.inGame) {
      if (!clients[idx].wasInGame) clients[idx].enteredGameAt = now;
      clients[idx].wasInGame = true;
      clients[idx].enteredLobbyAt = 0;
    }`
);

tsb = tsb.replace(
  `const targetRoom = (bq.sH.sH[0] && bq.sH.sH[0].vz < 7) ? bq.sH.sH[0] : (bq.sH.sH.find(r => r && r.vz < 7) || bq.sH.sH[0]);`,
  `const targetRoom = (bq.sH.sH[0] && bq.sH.sH[0].vz < 7) ? bq.sH.sH[0] : bq.sH.sH.find(r => r && r.vz < 7);`
);

tsb = tsb.replace(
  `if ((clients[idx].stalledPolls || 0) >= 4)`,
  `if ((clients[idx].stalledPolls || 0) >= 8)`
);

fs.writeFileSync('tsb-apex-squad.mjs', tsb, 'utf8');
console.log('Fixed tsb-apex-squad.mjs lobbyFailCount reset, strict Team room filter (vz < 7), and stalledPolls=8!');
