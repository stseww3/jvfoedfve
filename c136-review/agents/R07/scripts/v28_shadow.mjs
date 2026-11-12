#!/usr/bin/env node
// v28_shadow.mjs — R07：在「按录像重演出来的真实局面」上影子运行任意一份策略文件（默认 v28），只记它想发的指令。
//
// 和 65_shadow.mjs 同一个原理（resim 重演 + 每拍结算后对我方每个号各跑一次 act(g)，指令只记不执行），区别：
//   · 策略文件用 --src 给路径（v28 草稿、Vc 原文都行），参数用 --params 给 JSON（模块开关就在这里关 / 开）；
//   · 不做 Vb 专用的归因诊断，只出四样东西：指令流、报错、[V28-*] 日志条数、策略对象上的 v28 计数器；
//   · 给策略一个可控的钟 window.__c136Now（毫秒 = 拍号 × 56），免得模拟器跑得快被当成「追帧」。
//
// 用法（必须套重计算闸；一次只跑一个）：
//   bash c136-review/tools/run-heavy.sh node c136-review/agents/R07/scripts/v28_shadow.mjs <matchId> \
//        [--src 路径] [--label 名字] [--params '{"enableInflightLedger":0}'] [--from T0] [--until T1] [--bots a,b|all]
//        [--quit engine|none] [--share-window 1|0]
// 输出：
//   out/v28/<matchId>_<label>.json            （进仓库，小）报错清单、各号指令计数、[V28-*] 日志按标签计数、策略对象上的计数器（policy.v28n）
//   out/_cache/v28/<matchId>_<label>_cmds.tsv （不进仓库）每条影子指令：t、号、种类、pct、目标、附加参数
//   out/_cache/v28/<matchId>_<label>_log.txt  （不进仓库）[V28-*] 与 [SHADOW-ERROR] 日志原文
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const DATA = '/agent/repos/c136-data';
const HERE = path.dirname(fileURLToPath(import.meta.url));
const args = process.argv.slice(2);
const mid = args[0];
if (!mid || mid.startsWith('--')) { console.error('用法：v28_shadow.mjs <matchId> [--src 路径] [--label 名字] [--params JSON] [--from T0] [--until T1] [--bots a,b|all]'); process.exit(2); }
const opt = (k, d) => { const i = args.indexOf(k); return i >= 0 ? args[i + 1] : d; };
const OUT = path.join(HERE, '..', 'out', 'v28');
const RAW = path.join(HERE, '..', 'out', '_cache', 'v28');
fs.mkdirSync(OUT, { recursive: true });
fs.mkdirSync(RAW, { recursive: true });

const srcPath = path.resolve(opt('--src', path.join(HERE, '..', 'v28', 'v28-team-organism.js')));
const label = opt('--label', path.basename(srcPath).replace(/\.m?js$/, ''));
const params = JSON.parse(opt('--params', '{}'));
const from = +opt('--from', 0);
const until = +opt('--until', 1e9);
const quitMode = opt('--quit', 'engine');

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
globalThis.window = {
  __hlLog: (s) => { const text = String(s); if (/^\[(V28|SHADOW)/.test(text)) logs.push({ bot: curBot, t: curT, text }); const m = /^\[([A-Z0-9-]+)\]/.exec(text); if (m) tagCount[m[1]] = (tagCount[m[1]] || 0) + 1; },
  __tsbSquadSlot: 0,
  __c136Now: () => curT * 56,
};
const tagCount = {};

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

const cmds = [];
const errors = [];
const quitSet = new Set();
const proto = SIM.Game.prototype;
const origTick = proto.tick;
proto.tick = function () {
  origTick.call(this);
  const g = this;
  if (g.spawnPhase || g.over || g.t > until || g.t < from) return;
  if (!g.names) g.names = names;
  if (quitMode === 'engine') { for (let q = 0; q < H; q++) if (g.state[q] === 2) quitSet.add(q); window.__quitPlayers = quitSet; }
  const onlineHad = Object.prototype.hasOwnProperty.call(g, 'online');
  const online0 = g.online;
  g.online = true;
  for (const [b, p] of pol) {
    const me = p.me;
    if (!g.alive[me] || g.state[me] === 2) continue;
    curBot = b; curT = g.t;
    window.__tsbSquadSlot = slotOf.has(b) ? slotOf.get(b) : me % 10;
    const rec = (kind, pct, target, extra) => { cmds.push([g.t, b, kind, pct, target, extra ?? '']); };
    g.attack = (pct, target, pl = me) => {
      if (pl !== me) return false;
      const tg = Math.min(target, NEUTRAL);
      if (tg < NEUTRAL && g.alive[tg] && !g.isEnemy(me, tg)) return false;
      if (!g.hasAttack(me, tg < NEUTRAL && !g.alive[tg] ? NEUTRAL : tg) && !g.hasFreeSlot(me)) return false;
      rec('attack', pct, tg); return true;
    };
    g.donate = (pct, q, pl = me) => { if (pl !== me || !g.alive[q] || !g.isTeammate(me, q)) return false; rec('donate', pct, q); return true; };
    g.boat = (pct, water, dir, pl = me) => { if (!g.boatsAllowed(me)) return false; rec('boat', pct, water, dir); return true; };
    g.boatTo = (pct, target, pl = me, radius = 32) => { if (!g.boatsAllowed(me)) return false; rec('boatTo', pct, target, radius); return true; };
    g.chase = (pct, id, pl = me) => { rec('chase', pct, NEUTRAL, id); return true; };
    g.recall = (id, pl = me) => { rec('recall', 0, NEUTRAL, id); return true; };
    g.retreat = (target, pl = me) => { rec('retreat', 0, Math.min(target, NEUTRAL)); return true; };
    try { p.act(g); } catch (e) {
      const where = String((e && e.stack) || '').split('\n').slice(1, 4).map((s) => s.trim().replace(/\(?file:\/\/\S*strategy-[^:]+\.mjs:(\d+):\d+\)?/, (_, ln) => `L${+ln - 1}`)).join(' < ');
      errors.push({ t: g.t, bot: b, msg: String(e && e.message), where });
      logs.push({ bot: b, t: g.t, text: `[SHADOW-ERROR] ${e && e.message} @ ${where}` });
    }
    delete g.attack; delete g.donate; delete g.boat; delete g.boatTo; delete g.chase; delete g.recall; delete g.retreat;
  }
  if (onlineHad) g.online = online0; else delete g.online;
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
    for (const [k, n] of Object.entries(p.v28n)) statSum[k] = (statSum[k] || 0) + n;
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
fs.writeFileSync(path.join(OUT, `${mid}_${label}.json`), JSON.stringify(summary, null, 1) + '\n');
fs.writeFileSync(path.join(RAW, `${mid}_${label}_log.txt`), logs.map((l) => `${l.t}\t[${l.bot}] ${l.text}`).join('\n') + '\n');
console.log(`${mid} ${label}: 重演 ${out.endTick} 拍 ${summary.seconds}s；快照核对 ${v.bothExact}/${v.rows}；影子指令 ${cmds.length}（${Object.entries(kinds).map(([k, n]) => `${k}×${n}`).join(' ')}）；报错 ${errors.length}`);
if (errors.length) for (const e of errors.slice(0, 5)) console.log(`  报错 t=${e.t} ${e.bot}: ${e.msg} @ ${e.where}`);
const vt = Object.entries(tagCount).filter(([k]) => k.startsWith('V28')).map(([k, n]) => `${k}×${n}`).join(' ');
if (vt) console.log(`  [V28-*] 日志：${vt}`);
if (Object.keys(statSum).length) console.log(`  v28 计数器：${Object.entries(statSum).sort().map(([k, n]) => `${k}=${n}`).join(' ')}`);
