#!/usr/bin/env node
// 105_human_fill.mjs — R07：每个真人席位的天然地盘和各拍实际领土（给断面归因的「出生站位」一层定基准用；纯离线，只读录像）。
//
// 做法：干净模拟器按录像重演到 1500 拍（不跑任何策略，不改局面）。出生阶段结束那一拍，取每个有地的真人位的落点
// （领土包围盒中心，和 46_voronoi.mjs 同口径），把全图陆地格按直线距离分给最近的真人位 → 每个真人的天然地盘格数；
// 另记这个天然地盘里开局时内置 AI 占了多少格。然后记每个真人在 300 / 630 / 900 / 1200 / 1500 拍的领土和是否还在。
// 输出：out/_cache/fill/<局>.json（不进 git）；汇总由 106_spawn_par.py 做。
// --late：重演到 5184 拍（或终局），另记 1800 / 2100 / 2400 / 3300 / 4284 / 5184 拍，输出到 out/_cache/fill_late/<局>.json
//        （给 1500 拍以后的断面窗口定站位基准用；原来的 fill/ 不动）。
// 用法（必须套重计算闸；可以一次给多局，已有输出的跳过）：
//   bash c136-review/tools/run-heavy.sh node c136-review/agents/R07/scripts/105_human_fill.mjs A007 A033 …
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const DATA = '/agent/repos/c136-data';
const HERE = path.dirname(fileURLToPath(import.meta.url));
const mids = process.argv.slice(2).filter((a) => !a.startsWith('--'));
if (!mids.length) { console.error('用法：105_human_fill.mjs <局> [<局> …]'); process.exit(2); }
const LATE = process.argv.includes('--late');
const OUTDIR = path.join(HERE, '..', 'out', '_cache', LATE ? 'fill_late' : 'fill');
fs.mkdirSync(OUTDIR, { recursive: true });
const SIM = await import(path.join(DATA, 'src/sim/sim/index.js'));
(await import(path.join(HERE, 'r07simfix.mjs'))).applyOddLandingFix(SIM);
const { resim } = await import(path.join(DATA, 'src/tools/resim.mjs'));
const LIB = await import(path.join(DATA, 'src/sim/tools/c102-replay-lib.mjs'));
const { T_LAND, P_INNER } = SIM;
const SQUAD = ['sora_w', 'ryan_m', 'noah88', 'zexos1', 'talon5', 'alex_k', 'leo_tx', 'zero_7', 'kaito9', 'riku_x'];
const AT = LATE ? [300, 630, 900, 1200, 1500, 1800, 2100, 2400, 3300, 4284, 5184] : [300, 630, 900, 1200, 1500];
const UNTIL = LATE ? 5184 : 1500;
const deadline = +(process.env.CP_DEADLINE_MS || Infinity);

for (const mid of mids) {
  const outPath = path.join(OUTDIR, `${mid}.json`);
  if (fs.existsSync(outPath) && fs.statSync(outPath).size > 0) continue;
  if (Date.now() + (LATE ? 45000 : 25000) > deadline) { console.log(`LATER ${mid}`); continue; }
  const d = LIB.decodeReplay(fs.readFileSync(path.join(DATA, 'bundles', mid, 'replay.txt'), 'utf8'));
  const H = d.vu.humanCount;
  const names = d.vu.playerNamesData ? Array.from(d.vu.playerNamesData).slice(0, H).map((s) => String(s ?? '').trim()) : [];
  const squadOf = (p) => { const n = (names[p] || '').toLowerCase(); for (const s of SQUAD) if (n.endsWith(s)) return s; return null; };
  let sites = null, land = 0;
  const proto = SIM.Game.prototype;
  const origTick = proto.tick;
  proto.tick = function () {
    origTick.call(this);
    const g = this;
    if (g.spawnPhase) return;
    if (sites === null) {
      const W = g.W, px = g.px, own = g.own;
      sites = [];
      for (let p = 0; p < H; p++) {
        if (g.terr[p] <= 0) continue;
        sites.push({ p, bot: squadOf(p), team: g.teams ? g.teams[p] : 0, x: (g.x0[p] + g.x1[p] + 1) / 2, y: (g.y0[p] + g.y1[p] + 1) / 2, vor: 0, aiIn: 0, terr0: g.terr[p], at: {} });
      }
      const n = sites.length;
      const sx = Float64Array.from(sites.map((s) => s.x)), sy = Float64Array.from(sites.map((s) => s.y));
      for (let c = 0; c < px.length; c++) {
        if (!(px[c] === T_LAND || px[c] >= P_INNER)) continue;
        land++;
        const x = (c % W) + 0.5, y = ((c / W) | 0) + 0.5;
        let best = -1, bd = Infinity;
        for (let k = 0; k < n; k++) { const dx = x - sx[k], dy = y - sy[k]; const dd = dx * dx + dy * dy; if (dd < bd) { bd = dd; best = k; } }
        sites[best].vor++;
        if (px[c] >= P_INNER && own[c] >= H) sites[best].aiIn++;
      }
      // 最近的别的真人落点、最近的敌方真人落点的距离
      for (const s of sites) {
        let dn = Infinity, de = Infinity;
        for (const o of sites) {
          if (o === s) continue;
          const dd = Math.hypot(o.x - s.x, o.y - s.y);
          if (dd < dn) dn = dd;
          if ((s.team === 0 || o.team !== s.team) && dd < de) de = dd;
        }
        s.nearest = Math.round(dn); s.nearestEnemy = Number.isFinite(de) ? Math.round(de) : -1;
      }
    }
    if (AT.includes(g.t)) for (const s of sites) s.at[g.t] = { terr: g.alive[s.p] ? g.terr[s.p] : 0, bal: g.alive[s.p] ? g.bal[s.p] : 0, st: !g.alive[s.p] ? 0 : g.state[s.p] === 2 ? 2 : 1 };
  };
  let out;
  try { out = resim(mid, { until: UNTIL }); } finally { proto.tick = origTick; }
  fs.writeFileSync(outPath, JSON.stringify({ mid, H, land, teamSizes: out.teamSizes, until: UNTIL, endTick: out.endTick ?? null, sites }));
  console.log(`${mid} 真人 ${sites.length} 位（我方 ${sites.filter((s) => s.bot).length}），陆地 ${land} 格，traj 核对 ${out.validate.bothExact}/${out.validate.rows}`);
}
