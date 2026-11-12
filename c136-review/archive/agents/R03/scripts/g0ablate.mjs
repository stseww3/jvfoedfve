#!/usr/bin/env node
// g0ablate.mjs — G0 保真度验收的「反向检验」：把重放 / 影子里某一条线上细节换回数据仓库模拟器的默认做法，
// 看核对指标掉多少。一条验收指标只有在这种时候会掉，才算得上验收。只打印一行摘要，不写任何缓存。
//
//   bash c136-review/tools/run-heavy.sh node scripts/g0ablate.mjs <局> --phys base|colors|botteams|nobotteams|cache32 [--until T]
//   bash c136-review/tools/run-heavy.sh node scripts/g0ablate.mjs <局> --shadow base|multi|strict-donate|offline|adapter-sim|isbot-sim [--until T]
//
// --phys   物理/建局层（resim.mjs 的真值重演，指标 = traj.csv 逐行核对）：
//   colors   组队局也用自由混战的配色随机数        botteams 内置 AI 一律轮流入队        cache32 不走 32 拍队伍总地缓存
//   nobotteams 内置 AI 一律不入队（8 队的局线上是入队的，用来检验「8 队及以上才入队」的正方向）
// --shadow 决策/适配层（shadow.mjs 的影子策略，指标 = 与线上日志、录像成交的一致数）：
//   multi          同一决策拍允许多条指令（线上适配层每拍只收 1 条）
//   strict-donate  捐款发令时就按受捐额度判定成败（数据仓库 sim 的 donate()；线上发令时不知道额度）
//   offline        g.online 为假（数据仓库 sim 自由运行时的取值）
//   adapter-sim    陆攻发令是否被接受按 sim 的 attack() 判（线上适配层只看有没有相邻格）
//   isbot-sim      isBot 用 sim 的定义（离线的真人一律算机器人）
import { resim } from './resim.mjs';

const args = process.argv.slice(2);
const mid = args[0];
const opt = (k, d) => (args.includes(`--${k}`) ? args[args.indexOf(`--${k}`) + 1] : d);
const until = opt('until', null);
const phys = opt('phys', null);
const sh = opt('shadow', null);
if (!mid || (!phys && !sh)) { console.error('用法见文件头'); process.exit(2); }
const t0 = Date.now();
const secs = () => ((Date.now() - t0) / 1000).toFixed(0);

if (phys) {
  process.env.G0_ABLATE = phys === 'base' ? '' : phys;
  let fastT = -1;
  const R = resim(mid, { until: until ? +until : undefined, onState: (g) => { if (fastT < 0 && g.endgameFast) fastT = g.t; } });
  const v = R.validate;
  const first = v.mism.length ? v.mism[0][0] : -1;
  const sq = Object.values(R.squad).filter((s) => s.id >= 0).map((s) => s.id);
  const lastT = R.snapT.length - 1;
  let land = 0;
  for (const p of sq) land += R.snapTerr[lastT][p];
  console.log(`${mid} | phys=${phys} | until=${until || 'end'} | traj 行 ${v.rows} | 地一致 ${v.terrExact} | 兵一致 ${v.balExact} | 都一致 ${v.bothExact} | 首个不一致拍 ${first} | 结束拍 ${R.endTick} | 胜队 ${R.over ? R.winnerTeam : -1} | 终局提速拍 ${fastT} | 猎杀次数 ${R.engineEvents.filter((e) => e[1] === 'hunt').length} | 末拍编队地 ${land} | ${secs()}s`);
} else {
  const { shadow } = await import('./shadow.mjs');
  const o = { until: until ? +until : undefined };
  if (sh === 'multi') o.multi = true;
  else if (sh === 'strict-donate') o.strictDonate = true;
  else if (sh === 'offline') o.online = false;
  else if (sh === 'adapter-sim') o.adapter = 'sim';
  else if (sh === 'isbot-sim') o.isBotMode = 'sim';
  else if (sh !== 'base') { console.error(`不认识的影子消融：${sh}`); process.exit(2); }
  const rep = shadow(mid, o);
  const T = { rows: 0, cmds: 0, nb: 0, neut: 0, boats: 0, dl: 0, dsh: 0, ds: 0, ol: 0, os: 0, ex: 0, mt: 0, issued: 0, err: 0 };
  for (const b of Object.values(rep.bots)) {
    const c = b.check;
    T.rows += c.tick.rows; T.cmds += c.tick.cmds; T.nb += c.tick.nb; T.neut += c.tick.neut; T.boats += c.tick.boats;
    T.dl += c.dispatch.log; T.dsh += c.dispatch.shadow; T.ds += c.dispatch.same;
    T.ol += c.opening.log; T.os += c.opening.same;
    T.ex += b.match.exec; T.mt += b.match.matched; T.issued += b.match.issued;
    if (b.error) T.err++;
  }
  const v = rep.validate;
  console.log(`${mid} | shadow=${sh} | until=${until || 'end'} | traj ${v.bothExact}/${v.rows} | HL-TICK 行 ${T.rows} | cmds 一致 ${T.cmds} | nb 一致 ${T.nb} | neut 一致 ${T.neut} | boats 一致 ${T.boats} | 调度 日志 ${T.dl} 影子 ${T.dsh} 相同 ${T.ds} | 开局 日志 ${T.ol} 相同 ${T.os} | 成交 ${T.ex} 对上 ${T.mt} | 影子发令 ${T.issued} | 报错号 ${T.err} | ${secs()}s`);
}
