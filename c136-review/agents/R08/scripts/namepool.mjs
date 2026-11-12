#!/usr/bin/env node
// namepool.mjs — 「名字池误认」的真相口径原料：整局重演一遍，把和「谁打了谁、谁挨着谁、谁给谁捐」有关的账压成小文件，
// 分类（我方 / 名字在池里的外人 / 同队 / 跨队 / 空壳 / 野人）留给 namepool.py 做。
// 只读 /agent/repos/c136-data（发现集）；不跑策略，不改任何指令。
//
//   bash c136-review/tools/run-heavy.sh node c136-review/agents/R08/scripts/namepool.mjs <局> <局> …
//   → out/_run/namepool/<局>.json（不入库）；汇总：python3 namepool.py → out/_cross/namepool.txt
//
// 录像取自哪一份包：out/_run/room_pairs.json（roompairs.py 写）里列了的局，用同房另一份包更长的录像，本包的号按名字认；
//   [--own-recording] 强制用自己的。已有输出用的录像和现在该用的不是同一份，就重跑。
//
// 每局写出：
//   names / teams / leftT / deathT / squad（我方号 → 席位）/ H / land / endTick / nTeams / gameMode
//   replayFrom（录像取自哪一份包；自己的就是 null）/ mismT（重演和本包日志第一次对不上的那一拍；全对得上是 null）
//   snapT / terr：每 90 拍全部真人席位的地
//   flows：[窗(300 拍一窗的起点), 进攻方, 被打方, 进攻方吃到的格, 进攻方烧掉的兵, 被打方掉的余额]，只留「至少一方是真人席位」的对
//   nb：我方每个号每 90 拍贴着谁（接触格数最多的 12 个；512 = 无主地）
//   atk：我方号的陆攻指令按 (窗, 发的人, 目标) 合计 [条数, 成功条数, 出兵]
//   dons：全部真人的捐款指令 [t, 捐的人, 收的人, 成功, 到账, 损耗, 捐前余额]
//   husk：空壳 / 内置 AI 的赠兵 [t, 给方, 收方, 给方余额前, 收方到账]
//   boats：真人席位的发船指令 [t, 发的人, 发船那一拍目的地那一格是谁的(512 = 无主地), 成功, 上船的兵]
//   lands：真人席位的船靠岸 [t, 船主, 靠岸那一格是谁的(512 = 无主地；-1 = 不是能占的格), 兵, 对方到账(靠在队友地上时)]
//   deaths：真人席位出局 [t, 席位, 类别, 出局前的地, 账上的兵, 峰值, 状态(0 在线 / 2 空壳), 自己在途的兵, 正在打它的人数, 压在它身上的兵, 压得最多的那个, 海上的船数]
// 同一趟重演顺手把 deaths 另存一份到 out/_run/deathbank/<局>.json（deathbank.py 用）。
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { resim } from './resim_r08.mjs';
import { deathRows, writeDeathbank, recordingOf, sameRecording } from './deathbank.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const RUN = path.join(HERE, '..', 'out', '_run', 'namepool');
fs.mkdirSync(RUN, { recursive: true });
const BIN = 300;
const ARGV = process.argv.slice(2);
const FORCE = ARGV.includes('--force');
// 录像取自哪一份包：out/_run/room_pairs.json（roompairs.py 写）里列了的局用同房另一份包更长的录像；--own-recording 强制用自己的
const OWN_REC = ARGV.includes('--own-recording');
// --budget <秒>：开跑下一局之前看一眼已经用掉的时间，超了就停，剩下的下一批接着跑
const BI = ARGV.indexOf('--budget');
const BUDGET = BI >= 0 ? +ARGV.splice(BI, 2)[1] : Infinity;
const T_START = Date.now();
const hasDeaths = (file) => { try { return Array.isArray(JSON.parse(fs.readFileSync(file, 'utf8')).deaths); } catch { return false; } };

for (const mid of ARGV.filter((a) => !a.startsWith('--'))) {
  const file = path.join(RUN, `${mid}.json`);
  const src = recordingOf(mid, OWN_REC);
  // 旧版输出（没有 deaths / boats / lands）会重跑；用的录像和现在该用的不是同一份，也重跑
  if (fs.existsSync(file) && !FORCE && hasDeaths(file) && sameRecording(file, src)) { console.log(`${mid}: 已有，跳过`); continue; }
  if ((Date.now() - T_START) / 1000 > BUDGET) { console.log(`${mid}: 这一批的时间预算用完，留给下一批`); break; }
  const t0 = Date.now();
  let X;
  try { X = resim(mid, { replayFrom: src || undefined }); } catch (e) { console.log(`${mid}: 重演失败：${String(e.message || e).slice(0, 160)}`); continue; }
  const H = X.H;
  const snapT = [], terr = [];
  for (let i = 0; i < X.snapT.length; i++) if (X.snapT[i] % 90 === 0) { snapT.push(X.snapT[i]); terr.push(X.snapTerr[i]); }
  const fl = new Map();
  for (const [t, p, q, tiles, burnt, dB] of X.pairLog) {
    if (p >= H && q >= H) continue;
    if (!tiles && !burnt && !dB) continue;
    const bin = Math.floor((t - 1) / BIN) * BIN;
    const key = `${bin},${p},${q}`;
    let r = fl.get(key);
    if (!r) { r = [0, 0, 0]; fl.set(key, r); }
    r[0] += tiles; r[1] += burnt; r[2] += dB;
  }
  const flows = [...fl].map(([k, r]) => [...k.split(',').map(Number), ...r]);
  const nb = {};
  for (const [b, s] of Object.entries(X.sq)) nb[X.squad[b].id] = s.nb.filter((r) => r[0] % 90 === 0).map(([t, list]) => [t, list.map(([q, n]) => [q, n])]);
  const own = new Set(Object.values(X.squad).map((s) => s.id).filter((x) => x >= 0));
  const at = new Map();
  const dons = [];
  const boats = [];
  for (const c of X.cmdLog) {
    const [t, p, k] = c;
    if (k === 1 && p < H) {
      // 全部真人席位的陆攻都留（分类在 namepool.py 里做：包里有日志的我方号不止 X.squad 认出来的那些）
      const q = Math.min(c[4], 512);
      const key = `${Math.floor(t / BIN) * BIN},${p},${q}`;
      let r = at.get(key);
      if (!r) { r = [0, 0, 0]; at.set(key, r); }
      r[0]++; r[1] += c[5]; r[2] += c[6];
    } else if (k === 2) {
      dons.push([t, p, Math.min(c[4], 512), c[5], c[6], c[7], c[8]]);
    } else if (k === 3 && p < H) {
      boats.push([t, p, c[10], c[5], c[6]]);
    }
  }
  const atk = [...at].map(([k, r]) => [...k.split(',').map(Number), ...r]);
  const husk = X.huskGifts.map((g) => [g[0], g[1], g[2], g[4], g[6] - g[5]]);
  const lands = X.landings.filter((r) => r[1] < H).map((r) => [r[0], r[1], r[2], r[3], r[4]]);
  const deaths = deathRows(X);
  writeDeathbank(mid, X, deaths, src);
  const out = {
    matchId: mid, H, land: X.land, endTick: X.endTick, over: X.over, winnerTeam: X.winnerTeam, gameMode: X.gameMode, nTeams: X.nTeams, botsTeamed: X.botsTeamed,
    names: X.names.slice(0, H), teams: Array.from(X.teams).slice(0, H), leftT: X.leftT, deathT: X.deathT,
    squad: Object.fromEntries(Object.entries(X.squad).map(([b, s]) => [b, s.id])),
    exact: [X.validate.bothExact, X.validate.rows],
    replayFrom: src || null, mismT: X.validate.mism.length ? X.validate.mism[0][0] : null,
    snapT, terr, flows, nb, atk, dons, husk, boats, lands, deaths,
  };
  fs.writeFileSync(file, JSON.stringify(out));
  console.log(`${mid}: H=${H} 到 ${X.endTick} 拍${src ? `（录像取自 ${src}）` : ''}，日志 ${X.validate.bothExact}/${X.validate.rows}，流水 ${flows.length} 行，捐款 ${dons.length} 条 | ${((Date.now() - t0) / 1000).toFixed(1)}s`);
}
