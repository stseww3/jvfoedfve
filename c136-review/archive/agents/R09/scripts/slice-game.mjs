#!/usr/bin/env node
// slice-game.mjs — 从 G01-G09-squad.log / G01-G09-results.jsonl 里切出一局，写成自制对局包。
//
// 用法：node c136-review/agents/R09/scripts/slice-game.mjs G03 [G06 ...]
// 输出：c136-review/agents/R09/out/<局>/
//   squad.log      本局范围内的日志行，每行前面是原始文件行号 + TAB（连接、验证类的行不收，只计数）
//   results.jsonl  本局各号的结算记录（按日志里的 RESULT 行一一对上）
//   events.jsonl   解析后的事件（一行一个 JSON，含原始行号）
//   traj.csv       每号每 90 拍一条的 HL-TICK 快照
//   card.json      自制对局卡（只含数据里直接读得到的字段）
//
// 切法：按 HL-GAME-INIT 的 mapSeed 分段；一局 = 上一局最后一条 RESULT 的下一行 … 本局最后一条 RESULT。

import fs from 'node:fs';
import path from 'node:path';
import {
  loadLogLines, loadResults, segments, gameEvents, joinResults, isOutOfScope, ensureDir, writeCsv, OUT_ROOT, LOG_FILE, RESULTS_FILE,
} from './lib.mjs';

const labels = process.argv.slice(2);
if (!labels.length) {
  console.error('usage: slice-game.mjs G03 [G06 ...]');
  process.exit(2);
}

const lines = loadLogLines();
const results = loadResults();
const segs = segments(lines);

for (const label of labels) {
  const seg = segs.find((s) => s.label === label);
  if (!seg) throw new Error(`no segment ${label}`);
  const dir = ensureDir(path.join(OUT_ROOT, label));
  const { events, connLines } = gameEvents(lines, seg);

  const kept = [];
  for (let n = seg.start; n <= seg.end; n++) {
    const l = lines[n - 1];
    if (!l || isOutOfScope(l)) continue;
    kept.push(`${n}\t${l}`);
  }
  fs.writeFileSync(path.join(dir, 'squad.log'), kept.join('\n') + '\n');
  fs.writeFileSync(path.join(dir, 'events.jsonl'), events.map((e) => JSON.stringify(e)).join('\n') + '\n');

  const joined = joinResults(events, results);
  fs.writeFileSync(
    path.join(dir, 'results.jsonl'),
    joined.map((j) => JSON.stringify({ _logLine: j.logLine, ...j.rec })).join('\n') + '\n'
  );

  const ticks = events.filter((e) => e.kind === 'tick');
  writeCsv(path.join(dir, 'traj.csv'), ticks, [
    't', 'bot', 'terr', 'pct', 'bal', 'dens', 'nb', 'neut', 'cmds', 'boats', 'avgMs', 'maxMs', 'skip', 'line',
  ]);

  const inits = events.filter((e) => e.kind === 'init');
  const coords = events.filter((e) => e.kind === 'coord');
  const bots = {};
  for (const e of inits) bots[e.bot] = { me: e.me, initLine: e.line };
  for (const j of joined) {
    const r = j.rec;
    const b = r.bot.replace(/^\[Nope\] /, '');
    bots[b] = bots[b] || { me: null, initLine: null };
    Object.assign(bots[b], {
      port: r.port, result: r.result, event: r.event, tick: r.tick, seconds: r.seconds, place: r.place, alivePlayers: r.alivePlayers,
      territory: r.territory, lastTerritory: r.lastTerritory, lastRank: r.lastRank, peak: r.peak, balance: r.balance, sent: r.sent,
      accepted: r.accepted, teamMine: r.team ? r.team.mine : null, teamBest: r.team ? r.team.best : null,
      teamTotals: r.team ? r.team.totals : null, at: r.at, meIdInResult: r.me ? r.me.id : null, strategy: r.strategy, ext: r.ext,
      resultLogLine: j.logLine, resultsLine: r._resultsLine,
    });
  }
  const teamKeys = new Set();
  for (const j of joined) if (j.rec.team && j.rec.team.totals) for (const k of Object.keys(j.rec.team.totals)) teamKeys.add(k);
  const mine = [...new Set(joined.map((j) => (j.rec.team ? j.rec.team.mine : null)).filter((x) => x !== null))];
  const lands = [...new Set(joined.map((j) => j.rec.land))];
  const kinds = {};
  for (const e of events) kinds[e.kind] = (kinds[e.kind] || 0) + 1;

  const card = {
    label,
    source: { log: path.basename(LOG_FILE), results: path.basename(RESULTS_FILE), branch: 'cursor/c116-winrate-liaison-b3bc@d9a56dcde66f' },
    logRange: { start: seg.start, end: seg.end, firstInit: seg.firstInit, lastResult: seg.lastResult },
    init: { mode: seg.mode, map: seg.map, mapSeed: +seg.seed, playersField: seg.players },
    mapWH: coords.length ? { W: coords[0].W, H: coords[0].H } : null,
    land: lands.length === 1 ? lands[0] : lands,
    playersInResults: [...new Set(joined.map((j) => j.rec.players))],
    botsWithInit: inits.length,
    botsWithResult: joined.length,
    teamKeysSeenInTotals: [...teamKeys].sort(),
    ourTeamIdsSeen: mine,
    resultsSummary: joined.reduce((a, j) => { a[j.rec.result] = (a[j.rec.result] || 0) + 1; return a; }, {}),
    firstResultAt: joined.map((j) => j.rec.at).sort()[0] || null,
    lastResultAt: joined.map((j) => j.rec.at).sort().slice(-1)[0] || null,
    maxTick: Math.max(...joined.map((j) => j.rec.tick || 0)),
    eventKinds: kinds,
    outOfScopeLineCounts: connLines,
    bots,
  };
  fs.writeFileSync(path.join(dir, 'card.json'), JSON.stringify(card, null, 2) + '\n');
  console.log(`${label}: lines ${seg.start}-${seg.end}, kept ${kept.length}, events ${events.length}, ticks ${ticks.length}, results ${joined.length} -> ${dir}`);
}
