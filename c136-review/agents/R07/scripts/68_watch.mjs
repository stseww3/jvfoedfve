#!/usr/bin/env node
// 68_watch.mjs — R07：盯住任意几个玩家（不限我方号）：每隔 step 拍打印领土/余额/密度、正在打谁、被谁打，
// 以及他们每条录像指令的真实花费。用来回答「对手/队友那边发生了什么」。
//
// 用法（必须套重计算闸）：
//   bash c136-review/tools/run-heavy.sh node c136-review/agents/R07/scripts/68_watch.mjs <matchId> --ids 44,8 [--t0 6000] [--t1 7600] [--step 30] [--cmds 1] [--tag name]
//   --ids 可以写玩家号，也可以写我方号的名字（zero_7）；--cmds 1 同时列出这些玩家的每条指令
// 输出：out/<matchId>/watch_<tag 或 ids>.txt
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const DATA = '/agent/repos/c136-data';
const HERE = path.dirname(fileURLToPath(import.meta.url));
const args = process.argv.slice(2);
const mid = args[0];
const opt = (k, d) => { const i = args.indexOf(k); return i >= 0 ? args[i + 1] : d; };
if (!mid || !opt('--ids')) { console.error('用法：68_watch.mjs <matchId> --ids 44,8 [--t0 T] [--t1 T] [--step 30] [--cmds 1] [--tag name]'); process.exit(2); }
const OUT = path.join(HERE, '..', 'out', mid);
fs.mkdirSync(OUT, { recursive: true });
const SIM = await import(path.join(DATA, 'src/sim/sim/index.js'));
// 船落在没人占的水 / 边界 / 山格时按线上规则处理（见 r07simfix.mjs；来自 R01 的 resim_lib_r01.mjs）
(await import(path.join(HERE, 'r07simfix.mjs'))).applyOddLandingFix(SIM);
const { resim } = await import(path.join(DATA, 'src/tools/resim.mjs'));
const LIB = await import(path.join(DATA, 'src/sim/tools/c102-replay-lib.mjs'));
const { NEUTRAL, iV } = SIM;
const d = LIB.decodeReplay(fs.readFileSync(path.join(DATA, 'bundles', mid, 'replay.txt'), 'utf8'));
const H = d.vu.humanCount;
const names = d.vu.playerNamesData ? Array.from(d.vu.playerNamesData).slice(0, H).map((s) => String(s ?? '')) : [];
const ids = opt('--ids').split(',').map((s) => {
  if (/^\d+$/.test(s)) return +s;
  for (let p = 0; p < H; p++) if (names[p].trim().toLowerCase().endsWith(s.toLowerCase())) return p;
  console.error('找不到玩家：' + s); process.exit(2);
});
const t0 = +opt('--t0', 0), t1 = +opt('--t1', 1e9), step = +opt('--step', 30), wantCmds = +opt('--cmds', 0);
const tag = opt('--tag', ids.join('_'));
const watch = new Set(ids);
const nm = (g, q) => q >= NEUTRAL ? '无主地' : q < H ? `${(names[q] || '').trim().slice(0, 14)}#${q}[T${g.teams ? g.teams[q] : 0}${g.state[q] === 2 ? '离' : ''}]` : `AI#${q}`;
const proto = SIM.Game.prototype;
const lines = [];
const cmds = [];
for (const kind of ['attack', 'donate', 'boat', 'boatTo', 'chase', 'retreat']) {
  const orig = proto[kind];
  if (typeof orig !== 'function') continue;
  proto[kind] = function (...a) {
    const p = a[a.length - 1];
    const g = this;
    const mine = Number.isInteger(p) && watch.has(p) && g.t >= t0 && g.t <= t1;
    const toW = kind === 'donate' && watch.has(a[1]) && g.t >= t0 && g.t <= t1;
    if (!mine && !toW) return orig.apply(this, a);
    const b0 = Number.isInteger(p) ? g.bal[p] : 0;
    const tg = kind === 'attack' ? Math.min(a[1], NEUTRAL) : kind === 'donate' ? a[1] : kind === 'retreat' ? Math.min(a[0], NEUTRAL) : -1;
    const tb0 = tg >= 0 && tg < NEUTRAL ? g.bal[tg] : 0, tt0 = tg >= 0 && tg < NEUTRAL ? g.terr[tg] : 0;
    const ok = orig.apply(this, a);
    const b1 = Number.isInteger(p) ? g.bal[p] : 0;
    cmds.push(`  t=${g.t} ${nm(g, p)} ${kind} pct=${kind === 'retreat' ? '-' : a[0]} → ${tg >= 0 ? nm(g, tg) : '船'} | 余额 ${b0}→${b1}（花 ${b0 - b1}）${ok ? '' : ' 未生效'}${tg >= 0 && tg < NEUTRAL ? ` | 目标 ${tt0} 格 / ${tb0} 兵（密度 ${(tb0 / Math.max(1, tt0)).toFixed(0)}）` : ''}`);
    return ok;
  };
}
// 内置 AI（含离开后被接管的座位）送兵走的是 transfer，不是 donate 指令：单独挂钩记下来
const origTransfer = proto.transfer;
proto.transfer = function (p, q, troops) {
  const g = this;
  const hit = (watch.has(p) || watch.has(q)) && g.t >= t0 && g.t <= t1 && (p >= H || g.state[p] === 2);
  const b0 = g.bal[p];
  const v = origTransfer.call(this, p, q, troops);
  if (hit && v > 0) cmds.push(`  t=${g.t} ${nm(g, p)} 〔内置 AI 送兵〕→ ${nm(g, q)} | 余额 ${b0}→${g.bal[p]}（到账 ${v}，手续费 ${b0 - g.bal[p] - v}）`);
  return v;
};
// 船靠岸：落在谁的地上、带了多少兵、之后变成什么（落在队友岸上 = 免手续费送兵，受捐方配额或 150×领土硬上限装不下的部分直接没了）
const origLandAt = proto.landAt;
proto.landAt = function (p, troops, c, at) {
  const g = this;
  const hit = watch.has(p) && g.t >= t0 && g.t <= t1;
  if (!hit) return origLandAt.call(this, p, troops, c, at);
  const v = g.px[c];
  const tgt = v === SIM.T_LAND ? NEUTRAL : (v >= SIM.P_INNER ? g.own[c] : -1);
  const tb0 = tgt >= 0 && tgt < NEUTRAL ? g.bal[tgt] : 0;
  const b0 = g.bal[p];
  const r = origLandAt.call(this, p, troops, c, at);
  const W = g.w || g.W || g.width;
  let what;
  if (tgt === NEUTRAL) what = '无主地（变成进攻）';
  else if (tgt < 0) what = '没靠上岸（兵没了）';
  else if (tgt === p) what = `自己的地（兵回到余额 ${b0}→${g.bal[p]}）`;
  else if (!g.isEnemy(p, tgt)) what = `队友 ${nm(g, tgt)} 的岸：对方余额 ${tb0}→${g.bal[tgt]}（到账 ${g.bal[tgt] - tb0}，没到账 ${troops - (g.bal[tgt] - tb0)}；对方 ${g.terr[tgt]} 格，硬上限 ${150 * g.terr[tgt]}）`;
  else what = `敌方 ${nm(g, tgt)}（变成进攻，对方 ${g.terr[tgt]} 格 / ${g.bal[tgt]} 兵）`;
  cmds.push(`  t=${g.t} ${nm(g, p)} 〔船靠岸〕带 ${troops} 兵，落点${W ? `(${c % W},${Math.floor(c / W)})` : c} → ${what}`);
  return r;
};
const origTick = proto.tick;
proto.tick = function () {
  origTick.call(this);
  const g = this;
  if (g.spawnPhase || g.t < t0 || g.t > t1 || g.t % step !== 0) return;
  for (const p of ids) {
    if (!g.alive[p]) { lines.push(`t=${g.t} ${nm(g, p)} 已出局`); continue; }
    const b = g.slotBase(p);
    const outs = [];
    for (let i = 0; i < g.atkCount[p]; i++) outs.push(`${nm(g, g.atkTarget[b + i])}:${g.atkTroops[b + i]}`);
    const ins = g.attackersOf(p).map((q) => `${nm(g, q)}:${g.attackTroopsOn(q, p)}`);
    lines.push(`t=${g.t} ${nm(g, p)} ${g.terr[p]} 格 / ${g.bal[p]} 兵（密度 ${(g.bal[p] / Math.max(1, g.terr[p])).toFixed(0)}）| 在打 ${outs.join('、') || '-'} | 被打 ${ins.join('、') || '-'}`);
  }
};
const res = await resim(mid, { until: Math.min(t1 + 5, 1e9) });
const v = res.validate || {};
const txt = `# ${mid} 盯人：${ids.map((p) => `${(names[p] || '').trim()}#${p}`).join('、')}（t=${t0}~${Math.min(t1, res.endTick)}，每 ${step} 拍；重演核对 ${v.bothExact}/${v.rows}）\n` + lines.join('\n') + '\n' + (wantCmds ? '# 指令\n' + cmds.join('\n') + '\n' : '');
fs.writeFileSync(path.join(OUT, `watch_${tag}.txt`), txt);
process.stdout.write(txt.split('\n').slice(0, 14).join('\n') + `\n…（共 ${lines.length} 行状态，${cmds.length} 条指令）\n`);
