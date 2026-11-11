// cmd_latency.mjs — 量「策略发令 → 引擎执行」的延迟（拍）。
// 方法：日志里 [HL-OPENING] t=<发令拍> … spend=X/bal 这一句对应一条打无主地的进攻指令，
//   pct = ceil(X*1024/bal) - 1（Strategy.send 的换算，v27-team-c116.js 第 479~487 行）。
//   在录像命令流里找同一个号、目标=无主地(512)、pct 相同、tick >= t 的第一条记录，延迟 = tick - t。
//   录像只记通过校验的指令（见 donation_ledger.mjs 头注），所以配不上的 = 被引擎拒绝或 pct 口径不一致。
// 用法：node cmd_latency.mjs <matchId> [...matchId] [--detail]
// 输出：每个号：开局指令数、配上数、延迟 最小/中位/p90/最大；--detail 逐条。
import fs from 'node:fs';
import path from 'node:path';
import { loadReplay, timeline } from './replay_cmds.mjs';

const DATA = process.env.C136_DATA || '/agent/repos/c136-data';
const args = process.argv.slice(2);
const detail = args.includes('--detail');
const ids = args.filter((a) => !a.startsWith('--'));
const q = (arr, p) => (arr.length ? arr[Math.min(arr.length - 1, Math.floor(p * arr.length))] : null);

for (const id of ids) {
  let d;
  try { d = loadReplay(id); } catch (e) { console.log(`# ${id} 无录像`); continue; }
  const tl = timeline(d);
  const names = d.vu.playerNamesData ? d.vu.playerNamesData.data : [];
  const H = d.vu.humanCount;
  const re = /\[([^\]]+)\] \[HL-OPENING\] t=(\d+) cyc=(\d+) DP expand rings=(\d+) spend=(\d+)\/(\d+) terr=(\d+)/;
  const logs = [];
  for (const line of fs.readFileSync(path.join(DATA, 'bundles', id, 'in_game.log'), 'utf8').split('\n')) {
    const m = re.exec(line);
    if (m) logs.push({ bot: m[1], t: +m[2], cyc: +m[3], spend: +m[5], bal: +m[6], pct: Math.ceil((+m[5]) * 1024 / (+m[6])) - 1 });
  }
  const bots = [...new Set(logs.map((l) => l.bot))];
  const all = [];
  for (const bot of bots) {
    let pid = -1;
    for (let p = 0; p < H; p++) if (String(names[p] ?? '').replace(/\[[^\]]*\]/g, '').trim().toLowerCase() === bot.toLowerCase()) { pid = p; break; }
    if (pid < 0) { console.log(`${id} ${bot} 不在录像这一盘里（拆盘），跳过`); continue; }
    const R = tl.cmds.filter((c) => c.id === 1 && c.player === pid && c.dZ === 512).map((c) => ({ tick: c.tick, pct: c.dX, used: false }));
    const L = logs.filter((l) => l.bot === bot);
    const lags = [];
    let unmatched = 0;
    for (const l of L) {
      const r = R.find((x) => !x.used && x.tick >= l.t && x.pct === l.pct && x.tick - l.t <= 600);
      if (r) { r.used = true; l.exec = r.tick; lags.push(r.tick - l.t); } else { l.exec = null; unmatched++; }
    }
    const s = [...lags].sort((a, b) => a - b);
    all.push(...lags);
    console.log(`${id} ${bot} (#${pid}) 开局指令=${L.length} 配上=${lags.length} 配不上=${unmatched} 延迟 最小/中位/p90/最大=${s.length ? `${s[0]}/${q(s, 0.5)}/${q(s, 0.9)}/${s[s.length - 1]}` : '-'}`);
    if (detail) for (const l of L) console.log(`   t=${l.t} cyc=${l.cyc} pct=${l.pct} spend=${l.spend}/${l.bal} => ${l.exec === null ? '配不上' : `执行@${l.exec} (+${l.exec - l.t})`}`);
  }
  const s = all.sort((a, b) => a - b);
  console.log(`# ${id} 全队 配上=${s.length} 延迟 最小/中位/p90/最大=${s.length ? `${s[0]}/${q(s, 0.5)}/${q(s, 0.9)}/${s[s.length - 1]}` : '-'} 其中 >=35拍(约2秒) ${s.filter((x) => x >= 35).length} 条, >=90拍(约5秒) ${s.filter((x) => x >= 90).length} 条`);
}
