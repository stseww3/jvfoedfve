#!/usr/bin/env node
// atkfate.mjs — 每一路陆上进攻「结束时退回多少兵」的底账（真引擎重演，只读；包一层 endAttack 钩子）。
//
//   bash c136-review/tools/run-heavy.sh node c136-review/agents/R08/scripts/atkfate.mjs <局>
//        [--replay-from <局2>] [--peer <局2> | --peer-tag <标签>] [--until T]
// 输出：out/<局>/atkfate.json：
//   ends = [结束拍, 进攻方, 目标（512 = 无主地）, 兵, 目标当时还活着吗(0/1), 目标当时的格数, 这一路开始的拍, 这一路期间拿到的格数, 期间烧掉的兵, 类别]
//     类别 0 = endAttack：这一路结束，「兵」= 退回余额的兵（目标不接壤了 / 没有无主地了 / 推不动了）；
//     类别 1 = redirectAttackToNeutral：目标出局，压在它身上还没用掉的「兵」原样转成一路打无主地的进攻（引擎 game.js L856-869）。
//   只记进攻方是真人的。lagledger.py 把它和 resim.json 的指令账（每条陆攻实际派出的兵）合起来算「派出去的兵有多少没用上」。
// 口径：一路进攻 = 同一个进攻方对同一个目标、从第一次推进到结束 / 转向之间；中途追加的兵算在同一路里。
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const OUT = path.join(HERE, '..', 'out');
const NEUTRAL = 512;
const args = process.argv.slice(2);
const mid = args[0];
if (!mid) { console.error('用法见文件头'); process.exit(2); }
const opt = (k, d) => (args.includes(`--${k}`) ? args[args.indexOf(`--${k}`) + 1] : d);
const { resim } = await import(path.join(HERE, 'resim_r08.mjs'));

const ends = [];
const open = new Map();   // p*1024+target -> [startTick, terr0 累计拿到的格, burnt]
let H = 0;
const t0 = Date.now();
const R = resim(mid, {
  until: opt('until', null) ? +opt('until') : undefined, quiet: true,
  replayFrom: opt('replay-from', null), peer: opt('peer', null), peerTag: opt('peer-tag', null),
  onStart: (g, ctx) => {
    H = ctx.H;
    const prevEnd = g.endAttack, prevExp = g.expandAttack;
    g.expandAttack = function (p, a) {
      if (p >= H) return prevExp.call(this, p, a);
      const target = this.atkTarget[this.slotBase(p) + a];
      const key = p * 1024 + target;
      let e = open.get(key);
      if (!e) { e = [this.t, 0, 0]; open.set(key, e); }
      const own0 = this.totalAttackTroops(p) + this.bal[p], terr0 = this.terr[p];
      const r = prevExp.call(this, p, a);
      e[1] += this.terr[p] - terr0;
      e[2] += own0 - (this.totalAttackTroops(p) + this.bal[p]);
      return r;
    };
    const prevRed = g.redirectAttackToNeutral;
    g.redirectAttackToNeutral = function (p, target) {
      if (p >= H) return prevRed.call(this, p, target);
      const v = this.attackTroopsOn(p, target);
      const had = this.hasAttack(p, target);
      const r = prevRed.call(this, p, target);
      if (had) {
        const key = p * 1024 + target;
        const e = open.get(key) || [this.t, 0, 0];
        open.delete(key);
        ends.push([this.t, p, target, v, 0, this.terr[target], e[0], e[1], e[2], 1]);
      }
      return r;
    };
    g.endAttack = function (p, a, troops) {
      if (p >= H) return prevEnd.call(this, p, a, troops);
      const target = this.atkTarget[this.slotBase(p) + a];
      const b0 = this.bal[p];
      const r = prevEnd.call(this, p, a, troops);
      const key = p * 1024 + target;
      const e = open.get(key) || [this.t, 0, 0];
      open.delete(key);
      ends.push([this.t, p, target, this.bal[p] - b0, target < NEUTRAL ? (this.alive[target] ? 1 : 0) : 1, target < NEUTRAL ? this.terr[target] : -1, e[0], e[1], e[2], 0]);
      return r;
    };
  },
});
fs.mkdirSync(path.join(OUT, mid), { recursive: true });
fs.writeFileSync(path.join(OUT, mid, 'atkfate.json'), JSON.stringify({ matchId: mid, replayFrom: opt('replay-from', null) || mid, endTick: R.endTick, H, ends }));
console.log(`${mid}: atkfate.json 写出｜真人的进攻结束 ${ends.filter((e) => e[9] === 0).length} 路，退回余额合计 ${ends.filter((e) => e[9] === 0).reduce((s, e) => s + e[3], 0)} 兵；目标出局转打无主地 ${ends.filter((e) => e[9] === 1).length} 路 ${ends.filter((e) => e[9] === 1).reduce((s, e) => s + e[3], 0)} 兵｜重演到 t=${R.endTick}｜${((Date.now() - t0) / 1000).toFixed(1)}s`);
