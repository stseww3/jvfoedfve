import fs from 'node:fs';

// 1. In headless-bot.mjs: run active game RAF at 16ms (60Hz) and idle lobby RAF at 80ms (12.5Hz) so page.js Se() updates info.tick every 500ms!
let hb = fs.readFileSync('headless-bot.mjs', 'utf8').replace(/\r\n/g, '\n');

const oldRafBlock = `  const rafs = [];
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

const newRafBlock = `  const rafs = [];
  let lastRafRun = 0;
  setInterval(() => {
    const now = performance.now();
    const inActiveGame = (typeof sandbox === 'object' && (sandbox.aE?.a38 === 1 || sandbox.aE?.a2G === 1));
    if (!inActiveGame && now - lastRafRun < 90) return;
    lastRafRun = now;
    const batch = rafs.splice(0, rafs.length);
    for (const fn of batch) {
      try { fn(now); } catch {}
    }
  }, 15);`;

if (hb.includes(oldRafBlock)) {
  hb = hb.replace(oldRafBlock, newRafBlock);
  fs.writeFileSync('headless-bot.mjs', hb, 'utf8');
  console.log('Updated headless-bot.mjs RAF interval to 15ms!');
}

// 2. In tsb-apex-squad.mjs: read real-time engine tick directly from bi.kr() instead of stale info.tick (which only updates every 500ms via Se()), so a running match NEVER gets false-positive killed by __stalledCount!
let tsb = fs.readFileSync('tsb-apex-squad.mjs', 'utf8').replace(/\r\n/g, '\n');

const oldTickBlock = `        s.spawnPhase = !!info?.spawnPhase;
        s.tick = info?.tick || 0;
        if (s.inGame) {
          if (s.tick > 0 && !s.spawnPhase && window.__lastObsTick === s.tick) {
            window.__stalledCount = (window.__stalledCount || 0) + 1;
          } else {
            window.__lastObsTick = s.tick;
            window.__stalledCount = 0;
          }
          if ((window.__stalledCount || 0) >= 6 && g && g[d.sbLeave]) {
            window.__stalledCount = 0;
            g[d.sbLeave](true);
            s.inGame = false;
          }
        } else {
          window.__stalledCount = 0;
        }`;

const newTickBlock = `        const liveTick = (d && d.sbTickHolder && d.sbGetTick && window[d.sbTickHolder]?.[d.sbGetTick]) ? (window[d.sbTickHolder][d.sbGetTick]() | 0) : (info?.tick || 0);
        s.spawnPhase = !!(g && g[d.gameState] === 1 && g[d.gSelectableSpawn]);
        s.tick = liveTick || info?.tick || 0;
        if (s.inGame) {
          if (s.tick > 0 && !s.spawnPhase && window.__lastObsTick === s.tick) {
            window.__stalledCount = (window.__stalledCount || 0) + 1;
          } else {
            window.__lastObsTick = s.tick;
            window.__stalledCount = 0;
          }
          if ((window.__stalledCount || 0) >= 12 && g && g[d.sbLeave]) {
            window.__stalledCount = 0;
            g[d.sbLeave](true);
            s.inGame = false;
          }
        } else {
          window.__stalledCount = 0;
        }`;

if (!tsb.includes(oldTickBlock)) {
  console.error('Could not find oldTickBlock in tsb-apex-squad.mjs!');
  process.exit(1);
}
tsb = tsb.replace(oldTickBlock, newTickBlock);
fs.writeFileSync('tsb-apex-squad.mjs', tsb, 'utf8');
console.log('Successfully fixed liveTick (bi.kr()) reading in tsb-apex-squad.mjs so running bots are NEVER false-positive killed by __stalledCount!');
