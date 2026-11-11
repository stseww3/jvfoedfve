// 调试：某个号余额在一拍内跳涨时，是引擎的哪条路径加的兵（真值重演）。
// 用法：node dbg/bal-jump.mjs <mid> <席位> <t0> <t1> [最小增量=100000]
// 给 g.addBalance 包一层：在 [t0,t1] 内对该席位每次加兵 ≥ 最小增量 的调用打印拍号、请求量、实际加上的量和调用栈前 4 层
// （economyTick = 利息/地租，endAttack/cancelAttack = 进攻队列退兵，landAt = 船靠岸，donate = 捐款到账）。
import { resim } from '../resim.mjs';

const [mid, ps, t0s, t1s, mins] = process.argv.slice(2);
const p0 = +ps, t0 = +t0s, t1 = +t1s, minV = +(mins ?? 100000);
let hooked = false;
resim(mid, {
  until: t1 + 1,
  onState: (g) => {
    if (hooked) return;
    hooked = true;
    const orig = g.addBalance;
    g.addBalance = function (p, v) {
      const b0 = this.bal[p];
      const r = orig.call(this, p, v);
      if (p === p0 && this.t >= t0 && this.t <= t1 && this.bal[p] - b0 >= minV) {
        const st = new Error().stack.split('\n').slice(2, 6).map((s) => s.trim().replace(/\(file:\/\/.*\/([^/]+:\d+):\d+\)/, '($1)')).join(' < ');
        console.log(`t=${this.t} 请求 +${v} 实加 +${this.bal[p] - b0}（${b0} → ${this.bal[p]}，地 ${this.terr[p]}，硬上限 ${150 * this.terr[p]}）| ${st}`);
      }
      return r;
    };
  },
});
