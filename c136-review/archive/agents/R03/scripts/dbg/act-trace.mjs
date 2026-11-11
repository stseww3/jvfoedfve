// 调试：逐决策拍打印某个号在 act 里各个分支的输入与结果（不改策略，只在实例上包一层记录）。
// 用法：node dbg/act-trace.mjs <mid> <bot> <t0> <t1> [--all]
//   默认只打印决策拍（t % period === 0）；--all 连非决策拍也打印（只有额度那几行会变）。
// 每个邻居一行：allow / price / floorFor（留底）/ minShare / elimCost / amount 的返回值，
// 据此可以读出 pickTarget 为什么没有选它（价格超 maxCost、留底后不够、在途已够、amount 太小……）。
import { shadow } from '../shadow.mjs';

const args = process.argv.slice(2);
const [mid, bot, t0s, t1s] = args;
const t0 = +t0s, t1 = +t1s;
const all = args.includes('--all');
const NEUTRAL = 512;
const k = (x) => (typeof x !== 'number' ? String(x) : Math.abs(x) >= 1e6 ? (x / 1e6).toFixed(2) + 'M' : Math.abs(x) >= 1e4 ? Math.round(x / 1e3) + 'k' : Math.abs(x) >= 1e3 ? (x / 1e3).toFixed(1) + 'k' : (Math.round(x * 100) / 100).toString());

let wrapped = null, log = [], names = null, snap = new Map();
const PERQ = ['allow', 'price', 'floorFor', 'winFloor', 'peopleSafe', 'minShare', 'elimCost', 'amount', 'targetBias', 'warBias', 'safeAt'];
const CALLS = ['safeFinite', 'dpKeep', 'peopleFloor', 'counterAttack', 'warAct', 'expandNeutral', 'pickTarget', 'boatOut', 'boatFood', 'idleBoats', 'buyLand', 'tryDonateToTeammate', 'tryEmergencyBossRescue', 'tryEmergencySquadAssist', 'tryInterceptEnemyBoats', 'dpNeutral', 'openingExpand', 'send', 'floors', 'offers'];

const wrap = (pol) => {
  for (const name of [...PERQ, ...CALLS]) {
    const orig = pol[name];
    if (typeof orig !== 'function') continue;
    pol[name] = function (...a) {
      const depth = log.depth = (log.depth || 0) + 1;
      const idx = log.push({ name, depth, a, r: undefined }) - 1;
      if (PERQ.includes(name)) {
        const g = a[0], q = a[1], me = this.me;
        if (!snap.has(q)) snap.set(q, q === undefined || q < 0 ? {} : q === NEUTRAL ? { L: '-', B: '-', mine: g.attackTroopsOn(me, q), theirs: '-', cnt: '-' } : { L: g.terr[q], B: g.bal[q], mine: g.attackTroopsOn(me, q), theirs: g.attackTroopsOn(q, me), cnt: this.cnt ? this.cnt[q] ?? 0 : '-' });
      }
      let r;
      try { r = orig.apply(this, a); } finally { log.depth--; }
      log[idx].r = r;
      return r;
    };
  }
  wrapped = pol;
};

const who = (g, q) => (q === NEUTRAL ? '中立' : q >= g.humans ? `AI${q}` : `${(names[q] || '').slice(0, 12)}#${q}`);

const flush = (g, b, pol, header) => {
  if (!log.length) { snap = new Map(); return; }
  const me = b.me;
  const out = [];
  const perq = new Map();
  for (const e of log) {
    if (PERQ.includes(e.name)) {
      const q = e.a[1];
      if (!perq.has(q)) perq.set(q, []);
      const v = e.r;
      perq.get(q).push(`${e.name}=${typeof v === 'number' ? k(v) : v}${e.name === 'amount' ? `(avail ${k(e.a[2])} need ${k(e.a[3])} min ${k(e.a[4])})` : e.name === 'floorFor' ? `(f ${k(e.a[2])})` : ''}`);
      continue;
    }
    if (e.name === 'floors') { const r = e.r || {}; out.push(`floors cap=${k(r.cap)} avgNb=${k(r.avgNb)} floorAt(2)=${r.floorAt ? k(r.floorAt(2)) : '-'} floorAt(20)=${r.floorAt ? k(r.floorAt(20)) : '-'}`); continue; }
    if (e.name === 'send') { out.push(`${'  '.repeat(e.depth - 1)}send(${who(g, e.a[1])}, ${k(e.a[2])})→${e.r}`); continue; }
    if (e.name === 'pickTarget') { out.push(`pickTarget(maxCost=${k(e.a[2])})→${e.r ? `${who(g, e.r.q)} ${k(e.r.amount)}` : 'null'}`); continue; }
    if (e.name === 'expandNeutral') { out.push(`expandNeutral(spend=${k(e.a[1])})`); continue; }
    if (e.name === 'offers') {
      out.push(`offers→${Array.isArray(e.r) ? e.r.length : e.r}`);
      if (Array.isArray(e.r)) for (const o of e.r) {
        const fl = ['person', 'nearCollapse', 'bleeding', 'onMe', 'isCrowdedHard', 'isDoorSea'].filter((x) => o[x]).join('/');
        out.push(`    报价 ${who(g, o.q)}：c=${k(o.c)} need=${k(o.need)} inAtk=${k(o.inAtk ?? 0)} tD=${o.tD === undefined ? '-' : k(o.tD)} ${fl}`);
      }
      continue;
    }
    out.push(`${e.name}→${e.r === undefined ? 'undef' : typeof e.r === 'object' && e.r ? JSON.stringify(e.r).slice(0, 80) : typeof e.r === 'number' ? k(e.r) : e.r}`);
  }
  console.log(`${header} | 决策后 nb=${pol.nb.length} neut=${pol.neutral}`);
  // 相邻的重复行（boatFood/searchFood 会把同一个钩子调上百次）压成「×n」
  let prev = null, rep = 0;
  const emit = () => { if (prev !== null) console.log('    ' + prev + (rep > 1 ? ` ×${rep}` : '')); };
  for (const line of out) {
    if (line === prev) { rep++; continue; }
    emit();
    prev = line; rep = 1;
  }
  emit();
  for (const [q, items] of perq) {
    const s = snap.get(q) || {};
    const cnt = new Map();
    for (const it of items) cnt.set(it, (cnt.get(it) || 0) + 1);
    const txt = [...cnt].map(([it, n]) => (n > 1 ? `${it}×${n}` : it)).join(' ');
    const label = q === undefined || q < 0 ? '（不针对目标）' : `${who(g, q)} 地 ${s.L} 兵 ${k(s.B)} 我压它 ${k(s.mine)} 它压我 ${k(s.theirs)} 接壤 ${s.cnt}`;
    console.log(`      · ${label}：${txt}`);
  }
  log = [];
  snap = new Map();
};

// safeFinite 的来源：每个接壤的内置 AI 的「除我之外最弱的邻居」（Strategy.threatOf L417-443 的只读复算）
const P_INNER = 16, T_LAND = 1;
const threatDiag = (g, pol, ctx) => {
  const me = pol.me, out = [];
  for (const q of pol.nb) {
    if (!g.alive[q] || !g.isBot(q)) continue;
    const flags = [];
    if (!g.hasFreeSlot(q)) flags.push('无空槽');
    if (g.hasAttack(q, me)) flags.push('已在打我');
    const B = g.border[q], px = g.px, own = g.own, d = g.dir4;
    const busyNeutral = g.hasAttack(q, NEUTRAL);
    let minOther = Infinity, arg = -1, neutral = false;
    const seen = new Set();
    const n = B.length, step = n > 1024 ? Math.ceil(n / 1024) : 1;
    for (let i = n - 1; i >= 0 && !neutral; i -= step) {
      for (let kk = 0; kk < 4; kk++) {
        const c = B[i] + d[kk], v = px[c];
        if (v === T_LAND) { if (!busyNeutral) { neutral = true; break; } continue; }
        if (v < P_INNER) continue;
        const o = own[c];
        if (o === q || o === me || seen.has(o)) continue;
        seen.add(o);
        if (g.hasAttack(q, o)) continue;
        const sv = g.bal[o] + g.attackTroopsOn(o, q);
        if (sv < minOther) { minOther = sv; arg = o; }
      }
    }
    out.push(`${who(g, q)}：${neutral ? '挨着中立地（不算）' : arg < 0 ? '没有别的邻居' : `最弱的别的邻居 ${who(g, arg)} 兵+在途 ${k(minOther)}，减去我压它的 ${k(g.attackTroopsOn(me, q))}`}${flags.length ? '（' + flags.join('、') + '，不算）' : ''}`);
  }
  return out;
};

let pending = null;
shadow(mid, { until: t1 + 2, quiet: true, trace: (g, b, pol, ctx) => {
  if (b.bot !== bot) return;
  if (pending) { flush(g, b, pol, pending.header); pending = null; }
  if (g.t < t0 || g.t > t1) { log = []; snap = new Map(); return; }
  if (!wrapped) wrap(pol);
  if (!names) names = (ctx && ctx.names) || [];
  const period = (pol.p && pol.p.period) || 5;
  log = [];
  snap = new Map();
  if (!all && g.t % period !== 0) return;
  const me = b.me;
  if (args.includes('--threat')) for (const line of threatDiag(g, pol, ctx)) console.log(`    [t=${g.t} 决策前局面，邻居取自上一决策拍] ${line}`);
  pending = { header: `t=${g.t} B=${k(g.bal[me])} L=${g.terr[me]} 密=${(g.bal[me] / Math.max(1, g.terr[me])).toFixed(1)} 在途中立=${k(g.attackTroopsOn(me, NEUTRAL))} 槽=${g.atkCount[me]} nfs=${pol.isNoFullSend ? 1 : 0} sq=${k(pol.shadowQuota || 0)}` };
} });
