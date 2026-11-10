import fs from 'node:fs';

// 1. Fix SQUAD_SHORT_NAMES & [APEX] tag in spawn-coordinator.mjs + restrict voronoi=500 fallback to main continent
let sc = fs.readFileSync('spawn-coordinator.mjs', 'utf8').replace(/\r\n/g, '\n');

const oldSet = `'lucas94', 'dave_w', 'mark07', 'kevin_k', 'ethan21', 'ryan_m', 'noah88', 'leo_tx',`;
const newSet = `'lucas94', 'dave_w', 'mark07', 'kevin_k', 'ethan21', 'ryan_m', 'noah88', 'leo_tx', 'alex_k', 'zero_7', 'kaito9', 'riku_x', 'sora_w', 'zexos1', 'talon5',`;
if (sc.includes(oldSet)) sc = sc.replace(oldSet, newSet);

const oldIsSquad = `export function isSquadBotName(raw) {
  const s = stripClanTag(raw);
  return SQUAD_SHORT_NAMES.has(s);
}`;
const newIsSquad = `export function isSquadBotName(raw) {
  const norm = normalizePlayerName(raw).toUpperCase();
  if (norm.includes('[APEX]') || norm.includes('[NOPE]') || norm.includes('[NPL]')) return true;
  const s = stripClanTag(raw);
  return SQUAD_SHORT_NAMES.has(s);
}`;
if (sc.includes(oldIsSquad)) sc = sc.replace(oldIsSquad, newIsSquad);

// Also in fallback loop (around line 1045), require this.compSize[c] >= minViableCompSize so fallback NEVER picks tiny islands!
sc = sc.replace(
  'for (let x = 16; x < W - 16; x += 8) {\n            const c = y * W + x;\n            if (!landMask[c]) continue;',
  'for (let x = 16; x < W - 16; x += 8) {\n            const c = y * W + x;\n            if (!landMask[c] || this.compSize[c] < minViableCompSize) continue;'
);

fs.writeFileSync('spawn-coordinator.mjs', sc, 'utf8');
console.log('Fixed SQUAD_SHORT_NAMES & [APEX] recognition in spawn-coordinator.mjs!');

// 2. Fix v27-team-live.js:
// - Donor g.terr[me] >= 2500 (never let a 1px dying bot donate 9 troops and wasterecipient's ao.iD quota!)
// - Frontline Lead-Closing Lock: when L >= 22,000 and humanNbCount >= 1, keep >= Math.max(keep, Math.min(safe, 88 * L)) so a 35k~50k #1 carry NEVER drops below d=88!
let v27 = fs.readFileSync('v27-team-live.js', 'utf8').replace(/\r\n/g, '\n');

v27 = v27.replace(
  'if (g.t < 400 || g.t - (this.lastDonateTick ?? -999) < 18) return false;',
  'if (g.t < 400 || g.terr[me] < 2500 || g.bal[me] < 45000 || g.t - (this.lastDonateTick ?? -999) < 22) return false;'
);

const oldKeepBlock = `      keep = Math.max(keep, safe);

      const avail = B - fee - keep;`;

const newKeepBlock = `      keep = Math.max(keep, safe);
      if (person && !o.nearCollapse && L >= 22000 && humanNbCount >= 1) {
        keep = Math.max(keep, Math.min(safe, 88 * L));
      }

      const avail = B - fee - keep;`;

if (v27.includes(oldKeepBlock)) {
  v27 = v27.replace(oldKeepBlock, newKeepBlock);
  console.log('Added Lead-Closing 88*L Frontline Lock & 2500px Donor Floor to v27-team-live.js!');
}

fs.writeFileSync('v27-team-live.js', v27, 'utf8');
