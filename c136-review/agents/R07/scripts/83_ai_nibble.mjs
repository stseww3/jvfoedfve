#!/usr/bin/env node
// 83_ai_nibble.mjs — R07：一个内置 AI（或任何玩家）是怎么啃掉旁边一个号的地的：
// 逐段统计它对这个号新发了几次进攻、每次押了多少兵、赊了多少账（引擎 takeBalance：余额不够的部分记 debt，上限 5 万），
// 以及这一段两边的领土 / 余额变化。用来核对「0 兵的 AI 也能一圈一圈拿地」是引擎里哪一条规则。
//
// 用法（必须套重计算闸）：
//   bash c136-review/tools/run-heavy.sh node c136-review/agents/R07/scripts/83_ai_nibble.mjs <matchId> --ai 502 --bot alex_k [--t0 1500] [--t1 2560] [--step 100]
// 输出：out/<matchId>/ai_nibble_<ai>_<bot>.txt
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const DATA = '/agent/repos/c136-data';
const HERE = path.dirname(fileURLToPath(import.meta.url));
const args = process.argv.slice(2);
const mid = args[0];
const opt = (k, d) => { const i = args.indexOf(k); return i >= 0 ? args[i + 1] : d; };
if (!mid || !opt('--ai') || !opt('--bot')) { console.error('用法：83_ai_nibble.mjs <matchId> --ai <玩家号> --bot <我方号名或玩家号> [--t0 T] [--t1 T] [--step 100]'); process.exit(2); }
const OUT = path.join(HERE, '..', 'out', mid);
fs.mkdirSync(OUT, { recursive: true });
const SIM = await import(path.join(DATA, 'src/sim/sim/index.js'));
const { resim } = await import(path.join(DATA, 'src/tools/resim.mjs'));
const LIB = await import(path.join(DATA, 'src/sim/tools/c102-replay-lib.mjs'));
const d = LIB.decodeReplay(fs.readFileSync(path.join(DATA, 'bundles', mid, 'replay.txt'), 'utf8'));
const H = d.vu.humanCount;
const names = d.vu.playerNamesData ? Array.from(d.vu.playerNamesData).slice(0, H).map((s) => String(s ?? '')) : [];
const pid = (s) => {
  if (/^\d+$/.test(s)) return +s;
  for (let p = 0; p < H; p++) if (names[p].trim().toLowerCase().endsWith(s.toLowerCase())) return p;
  console.error('找不到玩家：' + s); process.exit(2);
};
const AI = pid(opt('--ai')), BOT = pid(opt('--bot'));
const t0 = +opt('--t0', 0), t1 = +opt('--t1', 1e9), step = +opt('--step', 100);
const proto = SIM.Game.prototype;
let seg = null;
const newSeg = (g) => ({ t: g.t, aiTerr: g.terr[AI], aiBal: g.bal[AI], aiDebt: g.debt[AI], botTerr: g.terr[BOT], botBal: g.bal[BOT], commits: 0, committed: 0, zeroCommits: 0, credit: 0, creditCalls: 0, wins: 0, cells: 0 });
const rows = [];
const samples = [];
let inAiExpand = false;

const origCommit = proto.commitAttack;
proto.commitAttack = function (p, target, from, troops) {
  if (seg && p === AI && target === BOT) {
    seg.commits++;
    seg.committed += troops;
    if (!(troops > 0)) seg.zeroCommits++;
    if (samples.length < 12) samples.push(`  t=${this.t} AI#${AI} 新发进攻 → ${names[BOT].trim()}：押 ${troops} 兵（发令时余额 ${this.bal[AI]}，debt ${this.debt[AI]}）`);
  }
  return origCommit.call(this, p, target, from, troops);
};
const origExpandAttack = proto.expandAttack;
proto.expandAttack = function (p, a) {
  if (!seg || p !== AI) return origExpandAttack.call(this, p, a);
  const k = this.slotBase(p) + a;
  const onBot = this.atkTarget[k] === BOT;
  const terr0 = this.terr[BOT];
  inAiExpand = onBot;
  const r = origExpandAttack.call(this, p, a);
  inAiExpand = false;
  if (onBot && this.terr[BOT] < terr0) { seg.wins++; seg.cells += terr0 - this.terr[BOT]; }
  return r;
};
const origTake = proto.takeBalance;
proto.takeBalance = function (p, v) {
  if (seg && inAiExpand && p === AI && v > this.bal[p]) { seg.credit += v - this.bal[p]; seg.creditCalls++; }
  return origTake.call(this, p, v);
};
const origTick = proto.tick;
proto.tick = function () {
  origTick.call(this);
  const g = this;
  if (g.spawnPhase || g.t < t0 || g.t > t1) return;
  if (!seg) { seg = newSeg(g); return; }
  if ((g.t - t0) % step === 0) {
    rows.push({ ...seg, t1: g.t, aiTerr1: g.terr[AI], aiBal1: g.bal[AI], aiDebt1: g.debt[AI], botTerr1: g.terr[BOT], botBal1: g.bal[BOT], aiAlive: g.alive[AI] });
    seg = newSeg(g);
  }
};
const res = await resim(mid, { until: Math.min(t1 + 5, 1e9) });
const v = res.validate || {};
const f = (x) => Math.round(x).toLocaleString('en-US');
const L = [`# ${mid} AI#${AI} 对 ${names[BOT].trim()}#${BOT}（t=${t0}~${Math.min(t1, res.endTick)}，每 ${step} 拍一段；重演核对 ${v.bothExact}/${v.rows}）`,
  '# 「新发进攻」= 引擎 commitAttack（AI 每个决策周期发一次）；「赊账」= 这些进攻推进时 takeBalance 取的兵超过 AI 余额的部分（引擎记成 debt，debt 上限 50,000）；「拿下的圈」= expandAttack 赢下的次数',
  '段\tAI 领土\tAI 余额（debt）\t号 领土\t号 余额\tAI 新发进攻 次（其中押 0 兵的）\t押的兵合计\t赊账 次 / 兵\t拿下的圈 / 格'];
const tot = { commits: 0, zero: 0, committed: 0, credit: 0, creditCalls: 0, wins: 0, cells: 0 };
for (const r of rows) {
  L.push(`${r.t}~${r.t1}\t${f(r.aiTerr)}→${f(r.aiTerr1)}\t${f(r.aiBal)}→${f(r.aiBal1)}（${f(r.aiDebt)}→${f(r.aiDebt1)}）\t${f(r.botTerr)}→${f(r.botTerr1)}\t${f(r.botBal)}→${f(r.botBal1)}\t${r.commits}（${r.zeroCommits}）\t${f(r.committed)}\t${r.creditCalls} / ${f(r.credit)}\t${r.wins} / ${f(r.cells)}`);
  tot.commits += r.commits; tot.zero += r.zeroCommits; tot.committed += r.committed; tot.credit += r.credit; tot.creditCalls += r.creditCalls; tot.wins += r.wins; tot.cells += r.cells;
}
L.push(`合计\t\t\t\t\t${tot.commits}（${tot.zero}）\t${f(tot.committed)}\t${tot.creditCalls} / ${f(tot.credit)}\t${tot.wins} / ${f(tot.cells)}`);
L.push('# 前 12 次新发进攻');
L.push(...samples);
const txt = L.join('\n') + '\n';
fs.writeFileSync(path.join(OUT, `ai_nibble_${AI}_${BOT}.txt`), txt);
process.stdout.write(txt);
