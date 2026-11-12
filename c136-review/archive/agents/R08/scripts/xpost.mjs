#!/usr/bin/env node
// xpost.mjs — 1500 拍以后「挨着的内置 AI / 空壳的地」普查（真值重演到 3000 拍）。只读发现集录像，不跑策略。
//
// 用法（必须套 run-heavy.sh；一批 4~6 局）：
//   bash c136-review/tools/run-heavy.sh node c136-review/agents/R08/scripts/xpost.mjs <局> <局> … [--until 3000] [--out-dir DIR]
// 输出：out/_run/xpost/<局>.json（中间产物，不进 git）；汇总由 xpost.py 做 → out/_cross/xpost.txt / xpost.json
//
// 每局记：
//   cp       1500 / 1800 / 2400 / 3000 拍每个真人席位的地、兵
//   aiAt     这几拍内置 AI 的 [席位, 地, 兵]
//   gain     分窗战果 (1500,1800] (1800,2400] (2400,3000]：[窗][真人] = [从内置 AI 吃的格, 烧的兵, 从无主地吃的格, 烧的兵, 从在线真人吃的格, 烧的兵, 被真人吃走的格, 从空壳吃的格, 烧的兵]
//            空壳 = 已经离开的真人席位（引擎接管，策略里算「非真人」目标）
//   reach    接壤普查（每 30 拍一个样本）：[窗][真人] = [样本, 挨着内置 AI, 挨着空壳, 挨着无主地, 挨着的内置 AI 地合计, 挨着内置 AI 且 90 拍内有生效陆攻落在内置 AI 上, 挨着内置 AI 的样本里能看满 90 拍的]
//   rows     挨着内置 AI / 空壳的样本的规则原料（给 xpost.py 照抄 1500 拍后的买地规则用）：
//            [t, 席位, 兵, 地, sb, sb 来源席位, 有空槽, 在打的非无主地目标数, 最强的 6 个真人邻居 [[席位, 兵 + 压在我身上的兵]…],
//             非真人邻居（还要兵的排前、按打垮价从低到高，最多 10 个）[[席位, 地, 兵, ⌊峰值/4⌋, 接触格数, 它的边界格数, 我压在它身上的兵, 它压在我身上的兵, 我在打它, 它在打我, 是空壳]…],
//             90 拍内有生效陆攻落在内置 AI 上（-1 = 看不满 90 拍）, 90 拍内有生效陆攻落在空壳上, 90 拍内有生效陆攻落在在线真人上]
//   dens     2500 拍起每个样本拍全部在线真人（地 ≥100）的 [席位, 兵, 地]（给 marketFloor 那一项用）
//   size     生效的陆攻按目标分四类（内置 AI / 空壳 / 在线真人 / 无主地）：[窗][真人] = 每类 [条数, 派出的兵, Σ 派出 ÷ 发令前余额, Σ 手续费, 派出的兵不到 4 倍手续费的条数]
//   cmds     落地的陆攻：[窗][真人] = [落地, 生效, 目标 512]
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const argv = process.argv.slice(2);
const take = (k, d) => {
  const i = argv.indexOf(`--${k}`);
  if (i < 0) return d;
  const v = argv[i + 1];
  argv.splice(i, 2);
  return v;
};
const until = +take('until', 3000);
const outDir = path.resolve(take('out-dir', path.join(HERE, '..', 'out', '_run', 'xpost')));
const { resim } = await import(path.join(HERE, 'resim_r08.mjs'));
fs.mkdirSync(outDir, { recursive: true });

const CP = [1500, 1800, 2400, 3000];
const WIN = [1500, 1800, 2400, 3000];
const NEUTRAL = 512;
const iV = (a, b) => Math.trunc(a / b);

for (const mid of argv) {
  const t0 = Date.now();
  let R;
  const rows = [];
  const cens = [];   // [t, 席位, 挨着内置 AI, 挨着空壳, 挨着无主地, 挨着的内置 AI 地合计]
  const dens = [];
  const onTick = (g, ctx) => {
    const t = g.t;
    if (t <= WIN[0] || t > WIN[WIN.length - 1] || t % 30 !== 0) return;
    const H = ctx.H;
    const dl = [];
    for (let p = 0; p < H; p++) if (g.alive[p] && g.state[p] !== 2 && g.terr[p] >= 100) dl.push([p, g.bal[p], g.terr[p]]);
    if (t >= 2500) dens.push([t, dl]);
    for (let p = 0; p < H; p++) {
      if (!g.alive[p] || g.state[p] === 2 || g.terr[p] <= 0) continue;
      const m = ctx.contact(p);
      let hasAi = 0, hasShell = 0, aiLand = 0;
      let sb = 0, sbSrc = -1;
      const persons = [], npc = [];
      for (const [q, cnt] of m) {
        if (q === NEUTRAL || !g.alive[q] || g.terr[q] <= 0) continue;
        if (!g.isEnemyOf(p, q)) continue;
        if (g.isBot(q)) {
          const T = g.terr[q], B = g.bal[q];
          const left = iV(g.peak[q], 4);
          const x = Math.min(1, left / Math.max(T, 1));
          const cost = 2 * B * (1 - Math.pow(x, 1.6)) + 2 * T * (1 - x);
          const mine = g.attackTroopsOn(p, q), theirs = g.attackTroopsOn(q, p);
          const shell = q < H ? 1 : 0;
          if (shell) hasShell = 1; else { hasAi = 1; aiLand += T; }
          npc.push([q, T, B, left, cnt, g.border[q].length, mine, theirs, g.hasAttack(p, q) ? 1 : 0, g.hasAttack(q, p) ? 1 : 0, shell, cost + theirs - mine]);
          // safeFinite / threatOf（和 xtruth.mjs 同一写法）
          if (!g.hasFreeSlot(q) || g.hasAttack(q, p)) continue;
          const mq = ctx.contact(q);
          if (mq.has(NEUTRAL) && !g.hasAttack(q, NEUTRAL)) continue;
          let minOther = Infinity, src = -1;
          for (const [o] of mq) {
            if (o === NEUTRAL || o === p || o === q || g.hasAttack(q, o)) continue;
            const sv = g.bal[o] + g.attackTroopsOn(o, q);
            if (sv < minOther) { minOther = sv; src = o; }
          }
          if (!Number.isFinite(minOther)) continue;
          const safe = minOther - g.attackTroopsOn(p, q);
          if (safe > sb) { sb = safe; sbSrc = src; }
        } else {
          persons.push([q, g.bal[q] + g.attackTroopsOn(q, p)]);
        }
      }
      cens.push([t, p, hasAi, hasShell, m.has(NEUTRAL) ? 1 : 0, aiLand]);
      if (!npc.length) continue;
      persons.sort((a, b) => b[1] - a[1]);
      // 还要兵的（打垮价 > 0）排前面、从便宜到贵；已经压够兵的排后面
      npc.sort((a, b) => (a[11] > 0 ? 0 : 1) - (b[11] > 0 ? 0 : 1) || a[11] - b[11]);
      let active = 0;
      const base = g.slotBase(p);
      for (let i = g.atkCount[p] - 1; i >= 0; i--) if (g.atkTarget[base + i] !== NEUTRAL) active++;
      rows.push([t, p, g.bal[p], g.terr[p], Math.round(sb), sbSrc, g.hasFreeSlot(p) ? 1 : 0, active, persons.slice(0, 6),
        npc.slice(0, 10).map((a) => a.slice(0, 11)), -1, -1, -1]);
    }
  };
  try {
    R = resim(mid, { until, onTick });
  } catch (e) {
    fs.writeFileSync(path.join(outDir, `${mid}.json`), JSON.stringify({ matchId: mid, error: String(e && e.message || e) }));
    console.log(`${mid}: 失败 ${String(e && e.message || e).slice(0, 120)}`);
    continue;
  }
  const H = R.H;
  const leftT = R.leftT;
  const isShellAt = (q, t) => q < H && leftT[q] >= 0 && t > leftT[q];
  const cp = {};
  for (const t of CP) {
    const i = R.snapT.indexOf(t);
    if (i < 0) continue;
    cp[t] = { terr: R.snapTerr[i].slice(0, H), bal: R.snapBal[i].slice(0, H) };
  }
  const aiAt = {};
  for (const [t, ai] of R.snapAi || []) if (CP.includes(t)) aiAt[t] = ai;
  const nW = WIN.length - 1;
  const gain = Array.from({ length: nW }, () => Array.from({ length: H }, () => [0, 0, 0, 0, 0, 0, 0, 0, 0]));
  const wOf = (t) => { for (let k = 0; k < nW; k++) if (t > WIN[k] && t <= WIN[k + 1]) return k; return -1; };
  for (const [t, atk, dfd, tiles, burnt] of R.pairLog) {
    const k = wOf(t);
    if (k < 0) continue;
    if (atk < H) {
      const g = gain[k][atk];
      if (dfd === NEUTRAL) { g[2] += tiles; g[3] += burnt; }
      else if (dfd >= H) { g[0] += tiles; g[1] += burnt; }
      else if (isShellAt(dfd, t)) { g[7] += tiles; g[8] += burnt; }
      else { g[4] += tiles; g[5] += burnt; }
    }
    if (dfd < H && atk < H && !isShellAt(dfd, t)) gain[k][dfd][6] += tiles;
  }
  // 生效的陆攻：按目标分 内置 AI / 空壳 / 在线真人 / 无主地；[窗][真人] = 每类 [条数, 派出的兵, Σ 派出 ÷ 发令前余额, Σ 手续费, 派出的兵不到 4 倍手续费的条数]
  const size = Array.from({ length: nW }, () => Array.from({ length: H }, () => new Array(20).fill(0)));
  // 落地的陆攻：[窗][真人] = [落地, 生效, 目标 512]
  const cmds = Array.from({ length: nW }, () => Array.from({ length: H }, () => [0, 0, 0]));
  const hitsAi = Array.from({ length: H }, () => []), hitsShell = Array.from({ length: H }, () => []), hitsHuman = Array.from({ length: H }, () => []);
  for (const c of R.cmdLog) {
    const [t, p, kind, , dZ, ok] = c;
    if (p >= H || kind !== 1) continue;
    const k = wOf(t);
    if (k >= 0) { const r = cmds[k][p]; r[0]++; if (ok) r[1]++; if (dZ === NEUTRAL) r[2]++; }
    if (!ok) continue;
    const cls = dZ === NEUTRAL ? 3 : dZ >= H ? 0 : isShellAt(dZ, t) ? 1 : 2;
    if (cls === 0) hitsAi[p].push(t); else if (cls === 1) hitsShell[p].push(t); else if (cls === 2) hitsHuman[p].push(t);
    if (k >= 0) {
      const sz = size[k][p], o = 5 * cls;
      sz[o]++; sz[o + 1] += c[6]; sz[o + 2] += c[6] / Math.max(1, c[8]); sz[o + 3] += c[7];
      if (c[6] < 4 * c[7]) sz[o + 4]++;
    }
  }
  const within = (arr, t) => (arr.some((x) => x > t && x <= t + 90) ? 1 : 0);
  const reach = Array.from({ length: nW }, () => Array.from({ length: H }, () => [0, 0, 0, 0, 0, 0, 0]));
  for (const [t, p, hasAi, hasShell, hasN, aiLand] of cens) {
    const k = wOf(t);
    if (k < 0) continue;
    const r = reach[k][p];
    r[0]++; r[1] += hasAi; r[2] += hasShell; r[3] += hasN; r[4] += aiLand;
    if (hasAi && t + 90 <= R.endTick) { r[6]++; r[5] += within(hitsAi[p], t); }
  }
  for (const row of rows) {
    const t = row[0], p = row[1];
    if (t + 90 > R.endTick) continue;
    row[10] = within(hitsAi[p], t); row[11] = within(hitsShell[p], t); row[12] = within(hitsHuman[p], t);
  }
  const v = R.validate || {};
  // 对不上的核对行的拍号（最多 400 条）：xpost.py 拿它判断重演到哪一窗开始跑偏
  const mismT = (v.mism || []).map((mm) => mm[0]);
  const out = {
    matchId: mid, until, H, players: R.players, land: R.land, gameMode: R.gameMode, nTeams: R.nTeams, botsTeamed: R.botsTeamed, endTick: R.endTick, over: R.over,
    names: R.names, teams: R.teams, spawnXY: R.spawnXY, startBox: R.startBox, leftT: R.leftT, deathT: R.deathT, squad: R.squad,
    validate: { rows: v.rows, terrExact: v.terrExact, balExact: v.balExact, bothExact: v.bothExact, mismT },
    cp, aiAt, win: WIN, gain, size, cmds, reach, rows, dens,
  };
  fs.writeFileSync(path.join(outDir, `${mid}.json`), JSON.stringify(out));
  console.log(`${mid}: H=${H} 到 t=${R.endTick} 核对 ${v.bothExact}/${v.rows} 行 样本 ${rows.length} ${((Date.now() - t0) / 1000).toFixed(1)}s`);
}
