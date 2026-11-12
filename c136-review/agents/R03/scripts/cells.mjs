#!/usr/bin/env node
// cells.mjs — 每个真人的「名下」格数（出生份额的逐人版本）。口径与 land-ledger.mjs 的 [G1] 完全相同：
// 选点期结束那一拍，每个真人的出生点 = 它那块地的质心；全图每一格陆地归直线距离最近的真人出生点。
// 只把录像放到第 1 拍，不做整局重放。
//
//   bash c136-review/tools/run-heavy.sh node scripts/cells.mjs A051 A087 …
//   写 out/council/cells/<局>.json：{ land, W, H, pts: [{ id, x, y, team, cells, squad, nearest }] }
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { resim } from './resim.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const OUT = path.join(HERE, '..', 'out', 'council', 'cells');
const P_INNER = 16, T_LAND = 1;
fs.mkdirSync(OUT, { recursive: true });

for (const mid of process.argv.slice(2)) {
  let done = null;
  resim(mid, {
    until: 1,
    onState: (g, ctx) => {
      if (done || g.spawnPhase) return;
      const H = ctx.H, W = g.W, N = g.px.length;
      const sq = new Set(Object.values(ctx.squad).map((s) => s.id).filter((x) => x >= 0));
      const sx = new Float64Array(512), sy = new Float64Array(512), sn = new Int32Array(512);
      const land = new Uint8Array(N);
      let total = 0;
      for (let c = 0; c < N; c++) {
        const v = g.px[c];
        if (v === T_LAND || v >= P_INNER) { land[c] = 1; total++; }
        if (v >= P_INNER) { const o = g.own[c]; sx[o] += c % W; sy[o] += Math.floor(c / W); sn[o]++; }
      }
      const pts = [];
      for (let p = 0; p < H; p++) if (sn[p] > 0) pts.push({ id: p, x: sx[p] / sn[p], y: sy[p] / sn[p], team: ctx.teamGame ? g.teams[p] : 0, cells: 0, squad: sq.has(p) ? 1 : 0 });
      const idx = new Map(pts.map((p, i) => [p.id, i]));
      for (let c = 0; c < N; c++) {
        if (!land[c]) continue;
        const x = c % W, y = Math.floor(c / W);
        let best = -1, bd = Infinity;
        for (const p of pts) {
          const d = (p.x - x) * (p.x - x) + (p.y - y) * (p.y - y);
          if (d < bd) { bd = d; best = p.id; }
        }
        pts[idx.get(best)].cells++;
      }
      for (const p of pts) {
        let bd = Infinity;
        for (const q of pts) if (q.id !== p.id) bd = Math.min(bd, Math.hypot(q.x - p.x, q.y - p.y));
        p.nearest = Math.round(bd);
        p.x = Math.round(p.x); p.y = Math.round(p.y);
      }
      done = { matchId: mid, land: total, W, H: Math.round(N / W), humans: pts.length, pts };
    },
  });
  fs.writeFileSync(path.join(OUT, `${mid}.json`), JSON.stringify(done));
  const s = done.pts.filter((p) => p.squad).reduce((a, p) => a + p.cells, 0);
  console.log(`${mid} 陆地 ${done.land} 真人 ${done.humans} 编队名下合计 ${s}`);
}
