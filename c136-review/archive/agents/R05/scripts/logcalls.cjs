// logcalls.cjs — 机械抽取一个策略文件里所有 window.__hlLog(...) 打印语句：
//   所在方法、行号、句式模板、每个字段对应的表达式、外层条件链（if / 循环 / &&）、
//   以及同一条路径上排在它前面的「提前退出」条件（if (...) return / continue / break）。
// 用法：node --expose-internals c136-review/agents/R05/scripts/logcalls.cjs <文件名> [--json]
// 输出：默认是可读文本；--json 输出机器可读数组。
'use strict';
const L = require('./jslib.cjs');
const name = process.argv[2] || 'c110.js';
const asJson = process.argv.includes('--json');
const { src, ast, repaired } = L.load(name);
L.annotate(ast);

const isFn = (n) => n.type === 'FunctionDeclaration' || n.type === 'FunctionExpression' || n.type === 'ArrowFunctionExpression';
const T = (n, max) => L.oneLine(L.text(src, n), max);

function isJump(n) {
  return n && (n.type === 'ReturnStatement' || n.type === 'ContinueStatement' || n.type === 'BreakStatement' || n.type === 'ThrowStatement');
}
// 语句是否「必然跳出」：本身是跳转，或是以跳转结尾的块
function alwaysJumps(n) {
  if (!n) return false;
  if (isJump(n)) return true;
  if (n.type === 'BlockStatement' && n.body.length) return alwaysJumps(n.body[n.body.length - 1]);
  return false;
}
// 语句里是否含有（不进入内层函数的）跳转
function containsJump(n) {
  let found = false;
  (function rec(x) {
    if (!x || typeof x.type !== 'string' || found) return;
    if (isFn(x)) return;
    if (isJump(x)) { found = true; return; }
    for (const k of Object.keys(x)) {
      if (k === 'parent' || k === 'loc' || k === 'range') continue;
      const v = x[k];
      if (Array.isArray(v)) v.forEach(rec); else if (v && typeof v.type === 'string') rec(v);
    }
  })(n);
  return found;
}
function jumpKind(n) {
  const last = n.type === 'BlockStatement' ? n.body[n.body.length - 1] : n;
  return last ? last.type.replace('Statement', '').toLowerCase() : '?';
}

// 模板字面量 -> { template, fields }
function tpl(arg) {
  if (arg.type === 'TemplateLiteral') {
    let template = '';
    const fields = [];
    for (let i = 0; i < arg.quasis.length; i++) {
      const q = arg.quasis[i].value.cooked;
      template += q;
      if (i < arg.expressions.length) {
        const e = arg.expressions[i];
        const expr = T(e);
        const m = /([A-Za-z_][A-Za-z0-9_]*)\s*=\s*\(?$/.exec(q) || /([A-Za-z_][A-Za-z0-9_-]*)\s*[:=]?\s*$/.exec(q);
        fields.push({ key: m ? m[1] : null, expr });
        template += '${' + expr + '}';
      }
    }
    return { template, fields };
  }
  if (arg.type === 'Literal') return { template: String(arg.value), fields: [] };
  if (arg.type === 'BinaryExpression' && arg.operator === '+') {
    const a = tpl(arg.left), b = tpl(arg.right);
    return { template: a.template + b.template, fields: a.fields.concat(b.fields) };
  }
  return { template: '${' + T(arg) + '}', fields: [{ key: null, expr: T(arg) }] };
}

const calls = [];
(function find(n) {
  if (!n || typeof n.type !== 'string') return;
  if (n.type === 'CallExpression' && n.callee.type === 'MemberExpression' && !n.callee.computed &&
      n.callee.property.name === '__hlLog') calls.push(n);
  for (const k of Object.keys(n)) {
    if (k === 'parent' || k === 'loc' || k === 'range') continue;
    const v = n[k];
    if (Array.isArray(v)) v.forEach(find); else if (v && typeof v.type === 'string') find(v);
  }
})(ast);

const out = [];
for (const c of calls) {
  const { template, fields } = tpl(c.arguments[0]);
  const tagM = /^\[([A-Za-z0-9_-]+)/.exec(template);
  const owner = L.ownerChain(c).join('.');
  const guards = [];
  // 自内向外走到最外层的命名方法为止
  let child = c;
  let fnCrossed = 0;
  for (let p = c.parent; p; child = p, p = p.parent) {
    if (p.type === 'ClassBody' || p.type === 'Program') break;
    if (p.type === 'IfStatement') {
      if (child === p.consequent) guards.push({ kind: 'if', line: p.loc.start.line, test: T(p.test) });
      else if (child === p.alternate) guards.push({ kind: 'else-of', line: p.loc.start.line, test: T(p.test) });
    } else if (p.type === 'ConditionalExpression') {
      if (child === p.consequent) guards.push({ kind: 'if', line: p.loc.start.line, test: T(p.test) });
      else if (child === p.alternate) guards.push({ kind: 'else-of', line: p.loc.start.line, test: T(p.test) });
    } else if (p.type === 'LogicalExpression' && child === p.right) {
      guards.push({ kind: p.operator === '&&' ? 'if' : (p.operator === '||' ? 'else-of' : 'nullish-of'), line: p.loc.start.line, test: T(p.left) });
    } else if (p.type === 'ForStatement') {
      guards.push({ kind: 'for', line: p.loc.start.line, test: `${p.init ? T(p.init) : ''}; ${p.test ? T(p.test) : ''}; ${p.update ? T(p.update) : ''}` });
    } else if (p.type === 'ForOfStatement' || p.type === 'ForInStatement') {
      guards.push({ kind: 'for', line: p.loc.start.line, test: `${T(p.left)} ${p.type === 'ForOfStatement' ? 'of' : 'in'} ${T(p.right, 160)}` });
    } else if (p.type === 'WhileStatement' || p.type === 'DoWhileStatement') {
      guards.push({ kind: 'while', line: p.loc.start.line, test: T(p.test) });
    } else if (p.type === 'TryStatement') {
      guards.push({ kind: child === p.block ? 'try' : (child === p.handler ? 'catch' : 'finally'), line: p.loc.start.line, test: '' });
    } else if (p.type === 'SwitchCase') {
      guards.push({ kind: 'case', line: p.loc.start.line, test: p.test ? T(p.test) : 'default' });
    } else if (isFn(p)) {
      fnCrossed++;
      const nm = L.fnName(p);
      guards.push({ kind: 'fn', line: p.loc.start.line, test: nm });
    }
    // 同一个块里排在前面的提前退出
    if ((p.type === 'BlockStatement' || p.type === 'Program' || p.type === 'SwitchCase') && Array.isArray(p.body || p.consequent)) {
      const body = p.body || p.consequent;
      const idx = body.indexOf(child);
      for (let i = idx - 1; i >= 0; i--) {
        const s = body[i];
        if (s.type === 'IfStatement') {
          if (alwaysJumps(s.consequent) && !s.alternate) {
            guards.push({ kind: 'prior-exit', line: s.loc.start.line, test: T(s.test), exit: jumpKind(s.consequent) });
          } else if (containsJump(s)) {
            guards.push({ kind: 'prior-may-exit', line: s.loc.start.line, test: T(s.test, 200) });
          }
        } else if (isJump(s)) {
          guards.push({ kind: 'prior-exit', line: s.loc.start.line, test: 'true', exit: jumpKind(s) });
        } else if (containsJump(s) && s.type !== 'ForStatement' && s.type !== 'ForOfStatement' && s.type !== 'WhileStatement' && s.type !== 'ForInStatement') {
          guards.push({ kind: 'prior-may-exit', line: s.loc.start.line, test: T(s, 200) });
        }
      }
    }
  }
  guards.reverse(); // 由外到内
  out.push({ file: name, line: c.loc.start.line, owner, tag: tagM ? tagM[1] : null, template, fields, guards });
}

if (asJson) {
  console.log(JSON.stringify(out, null, 1));
} else {
  console.log(`# logcalls ${name}  共 ${out.length} 处 __hlLog 调用${repaired ? `  （文件被截断于第 ${repaired.cutLine} 行，之后的调用缺失）` : ''}`);
  for (const o of out) {
    console.log(`\n## L${o.line}  ${o.owner}  [${o.tag}]`);
    console.log(`template: ${o.template}`);
    for (const f of o.fields) console.log(`  field ${f.key || '?'} = ${f.expr}`);
    for (const g of o.guards) console.log(`  ${g.kind.padEnd(14)} L${g.line}: ${g.test}${g.exit ? '  -> ' + g.exit : ''}`);
  }
}
