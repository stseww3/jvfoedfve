// replay_decode.mjs — 只解码录像指令流（不做模拟、不需要地图）：
//   node replay_decode.mjs <matchId> [--json out.json]
// 输出：录像头（人数/队数/玩家名）、每条指令的拍号（按 jY/ja 逐拍结构还原）、指令类型统计。
// 指令 id：0 选点 1 陆攻(pct,target) 2 捐款(pct,target) 3 发船 4 追船/召回 5 撤回 7 ? 8/9 离开 10 ?
import fs from 'node:fs';
import { decodeReplay } from '/agent/repos/c136-data/src/sim/tools/c102-replay-lib.mjs';

export function loadReplay(matchId) {
  const p = `/agent/repos/c136-data/bundles/${matchId}/replay.txt`;
  const raw = fs.readFileSync(p, 'utf8');
  const d = decodeReplay(raw);
  // 还原每条指令所在的“录像步”。jY[i]=1: 本步有 ja[i] 条指令；jY[i]=0: 连续 ja[i] 个空步。
  const H = d.vu.humanCount;
  const jJ = H <= 2 ? 30 : H <= 50 ? 40 : 50; // 选点阶段步数（见 c102-replay-lib makeStepper.runSpawnPhase）
  const out = [];
  let step = 0, iw = 0;
  for (let iv = 0; iv < d.ja.length; iv++) {
    const n = d.ja[iv];
    if (d.jY[iv]) {
      for (let a = iw; a < iw + n; a++) out.push({ step, ...d.cmds[a] });
      iw += n;
      step += 1;
    } else {
      step += n;
    }
  }
  return { d, H, jJ, cmds: out, steps: step };
}

if (process.argv[1] && process.argv[1].endsWith('replay_decode.mjs')) {
  const mid = process.argv[2];
  const { d, H, jJ, cmds, steps } = loadReplay(mid);
  const vu = d.vu;
  const brief = { ...vu };
  for (const k of Object.keys(brief)) if (brief[k] && typeof brief[k] === 'object' && brief[k].length > 12) brief[k] = `[len ${brief[k].length}]`;
  console.log(JSON.stringify(brief));
  console.log('humans', H, 'players', vu.playerCount, 'spawnSteps', jJ, 'totalSteps', steps, 'cmds', cmds.length);
  const byId = {};
  for (const c of cmds) byId[c.id] = (byId[c.id] || 0) + 1;
  console.log('cmd ids', JSON.stringify(byId));
  console.log('teamPlayerCount', Array.from(vu.teamPlayerCount || []));
  const names = vu.playerNamesData ? Array.from(vu.playerNamesData).slice(0, H) : [];
  console.log('names', names.map((n, i) => `${i}:${n}`).join(' | '));
  console.log('first cmds', JSON.stringify(cmds.slice(0, 12)));
  console.log('last cmds', JSON.stringify(cmds.slice(-12)));
}
