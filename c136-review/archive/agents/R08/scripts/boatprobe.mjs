#!/usr/bin/env node
// boatprobe.mjs — 走偏根因的直接取证：线上引擎原文里，一艘船靠在「不是地」的格上以后，那笔兵去了哪。
//
// engdiff / fidmism 只看得到现象（A053 #32、A057 #93：船到岸 4 拍后真引擎把兵加回余额，模拟器没有）。
// 这里把线上引擎原文（src/engine/live_game_js.js，用 src/tools/engine_replay.cjs 在 Node 里原样加载）按录像重放到那几拍，
// 逐拍读引擎自己的状态：这个玩家的余额、它名下每一条进攻（目标玩家号、兵）、它的每一艘船（兵、进度、类型）；
// 船走到头的那一拍，把靠岸函数（acN）将要读的那一格摊开：是不是无主地（ad.fQ）、是不是有主的地（ad.h9）、是不是水（ad.iq）、
// 地形号 ≥3（ad.aKj）、以及 acN 当作「主人号」读出来的数（ad.fR）——再看这个号在场上是谁、和船主是不是敌对（bv.fS）。
// 只读 /agent/repos/c136-data（发现集）；不跑策略，不改任何指令，不改引擎的任何状态。
//
// 对着读的引擎原文（live_game_js.js）：
//   靠岸  acN(player,iI,acL,aae){ if(ad.fQ(acL)) k3=aE.fW; else { k3=ad.fR(acL); if(k3===player){…退回…;return} if(!bv.fS(player,k3)){bB.kw.rE(player,k3,iI);return} }
//                                 if(!ae.kF(player,k3)&&!ae.kY(player)){…;return} ah.h1[player].push(aae<<2); ae.ei(player,iI,k3); aG.k1(player,true) }
//         —— 这一格不是无主地时，不管它是不是有主的地，都按 ad.fR 读「主人号」。
//   格子  ad.fQ: aFA[fD+3]===0 && aFA[fD+2]===1（无主地）；ad.iq: …===2（水）；ad.aKj: …>=3；ad.h9: aFA[fD+3]>=aKW（有主的地）；
//         ad.fR = ((aFA[fD]&3)<<7)+((aFA[fD+1]&3)<<5)+((aFA[fD+2]&3)<<3)+(aFA[fD+3]&7) —— 地形格的 aFA[fD+2] 存的是地形号，3 号地形读出来就是 24。
//   进攻  gh(){ gU=ae.gl(gQ,gP); gR=ae.gm(gQ,gP); …; go(); if(gV===0){gp();return} … }   gp(){ …; var ea=bD.gv.gy(gQ,gR); bg.gz(gQ,gR-ea,12); ae.h0(gQ,gP) }
//         —— 一条进攻找不到可占的格（gV===0）就撤销，兵加回余额。
//
//   转交  bv.fS(player,k3) = bj.fX[player]===0 || bj.fX[player]!==bj.fX[k3]（敌对 = 自己没有队，或者两人不同队）；
//         bB.kw.rE(player,qu,iI){ if(!bD.gv.rF(iI,qu)){bg.gz(player,iI,12);return} … bD.gv.gy(qu,bR.g6[0]); … }；
//         rF 里的上限 a6a(qu,g1) = max(0, min(g1, 地×aE.a6d − 余额, aE.a6e − 余额)) —— 对方地是 0 时上限是 0，兵作废（统计项 12）。
//
// 用法：每个参数是一局，冒号后面是若干个「玩家号:起拍:止拍」的窗，用逗号隔开；一局只重放一遍。
//   bash c136-review/tools/run-heavy.sh node c136-review/agents/R08/scripts/boatprobe.mjs \
//       A053=32:1748:1772 A057=93:2468:2493 B010=42:1:1,45:1:1 --lands out/_run/namepool
//   --lands <目录>：窗写成 玩家号:1:1 时，从 namepool.mjs 的逐局输出里找这个号「靠在不能占的格上」的船，各取靠岸前 12 拍到后 8 拍。
//   → out/_cross/boatprobe.txt、boatprobe.json
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
const { startReplay } = require('/agent/repos/c136-data/src/tools/engine_replay.cjs');

const HERE = path.dirname(fileURLToPath(import.meta.url));
const OUT = path.join(HERE, '..', 'out', '_cross');

const PROBE = `(function (p) {
  var out = { bal: ah.hb[p], debt: ah.a6b[p], terr: ah.hN[p], atk: [], boats: [] };
  var n = ae.gg(p), i;
  for (i = 0; i < n; i++) out.atk.push([ae.gl(p, i), ae.gm(p, i)]);
  var z = bQ.z;
  for (var b = 0; b < z.mk; b++) {
    if ((z.mo[b] >> 3) !== p) continue;
    var type = z.ml[b] % 64;
    var row = { troops: z.a9g[b], prog: z.ab0[b], type: type };
    if (z.ab0[b] === 65535 && type < 4) {
      var aae = bP.jK(z.mz[b]);
      var acL = aae + bP.ie[type] << 2;
      var px = acL >> 2;
      var off = px < 0 || px >= bV.fk * bV.fl;
      var k3 = ad.fR(acL);
      var inGame = k3 < aE.a0E;
      row.cell = { aae: aae, px: px, off: off ? 1 : 0, w: bV.fk, h: bV.fl,
        land: ad.fQ(acL) ? 1 : 0, owned: ad.h9(acL) ? 1 : 0, water: ad.iq(acL) ? 1 : 0, ge3: ad.aKj(acL) ? 1 : 0,
        fR: k3,
        k3name: inGame ? String(ah.a3o[k3]) : null, k3alive: inGame ? (ah.nU[k3] ? 1 : 0) : null, k3terr: inGame ? ah.hN[k3] : null,
        k3bal: inGame ? ah.hb[k3] : null,
        k3human: k3 < aE.ku ? 1 : 0, enemy: inGame ? (bv.fS(p, k3) ? 1 : 0) : null,
        teamP: bj.fX[p], teamK: inGame ? bj.fX[k3] : null,
        room: inGame ? Math.max(0, Math.min(z.a9g[b], ah.hN[k3] * aE.a6d - ah.hb[k3], aE.a6e - ah.hb[k3])) : null,
        hasAtk: ae.kF(p, k3) ? 1 : 0, freeSlot: ae.kY(p) ? 1 : 0 };
    }
    out.boats.push(row);
  }
  return JSON.stringify(out);
})`;
const BAL = '(function (q) { return ah.hb[q]; })';

const args = process.argv.slice(2);
let landsDir = null;
const specs = [];
for (let i = 0; i < args.length; i++) {
  if (args[i] === '--lands') landsDir = path.resolve(HERE, '..', args[++i]);
  else specs.push(args[i]);
}

function windowsOf(mid, text) {
  const out = [];
  for (const w of text.split(',')) {
    const [p, lo, hi] = w.split(':').map(Number);
    if (lo === 1 && hi === 1) {
      // 从 namepool.mjs 的逐局输出里取：这个号靠在「不是能占的格」上的船（lands 里对方 = -1）
      const src = fs.readdirSync(landsDir).map((f) => JSON.parse(fs.readFileSync(path.join(landsDir, f), 'utf8')))
        .find((R) => (R.replayFrom || R.matchId) === mid);
      if (!src) throw new Error(`${mid}: --lands 目录里没有用这份录像的逐局输出`);
      for (const [t, q, tgt] of src.lands) if (q === p && tgt < 0) out.push({ p, lo: Math.max(1, t - 12), hi: t + 8, from: src.matchId });
    } else out.push({ p, lo, hi });
  }
  return out;
}

const sg = (x) => (x > 0 ? '+' : '') + x;
const J = [];
const lines = ['boatprobe.mjs — 线上引擎原文里，船靠在「不是地」的格上以后那笔兵的去向（逐拍读引擎自己的状态）',
  '  净额 = 余额 − 欠账（引擎的 ah.hb − ah.a6b；余额是 0 的号进账先还欠账）。「靠岸要读的那一格」= 船走到头的位置按船的类型挪一格。', ''];
const tally = [];
for (const spec of specs) {
  const [mid, text] = spec.split('=');
  const wins = windowsOf(mid, text);
  const { h, info, api } = startReplay(mid);
  const probe = h.run(PROBE);
  const balOf = h.run(BAL);
  const names = api.names();
  const maxT = Math.max(...wins.map((w) => w.hi));
  for (const w of wins) { w.rows = []; w.watch = null; }
  let lastT = -1;
  while (true) {
    const [t, hx, st] = api.advance(1);
    if (hx) continue;
    if (t === lastT) { if (st === 2) break; continue; }
    lastT = t;
    for (const w of wins) {
      if (t < w.lo || t > w.hi) continue;
      const r = { t, ...JSON.parse(probe(w.p)) };
      for (const b of r.boats) if (b.cell && !b.cell.land && !b.cell.owned && b.cell.k3name !== null) w.watch = b.cell.fR;
      if (w.watch !== null) r.balK = balOf(w.watch);
      w.rows.push(r);
    }
    if (st === 2 || t >= maxT) break;
  }
  for (const w of wins) {
    const { p, lo, hi, rows } = w;
    J.push({ matchId: mid, player: p, name: String(names[p]), humans: info.ku, lo, hi, rows });
    lines.push(`== ${mid} 玩家 #${p}（${String(names[p]).trim()}）；真人 ${info.ku}；拍 ${lo}~${hi}`);
    lines.push('  拍 | 余额 | 欠账 | 净额比上一拍 | 地 | 名下的进攻（目标玩家号:兵）| 名下的船（兵 / 进度 / 类型）| 读出来的那个「主人号」的余额');
    const subjects = [];
    let prev = null;
    for (const r of rows) {
      r.net = r.bal - r.debt;
      r.d = prev ? r.net - prev.net : null;
      lines.push(`  ${r.t} | ${r.bal} | ${r.debt} | ${r.d === null ? '' : sg(r.d)} | ${r.terr} | ${r.atk.map(([k, v]) => `${k}:${v}`).join(' ') || '–'} | `
        + `${r.boats.map((b) => `${b.troops} / ${b.prog} / ${b.type}`).join('；') || '–'} | ${r.balK === undefined ? '' : r.balK}`);
      for (const b of r.boats) {
        if (!b.cell) continue;
        const c = b.cell;
        if (c.land || c.owned) {
          lines.push(`    （${b.troops} 兵的船走到头，要读的那一格 ${c.px} 是${c.land ? '无主地' : `#${c.fR} 的地`}：正常靠岸，不在这里的题目里）`);
          continue;
        }
        const fresh = !prev || !prev.boats.some((x) => x.troops === b.troops);
        subjects.push({ t: r.t, troops: b.troops, cell: c, fresh });
        lines.push(`    ↑ ${b.troops} 兵的船走到头了（进度 65535，类型 ${b.type}${fresh ? '；上一拍名下还没有这艘船——发出的当拍就到头' : ''}）。船的位置是地图下标 ${c.aae}（地图 ${c.w} × ${c.h}）；`
          + `靠岸要读的那一格是下标 ${c.px}` + (c.off ? '——在图外' : `：无主地 ${c.land}｜有主的地 ${c.owned}｜水 ${c.water}｜地形号 ≥3 ${c.ge3}`)
          + `；按「主人号」读出来的是 ${c.fR}`
          + (c.k3name === null ? '（超出玩家数）' : `（场上的 #${c.fR}「${c.k3name.trim()}」：${c.k3human ? '真人席位' : '内置 AI'}，${c.k3alive ? '在场' : '不在场'}，地 ${c.k3terr}，余额 ${c.k3bal}；`
            + `船主在第 ${c.teamP} 队、它在第 ${c.teamK} 队，${c.enemy ? '敌对' : '不敌对'}；按受捐上限它收得下 ${c.room} 兵）`)
          + `；船主已有对它的进攻 ${c.hasAtk}，有空的进攻栏 ${c.freeSlot}`);
      }
      prev = r;
    }
    const at = (t) => rows.find((r) => r.t === t);
    for (const A of subjects) {
      const k = A.cell.fR;
      const withAtk = [];
      for (let t = A.t + 1; at(t) && at(t).atk.some(([q]) => q === k); t++) withAtk.push(at(t));
      const end = rows[rows.length - 1];
      let kind;
      if (withAtk.length) {
        const first = withAtk[0], last = withAtk[withAtk.length - 1];
        const gone = at(last.t + 1);
        const jump = gone ? gone.d : null;
        kind = jump === null ? '挂成进攻（窗里没看到它消失）' : (jump >= A.troops ? '挂成进攻、找不到可占的格被撤销，兵退回' : '挂成进攻后消失，净额没有涨回来');
        lines.push(`  小结：船（${A.troops} 兵）在 ${A.t} 拍走到头；之后名下出现对 #${k} 的进攻的拍：${withAtk.map((r) => r.t).join(' ')}`
          + `（第一拍这条进攻的兵 ${first.atk.find(([q]) => q === k)[1]}，最后一拍 ${last.atk.find(([q]) => q === k)[1]}）`
          + (gone ? `；进攻消失的那一拍（${gone.t}）净额 ${sg(jump)}（余额 ${last.bal} → ${gone.bal}，欠账 ${last.debt} → ${gone.debt}）` : ''));
        if (gone) {
          // 那一拍的涨幅 = 退回的船兵 + 同一拍别的进账。窗里这个号没有船、没有进攻的拍上净额的变化列出来对照（逢 10 的拍有定期进账）。
          const quiet = rows.filter((r) => r.d && r.t !== gone.t && r.t < A.t - 1 && !r.boats.length && !r.atk.length);
          lines.push(`  对账：这一拍涨的 ${jump} − 船上的 ${A.troops} = ${jump - A.troops}`
            + (quiet.length ? `；窗里这个号名下没有船也没有进攻的拍上，净额的变化：${quiet.map((r) => `${r.t} 拍 ${sg(r.d)}`).join('，')}` : ''));
        }
      } else {
        const next = at(A.t + 1);
        const dk = end.balK !== undefined && A.cell.k3bal !== null ? end.balK - A.cell.k3bal : null;
        kind = dk ? '交给了读出来的那个号' : (next && next.d >= A.troops ? '当拍退回' : (next ? '兵作废' : '窗里看不到下一拍'));
        lines.push(`  小结：船（${A.troops} 兵）在 ${A.t} 拍走到头；之后名下没有出现对 #${k} 的进攻。`
          + `下一拍（${next ? next.t : '–'}）船主净额的变化 ${next ? sg(next.d) : '–'}；`
          + `到窗尾（${end.t} 拍）#${k} 的余额 ${A.cell.k3bal} → ${end.balK}` + (dk === null ? '' : `（${sg(dk)}）`) + `。归类：${kind}`);
      }
      tally.push({ mid, p, t: A.t, troops: A.troops, aae: A.cell.aae, px: A.cell.px, off: A.cell.off, fresh: A.fresh, k, enemy: A.cell.enemy, kTerr: A.cell.k3terr, kind, from: w.from || null });
    }
    if (!subjects.length) lines.push('  小结：窗里没有看到这个号的船走到「不是地」的格上。');
    lines.push('');
  }
}
lines.push('[BP-A] 汇总：船走到头、靠岸要读的那一格不是无主地也不是有主的地的每一艘');
lines.push('  局 | 船主 | 走到头的拍 | 船上的兵 | 发出的当拍就到头 | 船的位置（地图下标）| 要读的那一格（下标）| 读出来的「主人号」 | 和船主 | 那个号的地 | 线上引擎里这笔兵的去向');
for (const r of tally) {
  lines.push(`  ${r.mid} | #${r.p} | ${r.t} | ${r.troops} | ${r.fresh ? '是' : '否'} | ${r.aae} | ${r.px}${r.off ? '（图外）' : ''} | ${r.k} | ${r.enemy ? '敌对' : '不敌对'} | ${r.kTerr} | ${r.kind}`);
}
const byKind = {};
for (const r of tally) byKind[r.kind] = (byKind[r.kind] || 0) + 1;
lines.push(`  合计 ${tally.length} 艘：` + Object.entries(byKind).map(([k, n]) => `${k} ${n} 艘`).join('；')
  + `；其中船的位置是地图下标 0 的 ${tally.filter((r) => r.aae === 0).length} 艘，发出的当拍就到头的 ${tally.filter((r) => r.fresh).length} 艘`);
lines.push('  模拟器的 boats.js landAt（L262-287）：这一格既不是无主地、也没有主人时直接返回，船上的兵不进任何人的账。');
fs.mkdirSync(OUT, { recursive: true });
fs.writeFileSync(path.join(OUT, 'boatprobe.txt'), lines.join('\n') + '\n');
fs.writeFileSync(path.join(OUT, 'boatprobe.json'), JSON.stringify({ windows: J, tally }));
console.log(lines.join('\n'));
