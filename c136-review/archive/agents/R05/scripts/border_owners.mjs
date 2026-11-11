// border_owners.mjs — 某号在指定拍的「边界邻居构成」：边界外侧相邻格分别属于谁（敌方真人 / 队友（含已离线）/ AI 机器人 / 中立 / 水）。
// 用途：判断一个号是不是被队友的地（特别是已离线队友的地）围死、还剩多少对敌接触面。
// 用法：node border_owners.mjs <matchId> --bots talon5,sora_w --at 3000,3300,3600
// 数据来自逐拍精确重放（sim_replay.mjs），只读。
import { simulate, P_INNER, NEUTRAL } from './sim_replay.mjs';
import { squadIds } from './match_truth.mjs';
const { T_LAND } = await import('file:///agent/repos/c136-data/src/sim/sim/map.js');

const args = process.argv.slice(2);
const mid = args[0];
const opt = (k, d) => { const i = args.indexOf(k); return i >= 0 ? args[i + 1] : d; };
const want = (opt('--bots', '') || '').split(',').filter(Boolean);
const at = new Set((opt('--at', '') || '').split(',').filter(Boolean).map(Number));
const maxT = Math.max(...at) + 1;
let R = null;
await simulate(mid, {
  maxTick: maxT,
  onStart(g, info) {
    R = info;
    R.sq = [...squadIds(mid, info.names, info.H).squad.entries()].map(([p, bot]) => ({ p, bot })).filter((s) => !want.length || want.includes(s.bot));
  },
  onTick(g, t) {
    if (!at.has(t)) return;
    for (const s of R.sq) {
      const me = s.p;
      if (!g.alive[me]) { console.log(`t=${t} ${s.bot} 已阵亡`); continue; }
      const cnt = new Map();
      let water = 0, total = 0;
      const B = g.border[me], px = g.px, own = g.own, d = g.dir4;
      for (let i = 0; i < B.length; i++) {
        const b = B[i];
        for (let k = 0; k < 4; k++) {
          const c = b + d[k];
          if (px[c] < P_INNER) {
            if (px[c] === T_LAND) { total++; cnt.set(NEUTRAL, (cnt.get(NEUTRAL) || 0) + 1); } else water++;
            continue;
          }
          const o = own[c];
          if (o === me) continue;
          total++;
          cnt.set(o, (cnt.get(o) || 0) + 1);
        }
      }
      const cls = { 敌方真人: 0, 在线队友: 0, 已离线队友: 0, 机器人: 0, 中立: 0 };
      const det = [];
      for (const [o, n] of [...cnt.entries()].sort((a, b) => b[1] - a[1])) {
        let k;
        if (o === NEUTRAL || o < 0 || o >= g.players) k = '中立';
        else if (o >= R.H) k = '机器人';
        else if (g.teams[o] === g.teams[me]) k = g.state[o] === 2 ? '已离线队友' : '在线队友';
        else k = '敌方真人';
        cls[k] += n;
        if (k !== '中立' && det.length < 8) det.push(`${(R.names[o] || '#' + o).slice(0, 14)}#${o}[${k}${k === '敌方真人' ? ' T' + g.teams[o] : ''}] ${n}`);
      }
      console.log(`t=${t} ${s.bot} 地 ${g.terr[me]} 兵 ${g.bal[me]}｜陆上相邻格 ${total}（水 ${water}）：` +
        Object.entries(cls).map(([k, v]) => `${k} ${v}(${(100 * v / Math.max(1, total)).toFixed(0)}%)`).join(' ') + `｜${det.join('；')}`);
    }
  },
});
