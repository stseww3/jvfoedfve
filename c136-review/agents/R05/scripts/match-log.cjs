// match-log.cjs — 把小队日志里的策略打印（[HL-…] 开头的句子）逐行对到策略源码里的打印语句上。
// 做法：logcalls.cjs 抽出的每条句式模板生成一个正则（${表达式} 换成通配），拿日志的每一行去配。
// 输出：每个标签在日志里出现多少行、每条源码句式配上多少行、配不上的行按标签给样例。
// 用法：node --expose-internals c136-review/agents/R05/scripts/match-log.cjs <版本文件名> [日志文件名=squad.log]
//   例：match-log.cjs g09.js      （G01~G09 那晚的日志对 917e6b1 的源码）
// 只统计 [HL-…] 标签的行，以及数据 README 点名的三个编排层标签（BACKEND-SPAWN-COORD / OPENING-CHECK / RESULT）的行数；
// 其他行（连接、编排层）不在 R05 范围内，只给一个总数。
'use strict';
const fs = require('fs');
const path = require('path');
const { execFileSync } = require('child_process');
const L = require('./jslib.cjs');

const ver = process.argv[2] || 'g09.js';
const logName = process.argv[3] || 'squad.log';
const calls = JSON.parse(execFileSync(process.execPath, ['--expose-internals', path.join(__dirname, 'logcalls.cjs'), ver, '--json'], { maxBuffer: 64 << 20 }).toString());

function esc(s) { return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'); }
function toRegex(template) {
  // 把 ${...}（可能嵌套括号）换成通配
  let re = '', i = 0;
  while (i < template.length) {
    if (template[i] === '$' && template[i + 1] === '{') {
      let depth = 0, j = i + 1;
      for (; j < template.length; j++) {
        if (template[j] === '{') depth++;
        else if (template[j] === '}') { depth--; if (depth === 0) break; }
      }
      re += '(.*?)';
      i = j + 1;
    } else { re += esc(template[i]); i++; }
  }
  return new RegExp('^' + re + '$');
}
const pats = calls.map((c, idx) => ({ idx, line: c.line, owner: c.owner, tag: c.tag, template: c.template, re: toRegex(c.template), n: 0, firstLine: null }));

const text = fs.readFileSync(path.join(L.SRC_DIR, logName), 'utf8');
const lines = text.split('\n');
const tagCount = new Map();
const unmatched = new Map(); // tag -> { n, samples }
const multi = [];
const readmeTags = [/^\[BACKEND-SPAWN-COORD\]/, /^\[OPENING-CHECK /, /^\[RESULT /];
const readmeNames = ['BACKEND-SPAWN-COORD', 'OPENING-CHECK', 'RESULT'];
const readmeCount = [0, 0, 0];
let other = 0, hl = 0;
for (let ln = 0; ln < lines.length; ln++) {
  const s = lines[ln];
  if (!s) continue;
  const k = s.indexOf('[HL-');
  if (k < 0) {
    let hit = false;
    for (let r = 0; r < readmeTags.length; r++) if (readmeTags[r].test(s)) { readmeCount[r]++; hit = true; break; }
    if (!hit) other++;
    continue;
  }
  hl++;
  const body = s.slice(k);
  const tag = /^\[(HL-[A-Z0-9-]+)/.exec(body);
  const tg = tag ? tag[1] : '?';
  tagCount.set(tg, (tagCount.get(tg) || 0) + 1);
  const hits = pats.filter(p => p.tag === tg && p.re.test(body));
  if (hits.length === 0) {
    const u = unmatched.get(tg) || { n: 0, samples: [] };
    u.n++;
    if (u.samples.length < 3) u.samples.push(`L${ln + 1}: ${body.slice(0, 260)}`);
    unmatched.set(tg, u);
  } else {
    // 多条句式同时配上时（例如同一句式在几个方法里各有一份），记到第一条上，并报告
    hits[0].n++;
    if (hits[0].firstLine === null) hits[0].firstLine = ln + 1;
    if (hits.length > 1 && multi.length < 5) multi.push(`L${ln + 1} 同时配上源码 ${hits.map(h => 'L' + h.line).join(',')}`);
  }
}

console.log(`# match-log  源码=${ver}  日志=${logName}  日志总行数=${lines.length - (lines[lines.length - 1] === '' ? 1 : 0)}`);
console.log(`[HL-…] 行数=${hl}  README 点名的编排层标签行数：${readmeNames.map((n, i) => `${n}=${readmeCount[i]}`).join(' ')}  其他行（连接/编排层，不在 R05 范围）=${other}`);
console.log('\n## 日志里每个 [HL-…] 标签的行数');
for (const [t, n] of [...tagCount.entries()].sort((a, b) => b[1] - a[1])) {
  const inSrc = pats.filter(p => p.tag === t).length;
  console.log(`${String(n).padStart(7)}  ${t}  源码里同标签打印语句=${inSrc}${inSrc === 0 ? '  （策略文件里没有，出自别处）' : ''}`);
}
console.log('\n## 源码里每条打印语句配上的日志行数');
for (const p of pats) {
  console.log(`${String(p.n).padStart(7)}  L${p.line} ${p.owner} [${p.tag}]${p.firstLine ? '  首次出现在日志第 ' + p.firstLine + ' 行' : ''}`);
  console.log(`         ${p.template.slice(0, 200)}`);
}
console.log('\n## 配不上任何源码句式的 [HL-…] 行');
if (unmatched.size === 0) console.log('（无）');
for (const [t, u] of unmatched) {
  console.log(`${String(u.n).padStart(7)}  ${t}`);
  for (const s of u.samples) console.log(`         ${s}`);
}
if (multi.length) { console.log('\n## 一行配上多条句式（前 5 例）'); multi.forEach(m => console.log('  ' + m)); }
