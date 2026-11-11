// donation_bursts.mjs — 我方号「已执行捐兵」的到达间隔。策略侧同一个号两次调度决策至少隔 25 拍（v27-team-c116*.js 4331 行的槽位相位门），
// 所以录像里同一个号相邻两笔已执行捐兵的间隔 <25 拍（尤其是同一拍多笔）只能来自指令链路的积压/成批到达。
// 用法：node donation_bursts.mjs [--from 0 --to 40] → 每局一行：我方已执行捐兵数、同拍成批的笔数、间隔<25 的笔数、最大同拍批量、成批清单（拍:捐出号:笔数）
import fs from 'node:fs';
import path from 'node:path';
import { loadReplay, timeline } from './replay_cmds.mjs';
import { squadIds } from './match_truth.mjs';
const DATA = process.env.C136_DATA || '/agent/repos/c136-data';
const args = process.argv.slice(2);
const val = (k, d) => (args.includes(k) ? args[args.indexOf(k) + 1] : d);
const all = fs.readdirSync(path.join(DATA, 'bundles')).filter((m) => /^A/.test(m) && fs.existsSync(path.join(DATA, 'bundles', m, 'replay.txt'))).sort();
const ids = args.filter((a) => /^[A-Z]\d{3}$/.test(a));
const list = ids.length ? ids : all.slice(+val('--from', 0), +val('--to', all.length));
if (!ids.length && +val('--from', 0) === 0) console.log(['matchId', 'squadDonations', 'sameTickExtra', 'gapLT25', 'maxBatch', 'batches'].join('\t'));
for (const id of list) {
  try {
    const d = loadReplay(id);
    const names = d.vu.playerNamesData.data, H = d.vu.humanCount;
    const sq = squadIds(id, names, H).squad;
    const tl = timeline(d).cmds.filter((c) => c.id === 2 && sq.has(c.player));
    const by = new Map();
    for (const c of tl) { if (!by.has(c.player)) by.set(c.player, []); by.get(c.player).push(c.tick); }
    let n = 0, same = 0, lt25 = 0, maxB = 0; const batches = [];
    for (const [p, ts] of by) {
      n += ts.length;
      let run = 1;
      for (let i = 1; i <= ts.length; i++) {
        if (i < ts.length && ts[i] === ts[i - 1]) { same++; run++; } else { if (run > 1) batches.push(`${ts[i - 1]}:${sq.get(p)}:${run}`); maxB = Math.max(maxB, run); run = 1; }
        if (i < ts.length && ts[i] - ts[i - 1] < 25) lt25++;
      }
    }
    console.log([id, n, same, lt25, maxB, batches.slice(0, 12).join(' ')].join('\t'));
  } catch (e) { console.log([id, 'ERR', e.message.slice(0, 80)].join('\t')); }
}
