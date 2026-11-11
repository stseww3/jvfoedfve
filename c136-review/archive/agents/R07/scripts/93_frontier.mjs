#!/usr/bin/env node
// 93_frontier.mjs — R07：全场每个真人的边界贴着什么（无主地 / 内置 AI / 敌方真人 / 队友 / 水），以及「够得着的内置 AI 的地」有多少。
//
// 用来回答「抢内置 AI 那一段，我方落后是因为身边没有 AI 的地，还是有地不打」：
//   对每个采样拍、每个在场的真人，扫一遍它的边界格（g.border[p]），按四邻分类：
//     贴无主地（px === T_LAND）、贴内置 AI（主人是内置 AI 或已离开的席位）、贴敌方真人、贴同队真人、贴水；一格可以同时算进几类。
//   「够得着的 AI 地」= 和它接壤的内置 AI 的领土合计（每个 AI 只算一次）；分组合计时同一个 AI 在组内只算一次。
//   分组：我方号 / 和我方同队的其他真人 / 每个敌队的真人。
//
// 用法（必须套重计算闸）：
//   bash c136-review/tools/run-heavy.sh node c136-review/agents/R07/scripts/93_frontier.mjs <matchId> --at 540,720,990,1260,1530 [--tag name]
// 输出：out/<matchId>/frontier[_tag].txt
//   A. 分组 × 时刻：人数 | 领土 | 边界格 | 贴无主地 / 贴 AI / 贴敌方真人 / 贴同队 | 够得着的 AI：个数 / 领土 / 余额 | 每人中位数（贴 AI 格数、够得着的 AI 地）| 一格 AI 边界都没有的人数
//   B. 我方每个号 × 时刻：领土 / 余额 | 贴无主地 / 贴 AI / 贴敌 / 贴同队 | 够得着的 AI（个数 / 领土）| 贴着的敌方真人
//   C. 全图：无主地格数、内置 AI 领土合计与个数、其中「一个真人都不挨着」的 AI 领土
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const DATA = '/agent/repos/c136-data';
const HERE = path.dirname(fileURLToPath(import.meta.url));
const args = process.argv.slice(2);
const mid = args[0];
const opt = (k, d) => { const i = args.indexOf(k); return i >= 0 ? args[i + 1] : d; };
if (!mid || !opt('--at')) { console.error('用法：93_frontier.mjs <matchId> --at 540,990,1530 [--tag name]'); process.exit(2); }
const at = new Set(opt('--at').split(',').map(Number));
const tag = opt('--tag', '');
const OUT = path.join(HERE, '..', 'out', mid);
fs.mkdirSync(OUT, { recursive: true });
const SIM = await import(path.join(DATA, 'src/sim/sim/index.js'));
(await import(path.join(HERE, 'r07simfix.mjs'))).applyOddLandingFix(SIM);
const { resim } = await import(path.join(DATA, 'src/tools/resim.mjs'));
const LIB = await import(path.join(DATA, 'src/sim/tools/c102-replay-lib.mjs'));
const { T_LAND, T_WATER, P_INNER } = SIM;
const d = LIB.decodeReplay(fs.readFileSync(path.join(DATA, 'bundles', mid, 'replay.txt'), 'utf8'));
const H = d.vu.humanCount;
const names = d.vu.playerNamesData ? Array.from(d.vu.playerNamesData).slice(0, H).map((s) => String(s ?? '').trim()) : [];
const SQUAD = ['sora_w', 'ryan_m', 'noah88', 'zexos1', 'talon5', 'alex_k', 'leo_tx', 'zero_7', 'kaito9', 'riku_x'];
const squadOf = (p) => { const n = (names[p] || '').toLowerCase(); for (const s of SQUAD) if (n.endsWith(s)) return s; return null; };
const fmt = (n) => Math.round(n).toLocaleString('en-US');
const med = (a) => { if (!a.length) return 0; const s = [...a].sort((x, y) => x - y); const m = s.length >> 1; return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2; };

const snaps = [];
const proto = SIM.Game.prototype;
const origTick = proto.tick;
proto.tick = function () {
  origTick.call(this);
  const g = this;
  if (g.spawnPhase || !at.has(g.t)) return;
  const px = g.px, own = g.own, d4 = g.dir4;
  const per = [];
  const aiTouchedByHuman = new Set();
  for (let p = 0; p < H; p++) {
    if (!g.alive[p] || g.state[p] === 2 || g.terr[p] <= 0) continue;
    const B = g.border[p] || [];
    let nNeut = 0, nAI = 0, nEnemy = 0, nMate = 0, nWater = 0;
    const ai = new Map(), enemies = new Map();
    for (let i = 0; i < B.length; i++) {
      const b = B[i];
      let fN = 0, fA = 0, fE = 0, fM = 0, fW = 0;
      for (let k = 0; k < 4; k++) {
        const c = b + d4[k];
        const v = px[c];
        if (v === T_LAND) { fN = 1; continue; }
        if (v < P_INNER) { if (v === T_WATER) fW = 1; continue; }
        const o = own[c];
        if (o === p) continue;
        if (g.isBot(o)) { fA = 1; ai.set(o, (ai.get(o) || 0) + 1); }
        else if (g.teams[p] !== 0 && g.teams[o] === g.teams[p]) fM = 1;
        else { fE = 1; enemies.set(o, (enemies.get(o) || 0) + 1); }
      }
      nNeut += fN; nAI += fA; nEnemy += fE; nMate += fM; nWater += fW;
    }
    for (const o of ai.keys()) aiTouchedByHuman.add(o);
    per.push({ p, team: g.teams[p], squad: squadOf(p), terr: g.terr[p], bal: g.bal[p], border: B.length, nNeut, nAI, nEnemy, nMate, ai, enemies });
  }
  let neutralLand = 0;
  for (let c = 0; c < px.length; c++) if (px[c] === T_LAND) neutralLand++;
  let aiN = 0, aiTerr = 0, aiBal = 0, aiFarTerr = 0, aiFarN = 0;
  const aiInfo = new Map();
  for (let q = 0; q < g.alive.length; q++) {
    if (!g.alive[q] || !g.isBot(q) || g.terr[q] <= 0) continue;
    aiN++; aiTerr += g.terr[q]; aiBal += g.bal[q];
    aiInfo.set(q, { terr: g.terr[q], bal: g.bal[q] });
    if (!aiTouchedByHuman.has(q)) { aiFarTerr += g.terr[q]; aiFarN++; }
  }
  snaps.push({ t: g.t, per, neutralLand, aiN, aiTerr, aiBal, aiFarTerr, aiFarN, aiInfo, teams: Array.from(g.teams).slice(0, H) });
};
const res = await resim(mid, { until: Math.max(...at) + 5 });
const v = res.validate || {};

const ourTeam = (() => { for (let p = 0; p < H; p++) if (squadOf(p)) return snaps[0]?.teams[p] ?? 0; return 0; })();
const groupOf = (r) => r.squad ? '我方号' : r.team === ourTeam ? `T${r.team} 其他真人` : `T${r.team} 真人`;
const L = [];
L.push(`# ${mid} 全场真人的边界构成与够得着的内置 AI 地（干净模拟器重演，核对 ${v.bothExact}/${v.rows}；采样拍 ${[...at].sort((a, b) => a - b).join(',')}）`);
L.push('# 一格边界可以同时算进几类；「够得着的 AI」= 和它接壤的内置 AI（含离开后被接管的席位），每个 AI 在一个人 / 一个组里只算一次');
L.push('');
L.push('A. 分组 × 时刻');
L.push('t\t组\t人数\t领土\t余额\t边界格\t贴无主地\t贴AI\t贴敌方真人\t贴同队\t够得着的AI 个数/领土/余额\t每人中位：贴AI格 / 够得着的AI地\t没有AI边界的人数');
for (const s of snaps) {
  const groups = new Map();
  for (const r of s.per) { const k = groupOf(r); if (!groups.has(k)) groups.set(k, []); groups.get(k).push(r); }
  const order = [...groups.keys()].sort((a, b) => (a === '我方号' ? -1 : b === '我方号' ? 1 : a.localeCompare(b)));
  for (const k of order) {
    const rs = groups.get(k);
    const sum = (f) => rs.reduce((a, r) => a + f(r), 0);
    const ai = new Set(); for (const r of rs) for (const o of r.ai.keys()) ai.add(o);
    let aiT = 0, aiB = 0; for (const o of ai) { const x = s.aiInfo.get(o); if (x) { aiT += x.terr; aiB += x.bal; } }
    const perAiT = rs.map((r) => { let x = 0; for (const o of r.ai.keys()) x += s.aiInfo.get(o)?.terr ?? 0; return x; });
    L.push([s.t, k, rs.length, fmt(sum((r) => r.terr)), fmt(sum((r) => r.bal)), fmt(sum((r) => r.border)), fmt(sum((r) => r.nNeut)), fmt(sum((r) => r.nAI)), fmt(sum((r) => r.nEnemy)), fmt(sum((r) => r.nMate)),
      `${ai.size} / ${fmt(aiT)} / ${fmt(aiB)}`, `${fmt(med(rs.map((r) => r.nAI)))} / ${fmt(med(perAiT))}`, rs.filter((r) => r.nAI === 0).length].join('\t'));
  }
}
L.push('');
L.push('B. 我方每个号 × 时刻');
L.push('t\t号\t领土 / 余额\t边界格\t贴无主地\t贴AI\t贴敌方真人\t贴同队\t够得着的AI 个数/领土\t贴着的敌方真人（接壤格数）');
for (const s of snaps) {
  for (const r of s.per.filter((x) => x.squad).sort((a, b) => a.squad.localeCompare(b.squad))) {
    let aiT = 0; for (const o of r.ai.keys()) aiT += s.aiInfo.get(o)?.terr ?? 0;
    const en = [...r.enemies].sort((a, b) => b[1] - a[1]).map(([o, c]) => `${names[o].slice(0, 16)}#${o}[T${s.teams[o]}]:${c}`).join('、') || '-';
    L.push([s.t, r.squad, `${fmt(r.terr)} / ${fmt(r.bal)}`, r.border, r.nNeut, r.nAI, r.nEnemy, r.nMate, `${r.ai.size} / ${fmt(aiT)}`, en].join('\t'));
  }
}
L.push('');
L.push('C. 全图');
L.push('t\t无主地格数\t内置AI 个数 / 领土 / 余额\t其中一个真人都不挨着的 AI：个数 / 领土');
for (const s of snaps) L.push([s.t, fmt(s.neutralLand), `${s.aiN} / ${fmt(s.aiTerr)} / ${fmt(s.aiBal)}`, `${s.aiFarN} / ${fmt(s.aiFarTerr)}`].join('\t'));
const file = path.join(OUT, `frontier${tag ? '_' + tag : ''}.txt`);
fs.writeFileSync(file, L.join('\n') + '\n');
process.stdout.write(L.slice(0, 40).join('\n') + `\nwrote ${file}\n`);
