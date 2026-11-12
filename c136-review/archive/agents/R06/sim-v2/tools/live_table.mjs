#!/usr/bin/env node
// live_table.mjs — 把 --mode live 的逐局结果（sim-v2/calib/live/*.json）汇成「实盘区间」：按策略版本 × 卡顿档，各项签名的 P25 / 中位 / P75。
//
// 用法（在 c136-review/agents/R06 下）：node sim-v2/tools/live_table.mjs [--dir sim-v2/calib/live] [--out sim-v2/calib/live-bands.json] [--list]
//
// 只收：日志快照与重放逐条相同的局（logSnaps.ok == n > 0）、我方 ≥ 6 席、窗口跑满的局。
// 卡顿档按第一窗口（630~1530）的同拍批占比分：clean < 15%，lag ≥ 50%，其间是 mid。
import fs from 'node:fs';
import path from 'node:path';

const argv = process.argv.slice(2);
const opt = (k, d) => { const i = argv.indexOf(`--${k}`); return i >= 0 ? argv[i + 1] : d; };
const dir = opt('dir', 'sim-v2/calib/live');
const outFile = opt('out', 'sim-v2/calib/live-bands.json');
const LIST = argv.includes('--list');

export const SIG = [
  ['recPerSeat', '进录像条数 ÷ 席位', (w, r) => w.recorded / r.squad, 1],
  ['batchShare', '同拍批占比', (w) => w.batchShare, 0],
  ['gap0', '同回合连发占比', (w) => (w.gapShare ? w.gapShare[0] : null), 0],
  ['dumpPerSeat', '清仓批 ÷ 席位', (w, r) => w.dumpBatches / r.squad, 2],
  ['atkVoidRate', '陆攻落空率', (w) => w.atkVoidRate, 0],
  ['atkNeutralShare', '陆攻记成无主地占比', (w) => w.atkNeutralShare, 0],
  ['relTerr1', '窗口末人均相对领土', (w) => w.relTerr1, 3],
  ['aliveShare', '窗口末存活席位占比', (w, r) => w.alive1 / r.squad, 0],
  ['donNotLanded', '捐款发出后没成交的占比', (w) => w.donNotLanded, 0],
  ['dupShare', '重复单占比（有实录配对的局）', (w) => (w.dupShare === undefined ? null : w.dupShare), 0],
  ['rerouteRate', '目标已死改道率（有实录配对的局）', (w) => (w.rerouteRate === undefined ? null : w.rerouteRate), 0],
];

function q(a, p) {
  if (!a.length) return null;
  const s = a.slice().sort((x, y) => x - y);
  const i = (s.length - 1) * p, lo = Math.floor(i), hi = Math.ceil(i);
  return s[lo] + (s[hi] - s[lo]) * (i - lo);
}

export function loadLive(d) {
  const rows = [];
  for (const f of fs.readdirSync(d).sort()) {
    if (!f.endsWith('.json')) continue;
    const r = JSON.parse(fs.readFileSync(path.join(d, f), 'utf8'));
    if (r.error || !r.windows || !r.windows.length) continue;
    rows.push(r);
  }
  return rows;
}

export const lagClass = (bs) => (bs === null || bs === undefined ? '?' : bs < 0.15 ? 'clean' : bs >= 0.5 ? 'lag' : 'mid');

export function bands(rows) {
  const ok = rows.filter((r) => r.logSnaps && r.logSnaps.n > 0 && r.logSnaps.ok === r.logSnaps.n && r.squad >= 6);
  const out = { note: '每项：[P25, 中位, P75, 局数]；只收日志快照与重放逐条相同、我方 ≥ 6 席、窗口跑满的局', cohorts: {}, matches: {} };
  for (const r of ok) {
    const w1 = r.windows[0];
    if (!w1 || w1.t1 !== w1.asked[1]) continue;
    const cls = lagClass(w1.batchShare);
    out.matches[r.match] = { cohort: r.cohort, cls, humans: r.humans, nTeams: r.nTeams, squad: r.squad };
    for (let wi = 0; wi < r.windows.length; wi++) {
      const w = r.windows[wi];
      if (w.t1 !== w.asked[1]) continue;
      for (const c of [cls, 'all']) {
        const key = `${r.cohort}|${c}|${w.asked[0]}~${w.asked[1]}`;
        const g = (out.cohorts[key] = out.cohorts[key] || { n: 0, vals: {} });
        g.n++;
        for (const [k, , fn] of SIG) {
          const v = fn(w, r);
          if (v === null || v === undefined || Number.isNaN(v)) continue;
          (g.vals[k] = g.vals[k] || []).push(v);
        }
      }
    }
  }
  for (const g of Object.values(out.cohorts)) {
    g.band = {};
    for (const [k, a] of Object.entries(g.vals)) g.band[k] = [q(a, 0.25), q(a, 0.5), q(a, 0.75), a.length].map((x, i) => (i < 3 ? +x.toFixed(4) : x));
    delete g.vals;
  }
  return out;
}

const isMain = process.argv[1] && path.resolve(process.argv[1]) === path.resolve(new URL(import.meta.url).pathname);
if (isMain) {
  const rows = loadLive(dir);
  const B = bands(rows);
  fs.writeFileSync(outFile, JSON.stringify(B, null, 1));
  const fmt = (v, d) => (v === null || v === undefined ? '-' : d === 0 ? Math.round(100 * v) + '%' : v.toFixed(d));
  const keys = Object.keys(B.cohorts).sort();
  console.log(['版本', '卡顿档', '窗口', '局数', ...SIG.map((s) => s[1])].join('\t'));
  for (const key of keys) {
    const [co, cls, win] = key.split('|');
    const g = B.cohorts[key];
    console.log([co, cls, win, g.n, ...SIG.map(([k, , , d]) => (g.band[k] ? `${fmt(g.band[k][0], d)}/${fmt(g.band[k][1], d)}/${fmt(g.band[k][2], d)}${g.band[k][3] !== g.n ? `(${g.band[k][3]})` : ''}` : '-'))].join('\t'));
  }
  console.log('每格：P25/中位/P75（括号里 = 这一项有数的局数，与本行局数不同时才标）');
  const bad = rows.filter((r) => !(r.logSnaps && r.logSnaps.n > 0 && r.logSnaps.ok === r.logSnaps.n));
  console.log(`收 ${Object.keys(B.matches).length} 局；日志快照对不上或没有快照的 ${bad.length} 局不收：${bad.map((r) => `${r.match}(${r.logSnaps ? r.logSnaps.ok + '/' + r.logSnaps.n : '-'})`).join(' ')}`);
  if (LIST) {
    for (const [mid, m] of Object.entries(B.matches)) console.log(`${mid}\t${m.cohort}\t${m.cls}\t真人 ${m.humans}\t${m.nTeams} 队\t我方 ${m.squad}`);
  }
  console.log(`写入 ${outFile}`);
}
