#!/usr/bin/env node
// g0_batch.mjs — 一个进程里按清单连着跑多次 checkpoint / arena（每次运行各写各的结果文件）。
//
// 为什么要它：这台机器的重计算槽位是全机共用的，每跑一次都要排一次队；一次断面只要几秒，排队却常常要半分钟以上。
// 把几十次运行放进同一个进程，排一次队跑一批，每批仍然不超过重计算闸门的 110 秒。
// 与单独起进程逐个跑的结果相同：每次运行之前把策略文件重新编译一遍（sandbox.resetCompiled），随机数都是 (种子, 席位, 拍) 的散列、
// 没有跨运行的状态。tools/g0_all.sh 的 batchcheck 阶段拿同一批运行两种跑法的结果逐字段核对（除计时外应当完全相同）。
//
// 用法（在 c136-review/agents/R06 下，经重计算闸门）：
//   node sim-v2/tools/g0_batch.mjs checkpoint <结果目录名> <清单文件> [--deadline 截止时刻的毫秒时间戳] [--only 标签前缀]
//       清单每行：<标签> <局> <t0> <len> <策略> <通道> [其余开关]        → sim-v2/calib/<目录>/<标签>.json
//   node sim-v2/tools/g0_batch.mjs arena <结果目录名> <清单文件> --len 4300 --channel C2 [其余开关原样传给 arena] [--deadline …]
//       清单每行：<局> <策略>                                          → sim-v2/calib/<目录>/<局>.json
//   node sim-v2/tools/g0_batch.mjs verify <结果目录名> <清单文件> [--deadline …]
//       清单每行：<局> […]（只用第一列）                                → sim-v2/calib/<目录>/<局>.json
// 已有结果文件的跳过。最后一行打印「还剩 N 个」，外层循环看到 0 就停。
// 截止时刻 = min(--deadline, 本进程起跑后 104 秒)：前者是外层 timeout 120 的界，后者是重计算闸门 110 秒的界（它从排到槽位起算）。
// 一次运行如果被本批剩下的时间截断，结果不留，留给下一批从头跑。结果先写到 <名字>.part，跑完才改名，半路被杀留不下半个文件。
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { parseArgs } from '../lib/util.mjs';
import { resetCompiled } from '../lib/sandbox.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const SIMV2 = path.resolve(HERE, '..');
const [kind, dirName, listFile, ...restArgv] = process.argv.slice(2);
if (!['checkpoint', 'arena', 'verify'].includes(kind) || !dirName || !listFile) {
  console.error('用法：g0_batch.mjs checkpoint|arena|verify <结果目录名> <清单文件> [开关…]');
  process.exit(2);
}
const extra = parseArgs(restArgv);
const startAt = Date.now();
const deadline = Math.min(extra.deadline ? +extra.deadline : Infinity, startAt + 104000);
const only = typeof extra.only === 'string' ? extra.only : '';
delete extra.deadline; delete extra.only; delete extra._;
const dir = path.join(SIMV2, 'calib', dirName);
fs.mkdirSync(dir, { recursive: true });

const jobs = [];
for (const line of fs.readFileSync(listFile, 'utf8').split('\n')) {
  const s = line.trim();
  if (!s || s.startsWith('#')) continue;
  const p = s.split(/\s+/);
  if (kind === 'checkpoint') {
    const [tag, mid, t0, len, strat, chan, ...rest] = p;
    if (only && !tag.startsWith(only)) continue;
    jobs.push({ tag, o: { mode: 'checkpoint', match: mid, t0, len, baseline: strat, channel: chan, ...parseArgs(rest), ...extra } });
  } else if (kind === 'arena') {
    const [mid, strat, ...rest] = p;
    if (only && !mid.startsWith(only)) continue;
    jobs.push({ tag: mid, o: { mode: 'arena', room: mid, baseline: strat, ...parseArgs(rest), ...extra } });
  } else {
    const mid = p[0];
    if (only && !mid.startsWith(only)) continue;
    jobs.push({ tag: mid, o: { mode: 'verify', match: mid, ...extra } });
  }
}
for (const j of jobs) { delete j.o._; j.out = path.join(dir, `${j.tag}.json`); }
const todo = jobs.filter((j) => !(fs.existsSync(j.out) && fs.statSync(j.out).size > 0));
const { runCheckpoint } = kind === 'checkpoint' ? await import('../lib/checkpoint.mjs') : {};
const { runArena } = kind === 'arena' ? await import('../lib/arena.mjs') : {};
const { runVerify } = kind === 'verify' ? await import('../lib/verify.mjs') : {};
const FULL = 95000;      // 一次运行最多给这么多墙钟（单独起进程跑时 checkpoint / verify 缺省 95 秒、arena 100 秒；没被截断的运行，结果与预算无关）

let done = 0, starved = 0, longest = kind === 'arena' ? 20000 : 12000;
const log = [];
for (const j of todo) {
  const left = deadline - Date.now();
  // 剩下的时间不够跑一次像样的运行就收工（第一个任务至少给它试一次，免得一个特别慢的任务永远轮不上）
  if (left < Math.min(60000, 1.6 * longest) + 4000 && (done > 0 || left < 30000)) break;
  const t0 = Date.now();
  resetCompiled();
  const part = j.out + '.part';
  const budget = Math.max(5000, Math.min(FULL, left - 6000));
  const o = { ...j.o, quiet: true, out: part, 'budget-ms': String(budget) };
  const realLog = console.log;
  console.log = () => {};
  let res = null, err = null;
  try { res = kind === 'checkpoint' ? await runCheckpoint(o) : kind === 'arena' ? await runArena(o) : runVerify(o); } catch (e) { err = e; }
  console.log = realLog;
  const ms = Date.now() - t0;
  if (err) {
    if (/^纯离线范围/.test(String(err.message))) { console.error(`[g0_batch] ${j.tag}：${err.message}`); process.exit(3); }
    if (fs.existsSync(part)) fs.rmSync(part);
    if (budget < FULL && /时间预算/.test(String(err.message))) { log.push(`${j.tag} 本批时间不够（${ms} ms），留给下一批`); starved++; break; }
    log.push(`${j.tag} 出错：${String(err.message).slice(0, 160)}`);
    j.failed = true;
    continue;
  }
  if (res && res.truncated && (budget < FULL || (res.cpuMs ?? ms) < 0.5 * ms)) {
    // 被这一批剩下的时间截断的、或者机器太挤（这次运行拿到的 CPU 不到墙钟的一半）才截断的：不留，下一批从头跑。
    // 给足整份预算、CPU 也拿够了还截断的才留，结果里带 truncated 标记。
    if (fs.existsSync(part)) fs.rmSync(part);
    log.push(`${j.tag} 本批时间不够（${ms} ms），留给下一批`);
    starved++;
    break;
  }
  if (!fs.existsSync(part)) { log.push(`${j.tag} 出错：没有写出结果`); j.failed = true; continue; }
  fs.renameSync(part, j.out);
  done++;
  if (ms > longest) longest = ms;
  log.push(`${j.tag} ${ms} ms${res && res.truncated ? '（时间预算截断）' : ''}`);
}
const left = jobs.filter((j) => !(fs.existsSync(j.out) && fs.statSync(j.out).size > 0));
const failed = todo.filter((j) => j.failed);
for (const l of log) console.log(l);
// 出错的任务不算进「还剩」，否则外层会一直重试；它们单独列出来
const remain = left.length - failed.length;
// 一个都没跑完、原因只是时间不够（槽位排得晚，或机器太挤）：也按「没轮上」报，外层接着排，不算卡住
if (!done && !failed.length && remain > 0 && (!log.length || starved)) console.log(`[g0_batch] ${kind} ${dirName}：没轮上（${starved ? '轮到了但这一批剩下的时间不够跑完一个' : `排到重计算槽位时离截止只剩 ${Math.round((deadline - startAt) / 1000)} 秒`}）；还剩 ${remain} 个`);
else console.log(`[g0_batch] ${kind} ${dirName}：本批跑完 ${done} 个${failed.length ? `，出错 ${failed.length} 个（${failed.map((j) => j.tag).join(' ')}）` : ''}；还剩 ${remain} 个`);
