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
//   · 分段（0~600、600~1500、1500~1800）每个真人落地的陆攻条数、其中生效的条数、目标是 512 的条数；船、捐款条数
//   · 和日志的核对（traj.csv 的快照逐条对地 / 兵）：对得上才说明这份录像就是这个包的主房间
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
const WIN = [0, 600, 900, 1260, 1500, 1800];
const PER = [0, 600, 1500, 1800];
const NEUTRAL = 512;

for (const mid of argv) {
  const t0 = Date.now();
  let R;
  try {
    R = resim(mid, { until });
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
  const pOf = (t) => { for (let k = 0; k < nP; k++) if (t >= PER[k] && t < PER[k + 1]) return k; return t === PER[nP] ? nP - 1 : -1; };
  for (const c of R.cmdLog) {
    const [t, p, kind, , dZ, ok] = c;
    if (p >= H) continue;
    const k = pOf(t);
    if (k < 0) continue;
    const row = cmds[k][p];
    if (kind === 1) { row[0]++; if (ok) row[1]++; if (dZ === NEUTRAL) row[2]++; } else if (kind === 3) row[3]++; else if (kind === 2) { row[4]++; if (ok) row[5]++; }
  }
  const v = R.validate || {};
  const out = {
    matchId: mid, until, H, players: R.players, land: R.land, W: R.W, Hh: R.Hh, gameMode: R.gameMode, nTeamsHeader: R.nTeamsHeader, nTeams: R.nTeams,
    botsTeamed: R.botsTeamed, endTick: R.endTick, over: R.over,
    names: R.names, teams: R.teams, spawnXY: R.spawnXY, nPicks: (R.spawnSeq || []).map((s) => s.length), lastPick: (R.spawnSeq || []).map((s) => (s.length ? s[s.length - 1].slice(1) : null)),
    startBox: R.startBox, leftT: R.leftT, deathT: R.deathT,
    squad: R.squad, validate: { rows: v.rows, terrExact: v.terrExact, balExact: v.balExact, bothExact: v.bothExact },
    cp, aiAt, win: WIN, gain, per: PER, cmds,
  };
  fs.writeFileSync(path.join(outDir, `${mid}.json`), JSON.stringify(out));
  console.log(`${mid}: H=${H} 到 t=${R.endTick} 核对 ${v.bothExact}/${v.rows} 行 ${((Date.now() - t0) / 1000).toFixed(1)}s`);
}
