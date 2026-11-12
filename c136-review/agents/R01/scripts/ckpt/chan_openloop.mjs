// chan_openloop.mjs — 通道层开环核对（纯离线，不跑引擎、不跑策略）。
//
// 把 R01 影子重演得到的「我方每个席位逐拍受理的指令」（out/<局>/shadow_cmds.csv，ok=1 的行：决策拍 τ、种类）原样喂进
// R06 的通道模型（lib/channel.mjs 的 Profile + Channel：C2 实录阶梯、d 的实测分布、同席位先发先到、连续 3 个回合 9 条顶、留先发的），
// 看模型给出的落地拍 / 同拍批 / 被顶掉的条数，与录像里真实发生的对不对得上：
//   ① 样本内：配上的指令（τ ↔ 录像落地拍 E），模型的落地拍与 E 相差几个回合
//   ② 留一法（10 折）：把一部分配对从阶梯里拿掉，用剩下的已知点补出 S(τ)，预测被拿掉的那些的落地拍——这是「已知点之间怎么补」的误差，
//      反事实臂里策略在别的拍下令时用的就是这种补出来的值。fill = auto / nearest / linear 各算一遍；另给不用阶梯（C1）的基线
//   ③ 批结构：模型里每个（席位, 回合）执行几条 ↔ 录像里我方每个（席位, 落地拍）进录像几条（陆攻 + 捐款 + 船）
//   ④ 没配上的指令：模型判成 9 条顶丢 / 通道已断 / 执行，与 R01 第 6 阶段从录像数出来的「挤掉」条数（channel_bursts.csv）对照
// 用法：HEAVY_TIMEOUT=110 timeout 120 bash ../../tools/run-heavy.sh node scripts/ckpt/chan_openloop.mjs <局号…> [--seed 1]
// 输出：reports/ckpt-data/chan_openloop.csv（追加 / 覆盖同一局的行）与逐局一段摘要
import fs from 'node:fs';
import path from 'node:path';
import { R01, OUT, LC, LU, loadR01, readCsv } from './common.mjs';

const o = LU.parseArgs(process.argv.slice(2));
const mids = o._;
if (!mids.length) { console.error('用法：chan_openloop.mjs <局号…>'); process.exit(2); }
const seed = LU.num(o.seed, 1);
const ceil7 = LU.ceil7;
const q = (a, p) => { if (!a.length) return null; const b = a.slice().sort((x, y) => x - y); return b[Math.min(b.length - 1, Math.floor(p * b.length))]; };
const share = (a, f) => (a.length ? +(a.filter(f).length / a.length).toFixed(4) : null);

const outRows = [];
for (const mid of mids) {
  const M = loadR01(mid);
  const squad = M.squad, squadSet = new Set(squad);
  const trace = JSON.parse(fs.readFileSync(path.join(R01, 'reports', 'ckpt-data', 'traces', `${mid}.json`), 'utf8'));
  const dec = readCsv(path.join(OUT, mid, 'shadow_cmds.csv')).filter((r) => r.ok === '1' && squadSet.has(+r.p))
    .map((r) => ({ p: +r.p, W: +r.t, k: r.kind === 'attack' ? 'atk' : r.kind === 'donate' ? 'don' : 'boat', landedAt: r.landedAt === '' || r.landedAt === undefined ? null : +r.landedAt }))
    .sort((a, b) => a.W - b.W || a.p - b.p);
  const Wmax = Math.max(...dec.map((d) => d.W), 0) + 2500;

  // ---- ①③④ 整条通道跑一遍
  const prof = LC.makeProfile('C2:fill=auto', { seed, seats: squad, trace, seatMap: null, Wmax, pageEnd: M.pageEnd, doomed: M.doomed, ownTrace: true });
  const host = { world: { t: 0 }, onIssue() {}, onDrop(seat, cmd, why) { cmd.st = 'drop'; cmd.why = why; }, execOur(seat, cmd) { cmd.st = 'exec'; cmd.Ex = host.world.t; return { ok: true, rec: true }; } };
  const chan = new LC.Channel(host, prof, { multi: false, cap: 9, capRounds: 3, keep: 'first', order: 'lifo' });
  const seatObj = new Map(squad.map((p) => [p, { p }]));
  let i = 0;
  for (let t = 0; t <= Wmax; t++) {
    host.world.t = t;
    while (i < dec.length && dec[i].W === t) { chan.submit(seatObj.get(dec[i].p), dec[i]); i++; }
    if (t % 7 === 0) chan.settle(t);
  }
  const paired = dec.filter((d) => d.landedAt !== null);
  // 没配上的只看陆攻：捐款被配额拒掉的本来就不进录像，船没有做落地对账
  const unpaired = dec.filter((d) => d.landedAt === null && d.k === 'atk');
  const errIn = paired.filter((d) => d.st === 'exec').map((d) => d.Ex - d.landedAt);
  const inSample = {
    n: paired.length, exec: paired.filter((d) => d.st === 'exec').length, dropCap: paired.filter((d) => d.st === 'drop' && d.why === 'cap').length, lost: paired.filter((d) => d.st === 'drop' && d.why === 'deadchan').length,
    exact: share(errIn, (e) => e === 0), within7: share(errIn, (e) => Math.abs(e) <= 7), within14: share(errIn, (e) => Math.abs(e) <= 14), medAbs: q(errIn.map(Math.abs), 0.5), p90Abs: q(errIn.map(Math.abs), 0.9),
  };
  const un = {
    n: unpaired.length, exec: unpaired.filter((d) => d.st === 'exec').length, dropCap: unpaired.filter((d) => d.st === 'drop' && d.why === 'cap').length, lost: unpaired.filter((d) => d.st === 'drop' && d.why === 'deadchan').length,
  };
  // 批结构
  const grp = (items, keyOf) => { const m = new Map(); for (const x of items) { const k = keyOf(x); m.set(k, (m.get(k) || 0) + 1); } return m; };
  const stat = (m) => { let n = 0, b3 = 0, b9 = 0, c3 = 0, mx = 0; for (const v of m.values()) { n += v; if (v >= 3) { b3++; c3 += v; } if (v >= 9) b9++; if (v > mx) mx = v; } return { cmds: n, rounds: m.size, b3, b9, share3: n ? +(c3 / n).toFixed(4) : null, max: mx }; };
  // 两边都只数陆攻 + 船（捐款在结算时被配额拒掉的不进录像，模型这里不跑引擎、分不出来）
  const model = stat(grp(dec.filter((d) => d.st === 'exec' && d.k !== 'don'), (d) => d.p * 100000 + d.Ex));
  const rc = readCsv(path.join(OUT, mid, 'replay_cmds.csv')).filter((r) => squadSet.has(+r.player) && +r.tick >= 0 && (r.kind === 'attack' || r.kind === 'boat'));
  const actual = stat(grp(rc, (r) => +r.player * 100000 + +r.tick));
  // R01 第 6 阶段从录像数出来的「挤掉」
  const bursts = readCsv(path.join(R01, 'reports', 'm6-data', 'channel_bursts.csv')).filter((r) => r.mid === mid);
  const squeezed = bursts.reduce((s, r) => s + (+r.droppedAfter || 0), 0);
  const atkDec = dec.filter((d) => d.k === 'atk');
  const atkLanded = atkDec.filter((d) => d.landedAt !== null).length;

  // ---- ② 留一法
  const loo = {};
  const folds = 10;
  const pairsOf = (p) => (trace.seats[String(p)] || []);
  for (const fill of ['auto', 'nearest', 'linear', 'none']) {
    const err = [], errLag = [];
    for (let f = 0; f < folds; f++) {
      const held = [];
      const tr = { ...trace, seats: {} };
      for (const p of squad) {
        const keep = [];
        for (const r of pairsOf(p)) { if (LU.hash32(seed, p, r[0], r[1], 991) % folds === f) held.push([p, r[0], r[1]]); else keep.push(r); }
        if (keep.length) tr.seats[String(p)] = keep;
      }
      const pf = fill === 'none' ? LC.makeProfile('C1:slowShare=0', { seed, seats: squad, Wmax }) : LC.makeProfile(`C2:fill=${fill},pagedeath=0`, { seed, seats: squad, trace: tr, seatMap: null, Wmax });
      for (const [p, tau, E] of held) {
        const e = ceil7(pf.serverTick(p, tau) + pf.delay(p, tau)) - E;
        err.push(e);
        if (E - tau > 28) errLag.push(e);
      }
    }
    loo[fill] = {
      n: err.length, exact: share(err, (e) => e === 0), within7: share(err, (e) => Math.abs(e) <= 7), within21: share(err, (e) => Math.abs(e) <= 21), medAbs: q(err.map(Math.abs), 0.5), p90Abs: q(err.map(Math.abs), 0.9), bias: err.length ? +(err.reduce((s, x) => s + x, 0) / err.length).toFixed(1) : null,
      nLag: errLag.length, lagWithin21: share(errLag, (e) => Math.abs(e) <= 21), lagMedAbs: q(errLag.map(Math.abs), 0.5), lagP90Abs: q(errLag.map(Math.abs), 0.9), lagBias: errLag.length ? +(errLag.reduce((s, x) => s + x, 0) / errLag.length).toFixed(1) : null,
    };
  }

  console.log(`[chan] ${mid}：受理的影子指令 ${dec.length} 条（配上落地拍的 ${paired.length}，没配上的陆攻 ${unpaired.length}，船 ${dec.filter((d) => d.k === 'boat').length}）`);
  console.log(`  ① 样本内：配上的 ${inSample.n} 条里模型执行 ${inSample.exec}、判 9 条顶丢 ${inSample.dropCap}、判通道已断 ${inSample.lost}；落地拍与录像相同 ${inSample.exact}，差 ≤1 个回合 ${inSample.within7}，≤2 个回合 ${inSample.within14}，|差| 中位 ${inSample.medAbs} / P90 ${inSample.p90Abs} 拍`);
  for (const [fill, r] of Object.entries(loo)) console.log(`  ② 留一法 ${fill.padEnd(7)}：${r.n} 条，落地拍相同 ${r.exact}、差 ≤1 个回合 ${r.within7}、≤3 个回合 ${r.within21}，|差| 中位 ${r.medAbs} / P90 ${r.p90Abs} 拍，平均偏差 ${r.bias}；其中真局落后 >28 拍的 ${r.nLag} 条：≤3 个回合 ${r.lagWithin21}，|差| 中位 ${r.lagMedAbs} / P90 ${r.lagP90Abs}，平均偏差 ${r.lagBias}`);
  console.log(`  ③ 批结构（陆攻 + 船）：模型 执行 ${model.cmds} 条 / ${model.rounds} 个（席位,回合），≥3 条的批 ${model.b3}（占条数 ${model.share3}）、满 9 条 ${model.b9}、最大 ${model.max}｜录像 ${actual.cmds} 条 / ${actual.rounds} 个，≥3 条的批 ${actual.b3}（占 ${actual.share3}）、满 9 条 ${actual.b9}、最大 ${actual.max}`);
  const atkModelExec = atkDec.filter((d) => d.st === 'exec').length;
  console.log(`  ④ 陆攻：影子受理 ${atkDec.length} 条，录像里落地并配上 ${atkLanded}（${(100 * atkLanded / Math.max(1, atkDec.length)).toFixed(0)}%），模型执行 ${atkModelExec}（${(100 * atkModelExec / Math.max(1, atkDec.length)).toFixed(0)}%）；没配上的 ${un.n} 条里模型判执行 ${un.exec}、9 条顶丢 ${un.dropCap}、通道已断 ${un.lost}`);
  outRows.push({ mid, dec: dec.length, paired: paired.length, unpaired: unpaired.length, atkDec: atkDec.length, atkLanded, atkModelExec, inSample, un, model, actual, squeezed, loo });
}

// 落盘（同一局覆盖旧行）
const dst = path.join(R01, 'reports', 'ckpt-data', 'chan_openloop.json');
let all = {};
if (fs.existsSync(dst)) all = JSON.parse(fs.readFileSync(dst, 'utf8'));
for (const r of outRows) all[r.mid] = r;
fs.mkdirSync(path.dirname(dst), { recursive: true });
fs.writeFileSync(dst, JSON.stringify(all, null, 1));
