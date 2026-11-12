#!/usr/bin/env node
// g0_batch.mjs — 一个进程里按清单连着跑多次 checkpoint / arena / verify（每次运行各写各的结果文件）。
//
// 为什么要它：这台机器的重计算槽位是全机共用的，每跑一次都要排一次队；一次断面只要几秒，排队却常常要好几分钟。
// 把几十次运行放进同一个进程，排一次队跑一批，每批仍然不超过重计算闸门的 110 秒。
// 与单独起进程逐个跑的结果相同：每次运行之前把策略文件重新编译一遍（sandbox.resetCompiled），随机数都是 (种子, 席位, 拍) 的散列、
// 没有跨运行的状态。拆掉候选臂之前入库的那批结果是单独起进程逐个跑的，tools/old_vs_new.sh 拿它们和这里批量跑出来的同名结果
// 逐字段核对（除计时外应当完全相同）。
//
// 用法（在 c136-review/agents/R06 下，经重计算闸门）：
//   node sim-v2/tools/g0_batch.mjs checkpoint <结果目录名> <清单文件> [--deadline 截止时刻的毫秒时间戳] [--only 标签前缀]
//       清单每行：<标签> <局> <t0> <len> <策略> <通道> [其余开关]        → sim-v2/calib/<目录>/<标签>.json
//   node sim-v2/tools/g0_batch.mjs arena <结果目录名> <清单文件> --len 4300 --channel C2 [其余开关原样传给 arena] [--deadline …]
//       清单每行：<局> <策略>                                          → sim-v2/calib/<目录>/<局>.json
//   node sim-v2/tools/g0_batch.mjs verify <结果目录名> <清单文件> [--deadline …]
//       清单每行：<局> […]（只用第一列）                                → sim-v2/calib/<目录>/<局>.json
//   node sim-v2/tools/g0_batch.mjs plan <计划文件> [--deadline …]
//       计划文件每行就是上面三种调用之一的参数（checkpoint|arena|verify <结果目录名> <清单文件> [开关…]），按先后排优先级：
//       排到一次槽位，从第一行起接着往下跑，前面的清单跑完了就跑后面的，直到这一批的时间用完。
// 已有结果文件的跳过。最后一行打印「还剩 N 个」，外层循环看到 0 就停。
// 截止时刻 = min(--deadline, 本进程起跑后 104 秒)：前者是外层 timeout 120 的界，后者是重计算闸门 110 秒的界（它从排到槽位起算）。
// 一次运行如果被本批剩下的时间截断，结果不留，留给下一批从头跑。结果先写到 <名字>.part，跑完才改名，半路被杀留不下半个文件。
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { parseArgs } from '../lib/util.mjs';
import { resetCompiled } from '../lib/sandbox.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const SIMV2 = path.resolve(HERE, '..');
const KINDS = ['checkpoint', 'arena', 'verify'];
const [kind0, ...argv0] = process.argv.slice(2);
const usage = () => { console.error('用法：g0_batch.mjs checkpoint|arena|verify <结果目录名> <清单文件> [开关…]　或　g0_batch.mjs plan <计划文件>'); process.exit(2); };
if (![...KINDS, 'plan'].includes(kind0) || !argv0.length) usage();

const startAt = Date.now();
const FULL = 95000;      // 一次运行最多给这么多墙钟（单独起进程跑时 checkpoint / verify 缺省 95 秒、arena 100 秒；没被截断的运行，结果与预算无关）

// 一行调用 → { kind, dirName, jobs }
function readList(kind, dirName, listFile, extra0) {
  const extra = { ...extra0 };
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
  return { kind, dirName, jobs };
}

const steps = [];
let deadlineArg = Infinity;
if (kind0 === 'plan') {
  const [planFile, ...rest] = argv0;
  const ex = parseArgs(rest);
  if (ex.deadline) deadlineArg = +ex.deadline;
  for (const line of fs.readFileSync(planFile, 'utf8').split('\n')) {
    const s = line.trim();
    if (!s || s.startsWith('#')) continue;
    const [k, d, l, ...r] = s.split(/\s+/);
    if (!KINDS.includes(k) || !d || !l) { console.error(`[g0_batch] 计划文件里这一行看不懂：${s}`); process.exit(2); }
    steps.push(readList(k, d, l, parseArgs(r)));
  }
} else {
  const [dirName, listFile, ...rest] = argv0;
  if (!dirName || !listFile) usage();
  const ex = parseArgs(rest);
  if (ex.deadline) deadlineArg = +ex.deadline;
  steps.push(readList(kind0, dirName, listFile, ex));
}
const deadline = Math.min(deadlineArg, startAt + 104000);
const has = (j) => fs.existsSync(j.out) && fs.statSync(j.out).size > 0;

const runners = {};
async function runnerOf(kind) {
  if (!runners[kind]) {
    runners[kind] = kind === 'checkpoint' ? (await import('../lib/checkpoint.mjs')).runCheckpoint
      : kind === 'arena' ? (await import('../lib/arena.mjs')).runArena
        : (await import('../lib/verify.mjs')).runVerify;
  }
  return runners[kind];
}

// 同一份清单可能有两个进程同时在跑（比如队列被重启、旧的一批还没退出）。每个任务开跑前先占一个 .claim 文件，
// 别的进程看到 150 秒以内的 .claim 就跳过这个任务；跑完（或失败）就删掉。超过 150 秒的 .claim 当作上一个进程被杀留下的，接手。
const claimOf = (j) => j.out + '.claim';
function claim(j) {
  const c = claimOf(j);
  try { fs.writeFileSync(c, String(process.pid), { flag: 'wx' }); return true; } catch (e) {
    try { if (Date.now() - fs.statSync(c).mtimeMs > 150000) { fs.writeFileSync(c, String(process.pid)); return true; } } catch (e2) { /* 刚好被删掉：留给下一批 */ }
    return false;
  }
}
const unclaim = (j) => { try { fs.rmSync(claimOf(j)); } catch (e) { /* 已经没有了 */ } };

// 每跑完一次，在 calib/run-log.jsonl 里记一行：哪个结果、什么时候、这个进程的 nice 值。
// 经重计算闸门（run-heavy.sh）跑的进程 nice 是 19；不是 19 的就是没经闸门跑的。g0_report.mjs 按这份流水数两种各有多少次。
const NICE = (() => { try { return os.getPriority(); } catch (e) { return null; } })();
function runLog(st, j, ms) {
  try {
    fs.appendFileSync(path.join(SIMV2, 'calib', 'run-log.jsonl'),
      JSON.stringify({ dir: st.dirName, tag: j.tag, at: new Date().toISOString(), ms, nice: NICE, pid: process.pid, ppid: process.ppid }) + '\n');
  } catch (e) { /* 流水写不进去不影响结果 */ }
}

let done = 0, starved = 0, stop = false, busy = 0;
const longest = { checkpoint: 12000, arena: 20000, verify: 12000 };
const log = [], failedAll = [];
for (const st of steps) {
  if (stop) break;
  const todo = st.jobs.filter((j) => !has(j));
  if (!todo.length) continue;
  const run = await runnerOf(st.kind);
  for (const j of todo) {
    const left = deadline - Date.now();
    // 剩下的时间不够跑一次像样的运行就收工（第一个任务至少给它试一次，免得一个特别慢的任务永远轮不上）
    if (left < Math.min(60000, 1.6 * longest[st.kind]) + 4000 && (done > 0 || left < 30000)) { stop = true; break; }
    if (has(j)) continue;                    // 这一批开始之后别的进程已经跑完了它
    if (!claim(j)) { busy++; continue; }     // 别的进程正在跑它
    try {
    const t0 = Date.now();
    resetCompiled();
    const part = j.out + '.part';
    const budget = Math.max(5000, Math.min(FULL, left - 6000));
    const o = { ...j.o, quiet: true, out: part, 'budget-ms': String(budget) };
    const realLog = console.log;
    console.log = () => {};
    let res = null, err = null;
    try { res = await run(o); } catch (e) { err = e; }
    console.log = realLog;
    const ms = Date.now() - t0;
    if (err) {
      if (/^纯离线范围/.test(String(err.message))) { console.error(`[g0_batch] ${j.tag}：${err.message}`); process.exit(3); }
      if (fs.existsSync(part)) fs.rmSync(part);
      if (budget < FULL && /时间预算/.test(String(err.message))) { log.push(`${j.tag} 本批时间不够（${ms} ms），留给下一批`); starved++; stop = true; break; }
      log.push(`${j.tag} 出错：${String(err.message).slice(0, 160)}`);
      j.failed = true; failedAll.push(j);
      continue;
    }
    if (res && res.truncated && (budget < FULL || (res.cpuMs ?? ms) < 0.5 * ms)) {
      // 被这一批剩下的时间截断的、或者机器太挤（这次运行拿到的 CPU 不到墙钟的一半）才截断的：不留，下一批从头跑。
      // 给足整份预算、CPU 也拿够了还截断的才留，结果里带 truncated 标记。
      if (fs.existsSync(part)) fs.rmSync(part);
      log.push(`${j.tag} 本批时间不够（${ms} ms），留给下一批`);
      starved++; stop = true;
      break;
    }
    if (!fs.existsSync(part)) { log.push(`${j.tag} 出错：没有写出结果`); j.failed = true; failedAll.push(j); continue; }
    fs.renameSync(part, j.out);
    runLog(st, j, ms);
    done++;
    if (ms > longest[st.kind]) longest[st.kind] = ms;
    log.push(`${j.tag} ${ms} ms${res && res.truncated ? '（时间预算截断）' : ''}`);
    } finally { unclaim(j); }
  }
}
for (const l of log) console.log(l);
// 出错的任务不算进「还剩」，否则外层会一直重试；它们单独列出来。本进程没轮到的清单里以前出过错的任务仍算「还剩」（下一批会再试一次）。
const remain = steps.reduce((n, st) => n + st.jobs.filter((j) => !has(j) && !j.failed).length, 0);
const name = kind0 === 'plan' ? `plan ${path.basename(argv0[0])}` : `${kind0} ${argv0[0]}`;
const perStep = kind0 === 'plan' ? `（${steps.map((st) => st.jobs.filter((j) => !has(j) && !j.failed).length).join(' + ')}）` : '';
// 一个都没跑完、原因只是时间不够（槽位排得晚，或机器太挤）：也按「没轮上」报，外层接着排，不算卡住
if (!done && !failedAll.length && remain > 0 && busy > 0 && !starved && !log.length) console.log(`[g0_batch] ${name}：没轮上（清单上剩下的 ${busy} 个任务都有别的进程正在跑）；还剩 ${remain} 个${perStep}`);
else if (!done && !failedAll.length && remain > 0 && (!log.length || starved)) console.log(`[g0_batch] ${name}：没轮上（${starved ? '轮到了但这一批剩下的时间不够跑完一个' : `排到重计算槽位时离截止只剩 ${Math.round((deadline - startAt) / 1000)} 秒`}）；还剩 ${remain} 个${perStep}`);
else console.log(`[g0_batch] ${name}：本批跑完 ${done} 个${failedAll.length ? `，出错 ${failedAll.length} 个（${failedAll.map((j) => j.tag).join(' ')}）` : ''}；还剩 ${remain} 个${perStep}`);
