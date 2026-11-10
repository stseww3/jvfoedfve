import fs from 'node:fs';

const html = fs.readFileSync('fresh_9225.html', 'utf8');
const live = fs.readFileSync('live_game_js.js', 'utf8');

console.log('=== LOCAL aWU + aXN ===');
const lWU = live.indexOf('function aWU()');
console.log(live.slice(lWU, lWU + 2200).replace(/\r?\n/g, ' '));

console.log('=== LOCAL aG1 ===');
const lG1 = live.indexOf('function aG1()');
console.log(live.slice(lG1, lG1 + 2500).replace(/\r?\n/g, ' '));

console.log('=== LOCAL aGf / select ===');
const lGf = live.indexOf('this.aGf=function()');
console.log(live.slice(lGf - 100, lGf + 1500).replace(/\r?\n/g, ' '));

console.log('=== LOCAL aFz ===');
const lFz = live.indexOf('function aFz()');
console.log(live.slice(lFz, lFz + 1500).replace(/\r?\n/g, ' '));

console.log('=== FRESH outgoing packet 4 (select room) ===');
for (const m of html.matchAll(/aHW\(4,/g)) {
  console.log(html.slice(m.index - 100, m.index + 300).replace(/\r?\n/g, ' '));
}
const iHW = html.indexOf('this.aHW=function(');
console.log(html.slice(iHW - 100, iHW + 1500).replace(/\r?\n/g, ' '));

console.log('=== LOCAL outgoing packet 4 (select room) ===');
for (const m of live.matchAll(/\.select=function\(/g)) {
  console.log(live.slice(m.index - 100, m.index + 400).replace(/\r?\n/g, ' '));
}
