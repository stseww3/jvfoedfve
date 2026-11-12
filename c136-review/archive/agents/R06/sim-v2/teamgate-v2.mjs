#!/usr/bin/env node
// teamgate-v2.mjs — 高保真组队模拟器与断面反事实评测器（R06 执笔，阶段 B）。
//
// 用法（都在 c136-review/agents/R06 下，经重计算闸门跑）：
//   HEAVY_TIMEOUT=110 timeout 120 bash ../../tools/run-heavy.sh node sim-v2/teamgate-v2.mjs --mode <模式> …
//
//   --mode verify      物理底座自检：整段重放一局录像，与真引擎重放的指纹核对；clone 分叉自检；计时
//       --match B021 [--to 拍] [--clone-at 拍] [--clone-len 拍数]
//   --mode checkpoint  真局断面反事实：从录像的 t0 接管我方席位，同一条指令通道下对照臂 / 处理臂各跑一个窗口，出成对差
//   --mode arena       闭环多原型对抗：离线地图上多队对打（同标签同队 / 拆队、路人、掉线空壳、对手原型），配对 A/B
//   --mode pair        汇总若干次 checkpoint / arena 的结果文件，出成对差的中位数与 P10
//   --help             各模式的全部开关
//
// 只读 /agent/repos/c136-data/（引擎移植、录像、日志、策略）和本目录；结果写到 --out 指定的文件（缺省只打印）。
import { parseArgs } from './lib/util.mjs';

const o = parseArgs(process.argv.slice(2));
const mode = o.mode || (o.help ? 'help' : '');

if (mode === 'verify') {
  const { runVerify } = await import('./lib/verify.mjs');
  runVerify(o);
} else if (mode === 'checkpoint') {
  const { runCheckpoint } = await import('./lib/checkpoint.mjs');
  await runCheckpoint(o);
} else if (mode === 'arena') {
  const { runArena } = await import('./lib/arena.mjs');
  await runArena(o);
} else if (mode === 'pair') {
  const { runPair } = await import('./lib/pair.mjs');
  await runPair(o);
} else {
  const { HELP } = await import('./lib/help.mjs');
  console.log(HELP);
  if (mode !== 'help') process.exitCode = 2;
}
