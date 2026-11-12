#!/usr/bin/env node
// v28_shadow.mjs — R07：在「按录像重演出来的真实局面」上运行任意一份策略文件（默认 v28）。两种跑法：
//
// 【影子】（默认）resim 重演 + 每拍结算后对我方每个号各跑一次 act(g)，指令只记不执行。局面永远是录像里的真实局面。
//         用途：语法 / 运行错误、各模块触发次数、「开关全关 ≡ Vc」的逐条比对。
//         局限：指令不执行，所以「发出去之后」的事（在途账本清算、重复下单有没有少）影子模式看不到。
// 【接管】（--takeover T0）从 T0 拍起，录像里我方各号的指令不再执行，改为执行策略自己发的指令，经过一条延迟信道：
//           --chan c0  零延迟（当拍执行）
//           --chan c1  每条指令延迟 d∈[10,18] 拍，向上取整到 7 的倍数那一拍结算；同拍后发先结算；
//                      每号任意连续 3 轮（21 拍）最多结算 9 条，超出的丢弃
//           --stall a-b[:extra]  在 [a,b] 拍之间发出的指令再加 extra 拍延迟（默认 150），模拟滞涩波
//         对手仍按录像发指令（不会对我方的新走法作反应），所以接管只用来核对机制（账本清算、重复下单、滞涩态），
//         不能拿它的地盘 / 兵力结果当胜率证据。
//
// 和 65_shadow.mjs 的区别：策略文件用 --src 给路径（v28 草稿、Vc 原文都行），参数用 --modules / --params 给；
// 不做 Vb 专用的归因诊断；给策略一个可控的钟 window.__c136Now（毫秒 = 拍号 × 56），免得模拟器跑得快被当成「追帧」。
//
// 用法（必须套重计算闸；一次只跑一个）：
//   bash c136-review/tools/run-heavy.sh node c136-review/agents/R07/scripts/v28_shadow.mjs <matchId> \
//        [--src 路径] [--label 名字] [--modules none|all|p1,p3] [--params '{"p8Margin":0.2}'] [--from T0] [--until T1]
//        [--bots a,b|all] [--quit engine|none] [--takeover T0 --chan c0|c1 [--seed N] [--stall a-b[:extra]]]
// 输出：
//   out/v28/<matchId>_<label>.json            （进仓库，小）报错清单、各号指令计数、[V28-*] 日志按标签计数、
//                                              策略对象上的计数器（policy.v28n）、接管模式下的信道统计与期末地盘兵力
//   out/_cache/v28/<matchId>_<label>_cmds.tsv （不进仓库）每条指令：t、号、种类、pct、目标、附加参数
//   out/_cache/v28/<matchId>_<label>_log.txt  （不进仓库）[V28-*] 与 [SHADOW-ERROR] 日志原文
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const DATA = '/agent/repos/c136-data';
const HERE = path.dirname(fileURLToPath(import.meta.url));
const args = process.argv.slice(2);
const mid = args[0];
if (!mid || mid.startsWith('--')) { console.error('用法：v28_shadow.mjs <matchId> [--src 路径] [--label 名字] [--modules …] [--params JSON] [--from T0] [--until T1] [--bots a,b|all] [--takeover T0 --chan c0|c1]'); process.exit(2); }
const opt = (k, d) => { const i = args.indexOf(k); return i >= 0 ? args[i + 1] : d; };
const OUT = path.join(HERE, '..', 'out', 'v28');
const RAW = path.join(HERE, '..', 'out', '_cache', 'v28');
fs.mkdirSync(OUT, { recursive: true });
fs.mkdirSync(RAW, { recursive: true });

const srcPath = path.resolve(opt('--src', path.join(HERE, '..', 'v28', 'v28-team-organism.js')));
const label = opt('--label', path.basename(srcPath).replace(/\.m?js$/, ''));
// --modules none|all|p1,p3,…：模块开关的简写（none = 八个全关 = Vc；p1,p3 = 只开这两个）；--params 里写的优先。
const SWITCH = { p1: 'enableInflightLedger', p2: 'enableSpawnClosedLoop', p3: 'enableAiFloorCap', p4: 'enableCoordinatedStrike', p5: 'enableSmartOverCap', p6: 'enableQuotaExactDonate', p7: 'enableSeaPrecision', p8: 'enableCollapseGuard' };
const modSel = opt('--modules', '');
const modParams = {};
if (modSel && modSel !== 'all') {
  const on = new Set(modSel === 'none' ? [] : modSel.toLowerCase().split(','));
  for (const m of on) if (!SWITCH[m]) { console.error(`--modules 里不认识 ${m}`); process.exit(2); }
  for (const [m, k] of Object.entries(SWITCH)) modParams[k] = on.has(m) ? 1 : 0;
}
const params = { ...modParams, ...JSON.parse(opt('--params', '{}')) };
const from = +opt('--from', 0);
const until = +opt('--until', 1e9);
const quitMode = opt('--quit', 'engine');
const takeFrom = +opt('--takeover', -1);
const chan = opt('--chan', 'c1');
if (takeFrom >= 0 && chan !== 'c0' && chan !== 'c1') { console.error('--chan 只认 c0 / c1'); process.exit(2); }
let rs = (+opt('--seed', 1) * 2654435761) >>> 0;
const rnd = () => (rs = (Math.imul(rs, 1664525) + 1013904223) >>> 0) / 4294967296;
const stallArg = opt('--stall', '');
const stall = stallArg ? (() => { const m = /^(\d+)-(\d+)(?::(\d+))?$/.exec(stallArg); if (!m) { console.error('--stall 写法：a-b[:extra]'); process.exit(2); } return { a: +m[1], b: +m[2], extra: +(m[3] ?? 150) }; })() : null;

let code = fs.readFileSync(srcPath, 'utf8');
const nImp = (code.match(/from "\.\.\/\.\.\/sim\/(index|map)\.js"/g) || []).length;
if (nImp !== 2) { console.error(`策略文件里应当正好有 2 行 ../../sim 的 import，实际 ${nImp} 行`); process.exit(2); }
code = code.replace('from "../../sim/index.js"', `from "${DATA}/src/sim/sim/index.js"`).replace('from "../../sim/map.js"', `from "${DATA}/src/sim/sim/map.js"`);
const cacheDir = path.join(HERE, '..', 'out', '_cache');
fs.mkdirSync(cacheDir, { recursive: true });
const modPath = path.join(cacheDir, `strategy-${label.replace(/[^A-Za-z0-9_.-]/g, '_')}.mjs`);
fs.writeFileSync(modPath, `// 由 v28_shadow.mjs 生成：${srcPath} 原文，只改了 2 行 import 的路径\n` + code);

let curBot = null, curT = 0;
const logs = [];
const tagCount = {};
globalThis.window = {
  __hlLog: (s) => { const text = String(s); if (/^\[(V28|SHADOW)/.test(text)) logs.push({ bot: curBot, t: curT, text }); const m = /^\[([A-Z0-9-]+)\]/.exec(text); if (m) tagCount[m[1]] = (tagCount[m[1]] || 0) + 1; },
  __tsbSquadSlot: 0,
  __c136Now: () => curT * 56,
};

Error.stackTraceLimit = 30;
const SIM = await import(path.join(DATA, 'src/sim/sim/index.js'));
(await import(path.join(HERE, 'r07simfix.mjs'))).applyOddLandingFix(SIM);
const { resim } = await import(path.join(DATA, 'src/tools/resim.mjs'));
const LIB = await import(path.join(DATA, 'src/sim/tools/c102-replay-lib.mjs'));
const STR = await import(pathToFileURL(modPath).href);
const { Policy } = STR;
const { NEUTRAL } = SIM;

const d = LIB.decodeReplay(fs.readFileSync(path.join(DATA, 'bundles', mid, 'replay.txt'), 'utf8'));
const H = d.vu.humanCount;
const names = d.vu.playerNamesData ? Array.from(d.vu.playerNamesData).slice(0, H).map((s) => String(s ?? '')) : [];
const logText = fs.readFileSync(path.join(DATA, 'bundles', mid, 'in_game.log'), 'utf8').split('\n');
const realBots = new Set();
const slotOf = new Map();
for (const ln of logText) {
  const m = /^\d+\t\[([A-Za-z0-9_]+)\] (.*)$/.exec(ln);
  if (!m) continue;
  realBots.add(m[1]);
  const s = /\[HL-SPAWN(?:-BACKEND)?\] me=(\d+) slot=(\d+)/.exec(m[2]);
  if (s) slotOf.set(m[1], +s[2]);
}
const idOf = new Map();
for (const b of realBots) for (let p = 0; p < H; p++) if (names[p].trim().toLowerCase().endsWith(b.toLowerCase())) { idOf.set(b, p); break; }
const botSel = opt('--bots', 'all');
const bots = botSel === 'all' ? [...idOf.keys()] : botSel.split(',');

const pol = new Map();
for (const b of bots) {
  const me = idOf.get(b);
  if (me === undefined) continue;
  pol.set(b, new Policy(params, me));
}
const ourIds = new Set([...pol.values()].map((p) => p.me));

// ---- 接管模式：录像里我方的指令从 takeFrom 起不执行；策略的指令经信道执行 ----
const proto = SIM.Game.prototype;
let injecting = false, suppressed = 0, seq = 0, tookOver = false;
let queue = [];
const execRounds = new Map();
const chanStat = {};
const cs = (b) => (chanStat[b] ??= { issued: 0, attack: 0, dupAttack: 0, dupNeutral: 0, dupBot: 0, dupPerson: 0, executed: 0, failed: 0, dropped: 0, latSum: 0 });
const taking = (g) => takeFrom >= 0 && !g.spawnPhase && g.t >= takeFrom;
if (takeFrom >= 0) {
  const playerArg = { attack: 2, donate: 2, boat: 3, boatTo: 2, chase: 2, recall: 1, retreat: 1, leave: 0 };
  for (const [name, idx] of Object.entries(playerArg)) {
    const orig = proto[name];
    proto[name] = function (...a) {
      if (!injecting && taking(this) && ourIds.has(a[idx])) { suppressed++; return false; }
      return orig.apply(this, a);
    };
  }
}
const flushChannel = (g) => {
  if (!queue.length) return;
  const due = queue.filter((c) => c.due <= g.t).sort((x, y) => y.seq - x.seq);
  if (!due.length) return;
  queue = queue.filter((c) => c.due > g.t);
  for (const c of due) {
    const st = cs(c.b), round = Math.floor(c.due / 7);
    const hist = execRounds.get(c.me) ?? [];
    if (hist.filter((r) => round - r < 3).length >= 9) { st.dropped++; continue; }
    hist.push(round);
    execRounds.set(c.me, hist.slice(-40));
    injecting = true;
    let ok = false;
    try { ok = !!c.call(); } finally { injecting = false; }
    if (ok) { st.executed++; st.latSum += g.t - c.t; } else st.failed++;
  }
};

const cmds = [];
const errors = [];
const quitSet = new Set();
const origTick = proto.tick;
proto.tick = function () {
  origTick.call(this);
  const g = this;
  if (g.spawnPhase || g.over || g.t > until || g.t < from) return;
  if (!g.names) g.names = names;
  if (takeFrom >= 0) flushChannel(g);
  // 接管开始那一拍：之前影子阶段攒下的计数器和在途账本清零（那些指令并没有真的发出去）
  if (takeFrom >= 0 && !tookOver && taking(g)) {
    tookOver = true;
    for (const p of pol.values()) { if (p.v28n) for (const k of Object.keys(p.v28n)) delete p.v28n[k]; if (typeof p.ledgerReset === 'function') p.ledgerReset(); }
    for (const k of Object.keys(tagCount)) delete tagCount[k];
  }
  if (quitMode === 'engine') { for (let q = 0; q < H; q++) if (g.state[q] === 2) quitSet.add(q); window.__quitPlayers = quitSet; }
  const onlineHad = Object.prototype.hasOwnProperty.call(g, 'online');
  const online0 = g.online;
  g.online = true;
  for (const [b, p] of pol) {
    const me = p.me;
    if (!g.alive[me] || g.state[me] === 2) continue;
    curBot = b; curT = g.t;
    window.__tsbSquadSlot = slotOf.has(b) ? slotOf.get(b) : me % 10;
    // 一条指令：先记进指令流；影子模式到此为止，接管模式再交给信道
    const submit = (kind, pct, target, extra, call) => {
      cmds.push([g.t, b, kind, pct, target, extra ?? '']);
      if (!taking(g)) return true;
      const st = cs(b);
      st.issued++;
      if (kind === 'attack') {
        st.attack++;
        // 「重复下单」的地面真值：同一目标的上一条进攻指令还在信道里没结算（按目标分：中立 / 人机与空壳 / 真人）
        if (queue.some((c) => c.me === me && c.kind === 'attack' && c.target === target)) {
          st.dupAttack++;
          if (target >= NEUTRAL) st.dupNeutral++; else if (g.isBot(target)) st.dupBot++; else st.dupPerson++;
        }
      }
      if (chan === 'c0') {
        injecting = true;
        let ok = false;
        try { ok = !!call(); } finally { injecting = false; }
        if (ok) st.executed++; else st.failed++;
        return ok;
      }
      let dly = 10 + Math.floor(rnd() * 9);
      if (stall && g.t >= stall.a && g.t <= stall.b) dly += stall.extra;
      queue.push({ due: Math.ceil((g.t + dly) / 7) * 7, seq: ++seq, b, me, kind, target, call, t: g.t });
      return true;
    };
    g.attack = (pct, target, pl = me) => {
      if (pl !== me) return false;
      const tg = Math.min(target, NEUTRAL);
      if (tg < NEUTRAL && g.alive[tg] && !g.isEnemy(me, tg)) return false;
      if (!g.hasAttack(me, tg < NEUTRAL && !g.alive[tg] ? NEUTRAL : tg) && !g.hasFreeSlot(me)) return false;
      return submit('attack', pct, tg, '', () => proto.attack.call(g, pct, target, me));
    };
    g.donate = (pct, q, pl = me) => { if (pl !== me || !g.alive[q] || !g.isTeammate(me, q)) return false; return submit('donate', pct, q, '', () => proto.donate.call(g, pct, q, me)); };
    g.boat = (pct, water, dir, pl = me) => { if (!g.boatsAllowed(me)) return false; return submit('boat', pct, water, dir, () => proto.boat.call(g, pct, water, dir, me)); };
    g.boatTo = (pct, target, pl = me, radius = 32) => { if (!g.boatsAllowed(me)) return false; return submit('boatTo', pct, target, radius, () => proto.boatTo.call(g, pct, target, me, radius)); };
    g.chase = (pct, id, pl = me) => submit('chase', pct, NEUTRAL, id, () => proto.chase.call(g, pct, id, me));
    g.recall = (id, pl = me) => submit('recall', 0, NEUTRAL, id, () => proto.recall.call(g, id, me));
    g.retreat = (target, pl = me) => submit('retreat', 0, Math.min(target, NEUTRAL), '', () => proto.retreat.call(g, target, me));
    try { p.act(g); } catch (e) {
      const where = String((e && e.stack) || '').split('\n').slice(1, 4).map((s) => s.trim().replace(/\(?file:\/\/\S*strategy-[^:]+\.mjs:(\d+):\d+\)?/, (_, ln) => `L${+ln - 1}`)).join(' < ');
      errors.push({ t: g.t, bot: b, msg: String(e && e.message), where });
      logs.push({ bot: b, t: g.t, text: `[SHADOW-ERROR] ${e && e.message} @ ${where}` });
    }
    delete g.attack; delete g.donate; delete g.boat; delete g.boatTo; delete g.chase; delete g.recall; delete g.retreat;
  }
  if (onlineHad) g.online = online0; else delete g.online;
  if (takeFrom >= 0 && (g.t === takeFrom || g.t % 100 === 0)) noteTraj(g);
  lastG = g;
};
let lastG = null;
const traj = [];
const noteTraj = (g) => {
  let land = 0, troops = 0, alive = 0;
  for (const me of ourIds) { if (g.alive[me] && g.state[me] !== 2) { alive++; land += g.terr[me]; troops += g.bal[me]; } }
  traj.push([g.t, alive, land, troops]);
};

const t0 = Date.now();
const out = resim(mid, { until: Number.isFinite(until) ? until : undefined });
proto.tick = origTick;
const v = out.validate;

fs.writeFileSync(path.join(RAW, `${mid}_${label}_cmds.tsv`), 't\tbot\tkind\tpct\ttarget\textra\n' + cmds.map((c) => c.join('\t')).join('\n') + '\n');
const kinds = {};
for (const c of cmds) { const k = `${c[2]}`; kinds[k] = (kinds[k] || 0) + 1; }
const perBot = {};
for (const c of cmds) { perBot[c[1]] = perBot[c[1]] || {}; perBot[c[1]][c[2]] = (perBot[c[1]][c[2]] || 0) + 1; }
const stats = {};
const statSum = {};
for (const [b, p] of pol) {
  if (p.v28n && typeof p.v28n === 'object') {
    stats[b] = { ...p.v28n };
    for (const [k, n] of Object.entries(p.v28n)) statSum[k] = k.endsWith('_max') ? Math.max(statSum[k] || 0, n) : (statSum[k] || 0) + n;
  }
}
const summary = {
  matchId: mid, src: srcPath, label, params, from, until: Number.isFinite(until) && until < 1e9 ? until : null,
  endTick: out.endTick, seconds: +((Date.now() - t0) / 1000).toFixed(1),
  replayCheck: { rows: v.rows, terrExact: v.terrExact, balExact: v.balExact, bothExact: v.bothExact },
  bots: [...pol.keys()], cmds: cmds.length, kinds, perBot,
  errors: errors.length, errorList: errors.slice(0, 40),
  logTags: tagCount, v28Counters: statSum, v28CountersPerBot: stats,
};
if (takeFrom >= 0) {
  const tot = { issued: 0, attack: 0, dupAttack: 0, dupNeutral: 0, dupBot: 0, dupPerson: 0, executed: 0, failed: 0, dropped: 0, latSum: 0 };
  for (const s of Object.values(chanStat)) for (const k of Object.keys(tot)) tot[k] += s[k];
  if (lastG) noteTraj(lastG);
  summary.takeover = {
    from: takeFrom, chan, seed: +opt('--seed', 1), stall, suppressedRecorded: suppressed, stillInChannel: queue.length,
    total: tot, dupAttackShare: tot.attack ? +(tot.dupAttack / tot.attack).toFixed(4) : null,
    meanLatency: tot.executed ? +(tot.latSum / tot.executed).toFixed(2) : null,
    perBot: chanStat, trajectory_t_alive_land_troops: traj,
  };
}
fs.writeFileSync(path.join(OUT, `${mid}_${label}.json`), JSON.stringify(summary, null, 1) + '\n');
fs.writeFileSync(path.join(RAW, `${mid}_${label}_log.txt`), logs.map((l) => `${l.t}\t[${l.bot}] ${l.text}`).join('\n') + '\n');
console.log(`${mid} ${label}: 重演 ${out.endTick} 拍 ${summary.seconds}s；快照核对 ${v.bothExact}/${v.rows}；指令 ${cmds.length}（${Object.entries(kinds).map(([k, n]) => `${k}×${n}`).join(' ')}）；报错 ${errors.length}`);
if (errors.length) for (const e of errors.slice(0, 5)) console.log(`  报错 t=${e.t} ${e.bot}: ${e.msg} @ ${e.where}`);
const vt = Object.entries(tagCount).filter(([k]) => k.startsWith('V28')).map(([k, n]) => `${k}×${n}`).join(' ');
if (vt) console.log(`  [V28-*] 日志：${vt}`);
if (Object.keys(statSum).length) console.log(`  v28 计数器：${Object.entries(statSum).sort().map(([k, n]) => `${k}=${n}`).join(' ')}`);
if (summary.takeover) {
  const k = summary.takeover, tt = k.total;
  console.log(`  接管 t≥${k.from} 信道 ${k.chan}：发出 ${tt.issued}（进攻 ${tt.attack}，其中重复下单 ${tt.dupAttack} = ${k.dupAttackShare === null ? '-' : (100 * k.dupAttackShare).toFixed(1) + '%'}：中立 ${tt.dupNeutral} / 人机 ${tt.dupBot} / 真人 ${tt.dupPerson}）；结算 ${tt.executed}，结算时无效 ${tt.failed}，超限丢弃 ${tt.dropped}，仍在途 ${k.stillInChannel}；平均延迟 ${k.meanLatency ?? '-'} 拍；录像里我方指令被屏蔽 ${k.suppressedRecorded} 条`);
  const last = traj[traj.length - 1];
  if (last) console.log(`  期末 t=${last[0]}：我方存活 ${last[1]} 号，地 ${last[2]}，兵 ${last[3]}`);
}
