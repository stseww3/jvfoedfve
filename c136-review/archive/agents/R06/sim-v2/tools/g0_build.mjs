#!/usr/bin/env node
// g0_build.mjs — 把保真度验收报告的正文模板和 g0_report.mjs 生成的表、数字拼成 reports/SIM-V2-CALIBRATION-G0.md。
//
// 正文模板：reports/src-g0/*.md，按文件名顺序拼接。模板里三种记号：
//   {{T:表名}}        换成 sim-v2/calib/report/tables/<表名>.md 整张表
//   {{v:键}}          换成 sim-v2/calib/report/values.json 里这个键的值
//   <!-- assert: 表达式 -->   正文里一句定性的话所依赖的数量关系。表达式是 JavaScript，n('键') 取这个键里的第一个数
//                      （去掉逗号；百分号、正负号「−」照认），s('键') 取原字符串。表达式不成立就报错、不写报告——
//                      数据重跑之后正文里的话要是不再成立，在这里就拦下来。这一行不进报告。
// 缺表、缺键、断言不成立，全部列出来并以退出码 1 结束；--draft 时照样写出报告（缺的地方标「【缺 …】」），用来边跑数据边看稿。
//
// 用法（在 c136-review/agents/R06 下）：node sim-v2/tools/g0_build.mjs [--draft] [--out 报告路径]
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const R06 = path.resolve(HERE, '..', '..');
const SRC = path.join(R06, 'reports', 'src-g0');
const REP = path.join(R06, 'sim-v2', 'calib', 'report');
const argv = process.argv.slice(2);
const DRAFT = argv.includes('--draft');
const OUT = argv.includes('--out') ? path.resolve(argv[argv.indexOf('--out') + 1]) : path.join(R06, 'reports', 'SIM-V2-CALIBRATION-G0.md');

const values = JSON.parse(fs.readFileSync(path.join(REP, 'values.json'), 'utf8'));
const problems = [];
const usedTables = new Set(), usedKeys = new Set();

const s = (k) => { if (!(k in values)) throw new Error(`缺键 ${k}`); return values[k]; };
const n = (k) => {
  const m = String(s(k)).replace(/,/g, '').match(/[+−-]?\d+(\.\d+)?/);
  if (!m) throw new Error(`键 ${k} 的值「${values[k]}」里没有数`);
  return parseFloat(m[0].replace('−', '-'));
};

let asserts = 0;
const parts = [];
const ASSERT_RE = /^[ \t]*<!--\s*assert:\s*([\s\S]*?)-->[ \t]*\n?/gm;
const files = fs.readdirSync(SRC).filter((x) => x.endsWith('.md')).sort();
// 模板里可以引用「一共核对了多少条断言」：先数一遍
values['build.asserts'] = String(files.reduce((a, file) => a + (fs.readFileSync(path.join(SRC, file), 'utf8').match(ASSERT_RE) || []).length, 0));
for (const file of files) {
  let text = fs.readFileSync(path.join(SRC, file), 'utf8');
  text = text.replace(ASSERT_RE, (m, expr) => {
    asserts++;
    try {
      // eslint-disable-next-line no-new-func
      if (!new Function('n', 's', `return (${expr});`)(n, s)) problems.push(`${file}：断言不成立：${expr.trim()}`);
    } catch (e) { problems.push(`${file}：断言算不出来（${e.message}）：${expr.trim()}`); }
    return '';
  });
  text = text.replace(/\{\{T:([^}]+)\}\}/g, (m, name) => {
    const f = path.join(REP, 'tables', `${name.trim()}.md`);
    if (!fs.existsSync(f)) { problems.push(`${file}：缺表 ${name}`); return `【缺表 ${name}】`; }
    usedTables.add(name.trim());
    return fs.readFileSync(f, 'utf8').trimEnd();
  });
  text = text.replace(/\{\{v:([^}]+)\}\}/g, (m, key) => {
    const k = key.trim();
    if (!(k in values)) { problems.push(`${file}：缺键 ${k}`); return `【缺 ${k}】`; }
    usedKeys.add(k);
    return values[k];
  });
  parts.push(text.trimEnd());
}
const allTables = fs.existsSync(path.join(REP, 'tables')) ? fs.readdirSync(path.join(REP, 'tables')).filter((x) => x.endsWith('.md')).map((x) => x.slice(0, -3)) : [];
const unused = allTables.filter((t) => !usedTables.has(t));

if (problems.length) {
  console.error(`有 ${problems.length} 处问题：`);
  for (const p of problems.slice(0, 80)) console.error('  ' + p);
}
if (!problems.length || DRAFT) {
  fs.writeFileSync(OUT, parts.join('\n\n') + '\n');
  const bytes = fs.statSync(OUT).size;
  console.log(`写入 ${path.relative(process.cwd(), OUT)}（${bytes} 字节）：用到表 ${usedTables.size} 张、数字 ${usedKeys.size} 个，核对正文断言 ${asserts} 条${DRAFT && problems.length ? '（草稿：有缺项）' : ''}`);
}
if (unused.length) console.log(`生成了但正文没用到的表：${unused.join(' ')}`);
process.exit(problems.length ? 1 : 0);
