// 调试：任意席位（含内置 AI 的席位号 ≥ 真人数）的 地 / 余额 / 密度 / 在外进攻兵 / 被压的进攻兵 / 海上船数，按固定步长打印（真值重演）。
// 用法：node dbg/player-track.mjs <mid> <席位,逗号分隔> <t0> <t1> [步长=100]
// 重放快照（resim.json 的 snapTerr/snapBal）只存真人席位；要看某个内置 AI（例如收官阶段剩下的最后一个）得用这个。
import { resim } from '../resim.mjs';

const [mid, plist, t0s, t1s, steps] = process.argv.slice(2);
const want = String(plist).split(',').map(Number);
const t0 = +t0s, t1 = +t1s, step = +(steps ?? 100);
const k = (x) => (Math.abs(x) >= 1e6 ? (x / 1e6).toFixed(2) + 'M' : Math.abs(x) >= 1e4 ? Math.round(x / 1e3) + 'k' : Math.abs(x) >= 1e3 ? (x / 1e3).toFixed(1) + 'k' : String(Math.round(x)));
const rows = [];
const died = new Map();
const R = resim(mid, {
  until: t1 + 1,
  quiet: true,
  onState: (g, ctx) => {
    for (const p of want) if (!died.has(p) && g.t > 0 && g.alive[p] === 0) died.set(p, g.t);
    if (g.t < t0 || g.t > t1 || (g.t - t0) % step) return;
    const cells = [];
    for (const p of want) {
      if (!g.alive[p]) { cells.push(`#${p} 已灭`); continue; }
      let onMe = 0;
      const who = [];
      for (const a of g.attackersOf(p)) { const v = g.attackTroopsOn(a, p); onMe += v; who.push(`${a}:${k(v)}`); }
      const L = g.terr[p], B = g.bal[p];
      cells.push(`#${p} 地 ${L} 兵 ${k(B)} 密 ${(B / Math.max(1, L)).toFixed(1)} 在外 ${k(g.totalAttackTroops(p))} 被压 ${k(onMe)}${who.length ? '[' + who.slice(0, 4).join(' ') + ']' : ''} 船 ${g.boatCount[p]}`);
    }
    rows.push(`t=${g.t} | ${cells.join(' | ')}`);
  },
});
for (const r of rows) console.log(r);
for (const [p, t] of died) console.log(`#${p} 灭亡拍 ${t}`);
