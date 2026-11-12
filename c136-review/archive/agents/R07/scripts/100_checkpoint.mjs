#!/usr/bin/env node
// 100_checkpoint.mjs — R07：历史断面上的离线通道对照（任务卡 0002；纯离线）。
//
// 只跑历史原策略：/agent/repos/c136-data/src/strategy/ 里的 v27-team-c116-va.js（Va）和 v27-team-c116-vb.js（Vb），
// 原文不改（只把两行 import 换成绝对路径），不改任何参数，不含任何新的决策代码。本脚本只做三件事：
//   1) 用统筹的干净模拟器（src/tools/resim.mjs）把 replay.txt 从头重演到断面 T0；重演期间让历史策略在真实局面上影子运行
//      （指令只记不执行），这样到 T0 时每个号的策略记忆和真号当时一致（与 65_shadow.mjs 同一做法）。
//   2) 从 T0 起，录像里我方号的指令不再执行，改由影子策略的指令经过一个「通道」后执行；别的真人仍按录像里的指令重放
//      （不会对我方的变化做出反应，这是本方法最大的限制，报告里有分歧指标）。
//   3) 每 30 拍记一次我方 / 其他真人的地和兵，以及通道里每条指令的去向。
//
// 通道（--chan）：
//   H    不接管：全部按录像（基线；同时输出影子发令和录像落地，给 101_release_map.py 对齐用）
//   C0   零延迟：策略的指令当拍直接交给引擎，返回值是引擎的真实结果，一拍可以多条
//   C0b  零延迟 + 桥接语义：当拍执行，但一个决策拍只受理第一条、返回值照桥接（见下）
//   C1   基础延迟：桥接语义；发令拍 t → 落地拍 ⌈(t+d)/7⌉×7。d 的默认取法（--dmodel emp）照 10 局 0~600 拍的实测在途拍数
//        （791 条：7~14 拍占 85%，均值 11.9，尾巴到 35）：d = 7 或 8 各一半，另有 10% 的指令再加 7 / 14 / 21 拍（6% / 2.5% / 1.5%）；
//        --dmodel uni 时 d 在 [--dmin, --dmax] 里均匀抽（敏感性用）。
//        每个席位连续 3 个回合最多落 9 条（多的丢掉，留先发的）；同一帧同一个号后发的先执行
//   C2   历史实录：C1 的桥接语义和上限，但每条指令的去向取这一局这个号在录像里的实际轨迹
//        （101_release_map.py 把录像落地和影子发令逐条对齐得到 out/<局>/release_map.json）：
//          · 发令拍落在某个「成批放行且后面有指令没落地」的段里 → 这一段里先发的 n 条在历史落地拍落地，其余丢掉；
//          · 其余时候 → 按发令拍最近的那条历史指令的在途拍数落地。
// 一帧之内的先后（引擎按指令执行的先后排扩张顺序，同一帧里谁先谁后会影响抢同一块地的结果）：
//   C2：这个号历史上在这一帧有指令 → 注入的指令放在它历史上的原位置；
//   C1、以及 C2 里历史上这一帧没有这个号的指令时 → 每个号每帧掷一次，一半排在这一帧录像指令之前，一半排在之后；
//   C0 / C0b 在策略决策那一刻执行（排在这一帧录像指令之前）。
// 桥接语义（与 65_shadow.mjs 的影子相同；11 局录像里我方落地的指令 97% 以上能和它逐条对上，见 release_map 的统计）：
//   进攻：目标是活着的队友 → 假；没有空槽且不是加兵 → 假；否则真。捐款：对方活着且是队友 → 真（被配额拒掉也是真，
//   按发令拍的盘面查，过不了就不进通道）。船：不能出船 → 假。一个决策拍里第一条返回真的指令之后，其余都返回假。
// 席位离开：录像里我方号的「离开」照旧执行（当作外生）；只有当历史上这个号在离开前已经死了、而这里还活着时不执行。
// 随机：--seed k>0 时在接管那一拍让引擎的随机数多走 k 步（内置 AI 之后的随机行为整体换一条序列），
//        C1 的延迟也用 k 做种子。k=0 不扰动。
//
// 用法（必须套重计算闸）：
//   bash c136-review/tools/run-heavy.sh node c136-review/agents/R07/scripts/100_checkpoint.mjs <局> --chan H
//   bash c136-review/tools/run-heavy.sh node c136-review/agents/R07/scripts/100_checkpoint.mjs <局> --chan C0|C0b|C1|C2 --t0 630 [--h 900] [--seed 0]
//        [--ver native|va|vb] [--dmodel emp|uni --dmin 5 --dmax 12] [--keep earliest|latest] [--leave hist|none] [--tag 名字]
//   同一进程连跑多条：把各条的参数用 +++ 隔开（每条都从录像第 0 拍重演，互不影响）；超出时间预算的留给下一次。
// 输出：out/_cache/cp/<局>/<名字>.json（不进 git；汇总表由 103_cp_table.py 生成，批量运行见 102_cp_plan.py / 102_cp_batch.sh）
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const DATA = '/agent/repos/c136-data';
const HERE = path.dirname(fileURLToPath(import.meta.url));
globalThis.window = { __hlLog: () => {}, __tsbSquadSlot: 0 };
const SIM = await import(path.join(DATA, 'src/sim/sim/index.js'));
(await import(path.join(HERE, 'r07simfix.mjs'))).applyOddLandingFix(SIM);
const { resim } = await import(path.join(DATA, 'src/tools/resim.mjs'));
const LIB = await import(path.join(DATA, 'src/sim/tools/c102-replay-lib.mjs'));
const { NEUTRAL, iV } = SIM;
const jsonCache = new Map();   // 同一进程里连跑多条时，基线和轨迹文件只读一次
const readJson = (p) => { if (!jsonCache.has(p)) jsonCache.set(p, JSON.parse(fs.readFileSync(p, 'utf8'))); return jsonCache.get(p); };

// 一条运行。同一进程可以连跑多条（命令行里用 +++ 隔开），每条都是全新的策略实例、全新的 window、从录像第 0 拍重演。
async function runOne(args) {
const mid = args[0];
if (!mid || mid.startsWith('--')) { console.error('用法：100_checkpoint.mjs <局> --chan H|C0|C0b|C1|C2 [--t0 T] [--h 900] [--seed k] [--ver native|va|vb]'); process.exit(2); }
const opt = (k, d) => { const i = args.indexOf(k); return i >= 0 ? args[i + 1] : d; };
const chan = opt('--chan', 'H');
if (!['H', 'C0', 'C0b', 'C1', 'C2'].includes(chan)) { console.error(`未知通道 ${chan}`); process.exit(2); }
const T0 = +opt('--t0', chan === 'H' ? -1 : 0);
const seed = +opt('--seed', 0);
const horizon = +opt('--h', 900);
const dmodel = opt('--dmodel', 'emp');
const dmin = +opt('--dmin', 5), dmax = +opt('--dmax', 12);
const keepMode = opt('--keep', 'earliest');
const leaveMode = opt('--leave', 'hist');
const verOpt = opt('--ver', 'native');
const until = chan === 'H' && T0 < 0 ? +opt('--until', 1e9) : T0 + horizon;

const num = +mid.slice(1);
const nativeVer = mid[0] === 'A' ? (num <= 17 ? 'va' : num <= 95 ? 'vb' : 'vc') : null;
const ver = verOpt === 'native' ? nativeVer : verOpt;
if (ver !== 'va' && ver !== 'vb') { console.error(`本脚本只跑历史原策略 Va / Vb；${mid} 的版本是 ${ver}`); process.exit(2); }
const SRC = { va: 'v27-team-c116-va.js', vb: 'v27-team-c116-vb.js' }[ver];

const CACHE = path.join(HERE, '..', 'out', '_cache');
const CPDIR = path.join(CACHE, 'cp', mid);
fs.mkdirSync(CPDIR, { recursive: true });
const defTag = chan === 'H' && T0 < 0 ? 'H'
  : `${chan}-t${T0}-s${seed}${ver !== nativeVer ? '-' + ver : ''}${chan === 'C1' && dmodel === 'uni' ? `-d${dmin}_${dmax}` : ''}${keepMode !== 'earliest' ? '-kl' : ''}${leaveMode !== 'hist' ? '-nl' : ''}`;
const tag = opt('--tag', defTag);
const outPath = path.join(CPDIR, `${tag}.json`);

// ---- 历史策略源码：原文，只换两行 import 的路径
const srcPath = path.join(DATA, 'src/strategy', SRC);
let code = fs.readFileSync(srcPath, 'utf8');
const nImp = (code.match(/from "\.\.\/\.\.\/sim\/(index|map)\.js"/g) || []).length;
code = code.replace('from "../../sim/index.js"', `from "${DATA}/src/sim/sim/index.js"`).replace('from "../../sim/map.js"', `from "${DATA}/src/sim/sim/map.js"`);
const modPath = path.join(CACHE, `strategy-${ver}.mjs`);
const modText = `// 由 R07 的脚本生成：${SRC} 原文，只改了 ${nImp} 行 import 的路径\n` + code;
if (!fs.existsSync(modPath) || fs.readFileSync(modPath, 'utf8').length !== modText.length) fs.writeFileSync(modPath, modText);

globalThis.window = { __hlLog: () => {}, __tsbSquadSlot: 0 };
const { Policy } = await import(pathToFileURL(modPath).href);

// ---- 我方号
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
for (const b of [...realBots].sort()) for (let p = 0; p < H; p++) if (names[p].trim().toLowerCase().endsWith(b.toLowerCase())) { idOf.set(b, p); break; }
const botOf = new Map([...idOf].map(([b, p]) => [p, b]));
const isSquad = new Uint8Array(512);
for (const p of idOf.values()) isSquad[p] = 1;

// ---- 基线（H.json）：历史上的死亡拍、别的真人每条指令的结果；C2 另读 release_map.json
const hPath = path.join(CPDIR, 'H.json');
const HB = chan !== 'H' || T0 >= 0 ? (fs.existsSync(hPath) ? readJson(hPath) : null) : null;
if (chan !== 'H' && !HB) { console.error(`先跑 --chan H 生成 ${hPath}`); process.exit(2); }
let RMAP = null;
if (chan === 'C2') {
  const rp = path.join(HERE, '..', 'out', mid, 'release_map.json');
  if (!fs.existsSync(rp)) { console.error(`先跑 101_release_map.py ${mid} 生成 ${rp}`); process.exit(2); }
  RMAP = readJson(rp);
}

// ---- 随机数（只给 C1 的延迟用）
let rs = (Math.imul(seed + 1, 2654435761) ^ Math.imul(T0 + 7, 40503) ^ Math.imul(num, 97)) >>> 0;
const rnd = () => (rs = (Math.imul(rs, 1664525) + 1013904223) >>> 0) / 4294967296;

// ---- 策略实例
const pol = new Map();
for (const [b, me] of idOf) pol.set(b, new Policy({}, me));

// ---- 引擎钩子
const proto = SIM.Game.prototype;
const origM = {};
const playerArg = { attack: 2, donate: 2, boat: 3, boatTo: 2, chase: 2, recall: 1, retreat: 1 };
let injecting = false, live = false, suppressed = 0, leaveSkipped = 0;
for (const [name, idx] of Object.entries(playerArg)) {
  const orig = proto[name];
  origM[name] = orig;
  proto[name] = function (...a) {
    if (!injecting && live) {
      const pl = a[idx] === undefined ? this.me : a[idx];
      if (isSquad[pl]) { suppressed++; onRecordedCall(this, pl); return false; }
    }
    return orig.apply(this, a);
  };
}
origM.leave = proto.leave;
proto.leave = function (p) {
  if (live && isSquad[p] && this.alive[p]) {
    const hd = HB && HB.deathT ? HB.deathT[p] : -1;
    if (leaveMode === 'none' || (hd >= 0 && hd <= this.t)) { leaveSkipped++; return; }
  }
  return origM.leave.call(this, p);
};

// ---- 通道
const queue = [];
let seqNo = 0;
const landRounds = new Map();   // me → 最近落地的回合号（给 3 回合 9 条的上限用）
const cmdRec = [];              // 接管后我方每条指令：[发令拍, 号, kind, pct, 目标, 发令时目标类别, 落地拍(-1=丢), 生效, 兵, 手续费, 落地时目标类别, 丢弃原因]
const intents = [];             // 影子阶段的发令（H 用）：[拍, 号, kind, pct, 目标, 捐款发令时是否会被拒]
const chanStat = { issued: 0, second: 0, donRej: 0, capDrop: 0, mapDrop: 0, landed: 0, landedOk: 0, inflight: 0, discarded: 0 };
const clsOf = (g, q) => (q >= NEUTRAL ? 'N' : q >= H || g.state[q] === 2 ? 'A' : isSquad[q] ? 'S' : g.teams && g.teams[q] === squadTeam ? 'M' : 'E');
let squadTeam = -1;

// C2：每个号的历史轨迹
const segOf = new Map();    // bot → {segs:[{a, b, T, n}], pts:[[s, lag]]}
const segUsed = new Map();  // bot → Map(seg 下标 → 已用条数)
let poolPts = [];
if (RMAP) {
  for (const [b, r] of Object.entries(RMAP.seats)) { segOf.set(b, r); segUsed.set(b, new Map()); }
  poolPts = RMAP.pool || [];
}
const nearestLag = (pts, t) => {
  if (!pts || !pts.length) return null;
  let lo = 0, hi = pts.length - 1;
  while (lo < hi) { const m = (lo + hi) >> 1; if (pts[m][0] < t) lo = m + 1; else hi = m; }
  let best = pts[lo];
  if (lo > 0 && Math.abs(pts[lo - 1][0] - t) <= Math.abs(best[0] - t)) best = pts[lo - 1];
  return best;
};
const dueOf = (b, t) => {
  if (chan === 'C1') {
    let dl;
    if (dmodel === 'uni') dl = dmin + Math.floor(rnd() * (dmax - dmin + 1));
    else {
      dl = rnd() < 0.5 ? 7 : 8;
      const u = rnd();
      if (u < 0.10) dl += 7 * (u < 0.06 ? 1 : u < 0.085 ? 2 : 3);
    }
    return { due: Math.ceil((t + dl) / 7) * 7 };
  }
  // C2
  const r = segOf.get(b);
  if (r) {
    const segs = r.segs;
    for (let i = 0; i < segs.length; i++) {
      const s = segs[i];
      if (t < s.a) break;
      if (t >= s.a && t < s.b) {
        const used = segUsed.get(b);
        const u = used.get(i) || 0;
        if (u >= s.n || s.T < t + 1) return { drop: 'map' };
        used.set(i, u + 1);
        return { due: s.T };
      }
    }
    const nn = nearestLag(r.pts, t);
    if (nn && Math.abs(nn[0] - t) <= 300) return { due: Math.ceil((t + Math.max(5, nn[1])) / 7) * 7 };
  }
  const pn = nearestLag(poolPts, t);
  const lag = pn && Math.abs(pn[0] - t) <= 300 ? Math.max(5, pn[1]) : 11;
  return { due: Math.ceil((t + lag) / 7) * 7 };
};

const execNow = (g, c) => {
  const me = c.me;
  const B0 = g.bal[me];
  let ok = false;
  injecting = true;
  try {
    if (c.kind === 'attack') ok = origM.attack.call(g, c.pct, c.target, me);
    else if (c.kind === 'donate') ok = origM.donate.call(g, c.pct, c.target, me);
    else if (c.kind === 'boat') ok = origM.boat.call(g, c.pct, c.water, c.dir, me);
    else if (c.kind === 'chase') ok = origM.chase.call(g, c.pct, c.target, me);
    else if (c.kind === 'recall') ok = origM.recall.call(g, c.target, me);
    else if (c.kind === 'retreat') ok = origM.retreat.call(g, c.target, me);
  } finally { injecting = false; }
  const spent = B0 - g.bal[me];
  let troops = 0, fee = 0;
  if (ok && (c.kind === 'attack' || c.kind === 'boat')) { troops = g.attackTroopsTmp; fee = g.attackFeeTmp; }
  else if (ok && c.kind === 'donate') { fee = iV(64 * B0, 1024); troops = spent - fee; }
  return { ok: !!ok, troops, fee };
};

// 一帧之内的先后（引擎按指令执行的先后排扩张顺序，同一帧里谁先谁后会影响抢同一块地的结果）：
//   C2：这个号历史上在这一帧有指令 → 注入的指令放在它历史上的原位置（第 k 次录像调用换成第 k 条；最后一次把剩下的都执行掉）
//   其余（C1，以及 C2 里历史上这一帧没有这个号的指令）：每个号每帧掷一次，一半排在这一帧录像指令之前，一半排在之后
const histCalls = new Map();   // 拍 → Map(号 → 历史上这一帧的指令条数)
if (chan === 'C2' && HB && HB.landed) {
  const CALLS = new Set(['attack', 'donate', 'boat', 'chase', 'recall', 'retreat']);
  for (const r of HB.landed) {
    if (!CALLS.has(r[2]) || (r[2] === 'retreat' && r[3] === 513)) continue;
    const me = idOf.get(r[1]);
    if (!histCalls.has(r[0])) histCalls.set(r[0], new Map());
    const m = histCalls.get(r[0]);
    m.set(me, (m.get(me) || 0) + 1);
  }
}
let rs2 = (Math.imul(seed + 3, 40503) ^ Math.imul(T0 + 11, 2654435761) ^ Math.imul(num, 131)) >>> 0;
const rnd2 = () => (rs2 = (Math.imul(rs2, 1664525) + 1013904223) >>> 0) / 4294967296;
const held = new Map();        // 号 → 等着在历史原位置执行的指令（按发令先后；从尾部取）
const callsLeft = new Map();   // 号 → 这一帧历史上还剩几次调用
const afterList = [];          // 排在这一帧录像指令之后执行的各组指令
let posStat = { hist: 0, before: 0, after: 0, late: 0 };
const execOne = (g, c) => {
  const cls1 = c.kind === 'attack' ? clsOf(g, c.target < NEUTRAL && !g.alive[c.target] ? NEUTRAL : c.target) : c.kind === 'donate' ? clsOf(g, c.target) : '-';
  const r = execNow(g, c);
  chanStat.landed++; if (r.ok) chanStat.landedOk++;
  c.rec[6] = g.t; c.rec[7] = r.ok ? 1 : 0; c.rec[8] = r.troops; c.rec[9] = r.fee; c.rec[10] = cls1;
};
const execAll = (g, list) => { while (list.length) execOne(g, list.pop()); };
function onRecordedCall(g, me) {
  const list = held.get(me);
  if (!list) return;
  const left = (callsLeft.get(me) || 1) - 1;
  callsLeft.set(me, left);
  if (left <= 0) { execAll(g, list); held.delete(me); } else if (list.length) execOne(g, list.pop());
}
const afterFrame = (g) => {
  if (held.size) { for (const list of held.values()) { posStat.late += list.length; execAll(g, list); } held.clear(); }
  if (afterList.length) { for (const list of afterList) execAll(g, list); afterList.length = 0; }
};

const flush = (g) => {
  if (!queue.length) return;
  const due = [];
  for (let i = queue.length - 1; i >= 0; i--) if (queue[i].due <= g.t) { due.push(queue[i]); queue.splice(i, 1); }
  if (!due.length) return;
  // 同一个号里后发的先执行；上限留先发的（--keep latest 时留后发的）
  const bySeat = new Map();
  for (const c of due) { if (!bySeat.has(c.me)) bySeat.set(c.me, []); bySeat.get(c.me).push(c); }
  const round = Math.floor(g.t / 7);
  const hc = histCalls.get(g.t);
  for (const me of [...bySeat.keys()].sort((a, b) => a - b)) {
    const list = bySeat.get(me).sort((x, y) => x.seq - y.seq);
    if (!live) { chanStat.discarded += list.length; continue; }
    const hist = (landRounds.get(me) || []).filter((r) => round - r < 3);
    const room = Math.max(0, 9 - hist.length);
    const kept = keepMode === 'latest' ? list.slice(Math.max(0, list.length - room)) : list.slice(0, room);
    const keptSet = new Set(kept);
    for (const c of list) if (!keptSet.has(c)) { chanStat.capDrop++; c.rec[6] = -1; c.rec[11] = 'cap'; }
    for (let i = 0; i < kept.length; i++) hist.push(round);
    landRounds.set(me, hist);
    if (!kept.length) continue;
    const n = hc ? hc.get(me) || 0 : 0;
    if (n > 0) { held.set(me, kept); callsLeft.set(me, n); posStat.hist += kept.length; }
    else if (rnd2() < 0.5) { posStat.before += kept.length; execAll(g, kept); }
    else { posStat.after += kept.length; afterList.push(kept); }
  }
};

// ---- 快照
const snaps = [];
const wantSnap = new Set([630, 1500, 4284, T0]);
const squadIds = [...idOf.values()];
const takeSnap = (g) => {
  let LS = 0, LO = 0, BS = 0, BO = 0, aS = 0, aO = 0, outS = 0, LM = 0, LE = 0;
  for (let p = 0; p < H; p++) {
    const L = g.alive[p] ? g.terr[p] : 0, B = g.alive[p] ? g.bal[p] : 0;
    const act = g.alive[p] && g.state[p] !== 2;
    if (isSquad[p]) { LS += L; BS += B; if (act) aS++; if (g.alive[p]) outS += g.totalAttackTroops(p); }
    else { LO += L; BO += B; if (act) aO++; if (g.teams && g.teams[p] === squadTeam) LM += L; else LE += L; }
  }
  const tl = g.teamGame ? Array.from(g.teamLands()) : [];
  let botL = 0;
  for (let i = g.aliveCount - 1; i >= 0; i--) { const p = g.aliveList[i]; if (p >= H) botL += g.terr[p]; }
  snaps.push({ t: g.t, LS, LO, BS, BO, aS, aO, outS, LM, LE, tl, botL, seat: squadIds.map((p) => (g.alive[p] ? g.terr[p] : 0)), seatB: squadIds.map((p) => (g.alive[p] ? g.bal[p] : 0)), seatSt: squadIds.map((p) => (!g.alive[p] ? 0 : g.state[p] === 2 ? 2 : 1)) });
};

// ---- 每拍：先跑策略，再结算到期的指令
const quitSet = new Set();
const origTick = proto.tick;
let gRef = null, perturbed = false, errCount = 0, firstErr = null, n0S = -1, n0O = -1;
const deathAll = new Int32Array(512).fill(-1);   // 每个玩家（含内置 AI）第一次被看到「已不在」的拍
proto.tick = function () {
  if ((this.t & 63) === 0 && globalThis.__cpAbort) globalThis.__cpAbort();
  if (live) afterFrame(this);
  origTick.call(this);
  const g = this;
  if (g.spawnPhase) return;
  gRef = g;
  if (!g.names) g.names = names;
  if (squadTeam < 0 && g.teams) squadTeam = g.teams[squadIds[0]];
  if (n0S < 0) { n0S = 0; n0O = 0; for (let p = 0; p < H; p++) if (g.alive[p]) { if (isSquad[p]) n0S++; else n0O++; } }
  for (let p = 0; p < g.players; p++) if (deathAll[p] < 0 && !g.alive[p]) deathAll[p] = g.t;
  if (!live && T0 >= 0 && g.t >= T0 && chan !== 'H') live = true;
  if (!perturbed && T0 >= 0 && g.t >= Math.max(1, T0)) { perturbed = true; for (let i = 0; i < seed; i++) g.rng.next(); }
  if (g.t % 30 === 0 || wantSnap.has(g.t) || g.over) takeSnap(g);
  if (g.over) return;
  for (let q = 0; q < H; q++) if (g.state[q] === 2) quitSet.add(q);
  window.__quitPlayers = quitSet;
  const onlineHad = Object.prototype.hasOwnProperty.call(g, 'online');
  const online0 = g.online;
  g.online = true;
  for (const [b, p] of pol) {
    const me = p.me;
    if (!g.alive[me] || g.state[me] === 2) continue;
    window.__tsbSquadSlot = slotOf.has(b) ? slotOf.get(b) : me % 10;
    let accepted = 0;
    const direct = live && chan === 'C0';
    const bridge = (kind, pct, target, extra) => {
      // 桥接语义：本拍已受理过一条 → 假
      if (accepted > 0) { chanStat.second++; return false; }
      accepted++;
      const c = { me, bot: b, kind, pct, target, t: g.t, seq: ++seqNo };
      if (extra) Object.assign(c, extra);
      if (!live) {
        const rej = kind === 'donate' && !(g.donateQuote(pct, target, me) > 0) ? 1 : 0;
        intents.push([g.t, b, kind, pct, kind === 'boat' ? c.water * 8 + c.dir : target, rej]);
        if (chan === 'H' || chan === 'C0' || chan === 'C0b' || rej) return true;
        const dd = dueOf(b, g.t);
        if (dd.drop || dd.due < T0) return true;
        c.rec = [g.t, b, kind, pct, target, kind === 'attack' || kind === 'donate' ? clsOf(g, target) : '-', -2, 0, 0, 0, '-', 'inflight'];
        c.due = dd.due; queue.push(c); chanStat.inflight++;
        return true;
      }
      chanStat.issued++;
      const rec = [g.t, b, kind, pct, target, kind === 'attack' || kind === 'donate' ? clsOf(g, target) : '-', -1, 0, 0, 0, '-', ''];
      cmdRec.push(rec);
      c.rec = rec;
      if (kind === 'donate' && !(g.donateQuote(pct, target, me) > 0)) { chanStat.donRej++; rec[11] = 'donRej'; return true; }
      if (chan === 'C0b') {
        const cls1 = kind === 'attack' ? clsOf(g, target < NEUTRAL && !g.alive[target] ? NEUTRAL : target) : kind === 'donate' ? clsOf(g, target) : '-';
        const r = execNow(g, c);
        chanStat.landed++; if (r.ok) chanStat.landedOk++;
        rec[6] = g.t; rec[7] = r.ok ? 1 : 0; rec[8] = r.troops; rec[9] = r.fee; rec[10] = cls1;
        return true;
      }
      const dd = dueOf(b, g.t);
      if (dd.drop) { chanStat.mapDrop++; rec[11] = dd.drop; return true; }
      c.due = dd.due; queue.push(c);
      return true;
    };
    const directExec = (kind, pct, target, extra) => {
      const c = { me, bot: b, kind, pct, target, t: g.t };
      if (extra) Object.assign(c, extra);
      const cls0 = kind === 'attack' || kind === 'donate' ? clsOf(g, Math.min(target, NEUTRAL)) : '-';
      const cls1 = kind === 'attack' ? clsOf(g, target < NEUTRAL && !g.alive[target] ? NEUTRAL : Math.min(target, NEUTRAL)) : cls0;
      const r = execNow(g, c);
      chanStat.issued++;
      if (r.ok) { chanStat.landed++; chanStat.landedOk++; }
      cmdRec.push([g.t, b, kind, pct, target, cls0, r.ok ? g.t : -1, r.ok ? 1 : 0, r.troops, r.fee, cls1, r.ok ? '' : 'engineFalse']);
      return r.ok;
    };
    if (direct) {
      g.attack = (pct, target, pl = me) => (pl !== me ? false : directExec('attack', pct, target));
      g.donate = (pct, q, pl = me) => (pl !== me ? false : directExec('donate', pct, q));
      g.boat = (pct, water, dir, pl = me) => (pl !== me ? false : directExec('boat', pct, water, { water, dir }));
      g.boatTo = (pct, target, pl = me, radius = 32) => {
        if (pl !== me) return false;
        const s = g.boatSpot(target, me, radius);
        return s !== null && directExec('boat', pct, target, { water: s.water, dir: s.dir });
      };
      g.chase = (pct, id, pl = me) => (pl !== me ? false : directExec('chase', pct, id));
      g.recall = (id, pl = me) => (pl !== me ? false : directExec('recall', 0, id));
      g.retreat = (target, pl = me) => (pl !== me ? false : directExec('retreat', 0, target));
    } else {
      g.attack = (pct, target, pl = me) => {
        if (pl !== me) return false;
        const tg = Math.min(target, NEUTRAL);
        if (tg < NEUTRAL && g.alive[tg] && !g.isEnemy(me, tg)) return false;
        if (!g.hasAttack(me, tg < NEUTRAL && !g.alive[tg] ? NEUTRAL : tg) && !g.hasFreeSlot(me)) return false;
        return bridge('attack', pct, tg);
      };
      g.donate = (pct, q, pl = me) => { if (pl !== me || !g.alive[q] || !g.isTeammate(me, q)) return false; return bridge('donate', pct, q); };
      g.boat = (pct, water, dir, pl = me) => { if (pl !== me || !g.boatsAllowed(me)) return false; return bridge('boat', pct, water, { water, dir }); };
      g.boatTo = (pct, target, pl = me, radius = 32) => {
        if (pl !== me || !g.boatsAllowed(me)) return false;
        const s = g.boatSpot(target, me, radius);
        if (s === null) return false;
        return bridge('boat', pct, target, { water: s.water, dir: s.dir });
      };
      g.chase = (pct, id, pl = me) => (pl !== me ? false : bridge('chase', pct, id));
      g.recall = (id, pl = me) => (pl !== me ? false : bridge('recall', 0, id));
      g.retreat = (target, pl = me) => (pl !== me ? false : bridge('retreat', 0, Math.min(target, NEUTRAL)));
    }
    try { p.act(g); } catch (e) { errCount++; if (!firstErr) firstErr = `${b} t=${g.t}: ${e && e.stack ? String(e.stack).split('\n').slice(0, 3).join(' | ') : e}`; }
    delete g.attack; delete g.donate; delete g.boat; delete g.boatTo; delete g.chase; delete g.recall; delete g.retreat;
  }
  if (onlineHad) g.online = online0; else delete g.online;
  flush(g);
};

const t0ms = Date.now();
let out;
try {
  out = resim(mid, { until: Number.isFinite(until) ? until : undefined });
} finally {
  proto.tick = origTick;
  for (const k of Object.keys(playerArg)) proto[k] = origM[k];
  proto.leave = origM.leave;
}
if (gRef && (!snaps.length || snaps[snaps.length - 1].t !== gRef.t)) takeSnap(gRef);

// ---- 录像里的指令：我方落地（H 用）与别的真人的结果（分歧指标用）
const KIND = { 1: 'attack', 2: 'donate', 3: 'boat', 4: 'chase', 5: 'retreat', 8: 'leave', 9: 'leave' };
const landed = [];   // [拍, 号, kind, pct, 目标(原值), 生效, 兵, 手续费]
const others = [];   // [拍, 玩家, type, 生效, 兵, 目标是否我方号]
for (const r of out.cmdLog) {
  const [t, p, type, dX, dZ, ok, troops, fee] = r;
  if (isSquad[p]) {
    if (chan === 'H' || t < T0) landed.push([t, botOf.get(p), type === 4 && dX === 849 ? 'recall' : KIND[type] || String(type), dX, dZ, ok, troops, fee]);
  } else others.push([t, p, type, ok, type === 1 || type === 3 ? troops : 0, type === 1 && dZ < H && isSquad[dZ] ? 1 : 0]);
}

// ---- 分歧指标：别的真人在这一次运行里每条指令的结果 vs 基线
let div = null;
if (HB && T0 >= 0) {
  const hb = HB.others;
  const key = (r) => `${r[0]}|${r[1]}|${r[2]}`;
  const hm = new Map();
  for (const r of hb) { if (r[0] < T0 || r[0] >= until) continue; const k = key(r); if (!hm.has(k)) hm.set(k, []); hm.get(k).push(r); }
  const seen = new Map();
  const win = [];
  const W = 150;
  for (let i = 0; i < Math.ceil(horizon / W); i++) win.push({ t0: T0 + i * W, n: 0, okDiff: 0, trH: 0, trC: 0, trAbs: 0, onSqH: 0, onSqC: 0, unmatched: 0 });
  let firstOkDiff = -1;
  for (const r of others) {
    if (r[0] < T0 || r[0] >= until) continue;
    const w = win[Math.min(win.length - 1, Math.floor((r[0] - T0) / W))];
    const k = key(r);
    const idx = seen.get(k) || 0; seen.set(k, idx + 1);
    const h = hm.get(k)?.[idx];
    w.n++;
    if (!h) { w.unmatched++; continue; }
    if (h[3] !== r[3]) { w.okDiff++; if (firstOkDiff < 0) firstOkDiff = r[0]; }
    w.trH += h[4]; w.trC += r[4]; w.trAbs += Math.abs(h[4] - r[4]);
    if (h[5]) w.onSqH += h[4];
    if (r[5]) w.onSqC += r[4];
  }
  div = { firstOkDiff, win };
}

// ---- 我方指令汇总（接管后）
const sumCmd = () => {
  const o = {};
  const add = (k, f, v) => { o[k] = o[k] || { issued: 0, landed: 0, ok: 0, troops: 0, fee: 0, drop: 0 }; o[k][f] += v; };
  const per = (t) => (t < 600 ? 'p0' : t < 1500 ? 'p1' : t < 3000 ? 'p2' : 'p3');
  for (const r of cmdRec) {
    const k = `${per(r[0])}:${r[2]}:${r[5]}`;
    add(k, 'issued', 1);
    if (r[6] >= 0) { add(k, 'landed', 1); if (r[7]) { add(k, 'ok', 1); add(k, 'troops', r[8]); add(k, 'fee', r[9]); } }
    else add(k, 'drop', 1);
  }
  return o;
};
// 落地时的目标类别（兵落在谁身上）
const sumLand = () => {
  const o = {};
  for (const r of cmdRec) {
    if (r[6] < 0 || !r[7] || r[2] !== 'attack') continue;
    const per = r[6] < 600 ? 'p0' : r[6] < 1500 ? 'p1' : r[6] < 3000 ? 'p2' : 'p3';
    const k = `${per}:${r[10]}`;
    o[k] = o[k] || { n: 0, troops: 0 };
    o[k].n++; o[k].troops += r[8];
  }
  return o;
};
const delays = cmdRec.filter((r) => r[6] >= 0).map((r) => r[6] - r[0]).sort((a, b) => a - b);
const q = (a, f) => (a.length ? a[Math.min(a.length - 1, Math.floor(f * a.length))] : null);

const res = {
  mid, ver, nativeVer, chan, T0, seed, until, tag, dmodel, dmin, dmax, keepMode, leaveMode,
  endTick: out.endTick, over: out.over, winnerTeam: out.winnerTeam, land: out.land, H,
  squad: [...idOf].map(([b, p]) => ({ bot: b, id: p, slot: slotOf.get(b) ?? null, team: out.teams[p] })),
  squadTeam, nSquad: n0S, nOther: n0O,
  teams: out.teams, teamSizes: out.teamSizes,
  validate: { rows: out.validate.rows, both: out.validate.bothExact },
  deathT: out.deathT, leftT: out.leftT,
  snaps, chanStat, posStat, suppressed, leaveSkipped, errCount, firstErr,
  cmdSum: sumCmd(), landSum: sumLand(), delayQ: { n: delays.length, p50: q(delays, 0.5), p90: q(delays, 0.9), max: delays.length ? delays[delays.length - 1] : null },
  div, ms: Date.now() - t0ms,
};
if (chan === 'H' && T0 < 0) { res.intents = intents; res.landed = landed; res.others = others; res.deathAll = Array.from(deathAll); }
if (opt('--dump', '') === 'cmds') res.cmdRec = cmdRec;
fs.writeFileSync(outPath, JSON.stringify(res));
const last = snaps[snaps.length - 1];
console.log(`${mid} ${tag} ver=${ver} end=${out.endTick} over=${out.over} | traj 核对 ${out.validate.bothExact}/${out.validate.rows} | 末拍 t=${last.t} LS=${last.LS} LO=${last.LO} | 通道 ${JSON.stringify(chanStat)} 压掉录像指令 ${suppressed} 跳过离开 ${leaveSkipped} | 策略报错 ${errCount}${firstErr ? ' 首条：' + firstErr : ''} | ${((Date.now() - t0ms) / 1000).toFixed(1)}s`);
}

// ---- 入口：参数里用 +++ 隔开多条运行，逐条跑；一条出错不影响后面的
const arms = [];
{
  let cur = [];
  for (const a of process.argv.slice(2)) { if (a === '+++') { if (cur.length) arms.push(cur); cur = []; } else cur.push(a); }
  if (cur.length) arms.push(cur);
}
if (!arms.length) { console.error('用法：100_checkpoint.mjs <局> --chan H|C0|C0b|C1|C2 [--t0 T] [--h 900] [--seed k] [--ver native|va|vb] [+++ <下一条> …]'); process.exit(2); }
// 时间预算：CP_DEADLINE_MS（绝对时刻，毫秒）和进程启动后 105 秒，取早的；估计下一条跑不完就不开始（留给下一次）
const tStart = Date.now();
// 连跑多条时先量一下这一刻分到的 CPU（重计算闸是 nice 19，机器被别的进程占满时几乎分不到）：
// 分到的不足 CP_MIN_SHARE（默认 0.15）就立刻退出把槽位让出来（退出码 76），由批量脚本稍后再来
if (arms.length > 1 || process.env.CP_MIN_SHARE) {
  const c0 = process.cpuUsage(), w0 = Date.now();
  let x = 0;
  while (Date.now() - w0 < 400) x += Math.sqrt(x + 1);
  const cu = process.cpuUsage(c0);
  const share = (cu.user + cu.system) / 1000 / Math.max(1, Date.now() - w0);
  if (share < +(process.env.CP_MIN_SHARE || 0.15)) { console.log(`STARVED 分到的 CPU ${(100 * share).toFixed(0)}%`); process.exit(76); }
}
const deadline = Math.min(+(process.env.CP_DEADLINE_MS || Infinity), arms.length > 1 ? tStart + 105000 : Infinity);
const minShare = +(process.env.CP_MIN_SHARE || 0.15);
let bad = 0, longest = 0, starved = false;
if (Number.isFinite(deadline)) {
  // 跑到一半也看：过了时间预算、或者最近 10 秒分到的 CPU 不足，就放弃这一条（留给下一次）
  let w1 = Date.now(), c1 = process.cpuUsage();
  globalThis.__cpAbort = () => {
    const now = Date.now();
    if (now > deadline) throw new Error('CP-DEADLINE');
    if (now - w1 >= 10000) {
      const cu = process.cpuUsage(c1);
      const share = (cu.user + cu.system) / 1000 / (now - w1);
      w1 = now; c1 = process.cpuUsage();
      if (share < minShare) throw new Error(`CP-STARVED ${(100 * share).toFixed(0)}%`);
    }
  };
}
for (const a of arms) {
  const name = `${a[0]} ${a[a.indexOf('--tag') + 1] || ''}`;
  const est = longest ? Math.max(15000, longest * 1.25) : 40000;
  if (starved || Date.now() + est > deadline) { console.log(`LATER ${name}`); continue; }
  const t = Date.now();
  try { await runOne(a); } catch (e) {
    const msg = e && e.message ? e.message : String(e);
    if (msg.startsWith('CP-')) { console.log(`LATER ${name} (${msg})`); if (msg.startsWith('CP-STARVED')) starved = true; continue; }
    bad++; console.error(`FAIL ${a.join(' ')} :: ${e && e.stack ? String(e.stack).split('\n').slice(0, 3).join(' | ') : e}`);
  }
  longest = Math.max(longest, Date.now() - t);
}
process.exit(starved ? 76 : bad ? 1 : 0);
