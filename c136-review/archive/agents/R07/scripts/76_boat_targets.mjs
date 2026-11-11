#!/usr/bin/env node
// 76_boat_targets.mjs — R07：我方每条船「想去哪、发船时那块地是谁的、靠岸时是谁的、兵最后去了哪」。
//
// 背景（引擎 /agent/repos/c136-data/src/sim/sim/boats.js L262-287 landAt）：
//   船靠岸的那一格如果是队友的地，引擎把船上的兵当成一笔「捐款」交给队友（不收手续费），
//   但要过收款人的反喂养额度和 150×领土硬上限；过不了的部分直接丢在海里。
//
// 做法：
//   1) 读 65_shadow.mjs 的 shadow_cmds.tsv 里的 boatTo 行：策略在决策拍选中的目标陆地格（像素号）和发令的源码位置；
//   2) 用统筹的干净模拟器（resim）重演录像：在每个影子决策拍记下目标格当时的主人；
//      包住 Game.boat（录像里真实的发船指令）和 Game.landAt（靠岸），记下发船拍 / 靠岸拍、靠岸格和它当时的主人、队友实收多少；
//   3) 同一个号按「发船顺序 = 靠岸顺序里带兵数相同的第一条」配对。
//
// 用法（必须套重计算闸；先跑过 65_shadow.mjs）：
//   bash c136-review/tools/run-heavy.sh node c136-review/agents/R07/scripts/76_boat_targets.mjs <matchId> [--reach t1,t2,…] [--lag N]
//   --lag：影子决策和真实发船配对的最大间隔（拍，默认 60）。指令晚到的局（A089：船晚 110~240 拍才发出去）要放宽，否则配不上。
//   --reach：在这些拍上，从每个有海岸的我方号的岸出发沿水路广搜（和策略 searchWater 一样从 coast + border 起步，最远 2500 格），
//            列出水路能到的岸各是谁的、最近多少格（C 段）。用来回答「当时有没有海路能到的敌岸」。
// 输出：out/<matchId>/boat_targets.txt / boat_targets.json
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const DATA = '/agent/repos/c136-data';
const HERE = path.dirname(fileURLToPath(import.meta.url));
const mid = process.argv[2];
if (!mid) { console.error('用法：76_boat_targets.mjs <matchId>'); process.exit(2); }
const OUT = path.join(HERE, '..', 'out', mid);

const SIM = await import(path.join(DATA, 'src/sim/sim/index.js'));
// 船落在没人占的水 / 边界 / 山格时按线上规则处理（见 r07simfix.mjs；来自 R01 的 resim_lib_r01.mjs）
(await import(path.join(HERE, 'r07simfix.mjs'))).applyOddLandingFix(SIM);
const { resim } = await import(path.join(DATA, 'src/tools/resim.mjs'));
const LIB = await import(path.join(DATA, 'src/sim/tools/c102-replay-lib.mjs'));
const { NEUTRAL } = SIM;

const d = LIB.decodeReplay(fs.readFileSync(path.join(DATA, 'bundles', mid, 'replay.txt'), 'utf8'));
const H = d.vu.humanCount;
const names = d.vu.playerNamesData ? Array.from(d.vu.playerNamesData).slice(0, H).map((s) => String(s ?? '')) : [];
const logText = fs.readFileSync(path.join(DATA, 'bundles', mid, 'in_game.log'), 'utf8').split('\n');
const realBots = new Set();
for (const ln of logText) { const m = /^\d+\t\[([A-Za-z0-9_]+)\] /.exec(ln); if (m) realBots.add(m[1]); }
const idOf = new Map();
for (const b of realBots) for (let p = 0; p < H; p++) if (names[p].trim().toLowerCase().endsWith(b.toLowerCase())) { idOf.set(b, p); break; }
const botOf = new Map([...idOf].map(([b, p]) => [p, b]));
const pname = (g, q) => q === -2 ? '水' : q === -1 ? '山/边' : q >= NEUTRAL ? '无主地' : botOf.has(q) ? `队友 ${botOf.get(q)}` : q < H ? `${(names[q] || '').trim().slice(0, 18)}#${q}[T${g.teams ? g.teams[q] : 0}]` : `AI#${q}`;
const ownerAt = (g, c) => { const v = g.px[c]; return v === SIM.T_LAND ? NEUTRAL : v >= SIM.P_INNER ? g.own[c] : v === SIM.T_WATER ? -2 : -1; };

// 影子决策
const shPath = path.join(OUT, 'shadow_cmds.tsv');
if (!fs.existsSync(shPath)) { console.error('缺 shadow_cmds.tsv：先跑 65_shadow.mjs'); process.exit(2); }
const shRows = fs.readFileSync(shPath, 'utf8').trim().split('\n');
const hdr = shRows[0].split('\t');
const shadow = [];
for (const ln of shRows.slice(1)) {
  const f = ln.split('\t'); const r = Object.fromEntries(hdr.map((h, i) => [h, f[i]]));
  if (r.kind !== 'boatTo') continue;
  shadow.push({ t: +r.t, bot: r.bot, pct: +r.pct, c: +r.target, site: r.site || '', bal: +r.bal, terr: +r.terr, troops: +r.troops });
}
const shByT = new Map();
for (const s of shadow) { if (!shByT.has(s.t)) shByT.set(s.t, []); shByT.get(s.t).push(s); }

const argv = process.argv.slice(3);
const reachTs = new Set((argv.includes('--reach') ? argv[argv.indexOf('--reach') + 1] : '').split(',').filter(Boolean).map(Number));
const LAG = argv.includes('--lag') ? Math.max(1, Number(argv[argv.indexOf('--lag') + 1]) || 60) : 60;
const reachOut = [];
function reachScan(g) {
  const N = g.N, px = g.px, own = g.own, d4 = g.dir4;
  for (const [b, me] of idOf) {
    if (!g.alive[me] || !g.coast[me] || !g.coast[me].length) continue;
    const dist = new Int32Array(N).fill(-1), q = new Int32Array(N);
    let h = 0, t = 0;
    const seed = (list) => { for (let i = list.length - 1; i >= 0; i--) for (let k = 0; k < 4; k++) { const c = list[i] + d4[k]; if (px[c] === SIM.T_WATER && dist[c] < 0) { dist[c] = 0; q[t++] = c; } } };
    seed(g.coast[me]); seed(g.border[me]);
    const seen = new Map(); // owner -> {d, cells}
    let neutD = -1, neutCells = 0, water = 0;
    while (h < t) {
      const c = q[h++]; const dc = dist[c];
      if (dc > 2500) break;
      water++;
      for (let k = 0; k < 4; k++) {
        const n = c + d4[k]; const v = px[n];
        if (v === SIM.T_WATER) { if (dist[n] < 0) { dist[n] = dc + 1; q[t++] = n; } }
        else if (v === SIM.T_LAND) { neutCells++; if (neutD < 0) neutD = dc + 1; }
        else if (v >= SIM.P_INNER) { const o = own[n]; if (o === me) continue; const e = seen.get(o) || { d: dc + 1, cells: 0 }; e.cells++; seen.set(o, e); }
      }
    }
    const rows = [...seen].map(([o, e]) => ({ o, d: e.d, cells: e.cells, mate: o < H && !g.isEnemy(me, o), squad: botOf.has(o), ai: o >= H, left: o < H && g.state[o] === 2, terr: g.terr[o], bal: g.bal[o] }));
    reachOut.push({ t: g.t, bot: b, coastPx: g.coast[me].length, water, neutD, neutCells, rows });
  }
}

const proto = SIM.Game.prototype;
const launches = [], landings = [];
const origBoat = proto.boat;
proto.boat = function (pct, water, dir, p = this.me) {
  const g = this;
  if (!botOf.has(p)) return origBoat.call(this, pct, water, dir, p);
  const b0 = g.bal[p];
  const ok = origBoat.call(this, pct, water, dir, p);
  const spent = b0 - g.bal[p];
  if (spent > 0) {
    const fee = Math.min(SIM.iV(32 * b0, 1024), spent);
    launches.push({ t: g.t, bot: botOf.get(p), p, pct, water, dir, b0, spent, fee, troops: spent - fee, terr: g.terr[p], sh: null, land: null });
  }
  return ok;
};
const origLandAt = proto.landAt;
proto.landAt = function (p, troops, c, at) {
  const g = this;
  if (!botOf.has(p)) return origLandAt.call(this, p, troops, c, at);
  const tgt = ownerAt(g, c);
  const tb0 = tgt >= 0 && tgt < NEUTRAL ? g.bal[tgt] : 0;
  const myB0 = g.bal[p];
  const quota0 = tgt >= 0 && tgt < NEUTRAL && g.sendQuota ? g.sendQuota[tgt] : null;
  origLandAt.call(this, p, troops, c, at);
  const mate = tgt >= 0 && tgt < NEUTRAL && tgt !== p && !g.isEnemy(p, tgt);
  landings.push({ t: g.t, bot: botOf.get(p), p, troops, c, x: c % g.W, y: Math.floor(c / g.W), owner: tgt, ownerName: pname(g, tgt), mate, self: tgt === p,
    delivered: mate ? g.bal[tgt] - tb0 : tgt === p ? g.bal[p] - myB0 : 0, ownerTerr: tgt >= 0 && tgt < NEUTRAL ? g.terr[tgt] : 0, ownerBal: tb0, used: false });
};
// 「发船那一拍目标格的主人」：发船拍要等重演完才知道，所以给每个影子目标在决策拍之后 LAG 拍内逐拍留样，配对后再取
const ownerHist = new Map(); // shadow idx -> Map(t -> owner)
const origTick = proto.tick;
proto.tick = function () {
  const g = this;
  const ss = shByT.get(g.t);
  if (ss) for (const s of ss) { s.owner = ownerAt(g, s.c); s.ownerName = pname(g, s.owner); s.x = s.c % g.W; s.y = Math.floor(s.c / g.W); s.ownerTerr = s.owner >= 0 && s.owner < NEUTRAL ? g.terr[s.owner] : 0; s.ownerBal = s.owner >= 0 && s.owner < NEUTRAL ? g.bal[s.owner] : 0; }
  for (let i = 0; i < shadow.length; i++) {
    const s = shadow[i];
    if (g.t >= s.t && g.t <= s.t + LAG) { if (!ownerHist.has(i)) ownerHist.set(i, new Map()); ownerHist.get(i).set(g.t, ownerAt(g, s.c)); }
  }
  origTick.call(this);
  if (reachTs.has(g.t) && !g.spawnPhase) { try { reachScan(g); } catch (e) { if (!reachScan.err) reachScan.err = String(e && e.message); } }
};

await resim(mid, {});

// 配对：影子决策 → 真实发船（同号、同 pct、发船拍在决策拍之后 LAG 拍内的第一条）
for (let i = 0; i < shadow.length; i++) {
  const s = shadow[i];
  const l = launches.find((x) => x.bot === s.bot && x.sh === null && x.pct === s.pct && x.t > s.t && x.t - s.t <= LAG);
  if (l) { l.sh = i; s.launch = l; }
}
// 真实发船 → 靠岸（同号、带兵数相同的第一条；没有就取同号下一条未用的）
for (const l of launches) {
  let ld = landings.find((x) => !x.used && x.bot === l.bot && x.t >= l.t && x.troops === l.troops);
  if (!ld) ld = landings.find((x) => !x.used && x.bot === l.bot && x.t >= l.t);
  if (ld) { ld.used = true; l.land = ld; }
}
const fmt = (n) => Number(n).toLocaleString('en-US');
const nameOf = (q) => q === -2 ? '水' : q === -1 ? '山/边' : q >= NEUTRAL ? '无主地' : botOf.has(q) ? `队友 ${botOf.get(q)}` : q < H ? `${(names[q] || '').trim().slice(0, 18)}#${q}` : `AI#${q}`;
const L = [];
const P = (s) => L.push(s);
P(`# ${mid} 我方的船：目标格的主人（决策拍 → 发船拍 → 靠岸拍）与兵的去向`);
P(`# 真实发船 ${launches.length} 条；影子决策里的 boatTo ${shadow.length} 条（其中配上真实发船的 ${shadow.filter((s) => s.launch).length} 条）；靠岸 ${landings.length} 次`);
P('');
P('A. 逐条（按发船拍）');
P('发船拍\t号\tpct\t带兵（手续费）\t发船前 余额 / 领土\t决策拍 / 发令位置\t目标格 (x,y)\t目标格主人：决策拍 → 发船拍\t靠岸拍（航行拍数）\t靠岸格 (x,y) 当时主人\t结果');
const J = [];
let lost = 0, lostN = 0, handed = 0, handedN = 0, atk = 0, atkN = 0, selfN = 0, selfV = 0, noLand = 0;
for (const l of launches) {
  const s = l.sh !== null ? shadow[l.sh] : null;
  const ld = l.land;
  let ownL = '';
  if (s) { const h = ownerHist.get(l.sh); const o = h && h.get(l.t); ownL = o === undefined ? '?' : nameOf(o); }
  let result = '还在海上 / 没靠岸';
  if (ld) {
    if (ld.mate) {
      const gone = ld.troops - ld.delivered;
      if (gone > 0) { lost += gone; lostN++; }
      if (ld.delivered > 0) { handed += ld.delivered; handedN++; }
      result = ld.delivered >= ld.troops ? `整船交给队友（到账 ${fmt(ld.delivered)}）` : ld.delivered > 0 ? `队友只收下 ${fmt(ld.delivered)}，丢 ${fmt(gone)}` : `队友一个兵没收下，整船 ${fmt(ld.troops)} 丢在海里（额度 / 上限拒收）`;
    } else if (ld.self) { selfN++; selfV += ld.delivered; result = `靠回自己的地（回到余额 ${fmt(ld.delivered)}）`; }
    else if (ld.owner === NEUTRAL) { atk += ld.troops; atkN++; result = '登上无主地，开打'; }
    else if (ld.owner >= 0) { atk += ld.troops; atkN++; result = `登上 ${ld.ownerName} 的地，开打（对方 ${fmt(ld.ownerTerr)} 格 / ${fmt(ld.ownerBal)} 兵）`; }
    else result = '靠岸格不是陆地，兵没了';
  } else noLand++;
  P(`${l.t}\t${l.bot}\t${l.pct}\t${fmt(l.troops)}（${fmt(l.fee)}）\t${fmt(l.b0)} / ${fmt(l.terr)}\t${s ? `${s.t} 〔${s.site}〕` : '（影子里没有对应决策）'}\t${s ? `(${s.x},${s.y})` : ''}\t${s ? `${s.ownerName}${s.ownerTerr ? `（${fmt(s.ownerTerr)} 格 / ${fmt(s.ownerBal)} 兵）` : ''} → ${ownL}` : ''}\t${ld ? `${ld.t}（${ld.t - l.t}）` : ''}\t${ld ? `(${ld.x},${ld.y}) ${ld.ownerName}` : ''}\t${result}`);
  J.push({ t: l.t, bot: l.bot, pct: l.pct, troops: l.troops, fee: l.fee, b0: l.b0, terr: l.terr, decisionT: s ? s.t : null, site: s ? s.site : null, target: s ? [s.x, s.y] : null, ownerAtDecision: s ? s.ownerName : null, ownerAtLaunch: ownL || null,
    landT: ld ? ld.t : null, landXY: ld ? [ld.x, ld.y] : null, landOwner: ld ? ld.ownerName : null, mate: ld ? ld.mate : null, delivered: ld ? ld.delivered : null, result });
}
P('');
P('B. 合计');
const total = launches.reduce((a, l) => a + l.troops, 0), fees = launches.reduce((a, l) => a + l.fee, 0);
P(`  发船 ${launches.length} 条，带兵 ${fmt(total)}，手续费 ${fmt(fees)}`);
P(`  登上敌方 / 无主地开打：${atkN} 条 ${fmt(atk)} 兵`);
P(`  靠到队友的岸：整船或部分到账 ${handedN} 条共 ${fmt(handed)} 兵；被拒收丢在海里 ${lostN} 条共 ${fmt(lost)} 兵`);
P(`  靠回自己的地：${selfN} 条 ${fmt(selfV)} 兵；没有靠岸记录：${noLand} 条`);
const chg = J.filter((r) => r.ownerAtDecision && r.landOwner && r.mate && !String(r.ownerAtDecision).startsWith('队友'));
P(`  决策拍目标格不是队友的地、靠岸时却是队友的地：${chg.length} 条（${chg.map((r) => `${r.bot}@${r.t}`).join('、') || '无'}）`);
const mateAtDec = J.filter((r) => r.ownerAtDecision && String(r.ownerAtDecision).startsWith('队友'));
P(`  决策拍目标格就已经是队友的地：${mateAtDec.length} 条（${mateAtDec.map((r) => `${r.bot}@${r.t}`).join('、') || '无'}）`);
if (reachTs.size) {
  P('');
  P(`C. 水路能到的岸（--reach；从该号的 coast + border 起步沿水广搜，最远 2500 格；距离 = 水路格数）${reachScan.err ? ' | 出错：' + reachScan.err : ''}`);
  for (const r of reachOut) {
    const en = r.rows.filter((x) => !x.mate && !x.ai).sort((a, b2) => a.d - b2.d);
    const ai = r.rows.filter((x) => x.ai).sort((a, b2) => a.d - b2.d);
    const mates = r.rows.filter((x) => x.mate).sort((a, b2) => a.d - b2.d);
    const f1 = (x) => `${(names[x.o] || 'AI').trim().slice(0, 16)}#${x.o}${x.left ? '（已离开）' : ''} 最近 ${x.d} 格（岸 ${x.cells} 格；他 ${fmt(x.terr)} 格 / ${fmt(x.bal)} 兵）`;
    P(`  t=${r.t} ${r.bot}（海岸 ${r.coastPx} 格，搜到水面 ${fmt(r.water)} 格）：无主地 ${r.neutD < 0 ? '搜不到' : `最近 ${r.neutD} 格（岸 ${r.neutCells} 格）`}；` +
      `敌方真人的岸 ${en.length} 家${en.length ? '：' + en.slice(0, 5).map(f1).join('；') : ''}；内置 AI 的岸 ${ai.length} 家${ai.length ? '（最近 ' + ai[0].d + ' 格）' : ''}；` +
      `队友的岸 ${mates.length} 家（其中我方号 ${mates.filter((x) => x.squad).length} 家${mates.length ? '；最近 ' + mates.slice(0, 3).map((x) => `${botOf.get(x.o) || (names[x.o] || '').trim().slice(0, 12) + '#' + x.o} ${x.d} 格`).join('、') : ''}）`);
  }
}
fs.writeFileSync(path.join(OUT, 'boat_targets.txt'), L.join('\n') + '\n');
fs.writeFileSync(path.join(OUT, 'boat_targets.json'), JSON.stringify({ launches: J, lost, lostN, handed, handedN, atk, atkN, reach: reachOut.map((r) => ({ ...r, rows: r.rows.map((x) => ({ ...x, name: x.o < H ? names[x.o] : 'AI#' + x.o })) })) }, null, 0));
console.log(L.join('\n'));
