#!/usr/bin/env node
// cfopen.mjs — 开环指令流消融（会审提案里的「O 档」）：真值重演 + 把录像里的一小撮指令拿掉，其余所有人的指令原样重放。
//
// 这不是策略，也不产出策略：没有任何决策代码参与，只是在历史录像上回答「这一撮指令当时换来了什么」。
// 局限写在提案里：别人的指令是按「余额的千分比 + 目标号」录的，状态一变它们照旧执行，不会像真人那样改主意；
// 所以读数只在短视界内有意义，而且要和安慰剂臂（随便拿掉一条编队指令）的离散度比。
//
//   bash ../../tools/run-heavy.sh node scripts/cfopen.mjs <局> --arms <臂,臂,…> [--until T] [--at t1,t2,…]
//
// 臂：
//   drop1@T:k        安慰剂：拿掉 T 拍起编队成交的第 k 条指令（陆攻/捐款/船，k 从 0 数）
//   enemydon@T       拿掉 T 拍起敌方真人之间的捐款（没有队伍的局 = 其他真人之间）
//   squaddon@A-B     拿掉 A~B 拍编队号发出的捐款
//   dead@A-B         拿掉 A~B 拍编队落地时目标已经没有地的陆攻
//   dups@A-B         拿掉 A~B 拍编队同一拍里重复的指令（同号、同类、同目标，留第一条）
//   臂+drop1@T:k     配对臂：机制臂再叠一条安慰剂扰动。和单独的 drop1@T:k 比，差的就是「同一个被扰动的世界里这条机制臂的效应」；
//                    试跑发现单独一条安慰剂就能让后面的局面走开很远，所以机制臂要在几个不同的扰动下各比一次（读数拍用 --at 给绝对拍）。
// 输出：每臂每个断面一行，写到标准输出；不写缓存。
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { resim } from './resim.mjs';

const CACHE = path.join(path.dirname(fileURLToPath(import.meta.url)), '..', 'out', 'cache');
const NEUTRAL = 512;
const args = process.argv.slice(2);
const mid = args[0];
const opt = (k, d) => (args.includes(`--${k}`) ? args[args.indexOf(`--${k}`) + 1] : d);
if (!mid || !opt('arms')) {
  console.error('用法：node scripts/cfopen.mjs <局> --arms drop1@630:0,enemydon@4284,… [--until T] [--at t1,t2,…]');
  process.exit(2);
}
const until = opt('until') ? +opt('until') : undefined;
const arms = opt('arms').split(',').filter(Boolean);
const atArg = opt('at') ? opt('at').split(',').map(Number) : null;

const fmt = (x) => Math.round(x).toLocaleString('en-US');
const pct = (a, b) => (b ? `${a >= b ? '+' : ''}${(100 * (a - b) / b).toFixed(2)}%` : '—');

function summarize(out) {
  const H = out.H;
  const sq = Object.values(out.squad).map((s) => s.id).filter((x) => x >= 0);
  const isSq = new Uint8Array(512);
  for (const p of sq) isSq[p] = 1;
  const teamGame = out.nTeams >= 2;
  const myTeam = teamGame ? out.teams[sq[0]] : -1;
  const enemy = (p) => p < H && !isSq[p] && (teamGame ? out.teams[p] !== myTeam : true);
  const ser = out.snapT.map((t, i) => {
    let sl = 0, sb = 0, sn = 0, el = 0, eb = 0, emax = 0;
    for (const p of sq) { sl += out.snapTerr[i][p]; sb += out.snapBal[i][p]; if (out.snapTerr[i][p] > 0) sn++; }
    for (let p = 0; p < H; p++) if (enemy(p)) { el += out.snapTerr[i][p]; eb += out.snapBal[i][p]; if (out.snapTerr[i][p] > emax) emax = out.snapTerr[i][p]; }
    return { t, sl, sb, sn, el, eb, emax, team: teamGame ? out.teamLand[i][myTeam] : sl };
  });
  return { ser, H, sq, isSq, teamGame, myTeam, enemy, endTick: out.endTick, over: out.over, winnerTeam: out.winnerTeam, validate: out.validate };
}

const at = (S, t) => {
  let best = S.ser[0];
  for (const r of S.ser) { if (r.t <= t) best = r; else break; }
  return best;
};

const t0 = Date.now();
const T = resim(mid, { until });
const TS = summarize(T);
const tv = T.validate;
console.log(`[CF-O] ${mid} | 跑到 ${until ?? '结束'} | 真值臂：traj ${tv.bothExact}/${tv.rows} 行一致，结束拍 ${T.endTick}${T.over ? `，胜队 ${T.winnerTeam}` : ''} | 编队 ${TS.sq.length} 号 | ${((Date.now() - t0) / 1000).toFixed(0)}s`);
const sqCmds = T.cmdLog.filter((c) => TS.isSq[c[1]] && c[2] >= 1 && c[2] <= 3);
const truthCmd = T.cmdLog;

function buildArm(spec) {
  if (spec.includes('+')) {
    const parts = spec.split('+').map(buildArm);
    if (parts.some((p) => !p)) return null;
    return {
      label: parts.map((p) => p.label).join(' ＋ '),
      win: parts[0].win,
      filter: (c, g, info) => { for (const p of parts) if (!p.filter(c, g, info)) return false; return true; },
      stat: () => parts.map((p) => p.stat()).join(' ＋ '),
    };
  }
  const [name, rest] = spec.split('@');
  let dropped = 0, firstT = -1;
  const note = (g) => { dropped++; if (firstT < 0) firstT = g.t; };
  const first = () => (firstT < 0 ? '' : `，最早 ${firstT} 拍`);
  if (name === 'drop1') {
    const [a, k] = rest.split(':').map(Number);
    const list = sqCmds.filter((c) => c[0] >= a && c[5] === 1);
    const pick = list[k];
    if (!pick) return null;
    let done = false;
    const kinds = { 1: '陆攻', 2: '捐款', 3: '船' };
    return {
      label: `拿掉 ${pick[0]} 拍号 ${pick[1]} 的一条${kinds[pick[2]]}（真值里${pick[2] === 2 ? '到账' : '送出'} ${fmt(pick[6])} 兵）`,
      win: [pick[0], pick[0] + 1],
      filter: (c, g) => {
        if (done || g.t !== pick[0] || c.player !== pick[1] || c.id !== pick[2] || c.dX !== pick[3] || c.dZ !== pick[4]) return true;
        done = true; note(g);
        return false;
      },
      stat: () => `丢 ${dropped} 条${first()}`,
    };
  }
  if (name === 'enemydon') {
    const a = +rest;
    const rows = truthCmd.filter((c) => c[2] === 2 && c[5] === 1 && c[0] >= a && TS.enemy(c[1]));
    const got = rows.reduce((s, c) => s + c[6], 0), tax = rows.reduce((s, c) => s + c[7], 0);
    return {
      label: `拿掉 ${a} 拍起敌方真人发出的捐款（真值里成交 ${rows.length} 笔、到账 ${fmt(got)}、税 ${fmt(tax)}）`,
      win: [a, Infinity],
      filter: (c, g, info) => {
        if (c.id !== 2 || g.t < a || c.player >= info.H || info.isSquad[c.player]) return true;
        if (info.teamGame && info.teams[c.player] === TS.myTeam) return true;
        note(g);
        return false;
      },
      stat: () => `丢 ${dropped} 条（含被拒的）${first()}`,
    };
  }
  const [a, b] = (rest || '').split('-').map(Number);
  if (name === 'squaddon') {
    const rows = truthCmd.filter((c) => c[2] === 2 && c[5] === 1 && c[0] >= a && c[0] < b && TS.isSq[c[1]]);
    const got = rows.reduce((s, c) => s + c[6], 0), tax = rows.reduce((s, c) => s + c[7], 0);
    return {
      label: `拿掉 ${a}~${b} 拍编队号发出的捐款（真值里成交 ${rows.length} 笔、到账 ${fmt(got)}、税 ${fmt(tax)}）`,
      win: [a, b],
      filter: (c, g, info) => {
        if (c.id !== 2 || g.t < a || g.t >= b || !info.isSquad[c.player]) return true;
        note(g);
        return false;
      },
      stat: () => `丢 ${dropped} 条（含被拒的）${first()}`,
    };
  }
  if (name === 'dead') {
    // 录像里这类指令的目标已经是 512（无主地）；「发令时打的是 AI/真人」要从影子缓存的配对里取：
    // pairs 行 = [服务器拍, 页面发令拍, 类别, 千分比, 落地目标, 是否生效, 发令序号, 发令目标]
    const SH = JSON.parse(fs.readFileSync(path.join(CACHE, `${mid}-shadow.json`), 'utf8'));
    const want = new Map();
    let n = 0, troops = 0, noop = 0;
    for (const B of Object.values(SH.bots)) {
      for (const pr of B.match.pairs) {
        if (pr[2] !== 1 || pr[1] < a || pr[1] >= b || pr[7] === NEUTRAL || pr[4] !== NEUTRAL) continue;
        const key = `${pr[0]}/${B.me}/${pr[3]}`;
        want.set(key, (want.get(key) || 0) + 1);
        n++;
      }
    }
    const left = new Map(want);
    for (const c of truthCmd) {
      if (c[2] !== 1 || c[4] !== NEUTRAL) continue;
      const key = `${c[0]}/${c[1]}/${c[3]}`;
      const k = left.get(key) || 0;
      if (!k) continue;
      left.set(key, k - 1);
      if (c[5] === 1) troops += c[6]; else noop++;
    }
    return {
      label: `拿掉 ${a}~${b} 拍发出、落地时目标已死的编队陆攻（影子配对 ${n} 条；真值里送出 ${fmt(troops)} 兵，作废 ${noop} 条）`,
      win: [a, b],
      filter: (c, g) => {
        if (c.id !== 1 || c.dZ !== NEUTRAL) return true;
        const key = `${g.t}/${c.player}/${c.dX}`;
        const k = want.get(key) || 0;
        if (!k) return true;
        want.set(key, k - 1);
        note(g);
        return false;
      },
      stat: () => `丢 ${dropped} 条${first()}`,
    };
  }
  if (name === 'dups') {
    let curT = -1, seen = new Set();
    return {
      label: `拿掉 ${a}~${b} 拍编队同一拍里重复的指令（同号、同类、同目标，留第一条）`,
      win: [a, b],
      filter: (c, g, info) => {
        if (g.t < a || g.t >= b || !info.isSquad[c.player] || c.id < 1 || c.id > 3) return true;
        if (g.t !== curT) { curT = g.t; seen = new Set(); }
        const key = `${c.player}/${c.id}/${c.dZ}`;
        if (!seen.has(key)) { seen.add(key); return true; }
        note(g);
        return false;
      },
      stat: () => `丢 ${dropped} 条${first()}`,
    };
  }
  return null;
}

// 开环臂的有效性指标：同一条录像指令（拍/号/种类/千分比/目标/第几次出现）在真值臂和反事实臂里的受理结果是否相同。
// 别人的指令是照原录像发的，世界一变，原来受理的会被拒、原来被拒的会受理；变的越多，这一臂离「别人照旧」越远。
function okMap(log, H) {
  const m = new Map(), occ = new Map();
  for (const c of log) {
    if (c[1] >= H || c[2] < 1 || c[2] > 3) continue;
    const k0 = `${c[0]}/${c[1]}/${c[2]}/${c[3]}/${c[4]}`;
    const n = occ.get(k0) || 0;
    occ.set(k0, n + 1);
    m.set(`${k0}#${n}`, c[5] ? 1 : 0);
  }
  return m;
}
const truthOk = okMap(T.cmdLog, T.H);
function flips(C) {
  const m = okMap(C.cmdLog, C.H);
  const r = { sq: [0, 0, -1], ot: [0, 0, -1] };
  for (const [k, ok] of m) {
    const t = truthOk.get(k);
    if (t === undefined) continue;
    const parts = k.split('/');
    const g = TS.isSq[+parts[1]] ? r.sq : r.ot;
    g[1]++;
    if (t !== ok) { g[0]++; if (g[2] < 0 || +parts[0] < g[2]) g[2] = +parts[0]; }
  }
  return r;
}

for (const spec of arms) {
  const arm = buildArm(spec);
  if (!arm) { console.log(`${mid} | ${spec} | 这一臂没有可丢的指令或写法不对`); continue; }
  const t1 = Date.now();
  const C = resim(mid, { until, cmdFilter: arm.filter });
  const CS = summarize(C);
  const v = C.validate;
  const firstMis = v.mism.length ? v.mism[0][0] : -1;
  console.log(`${mid} | ${spec} | ${arm.label} | ${arm.stat()} | traj ${v.bothExact}/${v.rows} 行仍与日志一致，首个不一致拍 ${firstMis < 0 ? '无' : firstMis} | 结束拍 ${C.endTick}${C.over ? `，胜队 ${C.winnerTeam}` : ''}（真值 ${T.endTick}） | ${((Date.now() - t1) / 1000).toFixed(0)}s`);
  const fl = flips(C);
  console.log(`${mid} | ${spec} | 受理结果变了的录像指令：其他真人 ${fl.ot[0]}/${fl.ot[1]} 条${fl.ot[2] >= 0 ? `（最早 ${fl.ot[2]} 拍）` : ''}，编队其余指令 ${fl.sq[0]}/${fl.sq[1]} 条${fl.sq[2] >= 0 ? `（最早 ${fl.sq[2]} 拍）` : ''}`);
  const base = arm.win[0];
  const cps = atArg || [base + 90, base + 300, base + 600, base + 900, base + 1500, base + 2400];
  const endT = Math.min(T.endTick, C.endTick);
  const list = [...new Set(cps.filter((t) => t <= endT).concat([endT]))];
  for (const t of list) {
    const a = at(TS, t), c = at(CS, t);
    console.log(`${mid} | ${spec} | t=${t} | 编队地 ${fmt(a.sl)} → ${fmt(c.sl)}（${pct(c.sl, a.sl)}） | 编队兵 ${fmt(a.sb)} → ${fmt(c.sb)}（${pct(c.sb, a.sb)}） | 有地号数 ${a.sn} → ${c.sn} | 本队地 ${fmt(a.team)} → ${fmt(c.team)}（${pct(c.team, a.team)}） | 敌方真人地 ${fmt(a.el)} → ${fmt(c.el)}（${pct(c.el, a.el)}） | 敌方最大一家 ${fmt(a.emax)} → ${fmt(c.emax)}（${pct(c.emax, a.emax)}） | 敌方真人兵 ${fmt(a.eb)} → ${fmt(c.eb)}（${pct(c.eb, a.eb)}）`);
  }
}
console.log(`[CF-O] ${mid} 共 ${((Date.now() - t0) / 1000).toFixed(0)}s`);
