#!/usr/bin/env node
// hidstate.mjs — 验收条款 R7 的现状：线上引擎原文 对 模拟器，整局逐拍比「看不见的状态」。
//
// engdiff 比的是全场每个玩家的地、余额、存活（每 10 拍）。机器决策还读别的东西——随机数状态、无主地扫描表、航线表、
// 船、欠账——它们先分开、过一阵才在地和兵上显出来（huskprobe：A001 的扫描表比兵早 102 拍），也可能到录像结束都不显
// （boatprobe：B010 有一艘船退回的 60 兵抵了欠账）。这里把 huskprobe 并排读的那几项拿出来，不盯某一个玩家，整局逐拍比：
//   随机数状态｜无主地扫描表（条数、内容校验和）｜航线表（条数、校验和）｜终局提速开关｜全场船数｜各玩家的欠账｜还有地的队数
// 两边各自按录像重放（线上引擎：engine_replay.cjs；模拟器：resim_r08.mjs），不跑策略、不改指令、不改 src/sim。
// 只读 /agent/repos/c136-data（发现集的对局包 + src）。
//
//   bash c136-review/tools/run-heavy.sh node c136-review/agents/R08/scripts/hidstate.mjs [--budget 秒] <局> [<局> ...]
//   → out/_run/hidstate/<局>.json（已有的跳过）；汇总见 hidstate.py
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';
import { resim } from './resim_r08.mjs';

const require = createRequire(import.meta.url);
const { startReplay } = require('/agent/repos/c136-data/src/tools/engine_replay.cjs');

const HERE = path.dirname(fileURLToPath(import.meta.url));
const OUT = path.join(HERE, '..', 'out', '_run', 'hidstate');
const argv = process.argv.slice(2);
let budget = 20;
const mids = [];
for (let i = 0; i < argv.length; i++) {
  if (argv[i] === '--budget') budget = +argv[++i];
  else mids.push(argv[i]);
}
const T0 = Date.now();
const MOD = 1000000007;
const FIELDS = ['随机数状态', '扫描表条数', '扫描表校验和', '航线表条数', '航线表校验和', '终局提速', '全场船数', '欠账', '还有地的队数'];
const DEBT = 7;   // 这一项存的是「有欠账的玩家：欠多少」的清单（字符串），不是校验和，对不上时能直接看出是谁

// 线上引擎这一侧：只读。az.aP0 随机数状态；ap.jY 无主地扫描表；bQ.mG 航线表；ap.performance.m8 终局提速；bQ.z.mk 船数；
// ah.a6b 欠账；bk.a6U() 还有地的队数（各队总地的 32 拍缓存里 > 0 的个数，含未入队那一组；自由混战记 -1）
const ENGINE = `(function () {
  return {
    state: function () {
      var n = ap.jY.m4, b = ap.jY.buffer, s = 0, i;
      for (i = 0; i < n; i++) s = (s * 31 + b[i]) % ${MOD};
      var R = bQ.mG.mI(), rs = 0;
      for (i = 0; i < R.length; i++) { var r = R[i]; rs = (rs * 31 + r[0] * 7 + r[r.length - 1] * 3 + r.length) % ${MOD}; }
      var d = '', P = aE.a0E, a = ah.a6b;
      for (i = 0; i < P; i++) if (a[i]) d += i + ':' + a[i] + ' ';
      return JSON.stringify([az.aP0(), n, s, R.length, rs, ap.performance.m8, bQ.z.mk, d, aE.iT ? bk.a6U() : -1]);
    }
  };
})`;

function probe(mid) {
  const eng = new Map();
  let engLast = -1, engOver = 0;
  {
    const { h, api } = startReplay(mid);
    const pr = h.run(ENGINE)();
    let lastT = -1;
    while (true) {
      const [t, hx, st] = api.advance(1);
      if (hx) continue;
      if (t === lastT) { if (st === 2) { engOver = 1; break; } continue; }
      lastT = t;
      eng.set(t, JSON.parse(pr.state()));
      engLast = t;
      if (st === 2) { engOver = 1; break; }
    }
  }
  const sim = new Map();
  const X = resim(mid, {
    onTick: (g) => {
      let s = 0;
      for (let i = 0; i < g.scanLen; i++) s = (s * 31 + g.scanBuf[i]) % MOD;
      let rs = 0;
      for (const r of g.routes) rs = (rs * 31 + r[0] * 7 + r[r.length - 1] * 3 + r.length) % MOD;
      let d = '';
      for (let p = 0; p < g.players; p++) if (g.debt[p]) d += `${p}:${g.debt[p]} `;
      let left = -1;
      if (g.teamGame) {
        left = 0;
        for (const v of g.teamCacheGet().subarray(0, g.nTeams + 1)) left += v > 0 ? 1 : 0;
      }
      sim.set(g.t, [g.rng.half(), g.scanLen, s, g.routes.length, rs, g.endgameFast, g.boatN, d, left]);
    },
  });
  const ts = [...eng.keys()].filter((t) => sim.has(t)).sort((a, b) => a - b);
  const first = {};
  for (let k = 0; k < FIELDS.length; k++) {
    let t0 = null;
    for (const t of ts) if (eng.get(t)[k] !== sim.get(t)[k]) { t0 = t; break; }
    let nBad = 0;
    if (t0 !== null) for (const t of ts) if (eng.get(t)[k] !== sim.get(t)[k]) nBad++;
    first[FIELDS[k]] = t0 === null ? null : { t: t0, eng: k === DEBT ? null : eng.get(t0)[k], sim: k === DEBT ? null : sim.get(t0)[k], nBad };
  }
  // 欠账第一次对不上的那一拍：哪些玩家、两边各欠多少
  let debtDiff = null;
  if (first[FIELDS[DEBT]]) {
    const t = first[FIELDS[DEBT]].t;
    const parse = (s) => new Map(s.trim().split(' ').filter(Boolean).map((x) => x.split(':').map(Number)));
    const a = parse(eng.get(t)[DEBT]), b = parse(sim.get(t)[DEBT]);
    debtDiff = [];
    for (const p of new Set([...a.keys(), ...b.keys()])) if ((a.get(p) || 0) !== (b.get(p) || 0)) debtDiff.push([p, p < X.H ? String(X.names[p]).trim() : '内置 AI', a.get(p) || 0, b.get(p) || 0]);
    debtDiff = debtDiff.slice(0, 12);
  }
  // 有过欠账的拍数（两边）——这一项全程是 0 的话，「相等」没有信息量
  let debtTicksE = 0, debtTicksS = 0;
  for (const t of ts) { if (eng.get(t)[DEBT]) debtTicksE++; if (sim.get(t)[DEBT]) debtTicksS++; }
  let scanTicks = 0, routeMax = 0, boatMax = 0;
  for (const t of ts) { const e = eng.get(t); if (e[1]) scanTicks++; if (e[3] > routeMax) routeMax = e[3]; if (e[6] > boatMax) boatMax = e[6]; }
  return { matchId: mid, H: X.H, nTeams: X.nTeams, teamGame: X.nTeams ? 1 : 0, engLast, engOver, simEnd: X.endTick, nCmp: ts.length, t0: ts[0], t1: ts[ts.length - 1],
    first, debtDiff, debtTicksE, debtTicksS, scanTicks, routeMax, boatMax };
}

fs.mkdirSync(OUT, { recursive: true });
let done = 0;
for (const mid of mids) {
  const fp = path.join(OUT, `${mid}.json`);
  if (fs.existsSync(fp)) continue;
  if (done && (Date.now() - T0) / 1000 > budget) break;
  const mark = path.join(OUT, `${mid}.started`);
  fs.writeFileSync(mark, String(Date.now()));
  const t1 = Date.now();
  const R = probe(mid);
  R.sec = Math.round((Date.now() - t1) / 100) / 10;
  fs.writeFileSync(fp, JSON.stringify(R));
  fs.unlinkSync(mark);
  done++;
  const bad = Object.entries(R.first).filter(([, v]) => v).map(([k, v]) => `${k}@${v.t}`);
  console.log(`${mid} 真人 ${R.H} 队 ${R.nTeams} 并排 ${R.nCmp} 拍（${R.t0}~${R.t1}）${R.sec}s | ${bad.length ? bad.join(' ') : '九项整局逐拍相等'}`);
}
console.log(`HIDSTATE ${done} 局，用时 ${Math.round((Date.now() - T0) / 1000)}s`);
