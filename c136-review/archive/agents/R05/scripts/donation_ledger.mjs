// donation_ledger.mjs — 把一局里「策略日志打印的捐款/调度」与「录像里实际被引擎接受的捐款指令」逐条对账。
// 依据（引擎源码 live_game_js.js，qj.qv）：录像记录点 bC.rg.rh(2,player,pct,to) 位于全部校验（队友、存活、
//   金额>=1、反喂养配额 ao.ei）之后，所以「录像里有的捐款指令 = 引擎真正执行了的捐款」；被拒的不进录像。
// 对账口径：同一个号、同一个 pct、同一个受捐方；日志拍号 t（发令时本地拍号）<= 录像拍号 tick；
//   贪心地把每条录像记录配给「还没配上的、最早的、且 tick - t <= MAXLAG」那条日志；配不上的日志 = 未被执行。
// 用法：node donation_ledger.mjs <matchId> [--maxlag 400] [--json] [--quiet]
// 输出：每个号一段：日志条数、被执行条数、延迟分布；逐条列出（--quiet 时只给汇总）。
import fs from 'node:fs';
import path from 'node:path';
import { loadReplay, timeline } from './replay_cmds.mjs';

const DATA = process.env.C136_DATA || '/agent/repos/c136-data';

export function parseLogDonations(matchId) {
  const p = path.join(DATA, 'bundles', matchId, 'in_game.log');
  const out = [];
  const reD = /\[([^\]]+)\] \[HL-DISPATCH\] t=(\d+) (\w+) pct=(\d+)\/1024 -> ally=(\d+)\(([^)]*)\) boxedIn=(true|false) myBal=(\d+) dMe=(-?\d+) dAlly=(-?\d+)/;
  const reN = /\[([^\]]+)\] \[HL-DONATE\] t=(\d+) ([a-z ]+?) pct=(\d+)\/1024 -> (?:boss|ally)=(\d+)\(([^)]*)\)(?: boxedIn=(true|false))? myBal=(\d+) dMe=(-?\d+)/;
  for (const line of fs.readFileSync(p, 'utf8').split('\n')) {
    let m = reD.exec(line);
    if (m) { out.push({ bot: m[1], t: +m[2], kind: m[3], pct: +m[4], to: +m[5], toName: m[6], boxed: m[7] === 'true', myBal: +m[8], dMe: +m[9], dAlly: +m[10] }); continue; }
    m = reN.exec(line);
    if (m) out.push({ bot: m[1], t: +m[2], kind: m[3].trim().replace(/ /g, '_'), pct: +m[4], to: +m[5], toName: m[6], boxed: m[7] === 'true', myBal: +m[8], dMe: +m[9], dAlly: null });
  }
  return out;
}

export function ledger(matchId, maxLag = 400) {
  const d = loadReplay(matchId);
  const tl = timeline(d);
  const names = d.vu.playerNamesData ? d.vu.playerNamesData.data : [];
  const H = d.vu.humanCount;
  const logs = parseLogDonations(matchId);
  // bot 名 -> 玩家号：按名字后缀匹配（"[APEX] noah88" 以 "noah88" 结尾）
  const idOf = new Map();
  for (const l of logs) {
    if (idOf.has(l.bot)) continue;
    let id = -1;
    // 号名校验：去掉 [前缀] 后全等才算（拆盘时不在录像这一盘里的号 id=-1，其日志捐款不参与对账）
    for (let p = 0; p < H; p++) if (String(names[p] ?? '').replace(/\[[^\]]*\]/g, '').trim().toLowerCase() === l.bot.toLowerCase()) { id = p; break; }
    idOf.set(l.bot, id);
  }
  const rec = tl.cmds.filter((c) => c.id === 2);
  const byPlayer = new Map();
  for (const r of rec) { if (!byPlayer.has(r.player)) byPlayer.set(r.player, []); byPlayer.get(r.player).push({ tick: r.tick, pct: r.dX, to: r.dZ, used: false }); }
  const res = [];
  for (const [bot, id] of idOf) {
    const L = logs.filter((l) => l.bot === bot).map((l) => ({ ...l, execTick: null }));
    const R = (byPlayer.get(id) || []).map((r) => ({ ...r }));
    for (const r of R) {
      for (const l of L) {
        if (l.execTick !== null) continue;
        if (l.pct !== r.pct || l.to !== r.to) continue;
        if (l.t > r.tick) break;
        if (r.tick - l.t > maxLag) continue;
        l.execTick = r.tick; r.used = true; break;
      }
    }
    res.push({ bot, id, logs: L, replayRecs: R });
  }
  return { matchId, H, totalTicks: tl.totalTicks, names, res, allDonations: rec };
}

if (import.meta.url === `file://${process.argv[1]}`) {
  const args = process.argv.slice(2);
  const id = args[0];
  const ml = args.includes('--maxlag') ? +args[args.indexOf('--maxlag') + 1] : 400;
  const quiet = args.includes('--quiet');
  const L = ledger(id, ml);
  if (args.includes('--json')) { console.log(JSON.stringify(L.res)); process.exit(0); }
  let tot = 0, ex = 0, orphan = 0, outN = 0;
  for (const b of L.res) {
    if (b.id < 0) { outN += b.logs.length; console.log(`## ${id} ${b.bot} 不在录像这一盘里（拆盘）：日志捐款=${b.logs.length} 条，无法对账`); continue; }
    const n = b.logs.length, e = b.logs.filter((l) => l.execTick !== null).length;
    const lags = b.logs.filter((l) => l.execTick !== null).map((l) => l.execTick - l.t).sort((a, c) => a - c);
    const un = b.replayRecs.filter((r) => !r.used).length;
    tot += n; ex += e; orphan += un;
    console.log(`## ${id} ${b.bot} (#${b.id}) 日志捐款=${n} 被执行=${e} 未执行=${n - e} 录像里该号捐款=${b.replayRecs.length} 录像有而日志配不上=${un} 延迟(拍) 最小/中位/最大=${lags.length ? `${lags[0]}/${lags[lags.length >> 1]}/${lags[lags.length - 1]}` : '-'}`);
    if (!quiet) {
      for (const l of b.logs) console.log(`  t=${l.t} ${l.kind} pct=${l.pct} -> ${l.to}(${l.toName}) boxed=${l.boxed} myBal=${l.myBal} dMe=${l.dMe} dAlly=${l.dAlly} => ${l.execTick === null ? '未执行' : `执行@${l.execTick} (+${l.execTick - l.t})`}`);
      for (const r of b.replayRecs.filter((x) => !x.used)) console.log(`  [录像独有] tick=${r.tick} pct=${r.pct} -> ${r.to}(${L.names[r.to] ?? ''})`);
    }
  }
  console.log(`# ${id} 合计（只算在录像这一盘里的号） 日志捐款=${tot} 被执行=${ex} (${tot ? (100 * ex / tot).toFixed(1) : '0'}%) 未执行=${tot - ex} 录像独有=${orphan} 全场捐款指令(所有真人)=${L.allDonations.length}${outN ? ` ；另有不在录像盘内的号的日志捐款 ${outN} 条未对账` : ''}`);
}
