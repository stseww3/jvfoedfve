#!/usr/bin/env node
// jsindex.cjs — 给压缩过的游戏客户端代码建索引，并生成排版后的副本。
//
// 用法：NODE_PATH=/tmp/c136-r04/nodetools/node_modules node jsindex.cjs <live_game_js.js> <输出目录>
// 输出（都在 /tmp，不进分支）：
//   <输出目录>/live.pretty.js   prettier 3.9.10、printWidth 140 排版后的全文（行号只对这个版本有效）
//   <输出目录>/index.json       { sha256, bytes, ctors, globals }
//     ctors[名字]   = { start, end, members: { 名字: {start,end,kind} }, news: { 属性: 构造函数 } }
//     globals[变量] = 构造函数名（来自任意位置的 `变量 = new 构造函数()`）
//
// 「出处」的写法：<构造函数>.<成员> @<偏移>，例如 a5M.rD @146160。
// 偏移 = 原文件按 UTF-8 读成 JS 字符串后的下标（文件开头的字符串表里有非 ASCII 字符，
// 所以它比字节偏移略小），针对 sha256 固定的原文件，可用 jsfn.cjs 取出对应片段复核。
const fs = require('fs');
const crypto = require('crypto');
const path = require('path');
const acorn = require('acorn');
const walk = require('acorn-walk');
const prettier = require('prettier');

const [, , srcFile, outDir] = process.argv;
if (!srcFile || !outDir) {
  console.error('用法：node jsindex.cjs <live_game_js.js> <输出目录>');
  process.exit(2);
}
const src = fs.readFileSync(srcFile, 'utf8');
const sha256 = crypto.createHash('sha256').update(fs.readFileSync(srcFile)).digest('hex');
const ast = acorn.parse(src, { ecmaVersion: 'latest', sourceType: 'script' });

const ctors = {};
const globals = {};
const topFns = {};

function memberName(node) {
  if (node.type !== 'MemberExpression' || node.computed) return null;
  if (node.object.type !== 'ThisExpression') return null;
  return node.property.name;
}

for (const stmt of ast.body) {
  if (stmt.type !== 'FunctionDeclaration') continue;
  const name = stmt.id.name;
  const info = { start: stmt.start, end: stmt.end, members: {}, news: {} };
  // 只看构造函数体的直接语句和其中的赋值表达式（不进嵌套函数）
  walk.ancestor(stmt.body, {
    AssignmentExpression(node, _state, ancestors) {
      const inner = ancestors.filter((a) => a.type === 'FunctionExpression' || a.type === 'ArrowFunctionExpression' || a.type === 'FunctionDeclaration');
      const m = memberName(node.left);
      if (m && inner.length === 0) {
        const r = node.right;
        if (r.type === 'FunctionExpression' || r.type === 'ArrowFunctionExpression') {
          info.members[m] = { start: node.start, end: node.end, kind: 'fn' };
        } else if (r.type === 'NewExpression' && r.callee.type === 'Identifier') {
          info.news[m] = r.callee.name;
        } else if (!info.members[m]) {
          info.members[m] = { start: node.start, end: node.end, kind: 'val' };
        }
      }
    },
  });
  ctors[name] = info;
  topFns[name] = { start: stmt.start, end: stmt.end };
}

// 全局实例：任意位置的 `标识符 = new 构造函数(...)`
walk.simple(ast, {
  AssignmentExpression(node) {
    if (node.left.type === 'Identifier' && node.right.type === 'NewExpression' && node.right.callee.type === 'Identifier') {
      const g = node.left.name;
      const c = node.right.callee.name;
      if (ctors[c]) {
        if (!globals[g]) globals[g] = c;
        else if (globals[g] !== c) globals[g] = `${globals[g]}|${c}`;
      }
    }
  },
});

fs.mkdirSync(outDir, { recursive: true });
const index = { sha256, bytes: Buffer.byteLength(src), ctors, globals };
fs.writeFileSync(path.join(outDir, 'index.json'), JSON.stringify(index));

prettier
  .format(src, { parser: 'babel', printWidth: 140 })
  .then((out) => {
    fs.writeFileSync(path.join(outDir, 'live.pretty.js'), out);
    const nMembers = Object.values(ctors).reduce((s, c) => s + Object.keys(c.members).length, 0);
    console.log(`JSINDEX: sha256=${sha256} bytes=${index.bytes} ctors=${Object.keys(ctors).length} members=${nMembers} globals=${Object.keys(globals).length} prettyLines=${out.split('\n').length}`);
  })
  .catch((e) => {
    console.error('JSINDEX: ERROR', String(e).slice(0, 400));
    process.exit(2);
  });
