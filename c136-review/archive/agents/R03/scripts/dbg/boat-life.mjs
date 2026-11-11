// 调试：跟一条船从出港到消失的全过程（真值重演，不跑影子策略）。
// 用法：node dbg/boat-life.mjs <mid> <玩家席位,逗号分隔> [t0] [t1]
// 每条船打印：出港拍、船型（bType%64：0~3 定向、4 找空地/敌岸、5 回自家岸、6 追船）、出港兵、航线段数与像素长度、
//   每 100 拍的兵数与位置、被敌船打到（bHit>0）的拍数、消失拍与消失前一拍的兵数、消失那一拍有没有靠岸记录。
// 引擎口径：boats.js boatsTick L204~217（每拍 landBoats→moveBoats；奇数拍 fightBoats；t%5==3 decayBoats 掉 v>>7；兵数归零即移除）。
import { resim } from '../resim.mjs';

const [mid, plist, t0s, t1s] = process.argv.slice(2);
const want = new Set(String(plist).split(',').map(Number));
const t0 = +(t0s ?? 0), t1 = +(t1s ?? 1e9);
const live = new Map();
const done = [];
let R = null;
const routeLen = (g, rb) => {
  let s = 0;
  for (let k = 0; k + 1 < rb.length; k++) {
    const a = rb[k], e = rb[k + 1];
    const ax = a % g.W, ay = Math.floor(a / g.W), ex = e % g.W, ey = Math.floor(e / g.W);
    s += Math.hypot(ex - ax, ey - ay);
  }
  return Math.round(s);
};
R = resim(mid, {
  until: t1 + 1,
  onState: (g) => {
    const seen = new Set();
    for (let b = 0; b < g.boatN; b++) {
      const p = g.bSlot[b] >> 3;
      if (!want.has(p)) continue;
      const id = g.bId[b];
      const key = p + ':' + id;
      seen.add(key);
      let r = live.get(key);
      const at = g.subToPixel(g.bPos[b]);
      const xy = [at % g.W, Math.floor(at / g.W)];
      if (!r) {
        const rb = g.bRoute[b];
        r = { p, id, t0: g.t, type: g.bType[b] % 64, troops0: g.bTroops[b], legs: rb.length - 1, len: routeLen(g, rb), from: xy, to: [rb[rb.length - 1] % g.W, Math.floor(rb[rb.length - 1] / g.W)], hitTicks: 0, firstHit: -1, samples: [], minStep: null };
        live.set(key, r);
      }
      if (g.bHit[b] > 0) {
        r.hitTicks++;
        if (r.firstHit < 0) r.firstHit = g.t;
        // 附近 40 像素内的敌方船（谁在打它）：记 船主 → 出现过的最大船上兵数
        for (let o = 0; o < g.boatN; o++) {
          const q = g.bSlot[o] >> 3;
          if (!g.isEnemyOf(p, q)) continue;
          const ao = g.subToPixel(g.bPos[o]);
          const dx = (ao % g.W) - xy[0], dy = Math.floor(ao / g.W) - xy[1];
          if (dx * dx + dy * dy > 1600) continue;
          const m = (r.foes ||= {});
          m[q] = Math.max(m[q] || 0, g.bTroops[o]);
        }
      }
      if (r.last && r.lastTroops - g.bTroops[b] > Math.max(1, r.lastTroops >> 7) + 1) (r.bigLoss ||= []).push([g.t, r.lastTroops, g.bTroops[b]]);
      r.last = g.t; r.lastTroops = g.bTroops[b]; r.lastXY = xy; r.lastLeg = g.bLeg[b]; r.lastProg = g.bProg[b];
      if (g.t % 100 === 0) r.samples.push([g.t, g.bTroops[b], xy[0], xy[1], g.bLeg[b]]);
    }
    for (const [key, r] of live) {
      if (seen.has(key)) continue;
      r.goneT = g.t;
      done.push(r);
      live.delete(key);
    }
  },
});
for (const r of live.values()) { r.goneT = null; done.push(r); }
const names = R.names;
const nm = (q) => (q === 512 ? '中立' : q < 0 ? '无' : `${(names[q] || '?').slice(0, 12)}#${q}`);
done.sort((a, b) => a.t0 - b.t0);
for (const r of done) {
  if (r.t0 < t0) continue;
  const land = R.landings.filter((l) => l[1] === r.p && r.goneT != null && Math.abs(l[0] - r.goneT) <= 1);
  console.log(`${nm(r.p)} 船 id=${r.id} 型 ${r.type} | 出港 ${r.t0} 兵 ${r.troops0} 从 (${r.from}) 到 (${r.to}) 航线 ${r.legs} 段 ${r.len} 像素 | 消失 ${r.goneT ?? '未消失'} 在海上 ${r.goneT != null ? r.goneT - r.t0 : '-'} 拍 末兵 ${r.lastTroops} 末位置 (${r.lastXY}) 段 ${r.lastLeg}/${r.legs}`);
  console.log(`    被敌船打到的拍数 ${r.hitTicks}（首次 ${r.firstHit}）| 一拍内掉兵超过衰减的次数 ${(r.bigLoss || []).length}${r.bigLoss ? '：' + r.bigLoss.slice(0, 6).map((x) => `${x[0]}拍 ${x[1]}→${x[2]}`).join('，') : ''}`);
  if (r.foes) console.log(`    被打时 40 像素内的敌船：${Object.entries(r.foes).map(([q, v]) => `${nm(+q)}（船上最多 ${v}）`).join('，')}`);
  console.log(`    靠岸记录：${land.length ? land.map((l) => `${l[0]}拍 落在 ${nm(l[2])} 的地上，船上 ${l[3]}，对方到账 ${l[4]}`).join('；') : '无（没有调用 landAt）'}`);
  console.log(`    每 100 拍：${r.samples.map((s) => `${s[0]}:${s[1]}@(${s[2]},${s[3]})段${s[4]}`).join(' ')}`);
}
