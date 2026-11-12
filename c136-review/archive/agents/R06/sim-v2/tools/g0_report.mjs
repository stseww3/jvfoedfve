#!/usr/bin/env node
// g0_report.mjs — 保真度验收报告（reports/SIM-V2-CALIBRATION-G0.md）里全部表格和数字的出处。
//
// 读（都在 sim-v2/calib/ 下，由 tools/g0_all.sh 那条队列生成）：
//   verify/<局>.json            --mode verify：物理底座对真引擎重放
//   live/<局>.json              --mode live：全部有录像的局的实盘签名（只放录像）
//   g0/<标签>.json              --mode checkpoint：630 / 1530 两个断面 × C0 / C1 / C2 / C3
//   fill/<标签>.json            C2 已知点之间的补法对照
//   attr/<标签>.json            通道延迟归因：0 / 630 / 1500 / 4284 四个断面
//   arena-acc20/<局>.json、arena-rp1530/<局>.json   --mode arena：闭环对手模型标定
//   opening-delay.json          tools/opening_delay.mjs --json：日志里带拍号的发令记录 ↔ 录像执行拍
//   batchcheck/                 同一批运行「单独起进程跑」与「一个进程连着跑」两种跑法的结果（tools/same_result.mjs 逐字段核对）
// 写：sim-v2/calib/report/tables/<表名>.md（Markdown 表）、sim-v2/calib/report/values.json（正文里引用的单个数字）
//
// 用法（在 c136-review/agents/R06 下）：node sim-v2/tools/g0_report.mjs [--only 表名前缀] [--print] [--calib 结果目录]
// 之后 node sim-v2/tools/g0_build.mjs 把 reports/src-g0/ 下的正文模板和这些表拼成报告。
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { SIG as LIVE_SIG, loadLive, lagClass, bands } from './live_table.mjs';
import { cohortOf, quantile } from '../lib/util.mjs';
import { Profile } from '../lib/channel.mjs';
import { HISTORICAL_STRATEGIES } from '../lib/sandbox.mjs';
import { compareDirs } from './same_result.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const SIMV2 = path.resolve(HERE, '..');
const argv = process.argv.slice(2);
// --calib：换一个结果目录读（调试用；缺省 sim-v2/calib），表和数字写到它下面的 report/
const CALIB = argv.includes('--calib') ? path.resolve(argv[argv.indexOf('--calib') + 1]) : path.join(SIMV2, 'calib');
const OUT = path.join(CALIB, 'report');
const ONLY = argv.includes('--only') ? argv[argv.indexOf('--only') + 1] : '';
const PRINT = argv.includes('--print');

// ---------- 小工具
const readJson = (f) => JSON.parse(fs.readFileSync(f, 'utf8'));
const loadDir = (name) => {
  const d = path.join(CALIB, name);
  const m = new Map();
  if (!fs.existsSync(d)) return m;
  for (const f of fs.readdirSync(d).sort()) {
    if (!f.endsWith('.json')) continue;
    try { m.set(f.slice(0, -5), readJson(path.join(d, f))); } catch (e) { console.error(`读不了 ${name}/${f}：${e.message}`); }
  }
  return m;
};
const ok = (v) => v !== null && v !== undefined && !Number.isNaN(v) && Number.isFinite(v);
const clean = (a) => a.filter(ok);
const q = (a, p) => { const b = clean(a); return b.length ? quantile(b, p) : null; };
const med = (a) => q(a, 0.5);
const sum = (a) => clean(a).reduce((x, y) => x + y, 0);
const mean = (a) => { const b = clean(a); return b.length ? sum(b) / b.length : null; };
const f = (v, d = 2) => (ok(v) ? v.toFixed(d) : '-');
const pc = (v, d = 0) => (ok(v) ? (100 * v).toFixed(d) + '%' : '-');
const pp = (v, d = 0) => (ok(v) ? (v >= 0 ? '+' : '−') + Math.abs(100 * v).toFixed(d) : '-');        // 百分点差
const sgn = (v, d = 2) => (ok(v) ? (v >= 0 ? '+' : '−') + Math.abs(v).toFixed(d) : '-');
const rpc = (v, d = 0) => (ok(v) ? (v >= 1 ? '+' : '−') + Math.abs(100 * (v - 1)).toFixed(d) + '%' : '-');   // 比值 → 相对变化
const k1 = (v) => (ok(v) ? (Math.abs(v) >= 1e6 ? (v / 1e6).toFixed(2) + ' 百万' : Math.abs(v) >= 1e4 ? (v / 1e4).toFixed(1) + ' 万' : String(Math.round(v))) : '-');
const int = (v) => (ok(v) ? String(Math.round(v)).replace(/\B(?=(\d{3})+(?!\d))/g, ',') : '-');
const q3 = (a, fmt = f, d) => (clean(a).length ? `${fmt(q(a, 0.25), d)} / ${fmt(med(a), d)} / ${fmt(q(a, 0.75), d)}` : '-');
const div = (a, b) => (ok(a) && ok(b) && b !== 0 ? a / b : null);
const VER = { va: 'Va', vb: 'Vb', vc: 'Vc', c110: 'c110' };
const VORDER = ['va', 'vb', 'vc', 'c110'];
const CLS = { clean: '不卡', mid: '轻度', lag: '卡顿' };

const tables = {};   // 表名 → Markdown
const values = {};   // 键 → 字符串（正文里 {{v:键}} 引用）
const notes = [];    // 生成时的提醒（缺文件、被截断的运行等）
function table(name, head, rows, foot = '') {
  const L = ['| ' + head.join(' | ') + ' |', '|' + head.map(() => '---').join('|') + '|'];
  for (const r of rows) L.push('| ' + r.join(' | ') + ' |');
  tables[name] = L.join('\n') + (foot ? '\n\n' + foot : '');
}
const val = (k, v) => { values[k] = String(v); };
const want = (name) => !ONLY || name.startsWith(ONLY);

// ---------- 对局包里的局、每局的版本与卡顿档
const PACK = readJson(path.join(SIMV2, 'packs', 'index.json'));
const MIDS = Object.keys(PACK).sort((a, b) => VORDER.indexOf(cohortOf(a)) - VORDER.indexOf(cohortOf(b)) || a.localeCompare(b));
const CORE = new Set(fs.readFileSync(path.join(HERE, 'arena_calib_list20.txt'), 'utf8').split('\n').filter((l) => l && !l.startsWith('#')).map((l) => l.split(/\s+/)[0]));
const LIVE = fs.existsSync(path.join(CALIB, 'live')) ? loadLive(path.join(CALIB, 'live')) : [];
const liveOf = new Map(LIVE.map((r) => [r.match, r]));

// 一条臂 / 历史臂的签名与结果
function sig(m) {
  if (!m) return null;
  return {
    recPerSeat: m.recorded / m.seats, issuedPerSeat: ok(m.issued) ? m.issued / m.seats : null,
    dupShare: m.dupShare, batchShare: m.batchShare, gap0: m.gapShare ? m.gapShare[0] : null,
    dumpPerSeat: m.dumpBatches / m.seats, fullPerSeat: m.fullBatches / m.seats, batchesPerSeat: m.batches / m.seats,
    atkVoidRate: m.atkVoidRate, rerouteRate: m.rerouteRate, atkNeutralShare: m.atkNeutralShare, donNotLanded: m.donNotLanded,
    relTerr1: m.relTerr1, aliveShare: m.alive1 / m.seats, alive1: m.alive1, seats: m.seats, terr1: m.terr1, terr0: m.terr0,
    capture1: m.capture1, netProd: m.netProd, income: m.income, feeAtk: m.feeAtk, feeLoss: m.feeLoss, wealth1: m.wealth1,
    landedShare: m.landedShare, droppedPerSeat: ok(m.dropped) ? m.dropped / m.seats : null, lostChan: m.lostChan,
    batches: m.batches, dumpBatches: m.dumpBatches, fullBatches: m.fullBatches, recorded: m.recorded, dumpCost: m.dumpCost,
    atkSent: m.byKind ? m.byKind.atk.sent : null, pageDead: m.pageDead,
    othersAsRec: m.others && m.others.atk ? m.others.asRecorded / m.others.atk : null,
  };
}
// 签名表（键、表头、类型：rate = 占比（差用百分点）、cnt = 计数（比值）、lvl = 水平量）
const SIGS = [
  ['recPerSeat', '进录像条数 ÷ 席位', 'cnt', (v) => f(v, 1)],
  ['dupShare', '重复单占比', 'rate', pc],
  ['batchShare', '同拍批占比', 'rate', pc],
  ['gap0', '同回合连发占比', 'rate', pc],
  ['dumpPerSeat', '清仓批 ÷ 席位', 'cnt', (v) => f(v, 2)],
  ['atkVoidRate', '陆攻落空率', 'rate', pc],
  ['atkNeutralShare', '陆攻记成无主地占比', 'rate', pc],
  ['donNotLanded', '捐款没成交占比', 'rate', pc],
  ['relTerr1', '窗口末人均相对领土', 'lvl', (v) => f(v, 2)],
  ['aliveShare', '窗口末在场席位占比', 'rate', pc],
];

// 断面运行：按 (目录, 局, t0, 臂) 取
const parseTag = (tag) => {
  // g0：<局>-<t0>-<策略>-<通道>；attr：<局>-<t0>-C0 | -C1-s1 | -C2-s1 | -C2nd-s1 | -C3-s1；fill：<局>-0630-<补法>
  const p = tag.split('-');
  return { mid: p[0], t0: +p[1], rest: p.slice(2) };
};
function loadRuns(dirName, armOf) {
  const out = [];
  for (const [tag, r] of loadDir(dirName)) {
    if (!r.arms || !r.arms.baseline || !r.history) { notes.push(`${dirName}/${tag}：不是断面结果`); continue; }
    const t = parseTag(tag);
    const arm = armOf(t.rest);
    if (r.truncated) notes.push(`${dirName}/${tag}：被时间预算截断在 t=${r.t1}`);
    if (r.arms.baseline.stratErrors && r.arms.baseline.stratErrors.length) notes.push(`${dirName}/${tag}：策略报错的席位 ${r.arms.baseline.stratErrors.length}`);
    out.push({ tag, mid: t.mid, t0: r.t0, t1: r.t1, arm: arm.arm, seed: arm.seed, r, a: sig(r.arms.baseline), h: sig(r.history), co: cohortOf(t.mid), truncated: !!r.truncated,
      sha: r.arms.baseline.sha256, errs: (r.arms.baseline.stratErrors || []).length });
  }
  return out;
}
const G0 = loadRuns('g0', (rest) => ({ arm: rest[1], seed: 1 }));
const ATTR = loadRuns('attr', (rest) => ({ arm: rest[0], seed: rest[1] ? +rest[1].slice(1) : 1 }));
const FILL = loadRuns('fill', (rest) => ({ arm: rest[0], seed: 1 }));
const HOLD = loadRuns('hold', () => ({ arm: 'hold', seed: 1 }));

// 卡顿档：这一局 630~1530 拍录像里的同拍批占比（< 15% 不卡，≥ 50% 卡顿，其间轻度）——取历史臂（= 录像），没有断面结果的局取 live
const clsOf = (() => {
  const m = new Map();
  for (const x of G0) if (x.t0 === 630 && !m.has(x.mid)) m.set(x.mid, lagClass(x.h.batchShare));
  for (const mid of MIDS) if (!m.has(mid) && liveOf.has(mid)) m.set(mid, lagClass(liveOf.get(mid).windows[0].batchShare));
  return (mid) => m.get(mid) || '?';
})();
const midsOf = (pred) => MIDS.filter(pred);
val('pack.n', MIDS.length);
val('pack.core', MIDS.filter((m) => CORE.has(m)).length);
val('pack.ext', MIDS.filter((m) => !CORE.has(m)).length);
for (const co of VORDER) val(`pack.ext.${co}`, MIDS.filter((m) => !CORE.has(m) && cohortOf(m) === co).length);
for (const co of VORDER) {
  const a = MIDS.filter((m) => cohortOf(m) === co);
  val(`pack.${co}.n`, a.length);
  val(`pack.${co}.list`, a.join(' ') || '—');
  for (const c of ['clean', 'mid', 'lag']) { const b = a.filter((m) => clsOf(m) === c); val(`pack.${co}.${c}.n`, b.length); val(`pack.${co}.${c}.list`, b.join(' ') || '—'); }
}
for (const c of ['clean', 'mid', 'lag']) { const b = MIDS.filter((m) => clsOf(m) === c); val(`pack.${c}.n`, b.length); val(`pack.${c}.list`, b.join(' ') || '—'); }

// =====================================================================================================================
// 零、范围：复现臂装的是哪几个策略文件；一共跑了多少次；两种跑法的结果是否相同
// =====================================================================================================================
if (want('scope')) {
  const ARENA_ALL = [...loadDir('arena-acc20').entries()].map(([mid, r]) => ({ dir: 'arena-acc20', mid, r })).concat([...loadDir('arena-rp1530').entries()].map(([mid, r]) => ({ dir: 'arena-rp1530', mid, r })));
  const rows = [];
  let wrong = 0, total = 0;
  for (const co of VORDER) {
    const H = HISTORICAL_STRATEGIES[co];
    const ck = [...G0, ...ATTR, ...FILL, ...HOLD].filter((x) => x.co === co);
    const ar = ARENA_ALL.filter((x) => cohortOf(x.mid) === co && x.r.arms && x.r.arms.baseline);
    const shas = [...ck.map((x) => x.sha), ...ar.map((x) => x.r.arms.baseline.sha256)];
    const bad = shas.filter((v) => v !== H.sha256).length;
    wrong += bad; total += shas.length;
    rows.push([VER[co], `\`src/strategy/${H.file}\``, `\`${H.sha256.slice(0, 16)}…\``, String(MIDS.filter((m) => cohortOf(m) === co).length), String(ck.length), String(ar.length), bad ? `${bad} 次不同` : shas.length ? '全部相同' : '-']);
    val(`scope.${co}.file`, H.file); val(`scope.${co}.sha`, H.sha256.slice(0, 16)); val(`scope.${co}.runs`, shas.length);
  }
  table('scope', ['当年版本', '策略文件（数据包里的原文件）', '内容散列 sha256（前 16 位）', '入库的局', '断面运行', '闭环运行', '运行结果里记下的文件散列'], rows,
    '模拟器只装这四个文件，装之前核对内容散列；每一局只跑它当年线上那一版。每次运行把实际装进去的文件散列写进结果，最后一列是拿它与白名单逐次比对。');
  val('scope.runs', total); val('scope.wrong', wrong);

  // 运行清点
  const inv = [];
  const V = loadDir('verify');
  const invRow = (label, mode, n, trunc, errs) => inv.push([label, mode, String(n), String(trunc), errs === null ? '-' : String(errs)]);
  invRow('`calib/verify/`', 'verify', V.size, [...V.values()].filter((r) => r.truncated).length, null);
  invRow('`calib/live/`', 'live', LIVE.length, LIVE.filter((r) => r.truncated).length, null);
  for (const [label, a] of [['`calib/g0/`', G0], ['`calib/attr/`', ATTR], ['`calib/fill/`', FILL], ['`calib/hold/`', HOLD]]) invRow(label, 'checkpoint', a.length, a.filter((x) => x.truncated).length, a.filter((x) => x.errs > 0).length);
  for (const d of ['arena-acc20', 'arena-rp1530']) {
    const a = ARENA_ALL.filter((x) => x.dir === d);
    invRow(`\`calib/${d}/\``, 'arena', a.length, a.filter((x) => x.r.truncated).length, a.filter((x) => x.r.arms && x.r.arms.baseline && (x.r.arms.baseline.stratErrors || []).length > 0).length);
  }
  table('runs', ['结果目录', '模式', '运行数', '被时间预算截断', '有席位策略报错的运行'], inv, '「被时间预算截断」= 一次运行给足 95 秒墙钟仍没跑到窗口结束（结果里带标记，统计时照常用到它停下的那一拍）。');
  val('runs.g0', G0.length); val('runs.attr', ATTR.length); val('runs.fill', FILL.length); val('runs.hold', HOLD.length); val('runs.ckpt', G0.length + ATTR.length + FILL.length + HOLD.length);
  val('runs.ckpt.trunc', [...G0, ...ATTR, ...FILL, ...HOLD].filter((x) => x.truncated).length); val('runs.ckpt.errs', [...G0, ...ATTR, ...FILL, ...HOLD].filter((x) => x.errs > 0).length);
  val('runs.arena', ARENA_ALL.length);

  // 任务卡说的 60 次（tools/g0_list.txt）
  const tags60 = fs.readFileSync(path.join(HERE, 'g0_list.txt'), 'utf8').split('\n').filter((l) => l.trim() && !l.startsWith('#')).map((l) => l.split(/\s+/)[0]);
  const have60 = tags60.filter((t) => G0.some((x) => x.tag === t));
  val('runs.g0.card', tags60.length); val('runs.g0.cardHave', have60.length);
  val('runs.g0.cardGames', new Set(tags60.map((t) => t.split('-')[0])).size);

  // 拆掉候选臂之前入库的旧结果，对现在重跑出来的同名结果（tools/old_vs_new.sh）
  const ovn = path.join(CALIB, 'old-vs-new.json');
  if (fs.existsSync(ovn)) {
    const O = readJson(ovn);
    val('old.ref', O.ref);
    for (const [d, k] of [['verify', 'verify'], ['g0', 'g0'], ['arena-acc20', 'arena']]) {
      const x = O[d] || { old: 0, both: 0, same: 0 };
      val(`old.${k}.old`, x.old); val(`old.${k}.both`, x.both); val(`old.${k}.same`, x.same);
    }
  } else notes.push('缺 calib/old-vs-new.json（bash sim-v2/tools/old_vs_new.sh）');

  // 两种跑法的结果核对
  const a = compareDirs(path.join(CALIB, 'batchcheck', 'g0-batched'), path.join(CALIB, 'g0'));
  const b = compareDirs(path.join(CALIB, 'batchcheck', 'attr-single'), path.join(CALIB, 'attr'));
  val('batch.n', a.n + b.n); val('batch.same', a.same + b.same);
  for (const [f1, d] of [...a.bad, ...b.bad]) notes.push(`两种跑法结果不同：${f1}：${d.join('；')}`);
}

// =====================================================================================================================
// 一、verify：物理底座对真引擎重放
// =====================================================================================================================
if (want('verify')) {
  const V = loadDir('verify');
  const rows = [];
  let nFull = 0, samples = 0, snapN = 0, snapOk = 0, teamOk = 0, cloneOk = 0, n = 0, ticks = 0, cpu = 0;
  const partial = [];
  for (const mid of MIDS) {
    const r = V.get(mid);
    if (!r) { notes.push(`verify 缺 ${mid}`); continue; }
    n++;
    const full = r.truth && r.truth.firstBadT < 0 && !r.truncated;
    if (full) nFull++; else partial.push(`${mid}（一致到 t=${r.truth ? r.truth.lastOkT : '-'}，第一处不同 t=${r.truth ? r.truth.firstBadT : '-'}，录像 ${r.replayTicks} 拍）`);
    samples += r.truth ? r.truth.samples : 0;
    snapN += r.logSnaps ? r.logSnaps.n : 0; snapOk += r.logSnaps ? r.logSnaps.ok : 0;
    const tOk = r.teamsVsEngine && r.teamsVsEngine.same === r.teamsVsEngine.of && r.teamsVsEngine.nTeamsOk && r.teamsVsEngine.botTeamsOk;
    if (tOk) teamOk++;
    const cOk = r.clone && r.clone.twinFirstBad < 0 && r.clone.origSame;
    if (cOk) cloneOk++;
    ticks += r.endT; cpu += r.cpuMs;
    rows.push([mid + (CORE.has(mid) ? '' : ' ＋'), VER[cohortOf(mid)], r.replay === mid ? '本局' : r.replay, String(r.humans), `${r.nTeams}${r.botsTeamed ? '（AI 入队）' : ''}`, String(r.squad),
      int(r.replayTicks), String(r.truth ? r.truth.samples : '-'), r.truth ? int(r.truth.lastOkT) : '-', r.truth && r.truth.firstBadT >= 0 ? int(r.truth.firstBadT) : '没有',
      r.logSnaps ? `${int(r.logSnaps.ok)} / ${int(r.logSnaps.n)}` : '-', tOk ? `${r.teamsVsEngine.same} / ${r.teamsVsEngine.of}` : '不同', cOk ? `${r.clone.twinSame} / ${r.clone.len}` : '不同', f(r.cpuMs / 1000, 1)]);
  }
  table('verify', ['局', '当年版本', '录像取自', '真人', '队数', '我方席位', '录像拍数', '核对的采样拍', '与真引擎一致到', '第一处不同', '日志快照 相同 / 总数', '分队与真引擎相同', '分叉自检（300 拍）', 'CPU 秒'], rows,
    '「＋」= 本报告为了覆盖 Va / Vc 新接进来的局（不在任务卡说的 20 局里）。核对内容：全体真人的（领土、兵力）每 30 拍一个指纹，与真引擎重放的同一拍逐个比；日志快照 = 策略日志 `[HL-TICK]` 里我方号当时看到的自己的（领土、兵力），与重放到同一拍的同一席位比；分叉自检 = 在第 1200 拍把世界复制一份，两份各走 300 拍，逐拍指纹相同且原世界不受影响。');
  val('verify.n', n); val('verify.full', nFull); val('verify.partial', partial.join('；') || '没有'); val('verify.samples', int(samples));
  val('verify.snaps', `${int(snapOk)} / ${int(snapN)}`); val('verify.teams', `${teamOk} / ${n}`); val('verify.clone', `${cloneOk} / ${n}`);
  val('verify.ticks', int(ticks)); val('verify.cpuPer1000', f(cpu / ticks, 2));
  for (const co of VORDER) val(`verify.${co}.n`, MIDS.filter((m) => cohortOf(m) === co && V.has(m)).length);
  val('verify.partial.n', partial.length);
  // 没有一致到最后的局，分歧之前那一拍场上的局面（tools/verify_tail.mjs）
  const tf = path.join(CALIB, 'verify-tail.json');
  if (fs.existsSync(tf)) {
    for (const [mid, x] of Object.entries(readJson(tf))) {
      const k = `verify.tail.${mid}`;
      val(`${k}.t`, int(x.t)); val(`${k}.firstBadT`, int(x.firstBadT)); val(`${k}.replayTicks`, int(x.replayTicks));
      val(`${k}.leadLand`, pc(x.leadShareOfLand, 1)); val(`${k}.leadOwned`, pc(x.leadShareOfOwned, 1));
      val(`${k}.humansPresent`, x.humansPresent); val(`${k}.humansHusk`, x.humansHusk); val(`${k}.squadPresent`, `${x.squadPresent} / ${x.squad}`);
      if (x.diff) {
        // 第一处不同的采样拍上是哪几个真人不同（模拟器 ↔ 真引擎）
        const D = x.diff, husk = D.seats.filter((z) => z.husk), rest = D.seats.filter((z) => !z.husk);
        val(`${k}.diff.n`, D.n); val(`${k}.diff.humans`, D.humans); val(`${k}.diff.husk`, husk.length);
        val(`${k}.diff.teams`, [...new Set(D.seats.map((z) => z.team))].length);
        val(`${k}.diff.leadTeamOnly`, D.seats.every((z) => z.team === x.leadTeam) ? '是' : '否');
        val(`${k}.diff.huskLand`, husk.length ? int(Math.max(...husk.map((z) => Math.abs(z.terr[1] - z.terr[0])))) : '-');
        val(`${k}.diff.restLand`, rest.length ? int(Math.max(...rest.map((z) => Math.abs(z.terr[1] - z.terr[0])))) : '-');
        val(`${k}.diff.restBal`, rest.length ? k1(Math.max(...rest.map((z) => Math.abs(z.bal[1] - z.bal[0])))) : '-');
        // 引擎规则：一个席位能收下的兵以「领土 × 150」为上限（数据包 src/sim/sim/game.js）。在场的那个席位在哪一边正好顶在这个上限上？
        val(`${k}.diff.restAtCapSim`, rest.length && rest.every((z) => z.bal[0] === z.terr[0] * 150) ? '是' : '否');
        val(`${k}.diff.restAtCapTruth`, rest.length && rest.every((z) => z.bal[1] === z.terr[1] * 150) ? '是' : '否');
        val(`${k}.diff.huskBal`, husk.length ? k1(Math.max(...husk.map((z) => z.bal[1] - z.bal[0]))) : '-');
        val(`${k}.diff.cmdsBetween`, sum(D.seats.map((z) => z.cmdsBetween || 0)));
        val(`${k}.diff.huskLeaveT`, husk.length ? int(Math.min(...husk.map((z) => z.leaveT))) : '-');
        val(`${k}.diff.list`, D.seats.map((z) => `${z.p} 号（${z.husk ? '离场托管' : '在场'}）领土 ${int(z.terr[0])} ↔ ${int(z.terr[1])}、兵 ${k1(z.bal[0])} ↔ ${k1(z.bal[1])}`).join('；'));
      }
    }
  } else if (partial.length) notes.push('缺 calib/verify-tail.json（node sim-v2/tools/verify_tail.mjs）');
}

// =====================================================================================================================
// 二、live：全部有录像的局的实盘签名与区间
// =====================================================================================================================
let BANDS = null;
if (LIVE.length) {
  BANDS = bands(LIVE);
  if (want('live')) {
    // 覆盖面
    const rows = [];
    let tot = [0, 0, 0, 0, 0, 0];
    for (const co of [...VORDER, 'g09']) {
      const a = LIVE.filter((r) => r.cohort === co);
      if (!a.length) continue;
      const snapOkN = a.filter((r) => r.logSnaps && r.logSnaps.n > 0 && r.logSnaps.ok === r.logSnaps.n).length;
      const inB = Object.values(BANDS.matches).filter((m) => m.cohort === co);
      const c = (k) => inB.filter((m) => m.cls === k).length;
      const row = [a.length, snapOkN, inB.length, c('clean'), c('mid'), c('lag')];
      row.forEach((v, i) => { tot[i] += v; });
      ['n', 'snapOk', 'inBands', 'clean', 'mid', 'lag'].forEach((k, i) => val(`live.cover.${co}.${k}`, row[i]));
      rows.push([VER[co] || co, ...row.map(String)]);
    }
    rows.push(['合计', ...tot.map(String)]);
    table('live-cover', ['当年版本', '扫过的局（有录像）', '日志快照与重放逐条相同', '进区间的局', '其中 不卡', '轻度', '卡顿'], rows,
      '进区间的条件：日志快照与重放逐条相同、我方 ≥ 6 席、630~1530 拍这个窗口跑满。卡顿档按这一局 630~1530 拍录像里的同拍批占比分：< 15% 不卡，≥ 50% 卡顿，其间轻度。');
    val('live.n', LIVE.length); val('live.inBands', Object.keys(BANDS.matches).length);
    const bad = LIVE.filter((r) => !(r.logSnaps && r.logSnaps.n > 0 && r.logSnaps.ok === r.logSnaps.n));
    val('live.badSnap.n', bad.length); val('live.badSnap.list', bad.map((r) => r.match).join(' ') || '—');
    // 区间
    const keys = ['recPerSeat', 'batchShare', 'gap0', 'dumpPerSeat', 'atkVoidRate', 'atkNeutralShare', 'relTerr1', 'aliveShare'];
    const brow = [];
    for (const win of ['630~1530', '1530~3210']) for (const co of VORDER) for (const c of ['clean', 'lag']) {
      const g = BANDS.cohorts[`${co}|${c}|${win}`];
      if (!g) continue;
      brow.push([win, VER[co], CLS[c], String(g.n), ...keys.map((k) => {
        const b = g.band[k], s = LIVE_SIG.find((x) => x[0] === k);
        if (!b) return '-';
        const d = s[3];
        const fm = (v) => (d === 0 ? Math.round(100 * v) + '%' : v.toFixed(d));
        val(`live.band.${co}.${c}.${win.split('~')[0]}.${k}`, fm(b[1]));      // 中位
        return `${fm(b[0])} / ${fm(b[1])} / ${fm(b[2])}`;
      })]);
      val(`live.band.${co}.${c}.${win.split('~')[0]}.n`, g.n);
    }
    table('live-bands', ['窗口', '版本', '卡顿档', '局数', ...keys.map((k) => LIVE_SIG.find((x) => x[0] === k)[1])], brow, '每格：各局的 P25 / 中位 / P75。');
  }
}

// =====================================================================================================================
// 三、通道：d 的实测分布对 C1 模型；实录阶梯的形状；C2 补法对照
// =====================================================================================================================
if (want('chan')) {
  const od = path.join(CALIB, 'opening-delay.json');
  if (fs.existsSync(od)) {
    const D = readJson(od);
    // C1 模型的 d：按席位、按拍取散列，和通道层用的是同一个函数
    const prof = new Profile('C1', { seed: 1 });
    const ds = [], gaps = [];
    for (let p = 0; p < 400; p++) for (let W = 0; W < 600; W += 3) { const d = prof.delay(p, W); ds.push(d); gaps.push(7 * Math.ceil((W + d) / 7) - W); }
    const cdfM = (k) => ds.filter((d) => d <= k).length / ds.length;
    const rows = [];
    const all = D.cdf.all;
    for (const k of [4, 5, 6, 7, 8, 9, 10, 11, 12, 14, 16, 18, 21]) {
      const a = all.find((x) => x[0] === k), o = D.cdf.open.find((x) => x[0] === k), dn = D.cdf.don.find((x) => x[0] === k);
      const c = (x) => (x && x[1] >= 8 ? `${pc(x[2] / x[1])}（${x[1]}）` : '-');
      rows.push([String(k), c(o), c(dn), c(a), pc(cdfM(k))]);
    }
    table('chan-d', ['k（拍）', '开局陆攻 P(d ≤ k)（条数）', '捐款 P(d ≤ k)（条数）', '两类合计', 'C1 模型 P(d ≤ k)'], rows,
      `实测 = ${D.mids.length} 局不卡的局（${D.mids.join(' ')}）里策略日志带本机拍号的发令记录：\`[HL-OPENING]\` 开局陆攻 ${D.open.n} 条、\`[HL-DISPATCH]\` 捐款 ${D.don.n} 条，各配录像里同一席位的执行拍。读法：通道模型是 执行拍 = 7 × ceil((下令拍 + d) ÷ 7)，取下令拍 ≡ −k（mod 7）的那些指令，「执行拍 − 下令拍 ≤ k」的占比就是 P(d ≤ k)；每个 k 用到的指令互不重叠，括号里是用到的条数。`);
    const gq = (a, p) => quantile(a, p);
    const mg = D.gapsAll || [];
    val('chan.d.n', D.open.n + D.don.n); val('chan.d.open', D.open.n); val('chan.d.don', D.don.n); val('chan.d.mids', D.mids.length);
    val('chan.gap.real', mg.length ? `${gq(mg, 0.1)} / ${gq(mg, 0.25)} / ${gq(mg, 0.5)} / ${gq(mg, 0.75)} / ${gq(mg, 0.9)}` : '-');
    val('chan.gap.model', `${gq(gaps, 0.1)} / ${gq(gaps, 0.25)} / ${gq(gaps, 0.5)} / ${gq(gaps, 0.75)} / ${gq(gaps, 0.9)}`);
    val('chan.gap.real.mean', mg.length ? f(mean(mg), 1) : '-'); val('chan.gap.model.mean', f(mean(gaps), 1));
    if (D.seatMeans && D.seatMeans.length) {
      const sm = D.seatMeans.map((x) => x[2]);
      val('chan.seat.n', sm.length);
      val('chan.seat.q', `${f(q(sm, 0.1), 1)} / ${f(q(sm, 0.25), 1)} / ${f(med(sm), 1)} / ${f(q(sm, 0.75), 1)} / ${f(q(sm, 0.9), 1)}`);
      const m0 = med(sm);
      val('chan.seat.slowShare', pc(sm.filter((v) => v >= m0 + 3).length / sm.length));
      val('chan.seat.slowMean', f(mean(sm.filter((v) => v >= m0 + 3)), 1)); val('chan.seat.fastMean', f(mean(sm.filter((v) => v < m0 + 3)), 1));
    }
    const d7 = all.find((x) => x[0] === 7);
    val('chan.d.p7', d7 ? pc(d7[2] / d7[1]) : '-'); val('chan.d.p7.model', pc(cdfM(7)));
    const maxDiff = Math.max(...all.filter((x) => x[1] >= 30 && x[0] >= 5 && x[0] <= 16).map((x) => Math.abs(x[2] / x[1] - cdfM(x[0]))));
    val('chan.d.maxDiff', (100 * maxDiff).toFixed(0));
  } else notes.push('缺 calib/opening-delay.json（node sim-v2/tools/opening_delay.mjs … --json sim-v2/calib/opening-delay.json）');

  // 实录阶梯：每局各时段 执行拍 − 下令拍 的中位
  const BINS = [[0, 600], [600, 900], [900, 1200], [1200, 1500], [1500, 2100], [2100, 3000], [3000, 4284], [4284, 1e9]];
  const rows = [];
  for (const mid of MIDS) {
    const tf = path.join(SIMV2, 'traces', `${mid}.json`);
    if (!fs.existsSync(tf)) continue;
    const T = readJson(tf);
    const all = [];
    let tmax = -1;
    for (const rs of Object.values(T.seats)) for (const r of rs) { all.push(r); if (r[0] > tmax) tmax = r[0]; }
    const cells = BINS.map(([a, b]) => { const x = all.filter((r) => r[0] >= a && r[0] < b).map((r) => r[1] - r[0]); return x.length >= 5 ? String(Math.round(med(x))) : '-'; });
    const pk = PACK[mid];
    // 页面在席位还活着时就停摆的席位数：与 match.mjs 的口径一致的近似（日志最后一条快照 + 89 早于席位出局拍 / 录像末拍 − 90）
    let doomed = 0;
    for (const [p, ll] of Object.entries(T.lastLog || {})) { const d = (pk.deathT || {})[p] ?? -1; if (ll >= 0 && ll + 1 < (d >= 0 ? d : pk.replayLast - 90)) doomed++; }
    rows.push([mid + (CORE.has(mid) ? '' : ' ＋'), VER[cohortOf(mid)], CLS[clsOf(mid)] || '?', int(T.rows), int(tmax), ...cells, String(doomed)]);
  }
  // 已知点有多密：630~1530 拍这个窗口里，每个席位有几个已知点、最长多少拍没有已知点（录像够长的局）
  {
    const cnt = [], gap = [];
    for (const mid of MIDS) {
      const tf = path.join(SIMV2, 'traces', `${mid}.json`);
      if (!fs.existsSync(tf) || PACK[mid].replayLast < 1530) continue;
      for (const rs of Object.values(readJson(tf).seats)) {
        const taus = rs.map((r) => r[0]).filter((t) => t >= 630 && t <= 1530).sort((a, b) => a - b);
        const pts = [630, ...taus, 1530];
        let g = 0;
        for (let i = 1; i < pts.length; i++) g = Math.max(g, pts[i] - pts[i - 1]);
        cnt.push(taus.length); gap.push(g);
      }
    }
    val('chan.known.seats', cnt.length); val('chan.known.cnt', `${f(q(cnt, 0.25), 0)} / ${f(med(cnt), 0)} / ${f(q(cnt, 0.75), 0)}`);
    val('chan.known.gap', `${f(q(gap, 0.25), 0)} / ${f(med(gap), 0)} / ${f(q(gap, 0.75), 0)}`); val('chan.known.gap.med', f(med(gap), 0));
  }
  table('chan-stairs', ['局', '版本', '卡顿档', '配上的指令', '实录到（拍）', ...BINS.map(([a, b]) => (b > 1e8 ? `${a} 以后` : `${a}~${b}`)), '页面中途停摆的席位'], rows,
    '每格 = 这一时段下令的指令「录像执行拍 − 影子下令拍」的中位（拍），不落后时约 12；不足 5 条的时段记「-」。配对来自 `tools/export_traces.py`（当年那一版策略作影子逐拍重演，与录像里我方席位实际执行的指令按席位、种类、目标配对）。「页面中途停摆」= 日志最后一条快照早于席位出局（或录像结束）的席位。');

  // 我方席位平均落后拍数随时间的走势：真卡顿局的实录阶梯（C2）对合成卡顿波（C3，挂在不卡的局上）
  {
    const courseOf = (arm, c) => {
      const m = new Map();   // 拍 → 各局的平均落后
      for (const x of G0) {
        if (x.arm !== arm || clsOf(x.mid) !== c) continue;
        for (const [t, v] of x.r.lagCourse || []) { if (!m.has(t)) m.set(t, []); m.get(t).push(v); }
      }
      return m;
    };
    const cols = [['C2', 'lag', 'C2 实录，卡顿的局'], ['C2', 'clean', 'C2 实录，不卡的局'], ['C3', 'clean', 'C3 合成卡顿波（挂在不卡的局上）']].map(([arm, c, label]) => ({ label, m: courseOf(arm, c), arm, c }));
    const ts = [...new Set(cols.flatMap((c) => [...c.m.keys()]))].sort((a, b) => a - b);
    const rows3 = [];
    for (const t of ts) {
      rows3.push([`${t}~${t + 150}`, ...cols.map((c) => { const a = c.m.get(t) || []; return a.length ? `${f(med(a), 0)}（${f(q(a, 0.25), 0)}~${f(q(a, 0.75), 0)}；${a.length}）` : '-'; })]);
      for (const c of cols) { const a = c.m.get(t) || []; if (a.length) val(`chan.course.${c.arm}.${c.c}.${t}`, f(med(a), 0)); }
    }
    if (rows3.length) table('chan-course', ['时段（拍）', ...cols.map((c) => c.label)], rows3, '每格 = 这一时段里我方各席位平均落后拍数（页面本机拍落后服务器多少拍）的各局中位（P25~P75；局数）。630~1530 与 1530~3210 两个窗口的运行各管各的时段。');
    const peak = (c) => Math.max(...[...c.m.values()].map((a) => med(a)));
    for (const c of cols) if (c.m.size) val(`chan.course.${c.arm}.${c.c}.peak`, f(peak(c), 0));
  }

  // C2 的补法对照
  if (FILL.length) {
    const byFill = { auto: [], linear: [], nearest: [], burst: [] };
    for (const x of G0) if (x.arm === 'C2' && x.t0 === 630) byFill.auto.push(x);
    for (const x of FILL) if (byFill[x.arm]) byFill[x.arm].push(x);
    const rows2 = [];
    for (const c of ['lag', 'clean']) for (const fl of ['auto', 'linear', 'nearest', 'burst']) {
      const a = byFill[fl].filter((x) => clsOf(x.mid) === c && FILL.some((y) => y.mid === x.mid));
      if (!a.length) continue;
      const dd = (k) => a.map((x) => (ok(x.a[k]) && ok(x.h[k]) ? x.a[k] - x.h[k] : null));
      const cell = (k) => `${pp(med(dd(k)))} ｜ ${f(100 * med(dd(k).map((v) => (ok(v) ? Math.abs(v) : null))), 0)}`;
      const rr = (k) => a.map((x) => div(x.a[k], x.h[k]));
      rows2.push([CLS[c], fl === 'auto' ? 'auto（缺省）' : fl, String(a.length), cell('batchShare'), cell('gap0'), cell('dupShare'), cell('atkVoidRate'),
        `${sgn(med(dd('dumpPerSeat')))} ｜ ${f(med(dd('dumpPerSeat').map((v) => (ok(v) ? Math.abs(v) : null))))}`, f(med(rr('recPerSeat'))), f(med(rr('terr1')))]);
      val(`fill.${c}.${fl}.batchAbs`, f(100 * med(dd('batchShare').map((v) => (ok(v) ? Math.abs(v) : null))), 0));
      val(`fill.${c}.${fl}.batch`, pp(med(dd('batchShare'))));
      val(`fill.${c}.${fl}.n`, a.length);
    }
    table('chan-fill', ['卡顿档', '补法', '局数', '同拍批占比', '同回合连发占比', '重复单占比', '陆攻落空率', '清仓批 ÷ 席位', '进录像条数 模拟 ÷ 真局', '窗口末编队领土 模拟 ÷ 真局'], rows2,
      '窗口 630~1530 拍。占比类每格 = 各局「模拟 − 真局」的中位（百分点，带正负号）｜ 各局差的绝对值的中位（百分点）；清仓批同样两个数（每席位的批数）。最后两列是各局比值的中位。');
  }
}

// =====================================================================================================================
// 四、断面保真度：630 / 1530 × C0 / C1 / C2 / C3
// =====================================================================================================================
const RATE_TOL = 0.10;
const hitOf = (type, s, h) => {
  if (!ok(s) || !ok(h)) return null;
  if (type === 'rate') return Math.abs(s - h) <= RATE_TOL;
  if (type === 'cnt') return (s <= 0.2 && h <= 0.2) || (h > 0 && s / h >= 0.5 && s / h <= 2);
  return null;
};
if (want('ckpt')) {
  // 逐局：C2（本局实录阶梯）对这一局当年的真值
  for (const [t0, name] of [[630, 'ckpt-c2-630'], [1530, 'ckpt-c2-1530']]) {
    const rows = [];
    for (const mid of MIDS) {
      const x = G0.find((y) => y.mid === mid && y.t0 === t0 && y.arm === 'C2');
      if (!x) continue;
      rows.push([mid + (CORE.has(mid) ? '' : ' ＋'), VER[x.co], CLS[clsOf(mid)] || '?', `${x.t0}~${x.t1}`, String(x.a.seats),
        ...SIGS.map(([k, , , fm]) => `${fm(x.a[k])} / ${fm(x.h[k])}`), f(div(x.a.terr1, x.h.terr1)), pc(x.a.othersAsRec)]);
    }
    table(name, ['局', '版本', '卡顿档', '窗口', '席位', ...SIGS.map((s) => s[1]), '窗口末编队领土 模拟 ÷ 真局', '其余真人陆攻照录像执行'], rows,
      '每格：模拟（当年那一版策略 + 这一局的实录阶梯 C2）/ 这一局当年的真值（录像）。真局的重复单占比来自实录配对（要下令拍）；真局的「捐款没成交占比」= 1 − 录像里的捐款条数 ÷ 策略日志 `[HL-DISPATCH]` 的条数，只有 c116 系（Va / Vb / Vc）打这条日志。最后一列 = 这条臂里其余真人的陆攻有几成还能照录像原样执行（其余的目标已出局或已不接壤，改打身边最便宜的内置 AI / 无主地，或作废）。');
  }
  // 汇总：通道 × 卡顿档 × 窗口，模拟 − 真局
  const rows = [];
  const hitRows = [];
  for (const t0 of [630, 1530]) for (const c of ['clean', 'mid', 'lag']) for (const arm of ['C2', 'C1', 'C0', 'C3']) {
    const a = G0.filter((x) => x.t0 === t0 && x.arm === arm && clsOf(x.mid) === c);
    if (!a.length) continue;
    const cells = SIGS.map(([k, , type]) => {
      if (type === 'rate') { const d = a.map((x) => (ok(x.a[k]) && ok(x.h[k]) ? x.a[k] - x.h[k] : null)); return clean(d).length ? `${pp(med(d))} ｜ ${f(100 * med(d.map((v) => (ok(v) ? Math.abs(v) : null))), 0)}` : '-'; }
      const r = a.map((x) => (k === 'dumpPerSeat' ? (ok(x.a[k]) && ok(x.h[k]) ? x.a[k] - x.h[k] : null) : div(x.a[k], x.h[k])));
      if (!clean(r).length) return '-';
      return k === 'dumpPerSeat' ? `${sgn(med(r))} ｜ ${f(med(r.map((v) => (ok(v) ? Math.abs(v) : null))))}` : `×${f(med(r))}`;
    });
    const tr = a.map((x) => div(x.a.terr1, x.h.terr1));
    rows.push([t0 === 630 ? '630~1530' : '1530~3210', CLS[c], arm, String(a.length), ...cells, `×${f(med(tr))}（${f(q(tr, 0.25))}~${f(q(tr, 0.75))}）`]);
    // 容差命中
    const hr = [t0 === 630 ? '630~1530' : '1530~3210', CLS[c], arm, String(a.length)];
    let H = 0, N = 0;
    for (const [k, , type] of SIGS) {
      if (type === 'lvl') continue;
      const hs = a.map((x) => hitOf(type, x.a[k], x.h[k])).filter((v) => v !== null);
      hr.push(hs.length ? `${hs.filter(Boolean).length} / ${hs.length}` : '-');
      H += hs.filter(Boolean).length; N += hs.length;
    }
    const tin = tr.filter((v) => ok(v) && v >= 0.9 && v <= 1.1).length;
    hr.push(`${tin} / ${clean(tr).length}`);
    hr.push(`${H} / ${N}（${pc(H / N)}）`);
    hitRows.push(hr);
    val(`ckpt.${t0}.${c}.${arm}.hit`, `${H} / ${N}`); val(`ckpt.${t0}.${c}.${arm}.hitPc`, pc(H / N)); val(`ckpt.${t0}.${c}.${arm}.n`, a.length);
    val(`ckpt.${t0}.${c}.${arm}.terr`, f(med(tr))); val(`ckpt.${t0}.${c}.${arm}.terrIn`, `${tin} / ${clean(tr).length}`);
    for (const k of ['dupShare', 'batchShare', 'atkVoidRate', 'gap0']) {
      const d = a.map((x) => (ok(x.a[k]) && ok(x.h[k]) ? x.a[k] - x.h[k] : null));
      val(`ckpt.${t0}.${c}.${arm}.${k}.abs`, f(100 * med(d.map((v) => (ok(v) ? Math.abs(v) : null))), 0));
      val(`ckpt.${t0}.${c}.${arm}.${k}.sim`, pc(med(a.map((x) => x.a[k])))); val(`ckpt.${t0}.${c}.${arm}.${k}.real`, pc(med(a.map((x) => x.h[k]))));
    }
  }
  table('ckpt-err', ['窗口', '卡顿档', '通道', '运行数', ...SIGS.map((s) => s[1]), '窗口末编队领土 模拟 ÷ 真局'], rows,
    '占比类每格 = 各局「模拟 − 真局」的中位（百分点，带正负号）｜ 各局差的绝对值的中位（百分点）。进录像条数、人均相对领土 = 各局「模拟 ÷ 真局」的中位。清仓批 = 每席位批数之差的中位 ｜ 绝对值的中位。最后一列 = 中位（P25~P75）。');
  table('ckpt-hit', ['窗口', '卡顿档', '通道', '运行数', ...SIGS.filter((s) => s[2] !== 'lvl').map((s) => s[1]), '窗口末编队领土在真局的 ±10% 内', '合计（不含领土）'], hitRows,
    '每格 = 落在容差内的运行数 / 有数的运行数。容差（会审提案 §1.2 写下的讨论起点）：占比类与真局相差不超过 10 个百分点；计数类（进录像条数、清仓批）与真局同一量级，这里取 0.5~2 倍，两边每席位都不到 0.2 批的也算。');

  // 按版本汇总：C2 对真局（两个窗口合并）
  const vrows = [];
  for (const co of VORDER) for (const t0 of [630, 1530]) {
    const a = G0.filter((x) => x.co === co && x.arm === 'C2' && x.t0 === t0);
    if (!a.length) continue;
    let H = 0, N = 0;
    const cells = [];
    for (const [k, , type] of SIGS) {
      if (type === 'lvl') continue;
      const hs = a.map((x) => hitOf(type, x.a[k], x.h[k])).filter((v) => v !== null);
      cells.push(hs.length ? `${hs.filter(Boolean).length} / ${hs.length}` : '-');
      H += hs.filter(Boolean).length; N += hs.length;
    }
    const tr = a.map((x) => div(x.a.terr1, x.h.terr1));
    vrows.push([VER[co], t0 === 630 ? '630~1530' : '1530~3210', String(a.length), ...cells, `×${f(med(tr))}（${f(q(tr, 0.25))}~${f(q(tr, 0.75))}）`, `${H} / ${N}（${pc(H / N)}）`]);
    val(`ckpt.ver.${co}.${t0}.hit`, `${H} / ${N}`); val(`ckpt.ver.${co}.${t0}.hitPc`, pc(H / N)); val(`ckpt.ver.${co}.${t0}.n`, a.length); val(`ckpt.ver.${co}.${t0}.terr`, f(med(tr)));
  }
  table('ckpt-ver', ['版本', '窗口', '局数', ...SIGS.filter((s) => s[2] !== 'lvl').map((s) => s[1]), '窗口末编队领土 模拟 ÷ 真局', '合计（不含领土）'], vrows,
    '通道 C2（本局实录阶梯）。每格 = 落在容差内的局数 / 有数的局数；领土一列 = 各局比值的中位（P25~P75）。');

  // 计数的合计（会审提案 §1.2 自检表的口径：批数、清仓批、顶到 9 条的批、进录像条数）：C2 对真局，按版本
  const crow = [];
  for (const co of VORDER) for (const t0 of [630, 1530]) {
    const a = G0.filter((x) => x.co === co && x.arm === 'C2' && x.t0 === t0);
    if (!a.length) continue;
    const S = (k, w) => sum(a.map((x) => x[w][k]));
    crow.push([VER[co], t0 === 630 ? '630~1530' : '1530~3210', String(a.length), `${int(S('recorded', 'a'))} / ${int(S('recorded', 'h'))}`, `${int(S('batches', 'a'))} / ${int(S('batches', 'h'))}`,
      `${int(S('dumpBatches', 'a'))} / ${int(S('dumpBatches', 'h'))}`, `${int(S('fullBatches', 'a'))} / ${int(S('fullBatches', 'h'))}`, `${k1(S('dumpCost', 'a'))} / ${k1(S('dumpCost', 'h'))}`]);
    for (const k of ['recorded', 'batches', 'dumpBatches', 'fullBatches']) val(`ckpt.sum.${co}.${t0}.${k}`, `${int(S(k, 'a'))} / ${int(S(k, 'h'))}`);
  }
  table('ckpt-counts', ['版本', '窗口', '局数', '进录像的指令', '同拍批（≥ 3 条）', '清仓批', '顶到 9 条的批', '清仓批抽走的兵'], crow, '每格：各局合计，模拟（C2）/ 真局。');

  // 任务卡点名的那 60 次（tools/g0_list.txt）：按通道汇总
  {
    const CARD = new Set(fs.readFileSync(path.join(HERE, 'g0_list.txt'), 'utf8').split('\n').filter((l) => l && !l.startsWith('#')).map((l) => l.split(/\s+/)[0]));
    const crows = [];
    for (const [arm, label] of [['C2', 'C2 本局实录阶梯（对这一局的真值）'], ['C1', 'C1 正常延迟，挂在不卡的局上（对这一局的真值）'], ['C3', 'C3 合成卡顿波，挂在不卡的局上（对这一局的真值：应当对不上）']]) {
      for (const t0 of [630, 1530]) {
        const a = G0.filter((x) => CARD.has(x.tag) && x.arm === arm && x.t0 === t0);
        if (!a.length) continue;
        let H = 0, N = 0;
        for (const [k, , type] of SIGS) {
          if (type === 'lvl') continue;
          const hs = a.map((x) => hitOf(type, x.a[k], x.h[k])).filter((v) => v !== null);
          H += hs.filter(Boolean).length; N += hs.length;
        }
        const tr = a.map((x) => div(x.a.terr1, x.h.terr1));
        const tin = tr.filter((v) => ok(v) && v >= 0.9 && v <= 1.1).length;
        crows.push([label, t0 === 630 ? '630~1530' : '1530~3210', String(a.length), [...new Set(a.map((x) => x.mid))].length + ' 局', `${H} / ${N}（${pc(H / N)}）`, `${tin} / ${clean(tr).length}`, `×${f(med(tr))}（${f(q(tr, 0.25))}~${f(q(tr, 0.75))}）`]);
        val(`card.${arm}.${t0}.n`, a.length); val(`card.${arm}.${t0}.hit`, `${H} / ${N}`); val(`card.${arm}.${t0}.hitPc`, pc(H / N)); val(`card.${arm}.${t0}.terrIn`, `${tin} / ${clean(tr).length}`);
        val(`card.${arm}.${t0}.terr`, f(med(tr)));
      }
    }
    table('ckpt-card', ['通道', '窗口', '运行数', '局数', '签名落在容差内', '窗口末编队领土在真局的 ±10% 内', '窗口末编队领土 模拟 ÷ 真局'], crows,
      '这 60 次是任务卡点名的那一组（清单 `tools/g0_list.txt`）：C2 跑遍核心 20 局里录像够长的局，C1 与 C3 只挂在不卡的局上。容差与上表相同。');
    val('card.n', G0.filter((x) => CARD.has(x.tag)).length);
  }

  // C2 对不上的局：偏差集中在几个席位上？实录阶梯在窗口里有没有「看不见」的一段？
  {

    const blindOf = (mid, t0, t1) => {
      // 一个席位最后一个已知点之后，实录阶梯假定页面已追平。如果那个已知点上页面还落后很多（> 28 拍）、而席位和页面都还在，
      // 那之后到窗口末就是「看不见还在卡」的一段。返回这一段占 窗口内席位·拍 的份额、涉及的席位数、那些席位最后一个已知点上的落后中位。
      const tf = path.join(SIMV2, 'traces', `${mid}.json`);
      if (!fs.existsSync(tf)) return null;
      const T = readJson(tf), pk = PACK[mid];
      let blind = 0, tot = 0, n = 0;
      const lags = [];
      for (const [p, rs] of Object.entries(T.seats)) {
        if (!rs.length) continue;
        const d = (pk.deathT || {})[p] ?? -1, ll = (T.lastLog || {})[p];
        const end = Math.min(t1, d >= 0 ? d : Infinity, ok(ll) && ll >= 0 ? ll + 89 : Infinity);
        if (end <= t0) continue;
        tot += end - t0;
        let last = rs[0];
        for (const r of rs) if (r[1] > last[1]) last = r;
        const lag = last[1] - last[0] - 12;
        if (lag > 28 && last[1] < end) { blind += end - Math.max(t0, last[1]); n++; lags.push(lag); }
      }
      return { share: tot ? blind / tot : 0, seats: n, lag: med(lags) };
    };
    const orow = [];
    const devs = { blind: [], seen: [] };
    for (const x of G0) {
      if (x.arm !== 'C2') continue;
      const ratio = div(x.a.terr1, x.h.terr1);
      const b = blindOf(x.mid, x.t0, x.t1);
      if (ok(ratio) && b) devs[b.share >= 0.1 ? 'blind' : 'seen'].push(Math.abs(Math.log(ratio)));
      if (!ok(ratio) || (ratio >= 0.9 && ratio <= 1.1)) continue;
      // 偏差集中度：各席位「模拟 − 真局」的地，绝对值最大的那个席位占全部绝对偏差的份额
      const hp = new Map((x.r.history.perSeat || []).map((s) => [s.p, s.terr1]));
      const ds = (x.r.arms.baseline.perSeat || []).map((s) => s.terr1 - (hp.get(s.p) ?? 0));
      const absSum = sum(ds.map(Math.abs));
      const top = absSum ? Math.max(...ds.map(Math.abs)) / absSum : null;
      const top2 = absSum ? ds.map(Math.abs).sort((p1, p2) => p2 - p1).slice(0, 2).reduce((p1, p2) => p1 + p2, 0) / absSum : null;
      // 偏差最大的那个席位：它在别的通道臂里是不是也偏在同一边（是 → 不是通道的事）
      const seatsP = (x.r.arms.baseline.perSeat || []).map((sx) => sx.p);
      const topP = seatsP[ds.map(Math.abs).indexOf(Math.max(...ds.map(Math.abs)))];
      const topBy = {};
      for (const arm of ['C0', 'C1', 'C2']) {
        const z = G0.find((w) => w.mid === x.mid && w.t0 === x.t0 && w.arm === arm);
        const sz = z && (z.r.arms.baseline.perSeat || []).find((w) => w.p === topP);
        topBy[arm] = sz ? sz.terr1 : null;
        val(`out.${x.mid}.${x.t0}.topLand.${arm}`, ok(topBy[arm]) ? int(topBy[arm]) : '-');
      }
      const topHist = hp.get(topP) ?? 0;
      val(`out.${x.mid}.${x.t0}.topSeat`, topP); val(`out.${x.mid}.${x.t0}.topLand.hist`, int(topHist));
      // 这个席位在窗口里最长多少拍没有已知点（按下令拍，窗口两端也算）；全队各席位这个量的中位作参照
      {
        const tf = path.join(SIMV2, 'traces', `${x.mid}.json`);
        const T = fs.existsSync(tf) ? readJson(tf) : null;
        const gapOf = (pp0) => {
          const rs = T && T.seats[String(pp0)];
          if (!rs) return null;
          const pts = [x.t0, ...rs.map((r) => r[0]).filter((t) => t >= x.t0 && t <= x.t1).sort((p1, p2) => p1 - p2), x.t1];
          let g = 0;
          for (let i = 1; i < pts.length; i++) g = Math.max(g, pts[i] - pts[i - 1]);
          return g;
        };
        const tg = gapOf(topP), mg = med(seatsP.map(gapOf));
        val(`out.${x.mid}.${x.t0}.topGap`, ok(tg) ? int(tg) : '-'); val(`out.${x.mid}.${x.t0}.medGap`, ok(mg) ? int(mg) : '-');
      }
      // 真局里窗口末已经没地、模拟里还有地的席位（「多活下来的」）：几个，去掉它们之后编队领土是真局的几倍
      const rv = (x.r.arms.baseline.perSeat || []).filter((sx) => sx.terr1 > 0 && !((hp.get(sx.p) ?? 0) > 0));
      const rvLand = sum(rv.map((sx) => sx.terr1));
      const ratioEx = div(x.a.terr1 - rvLand, x.h.terr1);
      val(`out.${x.mid}.${x.t0}.revived`, rv.length); val(`out.${x.mid}.${x.t0}.ratioEx`, ok(ratioEx) ? f(ratioEx) : '-');
      // 这个席位在跑过的每一档通道下，是不是都偏在真局的同一边
      const sides = ['C0', 'C1', 'C2'].filter((arm) => ok(topBy[arm])).map((arm) => Math.sign(topBy[arm] - topHist));
      val(`out.${x.mid}.${x.t0}.topSameSide`, sides.length >= 2 && sides.every((v) => v === sides[0] && v !== 0) ? '是' : sides.length < 2 ? '只跑了一档' : '否');
      orow.push([x.mid + (CORE.has(x.mid) ? '' : ' ＋'), VER[x.co], CLS[clsOf(x.mid)] || '?', `${x.t0}~${x.t1}`, `×${f(ratio)}`, `${f(x.a.recPerSeat, 1)} / ${f(x.h.recPerSeat, 1)}`,
        `${x.a.alive1} / ${x.h.alive1}`, `${pc(top)}（前两个 ${pc(top2)}）`, `${int(topHist)} ｜ ${['C0', 'C1', 'C2'].map((arm) => (ok(topBy[arm]) ? int(topBy[arm]) : '-')).join(' / ')}`,
        rv.length ? `${rv.length} 个，去掉后 ×${f(ratioEx)}` : '0 个',
        b ? `${pc(b.share)}（${b.seats} 个席位，当时落后 ${ok(b.lag) ? f(b.lag, 0) : '-'} 拍）` : '-']);
      val(`out.${x.mid}.${x.t0}.ratio`, f(ratio)); val(`out.${x.mid}.${x.t0}.top`, pc(top)); val(`out.${x.mid}.${x.t0}.top2`, pc(top2));
      if (b) { val(`out.${x.mid}.${x.t0}.blind`, pc(b.share)); val(`out.${x.mid}.${x.t0}.blindSeats`, b.seats); val(`out.${x.mid}.${x.t0}.blindLag`, ok(b.lag) ? f(b.lag, 0) : '-'); }
    }
    table('ckpt-out', ['局', '版本', '卡顿档', '窗口', '窗口末编队领土 模拟 ÷ 真局', '进录像条数 ÷ 席位 模拟 / 真局', '窗口末在场席位 模拟 / 真局', '偏差最大的一个席位占全部偏差', '这个席位窗口末的地：真局 ｜ C0 / C1 / C2', '真局已出局、模拟里还在的席位', '最后一个已知点之后看不见的一段'], orow,
      '只列 C2 臂里窗口末编队领土偏出真局 ±10% 的运行。「偏差最大的一个席位」= 各席位（模拟 − 真局）的地取绝对值，最大那个占总和的份额；后一列是这同一个席位窗口末的地：真局多少，三档通道下的模拟各多少（没跑的臂记 -）。「真局已出局、模拟里还在的席位」= 窗口末真局里已经没有地、模拟里还有地的我方席位；「去掉后」= 把这些席位的地从模拟的编队领土里拿掉，再除以真局。「看不见的一段」= 某席位最后一个已知点上页面还落后 28 拍以上，而这之后席位和页面都还在：阶梯在已知点之后假定页面追平，这一段的落后模拟不出来；格里是这一段占窗口内全部 席位·拍 的份额。');
    val('out.n', orow.length);
    for (const t0 of [630, 1530]) {
      let rvN = 0, lostN = 0, seats = 0, runs = 0, runsRv = 0;
      const exIn = [];
      for (const x of G0) {
        if (x.arm !== 'C2' || x.t0 !== t0) continue;
        const hp = new Map((x.r.history.perSeat || []).map((sx) => [sx.p, sx.terr1]));
        const ps = x.r.arms.baseline.perSeat || [];
        const rv = ps.filter((sx) => sx.terr1 > 0 && !((hp.get(sx.p) ?? 0) > 0));
        const lost = ps.filter((sx) => !(sx.terr1 > 0) && (hp.get(sx.p) ?? 0) > 0);
        runs++; seats += ps.length; rvN += rv.length; lostN += lost.length; if (rv.length) runsRv++;
        const r0 = div(x.a.terr1, x.h.terr1), r1 = div(x.a.terr1 - sum(rv.map((sx) => sx.terr1)), x.h.terr1);
        if (ok(r0)) exIn.push([r0 >= 0.9 && r0 <= 1.1 ? 1 : 0, ok(r1) && r1 >= 0.9 && r1 <= 1.1 ? 1 : 0]);
      }
      val(`revived.${t0}.runs`, runs); val(`revived.${t0}.seats`, seats); val(`revived.${t0}.n`, rvN); val(`revived.${t0}.lost`, lostN); val(`revived.${t0}.runsWith`, runsRv);
      val(`revived.${t0}.in`, `${sum(exIn.map((e) => e[0]))} / ${exIn.length}`); val(`revived.${t0}.inEx`, `${sum(exIn.map((e) => e[1]))} / ${exIn.length}`);
    }
    val('blind.n', devs.blind.length); val('blind.dev', devs.blind.length ? pc(Math.exp(med(devs.blind)) - 1) : '-');
    val('seen.n', devs.seen.length); val('seen.dev', devs.seen.length ? pc(Math.exp(med(devs.seen)) - 1) : '-');
    val('blind.dev90', devs.blind.length ? pc(Math.exp(q(devs.blind, 0.9)) - 1) : '-'); val('seen.dev90', devs.seen.length ? pc(Math.exp(q(devs.seen, 0.9)) - 1) : '-');

    // 对照：最后一个已知点之后「追平」（缺省）换成「保持那时的落后」（C2:after=hold）
    if (HOLD.length) {
      const hrow = [];
      let between = 0, nOut = 0, closer = 0, nBlind = 0, outMoved = 0, sigDef = 0, sigHold = 0, sigTie = 0, recDef = 0, recHold = 0;
      const bsDef = [], bsHold = [];
      for (const y of HOLD) {
        const x = G0.find((z) => z.mid === y.mid && z.t0 === y.t0 && z.arm === 'C2');
        if (!x) { notes.push(`hold/${y.tag}：没有对应的缺省 C2 运行`); continue; }
        const b = blindOf(x.mid, x.t0, x.t1);
        const rd = div(x.a.terr1, x.h.terr1), rh = div(y.a.terr1, y.h.terr1);
        const out = ok(rd) && (rd < 0.9 || rd > 1.1);
        if (out) { nOut++; if (Math.min(rd, rh) <= 1 && Math.max(rd, rh) >= 1) between++; if (ok(rh) && rh >= 0.9 && rh <= 1.1) outMoved++; }
        if (b && b.share >= 0.1) {
          nBlind++;
          if (Math.abs(Math.log(rh)) < Math.abs(Math.log(rd)) - 0.02) closer++;
          // 看不见的一段占得多的运行：两种假定各自的签名离真局多远
          const dD = Math.abs(x.a.batchShare - x.h.batchShare), dH = Math.abs(y.a.batchShare - y.h.batchShare);
          if (ok(dD) && ok(dH)) { bsDef.push(dD); bsHold.push(dH); if (dD < dH - 0.02) sigDef++; else if (dH < dD - 0.02) sigHold++; else sigTie++; }
          const cD = Math.abs(Math.log(div(x.a.recPerSeat, x.h.recPerSeat))), cH = Math.abs(Math.log(div(y.a.recPerSeat, y.h.recPerSeat)));
          if (ok(cD) && ok(cH)) { if (cD < cH - 0.02) recDef++; else if (cH < cD - 0.02) recHold++; }
        }
        hrow.push([x.mid + (CORE.has(x.mid) ? '' : ' ＋'), `${x.t0}~${x.t1}`, b ? pc(b.share) : '-', `×${f(rd)} → ×${f(rh)}`,
          `${f(x.a.recPerSeat, 1)} → ${f(y.a.recPerSeat, 1)} ｜ ${f(x.h.recPerSeat, 1)}`, `${pc(x.a.batchShare)} → ${pc(y.a.batchShare)} ｜ ${pc(x.h.batchShare)}`,
          `${pc(x.a.atkVoidRate)} → ${pc(y.a.atkVoidRate)} ｜ ${pc(x.h.atkVoidRate)}`, `${x.a.alive1} → ${y.a.alive1} ｜ ${x.h.alive1}`]);
        val(`hold.${x.mid}.${x.t0}.def`, f(rd)); val(`hold.${x.mid}.${x.t0}.hold`, f(rh));
        val(`hold.${x.mid}.${x.t0}.rec`, `${f(x.a.recPerSeat, 1)} → ${f(y.a.recPerSeat, 1)}`); val(`hold.${x.mid}.${x.t0}.recReal`, f(x.h.recPerSeat, 1));
      }
      table('ckpt-hold', ['局', '窗口', '看不见的一段', '窗口末编队领土 模拟 ÷ 真局：追平 → 保持', '进录像条数 ÷ 席位：追平 → 保持 ｜ 真局', '同拍批占比：追平 → 保持 ｜ 真局', '陆攻落空率：追平 → 保持 ｜ 真局', '窗口末在场席位：追平 → 保持 ｜ 真局'], hrow,
        '「追平」= 缺省的 C2（一个席位最后一个已知点之后，页面在那个已知点的执行拍上一口气追平）；「保持」= `C2:after=hold`（之后一直保持那个已知点上的落后）。这是两头的假定：一头是卡顿在最后一个已知点上立刻退掉，一头是一直不退。清单由 `tools/hold_list.py` 按规则挑出（看不见的一段 ≥ 5%，或缺省 C2 的窗口末领土偏出 ±10%）。');
      val('hold.n', hrow.length); val('hold.out', nOut); val('hold.between', between); val('hold.blind', nBlind); val('hold.closer', closer);
      val('hold.outMoved', outMoved);
      val('hold.sig.def', sigDef); val('hold.sig.hold', sigHold); val('hold.sig.tie', sigTie);
      val('hold.sig.defAbs', bsDef.length ? f(100 * med(bsDef), 0) : '-'); val('hold.sig.holdAbs', bsHold.length ? f(100 * med(bsHold), 0) : '-');
      val('hold.rec.def', recDef); val('hold.rec.hold', recHold);
    }
  }

  // 实盘区间命中：模拟值与真值各有多少落在同版本、同卡顿档的 P25~P75 里
  if (BANDS) {
    const keys = ['recPerSeat', 'batchShare', 'gap0', 'dumpPerSeat', 'atkVoidRate', 'atkNeutralShare', 'relTerr1', 'aliveShare'];
    const rows3 = [];
    for (const [arm, bandCls, games, label] of [
      ['C1', 'clean', 'clean', 'C1，不卡的局 → 不卡档区间'],
      ['C2', 'clean', 'clean', 'C2，不卡的局 → 不卡档区间'],
      ['C2', 'lag', 'lag', 'C2，卡顿的局 → 卡顿档区间'],
      ['C3', 'lag', 'clean', 'C3（合成卡顿波），不卡的局 → 卡顿档区间'],
      ['C1', 'lag', 'lag', 'C1，卡顿的局 → 卡顿档区间（反例）'],
    ]) {
      for (const t0 of [630, 1530]) {
        const a = G0.filter((x) => x.arm === arm && x.t0 === t0 && clsOf(x.mid) === games && x.t1 === (t0 === 630 ? 1530 : 3210));
        if (!a.length) continue;
        let Hs = 0, Hh = 0, N = 0;
        const cells = keys.map((k) => {
          let hs = 0, hh = 0, n = 0;
          for (const x of a) {
            const g = BANDS.cohorts[`${x.co}|${bandCls}|${t0 === 630 ? '630~1530' : '1530~3210'}`];
            const b = g && g.band[k];
            if (!b || b[3] < 4 || !ok(x.a[k]) || !ok(x.h[k])) continue;
            n++;
            if (x.a[k] >= b[0] - 1e-9 && x.a[k] <= b[2] + 1e-9) hs++;
            if (x.h[k] >= b[0] - 1e-9 && x.h[k] <= b[2] + 1e-9) hh++;
          }
          Hs += hs; Hh += hh; N += n;
          return n ? `${hs} ｜ ${hh} / ${n}` : '-';
        });
        rows3.push([label, t0 === 630 ? '630~1530' : '1530~3210', String(a.length), ...cells, N ? `${pc(Hs / N)} ｜ ${pc(Hh / N)}` : '-']);
        // 键：band.<臂>.<哪一档的局>.<对哪一档区间>.<t0>.sim / .real
        val(`band.${arm}.${games}.${bandCls}.${t0}.sim`, N ? pc(Hs / N) : '-'); val(`band.${arm}.${games}.${bandCls}.${t0}.real`, N ? pc(Hh / N) : '-');
        val(`band.${arm}.${games}.${bandCls}.${t0}.n`, N);
      }
    }
    table('ckpt-bands', ['模拟臂 → 对哪一档区间', '窗口', '运行数', ...keys.map((k) => SIGS.find((s) => s[0] === k)?.[1] || LIVE_SIG.find((s) => s[0] === k)[1]), '合计命中率'], rows3,
      '区间 = 全部有录像的局里同一版本、同一卡顿档的 P25~P75（局数不足 4 的不判）。每格：模拟值落在区间内的运行数 ｜ 同一批局的真值落在区间内的局数 / 判过的数。区间只盖住中间一半的局，所以真值自己的命中率也只在一半上下——拿它当参照。');
  }
}

// =====================================================================================================================
// 五、通道延迟归因：0 / 630 / 1500 / 4284 四个断面
// =====================================================================================================================
const CPS = [0, 630, 1500, 4284];
const WIN = { 0: '0~630', 630: '630~1500', 1500: '1500~2400', 4284: '4284~5184' };
if (want('attr') && ATTR.length) {
  // 每局每断面：各臂的结果（多个种子取平均），历史臂取任一条
  const cell = new Map();   // `${mid}|${t0}` → { h, arms: {C0:[..], C1:[..], C2:[..], C2nd:[..], C3:[..]} }
  for (const x of ATTR) {
    const k = `${x.mid}|${x.t0}`;
    let c = cell.get(k);
    if (!c) cell.set(k, (c = { mid: x.mid, t0: x.t0, t1: x.t1, h: x.h, hr: x.r.history, arms: {} }));
    (c.arms[x.arm] = c.arms[x.arm] || []).push(x);
  }
  const cells = [...cell.values()];
  const avg = (c, arm, k) => (c.arms[arm] ? mean(c.arms[arm].map((x) => x.a[k])) : null);
  const terrR = (c, arm) => div(avg(c, arm, 'terr1'), c.h.terr1);
  // C2nd：没有页面中途停摆的局不另跑，就等于 C2 的种子 1
  const c2nd = (c, k) => (c.arms.C2nd ? avg(c, 'C2nd', k) : c.arms.C2 ? c.arms.C2.find((x) => x.seed === 1)?.a[k] ?? avg(c, 'C2', k) : null);

  // 覆盖
  const cov = [];
  for (const t0 of CPS) {
    const cs = cells.filter((c) => c.t0 === t0);
    const n = (arm) => cs.filter((c) => c.arms[arm]).length;
    const runs = (arm) => sum(cs.map((c) => (c.arms[arm] ? c.arms[arm].length : 0)));
    cov.push([String(t0), WIN[t0], String(cs.length), `${n('C0')}（${runs('C0')}）`, `${n('C1')}（${runs('C1')}）`, `${n('C2')}（${runs('C2')}）`, `${n('C2nd')}（${runs('C2nd')}）`, `${n('C3')}（${runs('C3')}）`,
      String(ATTR.filter((x) => x.t0 === t0 && x.truncated).length)]);
    val(`attr.${t0}.games`, cs.length);
  }
  table('attr-cover', ['断面 t0', '窗口', '局数', 'C0 即时', 'C1 正常延迟', 'C2 实录阶梯', 'C2 关掉页面停摆', 'C3 合成卡顿波', '被时间预算截断的运行'], cov,
    '每格：有这条臂的局数（运行数，含换种子的重复）。窗口不足 300 拍的局不跑；C2 只在实录阶梯还盖得到这个窗口的局跑（A 组的实录到 3700 拍前后为止）；「关掉页面停摆」只在有页面中途停摆的局跑；C3 只在不卡的局、卡顿波所在的两个断面跑。');
  val('attr.runs', ATTR.length); val('attr.trunc', ATTR.filter((x) => x.truncated).length);

  // 噪声底：C2 对历史（同一条通道、同一版策略，本该重现历史）；种子之间的散布
  const nrow = [];
  for (const t0 of CPS) for (const [arm, pick, label] of [['C2', () => true, 'C2 实录阶梯，全部局'], ['C1', (c) => clsOf(c.mid) === 'clean', 'C1 正常延迟，不卡的局']]) {
    const cs = cells.filter((c) => c.t0 === t0 && c.arms[arm] && pick(c));
    if (!cs.length) continue;
    const r = cs.map((c) => terrR(c, arm));
    const spread = cs.filter((c) => c.arms[arm].length >= 2).map((c) => { const v = c.arms[arm].map((x) => div(x.a.terr1, c.h.terr1)); return Math.max(...v) - Math.min(...v); });
    const al = cs.map((c) => avg(c, arm, 'alive1') - c.h.alive1);
    const rel = cs.map((c) => avg(c, arm, 'relTerr1') - c.h.relTerr1);
    nrow.push([String(t0), WIN[t0], label, String(cs.length), `${f(q(r, 0.1))} / ${f(q(r, 0.25))} / ${f(med(r))} / ${f(q(r, 0.75))} / ${f(q(r, 0.9))}`,
      f(100 * med(r.map((v) => Math.abs(v - 1))), 0) + '%', `${r.filter((v) => v >= 0.9 && v <= 1.1).length} / ${r.length}`, spread.length ? `${f(100 * med(spread), 0)}%（${spread.length} 局）` : '-', sgn(med(rel), 3), sgn(sum(al), 1), int(sum(cs.map((c) => c.h.alive1)))]);
    val(`attr.noise.${t0}.${arm}.med`, f(med(r))); val(`attr.noise.${t0}.${arm}.abs`, f(100 * med(r.map((v) => Math.abs(v - 1))), 0));
    val(`attr.noise.${t0}.${arm}.in10`, `${r.filter((v) => v >= 0.9 && v <= 1.1).length} / ${r.length}`); val(`attr.noise.${t0}.${arm}.n`, cs.length);
    val(`attr.noise.${t0}.${arm}.spread`, spread.length ? f(100 * med(spread), 0) : '-');
    val(`attr.noise.${t0}.${arm}.range`, `${f(q(r, 0.1))}~${f(q(r, 0.9))}`);
  }
  table('attr-noise', ['断面 t0', '窗口', '复现臂', '局数', '窗口末编队领土 复现 ÷ 历史：P10 / P25 / 中位 / P75 / P90', '偏离 1 的中位', '落在 ±10% 内的局', '同一局换种子的最大 − 最小（中位）', '人均相对领土 复现 − 历史（中位）', '在场席位 复现 − 历史（各局合计）', '历史在场席位（合计）'], nrow,
    '复现臂跑的是这一局当年那一版策略、当年那条通道，本该重现历史；它与历史的差就是「模拟器 + 开环重放其余真人」这套办法自身的误差，后面各通道之间的差要比它大才算数。换种子只换通道里 d 的抽样（C1 / C2 各 3 个种子）。');

  // 归因链：C0 → C1 → C2（关掉页面停摆）→ C2 → 历史
  const chain = [];
  for (const t0 of CPS) for (const c of ['clean', 'mid', 'lag']) {
    const cs = cells.filter((x) => x.t0 === t0 && clsOf(x.mid) === c && x.arms.C0 && x.arms.C1);
    if (!cs.length) continue;
    const has2 = cs.filter((x) => x.arms.C2);
    const r0 = cs.map((x) => terrR(x, 'C0')), r1 = cs.map((x) => terrR(x, 'C1'));
    const r2 = has2.map((x) => terrR(x, 'C2')), r2n = has2.map((x) => div(c2nd(x, 'terr1'), x.h.terr1));
    const f10 = cs.map((x) => div(avg(x, 'C1', 'terr1'), avg(x, 'C0', 'terr1')));
    const f21 = has2.map((x) => div(c2nd(x, 'terr1'), avg(x, 'C1', 'terr1')));
    const f22 = has2.map((x) => div(avg(x, 'C2', 'terr1'), c2nd(x, 'terr1')));
    const fh2 = has2.map((x) => div(x.h.terr1, avg(x, 'C2', 'terr1')));
    const fh1 = cs.map((x) => div(x.h.terr1, avg(x, 'C1', 'terr1')));
    const up = has2.filter((x) => avg(x, 'C1', 'terr1') > avg(x, 'C2', 'terr1')).length;
    chain.push([String(t0), WIN[t0], CLS[c], `${cs.length}（${has2.length}）`, f(med(r0)), f(med(r1)), has2.length ? f(med(r2n)) : '-', has2.length ? f(med(r2)) : '-',
      `${rpc(med(f10))}（${rpc(q(f10, 0.25))}~${rpc(q(f10, 0.75))}）`, has2.length ? `${rpc(med(f21))}（${rpc(q(f21, 0.25))}~${rpc(q(f21, 0.75))}）` : '-',
      has2.length ? `${rpc(med(f22))}（${rpc(q(f22, 0.25))}~${rpc(q(f22, 0.75))}）` : '-', has2.length ? `${rpc(med(fh2))}` : `${rpc(med(fh1))}（对 C1）`, has2.length ? `${up} / ${has2.length}` : '-']);
    const key = `attr.chain.${t0}.${c}`;
    val(`${key}.n`, cs.length); val(`${key}.n2`, has2.length); val(`${key}.c0`, f(med(r0))); val(`${key}.c1`, f(med(r1))); val(`${key}.c2`, has2.length ? f(med(r2)) : '-'); val(`${key}.c2nd`, has2.length ? f(med(r2n)) : '-');
    val(`${key}.f10`, rpc(med(f10))); val(`${key}.f10.range`, `${rpc(q(f10, 0.25))}~${rpc(q(f10, 0.75))}`);
    val(`${key}.f21`, has2.length ? rpc(med(f21)) : '-'); val(`${key}.f21.range`, has2.length ? `${rpc(q(f21, 0.25))}~${rpc(q(f21, 0.75))}` : '-');
    val(`${key}.f22`, has2.length ? rpc(med(f22)) : '-'); val(`${key}.fh2`, has2.length ? rpc(med(fh2)) : '-'); val(`${key}.up`, has2.length ? `${up} / ${has2.length}` : '-');
    val(`${key}.f10.neg`, `${f10.filter((v) => v < 1).length} / ${f10.length}`);
    val(`${key}.c1.gt110`, `${r1.filter((v) => v > 1.1).length} / ${r1.length}`);
  }
  // 归因占比：把「即时通道 → 历史」的总差按对数拆成四段。各局的对数差取平均（= 比值的几何平均），四段相加正好等于总差。
  const share = [];
  const lmean = (a) => mean(a.map((v) => (ok(v) && v > 0 ? Math.log(v) : null)));
  for (const t0 of CPS) for (const c of ['clean', 'mid', 'lag', 'all']) {
    const cs = cells.filter((x) => x.t0 === t0 && (c === 'all' || clsOf(x.mid) === c) && x.arms.C0 && x.arms.C1 && x.arms.C2 && x.h.terr1 > 0 && avg(x, 'C0', 'terr1') > 0 && avg(x, 'C1', 'terr1') > 0 && avg(x, 'C2', 'terr1') > 0 && c2nd(x, 'terr1') > 0);
    if (cs.length < 3) continue;
    const L = [
      lmean(cs.map((x) => div(avg(x, 'C1', 'terr1'), avg(x, 'C0', 'terr1')))),
      lmean(cs.map((x) => div(c2nd(x, 'terr1'), avg(x, 'C1', 'terr1')))),
      lmean(cs.map((x) => div(avg(x, 'C2', 'terr1'), c2nd(x, 'terr1')))),
      lmean(cs.map((x) => div(x.h.terr1, avg(x, 'C2', 'terr1')))),
    ];
    const tot = L.reduce((a, b) => a + b, 0);
    const big = Math.abs(tot) >= 0.05;
    const cellOf = (v) => `${rpc(Math.exp(v))}${big ? `（${f(100 * v / tot, 0)}%）` : ''}`;
    share.push([String(t0), WIN[t0], c === 'all' ? '全部' : CLS[c], String(cs.length), rpc(Math.exp(tot)), ...L.map(cellOf)]);
    const key = `attr.share.${t0}.${c}`;
    val(`${key}.n`, cs.length); val(`${key}.tot`, rpc(Math.exp(tot)));
    L.forEach((v, i) => { val(`${key}.l${i + 1}`, rpc(Math.exp(v))); val(`${key}.s${i + 1}`, big ? f(100 * v / tot, 0) : '-'); });
  }
  table('attr-share', ['断面 t0', '窗口', '卡顿档', '局数', '历史 ÷ C0（总差）', '① 正常延迟', '② 卡顿波', '③ 页面停摆', '④ 余项'], share,
    '只收四条臂都有、窗口末各臂编队领土都大于 0 的局。每格 = 这一段比值的几何平均，写成相对变化；括号里 = 这一段的对数差占总对数差的百分比（四段相加 100%；同号表示方向与总差相同，负数表示方向相反）。总差不到 5% 时不分摊。');

  table('attr-chain', ['断面 t0', '窗口', '卡顿档', '局数（其中有 C2 的）', 'C0 ÷ 历史', 'C1 ÷ 历史', 'C2 关掉页面停摆 ÷ 历史', 'C2 ÷ 历史', '① 正常延迟：C0 → C1', '② 卡顿波：C1 → C2（关掉页面停摆）', '③ 页面停摆：→ C2', '④ 余项：C2 → 历史', 'C1 高于 C2 的局'], chain,
    '量 = 窗口末编队领土（各席位合计，出局的记 0）。前四列是各局「这条臂 ÷ 历史」的中位；①~④ 是各局相邻两级之比的中位（括号里 P25~P75），写成相对变化：① = C1 ÷ C0 − 1，② = C2（关掉页面停摆）÷ C1 − 1，③ = C2 ÷ C2（关掉页面停摆）− 1，④ = 历史 ÷ C2 − 1。多个种子的臂先在局内取平均。没有页面中途停摆的局 ③ 记 0。');

  // 逐局（630 与 1500 两个断面）
  for (const t0 of [0, 630, 1500, 4284]) {
    const rows = [];
    for (const mid of MIDS) {
      const c = cell.get(`${mid}|${t0}`);
      if (!c) continue;
      const rg = (arm) => { if (!c.arms[arm]) return '-'; const v = c.arms[arm].map((x) => div(x.a.terr1, c.h.terr1)); return v.length > 1 ? `${f(mean(v))}（${f(Math.min(...v))}~${f(Math.max(...v))}）` : f(v[0]); };
      const al = (arm) => (c.arms[arm] ? f(avg(c, arm, 'alive1'), c.arms[arm].length > 1 ? 1 : 0) : '-');
      const oa = (arm) => (c.arms[arm] ? pc(avg(c, arm, 'othersAsRec')) : '-');
      rows.push([mid + (CORE.has(mid) ? '' : ' ＋'), VER[cohortOf(mid)], CLS[clsOf(mid)] || '?', `${c.t0}~${c.t1}`, int(c.h.terr1), f(c.h.relTerr1), rg('C0'), rg('C1'), rg('C2nd'), rg('C2'), rg('C3'),
        `${c.h.alive1} ｜ ${al('C2')} ｜ ${al('C1')} ｜ ${al('C0')}`, `${oa('C2')} ｜ ${oa('C1')} ｜ ${oa('C0')}`]);
    }
    table(`attr-games-${t0}`, ['局', '版本', '卡顿档', '窗口', '历史：窗口末编队领土（格）', '历史：人均相对领土', 'C0 ÷ 历史', 'C1 ÷ 历史', 'C2 关掉页面停摆 ÷ 历史', 'C2 ÷ 历史', 'C3 ÷ 历史', '窗口末在场席位：历史 ｜ C2 ｜ C1 ｜ C0', '其余真人陆攻照录像执行：C2 ｜ C1 ｜ C0'], rows,
      '比值 = 这条臂窗口末的编队领土 ÷ 历史；有 3 个种子的臂写 平均（最小~最大）。');
  }

  // 机制指标：各臂的签名（各局中位）
  const mrow = [];
  const MK = [['recPerSeat', '进录像条数 ÷ 席位', (v) => f(v, 1)], ['dupShare', '重复单占比', pc], ['batchShare', '同拍批占比', pc], ['dumpPerSeat', '清仓批 ÷ 席位', (v) => f(v, 2)], ['atkVoidRate', '陆攻落空率', pc], ['landedShare', '进录像 ÷ 发出', pc], ['droppedPerSeat', '被 9 条顶丢弃 ÷ 席位', (v) => f(v, 2)]];
  for (const t0 of CPS) for (const c of ['clean', 'lag']) {
    const cs = cells.filter((x) => x.t0 === t0 && clsOf(x.mid) === c);
    if (!cs.length) continue;
    for (const arm of ['历史', 'C2', 'C2nd', 'C1', 'C0', 'C3']) {
      const a = arm === '历史' ? cs : cs.filter((x) => x.arms[arm]);
      if (!a.length) continue;
      const g = (x, k) => (arm === '历史' ? x.h[k] : avg(x, arm, k));
      const np = a.map((x) => (arm === '历史' ? 1 : div(avg(x, arm, 'netProd'), x.h.netProd)));
      const fa = a.map((x) => (arm === '历史' ? 1 : div(avg(x, arm, 'feeAtk'), x.h.feeAtk)));
      mrow.push([String(t0), CLS[c], arm === 'C2nd' ? 'C2 关掉页面停摆' : arm, String(a.length), ...MK.map(([k, , fm]) => (arm === '历史' && (k === 'landedShare' || k === 'droppedPerSeat') ? '-' : fm(med(a.map((x) => g(x, k)))))),
        arm === '历史' ? '1' : f(med(np)), arm === '历史' ? '1' : f(med(fa))]);
      for (const [k, , fm] of MK) val(`attr.mech.${t0}.${c}.${arm === '历史' ? 'hist' : arm}.${k}`, fm(med(a.map((x) => g(x, k)))));
      val(`attr.mech.${t0}.${c}.${arm === '历史' ? 'hist' : arm}.netProd`, arm === '历史' ? '1' : f(med(np)));
    }
  }
  table('attr-mech', ['断面 t0', '卡顿档', '臂', '局数', ...MK.map((m) => m[1]), '净产兵 ÷ 历史', '陆攻手续费 ÷ 历史'], mrow,
    '各局的中位。净产兵 = 窗口内利息与地租入账 − 三种手续费。历史臂的指令流水来自录像，没有「发出」的条数，所以「进录像 ÷ 发出」「被 9 条顶丢弃」两项为空。');

  // 随时间的走势（630 与 1500 两个断面）：编队领土 各臂 ÷ 历史，各局中位
  for (const [t0, offs] of [[0, [150, 300, 450, 630]], [630, [150, 300, 450, 600, 750, 870]], [1500, [150, 300, 450, 600, 750, 900]], [4284, [150, 300, 450, 600, 750, 870]]]) {
    const rows = [];
    for (const [arm, c, label] of [['C2', 'all', 'C2，全部局'], ['C2', 'lag', 'C2，卡顿的局'], ['C1', 'clean', 'C1，不卡的局'], ['C1', 'lag', 'C1，卡顿的局'], ['C0', 'lag', 'C0，卡顿的局'], ['C0', 'clean', 'C0，不卡的局'], ['C3', 'clean', 'C3，不卡的局']]) {
      const cs = cells.filter((x) => x.t0 === t0 && x.arms[arm] && (c === 'all' || clsOf(x.mid) === c));
      if (!cs.length) continue;
      const row = [label, String(cs.length)];
      for (const o of offs) {
        const v = [];
        for (const x of cs) {
          // 走势每 30 拍（拍号是 30 的倍数）记一次：取断面后 o 拍起、30 拍以内的第一个记录点（4284 不是 30 的倍数）
          const hs = x.hr.series.find((s) => s.t >= t0 + o && s.t < t0 + o + 30);
          if (!hs || !(hs.terr > 0)) continue;   // 窗口不够长的局、历史上这一拍编队已经没地的局，不进这一列
          const as = x.arms[arm].map((y) => { const s = y.r.arms.baseline.series.find((z) => z.t === hs.t); return s ? s.terr : null; });
          const m = mean(as);
          if (ok(m)) v.push(m / hs.terr);
        }
        row.push(v.length >= 3 ? `${f(med(v))}（${f(q(v, 0.25))}~${f(q(v, 0.75))}；${v.length}）` : '-');
        if (v.length >= 3) val(`attr.course.${t0}.${arm}.${c}.${o}`, f(med(v)));
      }
      rows.push(row);
    }
    table(`attr-course-${t0}`, ['臂，哪些局', '局数', ...offs.map((o) => `断面后 ${o} 拍`)], rows, '每格 = 各局「这条臂的编队领土 ÷ 历史同一拍的编队领土」的中位（P25~P75；有数的局数）。窗口没到这么长的局不进这一列。');
  }

  // C3 注入：不卡的局里换成合成卡顿波
  {
    const rows = [];
    for (const t0 of [630, 1500]) {
      const cs = cells.filter((x) => x.t0 === t0 && x.arms.C3 && x.arms.C1);
      if (!cs.length) continue;
      const lagCs = cells.filter((x) => x.t0 === t0 && clsOf(x.mid) === 'lag');
      const g = (arm, k) => med(cs.map((x) => avg(x, arm, k)));
      const r31 = cs.map((x) => div(avg(x, 'C3', 'terr1'), avg(x, 'C1', 'terr1')));
      const r21 = lagCs.filter((x) => x.arms.C2 && x.arms.C1).map((x) => div(avg(x, 'C2', 'terr1'), avg(x, 'C1', 'terr1')));
      for (const [label, fn] of [['C1（不卡的局）', (k) => g('C1', k)], ['C3（同一批不卡的局）', (k) => g('C3', k)], ['历史（卡顿的局）', (k) => med(lagCs.map((x) => x.h[k]))]]) {
        rows.push([String(t0), label, String(label.startsWith('历史') ? lagCs.length : cs.length), f(fn('recPerSeat'), 1), pc(fn('dupShare')), pc(fn('batchShare')), f(fn('dumpPerSeat')), pc(fn('atkVoidRate')),
          label.startsWith('C3') ? `${rpc(med(r31))}（${rpc(q(r31, 0.25))}~${rpc(q(r31, 0.75))}）` : label.startsWith('历史') ? `${rpc(med(r21))}（${rpc(q(r21, 0.25))}~${rpc(q(r21, 0.75))}；C2 ÷ C1）` : '基准']);
      }
      val(`attr.c3.${t0}.r31`, rpc(med(r31))); val(`attr.c3.${t0}.r21`, rpc(med(r21))); val(`attr.c3.${t0}.n`, cs.length);
      val(`attr.c3.${t0}.down`, `${r31.filter((v) => v < 1).length} / ${r31.length}`);
    }
    table('attr-c3', ['断面 t0', '臂', '局数', '进录像条数 ÷ 席位', '重复单占比', '同拍批占比', '清仓批 ÷ 席位', '陆攻落空率', '窗口末编队领土 相对 C1'], rows,
      '各局的中位。前两行是同一批不卡的局分别挂 C1 和 C3（合成卡顿波）；第三行是真正卡过的那些局当年的真值，以及它们「C2 ÷ C1」的中位，用来对照合成波的量级。');
  }
}

// =====================================================================================================================
// 六、arena：闭环对手模型标定
// =====================================================================================================================
if (want('arena')) {
  const A = loadDir('arena-acc20'), RP = loadDir('arena-rp1530');
  const T = [357, 630, 1071, 1530, 2142, 3210, 4284];
  const summarize = (D, name, foot) => {
    const rows = [];
    for (const t of T) {
      const R = { oLand: [], oDens: [], sLand: [], sDens: [], rel: [], oAlive: [], ai: [], sAlive: [] };
      for (const r of D.values()) {
        const m = r.arms && r.arms.baseline, x = r.reality;
        if (!m || !x || !m.cps[t] || !x.cps[t]) continue;
        const a = m.cps[t], b = x.cps[t];
        R.oLand.push(div(a.othersPerSeat, b.othersPerSeat)); R.oDens.push(div(a.othersDensity, b.othersDensity));
        R.sLand.push(div(a.squadPerSeat, b.squadPerSeat)); R.sDens.push(div(a.squadDensity, b.squadDensity));
        R.rel.push(div(a.relOthers, b.relOthers)); R.oAlive.push(a.othersAliveShare - b.othersAliveShare); R.ai.push(a.aiShare - b.aiShare); R.sAlive.push(a.squadAlive - b.squadAlive);
      }
      if (!R.oLand.length) continue;
      rows.push([String(t), String(R.oLand.length), q3(R.oLand), q3(R.oDens), q3(R.sLand), q3(R.sDens), q3(R.rel), q3(R.oAlive, pp), q3(R.ai, pp), sgn(med(R.sAlive), 0)]);
      for (const k of Object.keys(R)) val(`${name}.${t}.${k}`, k === 'oAlive' || k === 'ai' ? pp(med(R[k])) : k === 'sAlive' ? sgn(med(R[k]), 0) : f(med(R[k])));
      val(`${name}.${t}.n`, R.oLand.length);
    }
    table(name, ['拍', '局数', '其余真人人均地', '其余真人兵密度', '我方人均地', '我方兵密度', '我方人均地 ÷ 其余真人人均地', '其余真人在场占比（差，百分点）', '内置 AI 占陆地（差，百分点）', '我方在场席位（差，中位）'], rows, foot);
  };
  if (A.size) {
    summarize(A, 'arena-cps', '每格：各局「模型 ÷ 同一局录像」的 P25 / 中位 / P75；标「差」的三列是「模型 − 录像」。模型 = 真局房间头 + 其余真人全部换成闭环对手模型（从第 0 拍起），我方挂当年那一版策略、走这一局的实录阶梯（C2）、各席位的页面寿命照当年。');
    val('arena.n', A.size);
    let trunc = 0;
    for (const [mid, r] of A) if (r.truncated) { trunc++; notes.push(`arena-acc20/${mid}：被时间预算截断在 t=${r.t1}`); }
    val('arena.trunc', trunc);
    // 出手强度：各局相加（按人·拍加权），模型 / 同房间录像
    const prof = readJson(path.join(CALIB, 'human-profile.json'));
    const P = prof.phases, K = ['neutral', 'ai', 'hum', 'boat'];
    const z = () => ({ alive: 0, bal: 0, c: [0, 0, 0, 0], s: [0, 0, 0, 0] });
    const agg = P.map(() => ({ m: z(), r: z() }));
    for (const r of A.values()) {
      if (!r.arms || !r.arms.baseline || !r.reality || !r.reality.intensity) continue;
      P.forEach((p, i) => {
        for (const [X, I] of [[agg[i].m, r.arms.baseline.crowd.intensity[i]], [agg[i].r, r.reality.intensity[i]]]) {
          if (!I || !I.ratePerAlive100 || !I.spendPer100) continue;
          const alive = I.cmds / (I.ratePerAlive100 / 100), bal = I.sent / (I.spendPer100 / 100);
          X.alive += alive; X.bal += bal;
          K.forEach((k, j) => { X.c[j] += I.okRateBy[k] * alive / 100; X.s[j] += I.sentBy[k]; });
        }
      });
    }
    const rows = [];
    P.forEach((p, i) => {
      const m = agg[i].m, r = agg[i].r;
      if (!m.alive || !r.alive || p.t0 >= 4284) return;   // 闭环只跑到 4300 拍，最后一个阶段只有十几拍，不列
      const rate = K.map((k, j) => `${f(100 * m.c[j] / m.alive)} / ${f(100 * r.c[j] / r.alive)}`);
      const tot = (X) => 1e4 * X.s.reduce((a, b) => a + b, 0) / X.bal;
      const totC = (X) => 100 * X.c.reduce((a, b) => a + b, 0) / X.alive;
      rows.push([p.phase, `${f(totC(m))} / ${f(totC(r))}`, ...rate, `${f(tot(m), 1)} / ${f(tot(r), 1)}`, `${k1(m.s[2])} / ${k1(r.s[2])}`, f(m.bal / m.alive / (r.bal / r.alive))]);
      val(`arena.int.${p.t0}.cmd`, f(totC(m) / totC(r))); val(`arena.int.${p.t0}.spend`, f(tot(m) / tot(r))); val(`arena.int.${p.t0}.hum`, f(div(m.s[2], r.s[2]))); val(`arena.int.${p.t0}.bal`, f(m.bal / m.alive / (r.bal / r.alive)));
      val(`arena.int.${p.t0}.humSent`, `${k1(m.s[2])} / ${k1(r.s[2])}`);
    });
    table('arena-intensity', ['阶段（拍）', '每人每 100 拍生效指令', '其中 打无主地', '打内置 AI', '打真人', '发船', '每 100 拍花掉余额（%）', '打真人出的兵（各局合计）', '人均余额 模型 ÷ 录像'], rows,
      '其余真人（不含我方）的账，各局相加（按人·拍加权）。每格 = 模型 / 同一批房间的录像。');
    // 人与人之间：到各时刻为止每人下过几条有兵的陆攻；其余真人的地的分布
    const prow = [];
    for (const Tk of Object.keys(prof.cmdCount || {})) {
      const R = prof.cmdCount[Tk];
      const rs = [...A.values()].map((r) => r.arms.baseline.crowd.cmdCount && r.arms.baseline.crowd.cmdCount[Tk]).filter(Boolean);
      if (!rs.length) continue;
      val(`arena.people.${Tk}.mean`, f(div(med(rs.map((x) => x.mean)), R.mean)));
      val(`arena.people.${Tk}.qmax`, f(Math.max(...[0, 1, 2, 3, 4].map((i) => Math.abs(med(rs.map((x) => x.q[i])) - R.q[i]))), 0));
      prow.push([`到 ${Tk} 拍`, pc(med(rs.map((x) => x.zero))), [0, 1, 2, 3, 4].map((i) => f(med(rs.map((x) => x.q[i])), 0)).join(' / '), f(med(rs.map((x) => x.mean))), pc(R.zero), R.q.join(' / '), f(R.mean)]);
    }
    table('arena-people', ['时刻', '模型：一条没下的人', '模型：每人条数 P10 / P25 / 中位 / P75 / P90', '模型：均值', '实测：一条没下的人', '实测：P10 / P25 / 中位 / P75 / P90', '实测：均值'], prow,
      `每人到这一拍为止下过的有兵陆攻指令数。模型 = 各局的中位；实测 = ${prof.matches.length} 局录像里其余真人的合计（\`calib/human-profile.json\`）。`);
    const drow = [];
    for (const t of T) {
      const M = [[], [], [], [], [], []], R = [[], [], [], [], [], []];
      for (const r of A.values()) {
        const m = r.arms.baseline.cps[t], x = r.reality && r.reality.cps[t];
        if (!m || !x || !m.othersQ || !x.othersQ || !(x.othersQ[2] > 0)) continue;
        for (let i = 0; i < 6; i++) { M[i].push(m.othersQ[i] / x.othersQ[2]); R[i].push(x.othersQ[i] / x.othersQ[2]); }
      }
      if (!M[0].length) continue;
      drow.push([String(t), String(M[0].length), M.map((a) => f(med(a))).join(' / '), R.map((a) => f(med(a))).join(' / ')]);
      val(`arena.dist.${t}.p90`, `${f(med(M[4]))} / ${f(med(R[4]))}`); val(`arena.dist.${t}.p10`, `${f(med(M[0]))} / ${f(med(R[0]))}`);
      ['10', '25', '50', '75', '90', 'max'].forEach((nm, i) => { val(`arena.dist.${t}.m${nm}`, f(med(M[i]))); val(`arena.dist.${t}.r${nm}`, f(med(R[i]))); });
    }
    table('arena-dist', ['拍', '局数', '模型：P10 / P25 / 中位 / P75 / P90 / 最大', '录像：P10 / P25 / 中位 / P75 / P90 / 最大'], drow, '其余在场真人每人的地，各分位 ÷ 同一局录像的中位数，再取各局的中位。');
    // 我方这一侧的陆攻：按时段、按对象，模型 / 录像
    const seg = {};
    for (const r of A.values()) {
      const ms = r.arms.baseline.atkSeg, rs = r.reality.squadAtkSeg;
      if (!ms || !rs) continue;
      for (let i = 0; i < ms.length; i++) {
        const S = (seg[ms[i].t0] ||= { m: {}, r: {} });
        for (const k of ['neutral', 'ai', 'hum', 'neutralSent', 'aiSent', 'humSent']) { S.m[k] = (S.m[k] || 0) + ms[i][k]; S.r[k] = (S.r[k] || 0) + rs[i][k]; }
      }
    }
    const srow = [];
    const tk = Object.keys(seg).map(Number).sort((a, b) => a - b);
    tk.forEach((t0, i) => {
      const S = seg[t0];
      if (t0 >= 4284) return;
      srow.push([`${t0}~${tk[i + 1] ?? ''}`, `${int(S.m.neutral)} / ${int(S.r.neutral)}`, `${k1(S.m.neutralSent)} / ${k1(S.r.neutralSent)}`, `${int(S.m.ai)} / ${int(S.r.ai)}`, `${k1(S.m.aiSent)} / ${k1(S.r.aiSent)}`, `${int(S.m.hum)} / ${int(S.r.hum)}`, `${k1(S.m.humSent)} / ${k1(S.r.humSent)}`]);
      val(`arena.sq.${t0}.aiSent`, `${k1(S.m.aiSent)} / ${k1(S.r.aiSent)}`); val(`arena.sq.${t0}.aiSentR`, f(div(S.m.aiSent, S.r.aiSent)));
      val(`arena.sq.${t0}.humSentR`, f(div(S.m.humSent, S.r.humSent)));
    });
    table('arena-squad', ['时段（拍）', '打无主地：条数', '出兵', '打内置 AI：条数', '出兵', '打真人席位：条数', '出兵'], srow, '我方席位生效的陆攻，各局合计。每格 = 模型（闭环）/ 同一批房间的录像。');
  }
  if (RP.size) {
    summarize(RP, 'arena-rp', '同上，但前 1530 拍其余真人照录像执行（我方仍从第 0 拍起闭环），1530 拍起才换成对手模型。');
    val('arena.rp.n', RP.size);
  }
}

// ---------- 输出
fs.mkdirSync(path.join(OUT, 'tables'), { recursive: true });
for (const [name, md] of Object.entries(tables)) fs.writeFileSync(path.join(OUT, 'tables', `${name}.md`), md + '\n');
let prev = {};
if (ONLY && fs.existsSync(path.join(OUT, 'values.json'))) prev = readJson(path.join(OUT, 'values.json'));
fs.writeFileSync(path.join(OUT, 'values.json'), JSON.stringify({ ...prev, ...values }, null, 1) + '\n');
fs.writeFileSync(path.join(OUT, 'notes.txt'), notes.join('\n') + '\n');
console.log(`表 ${Object.keys(tables).length} 张 → ${path.relative(process.cwd(), path.join(OUT, 'tables'))}/；数字 ${Object.keys(values).length} 个 → values.json；提醒 ${notes.length} 条 → notes.txt`);
if (PRINT) for (const [name, md] of Object.entries(tables)) console.log(`\n### ${name}\n\n${md}`);
