// shadow_prep.cjs — 为「影子策略」准备一份带分支探针的策略副本（只写到 /tmp/c136-r05/strat，绝不改 c136-data）。
// 用法：node --expose-internals shadow_prep.cjs <va|vb|vc|c110>
// 做三件事（策略逻辑一个字不动）：
//   1) 把 import 的相对路径改成干净模拟器的绝对路径；
//   2) 在选定方法里（嵌套函数除外），每个 return 前插 __br(行号)，continue/break 前插 __br(行号+0.5)；
//      方法入口插 __br(-起始行)，出口（try/finally）插 __br(0)；
//   3) 文件头定义 __br：只有 globalThis.__SH.on 为真时才把行号记进 globalThis.__SH.hits。
// 产出 /tmp/c136-r05/strat/<ver>.mjs 和 <ver>.map.json（方法名 → [起始行, 结束行]，行号都是原文件行号）。
'use strict';
const fs = require('fs');
const path = require('path');
const { pathToFileURL } = require('url');
const L = require('./jslib.cjs');
const acorn = require('internal/deps/acorn/acorn/dist/acorn');
const walk = require('internal/deps/acorn/acorn-walk/dist/walk');

const FILES = { va: 'v27-team-c116-va.js', vb: 'v27-team-c116-vb.js', vc: 'v27-team-c116.js', c110: 'v27-team-c110.js' };
const ver = process.argv[2] || 'vb';
const DATA = process.env.C136_DATA || '/agent/repos/c136-data';
const src = fs.readFileSync(path.join(DATA, 'src/strategy', FILES[ver]), 'utf8');
const ast = acorn.parse(src, { ecmaVersion: 'latest', sourceType: 'module', locations: true, ranges: true });

// 要插探针的方法（所有类里同名的都插；像素级热循环的 analyze 等不插）
const PROBE = new Set(['act', 'buyLand', 'tryDonateToTeammate', 'pickTarget', 'allow', 'botOk', 'dpNeutral', 'expandNeutral', 'send', 'idleBoats', 'boatFood', 'boatOut',
  'warAct', 'counterAttack', 'tryEmergencyBossRescue', 'tryEmergencySquadAssist', 'tryInterceptEnemyBoats', 'peerAggressor', 'hold', 'updateShadowQuota', 'tryPeaceVote', 'isMopUp',
  'trySquadRescuePoke', 'tryPrivateBossEmoji', 'bankAct', 'stepFlashLoan']);
const edits = []; // { pos, text }
const map = {};
for (const node of ast.body) {
  const cls = node.type === 'ClassDeclaration' ? node : (node.type === 'ExportNamedDeclaration' && node.declaration && node.declaration.type === 'ClassDeclaration' ? node.declaration : null);
  if (!cls) continue;
  for (const m of cls.body.body) {
    if (m.type !== 'MethodDefinition' || m.key.type !== 'Identifier') continue;
    const name = m.key.name;
    const fn = m.value;
    map[`${cls.id.name}.${name}`] = [fn.loc.start.line, fn.loc.end.line];
    if (!PROBE.has(name)) continue;
    const body = fn.body;
    // 入口记 -起始行；整个方法体包一层 try/finally，出口（无论 return 还是自然结束）记 0
    edits.push({ pos: body.start + 1, text: ` __br(-${fn.loc.start.line}); try {` });
    edits.push({ pos: body.end - 1, text: ` } finally { __br(0); } ` });
    // 只给方法自身的语句插探针（嵌套函数里的不插）：return 记行号，continue/break 记 行号+0.5
    const isFn = (n) => n.type === 'FunctionExpression' || n.type === 'ArrowFunctionExpression' || n.type === 'FunctionDeclaration';
    const visit = (n, anc) => {
      if (anc.slice(0, -1).some((a) => a !== body && isFn(a))) return;
      const half = n.type === 'ReturnStatement' ? '' : '.5';
      edits.push({ pos: n.start, text: `{ __br(${n.loc.start.line}${half}); `, close: n.end });
    };
    walk.ancestor(body, { ReturnStatement: visit, ContinueStatement: visit, BreakStatement: visit });
  }
}
// 从后往前改，避免偏移错位；带 close 的语句在结尾补一个 }
const ops = [];
for (const e of edits) {
  ops.push({ pos: e.pos, text: e.text, order: 1 });
  if (e.close != null) ops.push({ pos: e.close, text: ' }', order: 0 });
}
ops.sort((a, b) => b.pos - a.pos || a.order - b.order);
let out = src;
for (const o of ops) out = out.slice(0, o.pos) + o.text + out.slice(o.pos);
const simIdx = pathToFileURL(path.join(DATA, 'src/sim/sim/index.js')).href;
const simMap = pathToFileURL(path.join(DATA, 'src/sim/sim/map.js')).href;
let n1 = 0;
out = out.replace(/from\s+"\.\.\/\.\.\/sim\/index\.js"/g, () => { n1++; return `from ${JSON.stringify(simIdx)}`; });
out = out.replace(/from\s+"\.\.\/\.\.\/sim\/map\.js"/g, () => { n1++; return `from ${JSON.stringify(simMap)}`; });
const head = 'const __br = (l) => { const T = globalThis.__SH; if (T && T.on) T.hits.push(l); };\n';
// 头部多了 1 行，探针里的行号用的是原文件行号，不受影响
const dir = '/tmp/c136-r05/strat';
fs.mkdirSync(dir, { recursive: true });
fs.writeFileSync(path.join(dir, `${ver}.mjs`), head + out);
fs.writeFileSync(path.join(dir, `${ver}.map.json`), JSON.stringify(map));
// 语法自检
acorn.parse(head + out, { ecmaVersion: 'latest', sourceType: 'module' });
console.log(`${ver}: ${FILES[ver]} → ${dir}/${ver}.mjs｜改写 import ${n1} 处｜探针 ${edits.length} 个（方法 ${Object.keys(map).filter((k) => PROBE.has(k.split('.')[1])).length} 个）`);
