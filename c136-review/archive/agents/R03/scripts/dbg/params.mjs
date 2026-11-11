// 调试：打印某个策略文件的生效参数（Policy 实例上的 this.p）。用法：node dbg/params.mjs <mid|file.js> [正则]
import path from 'node:path';
import { strategyFileOf, compileStrategy } from '../shadow.mjs';
const [arg, re] = process.argv.slice(2);
const file = arg.endsWith('.js') ? arg : strategyFileOf(arg);
const full = path.isAbsolute(file) ? file : path.join('/agent/repos/c136-data/src/strategy', file);
globalThis.window = {};
const { Policy } = await compileStrategy(full);
const p = new Policy({}, 0).p;
const rx = re ? new RegExp(re) : null;
const keys = Object.keys(p).filter((k) => !rx || rx.test(k)).sort();
console.log(path.basename(full), keys.length, '项');
console.log(keys.map((k) => `${k}=${typeof p[k] === 'object' ? JSON.stringify(p[k]) : p[k]}`).join('  '));
