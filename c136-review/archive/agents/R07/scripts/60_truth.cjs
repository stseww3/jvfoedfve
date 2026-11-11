#!/usr/bin/env node
// 60_truth.cjs — R07：真引擎重放取全场真值。
//
// 规则与重放全部来自统筹提供的 /agent/repos/c136-data/src/tools/engine_replay.cjs（startReplay：在 Node 里原样加载线上客户端
// live_game_js.js，按 replay.txt 逐拍重放）。本脚本只是多读几个引擎自己的状态数组，不改任何规则：
//   ah.hN 领土、ah.hb 余额、ah.nU 是否在场、ah.a6S 状态（2 = 已离开，由内置 AI 接管）、ah.a3o 名字、
//   bj.fX 队号、ae.hc(a, b) = a 打 b 的那个进攻槽里的兵（b = 512 表示无主地）、bQ.z.ky 海上的船数。
//
// 用法（必须套重计算闸）：
//   bash c136-review/tools/run-heavy.sh node c136-review/agents/R07/scripts/60_truth.cjs <matchId> [--every 10] [--teams-every 30]
// 输出到 c136-review/agents/R07/out/<matchId>/：
//   truth_players.tsv  p name team human squad
//   truth_teams.tsv    t team terr bal alive（每 teams-every 拍，每个队一行；alive = 该队在场玩家数）
//   truth_bots.tsv     t bot p terr bal alive state boats（每 every 拍，我方每个号一行）
//   truth_atk.tsv      t dir from to troops（每 every 拍；dir=in：别人打我方号；dir=out：我方号打别人；to/from 是玩家号，512=无主地）
//   truth_all.tsv      t p terr bal alive state（每 teams-every×3 拍，全场领土 >0 的玩家）
//   truth_border.tsv   t bot p borderPx borderTouchWater neutralAdj nbs（每 90 拍；nbs = 相邻玩家号:相邻边界格数，按格数从多到少；
//                      边界格取自引擎的 ah.hF[p]（只算仍属于 p 且处于「边界态」ad.k5 的格）；borderTouchWater = 陆上边界格里同时挨着水（ad.iq）的格数——注意这不是「海岸格数」：引擎把只挨水不挨别人的格另存一张表，
//                      海岸格数/能否出船请看 65_shadow.mjs 的 shadow_coast.tsv（取自干净模拟器的 g.coast / g.boatsAllowed）；
//                      neutralAdj = 四邻有无主陆地（ad.fQ）的边界格数）
//   truth_cmd.tsv      tick p bot kind a b target bal_m2 bal_m1 bal_0 bal_p1 terr_m1 terr_p1 [tbal_m1 tbal_p1 tterr]
//                      （需要先用统筹的 replay_cmds.mjs 生成 out/<matchId>/cmds.tsv；逐条列出我方号被引擎接受的指令，
//                        以及该号在指令拍前后（T-2、T-1、T、T+1）的余额；捐款再给出受捐方前后余额）
//   truth_check.txt    与 traj.csv 快照的对账结果
const fs = require('fs');
const path = require('path');
const { startReplay, loadCsv, DATA } = require('/agent/repos/c136-data/src/tools/engine_replay.cjs');

const args = process.argv.slice(2);
const mid = args[0];
const opt = (k, d) => { const i = args.indexOf(k); return i >= 0 ? args[i + 1] : d; };
const every = +opt('--every', 10);
const teamsEvery = +opt('--teams-every', 30);
const OUT = path.join(__dirname, '..', 'out', mid);
fs.mkdirSync(OUT, { recursive: true });

const t0 = Date.now();
const { h, info, api } = startReplay(mid);
const names = api.names();
const api2 = h.run(`({
  teams: function () { var r = []; for (var p = 0; p < aE.a0E; p++) r.push(bj.fX[p]); return r; },
  all: function () { var r = []; for (var p = 0; p < aE.a0E; p++) r.push(ah.hN[p], ah.hb[p], ah.nU[p], ah.a6S[p]); return r; },
  boats: function (ids) { var r = []; for (var k = 0; k < ids.length; k++) r.push(bQ.z.ky[ids[k]] | 0); return r; },
  border: function (ids) {
    var out = [], fb = ad.fb;
    for (var k = 0; k < ids.length; k++) {
      var p = ids[k];
      if (!ah.nU[p]) { out.push(null); continue; }
      var list = ah.hF[p], seen = {}, nb = {}, coast = 0, neut = 0, n = 0;
      for (var i = 0; i < list.length; i++) {
        var fD = list[i];
        if (seen[fD]) continue; seen[fD] = 1;
        if (!ad.h9(fD) || ad.fR(fD) !== p) continue;
        n++;
        var c = 0, ne = 0, owners = {};
        for (var j = 0; j < 4; j++) {
          var q = fD + fb[j];
          if (ad.iq(q)) c = 1;
          else if (ad.fQ(q)) ne = 1;
          else if (ad.h9(q)) { var o = ad.fR(q); if (o !== p) owners[o] = 1; }
        }
        coast += c; neut += ne;
        for (var o2 in owners) nb[o2] = (nb[o2] || 0) + 1;
      }
      out.push([n, coast, neut, nb]);
    }
    return JSON.stringify(out);
  },
  atk: function (ids) {
    var r = [], N = aE.a0E, W = aE.fW;
    for (var k = 0; k < ids.length; k++) {
      var b = ids[k];
      if (!ah.nU[b]) continue;
      for (var p = 0; p < N; p++) {
        if (p === b || !ah.nU[p]) continue;
        var x = ae.hc(p, b); if (x > 0) r.push(0, p, b, x);
        var y = ae.hc(b, p); if (y > 0) r.push(1, b, p, y);
      }
      var z = ae.hc(b, W); if (z > 0) r.push(1, b, W, z);
    }
    return r;
  }
})`);

const traj = loadCsv(path.join(DATA, mid, 'traj.csv'));
const res = loadCsv(path.join(DATA, mid, 'results.csv'));
const botNames = [...new Set([...traj.map((r) => r.bot), ...res.map((r) => r.bot)])];
const idOf = new Map();
for (let p = 0; p < info.ku; p++) {
  const nm = String(names[p] || '');
  if (!/^\[APEX\] |^\[Nope\] |^\[COLD\] /.test(nm) && !botNames.some((b) => nm === b)) continue;
  const short = nm.replace(/^\[[A-Za-z]+\] /, '');
  idOf.set(short, p);
}
// 只保留名牌是 [APEX]/[Nope] 的号，以及 traj/results 里出现过的号
const squad = [...idOf].filter(([b, p]) => /^\[(APEX|Nope)\] /.test(String(names[p])) || botNames.includes(b));
const squadIds = squad.map(([, p]) => p);
const squadName = new Map(squad.map(([b, p]) => [p, b]));

const snapsAt = new Map();
for (const r of traj) { const p = idOf.get(r.bot); if (p === undefined) continue; const t = +r.t; if (!snapsAt.has(t)) snapsAt.set(t, []); snapsAt.get(t).push([r, p]); }

let teams = null;
const outTeams = ['t\tteam\tterr\tbal\talive'];
const outBots = ['t\tbot\tp\tterr\tbal\talive\tstate\tboats'];
const outAtk = ['t\tdir\tfrom\tto\ttroops'];
const outAll = ['t\tp\tterr\tbal\talive\tstate'];
const outBorder = ['t\tbot\tp\tborderPx\tborderTouchWater\tneutralAdj\tnbs'];
let exact = 0, total = 0, lastT = -1, steps = 0;
// 逐拍记下我方号（以及被我方捐款的对象）的余额/领土，供 truth_cmd.tsv 用
const cmdFile = path.join(OUT, 'cmds.tsv');
const cmds = [];
if (fs.existsSync(cmdFile)) {
  const L = fs.readFileSync(cmdFile, 'utf8').split('\n').filter(Boolean);
  for (const l of L.slice(1)) { const c = l.split('\t'); cmds.push({ tick: +c[0], id: +c[1], kind: c[2], p: +c[3], a: +c[5], b: +c[6], tname: c[7] || '' }); }
}
const watch = new Set(squadIds);
for (const c of cmds) if (c.kind === 'donate' && (squadIds.includes(c.p) || squadIds.includes(c.b))) { watch.add(c.p); watch.add(c.b); }
const watchIds = [...watch];
const hist = new Map(); // t -> Int32Array [terr, bal] * watchIds
const bad = [];
const deadline = t0 + 100000;
while (true) {
  const [t, hx, st] = api.advance(1);
  steps++;
  if (hx) continue;
  if (t === lastT) { if (st === 2) break; continue; }
  lastT = t;
  if (!teams) teams = api2.teams();
  {
    const w = api.snap(watchIds);
    const row = new Float64Array(watchIds.length * 2);
    for (let k = 0; k < watchIds.length; k++) { row[2 * k] = w[4 * k]; row[2 * k + 1] = w[4 * k + 1]; }
    hist.set(t, row);
  }
  const needAll = t % teamsEvery === 0 || snapsAt.has(t);
  const s = needAll || t % every === 0 ? api2.all() : null;
  if (snapsAt.has(t)) {
    for (const [r, p] of snapsAt.get(t)) {
      total++;
      if (s[p * 4] === +r.terr && s[p * 4 + 1] === +r.bal) exact++;
      else if (bad.length < 12) bad.push(`t=${t} ${r.bot}: 日志 ${r.terr}/${r.bal} | 引擎 ${s[p * 4]}/${s[p * 4 + 1]}`);
    }
  }
  if (t % teamsEvery === 0) {
    const agg = new Map();
    for (let p = 0; p < info.players; p++) {
      if (!s[p * 4 + 2]) continue;
      const k = teams[p];
      const a = agg.get(k) || [0, 0, 0];
      a[0] += s[p * 4]; a[1] += s[p * 4 + 1]; a[2] += 1;
      agg.set(k, a);
    }
    for (const [k, a] of [...agg].sort((x, y) => x[0] - y[0])) outTeams.push([t, k, a[0], a[1], a[2]].join('\t'));
    if (t % (teamsEvery * 3) === 0) for (let p = 0; p < info.players; p++) if (s[p * 4] > 0) outAll.push([t, p, s[p * 4], s[p * 4 + 1], s[p * 4 + 2], s[p * 4 + 3]].join('\t'));
  }
  if (t % 90 === 0 && t > 0) {
    const bd = JSON.parse(api2.border(squadIds));
    squadIds.forEach((p, k) => {
      const x = bd[k];
      if (!x) return;
      const nbs = Object.entries(x[3]).sort((a, b) => b[1] - a[1]).map(([o, c]) => `${o}:${c}`).join(' ');
      outBorder.push([t, squadName.get(p), p, x[0], x[1], x[2], nbs].join('\t'));
    });
  }
  if (t % every === 0) {
    const bt = api2.boats(squadIds);
    squadIds.forEach((p, k) => outBots.push([t, squadName.get(p), p, s[p * 4], s[p * 4 + 1], s[p * 4 + 2], s[p * 4 + 3], bt[k]].join('\t')));
    const a = api2.atk(squadIds);
    for (let i = 0; i < a.length; i += 4) outAtk.push([t, a[i] ? 'out' : 'in', a[i + 1], a[i + 2], a[i + 3]].join('\t'));
  }
  if (st === 2) break;
  if (Date.now() > deadline) { console.log(`# 时间到，停在第 ${t} 拍`); break; }
}
const players = ['p\tname\tteam\thuman\tsquad'];
for (let p = 0; p < info.players; p++) players.push([p, String(names[p] || '').replace(/[\t\n]/g, ' '), teams ? teams[p] : '', p < info.ku ? 1 : 0, squadName.has(p) ? squadName.get(p) : ''].join('\t'));
fs.writeFileSync(path.join(OUT, 'truth_players.tsv'), players.join('\n') + '\n');
fs.writeFileSync(path.join(OUT, 'truth_teams.tsv'), outTeams.join('\n') + '\n');
fs.writeFileSync(path.join(OUT, 'truth_bots.tsv'), outBots.join('\n') + '\n');
fs.writeFileSync(path.join(OUT, 'truth_atk.tsv'), outAtk.join('\n') + '\n');
fs.writeFileSync(path.join(OUT, 'truth_all.tsv'), outAll.join('\n') + '\n');
fs.writeFileSync(path.join(OUT, 'truth_border.tsv'), outBorder.join('\n') + '\n');
const outCmd = ['tick\tp\tbot\tkind\ta\tb\ttarget\tbal_m2\tbal_m1\tbal_0\tbal_p1\tterr_m1\tterr_p1\ttbal_m1\ttbal_p1\ttterr'];
const wIdx = new Map(watchIds.map((p, k) => [p, k]));
const hv = (t, p, j) => { const r = hist.get(t); const k = wIdx.get(p); return r && k !== undefined ? r[2 * k + j] : ''; };
for (const c of cmds) {
  if (c.tick < 0) continue;
  const mine = squadIds.includes(c.p);
  const toMine = c.kind === 'donate' && squadIds.includes(c.b);
  if (!mine && !toMine) continue;
  const T = c.tick;
  const row = [T, c.p, squadName.get(c.p) || String(names[c.p] || '').replace(/[\t\n]/g, ' '), c.kind, c.a, c.b, c.tname,
    hv(T - 2, c.p, 1), hv(T - 1, c.p, 1), hv(T, c.p, 1), hv(T + 1, c.p, 1), hv(T - 1, c.p, 0), hv(T + 1, c.p, 0)];
  if (c.kind === 'donate') row.push(hv(T - 1, c.b, 1), hv(T + 1, c.b, 1), hv(T - 1, c.b, 0)); else row.push('', '', '');
  outCmd.push(row.join('\t'));
}
fs.writeFileSync(path.join(OUT, 'truth_cmd.tsv'), outCmd.join('\n') + '\n');
const chk = [
  `# ${mid} 真引擎重放：真人 ${info.ku}，全部玩家 ${info.players}，地图 ${info.map}（${info.w}x${info.h}，陆地 ${info.ke}），队数 ${info.teams}`,
  `# 我方号：${squad.map(([b, p]) => `${b}=${p}(T${teams ? teams[p] : '?'})`).join(' ')}`,
  `# 重放到第 ${lastT} 拍，用时 ${((Date.now() - t0) / 1000).toFixed(1)} 秒`,
  `# 与 traj.csv 快照对账：${total} 个点，领土和余额都一致 ${exact} 个（${total ? (100 * exact / total).toFixed(1) : '0'}%）`,
  ...bad.map((b) => '#   ' + b),
];
fs.writeFileSync(path.join(OUT, 'truth_check.txt'), chk.join('\n') + '\n');
console.log(chk.join('\n'));
console.log(`# 已写 ${OUT}/truth_{players,teams,bots,atk,all,cmd}.tsv（bots ${outBots.length - 1} 行，atk ${outAtk.length - 1} 行，teams ${outTeams.length - 1} 行，cmd ${outCmd.length - 1} 行）`);
