#!/usr/bin/env node
// hdrdiff.mjs — 录像头里和「内置 AI 的难度」有关的字段，逐局列出来再汇总。
//
//   bash c136-review/tools/run-heavy.sh node c136-review/agents/R08/scripts/hdrdiff.mjs
//
// 只读发现集（manifest.jsonl 里 split == "discovery" 的局）的 bundles/<局>/replay.txt。
// 输出 out/_cross/hdrdiff.json（逐局）和 out/_cross/hdrdiff.txt（汇总）。跑不完会在 95 秒处停下、存盘，再跑一次接着做。
//
// 为什么要这张表：重放器（src/tools/sim_replay.mjs L139、src/sim/tools/c102-replay-lib.mjs L146、本目录 resim_r08.mjs L332）
// 在多人房一律按 difficulty = 0 建局（`H > 1 ? 0 : vu.botDifficultyValue`）。xtruth.py 按这个设置重演，
// 89 局 16154 行日志快照逐位对上。这里把录像头自己写的难度字段列出来，看它和「一律按 0」是什么关系。
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { decodeReplay } from '/agent/repos/c136-data/src/sim/tools/c102-replay-lib.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const OUT = path.resolve(HERE, '..', 'out', '_cross');
const DATA = process.env.C136_DATA || '/agent/repos/c136-data';
const t0 = Date.now();

const ids = fs.readFileSync(path.join(DATA, 'manifest.jsonl'), 'utf8').split('\n').filter(Boolean)
  .map((l) => JSON.parse(l)).filter((m) => m.split === 'discovery').map((m) => m.matchId).sort();

const jsonPath = path.join(OUT, 'hdrdiff.json');
let done = {};
try { done = JSON.parse(fs.readFileSync(jsonPath, 'utf8')).matches || {}; } catch { done = {}; }

let stopped = false;
for (const mid of ids) {
  if (done[mid]) continue;
  if (Date.now() - t0 > 95000) { stopped = true; break; }
  const p = path.join(DATA, 'bundles', mid, 'replay.txt');
  if (!fs.existsSync(p)) { done[mid] = { replay: false }; continue; }
  try {
    const vu = decodeReplay(fs.readFileSync(p, 'utf8')).vu;
    const H = vu.humanCount;
    const data = vu.botDifficultyData ? Array.from(vu.botDifficultyData).slice(H, vu.playerCount) : [];
    const hist = {};
    for (const v of data) hist[v] = (hist[v] || 0) + 1;
    done[mid] = {
      replay: true,
      humanCount: H,
      playerCount: vu.playerCount,
      neutralBots: vu.neutralBots,
      botDifficultyType: vu.botDifficultyType,
      botDifficultyValue: vu.botDifficultyValue,
      botDifficultyTeam: vu.botDifficultyTeam ? Array.from(vu.botDifficultyTeam) : null,
      botDifficultyDataHist: hist,
    };
  } catch (e) {
    done[mid] = { replay: true, error: String(e.message || e).slice(0, 160) };
  }
}

fs.mkdirSync(OUT, { recursive: true });
fs.writeFileSync(jsonPath, JSON.stringify({ matches: done }, null, 1));

const rows = Object.entries(done).filter(([, v]) => v.replay && !v.error);
const cnt = (f) => {
  const c = {};
  for (const [, v] of rows) { const k = f(v); c[k] = (c[k] || 0) + 1; }
  return Object.entries(c).sort((a, b) => b[1] - a[1]).map(([k, n]) => `${k}：${n} 局`).join('；');
};
const lines = [];
lines.push(`[HD-A] 录像头里的内置 AI 难度字段（发现集 ${ids.length} 局；有录像且解得开的 ${rows.length} 局；没录像 ${Object.values(done).filter((v) => !v.replay).length} 局；解不开 ${Object.values(done).filter((v) => v.error).length} 局${stopped ? '；本轮没跑完，再跑一次' : ''}）`);
lines.push(`  多人房（humanCount > 1）：${rows.filter(([, v]) => v.humanCount > 1).length} 局`);
lines.push(`  botDifficultyType：${cnt((v) => v.botDifficultyType)}`);
lines.push(`  botDifficultyValue：${cnt((v) => v.botDifficultyValue)}`);
lines.push(`  neutralBots：${cnt((v) => v.neutralBots)}`);
lines.push(`  botDifficultyTeam（各队一格）全是 0 的：${rows.filter(([, v]) => (v.botDifficultyTeam || []).every((x) => x === 0)).length} 局`);
lines.push(`  botDifficultyData（AI 席位逐个一格）只有一个取值的：${rows.filter(([, v]) => Object.keys(v.botDifficultyDataHist).length <= 1).length} 局；取值分布：${cnt((v) => Object.keys(v.botDifficultyDataHist).sort().join('/') || '空')}`);
lines.push('  说明：重放器在多人房不读这些字段，一律按难度 0 建局；按 0 重演和日志逐位对上的局数见 xtruth.txt 开头。');
fs.writeFileSync(path.join(OUT, 'hdrdiff.txt'), lines.join('\n') + '\n');
console.log(lines.join('\n'));
