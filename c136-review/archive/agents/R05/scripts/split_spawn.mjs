// split_spawn.mjs — 拆盘局的选点串线账：协调器只有一台（SPAWN L1529 /solve，按 matchKey 存一份状态），
//   同一张图的两个并行实例 matchKey 相同（SRC chooseSpawn：`${W}x${H}_${land}_${humans}`），两盘的号共用一份点集。
// 输出：
//   1) 日志里每条 [HL-SPAWN-BACKEND] 指派，按日志行号排，标出它属于哪一族点集（--sets 给出的点集，名字:点;点…）；
//   2) 录像这一盘里我方号的出生指令逐条（拍 → 坐标 → 命中哪一族点集 / 日志里哪个号被指派过这个点）；
//   3) 每个号「日志最后一条指派」与（录像里的号）「最后一条出生指令」；
//   4) 两盘各自的号最后指派点两两距离、同一个点被指派给过几个不同的号。
// 用法：node split_spawn.mjs <matchId> [--sets N:607,18;677,66;…  S:749,347;…] [--seq]（--seq 打印逐条指派序列）
import fs from 'node:fs';
import path from 'node:path';
import { loadReplay, timeline } from './replay_cmds.mjs';

const DATA = process.env.C136_DATA || '/agent/repos/c136-data';
const args = process.argv.slice(2);
const id = args.find((a) => !a.startsWith('--') && /^[AB]\d+$/.test(a));
const SEQ = args.includes('--seq');
const sets = new Map();
{ const i = args.indexOf('--sets'); if (i >= 0) for (let k = i + 1; k < args.length && !args[k].startsWith('--'); k++) { const [nm, pts] = args[k].split(':'); sets.set(nm, new Set(pts.split(';'))); } }
const fam = (x, y) => { for (const [nm, s] of sets) if (s.has(`${x},${y}`)) return nm; return '·'; };
const bare = (n) => String(n ?? '').replace(/\[[^\]]*\]/g, '').trim().toLowerCase();

const dir = path.join(DATA, 'bundles', id);
const d = loadReplay(id); const tl = timeline(d);
const H = d.vu.humanCount; const names = d.vu.playerNamesData ? d.vu.playerNamesData.data : [];
const W = d.vu.mapWidth || d.vu.width || Number((args.find((a) => a.startsWith('--W=')) || '').slice(4)) || 0;

const re = /^(\d+)\s+\[([^\]]+)\] \[HL-SPAWN(-BACKEND)?\] me=(\d+) slot=(\d+)(?: role=(\w+))?.*?-> \((\d+),(\d+)\)(.*)$/;
const assigns = []; const meOf = new Map();
for (const line of fs.readFileSync(path.join(dir, 'in_game.log'), 'utf8').split('\n')) {
  const m = re.exec(line); if (!m) continue;
  const ex = m[9] || '';
  const mad = /minAllyDist=(\d+)/.exec(ex); const bd = /bossDist=(\d+)/.exec(ex); const sq = /squad=(\d+)/.exec(line);
  assigns.push({ line: +m[1], bot: m[2], backend: !!m[3], me: +m[4], slot: +m[5], role: m[6] || 'AUTONOMOUS', x: +m[7], y: +m[8], minAlly: mad ? +mad[1] : null, bossDist: bd ? +bd[1] : null, squadSeen: sq ? +sq[1] : null });
  meOf.set(m[2], +m[4]);
}
const inReplay = new Map();
for (const [bot, me] of meOf) if (me < H && bare(names[me]) === bot.toLowerCase()) inReplay.set(bot, me);
const bots = [...meOf.keys()];
const Xbots = bots.filter((b) => inReplay.has(b)); const Ybots = bots.filter((b) => !inReplay.has(b));

// 宽度：用录像里我方号的出生像素对日志点集反解
const spawns = new Map();
for (const c of tl.cmds) if (c.id === 0) { if (!spawns.has(c.player)) spawns.set(c.player, []); spawns.get(c.player).push({ tick: c.tick, pix: c.dX }); }
const logPts = new Set(assigns.map((a) => `${a.x},${a.y}`));
let bestW = W, bestHit = -1;
if (!W) {
  const ourPix = []; for (const p of inReplay.values()) for (const s of spawns.get(p) || []) ourPix.push(s.pix);
  for (let w = 100; w < 6000; w++) { let hit = 0; for (const px of ourPix) if (logPts.has(`${px % w},${Math.floor(px / w)}`)) hit++; if (hit > bestHit) { bestHit = hit; bestW = w; } }
}
const xy = (px) => ({ x: px % bestW, y: Math.floor(px / bestW) });

console.log(`# ${id} 拆盘选点账｜录像真人 ${H}｜录像里的我方号 ${Xbots.map((b) => `${b}#${inReplay.get(b)}`).join(' ')}｜只在日志里的我方号 ${Ybots.map((b) => `${b}(me=${meOf.get(b)})`).join(' ')}｜地图宽 ${bestW}`);
console.log(`  日志指派 ${assigns.length} 条（后端 ${assigns.filter((a) => a.backend).length}，自主回退 ${assigns.filter((a) => !a.backend).length}）｜不同的点 ${logPts.size} 个｜点集族 ${[...sets.keys()].join('/') || '(未给)'}`);

// 1) 族序列
const famSeq = assigns.map((a) => fam(a.x, a.y));
const runs = []; for (let i = 0; i < assigns.length; i++) { const f = famSeq[i]; if (runs.length && runs[runs.length - 1].f === f) { runs[runs.length - 1].n++; runs[runs.length - 1].to = assigns[i].line; } else runs.push({ f, n: 1, from: assigns[i].line, to: assigns[i].line }); }
console.log(`  按日志行号的点集族游程（族×条数）：${runs.map((r) => `${r.f}×${r.n}`).join(' ')}`);
const cnt = {}; for (const f of famSeq) cnt[f] = (cnt[f] || 0) + 1;
console.log(`  族计数：${Object.entries(cnt).map(([k, v]) => `${k}=${v}`).join(' ')}｜族切换次数 ${runs.length - 1}`);
if (SEQ) for (const a of assigns) console.log(`    行${a.line} ${a.bot.padEnd(8)} me=${a.me} s${a.slot} ${a.role.padEnd(18)} (${a.x},${a.y}) 族=${fam(a.x, a.y)} minAlly=${a.minAlly ?? '-'}${a.backend ? '' : ` 自主(squad=${a.squadSeen})`}`);

// 2) 录像里我方号的出生指令
console.log('  录像里我方号的出生指令（拍→坐标｜族｜日志里被指派过这个点的号）：');
for (const [bot, p] of inReplay) {
  const sp = spawns.get(p) || [];
  const parts = sp.map((s) => { const q = xy(s.pix); const who = [...new Set(assigns.filter((a) => a.x === q.x && a.y === q.y).map((a) => a.bot))]; return `${s.tick}:(${q.x},${q.y})${fam(q.x, q.y)}[${who.map((w) => (w === bot ? '本号' : w)).join('/') || '无'}]`; });
  console.log(`    ${bot}#${p} ${sp.length} 条：${parts.join(' ')}`);
}

// 3) 每个号最后指派
console.log('  每个号的指派条数、换点次数、最后一条指派：');
for (const b of bots) {
  const A = assigns.filter((a) => a.bot === b); const last = A[A.length - 1];
  let moves = 0; for (let i = 1; i < A.length; i++) if (A[i].x !== A[i - 1].x || A[i].y !== A[i - 1].y) moves++;
  const fams = {}; for (const a of A) { const f = fam(a.x, a.y); fams[f] = (fams[f] || 0) + 1; }
  let fin = '';
  if (inReplay.has(b)) { const sp = spawns.get(inReplay.get(b)) || []; if (sp.length) { const q = xy(sp[sp.length - 1].pix); fin = `｜录像最后出生指令 拍${sp[sp.length - 1].tick} (${q.x},${q.y})${q.x === last.x && q.y === last.y ? ' =日志最后指派' : ' ≠日志最后指派'}`; } }
  console.log(`    ${b.padEnd(8)} ${inReplay.has(b) ? '录像盘' : '另一盘'} me=${meOf.get(b)} s${last.slot} 指派 ${A.length} 条 换点 ${moves} 次 族 ${Object.entries(fams).map(([k, v]) => `${k}${v}`).join(' ')}｜最后 行${last.line} ${last.role} (${last.x},${last.y}) minAlly=${last.minAlly ?? '-'}${fin}`);
}

// 4) 距离与复用
const lastOf = new Map(bots.map((b) => { const A = assigns.filter((a) => a.bot === b); return [b, A[A.length - 1]]; }));
const dist = (a, b) => Math.round(Math.hypot(a.x - b.x, a.y - b.y));
for (const [nm, grp] of [['录像盘', Xbots], ['另一盘', Ybots]]) {
  const pr = []; for (let i = 0; i < grp.length; i++) for (let j = i + 1; j < grp.length; j++) pr.push(dist(lastOf.get(grp[i]), lastOf.get(grp[j])));
  const near = grp.map((b) => Math.min(...grp.filter((o) => o !== b).map((o) => dist(lastOf.get(b), lastOf.get(o)))));
  if (pr.length) console.log(`  ${nm} ${grp.length} 号最后指派点：两两最小 ${Math.min(...pr)} 最大 ${Math.max(...pr)}｜各号到最近同盘队友 ${near.join('/')}`);
}
const cross = []; for (const a of Xbots) for (const b of Ybots) cross.push({ a, b, d: dist(lastOf.get(a), lastOf.get(b)) });
cross.sort((p, q) => p.d - q.d);
if (cross.length) console.log(`  跨盘最近的最后指派点对：${cross.slice(0, 4).map((c) => `${c.a}↔${c.b} ${c.d}px`).join('，')}`);
const usedBy = new Map(); for (const a of assigns) { const k = `${a.x},${a.y}`; if (!usedBy.has(k)) usedBy.set(k, new Set()); usedBy.get(k).add(a.bot); }
const multi = [...usedBy.entries()].filter(([, s]) => s.size >= 2).sort((p, q) => q[1].size - p[1].size);
console.log(`  同一个点先后指派给 ≥2 个不同号的点 ${multi.length}/${usedBy.size} 个；其中同时出现录像盘号与另一盘号的 ${multi.filter(([, s]) => [...s].some((b) => inReplay.has(b)) && [...s].some((b) => !inReplay.has(b))).length} 个`);
for (const [k, s] of multi.slice(0, 8)) console.log(`    (${k}) 族=${fam(...k.split(',').map(Number))} → ${[...s].join(' ')}`);
