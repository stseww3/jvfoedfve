#!/usr/bin/env node
// teamgate-v2.mjs — 离线组队模拟器（R06 执笔）。v2.1 纯离线范围：只用来验收「模拟器把历史旧策略复现得对不对」，
// 以及在历史断面上做指令通道延迟的反事实归因。只装历史旧策略 va / vb / vc / c110（数据包里的原文件，按内容散列核对），
// 不装载任何其他策略文件、不覆盖策略参数、不比较候选策略，不接线上。
//
// 用法（都在 c136-review/agents/R06 下，经重计算闸门跑）：
//   HEAVY_TIMEOUT=110 timeout 120 bash ../../tools/run-heavy.sh node sim-v2/teamgate-v2.mjs --mode <模式> …
//
//   --mode verify      物理底座自检：整段重放一局录像，与真引擎重放的指纹核对；clone 分叉自检；计时
//       --match B021 [--to 拍] [--clone-at 拍] [--clone-len 拍数]
//   --mode live        真局签名扫描：只放录像，用同一套口径算出每局当年真实的指令签名与席位结果（实盘区间）
//   --mode checkpoint  历史断面重演：从录像的 t0 起，我方席位改由这一局当年那一版历史策略经指令通道下令，跑一个窗口，
//                      和录像（历史臂）对照 → 复现度；换通道档（C0 / C1 / C2 / C3）重跑 → 通道延迟的归因量
//   --mode arena       闭环对手模型标定：真局房间头里，其余真人换成按实测画像拟合的对手模型，和同一局录像的走势对照
//   --help             各模式的全部开关
//
// 只读 /agent/repos/c136-data/（引擎移植、录像、日志、历史策略）和本目录；结果写到 --out 指定的文件（缺省只打印）。
import { parseArgs } from './lib/util.mjs';

const o = parseArgs(process.argv.slice(2));
const mode = o.mode || (o.help ? 'help' : '');

try {
  if (mode === 'verify') {
    const { runVerify } = await import('./lib/verify.mjs');
    runVerify(o);
  } else if (mode === 'checkpoint') {
    const { runCheckpoint } = await import('./lib/checkpoint.mjs');
    await runCheckpoint(o);
  } else if (mode === 'live') {
    const { runLive } = await import('./lib/live.mjs');
    runLive(o);
  } else if (mode === 'arena') {
    const { runArena } = await import('./lib/arena.mjs');
    await runArena(o);
  } else {
    const { HELP } = await import('./lib/help.mjs');
    console.log(HELP);
    if (mode !== 'help') process.exitCode = 2;
  }
} catch (err) {
  if (/^纯离线范围/.test(String(err && err.message))) { console.error(`[teamgate-v2] ${err.message}`); process.exitCode = 3; } else throw err;
}
