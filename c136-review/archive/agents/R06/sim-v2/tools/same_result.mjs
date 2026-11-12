#!/usr/bin/env node
// same_result.mjs — 两个结果目录里同名的结果文件逐字段核对（计时、内存这些与运行环境有关的字段除外）。
// 用途：tools/g0_batch.mjs 在一个进程里连着跑多次运行；抽一些运行单独起进程再跑一遍，两种跑法的结果应当逐字段相同。
// 用法：node sim-v2/tools/same_result.mjs [--common] [--json] <目录 A> <目录 B>      只比两边都有的文件；全部相同退出码 0，否则 1
//       --common：只比两边都有的字段（拿旧版工具跑出的结果对新版的结果时用，新版多记了几个字段）
//       --json：最后一行改成一行 JSON（个数、比过多少个数、只有一边才有的字段名）
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const SKIP = new Set(['cpuMs', 'wallMs', 'cpuReplayMs', 'cpuWarmMs', 'cpuRealityMs', 'cpuSetupMs', 'heapMB', 'ms', 'cpuMsPer1000', 'cloneMs']);
// st（可省）：{ leaves: 比过的数（叶子）个数, onlyA / onlyB: 只有一边有的字段名（数组下标写成 #） }
function diff(a, b, at, out, common, st) {
  if (a === undefined && b === undefined) return;
  if (a === undefined || b === undefined) {
    if (st) (a === undefined ? st.onlyB : st.onlyA).add(at.replace(/\.\d+(?=\.|$)/g, '.#'));
    if (common) return;   // 只比两边都有的字段
    if (out.length <= 5) out.push(`${at}: ${String(JSON.stringify(a)).slice(0, 60)} ≠ ${String(JSON.stringify(b)).slice(0, 60)}`);
    return;
  }
  if (a === null || b === null || typeof a !== 'object' || typeof b !== 'object') {
    if (st) st.leaves++;
    if (a !== b && out.length <= 5) out.push(`${at}: ${String(JSON.stringify(a)).slice(0, 60)} ≠ ${String(JSON.stringify(b)).slice(0, 60)}`);
    return;
  }
  if (Array.isArray(a) !== Array.isArray(b)) { if (out.length <= 5) out.push(`${at}: 类型不同`); return; }
  const ks = new Set([...Object.keys(a), ...Object.keys(b)]);
  for (const k of ks) { if (SKIP.has(k)) continue; diff(a[k], b[k], `${at}.${k}`, out, common, st); }
}

// → { n: 两边都有的文件数, same: 逐字段相同的个数, bad: [[文件, 头几处不同]…],
//     leaves: 一共比了多少个数, onlyA / onlyB: 只有 A / 只有 B 才有的字段名 }
// common = true：只比两边都有的字段（一边新加了字段、另一边是旧版结果时用）
export function compareDirs(A, B, common = false) {
  const res = { n: 0, same: 0, bad: [], leaves: 0, onlyA: [], onlyB: [] };
  if (!fs.existsSync(A) || !fs.existsSync(B)) return res;
  const st = { leaves: 0, onlyA: new Set(), onlyB: new Set() };
  for (const f of fs.readdirSync(A).sort()) {
    if (!f.endsWith('.json') || !fs.existsSync(path.join(B, f))) continue;
    res.n++;
    const out = [];
    diff(JSON.parse(fs.readFileSync(path.join(A, f), 'utf8')), JSON.parse(fs.readFileSync(path.join(B, f), 'utf8')), '', out, common, st);
    if (out.length) res.bad.push([f, out.slice(0, 4)]); else res.same++;
  }
  res.leaves = st.leaves; res.onlyA = [...st.onlyA].sort(); res.onlyB = [...st.onlyB].sort();
  return res;
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const args = process.argv.slice(2);
  const common = args.includes('--common');
  const [A, B] = args.filter((x) => !x.startsWith('--'));
  const r = compareDirs(A, B, common);
  for (const [f, out] of r.bad) console.log(`${f} 不同：${out.join('；')}`);
  if (args.includes('--json')) { console.log(JSON.stringify({ n: r.n, same: r.same, leaves: r.leaves, onlyA: r.onlyA, onlyB: r.onlyB })); process.exit(r.bad.length ? 1 : 0); }
  console.log(`核对 ${r.n} 个同名结果：${r.same} 个逐字段相同（计时字段除外${common ? '；只比两边都有的字段' : ''}），${r.bad.length} 个不同`);
  process.exit(r.bad.length ? 1 : 0);
}
