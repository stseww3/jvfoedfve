// engine_replay.cjs — 用线上客户端原文（live_game_js.js）按录像逐拍重放一局，
// 并和我方日志快照（traj.csv 的 [HL-TICK] 行）逐点对账。
//
// 用法：
//   node scripts/engine_replay.cjs <局号> [--until T] [--dump out.tsv] [--every N] [--quiet]
//     --until T   只重放到第 T 拍
//     --dump f    每 N 拍把全场所有活着的真人 + 我方号的 领土/余额 写成 TSV（列：t p name terr bal alive state）
//     --every N   dump 的采样间隔（默认 90）
//
// 规则全部来自线上原文；这里只做两件事：
//   1) 给录像播放器（af9）开一个口子 __step()，直接调用它自己的私有函数 afG()（一步 = 喂本步指令 + 结算一拍）；
//   2) 读引擎自己的状态数组（ah.hN 领土、ah.hb 余额、ah.nU 是否在场、ah.a6S 状态）。
const fs = require('fs');
const path = require('path');
const { createHost } = require('./engine_host.cjs');

const DATA = '/agent/repos/c136-data/bundles';

function patchSource(src) {
  const a = 'this.af1=0;this.dk=function(){afA=0;afB=0;afC=0;aK3=0;afD=0};this.ee=function(){i.ee();if(bF.aBm()<1.7)';
  if (src.split(a).length !== 2) throw new Error('补口子的锚点不唯一或找不到（引擎版本变了？）');
  return src.replace(a, 'this.__step=function(){afG()};this.__pos=function(){return [afA,afB,afC,aK3,afD]};' + a);
}

function startReplay(mid, opts = {}) {
  const h = createHost({ patch: patchSource, echo: opts.echo });
  h.run('bx(true)');
  h.flushTimers();
  h.ctx.__rep = fs.readFileSync(path.join(DATA, mid, 'replay.txt'), 'utf8').trim();
  if (!h.run('bC.aMU.zS(window.__rep)')) throw new Error('录像解不开：' + h.log.slice(-3).join(' | '));
  h.run('bC.aVq()');
  h.flushTimers();
  const info = JSON.parse(h.run('JSON.stringify({ku:aE.ku, players:aE.a0E, ke:aE.ke, w:bV.fk, h:bV.fl, map:bV.fF, teams:aE.a0L, spawnSteps:aE.a7a, hx:aE.hx, a38:aE.a38})'));
  // 一步到位的步进函数放在引擎上下文里，避免每拍跨上下文编译
  // 步进与取数函数在引擎作用域里建一次，之后直接调用
  const api = h.run(`({
    advance: function (n) { // 连续走 n 步；返回 [拍号, 是否还在出生阶段, 游戏状态]
      var st = bi.a3I;
      for (var k = 0; k < n; k++) { if (aE.a38 === 2) break; st.__step(); }
      return [bi.kr(), aE.hx ? 1 : 0, aE.a38];
    },
    names: function () { var r = []; for (var p = 0; p < aE.a0E; p++) r.push(ah.a3o[p]); return r; },
    snap: function (ids) { var r = []; for (var k = 0; k < ids.length; k++) { var p = ids[k]; r.push(ah.hN[p], ah.hb[p], ah.nU[p], ah.a6S[p]); } return r; }
  })`);
  return { h, info, api };
}

function loadCsv(file) {
  if (!fs.existsSync(file)) return [];
  const lines = fs.readFileSync(file, 'utf8').split('\n').filter(Boolean);
  const head = lines[0].split(',');
  return lines.slice(1).map((l) => { const c = l.split(','); const o = {}; head.forEach((k, i) => { o[k] = c[i]; }); return o; });
}

module.exports = { startReplay, patchSource, loadCsv, DATA };

if (require.main === module) {
  const args = process.argv.slice(2);
  const mid = args[0];
  const opt = (k, d) => { const i = args.indexOf(k); return i >= 0 ? args[i + 1] : d; };
  const until = +opt('--until', 1e9);
  const dump = opt('--dump', null);
  const every = +opt('--every', 90);
  const quiet = args.includes('--quiet');
  const t0 = Date.now();
  const { h, info, api } = startReplay(mid);
  const names = api.names();
  // 我方号：名字与 traj.csv 的 bot 对上的真人
  const traj = loadCsv(path.join(DATA, mid, 'traj.csv'));
  const bots = [...new Set(traj.map((r) => r.bot))];
  const idOf = new Map();
  for (let p = 0; p < info.ku; p++) for (const b of bots) if (names[p] === b || names[p] === '[APEX] ' + b || (names[p] || '').endsWith(' ' + b)) idOf.set(b, p);
  const snapsAt = new Map();
  for (const r of traj) { if (!idOf.has(r.bot)) continue; const t = +r.t; if (!snapsAt.has(t)) snapsAt.set(t, []); snapsAt.get(t).push(r); }
  const humans = []; for (let p = 0; p < info.ku; p++) humans.push(p);
  console.log(`# ${mid} 真引擎重放：真人 ${info.ku}，全部玩家 ${info.players}，地图 ${info.map}（${info.w}x${info.h}，陆地 ${info.ke}），队数 ${info.teams}`);
  console.log(`# 我方对上名字的号：${[...idOf].map(([b, p]) => `${b}=${p}`).join(' ')}`);
  let out = dump ? ['t\tp\tname\tterr\tbal\talive\tstate'] : null;
  let exact = 0, total = 0, firstBad = null, lastT = -1, spawnDone = false, steps = 0;
  const bad = [];
  const deadline = t0 + 100000;
  while (true) {
    const [t, hx, st] = api.advance(1);
    steps++;
    if (hx) continue;
    if (!spawnDone) { spawnDone = true; if (!quiet) console.log(`# 出生阶段结束：共 ${steps} 步，此时拍号 ${t}`); }
    if (t === lastT) { if (st === 2) break; continue; }
    lastT = t;
    if (snapsAt.has(t)) {
      const s = api.snap(humans);
      for (const r of snapsAt.get(t)) {
        const p = idOf.get(r.bot); total++;
        const terr = s[p * 4], bal = s[p * 4 + 1];
        if (terr === +r.terr && bal === +r.bal) exact++;
        else { if (firstBad === null) firstBad = t; if (bad.length < 12) bad.push(`t=${t} ${r.bot}: 日志 领土 ${r.terr} 余额 ${r.bal} | 引擎 领土 ${terr} 余额 ${bal}`); }
      }
    }
    if (out && t % every === 0) {
      const s = api.snap(humans);
      for (const p of humans) out.push([t, p, names[p], s[p * 4], s[p * 4 + 1], s[p * 4 + 2], s[p * 4 + 3]].join('\t'));
    }
    if (t >= until || st === 2) break;
    if (Date.now() > deadline) { console.log(`# 时间到，停在第 ${t} 拍`); break; }
  }
  console.log(`# 重放到第 ${lastT} 拍，用时 ${((Date.now() - t0) / 1000).toFixed(1)} 秒`);
  console.log(`# 与日志快照对账：${total} 个点，领土和余额都完全一致 ${exact} 个（${total ? (100 * exact / total).toFixed(1) : '0'}%）；首个不一致拍 ${firstBad === null ? '无' : firstBad}`);
  for (const b of bad) console.log('#   ' + b);
  const errs = h.log.filter((l) => /ERR|error|Error/.test(l));
  if (errs.length) console.log('# 引擎自己报的错：' + errs.slice(0, 5).join(' | '));
  if (out) { fs.mkdirSync(path.dirname(dump), { recursive: true }); fs.writeFileSync(dump, out.join('\n') + '\n'); console.log(`# 已写 ${dump}（${out.length - 1} 行）`); }
}
