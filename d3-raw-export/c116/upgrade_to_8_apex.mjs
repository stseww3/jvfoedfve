import fs from 'node:fs';

// 1. Upgrade tsb-apex-squad.mjs to 8 [APEX] bots!
let sq = fs.readFileSync('tsb-apex-squad.mjs', 'utf8').replace(/\r\n/g, '\n');

const oldHeadless5 = `const HEADLESS_BOTS = [
  { port: 9310, socksPort: 10801, donorChromePort: 9228, name: '[APEX] ryan_m', slot: 0, id: '', pw: '' },
  { port: 9311, socksPort: 10802, donorChromePort: 9228, name: '[APEX] noah88', slot: 1, id: '', pw: '' },
  { port: 9312, socksPort: 10803, donorChromePort: 9228, name: '[APEX] leo_tx', slot: 2, id: '', pw: '' },
  { port: 9313, socksPort: 10804, donorChromePort: 9228, name: '[APEX] alex_k', slot: 3, id: '', pw: '' },
  { port: 9314, socksPort: 10805, donorChromePort: 9228, name: '[APEX] zero_7', slot: 4, id: '', pw: '' },
];`;

const newHeadless8 = `const HEADLESS_BOTS = [
  { port: 9310, socksPort: 10801, donorChromePort: 9228, name: '[APEX] ryan_m', slot: 0, id: '', pw: '' },
  { port: 9311, socksPort: 10802, donorChromePort: 9228, name: '[APEX] noah88', slot: 1, id: '', pw: '' },
  { port: 9312, socksPort: 10803, donorChromePort: 9228, name: '[APEX] leo_tx', slot: 2, id: '', pw: '' },
  { port: 9313, socksPort: 10804, donorChromePort: 9228, name: '[APEX] alex_k', slot: 3, id: '', pw: '' },
  { port: 9314, socksPort: 10805, donorChromePort: 9228, name: '[APEX] zero_7', slot: 4, id: '', pw: '' },
  { port: 9315, socksPort: 10801, donorChromePort: 9228, name: '[APEX] kaito9', slot: 5, id: '', pw: '' },
  { port: 9316, socksPort: 10802, donorChromePort: 9228, name: '[APEX] riku_x', slot: 6, id: '', pw: '' },
  { port: 9317, socksPort: 10803, donorChromePort: 9228, name: '[APEX] sora_w', slot: 7, id: '', pw: '' },
];`;

if (sq.includes(oldHeadless5)) {
  sq = sq.replace(oldHeadless5, newHeadless8);
  fs.writeFileSync('tsb-apex-squad.mjs', sq, 'utf8');
  console.log('Scaled tsb-apex-squad.mjs to 8 [APEX] bots!');
}

// 2. Fix v27-team-live.js:
// - slot = mySquadIdx % 8 (instead of % 5)
// - remove dMe>=132 -> keep=108*L suicide override so frontline bots never attack into stronger neighbors at d=132!
let v27 = fs.readFileSync('v27-team-live.js', 'utf8').replace(/\r\n/g, '\n');

v27 = v27.replace('const slot = mySquadIdx % 5;', 'const slot = mySquadIdx % 8;');

const oldOverPulse = `      keep = Math.max(keep, safe);
      if (dMe >= 132) {
        keep = Math.min(keep, 108 * L);
      }

      const avail = B - fee - keep;
      if (avail <= 0) continue;

      if (!person) {
        const want = 1.25 * need + 3 * this.cnt[q];
        const x = Math.min(avail, want);
        if (x <= 0 || (x < want && x < P.chunk * B)) continue;
        return this.send(g, q, x);
      }

      const usePulseBlock =
        P.pulseFrac > 0 && (!over || dMe >= 132 || (P.overPulseMode > 0 && (o.nearCollapse || o.bleeding || avail < P.chunk * B)));`;

const newOverPulse = `      keep = Math.max(keep, safe);

      const avail = B - fee - keep;
      if (avail <= 0) continue;

      if (!person) {
        const want = 1.25 * need + 3 * this.cnt[q];
        const x = Math.min(avail, want);
        if (x <= 0 || (x < want && x < P.chunk * B)) continue;
        return this.send(g, q, x);
      }

      const usePulseBlock =
        P.pulseFrac > 0 && (!over || (P.overPulseMode > 0 && (o.nearCollapse || o.bleeding || avail < P.chunk * B)));`;

if (v27.includes(oldOverPulse)) {
  v27 = v27.replace(oldOverPulse, newOverPulse);
  console.log('Restored pure v27 safeAt defense floor (removed dMe>=132 keep=108*L suicide override)!');
}

fs.writeFileSync('v27-team-live.js', v27, 'utf8');
