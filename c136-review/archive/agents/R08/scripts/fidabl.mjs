#!/usr/bin/env node
// fidabl.mjs — 重放器保真度消融：把重放器（resim_r08.mjs 的 TGame + assignTeams）比 src/sim 基类多出来的东西逐项关掉，
// 同一份录像再重演一遍，看
//   (a) 和日志快照（traj.csv）逐位一致的行还剩多少、第一处不一致在哪一拍；
//   (b) 开环下宏观量偏多少（内置 AI 占全图陆地的份额、还有地的 AI 个数、各席位的地和兵）。
// 只读 /agent/repos/c136-data（发现集的对局包 + src/sim）；不跑策略，不改任何指令。
//
//   bash c136-review/tools/run-heavy.sh node c136-review/agents/R08/scripts/fidabl.mjs [--until 1800] [--arms full,nocolor,…]
//        [--replay-from <局2>] [--tag 名字] <局> <局> …
//   → out/_run/fidabl/<局>[.<tag>].json（不入库）；汇总：python3 fidabl.py → out/_cross/fidabl.txt
//
// 臂（opts.fid 见 resim_r08.mjs 文件头第 (5) 条）：
//   full       原样（参照；应当和日志逐位一致）
//   nocolor    不做组队配色随机数（基类 setupColors）
//   aiteam     内置 AI 一律轮流入队（基类 setupTeams 的默认值；teamgate.mjs 就是这样建局的）
//   diff6      内置 AI 难度 6（线上录像头全是 0）
//   nocache    各队总地不按 32 拍缓存
//   noteamend  猎杀 / 终局提速退回基类写法
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { resim } from './resim_r08.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const RUN = path.join(HERE, '..', 'out', '_run', 'fidabl');
const ARMS = {
  full: null,
  nocolor: { colors: false },
  aiteam: { botTeams: 'always' },
  diff6: { difficulty: 6 },
  nocache: { cache32: false },
  noteamend: { teamEnd: false },
};
const CP = [300, 600, 630, 900, 1260, 1500, 1800, 3000, 4290, 6000];   // 快照每 10 拍一条、AI 名单每 30 拍一条；4284 取 4290

const argv = process.argv.slice(2);
const take = (k, d) => {
  const i = argv.indexOf(`--${k}`);
  if (i < 0) return d;
  const v = argv[i + 1];
  argv.splice(i, 2);
  return v;
};
const until = take('until', null);
const arms = take('arms', 'full,nocolor,aiteam,diff6').split(',');
const replayFrom = take('replay-from', null);
const tag = take('tag', null);
fs.mkdirSync(RUN, { recursive: true });

for (const mid of argv) {
  const file = path.join(RUN, `${mid}${tag ? `.${tag}` : ''}.json`);
  if (fs.existsSync(file)) {
    // 已经跑过同一组臂的局跳过（分批跑、中途被超时杀掉以后可以原样重跑）
    try {
      const old = JSON.parse(fs.readFileSync(file, 'utf8'));
      if (arms.every((a) => old.arms && old.arms[a]) && old.until === (until ? +until : null)) { console.log(`${mid}: 已有，跳过`); continue; }
    } catch (e) { /* 坏文件重跑 */ }
  }
  const out = { matchId: mid, until: until ? +until : null, replayFrom, arms: {} };
  const t0 = Date.now();
  for (const arm of arms) {
    if (!(arm in ARMS)) { console.error(`不认识的臂：${arm}`); process.exit(2); }
    let X;
    try {
      X = resim(mid, { until: until ? +until : undefined, fid: ARMS[arm] || undefined, replayFrom: replayFrom || undefined });
    } catch (e) {
      out.arms[arm] = { error: String(e.message || e).slice(0, 200) };
      continue;
    }
    if (!out.H) {
      Object.assign(out, { H: X.H, land: X.land, names: X.names, nTeams: X.nTeams, nTeamsHeader: X.nTeamsHeader, botsTeamed: X.botsTeamed,
        gameMode: X.gameMode, squad: Object.fromEntries(Object.entries(X.squad).map(([b, s]) => [b, s.id])), leftT: X.leftT });
    }
    const v = X.validate;
    const cp = {};
    for (const t of CP) {
      const i = X.snapT.indexOf(t);
      if (i < 0) continue;
      const ai = X.snapAi.find((r) => r[0] === t);
      cp[t] = { terr: X.snapTerr[i], bal: X.snapBal[i], botLand: X.botLand[i], aiN: ai ? ai[1].length : null };
    }
    const ev = X.engineEvents || [];
    const hunts = ev.filter((e) => e[1] === 'hunt'), fasts = ev.filter((e) => e[1] === 'fast');
    out.arms[arm] = {
      endTick: X.endTick, over: X.over, rows: v.rows, exact: v.bothExact, terrExact: v.terrExact, balExact: v.balExact,
      firstMism: v.mism.length ? v.mism[0][0] : null, mism: v.mism.slice(0, 6), lastMism: v.mism.length ? v.mism[v.mism.length - 1][0] : null,
      hunts: hunts.length, firstHunt: hunts.length ? hunts[0][0] : null, firstFast: fasts.length ? fasts[0][0] : null,
      cmdOk: X.cmdLog.filter((c) => c[2] === 1).reduce((s, c) => s + (c[5] ? 1 : 0), 0), cmdN: X.cmdLog.filter((c) => c[2] === 1).length,
      cp,
    };
  }
  fs.writeFileSync(file, JSON.stringify(out));
  console.log(`${mid}: ${arms.map((a) => { const r = out.arms[a]; return r.error ? `${a}=ERR` : `${a}=${r.exact}/${r.rows}${r.firstMism !== null ? `@${r.firstMism}` : ''}`; }).join(' ')} | ${((Date.now() - t0) / 1000).toFixed(1)}s`);
}
