#!/usr/bin/env node
// slice.mjs — 从数据 A 的原始日志和结算里切出一局，写成对局包（R01 的对局包发布之前自用）。
// 用法：node scripts/slice.mjs            # 只打印全部局的索引核对表，并写 out/index.json
//       node scripts/slice.mjs G02 G05 G08  # 另外写 out/<局>/squad.log、results.jsonl、slice.json
//
// 切法：
//   1. 局的边界 = [HL-GAME-INIT] 的 (mode,map,mapSeed) 发生变化（lib.mjs: indexGames）。
//   2. 结算记录与日志的对应：日志里每条 "[RESULT <bot>] ... place= peak= team=" 与 results.jsonl 中
//      同一 bot、同 place、同 peak 的记录一一匹配（按时间顺序消费），不靠人工指定时间窗。
//   3. squad.log 每行前缀 "<原始行号>|"，丢弃与连接/验证/身份有关的行（不在范围内）。
import fs from 'node:fs';
import path from 'node:path';
import { loadRawLog, loadRawResults, indexGames, inScope, OUT_DIR, ensureDir } from './lib.mjs';

const lines = loadRawLog();
const results = loadRawResults();
const games = indexGames(lines);

// 结算匹配
const used = new Set();
const resRe = /^\[RESULT \[Nope\] ([^\]]+)\] result=(\w+) event=(\w+) place=(\d+) peak=(\d+) team=(.*)$/;
for (const g of games) {
  g.results = [];
  for (let i = g.start; i <= g.end; i++) {
    const m = resRe.exec(lines[i - 1]);
    if (!m) continue;
    const bot = '[Nope] ' + m[1];
    const idx = results.findIndex((r, k) => !used.has(k) && r.bot === bot && r.place === +m[4] && r.peak === +m[5] && r.result === m[2]);
    if (idx < 0) { console.error(`!! 未匹配到结算记录：${g.label} 行 ${i} ${lines[i - 1].slice(0, 80)}`); continue; }
    used.add(idx);
    g.results.push({ line: i, rec: results[idx], recIndex: idx + 1 });
  }
}
if (used.size !== results.length) console.error(`!! results.jsonl 有 ${results.length - used.size} 条没有对应的日志 RESULT 行`);

const index = games.map((g) => {
  const recs = g.results.map((r) => r.rec);
  const ats = recs.map((r) => r.at).sort();
  const teams = new Set();
  for (const r of recs) if (r.team && r.team.totals) for (const k of Object.keys(r.team.totals)) teams.add(k);
  return {
    label: g.label, mode: g.mode, map: g.map, mapSeed: g.mapSeed, humans: g.players,
    lines: [g.start, g.end], bots: Object.keys(g.bots).length, results: recs.length,
    firstAt: ats[0], lastAt: ats[ats.length - 1],
    land: recs[0] && recs[0].land, players: recs[0] && recs[0].players,
    mine: [...new Set(recs.filter((r) => r.team).map((r) => r.team.mine))],
    bestAtEnd: (recs.filter((r) => r.team).slice(-1)[0] || {}).team?.best,
    teamKeysSeen: [...teams].sort(),
    maxTick: Math.max(...recs.map((r) => r.tick || 0)),
    outcomes: recs.map((r) => r.result).join(','),
  };
});

ensureDir(OUT_DIR);
fs.writeFileSync(path.join(OUT_DIR, 'index.json'), JSON.stringify(index, null, 1) + '\n');
console.log('label mode map seed humans lines            bots res firstAt..lastAt(UTC)                 land   mine best maxTick teamKeys outcomes');
for (const x of index) {
  console.log([x.label, x.mode, x.map, x.mapSeed, x.humans, `${x.lines[0]}-${x.lines[1]}`.padEnd(11), x.bots, x.results,
    `${(x.firstAt || '').slice(11, 19)}..${(x.lastAt || '').slice(11, 19)}`, x.land, x.mine.join('/'), x.bestAtEnd, x.maxTick,
    x.teamKeysSeen.join(''), x.outcomes].join('  '));
}

for (const want of process.argv.slice(2)) {
  const g = games.find((x) => x.label === want);
  if (!g) { console.error('没有这一局：' + want); process.exitCode = 1; continue; }
  const dir = path.join(OUT_DIR, want);
  ensureDir(dir);
  const out = [];
  let dropped = 0;
  for (let i = g.start; i <= g.end; i++) {
    const l = lines[i - 1];
    if (!inScope(l)) { dropped++; continue; }
    out.push(i + '|' + l);
  }
  fs.writeFileSync(path.join(dir, 'squad.log'), out.join('\n') + '\n');
  fs.writeFileSync(path.join(dir, 'results.jsonl'),
    g.results.map((r) => JSON.stringify({ logLine: r.line, resultsJsonlLine: r.recIndex, ...r.rec })).join('\n') + '\n');
  fs.writeFileSync(path.join(dir, 'slice.json'), JSON.stringify({
    label: g.label, source: 'c116-winrate/data/G01-G09-squad.log + G01-G09-results.jsonl @ cursor/c116-winrate-liaison-b3bc',
    rawLineRange: [g.start, g.end], keptLines: out.length, droppedOutOfScopeLines: dropped,
    mode: g.mode, map: g.map, mapSeed: g.mapSeed, humansAtInit: g.players,
    bots: g.bots, resultsMatched: g.results.length,
  }, null, 1) + '\n');
  console.log(`${want}: 原始行 ${g.start}-${g.end}，保留 ${out.length} 行，丢弃范围外 ${dropped} 行，结算 ${g.results.length} 条 -> ${dir}`);
}
