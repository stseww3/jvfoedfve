// params-diff.cjs — 比较几个版本的生效参数（params.cjs 的输出），列出值不同的键、只在某版本存在的键。
// 用法：node c136-review/agents/R05/scripts/params-diff.cjs <out 目录> c110 g09 c116
'use strict';
const fs = require('fs');
const path = require('path');
const dir = process.argv[2];
const vers = process.argv.slice(3);
const data = vers.map(v => JSON.parse(fs.readFileSync(path.join(dir, `params-raw-${v}.json`), 'utf8')));
const keys = new Set();
data.forEach(d => Object.keys(d.params).forEach(k => keys.add(k)));
const show = (x) => x === undefined ? '（无）' : JSON.stringify(x);
let same = 0;
const rows = [];
for (const k of [...keys].sort()) {
  const vals = data.map(d => d.params[k] ? d.params[k].value : undefined);
  const s = vals.map(show);
  if (s.every(x => x === s[0])) { same++; continue; }
  rows.push(`${k.padEnd(22)} ${vers.map((v, i) => `${v}=${s[i]}`).join('   ')}   定值层：${vers.map((v, i) => data[i].params[k] ? data[i].params[k].setBy : '-').join(' / ')}`);
}
console.log(`# params-diff  版本：${vers.join(' ')}  键总数=${keys.size}  三版取值全相同=${same}  有差异=${rows.length}`);
console.log(`# 各版本键数：${vers.map((v, i) => `${v}=${data[i].count}`).join(' ')}`);
rows.forEach(r => console.log(r));
