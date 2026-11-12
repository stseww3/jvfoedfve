// verify.mjs — 物理底座自检：整段重放录像，与真引擎重放的指纹逐采样拍核对；分队、我方席位与入库名单核对；clone 分叉自检；计时。
import fs from 'node:fs';
import path from 'node:path';
import { loadMatch, buildWorld, ReplayStepper, SIMV2 } from './match.mjs';
import { TGame } from './tgame.mjs';
import { fnvU32, num } from './util.mjs';

export function runVerify(o) {
  const mid = o.match;
  if (!mid) throw new Error('verify 模式要 --match <局号>');
  const M = loadMatch(mid);
  const H = M.H;
  const packsFile = path.join(SIMV2, 'packs', 'index.json');
  const pk = fs.existsSync(packsFile) ? JSON.parse(fs.readFileSync(packsFile, 'utf8'))[mid] : null;
  const truthFile = path.join(SIMV2, 'truth', `${mid}.json`);
  const truth = fs.existsSync(truthFile) ? JSON.parse(fs.readFileSync(truthFile, 'utf8')) : null;
  const res = { match: mid, replay: M.replayMid, map: M.mapKey, humans: H, replayTicks: M.replayTicks };

  // 分队 / 我方席位 对 入库名单
  if (M.ta) {
    res.nTeams = M.ta.nTeams; res.botsTeamed = M.ta.botsTeamed;
    if (pk) {
      let bad = 0;
      for (let p = 0; p < H; p++) if (M.ta.fX[p] !== pk.teams[p]) bad++;
      res.teamsVsEngine = { same: H - bad, of: H, nTeamsOk: pk.nTeams === M.ta.nTeams, botTeamsOk: pk.botTeams === M.ta.botsTeamed };
    }
  }
  const logSeats = [...new Set(M.log.seatOf.values())].filter((p) => p < H).sort((a, b) => a - b);
  res.squad = M.squad.length;
  res.squadTeams = [...new Set(M.squad.map((p) => (M.ta ? M.ta.fX[p] : 0)))];
  if (pk) {
    const a = new Set(pk.squad), b = new Set(logSeats);
    res.squadLogVsPack = { pack: a.size, log: b.size, onlyPack: [...a].filter((p) => !b.has(p)), onlyLog: [...b].filter((p) => !a.has(p)) };
  }

  const g = buildWorld(M);
  const st = new ReplayStepper(M, g);
  st.runSpawnPhase();
  const to = num(o.to, Infinity);
  const cloneAt = num(o['clone-at'], Math.min(1200, Math.max(0, M.replayTicks - 400)));
  const cloneLen = num(o['clone-len'], 300);
  const tIdx = new Map();
  if (truth) truth.ticks.forEach((t, i) => tIdx.set(t, i));
  let lastOk = -1, firstBad = -1, nCmp = 0;
  const vals = new Array(2 * H);
  const t0 = Date.now();
  const cpu0 = process.cpuUsage();
  let cloneRes = null;
  let tickMs = 0;
  while (!g.over && g.t < to) {
    const i = tIdx.get(g.t);
    if (i !== undefined && firstBad < 0) {
      for (let p = 0; p < H; p++) {
        const tt = g.alive[p] ? g.terr[p] : 0;
        vals[2 * p] = tt;
        vals[2 * p + 1] = tt > 0 ? g.bal[p] : 0;
      }
      nCmp++;
      if (fnvU32(vals) === truth.hash[i]) lastOk = g.t; else firstBad = g.t;
    }
    if (g.t === cloneAt && !cloneRes) {
      const c0 = Date.now();
      const g2 = g.clone();
      const cloneMs = Date.now() - c0;
      const st2 = st.fork(g2);
      const sA = st.state();
      // 第三份：从同一个分叉点再走一遍，核对「同一局面 + 同一串指令」两次结果逐拍相同
      const g3 = g.clone();
      const st3 = st.fork(g3);
      let same = 0, n = 0, bad = -1;
      for (let k = 0; k < cloneLen && !g2.over; k++) {
        if (!st2.step()) break;
        g2.tick();
        if (!st3.step()) break;
        g3.tick();
        n++;
        if (g2.fingerprint() === g3.fingerprint()) same++; else if (bad < 0) bad = g2.t;
      }
      cloneRes = { at: cloneAt, len: n, cloneMs, proto: g2 instanceof TGame && g2.landAt === TGame.prototype.landAt, twinSame: same, twinFirstBad: bad, fpEnd: g2.fingerprint(), g2 };
      st.restore(sA);
    }
    if (!st.step()) break;
    g.tick();
    if (cloneRes && cloneRes.g2 && g.t === cloneRes.g2.t) {
      // 原局面继续走到分叉副本停下的那一拍：指纹应与副本相同（clone 没漏字段、没共享可变状态）
      cloneRes.origSame = g.fingerprint() === cloneRes.fpEnd;
      delete cloneRes.g2;
    }
  }
  tickMs = Date.now() - t0;
  const cpu = process.cpuUsage(cpu0);
  const cpuMs = Math.round((cpu.user + cpu.system) / 1000);
  if (cloneRes) delete cloneRes.g2;
  res.endT = g.t; res.over = !!g.over;
  res.truth = truth ? { samples: nCmp, lastOkT: lastOk, firstBadT: firstBad, truthEndT: truth.endT } : null;
  res.clone = cloneRes;
  res.oddLandings = g.oddLandings; res.oddLandingTroops = g.oddLandingTroops;
  res.ms = tickMs; res.cpuMs = cpuMs; res.cpuMsPer1000 = Math.round(1000 * cpuMs / Math.max(1, g.t));
  res.heapMB = Math.round(process.memoryUsage().heapUsed / 1048576);
  const tv = res.teamsVsEngine;
  console.log(`[verify] ${mid}（录像 ${M.replayMid}，地图 ${M.mapKey}，真人 ${H}，录像 ${M.replayTicks} 拍）`);
  if (M.ta) console.log(`  分队：${M.ta.nTeams} 队，内置 AI ${M.ta.botsTeamed ? '分队' : '不分队'}` + (tv ? `；与真引擎重放的队号 ${tv.same}/${tv.of} 相同，队数 ${tv.nTeamsOk ? '相同' : '不同'}，AI 分队 ${tv.botTeamsOk ? '相同' : '不同'}` : ''));
  console.log(`  我方席位 ${M.squad.length} 个（所在队 ${res.squadTeams.join('/')}）` + (res.squadLogVsPack ? `；日志 [HL-GAME-INIT] 认出 ${res.squadLogVsPack.log} 个，名单独有 ${JSON.stringify(res.squadLogVsPack.onlyPack)}，日志独有 ${JSON.stringify(res.squadLogVsPack.onlyLog)}` : ''));
  if (truth) console.log(`  与真引擎重放核对（全体真人的 领土、兵力，每 30 拍）：${nCmp} 个采样拍，一致到 t=${lastOk}` + (firstBad >= 0 ? `，第一处不同 t=${firstBad}` : '，没有不同'));
  else console.log('  没有这局的真引擎指纹（sim-v2/truth/），只跑了重放');
  if (cloneRes) console.log(`  clone 自检 @t=${cloneRes.at}：保留 TGame 原型 ${cloneRes.proto ? '是' : '否'}；两份副本各走 ${cloneRes.len} 拍逐拍指纹相同 ${cloneRes.twinSame}/${cloneRes.len}；原局面走到同一拍与副本 ${cloneRes.origSame ? '相同' : '不同'}；clone 一次 ${cloneRes.cloneMs} ms`);
  console.log(`  船落在水 / 边界 / 山格 ${g.oddLandings} 次（${g.oddLandingTroops} 兵）；走到 t=${g.t}${g.over ? '（分出胜负）' : ''}；墙钟 ${tickMs} ms、CPU ${cpuMs} ms（每 1000 拍 CPU ${res.cpuMsPer1000} ms）；堆 ${res.heapMB} MB`);
  return res;
}
