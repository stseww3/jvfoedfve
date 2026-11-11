#!/usr/bin/env node
// 94_conquest.mjs — R07：逐格过户账——每个时间段里，谁从谁手里拿走了多少格地。
//
// 用来回答「这几百万兵打出去换回了几格」「对面崩掉的那一队的地被谁分了」「我方丢的地到了谁手里」。
// 做法：在干净模拟器重演里包住三个引擎函数（game.js）：
//   expandAttack(p, a)   一条进攻推进一圈：调用前后 terr[p] 的差就是这一圈拿到的格数，目标是 atkTarget（真人 / 内置 AI / 无主地）；
//   clearTerritory(p)    崩盘清场（aliveTick：领土 ≤ 峰值的 1/4 → collapse → 整块地变成无主地，压在它身上的进攻改打无主地）：
//                        清场前把它每一格记上「原主」，之后谁把这格当无主地捡走，就记成「捡了它崩盘后的地」；
//   tick()               取拍号、记期初领土。
// 口径：
//   · 「直接打下」= 进攻目标就是那个玩家时拿到的格数；「崩盘后捡走」= 那个玩家清场之后变成无主地的格被捡走（每格只算第一次）。
//   · 分组：我方号 / 同队其他真人 / T<n> 真人 / 内置 AI。真人席位离开后被内置 AI 接管的仍按原来的队算（地还是那块地）。
//   · 核对：每个玩家「期末领土 − 出生阶段结束时的领土」应等于「吃进 − 被直接打掉 − 清场放掉」，不等的人数写在表头（应为 0）。
//
// 用法（必须套重计算闸）：
//   bash c136-review/tools/run-heavy.sh node c136-review/agents/R07/scripts/94_conquest.mjs <matchId> --cuts 0,990,1530,2610,3960,5670,7498 [--focus 32,40,kaito9] [--tag name]
// 输出：out/<matchId>/conquest[_tag].txt
//   A. 分组 × 时间段的过户矩阵（行 = 吃地的一方，列 = 地原来是谁的；每格「直接打下 + 崩盘后捡走」）
//   B. 我方每个号 × 时间段：吃进（按来源）/ 被打掉（按对手）/ 清场放掉
//   C. 每个 --focus 玩家 × 时间段：它的地被谁拿走、它从谁手里拿
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const DATA = '/agent/repos/c136-data';
const HERE = path.dirname(fileURLToPath(import.meta.url));
const args = process.argv.slice(2);
const mid = args[0];
const opt = (k, d) => { const i = args.indexOf(k); return i >= 0 ? args[i + 1] : d; };
if (!mid || !opt('--cuts')) { console.error('用法：94_conquest.mjs <matchId> --cuts 0,990,1530,... [--focus id或名字片段,...] [--tag name]'); process.exit(2); }
const cuts = opt('--cuts').split(',').map(Number);
const focusArg = opt('--focus', '').split(',').map((s) => s.trim()).filter(Boolean);
const tag = opt('--tag', '');
const OUT = path.join(HERE, '..', 'out', mid);
fs.mkdirSync(OUT, { recursive: true });
const SIM = await import(path.join(DATA, 'src/sim/sim/index.js'));
(await import(path.join(HERE, 'r07simfix.mjs'))).applyOddLandingFix(SIM);
const { resim } = await import(path.join(DATA, 'src/tools/resim.mjs'));
const LIB = await import(path.join(DATA, 'src/sim/tools/c102-replay-lib.mjs'));
const { NEUTRAL } = SIM;
const d = LIB.decodeReplay(fs.readFileSync(path.join(DATA, 'bundles', mid, 'replay.txt'), 'utf8'));
const H = d.vu.humanCount;
const names = d.vu.playerNamesData ? Array.from(d.vu.playerNamesData).slice(0, H).map((s) => String(s ?? '').trim()) : [];
const SQUAD = ['sora_w', 'ryan_m', 'noah88', 'zexos1', 'talon5', 'alex_k', 'leo_tx', 'zero_7', 'kaito9', 'riku_x'];
const squadOf = (p) => { const n = (names[p] || '').toLowerCase(); for (const s of SQUAD) if (n.endsWith(s)) return s; return null; };
const fmt = (n) => Math.round(n).toLocaleString('en-US');

const spanOf = (t) => { for (let i = cuts.length - 2; i >= 0; i--) if (t >= cuts[i]) return i; return 0; };
const nSpan = cuts.length - 1;
// direct[span]: Map(taker*4096 + from) -> cells；from: 0..N-1 玩家，N = 原生无主地
// picked[span]: Map(taker*4096 + exOwner) -> cells（崩盘后变成无主地再被捡走）
const direct = Array.from({ length: nSpan }, () => new Map());
const picked = Array.from({ length: nSpan }, () => new Map());
const released = Array.from({ length: nSpan }, () => new Map());
const add = (m, k, v) => m.set(k, (m.get(k) || 0) + v);
const NEUT = 4095;
let prevOwner = null;
let terr0 = null, teams = null, lastT = 0, terrEnd = null, tStart = -1;
const gainTot = new Map(), lossTot = new Map(), relTot = new Map();

const proto = SIM.Game.prototype;
const origTick = proto.tick;
proto.tick = function () {
  if (!this.over && !this.spawnPhase && terr0 === null) {
    terr0 = Array.from(this.terr);
    teams = Array.from(this.teams);
    tStart = this.t;
    prevOwner = new Int16Array(this.px.length).fill(-1);
  }
  origTick.call(this);
  if (terr0 !== null) { lastT = this.t; terrEnd = this.terr; }
};
const origExpand = proto.expandAttack;
proto.expandAttack = function (p, a) {
  const target = this.atkTarget[this.slotBase(p) + a];
  const before = this.terr[p];
  origExpand.call(this, p, a);
  const gain = this.terr[p] - before;
  if (gain <= 0 || terr0 === null) return;
  const s = spanOf(this.t);
  add(gainTot, p, gain);
  if (target === NEUTRAL) {
    const cand = this.cand;
    let fresh = 0;
    for (let i = 0; i < gain; i++) {
      const c = cand[i];
      const q = prevOwner[c];
      if (q >= 0) { add(picked[s], p * 4096 + q, 1); prevOwner[c] = -1; } else fresh++;
    }
    if (fresh) add(direct[s], p * 4096 + NEUT, fresh);
  } else {
    add(direct[s], p * 4096 + target, gain);
    add(lossTot, target, gain);
  }
};
const origClear = proto.clearTerritory;
proto.clearTerritory = function (p) {
  if (terr0 !== null && this.terr[p] > 0) {
    const W = this.W;
    let n = 0;
    for (let x = this.x1[p]; x >= this.x0[p]; x--) {
      for (let y = this.y1[p]; y >= this.y0[p]; y--) {
        const c = y * W + x;
        if (this.ownedBy(p, c)) { prevOwner[c] = p; n++; }
      }
    }
    add(released[spanOf(this.t)], p, n);
    add(relTot, p, n);
  }
  origClear.call(this, p);
};

const res = await resim(mid, { until: cuts[cuts.length - 1] + 5 });
const v = res.validate || {};

let bad = 0;
const badList = [];
for (let p = 0; p < terr0.length; p++) {
  const exp = terr0[p] + (gainTot.get(p) || 0) - (lossTot.get(p) || 0) - (relTot.get(p) || 0);
  if (exp !== terrEnd[p]) { bad++; if (badList.length < 8) badList.push(`#${p}: 期初 ${terr0[p]} + 吃进 ${gainTot.get(p) || 0} − 被打掉 ${lossTot.get(p) || 0} − 清场 ${relTot.get(p) || 0} = ${exp} ≠ 期末 ${terrEnd[p]}`); }
}

const ourTeam = (() => { for (let p = 0; p < H; p++) if (squadOf(p)) return teams[p]; return 0; })();
const groupOf = (o) => (o === NEUT ? '原生无主地' : o >= H ? '内置 AI' : squadOf(o) ? '我方号' : teams[o] === ourTeam ? `T${teams[o]} 同队其他真人` : `T${teams[o]} 真人`);
const label = (o) => (o === NEUT ? '原生无主地' : o >= H ? `AI#${o}` : `${squadOf(o) ? '*' + squadOf(o) : names[o].slice(0, 18)}#${o}[T${teams[o]}]`);
const groupOrder = (a, b) => {
  const rk = (k) => (k === '我方号' ? 0 : k.includes('同队') ? 1 : k.startsWith('T') ? 2 : k === '内置 AI' ? 8 : 9);
  return rk(a) - rk(b) || a.localeCompare(b);
};

const L = [];
L.push(`# ${mid} 逐格过户账（94_conquest.mjs；干净模拟器重演，与 traj.csv 核对 ${v.bothExact}/${v.rows}；从出生阶段结束 t=${tStart} 记到 t=${lastT}）`);
L.push(`# 核对：全部 ${terr0.length} 个玩家里「期初 + 吃进 − 被直接打掉 − 清场放掉 ≠ 期末领土」的有 ${bad} 个${bad ? '：' + badList.join('；') : ''}`);
L.push('# 每格「直接打下 + 崩盘后捡走」：直接打下 = 进攻目标就是它；崩盘后捡走 = 它的领土跌到峰值 1/4 以下被引擎清场成无主地之后，被谁捡走（每格只算第一次）');
L.push('');
L.push('A. 分组 × 时间段：行 = 吃地的一方，列 = 地原来是谁的');
for (let s = 0; s < nSpan; s++) {
  const M = new Map();
  const cols = new Set();
  const put = (src, isPick) => {
    for (const [k, c] of src) {
      const taker = Math.floor(k / 4096), from = k % 4096;
      const gt = groupOf(taker), gf = groupOf(from);
      cols.add(gf);
      if (!M.has(gt)) M.set(gt, new Map());
      const row = M.get(gt);
      if (!row.has(gf)) row.set(gf, [0, 0]);
      row.get(gf)[isPick ? 1 : 0] += c;
    }
  };
  put(direct[s], false);
  put(picked[s], true);
  const cs = [...cols].sort(groupOrder);
  L.push(`## t=${cuts[s]}~${cuts[s + 1]}`);
  L.push(['吃地的一方', ...cs.map((c) => '从 ' + c), '吃进合计'].join('\t'));
  for (const gt of [...M.keys()].sort(groupOrder)) {
    const row = M.get(gt);
    let tot = 0;
    const cells = cs.map((c) => { const x = row.get(c) || [0, 0]; tot += x[0] + x[1]; return x[1] ? `${fmt(x[0])} + ${fmt(x[1])}` : fmt(x[0]); });
    L.push([gt, ...cells, fmt(tot)].join('\t'));
  }
  const rel = new Map();
  for (const [p, n] of released[s]) add(rel, groupOf(p), n);
  if (rel.size) L.push('清场放掉（变成无主地）：' + [...rel].sort((a, b) => groupOrder(a[0], b[0])).map(([k, n]) => `${k} ${fmt(n)}`).join('；'));
  L.push('');
}

const perPlayer = (p, s) => {
  const got = new Map(), lost = new Map();
  for (const [k, c] of direct[s]) {
    const taker = Math.floor(k / 4096), from = k % 4096;
    if (taker === p) { if (!got.has(from)) got.set(from, [0, 0]); got.get(from)[0] += c; }
    if (from === p) { if (!lost.has(taker)) lost.set(taker, [0, 0]); lost.get(taker)[0] += c; }
  }
  for (const [k, c] of picked[s]) {
    const taker = Math.floor(k / 4096), from = k % 4096;
    if (taker === p) { if (!got.has(from)) got.set(from, [0, 0]); got.get(from)[1] += c; }
    if (from === p) { if (!lost.has(taker)) lost.set(taker, [0, 0]); lost.get(taker)[1] += c; }
  }
  return { got, lost, rel: released[s].get(p) || 0 };
};
const showList = (m, top, mergeAI) => {
  const mm = new Map();
  for (const [o, x] of m) {
    const key = mergeAI && o >= H && o !== NEUT ? '内置 AI（合并）' : label(o);
    if (!mm.has(key)) mm.set(key, [0, 0]);
    mm.get(key)[0] += x[0]; mm.get(key)[1] += x[1];
  }
  const arr = [...mm].sort((a, b) => (b[1][0] + b[1][1]) - (a[1][0] + a[1][1]));
  const tot = arr.reduce((a, [, x]) => a + x[0] + x[1], 0);
  const txt = arr.slice(0, top).map(([k, x]) => `${k} ${fmt(x[0])}${x[1] ? ' + ' + fmt(x[1]) : ''}`).join('、');
  return { tot, txt: txt || '-' };
};

L.push('B. 我方每个号 × 时间段：吃进（按来源）| 被打掉（按对手：直接 + 清场后被捡走）| 清场放掉');
L.push('时间段\t号\t吃进合计\t来源\t被直接打掉合计\t对手\t清场放掉');
for (let s = 0; s < nSpan; s++) {
  for (let p = 0; p < H; p++) {
    if (!squadOf(p)) continue;
    const r = perPlayer(p, s);
    const g = showList(r.got, 6, true);
    const lostDirect = [...r.lost.values()].reduce((a, x) => a + x[0], 0);
    const l = showList(r.lost, 6, true);
    if (!g.tot && !l.tot && !r.rel) continue;
    L.push([`${cuts[s]}~${cuts[s + 1]}`, squadOf(p), fmt(g.tot), g.txt, fmt(lostDirect), l.txt, fmt(r.rel)].join('\t'));
  }
}
L.push('');

const focus = [];
for (const f of focusArg) {
  if (/^\d+$/.test(f)) focus.push(Number(f));
  else { for (let p = 0; p < H; p++) if ((names[p] || '').toLowerCase().includes(f.toLowerCase())) focus.push(p); }
}
if (focus.length) {
  L.push('C. 指定玩家 × 时间段：它从谁手里拿（直接 + 捡崩盘后的）| 它的地被谁拿走（直接 + 清场后被捡走）| 清场放掉');
  for (const p of focus) {
    L.push(`## ${label(p)}`);
    for (let s = 0; s < nSpan; s++) {
      const r = perPlayer(p, s);
      const g = showList(r.got, 8, true), l = showList(r.lost, 8, true);
      if (!g.tot && !l.tot && !r.rel) continue;
      L.push(`  t=${cuts[s]}~${cuts[s + 1]}: 吃进 ${fmt(g.tot)}（${g.txt}）| 被拿走 ${fmt(l.tot)}（${l.txt}）| 清场放掉 ${fmt(r.rel)}`);
    }
  }
  L.push('');
}
const file = path.join(OUT, `conquest${tag ? '_' + tag : ''}.txt`);
fs.writeFileSync(file, L.join('\n') + '\n');
process.stdout.write(L.slice(0, 60).join('\n') + `\nwrote ${file}\n`);
