// exec_layer_scan.mjs — 全部对局的「执行层」体检：策略发令到引擎执行的延迟、我方号离场(leave)时点、捐款实际执行率。
// 证据来源：replay.txt 的命令流（只含通过引擎校验的指令，见 donation_ledger.mjs 头注）+ in_game.log。
// 每局一行 TSV：
//   matchId cohort endTick replayTicks nBots
//   openN openMatched lagMed lagP90 lagMax lag>=35 lag>=90      ← [HL-OPENING] 指令的执行延迟（拍）
//   leavers leaveTicks(号:录像离场拍/本地最后一拍)                ← 录像里我方号的 leave 指令
//   donLogged donExecuted execPct                                ← 日志捐款/调度条数 vs 录像里真正执行的条数
// 用法：node exec_layer_scan.mjs [matchId ...] > out/exec-layer.tsv   （不带参数 = 全部 bundles）
import fs from 'node:fs';
import path from 'node:path';
import { loadReplay, timeline } from './replay_cmds.mjs';
import { parseLogDonations } from './donation_ledger.mjs';

const DATA = process.env.C136_DATA || '/agent/repos/c136-data';
const ids = process.argv.slice(2).length ? process.argv.slice(2) : fs.readdirSync(path.join(DATA, 'bundles')).sort();
const q = (arr, p) => (arr.length ? arr[Math.min(arr.length - 1, Math.floor(p * arr.length))] : '');

console.log(['matchId', 'cohort', 'endTick', 'replayTicks', 'nBots', 'openN', 'openMatched', 'lagMed', 'lagP90', 'lagMax', 'lagGE35', 'lagGE90',
  'leavers', 'leaveDetail', 'donLogged', 'donExecuted', 'execPct'].join('\t'));
for (const id of ids) {
  const dir = path.join(DATA, 'bundles', id);
  if (!fs.existsSync(path.join(dir, 'replay.txt')) || !fs.existsSync(path.join(dir, 'in_game.log'))) continue;
  let d;
  try { d = loadReplay(id); } catch (e) { continue; }
  const card = JSON.parse(fs.readFileSync(path.join(dir, 'card.json'), 'utf8'));
  const tl = timeline(d);
  const H = d.vu.humanCount;
  const names = d.vu.playerNamesData ? d.vu.playerNamesData.data : [];
  const text = fs.readFileSync(path.join(dir, 'in_game.log'), 'utf8').split('\n');
  const meOf = new Map(), lastT = new Map();
  const opens = [];
  const reInit = /\[([^\]]+)\] \[HL-GAME-INIT\].* me=(\d+)/;
  const reTick = /\[([^\]]+)\] \[HL-TICK\] t=(\d+) /;
  const reOpen = /\[([^\]]+)\] \[HL-OPENING\] t=(\d+) cyc=(\d+) DP expand rings=(\d+) spend=(\d+)\/(\d+)/;
  for (const line of text) {
    let m = reInit.exec(line);
    if (m) { if (!meOf.has(m[1])) meOf.set(m[1], +m[2]); continue; }
    m = reTick.exec(line);
    if (m) { lastT.set(m[1], Math.max(lastT.get(m[1]) ?? 0, +m[2])); continue; }
    m = reOpen.exec(line);
    if (m) opens.push({ bot: m[1], t: +m[2], pct: Math.ceil((+m[5]) * 1024 / (+m[6])) - 1 });
  }
  const bots = new Set([...meOf.keys(), ...lastT.keys()]);
  const pid = (bot) => {
    if (meOf.has(bot)) return meOf.get(bot);
    for (let p = 0; p < H; p++) if (String(names[p] ?? '').trim().toLowerCase().endsWith(bot.toLowerCase())) return p;
    return -1;
  };
  // 开局延迟
  const lags = [];
  const byP = new Map();
  for (const c of tl.cmds) if (c.id === 1 && c.dZ === 512) { if (!byP.has(c.player)) byP.set(c.player, []); byP.get(c.player).push({ tick: c.tick, pct: c.dX, used: false }); }
  for (const o of opens) {
    const R = byP.get(pid(o.bot)) || [];
    const r = R.find((x) => !x.used && x.tick >= o.t && x.pct === o.pct && x.tick - o.t <= 600);
    if (r) { r.used = true; lags.push(r.tick - o.t); }
  }
  lags.sort((a, b) => a - b);
  // 离场
  const leave = [];
  for (const c of tl.cmds) if (c.id === 8 || c.id === 9) {
    for (const b of bots) if (pid(b) === c.player && c.tick >= 0) leave.push(`${b}:${c.tick}/${lastT.get(b) ?? '?'}`);
  }
  // 捐款执行率
  const logs = parseLogDonations(id);
  const recBy = new Map();
  for (const c of tl.cmds) if (c.id === 2) { const k = `${c.player}|${c.dX}|${c.dZ}`; if (!recBy.has(k)) recBy.set(k, []); recBy.get(k).push({ tick: c.tick, used: false }); }
  let ex = 0;
  for (const l of logs) {
    const R = recBy.get(`${pid(l.bot)}|${l.pct}|${l.to}`) || [];
    const r = R.find((x) => !x.used && x.tick >= l.t && x.tick - l.t <= 600);
    if (r) { r.used = true; ex++; }
  }
  console.log([id, card.cohort, card.outcome?.endTick ?? '', tl.totalTicks, bots.size, opens.length, lags.length, q(lags, 0.5), q(lags, 0.9),
    lags.length ? lags[lags.length - 1] : '', lags.filter((x) => x >= 35).length, lags.filter((x) => x >= 90).length,
    leave.length, leave.join(' '), logs.length, ex, logs.length ? (100 * ex / logs.length).toFixed(1) : ''].join('\t'));
}
