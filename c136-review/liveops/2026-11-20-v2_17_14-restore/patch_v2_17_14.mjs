import fs from 'node:fs';
import path from 'node:path';

const targetJs = path.resolve(process.argv[2] || '../c116/live_game_js.js');
const bakJs = `${targetJs}.bak-1774-20261120`;

const src = fs.readFileSync(targetJs, 'utf8');
const oldVer = 'this.dw=2;this.dx=1774;this.dy=0;var dz=2;var e0=17;var e1=13;this.rVersion=26;';
const newVer = 'this.dw=2;this.dx=1775;this.dy=0;var dz=2;var e0=17;var e1=14;this.rVersion=26;';

if (src.includes(newVer)) {
  console.log('Already on v2.17.14 (dx=1775):', targetJs);
  process.exit(0);
}
if (!src.includes(oldVer)) {
  throw new Error('Expected v2.17.13 (dx=1774) version signature not found in ' + targetJs);
}

if (!fs.existsSync(bakJs)) {
  fs.copyFileSync(targetJs, bakJs);
}
const patched = src.replace(oldVer, newVer);
fs.writeFileSync(targetJs, patched, 'utf8');
console.log('Patched', targetJs, 'to v2.17.14 (dx=1775), len=', patched.length);
