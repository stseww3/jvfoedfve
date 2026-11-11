// cmd_bursts.mjs — 同一玩家在同一拍（服务器帧）执行的陆攻+出船指令条数分布，我方号 vs 其他真人。
// 背景：策略每 5 拍最多下 1 条陆攻（Policy.act 的 t % period 门，period=5），指令只在 7 的倍数拍结算（服务器帧）；
//   所以同一拍 ≥3 条只能来自：客户端落后后追帧（把积压的几十拍一口气跑完、每 5 拍各下一条），或链路成批转发。
// 用法：node cmd_bursts.mjs [--from 0 --to 40] | <matchId>...  → 每局一行
import fs from 'node:fs';
import path from 'node:path';
import { loadReplay, timeline } from './replay_cmds.mjs';
import { squadIds } from './match_truth.mjs';
const DATA = process.env.C136_DATA || '/agent/repos/c136-data';
const args = process.argv.slice(2);
const val = (k, d) => (args.includes(k) ? args[args.indexOf(k) + 1] : d);
const all = fs.readdirSync(path.join(DATA, 'bundles')).filter((m) => /^[AB]/.test(m) && fs.existsSync(path.join(DATA, 'bundles', m, 'replay.txt'))).sort();
const ids = args.filter((a) => /^[A-Z]\d{3}$/.test(a));
const list = ids.length ? ids : all.slice(+val('--from', 0), +val('--to', all.length));
if (!ids.length && +val('--from', 0) === 0) console.log(['matchId', 'squadBots', 'squadCmds', 'squadBurstTicks(>=3)', 'squadCmdsInBursts', 'squadMaxBurst', 'squadBurst9', 'otherHumans', 'otherCmds', 'otherBurstTicks(>=3)', 'otherCmdsInBursts', 'otherMaxBurst', 'tickMod7Nonzero'].join('\t'));
for (const id of list) {
  try {
    const d = loadReplay(id);
    const names = d.vu.playerNamesData.data, H = d.vu.humanCount;
    const sq = squadIds(id, names, H).squad;
    const tl = timeline(d);
    const by = new Map(); let mod = 0;
    for (const x of tl.cmds) {
      if (x.tick < 0 || !(x.id === 1 || x.id === 3) || x.player >= H) continue;
      if (x.tick % 7) mod++;
      const k = x.player * 100000 + x.tick; by.set(k, (by.get(k) || 0) + 1);
    }
    const S = { cmds: 0, bt: 0, cb: 0, mx: 0, n9: 0 }, O = { cmds: 0, bt: 0, cb: 0, mx: 0, n9: 0 };
    const others = new Set();
    for (const [k, v] of by) {
      const p = Math.floor(k / 100000); const R = sq.has(p) ? S : O;
      if (!sq.has(p)) others.add(p);
      R.cmds += v; if (v >= 3) { R.bt++; R.cb += v; } if (v > R.mx) R.mx = v; if (v >= 9) R.n9++;
    }
    console.log([id, sq.size, S.cmds, S.bt, S.cb, S.mx, S.n9, others.size, O.cmds, O.bt, O.cb, O.mx, mod].join('\t'));
  } catch (e) { console.log([id, 'ERR', e.message.slice(0, 80)].join('\t')); }
}
