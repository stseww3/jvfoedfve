// params.cjs — 参数表的机械部分。
// 对一个策略文件：
//   1) 真正加载它（配上模拟器仓库的 sim/ 模块），new Policy() 之后把生效的参数对象 this.p 整个倒出来（这就是「当前值」）；
//   2) 从语法树里找出每一层参数对象（DEFAULT_PARAMS / BASE / GENERAL_PARAMS / STYLE_PARAMS / PARAMS13 / P17 / PARAMS）
//      里每个键的字面值和紧挨着它的源码注释，得到「哪一层定的值、作者写的含义」；
//   3) 扫描所有 P.xxx / this.p.xxx 的读取位置，得到「每个参数被哪些方法读」。
// 用法：node --expose-internals c136-review/agents/R05/scripts/params.cjs <文件名> > out/params-raw-<版本>.json
'use strict';
const fs = require('fs');
const path = require('path');
const { pathToFileURL } = require('url');
const L = require('./jslib.cjs');

const name = process.argv[2] || 'c110.js';
const LAYERS = ['DEFAULT_PARAMS', 'BASE', 'GENERAL_PARAMS', 'STYLE_PARAMS', 'PARAMS13', 'P17', 'PARAMS'];

(async () => {
  const raw = L.readSrc(name);
  let srcText = raw, repaired = null;
  try { L.parse(raw); } catch (e) { repaired = L.repairTruncated(raw); srcText = repaired.text; }

  // ---- 1) 真正加载，取生效值 ----
  const runDir = path.join(L.SRC_DIR, 'run', 'a');
  fs.mkdirSync(runDir, { recursive: true });
  fs.writeFileSync(path.join(L.SRC_DIR, 'package.json'), '{"type":"module"}\n');
  const modPath = path.join(runDir, name.replace(/\.js$/, '') + '.mjs');
  fs.writeFileSync(modPath, srcText);
  const mod = await import(pathToFileURL(modPath).href);
  // 实盘里扩展（page.js）是这样建实例的：new Policy({ spawnRoll: 0, planEvery: 0 }, me)
  // 依据：数据 B 的 tsb/squad/page.js 里 `const vt={spawnRoll:0,planEvery:0}` 和 `new s(vt,e)`。
  const pol = new mod.Policy({ spawnRoll: 0, planEvery: 0 }, 0);
  const effective = {};
  for (const k of Object.keys(pol.p).sort()) effective[k] = pol.p[k];

  // ---- 2) 各层字面值和注释 ----
  const comments = [];
  const ast = L.acorn.parse(srcText, {
    ecmaVersion: 'latest', sourceType: 'module', locations: true, ranges: true,
    onComment: (block, text, start, end, startLoc, endLoc) => comments.push({ block, text, start, end, line: startLoc.line, endLine: endLoc.line }),
  });
  L.annotate(ast);
  const layers = {};
  const layerOrder = [];
  for (const n of ast.body) {
    const d = n.type === 'ExportNamedDeclaration' && n.declaration ? n.declaration : n;
    if (d.type !== 'VariableDeclaration') continue;
    for (const v of d.declarations) {
      if (!v.id || !LAYERS.includes(v.id.name) || !v.init || v.init.type !== 'ObjectExpression') continue;
      const keys = {};
      let prevEnd = v.init.start;
      const spreads = [];
      for (const prop of v.init.properties) {
        if (prop.type === 'SpreadElement') { spreads.push(L.text(srcText, prop.argument)); prevEnd = prop.end; continue; }
        const key = prop.key.name || prop.key.value;
        // 注释：上一个属性结束之后、本属性开始之前的整段注释；以及同一行尾部的注释
        const lead = comments.filter(c => c.start >= prevEnd && c.end <= prop.start).map(c => c.text.trim());
        const nextStart = srcText.indexOf('\n', prop.end);
        const trail = comments.filter(c => c.start >= prop.end && c.start <= (nextStart < 0 ? srcText.length : nextStart) && c.line === prop.loc.end.line).map(c => c.text.trim());
        keys[key] = { value: L.oneLine(L.text(srcText, prop.value)), line: prop.loc.start.line, comment: L.oneLine(lead.concat(trail).join(' ')) };
        // 行尾注释算在本属性上，下一个属性的前导注释从它之后起算
        prevEnd = trail.length ? comments.filter(c => c.start >= prop.end && c.line === prop.loc.end.line).reduce((m, c) => Math.max(m, c.end), prop.end) : prop.end;
      }
      layers[v.id.name] = { line: v.loc.start.line, spreads, keys };
      layerOrder.push(v.id.name);
    }
  }

  // 构造函数里对 this.p 的直接改写（例如 this.p.xxx = …）
  const ctorWrites = [];
  // ---- 3) 读取位置 ----
  const reads = {};
  const writes = {};
  (function rec(n) {
    if (!n || typeof n.type !== 'string') return;
    if (n.type === 'MemberExpression' && !n.computed && n.property && n.property.type === 'Identifier') {
      const o = n.object;
      const isP = (o.type === 'Identifier' && o.name === 'P') ||
        (o.type === 'MemberExpression' && !o.computed && o.object.type === 'ThisExpression' && o.property.name === 'p');
      if (isP) {
        const owner = L.ownerChain(n).join('.') || '(top)';
        const isWrite = n.parent && n.parent.type === 'AssignmentExpression' && n.parent.left === n;
        const bag = isWrite ? writes : reads;
        const key = n.property.name;
        (bag[key] = bag[key] || {});
        (bag[key][owner] = bag[key][owner] || []).push(n.loc.start.line);
      }
    }
    for (const k of Object.keys(n)) {
      if (k === 'parent' || k === 'loc' || k === 'range') continue;
      const v = n[k];
      if (Array.isArray(v)) v.forEach(rec); else if (v && typeof v.type === 'string') rec(v);
    }
  })(ast);

  // 每个生效参数：最后定值的那一层
  const table = {};
  for (const k of Object.keys(effective)) {
    let setBy = null, comment = '';
    for (const ln of layerOrder) {
      const e = layers[ln].keys[k];
      if (e) { setBy = ln; if (e.comment) comment = e.comment; }
    }
    const perLayer = {};
    for (const ln of layerOrder) if (layers[ln].keys[k]) perLayer[ln] = layers[ln].keys[k].value;
    table[k] = {
      value: effective[k],
      setBy,
      perLayer,
      authorComment: comment,
      readBy: reads[k] ? Object.fromEntries(Object.entries(reads[k]).map(([o, ls]) => [o, ls])) : {},
      writtenBy: writes[k] || undefined,
    };
  }
  // 被读取但不在生效参数里的名字（读到 undefined）
  const readButUndefined = Object.keys(reads).filter(k => !(k in effective)).sort();
  // 在生效参数里但全文没有任何读取的名字
  const neverRead = Object.keys(effective).filter(k => !reads[k]).sort();

  const out = {
    file: name,
    truncated: repaired ? { cutLine: repaired.cutLine, droppedBytes: repaired.droppedBytes } : null,
    layerOrder,
    layerSpreads: Object.fromEntries(layerOrder.map(l => [l, layers[l].spreads])),
    count: Object.keys(effective).length,
    readButUndefined,
    neverRead,
    params: table,
  };
  process.stdout.write(JSON.stringify(out, null, 1) + '\n');
})().catch(e => { console.error('params.cjs 失败：', e.stack || e); process.exit(1); });
