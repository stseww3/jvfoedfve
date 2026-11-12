#!/usr/bin/env node
// cfprobe.mjs — 「历史真局断面反事实」的可行性探针：从 t=630 的真实断面起，把本编队的指令换掉，其余人照录像走，看三件事：
//   (1) 同一条简单规则，过不同的指令通道（立即 / 固定 14 拍 / 7~19 拍抖动 / 这一局这个号的历史卡顿），到 1500 拍差多少；
//   (2) 各通道下「成批落地」「落地没生效」这两个签名长什么样，和线上实测对不对得上；
//   (3) 开环偏差：本编队换了打法以后，录像里别的真人的指令有多少条「生效 / 没生效」翻了面（录像指令还能信多久）。
//
//   bash c136-review/tools/run-heavy.sh node c136-review/agents/R08/scripts/cfprobe.mjs [<局> …] [--budget 95]
//
// 不给局号 = 发现集里有录像、out/_run/cfprobe/ 下还没有结果的局，做到时间预算为止，再跑一次接着做。
// 每局一个文件 out/_run/cfprobe/<局>.json（不进 git）。只读 bundles/（发现集）。汇总在 cfprobe.py。
//
// 臂：
//   fact  录像原样（= 历史）。
//   idle  t ≥ 630 起本编队的指令（陆攻 / 捐款 / 船 / 追船 / 撤军）全部不执行，别的不动。
//   p0    本编队换成探针规则，指令立即执行（旧模拟器的做法）。
//   p14   探针规则；指令在「决策拍 + 14」之后的第一个 7 的倍数拍执行。
//   pj    探针规则；每条指令的时延在 7~19 拍里均匀抽，执行拍取 7 的倍数。
//   ph    探针规则；平时同 pj，另外套上这个号在这一局录像里的历史卡顿：
//         录像里这个号某一拍落地 ≥3 条、且离它上一次有指令落地 ≥70 拍，就把这一段沉默当作一次卡顿——
//         沉默期间做出的决策全部压到那一拍执行（同一拍每号最多 9 条，多的丢掉）。
//   wj    别人不动，本编队还是录像里的指令，但 t ≥ 630 的每条都推迟 7~19 拍再执行（看「把历史指令挪一下」本身翻多少面，当开环偏差的地板）。
//
// 探针规则（不是候选策略，只是一把固定的尺子；每 5 拍对每个在线的本编队号跑一次，看到的是当拍的真实局面，没有在途账本）：
//   · 挨着的内置 AI 里，挑「打垮它还差的兵 ÷ 能吃到的地」最小的；还差的兵 need = elimCost + 它压在我身上的兵 − 我压在它身上的兵
//     （elimCost 用策略自己的公式 2·B·(1−x^1.6) + 2·T·(1−x)，x = ⌊峰值/4⌋ ÷ T）；
//     1.25·need + 手续费 ≤ 余额的一半才下单，派 1.25·need；同一个目标 15 拍内不重复下单，同一个号两条指令至少隔 10 拍。
//   · 没有可买的 AI、挨着无主地、且没有正在吃无主地：派余额的 10% 吃无主地。
//   · 不打真人、不发船、不捐款。pct 在决策拍按当时余额折算，执行拍引擎按执行时的余额抽兵（和线上一样）。
// 读数时注意：别的真人是开环的（照录像走，不会因为本编队变强而改打法），所以探针臂的绝对水平偏乐观；
// 臂和臂之间只差通道，差值受这个偏差的影响小。翻面比例就是用来量这个偏差的。
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const DATA = process.env.C136_DATA || '/agent/repos/c136-data';
const argv = process.argv.slice(2);
const take = (k, d) => {
  const i = argv.indexOf(`--${k}`);
  if (i < 0) return d;
  const v = argv[i + 1];
  argv.splice(i, 2);
  return v;
};
const budget = +take('budget', 95) * 1000;
const outDir = path.resolve(take('out-dir', path.join(HERE, '..', 'out', '_run', 'cfprobe')));
const { resim } = await import(path.join(HERE, 'resim_r08.mjs'));
fs.mkdirSync(outDir, { recursive: true });

const NEUTRAL = 512;
const T0 = 630, TEND = 1500;
const CPS = [630, 900, 1260, 1500];
const DWIN = [630, 900, 1260, 1500];
const ARMS = ['fact', 'idle', 'p0', 'p14', 'pj', 'ph', 'wj'];
const iV = (a, b) => Math.floor((a + 0.5) / b);
const ceil7 = (t) => 7 * Math.ceil(t / 7);
const hash = (s) => { let h = 2166136261; for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619); } return h >>> 0; };
const mulberry = (a) => () => { a |= 0; a = (a + 0x6D2B79F5) | 0; let t = Math.imul(a ^ (a >>> 15), 1 | a); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };

let ids = argv.slice();
if (!ids.length) {
  ids = fs.readFileSync(path.join(DATA, 'manifest.jsonl'), 'utf8').split('\n').filter(Boolean)
    .map((l) => JSON.parse(l)).filter((m) => m.split === 'discovery').map((m) => m.matchId).sort()
    .filter((mid) => fs.existsSync(path.join(DATA, 'bundles', mid, 'replay.txt')) && !fs.existsSync(path.join(outDir, `${mid}.json`)));
}

function runArm(mid, arm, own, stalls) {
  const ownSet = new Set(own);
  const cp = {};
  const rnd = mulberry(hash(`${mid}|${arm}`));
  const outbox = [];                 // [执行拍, 号, pct, 目标, 决策拍, 想派的兵]
  const lastEmit = new Map();        // 号 → 上一条指令的决策拍
  const lastTgt = new Map();         // 号*1024+目标 → 上一条的决策拍
  const stat = { dec: 0, exec: 0, ok: 0, capDrop: 0, intended: 0, sent: 0, perTurn: new Map(), toAi: 0, toNeutral: 0, okAi: 0 };
  const delayed = [];                // wj 臂：推迟执行的录像指令 [执行拍, 指令]
  let execRecorded = null;
  const probe = arm[0] === 'p';

  const decide = (g, ctx, p) => {
    const B = g.bal[p];
    if (B < 50) return null;
    const fee = iV(12 * B, 1024);
    const m = ctx.contact(p);
    let best = null, bestS = Infinity, hasNeutral = false;
    for (const [q] of m) {
      if (q === NEUTRAL) { hasNeutral = true; continue; }
      if (q < ctx.H || !g.alive[q] || g.terr[q] <= 0 || !g.isEnemy(p, q)) continue;
      if (!g.hasAttack(p, q) && !g.hasFreeSlot(p)) continue;
      const T = g.terr[q], Bq = g.bal[q];
      const left = iV(g.peak[q], 4);
      const x = Math.min(1, left / Math.max(T, 1));
      const need = 2 * Bq * (1 - Math.pow(x, 1.6)) + 2 * T * (1 - x) + g.attackTroopsOn(q, p) - g.attackTroopsOn(p, q);
      if (need <= 0) continue;
      const troops = 1.25 * need;
      if (troops + fee > 0.5 * B || troops < fee) continue;
      if (g.t - (lastTgt.get(p * 1024 + q) ?? -999) < 15) continue;
      const s = need / Math.max(1, T - left);
      if (s < bestS) { bestS = s; best = [q, troops]; }
    }
    if (best) return best;
    if (hasNeutral && !g.hasAttack(p, NEUTRAL) && g.hasFreeSlot(p) && g.t - (lastTgt.get(p * 1024 + NEUTRAL) ?? -999) >= 15) return [NEUTRAL, 0.1 * B];
    return null;
  };

  const execOne = (g, o) => {
    const [, p, pct, target, , want] = o;
    if (!g.alive[p] || g.state[p] === 2) return;
    const ok = g.attack(pct, target, p);
    stat.exec++;
    stat.intended += want;
    if (target === NEUTRAL) stat.toNeutral++; else stat.toAi++;
    if (ok) { stat.ok++; stat.sent += g.attackTroopsTmp; if (target !== NEUTRAL) stat.okAi++; }
    const key = p * 4096 + g.t;
    stat.perTurn.set(key, (stat.perTurn.get(key) || 0) + 1);
  };

  const R = resim(mid, {
    until: TEND,
    cmdFilter: arm === 'fact' ? undefined : (c, g) => {
      if (g.spawnPhase || g.t < T0 || !ownSet.has(c.player) || c.id < 1 || c.id > 5) return true;
      if (arm === 'wj') delayed.push([ceil7(g.t + 7 + Math.floor(13 * rnd())), c]);
      return false;
    },
    onStart(g) {
      if (arm !== 'wj') return;
      // wj：推迟的录像指令到点后直接调引擎接口执行（只有陆攻 / 船 / 捐款 / 撤军这几种）
      execRecorded = (c) => {
        const { id, player, dX, dZ } = c;
        if (!g.alive[player] || g.state[player] === 2) return;
        if (id === 1) g.attack(dX, dZ, player);
        else if (id === 2) g.donate(dX, dZ, player);
        else if (id === 3) g.boat(dX, dZ >> 3, dZ & 7, player);
        else if (id === 4) { if (dX === 849) g.recall(dZ, player); else g.chase(dX, dZ, player); } else if (id === 5 && dX !== 513) g.retreat(dX, player);
      };
    },
    onTick(g, ctx) {
      const t = g.t;
      if (CPS.includes(t)) {
        const terr = [], bal = [];
        for (let q = 0; q < ctx.H; q++) {
          const on = g.alive[q] && g.state[q] !== 2 && g.terr[q] > 0;
          terr.push(on ? g.terr[q] : -1);
          bal.push(on ? g.bal[q] : -1);
        }
        cp[t] = { terr, bal };
      }
      if (t < T0 || t >= TEND) return;
      if (arm === 'wj') {
        for (let i = 0; i < delayed.length;) {
          if (delayed[i][0] <= t) { execRecorded(delayed[i][1]); delayed.splice(i, 1); } else i++;
        }
        return;
      }
      if (!probe) return;
      // 先执行到点的指令：同一拍每号最多 9 条（先到先得），多的丢掉
      if (outbox.length) {
        const cnt = new Map();
        for (let i = 0; i < outbox.length;) {
          const o = outbox[i];
          if (o[0] > t) { i++; continue; }
          const n = cnt.get(o[1]) || 0;
          if (n >= 9) stat.capDrop++;
          else { cnt.set(o[1], n + 1); execOne(g, o); }
          outbox.splice(i, 1);
        }
      }
      if (t % 5 !== 0) return;
      for (const p of own) {
        if (!g.alive[p] || g.state[p] === 2 || g.terr[p] <= 0) continue;
        if (t - (lastEmit.get(p) ?? -999) < 10) continue;
        const d = decide(g, ctx, p);
        if (!d) continue;
        const [q, troops] = d;
        const B = g.bal[p];
        const pct = Math.max(0, Math.min(1023, Math.ceil((troops * 1024) / B) - 1));
        lastEmit.set(p, t);
        lastTgt.set(p * 1024 + q, t);
        stat.dec++;
        let te;
        if (arm === 'p0') te = t;
        else if (arm === 'p14') te = ceil7(t + 14);
        else {
          te = ceil7(t + 7 + Math.floor(13 * rnd()));
          if (arm === 'ph') {
            for (const [a, b] of stalls[p] || []) if (t > a && t <= b - 7) { te = b; break; }
          }
        }
        const o = [te, p, pct, q, t, troops];
        if (te <= t) execOne(g, o); else outbox.push(o);
      }
    },
  });

  const H = R.H;
  // 630 拍以后的逐号地账（pairLog 的窗 30 拍一格，630 正好是窗边）：
  //   aiCells 从内置 AI 手里拿到的格｜gN 吃无主地｜gH 从真人（含空壳）手里拿到｜lAI 被内置 AI 咬走｜lH 被真人（含空壳）拿走
  //   dAI / dH 被内置 AI / 真人打掉的余额｜bAI / bN 打 AI / 吃无主地烧掉的兵
  const zero = () => new Array(H).fill(0);
  const aiCells = zero();
  const bud = { gN: zero(), gH: zero(), lAI: zero(), lH: zero(), dAI: zero(), dH: zero(), bAI: zero(), bN: zero() };
  for (const [t, atk, dfd, tiles, burnt, dB] of R.pairLog) {
    if (t <= T0) continue;
    if (atk < H) {
      if (dfd === NEUTRAL) { bud.gN[atk] += tiles; bud.bN[atk] += burnt; }
      else if (dfd >= H) { aiCells[atk] += tiles; bud.bAI[atk] += burnt; }
      else { bud.gH[atk] += tiles; bud.lH[dfd] += tiles; bud.dH[dfd] += dB; }
    } else if (dfd < H) { bud.lAI[dfd] += tiles; bud.dAI[dfd] += dB; }
  }
  // 别的真人的陆攻：按录像顺序的「生效」标记（各臂顺序一致，逐条可比）
  const wild = [];
  const ownRec = { exec: 0, ok: 0, perTurn: new Map() };
  for (const c of R.cmdLog) {
    const [t, p, kind, , , ok] = c;
    if (t < T0 || t > TEND) continue;
    if (ownSet.has(p)) {
      if (kind >= 1 && kind <= 3) {
        ownRec.exec++;
        if (kind === 1 && ok) ownRec.ok++;
        if (kind === 1) ownRec.atk = (ownRec.atk || 0) + 1;
        const key = p * 4096 + t;
        ownRec.perTurn.set(key, (ownRec.perTurn.get(key) || 0) + 1);
      }
    } else if (kind === 1) wild.push([t, ok]);
  }
  const batchShare = (mp) => { let n = 0, b = 0; for (const v of mp.values()) { n += v; if (v >= 3) b += v; } return [n, b]; };
  let ownDead = 0;
  for (const p of own) if (R.deathT[p] > T0 && R.deathT[p] <= TEND) ownDead++;
  return {
    cp, aiCells, bud, ownDead, wild,
    probe: probe ? { dec: stat.dec, exec: stat.exec, ok: stat.ok, capDrop: stat.capDrop, intended: Math.round(stat.intended), sent: stat.sent, toAi: stat.toAi, okAi: stat.okAi, toNeutral: stat.toNeutral, batch: batchShare(stat.perTurn) } : null,
    rec: { exec: ownRec.exec, atk: ownRec.atk || 0, ok: ownRec.ok, batch: batchShare(ownRec.perTurn) },
    cmdLog: arm === 'fact' ? R.cmdLog : null, squad: R.squad, H, endTick: R.endTick, leftT: Array.from(R.leftT), validate: { rows: R.validate.rows, bothExact: R.validate.bothExact },
  };
}

const tStart = Date.now();
let did = 0;
for (const mid of ids) {
  if (Date.now() - tStart > budget) break;
  const t0 = Date.now();
  try {
    const F = runArm(mid, 'fact', [], {});
    const own = Object.values(F.squad).map((s) => s.id).filter((x) => x >= 0);
    if (F.endTick < 900 || !own.length) {
      fs.writeFileSync(path.join(outDir, `${mid}.json`), JSON.stringify({ matchId: mid, skip: F.endTick < 900 ? '录像不到 900 拍' : '没有认出本编队的号', endTick: F.endTick }));
      did++;
      continue;
    }
    // 历史卡顿：每个本编队号的落地拍 → [沉默起点, 成批落地的那一拍, 条数]
    const land = new Map();
    for (const c of F.cmdLog) {
      const [t, p, kind] = c;
      if (!own.includes(p) || kind < 1 || kind > 5) continue;
      if (!land.has(p)) land.set(p, new Map());
      land.get(p).set(t, (land.get(p).get(t) || 0) + 1);
    }
    const stalls = {};
    for (const [p, mp] of land) {
      const ts = [...mp.keys()].sort((a, b) => a - b);
      const list = [];
      for (let i = 0; i < ts.length; i++) {
        const prev = i ? ts[i - 1] : 0;
        if (mp.get(ts[i]) >= 3 && ts[i] - prev >= 70 && ts[i] > T0) list.push([prev, ts[i], mp.get(ts[i])]);
      }
      if (list.length) stalls[p] = list;
    }
    // 重跑 fact（带上 own，统计本编队录像指令的签名）
    const arms = {};
    const base = runArm(mid, 'fact', own, stalls);
    const strip = (A) => ({ cp: A.cp, aiCells: A.aiCells, bud: A.bud, ownDead: A.ownDead, probe: A.probe, rec: A.rec });
    arms.fact = strip(base);
    const wf = base.wild;
    for (const arm of ARMS.slice(1)) {
      const A = runArm(mid, arm, own, stalls);
      const div = DWIN.slice(1).map(() => [0, 0, 0, 0]);   // [条数, 翻面, 历史生效→现在没生效, 历史没生效→现在生效]
      const n = Math.min(wf.length, A.wild.length);
      for (let i = 0; i < n; i++) {
        const t = wf[i][0];
        const k = t <= DWIN[1] ? 0 : t <= DWIN[2] ? 1 : 2;
        div[k][0]++;
        if (wf[i][1] !== A.wild[i][1]) { div[k][1]++; if (wf[i][1]) div[k][2]++; else div[k][3]++; }
      }
      arms[arm] = { ...strip(A), wildDiv: div, wildLenSame: wf.length === A.wild.length };
    }
    const out = { matchId: mid, H: base.H, endTick: base.endTick, own, leftT: base.leftT, validate: base.validate, stalls, arms };
    fs.writeFileSync(path.join(outDir, `${mid}.json`), JSON.stringify(out));
    console.log(`${mid}: 到 ${base.endTick} 拍，own ${own.length} 个，历史卡顿 ${Object.values(stalls).reduce((a, v) => a + v.length, 0)} 段，${((Date.now() - t0) / 1000).toFixed(1)} 秒`);
  } catch (e) {
    fs.writeFileSync(path.join(outDir, `${mid}.json`), JSON.stringify({ matchId: mid, error: String((e && e.message) || e) }));
    console.log(`${mid}: 失败 ${String((e && e.stack) || e).slice(0, 300)}`);
  }
  did++;
}
const left = ids.length - did;
console.log(`cfprobe: 本轮 ${did} 局${left > 0 ? `，还剩 ${left} 局，再跑一次` : '，全部做完'}`);
