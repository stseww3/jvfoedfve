#!/usr/bin/env node
// engine-diff.mjs — 比较两份引擎代码（2.17.1 取证版 与 c136-data 镜像版），逐个「顶层函数.成员」比较排版后的源码，
// 列出有差异的成员和差异行。只读：不执行引擎代码。
//
// 用法：node engine-diff.mjs <旧文件> <新文件> [--full]
//   默认只列出有差异的成员名和差异行数；--full 连同差异行一起输出。
// 环境变量 NM：node 依赖目录（acorn、astring），默认 /tmp/c136-r03/nm
import { loadEngine, pretty } from './engine-extract.mjs';

const [oldFile, newFile, flag] = process.argv.slice(2);
if (!oldFile || !newFile) {
  console.log('用法：node engine-diff.mjs <旧文件> <新文件> [--full]');
  process.exit(1);
}
const A = loadEngine(oldFile);
const B = loadEngine(newFile);
console.log(`# engine-diff`);
console.log(`# old sha256=${A.sha} chars=${A.src.length} tops=${A.tops.size}`);
console.log(`# new sha256=${B.sha} chars=${B.src.length} tops=${B.tops.size}`);

function parts(t) {
  // 成员 → 源码；另把不属于任何成员的顶层语句拼成 <body>
  const m = new Map();
  const seen = new Set();
  for (const [name, node] of t.members) {
    m.set(name, pretty(node));
    seen.add(node);
  }
  const rest = t.node.body.body.filter((s) => !seen.has(s)).map(pretty).join('\n');
  m.set('<body>', rest);
  return m;
}

function lineDiff(a, b) {
  const la = a.split('\n');
  const lb = b.split('\n');
  const sa = new Map();
  const sb = new Map();
  for (const l of la) sa.set(l, (sa.get(l) || 0) + 1);
  for (const l of lb) sb.set(l, (sb.get(l) || 0) + 1);
  const minus = [];
  const plus = [];
  for (const [l, n] of sa) {
    const d = n - (sb.get(l) || 0);
    for (let i = 0; i < d; i++) minus.push(l.trim());
  }
  for (const [l, n] of sb) {
    const d = n - (sa.get(l) || 0);
    for (let i = 0; i < d; i++) plus.push(l.trim());
  }
  return { minus, plus };
}

let same = 0;
let diff = 0;
const onlyOld = [];
const onlyNew = [];
for (const [name, ta] of A.tops) {
  const tb = B.tops.get(name);
  if (!tb) {
    onlyOld.push(name);
    continue;
  }
  const pa = parts(ta);
  const pb = parts(tb);
  for (const [mn, sa] of pa) {
    const sb = pb.get(mn);
    if (sb === undefined) {
      console.log(`- ${name}.${mn}: 只在旧版`);
      diff++;
      continue;
    }
    if (sa === sb) {
      same++;
      continue;
    }
    diff++;
    const d = lineDiff(sa, sb);
    console.log(`* ${name}.${mn}: -${d.minus.length} +${d.plus.length}`);
    if (flag === '--full') {
      for (const l of d.minus.slice(0, 40)) console.log(`    - ${l.slice(0, 220)}`);
      for (const l of d.plus.slice(0, 40)) console.log(`    + ${l.slice(0, 220)}`);
    }
  }
  for (const mn of pb.keys()) {
    if (!pa.has(mn)) {
      console.log(`+ ${name}.${mn}: 只在新版`);
      diff++;
    }
  }
}
for (const name of B.tops.keys()) if (!A.tops.has(name)) onlyNew.push(name);
console.log(`# 相同成员 ${same}，有差异成员 ${diff}，只在旧版的顶层函数 ${onlyOld.length}，只在新版的顶层函数 ${onlyNew.length}`);
if (onlyOld.length) console.log(`# 只在旧版：${onlyOld.join(' ')}`);
if (onlyNew.length) console.log(`# 只在新版：${onlyNew.join(' ')}`);
