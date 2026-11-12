#!/usr/bin/env node
// huskprobe.mjs — 走偏根因的直接取证（第二处）：同一个机器决策，线上引擎原文和模拟器在哪一步分了岔。
//
// engdiff / fidmism 只看得到现象（A001 的空壳 #11 在 4780 拍：线上引擎里它发了一艘船，模拟器里它把余额交给了队友）。
// 全场 512 个玩家的地和兵在那之前逐位一致，所以分岔的是「看不见的状态」——机器决策用到、但不在地和兵里的东西。
// 这里把两边都按录像重放到那一拍，逐拍并排读这些看不见的状态：
//   随机数状态｜无主地扫描表（条数、内容的校验和）｜航线表（条数、首尾和长度的校验和）｜终局提速开关｜全场的船数
// 并且在被观察的那个玩家身上，把机器决策的每一级（陆上挑目标 → 发船的三条路 → 爬山 → 交兵）的返回值两边各记一份。
// 线上引擎这一侧的记法：把这几个函数各包一层只读的壳（原样调用、原样返回，只多记一行），不改任何对局状态；
// 模拟器这一侧同样只在本脚本的实例上包壳，src/sim 的文件不动。
// 只读 /agent/repos/c136-data（发现集的对局包 + src）；不跑策略，不改任何指令。
//
// 对着读的引擎原文（live_game_js.js）和模拟器（src/sim/sim/bots.js）：
//   组队局的机器决策  kh(player,…)：ap.jf.k7 / ap.jf.kC（陆上挑目标）→ bQ.ki.ee（发船）→ ap.jj.ee（爬山）→ kq（交兵，bB.kw.kx）
//                     = botAttackTeam：pickTargets / firstTarget → botBoat → botMountain → botDonate（botGive）
//   发船              aaN.ee：ap.jl.ee（已有航线）‖ ap.ja.ee（朝无主地，读扫描表 ap.jY）‖ ap.jc.ee（朝玩家）；落到 bQ.lh.li（朝某个水格发船）
//                     = botBoat：knownRouteBoat ‖ boatToNeutral（scanBuf / scanLen）‖ boatToPlayer；boatTowards
//
//   bash c136-review/tools/run-heavy.sh node c136-review/agents/R08/scripts/huskprobe.mjs A001 11 3400 4782
//   → out/_cross/huskprobe.txt、huskprobe.json
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';
import { resim } from './resim_r08.mjs';

const require = createRequire(import.meta.url);
const { startReplay } = require('/agent/repos/c136-data/src/tools/engine_replay.cjs');

const HERE = path.dirname(fileURLToPath(import.meta.url));
const OUT = path.join(HERE, '..', 'out', '_cross');
const [mid, ps, los, his] = process.argv.slice(2);
const P = +ps, lo = +los, hi = +his;
const MOD = 1000000007;

const FIELDS = ['随机数状态', '扫描表条数', '扫描表校验和', '航线表条数', '航线表校验和', '终局提速', '全场船数', '被观察玩家的余额', '被观察玩家的船数',
  '还有地的队数（各队总地的 32 拍缓存里 > 0 的个数，含未入队那一组）', '扫描表「不重扫」的条件（1 = 成立）'];
// 最后一项两边的算法不同，正是要对的东西：
//   线上引擎  bD.gv.mf()：存活 < 2 → 0；自由混战 → 第二名的地；组队局 → bk.a6U() > 1（还有地的队多于一个）
//   模拟器    bots.js scanTick L723：second = aliveCount < 2 ? 0 : terr[rank[1]]（不分模式，一律看第二名个人的地）

// ---- 线上引擎 ----
const ENGINE = `(function (P) {
  var log = [];
  function wrap(obj, name, tag) {
    var f = obj[name];
    obj[name] = function () {
      var r0 = az.aP0(), n0 = ap.jY.m4, m0 = bQ.mG.mI().length, b0 = ah.hb[P];
      var r = f.apply(obj, arguments);
      if (arguments[0] === P) {
        log.push([bi.kr(), tag, r ? 1 : 0, r0, az.aP0(), n0, m0, arguments.length > 1 ? arguments[1] : null, b0, ah.hb[P]]);
      }
      return r;
    };
  }
  wrap(ap.jf, 'k7', '陆上挑目标（沿边界抽样）'); wrap(ap.jf, 'kC', '陆上挑目标（第一个）');
  wrap(bQ.ki, 'ee', '发船'); wrap(ap.jl, 'ee', '发船·已有航线'); wrap(ap.ja, 'ee', '发船·朝无主地'); wrap(ap.jc, 'ee', '发船·朝玩家');
  wrap(bQ.lh, 'li', '朝水格发船'); wrap(ap.jj, 'ee', '爬山'); wrap(bB.kw, 'kx', '交兵');
  return {
    state: function () {
      var n = ap.jY.m4, b = ap.jY.buffer, s = 0, i;
      for (i = 0; i < n; i++) s = (s * 31 + b[i]) % ${MOD};
      var R = bQ.mG.mI(), rs = 0;
      for (i = 0; i < R.length; i++) { var r = R[i]; rs = (rs * 31 + r[0] * 7 + r[r.length - 1] * 3 + r.length) % ${MOD}; }
      return JSON.stringify([az.aP0(), n, s, R.length, rs, ap.performance.m8, bQ.z.mk, ah.hb[P], bQ.z.ky[P], aE.iT ? bk.a6U() : -1, bD.gv.mf() ? 1 : 0]);
    },
    scan: function () { return JSON.stringify(Array.prototype.slice.call(ap.jY.buffer, 0, ap.jY.m4)); },
    log: function () { return JSON.stringify(log); }
  };
})`;

const eng = new Map();
const engScan = new Map();
let engLog;
{
  const { h, api } = startReplay(mid);
  const probe = h.run(ENGINE)(P);
  let lastT = -1;
  while (true) {
    const [t, hx, st] = api.advance(1);
    if (hx) continue;
    if (t === lastT) { if (st === 2) break; continue; }
    lastT = t;
    if (t >= lo && t <= hi) { eng.set(t, JSON.parse(probe.state())); engScan.set(t, probe.scan()); }
    if (t >= hi || st === 2) break;
  }
  engLog = JSON.parse(probe.log());
}

// ---- 模拟器 ----
const sim = new Map();
const secondAt = new Map();
const simScan = new Map();
const simLog = [];
const SIM_WRAP = [['pickTargets', '陆上挑目标（沿边界抽样）'], ['firstTarget', '陆上挑目标（第一个）'], ['botBoat', '发船'], ['knownRouteBoat', '发船·已有航线'],
  ['boatToNeutral', '发船·朝无主地'], ['boatToPlayer', '发船·朝玩家'], ['boatTowards', '朝水格发船'], ['botMountain', '爬山'], ['botGive', '交兵']];
const X = resim(mid, {
  until: hi,
  onStart: (g) => {
    for (const [name, tag] of SIM_WRAP) {
      const f = g[name];
      g[name] = function (...a) {
        const r0 = g.rng.half(), n0 = g.scanLen, m0 = g.routes.length, b0 = g.bal[P];
        const r = f.apply(g, a);
        if (a[0] === P) simLog.push([g.t, tag, r ? 1 : 0, r0, g.rng.half(), n0, m0, a.length > 1 ? a[1] : null, b0, g.bal[P]]);
        return r;
      };
    }
  },
  onTick: (g) => {
    if (g.t < lo || g.t > hi) return;
    let s = 0;
    for (let i = 0; i < g.scanLen; i++) s = (s * 31 + g.scanBuf[i]) % MOD;
    let rs = 0;
    for (const r of g.routes) rs = (rs * 31 + r[0] * 7 + r[r.length - 1] * 3 + r.length) % MOD;
    let teamsLeft = -1;
    if (g.teamGame) {
      teamsLeft = 0;
      for (const v of g.teamCacheGet().subarray(0, g.nTeams + 1)) teamsLeft += v > 0 ? 1 : 0;
    }
    const second = g.aliveCount < 2 ? 0 : g.terr[g.rank[1]];
    secondAt.set(g.t, second);
    sim.set(g.t, [g.rng.half(), g.scanLen, s, g.routes.length, rs, g.endgameFast, g.boatN, g.bal[P], g.boatCount[P], teamsLeft, second ? 1 : 0]);
    simScan.set(g.t, JSON.stringify(Array.from(g.scanBuf.subarray(0, g.scanLen))));
  },
});

// ---- 并排 ----
const lines = [];
const out = (s) => { console.log(s); lines.push(s); };
out(`huskprobe.mjs — ${mid} 玩家 #${P}（${String(X.names[P]).trim()}；真人 ${X.H}；${X.leftT[P] >= 0 ? `${X.leftT[P]} 拍离开，之后是空壳` : '没离开'}）：线上引擎原文 对 模拟器，拍 ${lo}~${hi}，逐拍并排「看不见的状态」`);
out('');
out('[HP-A] 每一项第一次对不上的拍（– = 整段都一致）');
const first = {};
for (let k = 0; k < FIELDS.length; k++) {
  let t0 = null;
  for (let t = lo; t <= hi; t++) {
    const e = eng.get(t), s = sim.get(t);
    if (!e || !s) continue;
    if (e[k] !== s[k]) { t0 = t; break; }
  }
  first[FIELDS[k]] = t0;
  const e = t0 === null ? null : eng.get(t0), s = t0 === null ? null : sim.get(t0);
  out(`  ${FIELDS[k]} | ${t0 === null ? '–' : `${t0} 拍：引擎 ${e[k]}，模拟器 ${s[k]}`}`);
}
const nCmp = [...eng.keys()].filter((t) => sim.has(t)).length;
out(`  并排的拍数 ${nCmp}`);
const firstAny = Math.min(...Object.values(first).filter((v) => v !== null), Infinity);
out('');
if (Number.isFinite(firstAny)) {
  out(`[HP-B] 最早对不上的那一拍（${firstAny}）前后：拍 | 引擎：${FIELDS.map((f) => f.replace(/（.*$/, '')).join(' / ')} | 模拟器：同样 ${FIELDS.length} 项 | * = 这一拍有对不上的项`);
  for (let t = Math.max(lo, firstAny - 6); t <= Math.min(hi, firstAny + 12); t++) {
    const e = eng.get(t), s = sim.get(t);
    if (!e || !s) continue;
    out(`  ${t} | ${e.join(' / ')} | ${s.join(' / ')}${e.some((v, k) => v !== s[k]) ? ' *' : ''}`);
  }
  // 扫描表：第一次对不上的那一拍，两边各自有而对方没有的格
  const tS = first['扫描表校验和'] ?? first['扫描表条数'];
  if (tS !== null && tS !== undefined) {
    const a = JSON.parse(engScan.get(tS)), b = JSON.parse(simScan.get(tS));
    const A = new Set(a), B = new Set(b);
    const onlyE = a.filter((c) => !B.has(c)), onlyS = b.filter((c) => !A.has(c));
    let pos = 0;
    while (pos < Math.min(a.length, b.length) && a[pos] === b[pos]) pos++;
    out('');
    out(`[HP-C] 扫描表在 ${tS} 拍：引擎 ${a.length} 条，模拟器 ${b.length} 条；从头数第一个不同的位置 ${pos}；只在引擎里的格 ${onlyE.length} 个，只在模拟器里的格 ${onlyS.length} 个`
      + (onlyE.length ? `（引擎多的前几个：${onlyE.slice(0, 6).join(' ')}）` : '') + (onlyS.length ? `（模拟器多的前几个：${onlyS.slice(0, 6).join(' ')}）` : ''));
    const pe = eng.get(tS - 1), pss = sim.get(tS - 1);
    if (pe && pss) out(`  前一拍（${tS - 1}）：引擎 ${pe[1]} 条，模拟器 ${pss[1]} 条`);
  }
} else {
  out('[HP-B] 各项整段都一致。');
}
const tR = first[FIELDS[10]];
if (tR !== null && tR !== undefined) {
  out('');
  out(`[HP-F] 「不重扫」的条件第一次对不上是 ${tR} 拍：线上引擎 ${eng.get(tR)[10]}（还有地的队 ${eng.get(tR)[9]} 个），模拟器 ${sim.get(tR)[10]}（第二名个人的地 ${secondAt.get(tR)}；按同一份 32 拍缓存数还有地的队 ${sim.get(tR)[9]} 个）`);
  const tS2 = first['扫描表条数'];
  if (tS2 !== null && tS2 !== undefined) out(`  扫描表条数第一次对不上是 ${tS2} 拍（晚 ${tS2 - tR} 拍）；被观察玩家的余额第一次对不上是 ${first['被观察玩家的余额']} 拍（再晚 ${first['被观察玩家的余额'] - tS2} 拍）`);
}
out('');
const vis = first['被观察玩家的余额'] ?? first['被观察玩家的船数'] ?? hi;
// 「交兵」这一级两边的函数都没有返回值（bB.kw.kx 和 botGive 成不成都返回 undefined），成不成只能看调用前后的余额。
const NORET = new Set(['交兵']);
const ret = (r) => (NORET.has(r[1]) ? (r[9] < r[8] ? '兵出去了' : '兵没动') : (r[2] ? '成' : '不成'));
out(`[HP-D] 被观察玩家身上的机器决策，逐级的结果（只列 ${vis - 200} 拍以后的；拍 | 哪一级 | 结果 | 调用前后的随机数状态 | 调用时扫描表条数 / 航线表条数 | 第二个参数 | 被观察玩家调用前后的余额）`);
out('  结果一栏：「交兵」这一级两边的函数都没有返回值，写的是调用前后余额有没有少；其余各级写的是返回值（成 / 不成）。');
for (const [name, L] of [['线上引擎', engLog], ['模拟器', simLog]]) {
  out(`  ${name}：`);
  const rows = L.filter((r) => r[0] >= vis - 200);
  for (const r of rows) out(`    ${r[0]} | ${r[1]} | ${ret(r)} | ${r[3]} → ${r[4]} | ${r[5]} / ${r[6]} | ${r[7] === null ? '' : r[7]} | ${r[8]} → ${r[9]}`);
  if (!rows.length) out('    （没有调用）');
}
// 两边的决策序列第一处不同
const key = (r) => `${r[1]}|${ret(r)}|${r[7]}`;
let d = 0;
while (d < Math.min(engLog.length, simLog.length) && key(engLog[d]) === key(simLog[d])) d++;
out('');
out(`[HP-E] 两边的决策记录（整段，从 ${lo} 拍以前就开始记）：引擎 ${engLog.length} 行，模拟器 ${simLog.length} 行；从头数前 ${d} 行逐行相同（哪一级、结果、第二个参数）`);
if (d < Math.max(engLog.length, simLog.length)) {
  const e = engLog[d], s = simLog[d];
  out(`  第一处不同：引擎 ${e ? `${e[0]} 拍「${e[1]}」${ret(e)}（第二个参数 ${e[7]}；随机数 ${e[3]} → ${e[4]}；扫描表 ${e[5]} 条、航线表 ${e[6]} 条）` : '（没有了）'}`
    + `；模拟器 ${s ? `${s[0]} 拍「${s[1]}」${ret(s)}（第二个参数 ${s[7]}；随机数 ${s[3]} → ${s[4]}；扫描表 ${s[5]} 条、航线表 ${s[6]} 条）` : '（没有了）'}`);
  const give = simLog.filter((r) => NORET.has(r[1]) && r[9] < r[8]).concat(engLog.filter((r) => NORET.has(r[1]) && r[9] < r[8]).map((r) => [...r, 'E']));
  for (const r of give) out(`  兵出去了的「交兵」：${r[10] ? '引擎' : '模拟器'} ${r[0]} 拍，交给 #${r[7]}「${String(X.names[r[7]]).trim()}」，被观察玩家的余额 ${r[8]} → ${r[9]}`);
}
fs.mkdirSync(OUT, { recursive: true });
fs.writeFileSync(path.join(OUT, 'huskprobe.txt'), lines.join('\n') + '\n');
fs.writeFileSync(path.join(OUT, 'huskprobe.json'), JSON.stringify({ matchId: mid, player: P, lo, hi, first, engLog, simLog }));
