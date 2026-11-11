// boattrack.mjs —— 真引擎重演里跟踪某个号的每条船：出发拍/兵、每 N 拍剩多少、被海战打掉多少、怎么消失（靠岸 / 兵耗尽 / 号死了）。
// 用法：node boattrack.mjs <matchId> --bot 名字 [--peer-tag TAG] [--replay-from M] [--t0 T] [--t1 T] [--every 60]
import { resim } from './resim_r08.mjs';

const args = process.argv.slice(2);
const mid = args[0];
const opt = (k, d) => (args.includes(`--${k}`) ? args[args.indexOf(`--${k}`) + 1] : d);
const botName = opt('bot', null);
if (!mid || !botName) { console.error('用法：node boattrack.mjs <matchId> --bot 名字 [--t0 T] [--t1 T] [--every 60]'); process.exit(2); }
const t0 = +opt('t0', 0), t1 = +opt('t1', 1e9), every = +opt('every', 60);
let me = -1, names = [];
const live = new Map(); // boat id -> {t0, v0, last, hitLoss, decayLoss, samples}
const done = [];
const out = resim(mid, {
  replayFrom: opt('replay-from', null), peer: opt('peer', null), peerTag: opt('peer-tag', null),
  onStart: (g, ctx) => { names = ctx.names; me = ctx.squad[botName] ? ctx.squad[botName].id : -1; },
  onTick: (g) => {
    if (me < 0 || g.t < t0 || g.t > t1) return;
    const seen = new Set();
    for (let b = 0; b < g.boatN; b++) {
      if ((g.bSlot[b] >> 3) !== me) continue;
      const id = g.bId ? g.bId[b] : (g.bSlot[b] << 20) + b;
      seen.add(id);
      const v = g.bTroops[b];
      let r = live.get(id);
      if (!r) { r = { id, t0: g.t, v0: v, last: v, hitLoss: 0, otherLoss: 0, by: {}, type: g.bType[b] % 64, samples: [] }; live.set(id, r); }
      if (v < r.last) {
        if (g.bHit[b] > 0) {
          r.hitLoss += r.last - v;
          // 谁的船在旁边：取距离最近的敌方船主（海战范围内）
          const S = g.sub, pb = g.bPos[b], x = pb % S, y = ~~((pb + 0.5) / S);
          let best = -1, bd = Infinity;
          for (let o = 0; o < g.boatN; o++) {
            const ow = g.bSlot[o] >> 3;
            if (o === b || !g.isEnemyOf(me, ow)) continue;
            const po = g.bPos[o], dx = x - (po % S), dy = y - ~~((po + 0.5) / S);
            const d2 = dx * dx + dy * dy;
            if (d2 < bd) { bd = d2; best = ow; }
          }
          if (best >= 0) r.by[best] = (r.by[best] || 0) + (r.last - v);
        } else r.otherLoss += r.last - v;
      }
      r.last = v; r.lastT = g.t;
      if ((g.t - r.t0) % every === 0) r.samples.push([g.t, v]);
    }
    for (const [id, r] of live) if (!seen.has(id)) { r.endT = g.t; r.ownerAlive = g.alive[me]; done.push(r); live.delete(id); }
  },
});
const land = (out.landings || []).filter((l) => l[1] === me);
console.log(`${mid} ${botName}(${me}) 的船（${done.length + live.size} 条）：出发拍 兵 | 消失拍 最后兵 | 海战被打掉 / 衰减等 | 靠岸记录 | 每 ${every} 拍剩余`);
for (const r of [...done, ...live.values()].sort((a, b) => a.t0 - b.t0)) {
  const l = land.find((x) => Math.abs(x[0] - (r.endT ?? -99)) <= 1 && Math.abs(x[3] - r.last) <= Math.max(2, r.last >> 6));
  const where = l ? `靠岸 t=${l[0]} 在 ${l[2] >= 512 ? '空地' : (l[2] < out.H ? names[l[2]] : 'AI' + l[2])} 兵 ${l[3]}${l[4] ? `（并入地主 ${l[4]}）` : ''}` : (r.endT === undefined ? '终局仍在海上' : (r.last === 0 ? '兵耗尽' : `没有靠岸记录（号还活着=${r.ownerAlive}）`));
  const by = Object.entries(r.by).sort((a, b) => b[1] - a[1]).slice(0, 3).map(([p, v]) => `${+p < out.H ? names[+p] : 'AI' + p}:${v}`).join(' ');
  console.log(`  ${r.t0} ${r.v0} | ${r.endT ?? '-'} ${r.last} | ${r.hitLoss}${by ? `（最近的敌船船主 ${by}）` : ''} / ${r.otherLoss} | ${where} | ${r.samples.map((s) => `${s[0]}:${s[1]}`).join(' ')}`);
}
