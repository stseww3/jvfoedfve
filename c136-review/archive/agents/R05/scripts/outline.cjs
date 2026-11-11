// outline.cjs — 打印一个策略文件的结构大纲：顶层声明、类、方法、命名的内部函数，带行号范围和行数。
// 用法：node --expose-internals c136-review/agents/R05/scripts/outline.cjs <文件名> [最小行数=1]
//   文件名相对 /tmp/c136-r05/src（由 fetch-src.sh 生成），例如 c110.js / c116.js / g09.js
'use strict';
const L = require('./jslib.cjs');
const name = process.argv[2] || 'c110.js';
const minLines = parseInt(process.argv[3] || '1', 10);
const { src, ast, repaired } = L.load(name);
const lines = src.split('\n').length;
console.log(`# outline ${name}  lines=${lines}  bytes=${Buffer.byteLength(src)}`);
if (repaired) console.log(`# TRUNCATED: 原文件在第 ${repaired.cutLine} 行之后被截断，丢弃残句 ${repaired.droppedBytes} 字节，补括号 "${repaired.closers}"（${repaired.error}）`);

function ln(n) { return `${n.loc.start.line}-${n.loc.end.line}`; }
function span(n) { return n.loc.end.line - n.loc.start.line + 1; }

function innerFns(node, depth, out) {
  // 列出 node 体内命名的函数（不跨进更深的类）
  (function rec(n, d) {
    if (!n || typeof n.type !== 'string') return;
    for (const k of Object.keys(n)) {
      if (k === 'parent' || k === 'loc' || k === 'range') continue;
      const v = n[k];
      const kids = Array.isArray(v) ? v : [v];
      for (const c of kids) {
        if (!c || typeof c.type !== 'string') continue;
        if (c.type === 'FunctionDeclaration' || c.type === 'FunctionExpression' || c.type === 'ArrowFunctionExpression') {
          const nm = L.fnName(c);
          if (nm !== '(anon)' && span(c) >= minLines) {
            out.push(`${'  '.repeat(d)}fn ${nm}(${c.params.map(p => src.slice(p.start, p.end)).join(', ')})  [${ln(c)}] ${span(c)}L`);
            rec(c.body, d + 1);
          } else rec(c.body, d);
        } else rec(c, d);
      }
    }
  })(node, depth);
}

L.annotate(ast);
for (const n of ast.body) {
  let d = n;
  let prefix = '';
  if (n.type === 'ExportNamedDeclaration' && n.declaration) { d = n.declaration; prefix = 'export '; }
  if (d.type === 'ImportDeclaration') {
    console.log(`import [${ln(d)}] ${L.oneLine(L.text(src, d), 140)}`);
  } else if (d.type === 'VariableDeclaration') {
    for (const v of d.declarations) {
      const init = v.init ? L.oneLine(L.text(src, v.init), 110) : '';
      console.log(`${prefix}${d.kind} ${v.id.name || L.text(src, v.id)}  [${ln(v)}] ${span(v)}L = ${init}`);
      if (v.init) { const out = []; innerFns(v.init, 1, out); out.forEach(s => console.log(s)); }
    }
  } else if (d.type === 'FunctionDeclaration') {
    console.log(`${prefix}function ${d.id.name}(${d.params.map(p => src.slice(p.start, p.end)).join(', ')})  [${ln(d)}] ${span(d)}L`);
    const out = []; innerFns(d.body, 1, out); out.forEach(s => console.log(s));
  } else if (d.type === 'ClassDeclaration') {
    console.log(`${prefix}class ${d.id.name}${d.superClass ? ' extends ' + L.text(src, d.superClass) : ''}  [${ln(d)}] ${span(d)}L`);
    for (const m of d.body.body) {
      if (m.type === 'MethodDefinition') {
        const f = m.value;
        const kn = m.key.name || m.key.value;
        console.log(`  ${m.static ? 'static ' : ''}${m.kind === 'get' ? 'get ' : m.kind === 'set' ? 'set ' : ''}${kn}(${f.params.map(p => src.slice(p.start, p.end)).join(', ')})  [${ln(m)}] ${span(m)}L`);
        const out = []; innerFns(f.body, 2, out); out.forEach(s => console.log(s));
      } else if (m.type === 'PropertyDefinition') {
        console.log(`  prop ${m.key.name}  [${ln(m)}]`);
      }
    }
  } else {
    console.log(`${d.type}  [${ln(d)}] ${span(d)}L  ${L.oneLine(L.text(src, d), 100)}`);
  }
}
