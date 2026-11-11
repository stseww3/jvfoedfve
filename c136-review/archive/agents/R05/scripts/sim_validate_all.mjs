// sim_validate_all.mjs — 对 bundles/ 下所有带录像的对局跑一遍 sim_replay 的逐拍重演，并与日志里每条 [HL-TICK] 的 terr/bal 比对。
// 输出一行一局：matchId、真人数、真人队数、各队人数、重演拍数、可比条数、全等条数、第一条不等的拍号（全等则为 -）。
// 用法：node sim_validate_all.mjs [--from 0] [--to 40] [--dir bundles|validation_bundles] > out/sim-validate.tsv   （分批跑，每批 <110 秒）
// 说明：A 系日志前缀就是号名，按「去掉 [标签] 后的名字全等」对号；B 系（squad20）日志前缀会轮换，改用 [HL-GAME-INIT] 的 me= 号对号（且该号名字须稳定出现）。
import fs from 'node:fs';
import path from 'node:path';
import { simulate, parseTicks, botIds } from './sim_replay.mjs';

const DATA = process.env.C136_DATA || '/agent/repos/c136-data';
const args = process.argv.slice(2);
const val = (k, d) => (args.includes(k) ? args[args.indexOf(k) + 1] : d);
const dir = val('--dir', 'bundles');
const all = fs.readdirSync(path.join(DATA, dir)).filter((m) => fs.existsSync(path.join(DATA, dir, m, 'replay.txt'))).sort();
const from = +val('--from', 0), to = +val('--to', all.length);
if (args.includes('--list')) { console.log(all.length, all.join(' ')); process.exit(0); }
if (from === 0) console.log(['matchId', 'humans', 'humanTeams', 'teamSizes', 'simTicks', 'tickLines', 'comparable', 'exact', 'firstDiffTick', 'cmds', 'attackNoFront', 'donateFail', 'boatFail', 'mountainCmds', 'ms'].join('\t'));
for (const id of all.slice(from, to)) {
  const t0 = Date.now();
  try {
    const ticks = parseTicks(id);
    const byT = new Map();
    for (const x of ticks) { if (!byT.has(x.t)) byT.set(x.t, []); byT.get(x.t).push(x); }
    let ids = null, n = 0, exact = 0, firstBad = -1;
    const R = simulate(id, {
      onStart: (g, ctx) => { ids = botIds(ctx.names, ctx.H, [...new Set(ticks.map((x) => x.bot))]); },
      onTick: (g, t) => {
        const L = byT.get(t);
        if (!L) return;
        for (const x of L) {
          const p = ids.get(x.bot);
          if (!(p >= 0)) continue;
          n++;
          if (g.terr[p] === x.terr && g.bal[p] === x.bal) exact++; else if (firstBad < 0) firstBad = t;
        }
      },
    });
    console.log([id, R.H, R.T ? R.T.humanTeams : 0, R.T ? R.T.counts.join('/') : '-', R.endTick, ticks.length, n, exact, firstBad < 0 ? '-' : firstBad, R.stats.cmds, R.stats.attackFail, R.stats.donateFail, R.stats.boatFail, R.stats.mountain, Date.now() - t0].join('\t'));
  } catch (e) {
    console.log([id, 'ERR', String(e.message).slice(0, 120)].join('\t'));
  }
}
