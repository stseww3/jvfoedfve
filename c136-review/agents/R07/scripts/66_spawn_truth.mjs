#!/usr/bin/env node
// 66_spawn_truth.mjs — R07：出生点真值。按录像重演到出生阶段结束，读出每个号「真正落在哪」，
// 与（a）协调器最后一次指派（日志 [HL-SPAWN-BACKEND]）、（b）该号录像里最后一条出生指令 逐一对照。
// 用来核对广播 0003-⑥：协调器反复重算时有没有两个号被指到同一个点、有没有号的最后一条指令没生效。
//
// 引擎规则（干净模拟器 src/sim/sim/game.js placeSpawnNear / spawnAreaFree）：出生指令指向 (x,y) 时，
// 从半径 0 到 19 逐圈找第一个「6×6 范围内没有别人边界格」的位置落下；所以两个号指同一个点时，后到的会被挪到几格之外。
//
// 用法（必须套重计算闸）：
//   bash c136-review/tools/run-heavy.sh node c136-review/agents/R07/scripts/66_spawn_truth.mjs <matchId>
// 输出：out/<matchId>/spawn_truth.txt、spawn_truth.tsv
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const DATA = '/agent/repos/c136-data';
const HERE = path.dirname(fileURLToPath(import.meta.url));
const mid = process.argv[2];
if (!mid) { console.error('用法：66_spawn_truth.mjs <matchId>'); process.exit(2); }
const OUT = path.join(HERE, '..', 'out', mid);
fs.mkdirSync(OUT, { recursive: true });

const SIM = await import(path.join(DATA, 'src/sim/sim/index.js'));
const { resim } = await import(path.join(DATA, 'src/tools/resim.mjs'));
const LIB = await import(path.join(DATA, 'src/sim/tools/c102-replay-lib.mjs'));

const d = LIB.decodeReplay(fs.readFileSync(path.join(DATA, 'bundles', mid, 'replay.txt'), 'utf8'));
const H = d.vu.humanCount;
const names = d.vu.playerNamesData ? Array.from(d.vu.playerNamesData).slice(0, H).map((s) => String(s ?? '')) : [];
const logText = fs.readFileSync(path.join(DATA, 'bundles', mid, 'in_game.log'), 'utf8').split('\n');

// 我方号 + 协调器历次指派
const realBots = new Set();
const assigned = new Map(); // bot -> [{line, x, y, role}]
logText.forEach((ln, i) => {
  const m = /^\d+\t\[([A-Za-z0-9_]+)\] (.*)$/.exec(ln);
  if (!m) return;
  realBots.add(m[1]);
  const s = /\[HL-SPAWN(?:-BACKEND)?\] me=(\d+) slot=(\d+) role=(\S+) -> \((\d+),(\d+)\)/.exec(m[2]);
  if (s) {
    if (!assigned.has(m[1])) assigned.set(m[1], []);
    assigned.get(m[1]).push({ line: i + 1, x: +s[4], y: +s[5], role: s[3] });
  }
});
const idOf = new Map();
for (const b of realBots) for (let p = 0; p < H; p++) if (names[p].trim().toLowerCase().endsWith(b.toLowerCase())) { idOf.set(b, p); break; }
const botOf = new Map([...idOf].map(([b, p]) => [p, b]));

// 出生阶段的指令流（按到达顺序）：hook chooseSpawn / placeSpawnNear
const calls = []; // {seq, p, x, y, placedX, placedY}
let seq = 0;
let W = 0;
let snap = null;
const origNear = SIM.Game.prototype.placeSpawnNear;
SIM.Game.prototype.placeSpawnNear = function (pl, cx, cy) {
  const r = origNear.call(this, pl, cx, cy);
  W = this.W;
  if (pl < H) {
    const ax = (this.x0[pl] + this.x1[pl]) / 2, ay = (this.y0[pl] + this.y1[pl]) / 2;
    calls.push({ seq: seq++, p: pl, x: cx, y: cy, ok: r ? 1 : 0, ax, ay, t: this.t });
  }
  return r;
};
const origEnd = SIM.Game.prototype.endSpawnPhase;
SIM.Game.prototype.endSpawnPhase = function () {
  const was = this.spawnPhase;
  const r = origEnd.call(this);
  if (was && !snap) {
    snap = [];
    for (let p = 0; p < H; p++) snap.push({ p, alive: this.alive[p], terr: this.terr[p], x: (this.x0[p] + this.x1[p]) / 2, y: (this.y0[p] + this.y1[p]) / 2, team: this.teams ? this.teams[p] : 0 });
  }
  return r;
};

const res = await resim(mid, { until: 5 });
if (!snap) { console.error('没有捕捉到出生阶段结束（endSpawnPhase 未被调用）'); process.exit(1); }

const L = [];
const P = (s = '') => L.push(s);
P(`# ${mid} 出生点真值（重演到出生阶段结束；真值 = 该号领土包围盒的中心）`);
P(`# 录像里真人位 ${H} 个；出生阶段共 ${calls.length} 次有效的选点调用，其中我方 ${calls.filter((c) => botOf.has(c.p)).length} 次`);
P('');
P('A. 我方各号：真实落点 | 协调器最后一次指派（日志行） | 最后一条出生指令指向 | 真实落点离指派 / 离最后一条指令（像素） | 出生指令条数 | 协调器指派次数 | 最近队友（真值，像素）');
const rows = [];
const mine = [...idOf].map(([b, p]) => ({ b, p, s: snap[p] }));
for (const m of mine) {
  const cs = calls.filter((c) => c.p === m.p);
  const last = cs[cs.length - 1];
  const as = assigned.get(m.b) || [];
  const la = as[as.length - 1];
  const dA = la ? Math.hypot(m.s.x - la.x, m.s.y - la.y) : null;
  const dL = last ? Math.hypot(m.s.x - last.x, m.s.y - last.y) : null;
  let near = Infinity, nearB = '';
  for (const o of mine) if (o !== m) { const dd = Math.hypot(o.s.x - m.s.x, o.s.y - m.s.y); if (dd < near) { near = dd; nearB = o.b; } }
  // 同一拍里是否有队友的最后一条指令指向同一个点
  let sameAs = '';
  for (const o of mine) if (o !== m) { const oc = calls.filter((c) => c.p === o.p); const ol = oc[oc.length - 1]; if (ol && last && ol.x === last.x && ol.y === last.y) sameAs += (sameAs ? ',' : '') + o.b; }
  rows.push({ bot: m.b, p: m.p, x: m.s.x, y: m.s.y, asgX: la ? la.x : '', asgY: la ? la.y : '', asgLine: la ? la.line : '', lastX: last ? last.x : '', lastY: last ? last.y : '', dAsg: dA === null ? '' : dA.toFixed(1), dLast: dL === null ? '' : dL.toFixed(1), nCmd: cs.length, nAsg: as.length, near: near.toFixed(1), nearBot: nearB, sameAs, role: la ? la.role : '' });
  P(`  ${m.b.padEnd(8)} 真 (${m.s.x.toFixed(1)},${m.s.y.toFixed(1)}) | 指派 ${la ? `(${la.x},${la.y}) ${la.role} L${la.line}` : '-'} | 末条指令 ${last ? `(${last.x},${last.y})` : '-'} | ${dA === null ? '-' : dA.toFixed(1)} / ${dL === null ? '-' : dL.toFixed(1)} | ${cs.length} | ${as.length} | ${near.toFixed(1)}（${nearB}）${sameAs ? ` | 末条指令与 ${sameAs} 指向同一点` : ''}`);
}
const off = rows.filter((r) => r.dAsg !== '' && +r.dAsg > 6);
const dup = rows.filter((r) => r.sameAs);
P('');
P(`  真实落点偏离最后指派 >6 像素的号：${off.length ? off.map((r) => `${r.bot}（${r.dAsg}）`).join('、') : '无'}`);
P(`  末条出生指令与队友指向同一点的号：${dup.length ? dup.map((r) => `${r.bot}↔${r.sameAs}`).join('、') : '无'}`);
const nears = rows.map((r) => +r.near).sort((a, b) => a - b);
P(`  我方最近队友距离（真值）：最小 ${nears[0]}、中位 ${nears[nears.length >> 1]}、最大 ${nears[nears.length - 1]} 像素`);
const xs = rows.map((r) => r.x), ys = rows.map((r) => r.y);
P(`  我方包围盒：x ${Math.min(...xs).toFixed(0)}~${Math.max(...xs).toFixed(0)}、y ${Math.min(...ys).toFixed(0)}~${Math.max(...ys).toFixed(0)}（${(Math.max(...xs) - Math.min(...xs)).toFixed(0)}×${(Math.max(...ys) - Math.min(...ys)).toFixed(0)} 像素）`);

// B. 全场对照：每个真人到最近「同队真人」和最近「任何真人」的距离
P('');
P('B. 全场对照（出生阶段结束时，有地的真人）：到最近同队真人 / 最近任何真人的距离中位数（像素）');
const live = snap.filter((s) => s.alive && s.terr > 0);
const nn = (s, same) => { let b = Infinity; for (const o of live) { if (o === s) continue; if (same && o.team !== s.team) continue; const dd = Math.hypot(o.x - s.x, o.y - s.y); if (dd < b) b = dd; } return b; };
const med = (a) => { const v = a.filter(Number.isFinite).sort((x, y) => x - y); return v.length ? v[v.length >> 1] : NaN; };
const groups = new Map();
for (const s of live) { const k = botOf.has(s.p) ? '我方号' : `T${s.team} 其他真人`; if (!groups.has(k)) groups.set(k, []); groups.get(k).push(s); }
for (const [k, arr] of [...groups].sort()) P(`  ${k.padEnd(10)} ${String(arr.length).padStart(3)} 人：最近同队 ${med(arr.map((s) => nn(s, true))).toFixed(1)}、最近任何真人 ${med(arr.map((s) => nn(s, false))).toFixed(1)}`);
P(`  全场 ${live.length} 人：最近任何真人 ${med(live.map((s) => nn(s, false))).toFixed(1)}`);

// C. 我方最后 12 次选点调用的先后（看对调）
P('');
P('C. 我方出生指令的到达顺序（最后 16 条）：序号 号 → 指向 (x,y) ⇒ 当时实际落在 (x,y)');
const mineCalls = calls.filter((c) => botOf.has(c.p));
for (const c of mineCalls.slice(-16)) P(`  #${c.seq} ${botOf.get(c.p).padEnd(8)} → (${c.x},${c.y}) ⇒ (${c.ax.toFixed(1)},${c.ay.toFixed(1)})${Math.hypot(c.ax - c.x, c.ay - c.y) > 6 ? '  ← 被挪开 ' + Math.hypot(c.ax - c.x, c.ay - c.y).toFixed(1) + ' 像素' : ''}`);
const moved = mineCalls.filter((c) => Math.hypot(c.ax - c.x, c.ay - c.y) > 6);
P(`  全部 ${mineCalls.length} 条里，落点被引擎挪开 >6 像素的 ${moved.length} 条`);

const txt = L.join('\n') + '\n';
fs.writeFileSync(path.join(OUT, 'spawn_truth.txt'), txt);
const cols = ['bot', 'p', 'x', 'y', 'asgX', 'asgY', 'asgLine', 'lastX', 'lastY', 'dAsg', 'dLast', 'nCmd', 'nAsg', 'near', 'nearBot', 'sameAs', 'role'];
fs.writeFileSync(path.join(OUT, 'spawn_truth.tsv'), cols.join('\t') + '\n' + rows.map((r) => cols.map((c) => r[c]).join('\t')).join('\n') + '\n');
process.stdout.write(txt);
