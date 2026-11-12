// params_all.mjs — 五个策略文件最终生效的参数（Policy 构造后的 this.p）并排打印，并列出各档取值不同的键。
// 用法：bash c136-review/tools/run-heavy.sh node c136-review/agents/R08/scripts/params_all.mjs
//   → out/_cross/params.txt、params.json
// 只读 /agent/repos/c136-data/src/strategy/；不跑对局。
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const OUT = path.join(HERE, "..", "out", "_cross");
const SRC = "/agent/repos/c136-data/src/strategy";
const FILES = [
  ["c110", "v27-team-c110.js", "squad20"],
  ["c116", "v27-team-c116.js", "squad10（Vc）"],
  ["c116-va", "v27-team-c116-va.js", "squad10（Va）"],
  ["c116-vb", "v27-team-c116-vb.js", "squad10（Vb）"],
  ["g09", "v27-team-g09.js", "squad8"],
];
// 卡片和报告里引用到的键（其余的只在「各档不同」里出现）
const KEYS = [
  "period", "maxTargets", "dpEnd", "coreFrom", "winR", "minSend", "feeK", "botMax", "idleCap", "dpSpend", "sendFrac", "foodK", "maxCost", "botWait", "botSkip",
  "elimW", "shareW", "chunk", "refN", "killW", "oppFloorCap", "collapseFloorCap", "counterK", "counterFloor", "maxW", "marketFrom", "marketFloor", "surplus", "growth",
  "pulseFrac", "bleedSafeCap", "maxBoats", "boatEvery", "boatRange", "boatFood", "boatFee", "pplK", "hungryK",
];

// 策略文件 import "../../sim/index.js"：和 shadow.mjs 一样，把策略拷到 out/_run/a/b/ 下、把引擎目录链到 out/_run/sim，路径才对得上
function ensureStrategy(f) {
  const runDir = path.join(HERE, "..", "out", "_run");
  const dst = path.join(runDir, "a", "b", f);
  const src = path.join(SRC, f);
  fs.mkdirSync(path.dirname(dst), { recursive: true });
  const link = path.join(runDir, "sim");
  if (!fs.existsSync(link)) fs.symlinkSync("/agent/repos/c136-data/src/sim/sim", link);
  if (!fs.existsSync(dst) || fs.statSync(dst).size !== fs.statSync(src).size) fs.copyFileSync(src, dst);
  return dst;
}

const P = {};
for (const [tag, f] of FILES) {
  const m = await import(pathToFileURL(ensureStrategy(f)).href);
  const Cls = m.Policy || m.default;
  P[tag] = new Cls().p;
}
const tags = FILES.map((x) => x[0]);
const fmt = (v) => (v === undefined ? "—" : typeof v === "number" ? String(Number.isInteger(v) ? v : +v.toFixed(4)) : JSON.stringify(v));
const lines = [];
lines.push(`[PA-A] 生效参数（Policy 构造后的 this.p）：键 | ${FILES.map(([t, , c]) => `${t}（${c}）`).join(" | ")} | 各档是否相同`);
for (const k of KEYS) {
  const vs = tags.map((t) => fmt(P[t][k]));
  lines.push(`  ${k} | ${vs.join(" | ")} | ${new Set(vs).size === 1 ? "同" : "不同"}`);
}
const all = new Set();
for (const t of tags) for (const k of Object.keys(P[t])) all.add(k);
const diff = [];
for (const k of [...all].sort()) {
  const vs = tags.map((t) => fmt(P[t][k]));
  if (new Set(vs).size > 1) diff.push([k, vs]);
}
lines.push("");
lines.push(`[PA-B] 全部 ${all.size} 个键里各档取值不同的 ${diff.length} 个：键 | ${tags.join(" | ")}`);
for (const [k, vs] of diff) lines.push(`  ${k} | ${vs.join(" | ")}`);
fs.mkdirSync(OUT, { recursive: true });
fs.writeFileSync(path.join(OUT, "params.txt"), lines.join("\n") + "\n");
fs.writeFileSync(path.join(OUT, "params.json"), JSON.stringify({ files: FILES, params: P }));
if (!process.argv.includes("--quiet")) console.log(lines.join("\n"));
else console.log(`params: ${all.size} 个键，${diff.length} 个各档不同`);
