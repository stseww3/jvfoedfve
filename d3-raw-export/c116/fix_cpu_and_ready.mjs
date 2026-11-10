import fs from 'node:fs';
import path from 'node:path';

// 1. Patch c116/headless-bot.mjs: throttle requestAnimationFrame when not in active game (aE.a38 !== 1) so 10 workers use <1% CPU in lobby
let hb = fs.readFileSync('headless-bot.mjs', 'utf8').replace(/\r\n/g, '\n');

const oldRaf = `  const rafs = [];
  setInterval(() => {
    const batch = rafs.splice(0, rafs.length);
    const now = performance.now();
    for (const fn of batch) {
      try { fn(now); } catch {}
    }
  }, 16);`;

const newRaf = `  const rafs = [];
  let lastRafRun = 0;
  setInterval(() => {
    const now = performance.now();
    const inActiveGame = (typeof sandbox === 'object' && (sandbox.aE?.a38 === 1 || sandbox.aE?.a2G === 1));
    if (!inActiveGame && now - lastRafRun < 120) return;
    lastRafRun = now;
    const batch = rafs.splice(0, rafs.length);
    for (const fn of batch) {
      try { fn(now); } catch {}
    }
  }, 20);`;

if (hb.includes(oldRaf)) {
  hb = hb.replace(oldRaf, newRaf);
  fs.writeFileSync('headless-bot.mjs', hb, 'utf8');
  console.log('Throttled idle requestAnimationFrame in c116/headless-bot.mjs!');
}

// 2. Also patch c110/headless-bot.mjs if it exists so c110 never hits the while(n8()) 100% CPU infinite loop!
const c110HbPath = 'C:\\Users\\workstation\\Desktop\\远程\\workspaces\\c110\\headless-bot.mjs';
if (fs.existsSync(c110HbPath)) {
  let hb110 = fs.readFileSync(c110HbPath, 'utf8').replace(/\r\n/g, '\n');
  hb110 = hb110.replace(
    `'if(this.ae5!==this.aIt*7){n8();while(this.ae7.length>0&&this.ae5<this.aIt*7&&aE.a2G!==2){n8()}if(this.ae7.length===0){return}}'`,
    `'if(this.ae5!==this.aIt*7){n8();var _w=0;while(this.ae7.length>0&&this.ae5<this.aIt*7&&aE.a2G===1&&bi.a3I===this&&++_w<64){var _p=this.ae5;n8();if(this.ae5===_p)break}if(this.ae7.length===0){return}}'`
  );
  hb110 = hb110.replace(
    `'if(this.af1!==this.aK3*7){n8();while(this.af3.length>0&&this.af1<this.aK3*7&&aE.a38!==2){n8()}if(this.af3.length===0){return}}'`,
    `'if(this.af1!==this.aK3*7){n8();var _w=0;while(this.af3.length>0&&this.af1<this.aK3*7&&aE.a38===1&&bi.a3I===this&&++_w<64){var _p=this.af1;n8();if(this.af1===_p)break}if(this.af3.length===0){return}}'`
  );
  if (hb110.includes(oldRaf)) {
    hb110 = hb110.replace(oldRaf, newRaf);
  }
  fs.writeFileSync(c110HbPath, hb110, 'utf8');
  console.log('Patched c110/headless-bot.mjs while(n8()) infinite loop & idle RAF throttle!');
}

// 3. Fix targetRoom selection in c116/tsb-apex-squad.mjs so Room 0 always selects the Team room
let tsb = fs.readFileSync('tsb-apex-squad.mjs', 'utf8').replace(/\r\n/g, '\n');
tsb = tsb.replace(
  `const targetRoom = (bq.sH.sH[0] && bq.sH.sH[0].vz < 7) ? bq.sH.sH[0] : bq.sH.sH.find(r => r && r.vz < 7);`,
  `const targetRoom = (bq.sH.sH[0] && bq.sH.sH[0].vz < 7) ? bq.sH.sH[0] : (bq.sH.sH.find(r => r && r.vz < 7) || bq.sH.sH[0]);`
);
fs.writeFileSync('tsb-apex-squad.mjs', tsb, 'utf8');
console.log('Restored targetRoom fallback in c116/tsb-apex-squad.mjs!');
