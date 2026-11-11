// 调试：收官/被围阶段某个号每个决策拍「为什么没发船 / 发了什么船」——按 Policy.idleBoats（Vb L5019-5070）和 General.boatOut（L999-1015）的判定顺序归类。
// 用法：node dbg/idle-boats.mjs <mid> <bot> <t0> <t1> [--list] [--bucket 300]
// 不改策略：只在影子实例上给 idleBoats / boatOut / searchWater / tryDonateToTeammate / buyLand / boatFood 包一层记录。
// 归类（每个决策拍一个）：
//   先被别的指令占了    本拍在走到 idleBoats 之前已经发了指令（捐款 / 买地 / 扩中立），L4962-4963 的 cmds 判定不再调 idleBoats
//   没走到idleBoats      act 在前面就返回了（本拍没有任何指令）
//   A:有兄弟在打且密<115 被围分支 L5031：有编队友在陆上接敌、自己密度 < 115
//   A/M:无岸或船≥6       L5032 / L5046
//   A:间隔<18            L5033（距上次 boatOut 不到 min(boatEvery,18) 拍）
//   船位满(≥maxBoats)    boatOut L1001：海上的船数 ≥ maxBoats（本版 2）
//   找不到落点           searchWater 返回空
//   额不够               boatOut L1008：max < min
//   boatTo被拒           引擎/适配层拒收
//   发船                 发出（记落点归属、落点块大小、水路步数、eff）
//   其它分支:…           nb>0 或 neutral>0 时走 L5053 以后的普通分支
import { shadow } from '../shadow.mjs';

const args = process.argv.slice(2);
const [mid, bot, t0s, t1s] = args;
const t0 = +t0s, t1 = +t1s;
const list = args.includes('--list');
const bi = args.indexOf('--bucket');
const BUCKET = bi > 0 ? +args[bi + 1] : 300;
const k = (x) => (typeof x !== 'number' ? String(x) : Math.abs(x) >= 1e6 ? (x / 1e6).toFixed(2) + 'M' : Math.abs(x) >= 1e4 ? Math.round(x / 1e3) + 'k' : Math.abs(x) >= 1e3 ? (x / 1e3).toFixed(1) + 'k' : String(Math.round(x * 10) / 10));
const T_LAND = 1, P_INNER = 16;

let wrapped = false, rec = null, names = null;
const rows = [];
const wrap = (pol) => {
  const hook = (name, fn) => {
    const orig = pol[name];
    if (typeof orig !== 'function') return;
    pol[name] = function (...a) {
      const pre = fn.pre ? fn.pre.call(this, ...a) : null;
      const r = orig.apply(this, a);
      if (rec && fn.post) fn.post.call(this, r, pre, ...a);
      return r;
    };
  };
  hook('tryDonateToTeammate', { post(r) { if (r) rec.donated = true; } });
  hook('buyLand', { post(r) { if (r) rec.bought = true; } });
  hook('boatFood', { post(r) { rec.food = r ? 'sent' : rec.food || 'no'; } });
  hook('searchWater', { post(r, pre, g) {
    rec.searched = true;
    if (r) {
      const v = g.px[r.land];
      const o = v === T_LAND ? 512 : v >= P_INNER ? g.own[r.land] : -1;
      rec.hit = { land: r.land, x: r.land % g.W, y: Math.floor(r.land / g.W), neutral: !!r.neutral, size: r.size, eff: r.eff, price: r.price, owner: o, dist: this.wdist ? this.wdist[r.land] : null };
      // 落点格是陆地，wdist 只标水格：取它四邻水格里最小的步数
      let dm = Infinity;
      for (let i = 0; i < 4; i++) { const c = r.land + g.dir4[i]; if (this.wdist && this.wdist[c] >= 0 && this.wdist[c] < dm) dm = this.wdist[c]; }
      rec.hit.dist = Number.isFinite(dm) ? dm : null;
    } else rec.hit = null;
  } });
  hook('boatOut', {
    pre(g) { return { cnt: g.boatCount[this.me], allowed: g.boatsAllowed(this.me), cmds: this.cmds, bal: g.bal[this.me], range: this.p.boatRange, maxBoats: this.p.maxBoats }; },
    post(r, pre) { rec.boatOut = { r, ...pre }; },
  });
  hook('idleBoats', {
    pre(g) {
      const me = this.me, P = this.p;
      const B = g.bal[me], L = Math.max(1, g.terr[me]);
      let fronts = 0;
      for (let p = 0; p < g.humans; p++) {
        if (p !== me && g.alive[p] && this.isTeammate(g, p) && (this.isOurSquadBot(g, p) || this.isBossNpl(g, p)) && g.terr[p] >= 500) {
          const nbs = this.peopleOf(g, p);
          if (nbs.some((o) => g.alive[o] && !this.isTeammate(g, o) && g.terr[o] > 0)) fronts++;
        }
      }
      const pre = { nb: this.nb.length, neutral: this.neutral, mop: this.isMopUp(g), fronts, dMe: B / L, cnt: g.boatCount[me], allowed: g.boatsAllowed(me), gap: g.t - this.lastBoat, every: Math.min(P.boatEvery, 18) };
      rec.idle = pre;
      return pre;
    },
  });
  wrapped = true;
};

const who = (q) => (q === 512 ? '中立' : q < 0 ? '?' : names && q < names.length ? `${names[q].replace('[APEX] ', '').slice(0, 10)}#${q}` : `AI${q}`);
const classify = (r) => {
  if (!r.idle) return r.donated ? '先被别的指令占了:捐款' : r.bought ? '先被别的指令占了:买地' : r.cmds > 0 ? '先被别的指令占了:其它' : '没走到idleBoats';
  const i = r.idle;
  const bo = r.boatOut;
  const boatRes = () => {
    if (!bo) return null;
    if (bo.r) return '发船';
    if (!bo.allowed) return '无岸';
    if (bo.cnt >= bo.maxBoats) return '船位满(≥maxBoats)';
    if (!r.searched || r.hit === undefined) return '船位满(≥maxBoats)';
    if (r.hit === null) return '找不到落点';
    return '额不够或boatTo被拒';
  };
  if (i.nb === 0 && i.neutral === 0 && !i.mop) {
    if (i.fronts >= 1 && i.dMe < 115) return 'A:有兄弟在打且密<115';
    if (!i.allowed || i.cnt >= 6) return 'A:无岸或船≥6';
    if (i.gap < i.every) return 'A:间隔<18';
    return 'A:' + (boatRes() || '?');
  }
  if (i.mop) {
    if (!i.allowed || i.cnt >= 6) return 'M:无岸或船≥6';
    return 'M:' + (boatRes() || '?');
  }
  if (r.food === 'sent') return '其它分支:boatFood发船';
  return '其它分支:' + (boatRes() || (i.neutral > 0 ? 'neutral>0' : '未调boatOut'));
};

let cur = null;
const flush = (g) => {
  if (!cur) return;
  cur.cls = classify(cur);
  rows.push(cur);
  cur = null;
};
shadow(mid, { until: t1 + 2, quiet: true, trace: (g, b, pol, ctx) => {
  if (b.bot !== bot) return;
  if (!names) names = (ctx && ctx.names) || null;
  flush(g);
  rec = null;
  if (g.t < t0 || g.t > t1) return;
  if (!wrapped) wrap(pol);
  const period = (pol.p && pol.p.period) || 5;
  if (g.t % period !== 0) return;
  const me = b.me;
  cur = rec = { t: g.t, B: g.bal[me], L: g.terr[me], cnt: g.boatCount[me], cmds0: pol.cmds };
  // 决策后的指令数要到下一拍才知道：在 flush 时补
  const pol0 = pol;
  Object.defineProperty(cur, 'cmds', { get() { return pol0.cmds - this.cmds0; }, enumerable: false });
} });
flush(null);

const buckets = new Map();
for (const r of rows) {
  const bk = Math.floor(r.t / BUCKET) * BUCKET;
  if (!buckets.has(bk)) buckets.set(bk, { n: 0, cls: {}, sent: [], balSum: 0, dSum: 0, cntSum: 0 });
  const o = buckets.get(bk);
  o.n++;
  o.cls[r.cls] = (o.cls[r.cls] || 0) + 1;
  o.balSum += r.B; o.dSum += r.B / Math.max(1, r.L); o.cntSum += r.cnt;
  if (r.cls.endsWith('发船') && r.hit) o.sent.push(r);
}
const total = {};
for (const r of rows) total[r.cls] = (total[r.cls] || 0) + 1;
console.log(`${mid} ${bot} idleBoats 归类 t=${t0}~${t1}：决策拍 ${rows.length} 个 → ${Object.entries(total).sort((a, b) => b[1] - a[1]).map(([c, n]) => `${c} ${n}`).join('，')}`);
for (const [bk, o] of [...buckets].sort((a, b) => a[0] - b[0])) {
  const sent = o.sent;
  const far = sent.filter((r) => r.hit.dist !== null && r.hit.dist >= 300).length;
  const med = (arr) => { if (!arr.length) return '-'; const s = [...arr].sort((a, b) => a - b); return s[s.length >> 1]; };
  console.log(`  ${String(bk).padStart(5)}~${bk + BUCKET - 1}：决策拍 ${o.n} 均密 ${(o.dSum / o.n).toFixed(0)} 平均在海上的船 ${(o.cntSum / o.n).toFixed(1)} | ${Object.entries(o.cls).sort((a, b) => b[1] - a[1]).map(([c, n]) => `${c} ${n}`).join('，')}` +
    (sent.length ? ` | 发船 ${sent.length}：落点水路步数中位 ${med(sent.filter((r) => r.hit.dist !== null).map((r) => r.hit.dist))}（≥300 步 ${far} 条），落点块大小中位 ${med(sent.map((r) => r.hit.size || 0))}，不同落点 ${new Set(sent.map((r) => r.hit.land)).size} 个` : ''));
}
if (list) {
  for (const r of rows) {
    const h = r.hit ? ` 落点(${r.hit.x},${r.hit.y}) ${who(r.hit.owner)} 块 ${r.hit.size} 水路 ${r.hit.dist} eff ${k(r.hit.eff)}` : '';
    const i = r.idle ? ` nb=${r.idle.nb} neut=${r.idle.neutral} mop=${r.idle.mop ? 1 : 0} 兄弟接敌=${r.idle.fronts} 距上次=${r.idle.gap}` : '';
    console.log(`    t=${r.t} B=${k(r.B)} 密=${(r.B / Math.max(1, r.L)).toFixed(0)} 海上船=${r.cnt}${i} → ${r.cls}${h}`);
  }
}
