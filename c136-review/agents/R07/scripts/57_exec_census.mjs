#!/usr/bin/env node
// 57_exec_census.mjs — R07：全部对局包的「执行层」普查的第一步：只解码录像（不重演），
// 把每一局的选点指令和全场真人的进攻 / 捐款 / 船 / 追击指令按落地拍列出来，顺手数「同一号同一拍 ≥3 条」的批。
//
// 录像的时间轴见 55_spawn_cmds.mjs：出生阶段 = 第 0~jJ 步，之后每一步 = 一拍，拍号 = 步号 − (jJ + 1)。
// 指令种类：id=1 进攻、2 捐款、3 船、4 追击（dX=849 是召回，不算）；和 74_side_flow.mjs 的 humans_cmd.tsv 同口径。
//
// 用法（套重计算闸；不给局号就是全部带 replay.txt 的对局包）：
//   bash c136-review/tools/run-heavy.sh node c136-review/agents/R07/scripts/57_exec_census.mjs [--root <目录>] [<matchId>...]
// 输出：<root>/<matchId>/spawn_cmds.tsv、<root>/<matchId>/humans_cmd.tsv（精简版：t p name squad kind）、<root>/<matchId>/squad_players.tsv（在这份录像里的我方号）、
//       <root>/census_batches.tsv（每局一行：我方 / 其他真人的批）。root 默认 out/_cache/census（不进 git）。
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const DATA = '/agent/repos/c136-data';
const HERE = path.dirname(fileURLToPath(import.meta.url));
const LIB = await import(path.join(DATA, 'src/sim/tools/c102-replay-lib.mjs'));
const SIM = await import(path.join(DATA, 'src/sim/sim/index.js'));

const args = process.argv.slice(2);
let ROOT = path.join(HERE, '..', 'out', '_cache', 'census');
const ri = args.indexOf('--root');
if (ri >= 0) { ROOT = path.resolve(args[ri + 1]); args.splice(ri, 2); }
let mids = args;
if (!mids.length) mids = fs.readdirSync(path.join(DATA, 'bundles')).filter((m) => fs.existsSync(path.join(DATA, 'bundles', m, 'replay.txt'))).sort();
fs.mkdirSync(ROOT, { recursive: true });

const KIND = { 1: 'attack', 2: 'donate', 3: 'boat', 4: 'chase' };
const sumRows = [];
for (const mid of mids) {
  const rp = path.join(DATA, 'bundles', mid, 'replay.txt');
  const lp = path.join(DATA, 'bundles', mid, 'in_game.log');
  if (!fs.existsSync(rp) || !fs.existsSync(lp)) { console.log(`${mid}\t（缺 replay.txt 或 in_game.log）`); continue; }
  let d;
  try { d = LIB.decodeReplay(fs.readFileSync(rp, 'utf8')); } catch (e) { console.log(`${mid}\t（录像解码失败：${String(e.message).slice(0, 60)}）`); continue; }
  const H = d.vu.humanCount;
  const names = d.vu.playerNamesData ? Array.from(d.vu.playerNamesData).slice(0, H).map((s) => String(s ?? '')) : [];
  const logText = fs.readFileSync(lp, 'utf8').split('\n');
  const realBots = new Set();
  for (const ln of logText) { const m = /^\d+\t\[([A-Za-z0-9_]+)\] /.exec(ln); if (m) realBots.add(m[1]); }
  const botOf = new Map();
  for (const b of realBots) for (let p = 0; p < H; p++) if (names[p].trim().toLowerCase().endsWith(b.toLowerCase())) { botOf.set(p, b); break; }

  let W = 0;
  try { const { mapIdx, mapSeed } = LIB.mapOf(d.vu); const m = SIM.loadMap(mapIdx, mapSeed); W = m.W ?? m.width ?? 0; } catch (e) { W = 0; }
  if (!W) { const g = /map=(\d+)x(\d+)/.exec(logText.find((l) => l.includes('[BACKEND-SPAWN-COORD] Solved')) || ''); W = g ? +g[1] : 0; }

  const jJ = H <= 2 ? 30 : H <= 50 ? 40 : 50;
  const spawn = [], cmds = [];
  let step = 0, ci = 0, firstAttackStep = -1;
  for (let iv = 0; iv < d.ja.length; iv++) {
    const n = d.ja[iv];
    if (d.jY[iv]) {
      for (let k = 0; k < n; k++) {
        const c = d.cmds[ci + k];
        if (c.player >= H) continue;
        if (c.id === 0) spawn.push({ step, phase: step <= jJ ? 'spawn' : 'late', order: k, player: c.player, bot: botOf.get(c.player) || '', x: W ? c.dX % W : -1, y: W ? Math.floor(c.dX / W) : -1 });
        else if (KIND[c.id] && !(c.id === 4 && c.dX === 849)) {
          if (c.id === 1 && firstAttackStep < 0) firstAttackStep = step;
          cmds.push({ t: step - (jJ + 1), p: c.player, kind: KIND[c.id] });
        }
      }
      ci += n;
      step += 1;
    } else step += n;
  }
  const OUT = path.join(ROOT, mid);
  fs.mkdirSync(OUT, { recursive: true });
  const cols = ['step', 'phase', 'order', 'player', 'bot', 'x', 'y'];
  fs.writeFileSync(path.join(OUT, 'spawn_cmds.tsv'), `# ${mid} 录像里全部出生指令（57_exec_census.mjs）；真人位 ${H}，出生阶段 = 第 0~${jJ} 步，地图宽 ${W}，第一条进攻指令在第 ${firstAttackStep} 步，录像共 ${step} 步\n` + cols.join('\t') + '\n' + spawn.map((r) => cols.map((c) => r[c]).join('\t')).join('\n') + '\n');
  // 对局包的日志里可能有不在这份录像里的号（分到了别的房间）：只有名字在录像里对得上的号才算「在场」
  fs.writeFileSync(path.join(OUT, 'squad_players.tsv'), `# ${mid} 录像里对得上名字的我方号（57_exec_census.mjs）；日志里有 ${realBots.size} 个号，录像里 ${botOf.size} 个；录像最后一拍 ${step - (jJ + 1)}\nplayer\tbot\n` + [...botOf].map(([p, b]) => `${p}\t${b}`).join('\n') + '\n');
  fs.writeFileSync(path.join(OUT, 'humans_cmd.tsv'), 't\tp\tname\tsquad\tkind\n' + cmds.map((c) => `${c.t}\t${c.p}\t${names[c.p].replace(/[\t\n]/g, ' ')}\t${botOf.has(c.p) ? 1 : 0}\t${c.kind}`).join('\n') + '\n');

  // 批：同一号同一拍 ≥3 条
  const grp = new Map();
  for (const c of cmds) { const k = c.p + '@' + c.t; grp.set(k, (grp.get(k) || 0) + 1); }
  const st = { sq: [0, 0, 0, 0, 0], ot: [0, 0, 0, 0, 0] }; // 批数、条数、正好 9 条的批、超过 9 条的批、最大一批
  const per = { sq: [0, 0, 0, 0], ot: [0, 0, 0, 0] };       // 四时段的批数
  for (const [k, n] of grp) {
    if (n < 3) continue;
    const [p, t] = k.split('@').map(Number);
    const s = botOf.has(p) ? 'sq' : 'ot';
    st[s][0]++; st[s][1] += n; if (n === 9) st[s][2]++; if (n > 9) st[s][3]++; if (n > st[s][4]) st[s][4] = n;
    per[s][t < 600 ? 0 : t < 1500 ? 1 : t < 3000 ? 2 : 3]++;
  }
  const nSq = cmds.filter((c) => botOf.has(c.p)).length;
  const notMod7 = cmds.filter((c) => botOf.has(c.p) && c.t % 7 !== 0).length;
  const row = [mid, H, realBots.size, botOf.size, step - (jJ + 1), nSq, cmds.length - nSq, ...st.sq, per.sq.join('/'), ...st.ot, per.ot.join('/'), notMod7,
    spawn.filter((r) => r.bot).length, spawn.filter((r) => !r.bot).length, spawn.filter((r) => r.phase === 'late').length];
  sumRows.push(row.join('\t'));
}
const head = ['matchId', 'humans', 'logBots', 'squadBots', 'lastTick', 'squadCmds', 'otherCmds', 'sqBatches', 'sqBatchCmds', 'sqBatch9', 'sqBatchGt9', 'sqBatchMax', 'sqBatchesByPeriod',
  'otBatches', 'otBatchCmds', 'otBatch9', 'otBatchGt9', 'otBatchMax', 'otBatchesByPeriod', 'squadCmdsNotMod7', 'squadSpawnCmds', 'otherSpawnCmds', 'spawnCmdsAfterPhase'];
fs.writeFileSync(path.join(ROOT, 'census_batches.tsv'), head.join('\t') + '\n' + sumRows.join('\n') + '\n');
console.log(`写了 ${sumRows.length} 局到 ${ROOT}`);
