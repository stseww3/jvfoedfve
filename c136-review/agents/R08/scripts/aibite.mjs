#!/usr/bin/env node
// aibite.mjs — 内置 AI / 空壳是怎么挑目标的、咬了真人多少地（发现集录像逐拍重演到 3000 拍的真值）。
//
//   bash c136-review/tools/run-heavy.sh node c136-review/agents/R08/scripts/aibite.mjs [<局> …] [--until 3000] [--budget 95]
//
// 不给局号 = 发现集里有录像、out/_run/aibite/ 下还没有结果的局，一个接一个做，做到时间预算（默认 95 秒）为止，再跑一次接着做。
// 做法：调 resim_r08.mjs 的 resim()（和 xtruth.mjs 同一份真引擎重演），只加只读的钩子：
//   · pickTargets / firstTarget：记下 AI 这次决策抽到的候选（过滤之前）；
//   · botAttackNeutral / botAttackPlayer：记下这次决策最后打了谁。
//     打真人（没离开的）的每一次记一行：
//       [t, 出手的号, 出手的是不是空壳, 目标, 派出的兵 dn, 出手方余额,
//        过滤前候选里：无主地 0/1、AI 或空壳的个数、真人的个数,
//        最后那份候选名单（引擎真正在里面挑的）里的真人：[[号, 余额 + 它压在出手方身上的兵, 兵密度×10, 包围盒中心到出手方中心的距离平方]…],
//        目标的地, 目标的余额, 这一口的战果 [吃到的格, 出手方烧的兵, 目标被打掉的余额, 圈数]]
//     战果 = 这一对 [出手方 → 目标] 从这次出手到下一次出手（最多 150 拍）之间的逐对战损账（30 拍一结，所以相邻两口挨得近时会有少量串账）。
//   · 决策计数：按「过滤前的候选是什么构成」分四类（有无主地 / 只有 AI 或空壳 / 只有真人 / 真人和 AI 或空壳都有），每类里最后打了谁。
//   · 逐对战损账（resim 自带的 pairLog，30 拍一结）：[出手方 → 真人] 吃了几格、出手方烧的兵、真人被打掉的余额、圈数。
//   · 窗首（600 / 900 / 1260 / 1500 / 1800 / 2400 / 3000）每个在线真人的地和余额（算人头用）。
// 只统计 600 < t ≤ until。钩子不改任何引擎状态；重演对不对得上日志由 xtruth.py 把关（这里只对「对得上」的局出数）。
// 每局一个文件 out/_run/aibite/<局>.json（不进 git）。只读 bundles/（发现集）。
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
const until = +take('until', 3000);
const budget = +take('budget', 95) * 1000;
const outDir = path.resolve(take('out-dir', path.join(HERE, '..', 'out', '_run', 'aibite')));
const { resim } = await import(path.join(HERE, 'resim_r08.mjs'));
fs.mkdirSync(outDir, { recursive: true });
const NEUTRAL = 512;
const T0 = 600;
const WIN = [600, 900, 1260, 1500, 1800, 2400, 3000];
const wOf = (t) => { for (let k = 0; k < WIN.length - 1; k++) if (t > WIN[k] && t <= WIN[k + 1]) return k; return -1; };

let ids = argv.slice();
if (!ids.length) {
  ids = fs.readFileSync(path.join(DATA, 'manifest.jsonl'), 'utf8').split('\n').filter(Boolean)
    .map((l) => JSON.parse(l)).filter((m) => m.split === 'discovery').map((m) => m.matchId).sort()
    .filter((mid) => fs.existsSync(path.join(DATA, 'bundles', mid, 'replay.txt')) && !fs.existsSync(path.join(outDir, `${mid}.json`)));
}
const tStart = Date.now();
let did = 0;
for (const mid of ids) {
  if (Date.now() - tStart > budget) break;
  const t0 = Date.now();
  const bites = [];
  // 决策计数：[窗][出手方类别 0 = 内置 AI，1 = 空壳][候选构成 0 = 有无主地，1 = 只有 AI / 空壳，2 = 只有真人，3 = 真人和 AI / 空壳都有]
  //   = [打无主地, 打 AI / 空壳, 打真人]
  const dec = Array.from({ length: WIN.length - 1 }, () => [0, 1].map(() => [0, 1, 2, 3].map(() => [0, 0, 0])));
  let R;
  const cp = {};   // 窗首（600 / 900 / …）每个真人的 [地, 余额]，离开的记 -1
  try {
    R = resim(mid, {
      until,
      onTick(g, ctx) {
        if (!WIN.includes(g.t)) return;
        const terr = [], bal = [];
        for (let q = 0; q < ctx.H; q++) {
          const on = g.alive[q] && g.state[q] !== 2 && g.terr[q] > 0;
          terr.push(on ? g.terr[q] : -1);
          bal.push(on ? g.bal[q] : -1);
        }
        cp[g.t] = { terr, bal };
      },
      onStart(g, ctx) {
        const H = ctx.H;
        const proto = Object.getPrototypeOf(g);
        const find = (name) => { let o = g; while (o && !Object.prototype.hasOwnProperty.call(o, name)) o = Object.getPrototypeOf(o); return o[name]; };
        const pickTargets0 = find('pickTargets'), firstTarget0 = find('firstTarget');
        const botAttackNeutral0 = find('botAttackNeutral'), botAttackPlayer0 = find('botAttackPlayer');
        let pre = null;   // 过滤前的候选：{p, neutral, bots, humans}
        const snapPre = (self, p) => {
          let neutral = 0, bots = 0, humans = 0;
          for (let i = 0; i < self.tgtCount; i++) {
            const o = self.tgt[i];
            if (o === NEUTRAL) neutral = 1; else if (self.isBot(o)) bots++; else humans++;
          }
          pre = { p, t: self.t, neutral, bots, humans };
        };
        g.pickTargets = function (p, any) {
          const r = pickTargets0.call(this, p, any);
          if (r) snapPre(this, p); else pre = null;
          return r;
        };
        g.firstTarget = function (p, any) {
          const r = firstTarget0.call(this, p, any);
          if (r) snapPre(this, p); else pre = null;
          return r;
        };
        const note = (self, p, kind) => {
          const k = wOf(self.t);
          if (k < 0 || !pre || pre.p !== p || pre.t !== self.t) return null;
          const cls = pre.neutral ? 0 : pre.humans === 0 ? 1 : pre.bots === 0 ? 2 : 3;
          dec[k][p < H ? 1 : 0][cls][kind - 1]++;
          return pre;
        };
        g.botAttackNeutral = function (p, dn) {
          note(this, p, 1);
          pre = null;
          return botAttackNeutral0.call(this, p, dn);
        };
        g.botAttackPlayer = function (p, dn, target, diff) {
          const human = target < H && !this.isBot(target);
          const pr = note(this, p, human ? 3 : 2);
          if (pr && human && this.t > T0) {
            const cx = (this.x1[p] + this.x0[p]) / 2, cy = (this.y1[p] + this.y0[p]) / 2;
            const cands = [];
            for (let i = 0; i < this.tgtCount; i++) {
              const o = this.tgt[i];
              if (o === NEUTRAL || this.isBot(o)) continue;
              const ox = (this.x1[o] + this.x0[o]) / 2, oy = (this.y1[o] + this.y0[o]) / 2;
              cands.push([o, this.bal[o] + this.attackTroopsOn(o, p), Math.round((10 * this.bal[o]) / Math.max(1, this.terr[o])), Math.round((cx - ox) ** 2 + (cy - oy) ** 2)]);
            }
            bites.push([this.t, p, p < H ? 1 : 0, target, dn, this.bal[p], pr.neutral, pr.bots, pr.humans, cands, this.terr[target], this.bal[target], [0, 0, 0, 0]]);
          }
          pre = null;
          return botAttackPlayer0.call(this, p, dn, target, diff);
        };
        void proto;
      },
    });
  } catch (e) {
    fs.writeFileSync(path.join(outDir, `${mid}.json`), JSON.stringify({ matchId: mid, error: String((e && e.message) || e) }));
    console.log(`${mid}: 失败 ${String((e && e.message) || e).slice(0, 120)}`);
    did++;
    continue;
  }
  const H = R.H;
  const leftT = R.leftT;
  // 逐对战损：[窗][真人] = 被内置 AI：[格, AI 烧的兵, 被打掉的余额, 圈数]；被空壳：同四项
  const loss = Array.from({ length: WIN.length - 1 }, () => Array.from({ length: H }, () => [0, 0, 0, 0, 0, 0, 0, 0]));
  for (const [t, atk, dfd, tiles, burnt, dB, , rings] of R.pairLog) {
    if (dfd >= H) continue;
    const k = wOf(t);
    if (k < 0) continue;
    let o;
    if (atk >= H) o = 0;
    else if (leftT[atk] >= 0 && leftT[atk] < t - 30) o = 4;
    else continue;
    const r = loss[k][dfd];
    r[o] += tiles; r[o + 1] += burnt; r[o + 2] += dB; r[o + 3] += rings;
  }
  // 每一口的战果：这一对的战损账里，落在 (这次出手, 下一次出手 或 +150 拍] 的那些行
  const byPair = new Map();
  for (const b of bites) {
    const key = b[1] * 1024 + b[3];
    if (!byPair.has(key)) byPair.set(key, []);
    byPair.get(key).push(b);
  }
  for (const [t, atk, dfd, tiles, burnt, dB, , rings] of R.pairLog) {
    const list = byPair.get(atk * 1024 + dfd);
    if (!list) continue;
    // pairLog 的 t 是 30 拍窗的窗末；出手拍落在 (t − 30, t] 里的那一口也算
    let hit = null;
    for (const b of list) { if (b[0] <= t && t - 30 < b[0] + 150) hit = b; else if (b[0] > t) break; }
    if (!hit) continue;
    const r = hit[12];
    r[0] += tiles; r[1] += burnt; r[2] += dB; r[3] += rings;
  }
  const out = {
    matchId: mid, until, H, endTick: R.endTick, validate: { rows: R.validate.rows, bothExact: R.validate.bothExact },
    leftT: Array.from(leftT), deathT: R.deathT, win: WIN, cp, dec, bites, loss,
  };
  fs.writeFileSync(path.join(outDir, `${mid}.json`), JSON.stringify(out));
  did++;
  console.log(`${mid}: 到 ${R.endTick} 拍，咬真人 ${bites.length} 次，${((Date.now() - t0) / 1000).toFixed(1)} 秒`);
}
const left = ids.length - did;
console.log(`aibite: 本轮 ${did} 局${left > 0 ? `，还剩 ${left} 局，再跑一次` : '，全部做完'}`);
