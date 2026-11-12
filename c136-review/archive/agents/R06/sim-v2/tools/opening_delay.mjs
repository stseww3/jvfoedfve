#!/usr/bin/env node
// opening_delay.mjs — 用策略日志里带本机拍号的两类发令记录，直接量「下令拍 → 录像执行拍」的间隔（不经影子配对）：
//   [HL-OPENING] t=…   开局扩张的陆攻（打无主地），策略在本机第 t 拍发出
//   [HL-DISPATCH] t=…  捐款（c116 系），策略在本机第 t 拍发出；成交的才进录像
// 每条日志配同一席位、执行拍 ≥ t 的第一条还没配过的同类录像指令（陆攻：目标是无主地；捐款：收款人相同）。
// 用法（在 c136-review/agents/R06 下）：node sim-v2/tools/opening_delay.mjs <局号…> [--live-clean 目录] [--tmax 600] [--max-gap 60] [--json 输出文件]
//   --live-clean  不逐个写局号，而是取 --mode live 结果目录（sim-v2/calib/live）里全部「不卡的局」：
//                 630~1530 拍窗口跑满、同拍批占比 < 15%、日志快照与重放逐条相同、我方 ≥ 6 席（与 tools/live_table.mjs 的口径相同）
//   --json        把分布写成文件（g0_report.mjs 的「d 的实测分布对 C1 模型」那张表读它）
import fs from 'node:fs';
import path from 'node:path';
import { loadMatch, BUNDLES, NEUTRAL } from '../lib/match.mjs';

const args = process.argv.slice(2);
const argOf = (k, d) => { const i = args.indexOf(k); return i >= 0 ? +args[i + 1] : d; };
const TMAX = argOf('--tmax', 600), MAXGAP = argOf('--max-gap', 60);
const JSON_OUT = args.includes('--json') ? args[args.indexOf('--json') + 1] : '';
const mids = args.filter((a, i) => !a.startsWith('--') && !(args[i - 1] || '').startsWith('--'));
const LIVE_CLEAN = args.includes('--live-clean') ? args[args.indexOf('--live-clean') + 1] : '';
if (LIVE_CLEAN) {
  for (const f of fs.readdirSync(LIVE_CLEAN).sort()) {
    if (!f.endsWith('.json')) continue;
    const r = JSON.parse(fs.readFileSync(path.join(LIVE_CLEAN, f), 'utf8'));
    if (r.error || !r.windows || !r.windows.length) continue;
    const w = r.windows[0];
    if (w.t1 !== w.asked[1] || !(r.logSnaps && r.logSnaps.n > 0 && r.logSnaps.ok === r.logSnaps.n) || r.squad < 6) continue;
    if (w.batchShare < 0.15 && !mids.includes(r.match)) mids.push(r.match);
  }
}
const all = { open: [], don: [], openPairs: [], donPairs: [] };
const used = [], seatGaps = new Map();
const noteSeat = (mid, p, gap) => { const k = `${mid}|${p}`; if (!seatGaps.has(k)) seatGaps.set(k, []); seatGaps.get(k).push(gap); };
for (const mid of mids) {
  let M;
  try { M = loadMatch(mid); } catch (e) { console.log(`${mid}: ${e.message}`); continue; }
  const d = M.d, H = M.H;
  // 每个席位的录像指令（局内拍）
  const atk = new Map(), don = new Map();
  let units = 0, iw = 0;
  for (let i = 0; i < d.ja.length; i++) {
    if (d.jY[i]) {
      const tick = units - M.spawnSteps;
      for (let a = iw; a < iw + d.ja[i]; a++) {
        const c = d.cmds[a];
        if (c.player >= H || tick < 0) continue;
        if (c.id === 1 && c.dZ >= NEUTRAL) { if (!atk.has(c.player)) atk.set(c.player, []); atk.get(c.player).push({ t: tick, used: false }); }
        if (c.id === 2) { if (!don.has(c.player)) don.set(c.player, []); don.get(c.player).push({ t: tick, to: c.dZ, used: false }); }
      }
      iw += d.ja[i];
      units += 1;
    } else units += d.ja[i];
  }
  const file = path.join(BUNDLES, mid, 'in_game.log');
  const open = [], dn = [];
  for (const line of fs.readFileSync(file, 'utf8').split('\n')) {
    let m = line.match(/\[([^\]]+)\] \[HL-OPENING\] t=(\d+) .*expand/);
    if (m) {
      const p = M.log.seatOf.get(m[1]), t = +m[2];
      if (p === undefined || t > TMAX) continue;
      const c = (atk.get(p) || []).find((x) => !x.used && x.t >= t);
      if (c && c.t - t <= MAXGAP) { c.used = true; open.push(c.t - t); all.openPairs.push([t, c.t]); noteSeat(mid, p, c.t - t); }
      continue;
    }
    m = line.match(/\[([^\]]+)\] \[HL-DISPATCH\] t=(\d+) \S+ pct=(\d+)\/1024 -> ally=(\d+)/);
    if (m) {
      const p = M.log.seatOf.get(m[1]), t = +m[2], to = +m[4];
      if (p === undefined) continue;
      const c = (don.get(p) || []).find((x) => !x.used && x.t >= t && x.to === to);
      if (c && c.t - t <= MAXGAP) { c.used = true; dn.push(c.t - t); all.donPairs.push([t, c.t]); noteSeat(mid, p, c.t - t); }
    }
  }
  const qs = (a) => { if (!a.length) return '-'; const s = a.slice().sort((x, y) => x - y); const q = (p) => s[Math.min(s.length - 1, Math.floor(p * s.length))]; return `${a.length} 条：最小 ${s[0]}，P10 ${q(0.1)}，P25 ${q(0.25)}，中位 ${q(0.5)}，P75 ${q(0.75)}，P90 ${q(0.9)}，最大 ${s[s.length - 1]}`; };
  console.log(`${mid}：开局陆攻 ${qs(open)}｜捐款 ${qs(dn)}`);
  all.open.push(...open); all.don.push(...dn);
  used.push(mid);
}
const hist = (a) => { const h = new Map(); for (const v of a) h.set(v, (h.get(v) || 0) + 1); return [...h.entries()].sort((x, y) => x[0] - y[0]).map(([k, v]) => `${k}:${v}`).join(' '); };
console.log(`合计 开局陆攻 ${all.open.length} 条，间隔分布（拍:条数）：${hist(all.open)}`);
console.log(`合计 捐款 ${all.don.length} 条，间隔分布（拍:条数）：${hist(all.don)}`);

// 通道模型 E = 7 × ceil((t + d) / 7) 里 d 的累积分布：对下令拍 t，「执行拍 ≤ 7 × floor((t + k) / 7)」当且仅当 d ≤ 7 × floor((t + k) / 7) − t。
// 取 t ≡ −k (mod 7) 的那些指令，上式右边正好是 k → P(d ≤ k) = 这些指令里 执行拍 − 下令拍 ≤ k 的占比。每个 k 用的是不同相位的指令，互不重叠。
function cdf(pairs, name) {
  const out = [], rows = [];
  for (let k = 1; k <= 21; k++) {
    const sel = pairs.filter(([t]) => (((t + k) % 7) + 7) % 7 === 0);
    const le = sel.filter(([t, E]) => E - t <= k).length;
    rows.push([k, sel.length, le]);
    if (sel.length < 8) { out.push(`${k}:-`); continue; }
    out.push(`${k}:${Math.round(100 * le / sel.length)}%(${sel.length})`);
  }
  console.log(`${name} 的 d 累积分布 P(d ≤ k)（括号里 = 用到的指令条数）：${out.join(' ')}`);
  return rows;
}
const cOpen = cdf(all.openPairs, '开局陆攻');
const cDon = cdf(all.donPairs, '捐款');
const cAll = cdf([...all.openPairs, ...all.donPairs], '两类合计');
if (JSON_OUT) {
  // 每个席位的平均间隔（至少 8 条的席位）：看「慢页面」占多少
  const seatMeans = [...seatGaps.entries()].filter(([, a]) => a.length >= 8).map(([k, a]) => [k.split('|')[0], +k.split('|')[1], +(a.reduce((x, y) => x + y, 0) / a.length).toFixed(2), a.length]);
  fs.mkdirSync(path.dirname(path.resolve(JSON_OUT)), { recursive: true });
  fs.writeFileSync(JSON_OUT, JSON.stringify({ mids: used, tmax: TMAX, maxGap: MAXGAP, open: { n: all.open.length }, don: { n: all.don.length },
    cdf: { open: cOpen, don: cDon, all: cAll }, gapsAll: [...all.open, ...all.don].sort((a, b) => a - b), seatMeans }));
  console.log(`写入 ${JSON_OUT}`);
}
