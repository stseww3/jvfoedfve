#!/usr/bin/env node
// engine-extract.mjs — 从压缩过的游戏客户端代码里按名字抽取函数并排版，给出原文件里的字节偏移。
// 只读工具：不修改、不执行引擎代码。
//
// 用法：
//   node engine-extract.mjs list [正则]            列出顶层函数（名字 @偏移+长度）和它的成员名
//   node engine-extract.mjs show <名字> [...]      排版输出。名字可以是顶层函数 gd，也可以是 类.成员，如 cd.aMi、a5M.gy
//   node engine-extract.mjs grep <正则> [范围正则]  在排版后的每个成员里搜，输出 类.成员:行内容（范围正则限定顶层函数名）
//   node engine-extract.mjs inst                    输出「全局变量 = new 类」的对照表（来自初始化函数）
//
// 环境变量：ENGINE（默认 /tmp/c136-r03/b/live_game_js.js），NM（node 依赖目录，默认 /tmp/c136-r03/nm）
// 先跑 fetch-inputs.sh 准备好输入。偏移以 sha256=2b5731c7…dcba6 的那份文件为准（脚本会校验并打印）。
import fs from 'node:fs';
import crypto from 'node:crypto';
import { createRequire } from 'node:module';

const ENGINE = process.env.ENGINE || '/tmp/c136-r03/b/live_game_js.js';
const NM = process.env.NM || '/tmp/c136-r03/nm';
const require = createRequire(NM.replace(/\/?$/, '/'));
const acorn = require('acorn');
const astring = require('astring');

export function loadEngine(file = ENGINE) {
  const src = fs.readFileSync(file, 'utf8');
  const sha = crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
  const ast = acorn.parse(src, { ecmaVersion: 'latest', sourceType: 'script' });
  const tops = new Map();
  ast.body.forEach((n, idx) => {
    if (n.type !== 'FunctionDeclaration') return;
    const members = new Map();
    for (const s of n.body.body) {
      if (s.type === 'FunctionDeclaration') members.set(s.id.name, s);
      else if (
        s.type === 'ExpressionStatement' && s.expression.type === 'AssignmentExpression' &&
        s.expression.left.type === 'MemberExpression' && s.expression.left.object.type === 'ThisExpression' &&
        !s.expression.left.computed
      ) {
        const r = s.expression.right;
        if (r.type === 'FunctionExpression') members.set(s.expression.left.property.name, s);
      }
    }
    tops.set(n.id.name, { node: n, idx, members });
  });
  return { src, sha, ast, tops };
}

export const pretty = (node) => astring.generate(node, { indent: '  ' });

export function resolve(eng, name) {
  const [a, b] = name.split('.');
  const t = eng.tops.get(a);
  if (!t) return null;
  if (!b) return { node: t.node, label: a };
  const m = t.members.get(b);
  if (!m) return null;
  return { node: m, label: `${a}.${b}` };
}

function main() {
  const [cmd, ...args] = process.argv.slice(2);
  const eng = loadEngine();
  const head = `// engine ${ENGINE} sha256=${eng.sha.slice(0, 16)}… bytes=${eng.src.length}`;
  if (cmd === 'list') {
    const re = args[0] ? new RegExp(args[0]) : null;
    console.log(head);
    for (const [name, t] of eng.tops) {
      if (re && !re.test(name)) continue;
      console.log(`${name} @${t.node.start}+${t.node.end - t.node.start}  [${[...t.members.keys()].join(' ')}]`);
    }
  } else if (cmd === 'show') {
    console.log(head);
    for (const name of args) {
      const r = resolve(eng, name);
      if (!r) {
        console.log(`// ${name}: NOT FOUND`);
        continue;
      }
      console.log(`// ---- ${r.label} @${r.node.start}+${r.node.end - r.node.start}`);
      console.log(pretty(r.node));
    }
  } else if (cmd === 'grep') {
    const re = new RegExp(args[0]);
    const scope = args[1] ? new RegExp(args[1]) : null;
    console.log(head);
    for (const [name, t] of eng.tops) {
      if (scope && !scope.test(name)) continue;
      const seen = new Set();
      const scan = (label, node) => {
        const lines = pretty(node).split('\n');
        lines.forEach((l, i) => {
          if (re.test(l)) console.log(`${label} @${node.start} L${i + 1}: ${l.trim()}`);
        });
      };
      for (const [mn, m] of t.members) {
        scan(`${name}.${mn}`, m);
        seen.add(m);
      }
      // 顶层函数体里不属于任何成员的语句
      for (const s of t.node.body.body) if (!seen.has(s)) scan(`${name}.<body>`, s);
    }
  } else if (cmd === 'inst') {
    console.log(head);
    const out = [];
    const walk = (n) => {
      if (!n || typeof n !== 'object') return;
      if (Array.isArray(n)) return n.forEach(walk);
      if (
        n.type === 'AssignmentExpression' && n.left.type === 'Identifier' &&
        n.right.type === 'NewExpression' && n.right.callee.type === 'Identifier' && n.right.arguments.length === 0
      ) out.push(`${n.left.name} = new ${n.right.callee.name}()`);
      for (const k in n) if (k !== 'type' && n[k] && typeof n[k] === 'object') walk(n[k]);
    };
    const bx = eng.tops.get('bx');
    walk(bx ? bx.node : eng.ast);
    console.log(out.join('\n'));
  } else {
    console.log('用法见文件开头注释');
    process.exit(1);
  }
}

if (process.argv[1] && fs.realpathSync(process.argv[1]) === fs.realpathSync(new URL(import.meta.url).pathname)) main();
