// jslib.cjs — R05 的公共解析库。
// 用 Node 自带的 acorn（node --expose-internals）把策略文件解析成语法树，不需要联网安装任何包。
// 被截断的文件用 repairTruncated() 补齐括号后再解析（v2.0 的三份源码都完整，不会触发）。
// v2.0：默认从 /agent/repos/c136-data/src/strategy 读源码（只读）；可用环境变量 R05_SRC 改。
'use strict';
const fs = require('fs');
const path = require('path');

let acorn, walk;
try {
  acorn = require('internal/deps/acorn/acorn/dist/acorn');
  walk = require('internal/deps/acorn/acorn-walk/dist/walk');
} catch (e) {
  console.error('需要用 node --expose-internals 运行（使用 Node 自带的 acorn）');
  process.exit(2);
}

const SRC_DIR = process.env.R05_SRC || '/agent/repos/c136-data/src/strategy';
// 需要落盘的中间文件（params.cjs 真正加载模块）一律写到 WORK_DIR，绝不写 c136-data。
const WORK_DIR = process.env.R05_WORK || '/tmp/c136-r05/work';
const SIM_DIR = process.env.R05_SIM || '/agent/repos/c136-data/src/sim/sim';

function readSrc(name) {
  const p = path.isAbsolute(name) ? name : path.join(SRC_DIR, name);
  return fs.readFileSync(p, 'utf8');
}

// 把截断的源码修成可解析的：
// 1) 用分词器走到出错为止，记录每个「语句边界」时的括号栈；
// 2) 退回到最后一个完整语句的结尾（深度不变处的 ; 或 }），丢掉之后的残句；
// 3) 按括号栈倒序补上闭括号。
// 返回 { text, cutLine, cutOffset, droppedBytes, closers }。
function repairTruncated(src) {
  const tt = acorn.tokTypes;
  const stack = [];
  let lastGood = null; // { end, stack }
  let prevType = null;
  const tok = acorn.tokenizer(src, { ecmaVersion: 'latest', sourceType: 'module', locations: true });
  try {
    for (;;) {
      const t = tok.getToken();
      if (t.type === tt.eof) break;
      // try 块被截断时，补的右括号后面要带一个空 catch，否则语法不成立
      if (t.type === tt.braceL) stack.push(prevType === tt._try ? '} catch {}' : '}');
      else if (t.type === tt.dollarBraceL) stack.push('}');
      else if (t.type === tt.parenL) stack.push(')');
      else if (t.type === tt.bracketL) stack.push(']');
      else if (t.type === tt.backQuote) {
        if (stack.length && stack[stack.length - 1] === '`') stack.pop(); else stack.push('`');
      } else if (t.type === tt.braceR || t.type === tt.parenR || t.type === tt.bracketR) stack.pop();
      const top = stack.length ? stack[stack.length - 1] : '';
      const inExpr = stack.includes(')') || stack.includes(']') || stack.includes('`');
      if (!inExpr && (t.type === tt.semi || (t.type === tt.braceR && top !== '`'))) {
        lastGood = { end: t.end, stack: stack.slice() };
      }
      prevType = t.type;
    }
    return { text: src, cutLine: null, cutOffset: src.length, droppedBytes: 0, closers: '' };
  } catch (e) {
    if (!lastGood) throw e;
    const head = src.slice(0, lastGood.end);
    const closers = lastGood.stack.slice().reverse().join('\n');
    const cutLine = head.split('\n').length;
    return {
      text: head + '\n' + closers + '\n',
      cutLine,
      cutOffset: lastGood.end,
      droppedBytes: Buffer.byteLength(src) - Buffer.byteLength(head),
      closers: lastGood.stack.slice().reverse().join(''),
      error: e.message,
    };
  }
}

function parse(src) {
  return acorn.parse(src, { ecmaVersion: 'latest', sourceType: 'module', locations: true, ranges: true });
}

// 解析一个文件；解析失败时尝试按截断修复。返回 { src, ast, repaired }。
function load(name) {
  const raw = readSrc(name);
  try {
    return { name, src: raw, ast: parse(raw), repaired: null };
  } catch (e) {
    const rep = repairTruncated(raw);
    return { name, src: rep.text, ast: parse(rep.text), repaired: rep };
  }
}

// 给每个节点挂 parent，返回按源码顺序的函数类节点清单。
function annotate(ast) {
  const fns = [];
  (function rec(node, parent) {
    if (!node || typeof node.type !== 'string') return;
    node.parent = parent;
    if (node.type === 'FunctionDeclaration' || node.type === 'FunctionExpression' ||
        node.type === 'ArrowFunctionExpression' || node.type === 'ClassDeclaration' ||
        node.type === 'ClassExpression') fns.push(node);
    for (const k of Object.keys(node)) {
      if (k === 'parent' || k === 'loc' || k === 'range') continue;
      const v = node[k];
      if (Array.isArray(v)) { for (const c of v) if (c && typeof c.type === 'string') rec(c, node); }
      else if (v && typeof v.type === 'string') rec(v, node);
    }
  })(ast, null);
  return fns;
}

// 一个函数类节点的可读名字。
function fnName(node) {
  if (!node) return '?';
  if (node.type === 'ClassDeclaration' || node.type === 'ClassExpression') return 'class ' + (node.id ? node.id.name : '?');
  if (node.id && node.id.name) return node.id.name;
  const p = node.parent;
  if (p) {
    if (p.type === 'MethodDefinition' || p.type === 'Property' || p.type === 'PropertyDefinition') {
      const k = p.key;
      const kn = k ? (k.name || k.value || '?') : '?';
      return (p.kind === 'get' ? 'get ' : p.kind === 'set' ? 'set ' : '') + kn;
    }
    if (p.type === 'VariableDeclarator' && p.id && p.id.name) return p.id.name;
    if (p.type === 'AssignmentExpression' && p.left) return '=' + (p.left.property ? (p.left.property.name || '?') : (p.left.name || '?'));
  }
  return '(anon)';
}

// 节点的外层命名链：class X > method > 内部函数。匿名回调不计入。
function ownerChain(node) {
  const chain = [];
  for (let n = node; n; n = n.parent) {
    if (n.type === 'ClassDeclaration' || n.type === 'ClassExpression') chain.push(fnName(n).replace(/^class /, ''));
    else if (n.type === 'FunctionDeclaration' || n.type === 'FunctionExpression' || n.type === 'ArrowFunctionExpression') {
      const nm = fnName(n);
      if (nm !== '(anon)') chain.push(nm);
    }
  }
  return chain.reverse();
}

function text(src, node) { return src.slice(node.start, node.end); }
function oneLine(s, max) {
  const t = s.replace(/\s+/g, ' ').trim();
  return max && t.length > max ? t.slice(0, max - 1) + '…' : t;
}

module.exports = { acorn, walk, SRC_DIR, WORK_DIR, SIM_DIR, readSrc, repairTruncated, parse, load, annotate, fnName, ownerChain, text, oneLine };
