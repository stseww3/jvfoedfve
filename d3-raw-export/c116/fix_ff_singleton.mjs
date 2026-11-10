import fs from 'node:fs';

let tsb = fs.readFileSync('tsb-apex-squad.mjs', 'utf8').replace(/\r\n/g, '\n');

const oldEnsure = `let firefoxDonor = null;

async function ensureFirefoxDonor(port = 9228) {
  if (firefoxDonor && firefoxDonor.ws && firefoxDonor.ws.readyState === 1 && firefoxDonor.ctx) {
    return firefoxDonor;
  }`;

const newEnsure = `let firefoxDonor = null;
let firefoxDonorInitPromise = null;

async function ensureFirefoxDonor(port = 9228) {
  if (firefoxDonor && firefoxDonor.ws && firefoxDonor.ws.readyState === 1 && firefoxDonor.ctx) {
    return firefoxDonor;
  }
  if (firefoxDonorInitPromise) return firefoxDonorInitPromise;
  firefoxDonorInitPromise = _initFirefoxDonor(port).finally(() => { firefoxDonorInitPromise = null; });
  return firefoxDonorInitPromise;
}

async function _initFirefoxDonor(port = 9228) {`;

if (!tsb.includes(oldEnsure)) {
  console.error('Could not find oldEnsure in tsb-apex-squad.mjs!');
  process.exit(1);
}
tsb = tsb.replace(oldEnsure, newEnsure);
fs.writeFileSync('tsb-apex-squad.mjs', tsb, 'utf8');
console.log('Added singleton firefoxDonorInitPromise lock to ensureFirefoxDonor!');
