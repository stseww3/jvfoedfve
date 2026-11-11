// engine_truth.cjs — 用线上客户端原文重放一局，并把“全场真相”取出来写成几张表（给逐局复盘用）。
//
// 用法：node scripts/engine_truth.cjs <局号> [--out 目录] [--step 10]
//   默认写到 tmp/truth/<局号>/（tmp 不进 git；任何人都能用本脚本重算出同样的表）
//
// 写出的表（全部制表符分隔，第一行是列名；p / q / 目标 都是引擎玩家编号，512 = 无主地）：
//   meta.json   局信息：玩家名、队伍、我方号、出生点、终局拍、每张表行数
//   cmd.tsv     每条被执行的指令，以及它执行前后的余额、真实出兵量 / 真实到账额、配额占用
//   ev.tsv      指令以外的事件：船靠岸及结果、AI 或离场号的赠送、出局（含当时的进攻者）、离场
//   state.tsv   每 step 拍：全部真人的领土、余额、在外进攻兵、被进攻兵、船数
//   our.tsv     每一拍：我方号的领土、余额、在外进攻兵、被进攻兵
//   team.tsv    每 step 拍：各队总领土、总余额、存活人数（队 0 = 没有队伍的玩家）
//   flow.tsv    每 step 拍：与我方队伍有关的地块易手（谁的地变成了谁的地，多少像素）
//   atk.tsv     每 step 拍：与我方队伍有关的在途进攻（进攻者、目标、剩余兵）
//
// 规则仍然全部来自线上原文。本脚本只做两类事：
//   1) 源码上开两个只读口子：录像播放器的单步函数、配额模块的两个私有量（已用点数、上限）；
//   2) 运行时在引擎的公开函数外面包一层记录（指令入口、出兵登记、赠送入账、船靠岸、出局），不改任何返回值。
const fs = require('fs');
const path = require('path');
const { createHost } = require('./engine_host.cjs');
const { patchSource, loadCsv, DATA } = require('./engine_replay.cjs');

function patchTruth(src) {
  src = patchSource(src);
  const a = 'function ca(){var aOX=new Uint16Array(aE.fW);var aOY=0;';
  if (src.split(a).length !== 2) throw new Error('配额模块的锚点找不到（引擎版本变了？）');
  return src.replace(a, a + 'this.__q=function(){return [aOX,aOY]};');
}

const HOOKS = String.raw`(function () {
  var T = window.__T = { cmd: [], ev: [], state: [], our: [], team: [], flow: [], atk: [], cur: null, land: null, spawnStep: 0 };
  var ku = aE.ku, N = aE.a0E, FW = aE.fW;
  var hb = ah.hb, hN = ah.hN, nU = ah.nU, a6S = ah.a6S;
  function used(q) { return ao.__q()[0][q]; }
  function cap() { return ao.__q()[1]; }

  // 指令入口
  var rV0 = bB.qk.rV;
  bB.qk.rV = function (id, p, a, b) {
    var c = { t: bi.kr(), sp: aE.hx ? T.spawnStep : -1, id: id, p: p, a: a === undefined ? -1 : a, b: b === undefined ? -1 : b, bal0: hb[p], terr0: hN[p], sub: [] };
    if (id === 2 && b < FW) { c.q = b; c.balQ0 = hb[b]; c.terrQ = hN[b]; c.used0 = used(b); c.cap = cap(); }
    T.cur = c;
    rV0.call(this, id, p, a, b);
    T.cur = null;
    c.bal1 = hb[p];
    if (id === 2 && b < FW) { c.balQ1 = hb[b]; c.used1 = used(b); }
    T.cmd.push(c);
  };
  // 出兵登记：真人指令、内置 AI 出兵、船靠岸转陆攻 都走这里
  var aeei0 = ae.ei;
  ae.ei = function (player, troops, target) {
    if (T.cur) T.cur.sub.push('atk:' + target + ':' + troops);
    else if (T.land) T.land.sub.push('atk:' + target + ':' + troops);
    else if (target < ku && player >= ku) T.ev.push([bi.kr(), 'aiatk', player, target, troops, '']);
    return aeei0.call(this, player, troops, target);
  };
  // 船出发
  var n50 = bQ.z.n5;
  bQ.z.n5 = function (player) {
    var id = this.n3, troops = bR.g6[0], path = bR.h[0];
    var r = n50.call(this, player);
    var end = path && path.length ? path[path.length - 1] : -1;
    if (T.cur) T.cur.sub.push('boat:' + id + ':' + this.a9g[this.mk - 1] + ':' + end);
    else if (player < ku) T.ev.push([bi.kr(), 'boatgo', player, id, this.a9g[this.mk - 1], String(end)]);
    return r;
  };
  // 船靠岸：acM 在结算前被调用，aak 在结算后移除船
  var acM0 = bg.acM;
  bg.acM = function (player) { T.land = { p: player, sub: [], bal0: hb[player] }; return acM0.call(this, player); };
  var rE0 = bB.kw.rE;
  bB.kw.rE = function (player, q, troops) {
    var b0 = hb[q], u0 = used(q);
    var r = rE0.call(this, player, q, troops);
    var got = hb[q] - b0;
    var s = 'give:' + q + ':' + troops + ':' + got + ':' + u0 + ':' + used(q) + ':' + cap();
    if (T.land) T.land.sub.push(s); else T.ev.push([bi.kr(), 'handoff', player, q, troops, s]);
    return r;
  };
  var aak0 = bQ.mt.aak;
  bQ.mt.aak = function (i) {
    var z = bQ.z, player = z.mo[i] >> 3, troops = z.a9g[i], id = z.mn[i];
    var pos = bP.jK(z.mz[i]);
    if (player < ku || (T.land && T.land.sub.length && /^(atk|give):(\d+)/.test(T.land.sub[0]) && +RegExp.$2 < ku)) {
      var kind = T.land && T.land.p === player ? 'land' : (troops === 0 ? 'sunk' : 'boatend');
      var sub = T.land && T.land.p === player ? T.land.sub.join(';') : '';
      if (kind === 'land' && !sub) sub = 'home_or_lost:' + (hb[player] - T.land.bal0);
      T.ev.push([bi.kr(), kind, player, id, troops, pos + '|' + sub]);
    }
    T.land = null;
    return aak0.call(this, i);
  };
  // AI / 离场号的赠送
  var kx0 = bB.kw.kx;
  bB.kw.kx = function (player, q, troops) {
    var b0 = hb[q], d0 = hb[player];
    var r = kx0.call(this, player, q, troops);
    if (q < ku || player < ku) T.ev.push([bi.kr(), 'aigift', player, q, hb[q] - b0, 'donorLost:' + (d0 - hb[player])]);
    return r;
  };
  // 出局
  var dt0 = al.dt;
  al.dt = function (p) {
    // 领土和峰值都已清零、只剩船在海上的号，每拍都会再进来一次（什么也不做），不重复记
    if (p < ku && (hN[p] + ah.a0i[p] > 0 || !bQ.z.ky[p])) {
      var at = ae.aL6(p), s = [];
      for (var i = 0; i < at.length; i++) s.push(at[i] + ':' + ae.hc(at[i], p) + ':' + hN[at[i]]);
      T.pendDead = [bi.kr(), 'collapse', p, hN[p], hb[p], 'peak:' + ah.a0i[p] + ';boats:' + bQ.z.ky[p] + ';out:' + ae.aLB(p) + ';by:' + s.join(',')];
    }
    var r = dt0.call(this, p);
    if (p < ku && T.pendDead) {
      // 三种结果：出局；地和余额清零但海上还有船（号还在）；没地但登陆战还在打（什么也没发生，不记）
      var had = T.pendDead[3] > 0 || /peak:[1-9]/.test(T.pendDead[5]);
      if (!nU[p]) { T.pendDead[1] = 'dead'; T.ev.push(T.pendDead); }
      else if (had) { T.pendDead[1] = 'wiped-keeps-boats'; T.ev.push(T.pendDead); }
      T.pendDead = null;
    }
    return r;
  };
  var aL40 = al.aL4;
  al.aL4 = function (p) {
    if (p < ku && !T.pendDead) {
      var at = ae.aL6(p), s = [];
      for (var i = 0; i < at.length; i++) s.push(at[i] + ':' + ae.hc(at[i], p) + ':' + hN[at[i]]);
      T.ev.push([bi.kr(), 'dead-other', p, hN[p], hb[p], 'peak:' + ah.a0i[p] + ';out:' + ae.aLB(p) + ';by:' + s.join(',')]);
    }
    return aL40.call(this, p);
  };

  var W = bV.fk, H = bV.fl, NP = W * H;
  var prev = new Uint16Array(NP), cur = new Uint16Array(NP);
  var inT = new Float64Array(FW + 1), inC = new Uint16Array(FW + 1);
  var lastState = new Uint8Array(FW);
  function owners(out) {
    for (var i = 0, fD = 0; i < NP; i++, fD += 4) out[i] = ad.h9(fD) ? ad.fR(fD) : (ad.fQ(fD) ? 512 : 700);
  }
  function incoming() {
    inT.fill(0); inC.fill(0);
    for (var p = 0; p < N; p++) { if (!nU[p]) continue; var n = ae.gg(p); for (var i = 0; i < n; i++) { var k = ae.gl(p, i); inT[k] += ae.gm(p, i); inC[k]++; } }
  }
  return {
    advance: function (n) { var st = bi.a3I; for (var k = 0; k < n; k++) { if (aE.a38 === 2) break; if (aE.hx) T.spawnStep++; st.__step(); } return [bi.kr(), aE.hx ? 1 : 0, aE.a38]; },
    names: function () { var r = []; for (var p = 0; p < N; p++) r.push(ah.a3o[p]); return r; },
    teams: function () { var r = []; for (var p = 0; p < N; p++) r.push(bj.fX[p]); return r; },
    boxes: function () { var r = []; for (var p = 0; p < ku; p++) r.push([ah.jS[p], ah.jU[p], ah.jT[p], ah.jV[p], hN[p], hb[p], nU[p]]); return r; },
    initOwners: function () { owners(prev); },
    // 每拍：我方号
    perTick: function (ours) {
      var t = bi.kr(); incoming();
      for (var k = 0; k < ours.length; k++) { var p = ours[k]; T.our.push(t, p, hN[p], hb[p], nU[p] ? ae.aLB(p) : 0, inT[p], inC[p], nU[p] ? bQ.z.ky[p] : 0); }
      for (var p2 = 0; p2 < ku; p2++) { if (a6S[p2] !== lastState[p2]) { T.ev.push([t, 'state', p2, lastState[p2], a6S[p2], 'terr:' + hN[p2] + ';bal:' + hb[p2]]); lastState[p2] = a6S[p2]; } }
    },
    // 每 step 拍：全体真人、各队、易手、在途进攻
    sample: function (teamFlag) {
      var t = bi.kr(); incoming();
      var fX = bj.fX, p, i;
      for (p = 0; p < ku; p++) T.state.push(t, p, hN[p], hb[p], nU[p] ? ae.aLB(p) : 0, nU[p] ? ae.gg(p) : 0, inT[p], inC[p], nU[p] ? bQ.z.ky[p] : 0, nU[p], a6S[p], ah.a6b[p]);
      var tt = {}, key;
      for (p = 0; p < N; p++) {
        if (!nU[p]) continue;
        key = fX[p] + (p >= ku ? 100 : 0); // 100+ = 内置 AI，按队分开记
        var o = tt[key] || (tt[key] = [0, 0, 0, 0]);
        o[0] += hN[p]; o[1] += hb[p]; o[2]++; if (p < ku && a6S[p] !== 2) o[3]++;
      }
      for (key in tt) T.team.push(t, +key, tt[key][0], tt[key][1], tt[key][2], tt[key][3]);
      owners(cur);
      var m = new Map();
      for (i = 0; i < NP; i++) { var a = prev[i], b = cur[i]; if (a !== b && (teamFlag[a] || teamFlag[b])) { var kk = a * 1024 + b; m.set(kk, (m.get(kk) || 0) + 1); } }
      m.forEach(function (v, kk) { T.flow.push(t, kk >> 10, kk & 1023, v); });
      var sw = prev; prev = cur; cur = sw;
      for (p = 0; p < N; p++) {
        if (!nU[p]) continue; var n = ae.gg(p);
        for (i = 0; i < n; i++) { var k = ae.gl(p, i); if (teamFlag[p] || (k < FW && teamFlag[k])) T.atk.push(t, p, k, ae.gm(p, i)); }
      }
    },
    quota: function (ids) { var q = ao.__q(); var r = [q[1]]; for (var i = 0; i < ids.length; i++) r.push(q[0][ids[i]]); return r; }
  };
})()`;

function runTruth(mid, opts = {}) {
  const step = opts.step || 10;
  const h = createHost({ patch: patchTruth });
  h.run('bx(true)');
  h.flushTimers();
  h.ctx.__rep = fs.readFileSync(path.join(DATA, mid, 'replay.txt'), 'utf8').trim();
  if (!h.run('bC.aMU.zS(window.__rep)')) throw new Error('录像解不开');
  h.run('bC.aVq()');
  h.flushTimers();
  const info = JSON.parse(h.run('JSON.stringify({ku:aE.ku, players:aE.a0E, ke:aE.ke, w:bV.fk, h:bV.fl, map:bV.fF, teamsField:aE.a0L, teamMode:aE.iT?1:0})'));
  const api = h.run(HOOKS);
  const T = h.ctx.__T;
  const names = api.names();
  // 我方号：先按名字（[APEX] xxx 或与 traj.csv 的 bot 同名），再用 results.csv 的 meId 补（B 组日志名会轮换）
  const traj = loadCsv(path.join(DATA, mid, 'traj.csv'));
  const results = loadCsv(path.join(DATA, mid, 'results.csv'));
  const bots = [...new Set(traj.map((r) => r.bot))];
  const ours = new Map(); // p -> 日志里的号名
  for (let p = 0; p < info.ku; p++) for (const b of bots) if (names[p] === b || names[p] === '[APEX] ' + b) ours.set(p, b);
  const byMe = [];
  if (opts.useMeId) for (const r of results) { const p = +r.meId; if (r.meId !== '' && p < info.ku && !ours.has(p)) { ours.set(p, r.bot); byMe.push(`${r.bot}=${p}(${names[p]})`); } }
  let spawnEnd = null, lastT = -1, teams = null, teamFlag = null, ourIds = null, boxes = null;
  const t0 = Date.now();
  while (true) {
    const [t, hx, st] = api.advance(1);
    if (hx) continue;
    if (spawnEnd === null) {
      spawnEnd = T.spawnStep;
      teams = api.teams();
      boxes = api.boxes();
      ourIds = [...ours.keys()].sort((a, b) => a - b);
      const ourTeams = new Set(ourIds.map((p) => teams[p]).filter((x) => x > 0));
      teamFlag = new Uint8Array(1024);
      for (let p = 0; p < info.ku; p++) if (ours.has(p) || (teams[p] > 0 && ourTeams.has(teams[p]))) teamFlag[p] = 1;
      api.initOwners();
    }
    if (t === lastT) { if (st === 2) break; continue; }
    lastT = t;
    api.perTick(ourIds);
    if (t % step === 0) api.sample(teamFlag);
    if (st === 2 || (opts.until && t >= opts.until)) break;
    if (Date.now() - t0 > 100000) { console.log(`# 时间到，停在第 ${t} 拍`); break; }
  }
  return { info, names, teams, ours, ourIds, boxes, spawnEnd, lastT, T, byMe, secs: (Date.now() - t0) / 1000, log: h.log };
}

function writeTruth(mid, R, outDir, step) {
  fs.mkdirSync(outDir, { recursive: true });
  const { T } = R;
  const rows = {};
  const w = (name, head, lines) => { fs.writeFileSync(path.join(outDir, name), head.join('\t') + '\n' + lines.join('\n') + (lines.length ? '\n' : '')); rows[name] = lines.length; };
  w('cmd.tsv', ['t', 'spawnStep', 'id', 'p', 'a', 'b', 'bal0', 'bal1', 'terr0', 'q', 'balQ0', 'balQ1', 'terrQ', 'used0', 'used1', 'cap', 'sub'],
    T.cmd.map((c) => [c.t, c.sp, c.id, c.p, c.a, c.b, c.bal0, c.bal1, c.terr0, c.q ?? '', c.balQ0 ?? '', c.balQ1 ?? '', c.terrQ ?? '', c.used0 ?? '', c.used1 ?? '', c.cap ?? '', c.sub.join(';')].join('\t')));
  w('ev.tsv', ['t', 'kind', 'p', 'x', 'y', 'detail'], T.ev.map((e) => e.join('\t')));
  const chunk = (arr, n) => { const o = []; for (let i = 0; i < arr.length; i += n) o.push(arr.slice(i, i + n).join('\t')); return o; };
  w('state.tsv', ['t', 'p', 'terr', 'bal', 'atkOut', 'nOut', 'atkIn', 'nIn', 'boats', 'alive', 'state', 'debt'], chunk(T.state, 12));
  w('our.tsv', ['t', 'p', 'terr', 'bal', 'atkOut', 'atkIn', 'nIn', 'boats'], chunk(T.our, 8));
  w('team.tsv', ['t', 'team', 'terr', 'bal', 'alive', 'humansPlaying'], chunk(T.team, 6));
  w('flow.tsv', ['t', 'from', 'to', 'px'], chunk(T.flow, 4));
  w('atk.tsv', ['t', 'attacker', 'target', 'troops'], chunk(T.atk, 4));
  const meta = {
    match: mid, step, info: R.info, spawnSteps: R.spawnEnd, lastTick: R.lastT,
    ours: Object.fromEntries([...R.ours].map(([p, b]) => [p, b])),
    players: R.names.slice(0, R.info.ku).map((n, p) => ({ p, name: n, team: R.teams[p], box: R.boxes[p].slice(0, 4), spawn: [Math.round((R.boxes[p][0] + R.boxes[p][2]) / 2), Math.round((R.boxes[p][1] + R.boxes[p][3]) / 2)] })),
    aiTeams: [...new Set(R.teams.slice(R.info.ku))].sort(), rows,
  };
  fs.writeFileSync(path.join(outDir, 'meta.json'), JSON.stringify(meta, null, 1));
  return rows;
}

module.exports = { runTruth, writeTruth, patchTruth };

if (require.main === module) {
  const args = process.argv.slice(2);
  const mid = args[0];
  const opt = (k, d) => { const i = args.indexOf(k); return i >= 0 ? args[i + 1] : d; };
  const step = +opt('--step', 10);
  const outDir = opt('--out', path.join(__dirname, '..', 'tmp', 'truth', mid));
  const R = runTruth(mid, { step, until: +opt('--until', 0) || 0, useMeId: args.includes('--me-id') });
  const rows = writeTruth(mid, R, outDir, step);
  // 自检：我方号在 [HL-TICK] 快照拍的领土、余额必须和 our.tsv 一致
  const traj = loadCsv(path.join(DATA, mid, 'traj.csv'));
  const at = new Map(); const T = R.T;
  for (let i = 0; i < T.our.length; i += 8) at.set(T.our[i] + ':' + T.our[i + 1], [T.our[i + 2], T.our[i + 3]]);
  const idOf = new Map([...R.ours].map(([p, b]) => [b, p]));
  let tot = 0, ok = 0;
  for (const r of traj) { if (!idOf.has(r.bot)) continue; const v = at.get(+r.t + ':' + idOf.get(r.bot)); if (!v) continue; tot++; if (v[0] === +r.terr && v[1] === +r.bal) ok++; }
  console.log(`# ${mid} 真相表已写到 ${path.relative(process.cwd(), outDir)}：终局拍 ${R.lastT}，用时 ${R.secs.toFixed(1)} 秒；自检 ${ok}/${tot} 个日志快照点一致`);
  console.log('# 行数 ' + Object.entries(rows).map(([k, v]) => `${k}=${v}`).join(' '));
  if (R.byMe.length) console.log('# 按 meId 补认的我方号：' + R.byMe.join(' '));
}
