#!/usr/bin/env node
// xtruth.mjs — 发现集录像的开局段真值压缩表（默认到 t=1800），给 xtruth.py 做跨局统计用。
//
//   bash c136-review/tools/run-heavy.sh node c136-review/agents/R08/scripts/xtruth.mjs <局1> <局2> … [--until 1800] [--out-dir <目录>]
//
// 做法：直接调 resim_r08.mjs 的 resim()（真引擎逐拍重演，和各局 truth 用的是同一份），只留跨局统计要的东西：
//   · 每个真人席位：名字、队、出生点（最后一条落地的选点；一条都没落地的号看 startBox——开局那一拍它那块地的外接框）、
//     出生期落地的选点条数、离开拍 / 出局拍
//   · 检查点（300 / 600 / 630 / 900 / 1260 / 1500 / 1800）每个真人的地和兵，内置 AI 的地合计
//   · 分窗（0~600、600~900、900~1260、1260~1500、1500~1800）每个真人从内置 AI / 无主地 / 真人手里拿到的格数和烧掉的兵
//   · 分段（0~600、600~1500、1500~1800）每个真人落地的陆攻条数、其中生效的条数、目标是 512 的条数；船、捐款条数；
//     生效的陆攻按目标分三类（内置 AI / 无主地 / 真人）的条数、派出的兵、派出占发令前余额的比例
//   · 和日志的核对（traj.csv 的快照逐条对地 / 兵）：对得上才说明这份录像就是这个包的主房间
//   · 接壤普查（600~1500，每 30 拍一个样本，全部在线真人都查——不跑任何策略，只看引擎状态）：
//       这个号的陆上边界挨着谁：能打的内置 AI / 无主地 / 只剩真人；
//       挨着的 AI 里最便宜的那个，按策略自己的 elimCost 公式（2·B·(1−x^1.6) + 2·T·(1−x)，x = ⌊峰值/4⌋ ÷ T）
//       推到出局线要多少兵，占这个号当时余额的几成（≤10% 记「白给」，≤25% 记「买得起」）；
//       之后 90 拍里这个号有没有一条生效的陆攻落在内置 AI 身上。
//     按席位、按窗（600~900、900~1260、1260~1500）累计。
//   · 买 AI 地规则的原料（同一批样本里挨着内置 AI 的那些；仍然不跑策略，只把引擎状态里规则要用的量记下来，规则本身在 xtruth.py 里照抄）：
//       sb = safeFinite（c110 L2532-2541 / threatOf L464）：我挨着的每个 AI（含离开者的空壳；有空槽、没在打我、不挨着它没在吃的无主地），
//            取「它别的邻居里最弱的那个的余额（加上那个邻居压在它身上的兵）」，再在这些 AI 里取最大；并记下这个「最弱的别的邻居」是谁（sbSrc）；
//       persons = 挨着的敌方真人（没离开的）[号, 余额 + 压在我身上的兵]，从大到小最多 6 个（dpKeep L2491-2496 的原料；谁算「受保护的队友」由 xtruth.py 按名字判）；
//       ais = 挨着的内置 AI [号, botPx×100, price×100, 打垮它还差多少兵 need, 我压在它身上的兵, 它压在我身上的兵, 接触格数, 它的地, 它的余额]，按 need 从小到大最多 6 个；
//       slotFree / active = 我还有没有空的进攻槽、正在打的非无主地目标数（pickTarget L1185-1192 的原料）。
//     每个样本一行 locks：[t, 席位, 白给, 买得起, 90 拍内出手, 余额, 地, sb, sbSrc, slotFree, active, persons, ais]。
// 每局一个文件，默认写到 out/_run/xtruth/（不进 git；几秒一局，随时能重出）。只读 bundles/（发现集）。
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
const until = +take('until', 1800);
const outDir = path.resolve(take('out-dir', path.join(HERE, '..', 'out', '_run', 'xtruth')));
const { resim } = await import(path.join(HERE, 'resim_r08.mjs'));
fs.mkdirSync(outDir, { recursive: true });

const CP = [300, 600, 630, 900, 1260, 1500, 1800];
const RW = [600, 900, 1260, 1500];
const iV = (a, b) => Math.trunc(a / b);

const WIN = [0, 600, 900, 1260, 1500, 1800];
const PER = [0, 600, 1500, 1800];
const NEUTRAL = 512;   // 和引擎的 NEUTRAL 一致（无主地）

for (const mid of argv) {
  const t0 = Date.now();
  let R;
  const lockRows = [];
  const samples = [];   // [t, 席位, 有 AI 邻居, 有无主地邻居, 最便宜 AI 的代价 ÷ 余额（×1000，封顶 60000）, 挨着的 AI 地合计, 买得起的 AI 地合计, 余额, 地]
  const onTick = (g, ctx) => {
    const t = g.t;
    if (t < RW[0] || t > RW[RW.length - 1] || t % 30 !== 0) return;
    for (let p = 0; p < ctx.H; p++) {
      if (!g.alive[p] || g.state[p] === 2 || g.terr[p] <= 0) continue;
      const m = ctx.contact(p);
      let hasAi = 0, best = Infinity, aiLand = 0, cheapLand = 0;
      const bal = Math.max(1, g.bal[p]);
      for (const [q] of m) {
        if (q === NEUTRAL || q < ctx.H) continue;
        if (!(g.teams[p] === 0 || g.teams[p] !== g.teams[q])) continue;
        hasAi = 1;
        const T = g.terr[q], B = g.bal[q];
        const x = Math.min(1, iV(g.peak[q], 4) / Math.max(T, 1));
        const cost = 2 * B * (1 - Math.pow(x, 1.6)) + 2 * T * (1 - x);
        aiLand += T;
        if (cost <= 0.25 * bal) cheapLand += T;
        if (cost < best) best = cost;
      }
      samples.push([t, p, hasAi, m.has(NEUTRAL) ? 1 : 0, hasAi ? Math.min(60000, Math.round((1000 * best) / bal)) : -1, aiLand, cheapLand, g.bal[p], g.terr[p]]);
      if (!hasAi) continue;
      // 买 AI 地规则的原料
      let sb = 0, sbSrc = -1;
      const persons = [], ais = [];
      for (const [q, cnt] of m) {
        if (q === NEUTRAL || !g.alive[q] || !g.isEnemyOf(p, q) || g.terr[q] <= 0) continue;
        if (g.isBot(q)) {
          if (q >= ctx.H) {
            const T = g.terr[q], B = g.bal[q];
            const x = Math.min(1, iV(g.peak[q], 4) / Math.max(T, 1));
            const cost = 2 * B * (1 - Math.pow(x, 1.6)) + 2 * T * (1 - x);
            const mine = g.attackTroopsOn(p, q), theirs = g.attackTroopsOn(q, p);
            ais.push([q, Math.round(100 * (2 + (1.78 * B) / Math.max(1, T))), Math.round(100 * (2 + (2 * B) / (1 + iV(10 * T, 16)))), Math.round(cost + theirs - mine), mine, theirs, cnt, T, B]);
          }
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
      persons.sort((a, b) => b[1] - a[1]);
      ais.sort((a, b) => a[3] - b[3]);
      let active = 0;
      const base = g.slotBase(p);
      for (let i = g.atkCount[p] - 1; i >= 0; i--) if (g.atkTarget[base + i] !== NEUTRAL) active++;
      const rr = Math.min(60000, Math.round((1000 * best) / bal));
      lockRows.push([t, p, rr <= 100 ? 1 : 0, rr <= 250 ? 1 : 0, 0, g.bal[p], g.terr[p], Math.round(sb), sbSrc, g.hasFreeSlot(p) ? 1 : 0, active, persons.slice(0, 6), ais.slice(0, 6)]);
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
  const cp = {};
  for (const t of CP) {
    const i = R.snapT.indexOf(t);
    if (i < 0) continue;
    cp[t] = { terr: R.snapTerr[i].slice(0, H), bal: R.snapBal[i].slice(0, H) };
  }
  const aiAt = {};
  for (const [t, ai] of R.snapAi || []) if (CP.includes(t)) aiAt[t] = ai;
  // 分窗战果：[窗序号][真人] = [从 AI 拿的格, 烧的兵, 从无主地拿的格, 烧的兵, 从真人拿的格, 烧的兵, 被真人拿走的格]
  const nW = WIN.length - 1;
  const gain = Array.from({ length: nW }, () => Array.from({ length: H }, () => [0, 0, 0, 0, 0, 0, 0]));
  const wOf = (t) => { for (let k = 0; k < nW; k++) if (t > WIN[k] && t <= WIN[k + 1]) return k; return -1; };
  for (const [t, atk, dfd, tiles, burnt] of R.pairLog) {
    const k = wOf(t);
    if (k < 0) continue;
    if (atk < H) {
      const g = gain[k][atk];
      if (dfd === NEUTRAL) { g[2] += tiles; g[3] += burnt; } else if (dfd >= H) { g[0] += tiles; g[1] += burnt; } else { g[4] += tiles; g[5] += burnt; }
    }
    if (dfd < H && atk < H) gain[k][dfd][6] += tiles;
  }
  // 分段指令：[段][真人] = [陆攻落地, 生效, 目标 512, 船, 捐款, 捐款生效]
  const nP = PER.length - 1;
  const cmds = Array.from({ length: nP }, () => Array.from({ length: H }, () => [0, 0, 0, 0, 0, 0]));
  // 生效的陆攻按目标分三类（内置 AI / 无主地 / 真人）：[段][真人] = 每类 [条数, 派出的兵, Σ 派出 ÷ 发令前余额]
  const size = Array.from({ length: nP }, () => Array.from({ length: H }, () => [0, 0, 0, 0, 0, 0, 0, 0, 0]));
  const pOf = (t) => { for (let k = 0; k < nP; k++) if (t >= PER[k] && t < PER[k + 1]) return k; return t === PER[nP] ? nP - 1 : -1; };
  for (const c of R.cmdLog) {
    const [t, p, kind, , dZ, ok] = c;
    if (p >= H) continue;
    const k = pOf(t);
    if (k < 0) continue;
    const row = cmds[k][p];
    if (kind === 1) { row[0]++; if (ok) row[1]++; if (dZ === NEUTRAL) row[2]++; } else if (kind === 3) row[3]++; else if (kind === 2) { row[4]++; if (ok) row[5]++; }
    if (kind === 1 && ok) {
      const o = dZ === NEUTRAL ? 3 : dZ >= H ? 0 : 6;
      const sz = size[k][p];
      sz[o]++; sz[o + 1] += c[6]; sz[o + 2] += c[6] / Math.max(1, c[8]);
    }
  }
  // 逐对账（600~1500）：每个 [真人 p → 内置 AI q] 一行
  //   [p, q, 生效条数, 派出的兵, 第一条落地拍, 最后一条落地拍, 从它身上吃到的格, 烧掉的兵, 第一条落地前 AI 的地, AI 的余额, AI 到那时的最大地（30 拍快照）, AI 没地的那一拍（30 拍快照；-1 = 到重演末还在）]
  //   战果从第一条落地那一拍算到 1800 拍（进攻会拖过窗末）。
  const pairMap = new Map();
  for (const c of R.cmdLog) {
    const [t, p, kind, , dZ, ok, troops] = c;
    if (kind !== 1 || !ok || p >= H || dZ < H || dZ === NEUTRAL || t < 600 || t >= 1500) continue;
    const key = p * 1024 + dZ;
    let e = pairMap.get(key);
    if (!e) { e = [p, dZ, 0, 0, t, t, 0, 0, 0, 0, 0, -1]; pairMap.set(key, e); }
    e[2]++; e[3] += troops; e[5] = t;
  }
  for (const [t, atk, dfd, tiles, burnt] of R.pairLog) {
    if (atk >= H || dfd < H || dfd === NEUTRAL) continue;
    const e = pairMap.get(atk * 1024 + dfd);
    if (!e || t < e[4]) continue;
    e[6] += tiles; e[7] += burnt;
  }
  if (pairMap.size) {
    const snaps = (R.snapAi || []).map(([t, ai]) => [t, new Map(ai.map((a) => [a[0], a]))]);
    const peakTo = new Map();   // q → 逐快照的最大地
    for (const e of pairMap.values()) {
      const q = e[1];
      let peak = 0, T0 = 0, B0 = 0, gone = -1;
      for (const [t, mp] of snaps) {
        const a = mp.get(q);
        if (t <= e[4]) {
          if (a) { if (a[1] > peak) peak = a[1]; T0 = a[1]; B0 = a[2]; }
        } else if (gone < 0 && (!a || a[1] <= 0)) { gone = t; break; }
      }
      e[8] = T0; e[9] = B0; e[10] = peak; e[11] = gone;
    }
  }
  const pairs = [...pairMap.values()];
  // 接壤普查 → 按席位、按窗累计
  const hits = Array.from({ length: H }, () => []);
  for (const c of R.cmdLog) if (c[2] === 1 && c[5] && c[1] < H && c[4] >= H && c[4] !== NEUTRAL) hits[c[1]].push(c[0]);
  const nR = RW.length - 1;
  // [样本, 有 AI 邻居, 有无主地邻居, 只剩真人, 白给, 白给且 90 拍内出手, 买得起, 买得起且 90 拍内出手, 有 AI 邻居且 90 拍内出手, 挨着的 AI 地合计, 买得起的 AI 地合计]
  const reach = Array.from({ length: nR }, () => Array.from({ length: H }, () => [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]));
  for (const [t, p, hasAi, hasN, ratio, aiLand, cheapLand] of samples) {
    let k = -1;
    for (let i = 0; i < nR; i++) if (t >= RW[i] && (t < RW[i + 1] || (i === nR - 1 && t === RW[i + 1]))) { k = i; break; }
    if (k < 0 || t + 90 > R.endTick) continue;
    const row = reach[k][p];
    const hit = hits[p].some((x) => x > t && x <= t + 90) ? 1 : 0;
    row[0]++;
    if (hasAi) { row[1]++; row[8] += hit; }
    if (hasN) row[2]++;
    if (!hasAi && !hasN) row[3]++;
    if (hasAi && ratio <= 100) { row[4]++; row[5] += hit; }
    if (hasAi && ratio <= 250) { row[6]++; row[7] += hit; }
    row[9] += aiLand; row[10] += cheapLand;
  }
  for (const row of lockRows) {
    const t = row[0], p = row[1];
    row[4] = hits[p].some((x) => x > t && x <= t + 90) ? 1 : 0;
  }
  const locks = lockRows.filter((row) => row[0] + 90 <= R.endTick);
  const v = R.validate || {};
  const out = {
    matchId: mid, until, H, players: R.players, land: R.land, W: R.W, Hh: R.Hh, gameMode: R.gameMode, nTeamsHeader: R.nTeamsHeader, nTeams: R.nTeams,
    botsTeamed: R.botsTeamed, endTick: R.endTick, over: R.over,
    names: R.names, teams: R.teams, spawnXY: R.spawnXY, nPicks: (R.spawnSeq || []).map((s) => s.length), lastPick: (R.spawnSeq || []).map((s) => (s.length ? s[s.length - 1].slice(1) : null)),
    startBox: R.startBox, leftT: R.leftT, deathT: R.deathT,
    squad: R.squad, validate: { rows: v.rows, terrExact: v.terrExact, balExact: v.balExact, bothExact: v.bothExact },
    cp, aiAt, win: WIN, gain, per: PER, cmds, size, reachWin: RW, reach, locks, pairs, 
  };
  fs.writeFileSync(path.join(outDir, `${mid}.json`), JSON.stringify(out));
  console.log(`${mid}: H=${H} 到 t=${R.endTick} 核对 ${v.bothExact}/${v.rows} 行 ${((Date.now() - t0) / 1000).toFixed(1)}s`);
}
