// 打印某个策略文件的最终生效参数（Policy 构造后 this.p），便于核对各层覆盖后的真实取值。
// 用法：bash c136-review/tools/run-heavy.sh node c136-review/agents/R08/scripts/dump_params.mjs <策略文件绝对路径> [键1,键2,...]
import { pathToFileURL } from "node:url";
const file = process.argv[2];
const keys = process.argv[3] ? process.argv[3].split(",") : null;
const m = await import(pathToFileURL(file).href);
const Cls = m.Policy || m.default;
const p = new Cls().p;
const out = {};
for (const k of keys || Object.keys(p).sort()) out[k] = p[k];
console.log(JSON.stringify(out, null, keys ? 0 : 1));
