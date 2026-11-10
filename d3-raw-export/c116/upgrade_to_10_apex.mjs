import fs from 'node:fs';

// 1. Update tsb-apex-squad.mjs to 10 fresh [APEX] bots on dedicated SOCKS5 ports 10821..10830
let sq = fs.readFileSync('tsb-apex-squad.mjs', 'utf8').replace(/\r\n/g, '\n');

const oldHeadless = sq.slice(sq.indexOf('const HEADLESS_BOTS = ['), sq.indexOf('];', sq.indexOf('const HEADLESS_BOTS = [')) + 2);

const newHeadless10 = `const HEADLESS_BOTS = [
  { port: 9310, socksPort: 10821, donorChromePort: 9228, name: '[APEX] ryan_m', slot: 0, id: '', pw: '' },
  { port: 9311, socksPort: 10822, donorChromePort: 9228, name: '[APEX] noah88', slot: 1, id: '', pw: '' },
  { port: 9312, socksPort: 10823, donorChromePort: 9228, name: '[APEX] leo_tx', slot: 2, id: '', pw: '' },
  { port: 9313, socksPort: 10824, donorChromePort: 9228, name: '[APEX] alex_k', slot: 3, id: '', pw: '' },
  { port: 9314, socksPort: 10825, donorChromePort: 9228, name: '[APEX] zero_7', slot: 4, id: '', pw: '' },
  { port: 9315, socksPort: 10826, donorChromePort: 9228, name: '[APEX] kaito9', slot: 5, id: '', pw: '' },
  { port: 9316, socksPort: 10827, donorChromePort: 9228, name: '[APEX] riku_x', slot: 6, id: '', pw: '' },
  { port: 9317, socksPort: 10828, donorChromePort: 9228, name: '[APEX] sora_w', slot: 7, id: '', pw: '' },
  { port: 9318, socksPort: 10829, donorChromePort: 9228, name: '[APEX] zexos1', slot: 8, id: '', pw: '' },
  { port: 9319, socksPort: 10830, donorChromePort: 9228, name: '[APEX] talon5', slot: 9, id: '', pw: '' },
];`;

sq = sq.replace(oldHeadless, newHeadless10);

// For 10 bots, allow ready when all 10 are in Room 0 (or >= 8 when startsIn <= 12)
sq = sq.replace(
  'headlessInRoom0 === HEADLESS_BOTS.length || (headlessInRoom0 >= HEADLESS_BOTS.length - 1 && minStartsIn <= 10)',
  'headlessInRoom0 === HEADLESS_BOTS.length || (headlessInRoom0 >= HEADLESS_BOTS.length - 2 && minStartsIn <= 12)'
);

fs.writeFileSync('tsb-apex-squad.mjs', sq, 'utf8');
console.log('Scaled tsb-apex-squad.mjs to 10 fresh [APEX] bots on ports 10821..10830!');

// 2. Update v27-team-live.js: slot = mySquadIdx % 10 and recognize zexos1 / talon5
let v27 = fs.readFileSync('v27-team-live.js', 'utf8').replace(/\r\n/g, '\n');
v27 = v27.replace('const slot = mySquadIdx % 8;', 'const slot = mySquadIdx % 10;');
v27 = v27.replace('const squadCount = Math.max(5, squadIds.length);', 'const squadCount = Math.max(10, squadIds.length);');
v27 = v27.replace(
  'low === "alex_k" || low === "zero_7"',
  'low === "alex_k" || low === "zero_7" || low === "kaito9" || low === "riku_x" || low === "sora_w" || low === "zexos1" || low === "talon5"'
);
fs.writeFileSync('v27-team-live.js', v27, 'utf8');
console.log('Updated v27-team-live.js for 10 [APEX] bots!');
