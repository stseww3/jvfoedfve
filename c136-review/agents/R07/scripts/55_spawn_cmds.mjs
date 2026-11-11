#!/usr/bin/env node
// 55_spawn_cmds.mjs — R07：录像里的出生指令（id=0）逐条列出来：第几步到的、谁、指向哪。
// 只解码录像，不重演。66_spawn_truth.mjs 只数「出生阶段里生效的选点调用」；这里连出生阶段结束之后
// 才到的出生指令也列出来（引擎 chooseSpawn 在 spawnPhase 结束后直接 return false，这种指令对局面没有任何作用）。
//
// 录像的时间轴（c102-replay-lib.mjs makeStepper）：每一步要么是一帧指令（jY=1，ja=条数），要么是空步（jY=0，ja=连续空步数）。
// 出生阶段 = 第 0 ~ jJ 步（真人位 ≤50 时 jJ=40，否则 50；≤2 时 30），第 jJ 步的指令执行完就 endSpawnPhase。
//
// 用法（套重计算闸）：
//   bash c136-review/tools/run-heavy.sh node c136-review/agents/R07/scripts/55_spawn_cmds.mjs <matchId> [<matchId>...]
// 输出：out/<matchId>/spawn_cmds.tsv（step, phase, order, player, bot, x, y）
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const DATA = '/agent/repos/c136-data';
const HERE = path.dirname(fileURLToPath(import.meta.url));
const LIB = await import(path.join(DATA, 'src/sim/tools/c102-replay-lib.mjs'));
const SIM = await import(path.join(DATA, 'src/sim/sim/index.js'));

for (const mid of process.argv.slice(2)) {
  const rp = path.join(DATA, 'bundles', mid, 'replay.txt');
  if (!fs.existsSync(rp)) { console.log(`${mid}\t（没有 replay.txt）`); continue; }
  const OUT = path.join(HERE, '..', 'out', mid);
  fs.mkdirSync(OUT, { recursive: true });
  const d = LIB.decodeReplay(fs.readFileSync(rp, 'utf8'));
  const H = d.vu.humanCount;
  const names = d.vu.playerNamesData ? Array.from(d.vu.playerNamesData).slice(0, H).map((s) => String(s ?? '')) : [];
  const logText = fs.readFileSync(path.join(DATA, 'bundles', mid, 'in_game.log'), 'utf8').split('\n');
  const realBots = new Set();
  for (const ln of logText) { const m = /^\d+\t\[([A-Za-z0-9_]+)\] /.exec(ln); if (m) realBots.add(m[1]); }
  const botOf = new Map();
  for (const b of realBots) for (let p = 0; p < H; p++) if (names[p].trim().toLowerCase().endsWith(b.toLowerCase())) { botOf.set(p, b); break; }

  // 地图宽度：出生指令的 dX = y*W + x
  const { mapIdx, mapSeed } = LIB.mapOf(d.vu);
  let W = 0;
  try { const m = SIM.loadMap(mapIdx, mapSeed); W = m.W ?? m.width ?? 0; } catch (e) { W = 0; }
  if (!W) {
    const g = /map=(\d+)x(\d+)/.exec(logText.find((l) => l.includes('[BACKEND-SPAWN-COORD] Solved')) || '');
    W = g ? +g[1] : 0;
  }

  const jJ = H <= 2 ? 30 : H <= 50 ? 40 : 50;
  const rows = [];
  let step = 0, ci = 0, firstAttackStep = -1;
  for (let iv = 0; iv < d.ja.length; iv++) {
    const n = d.ja[iv];
    if (d.jY[iv]) {
      for (let k = 0; k < n; k++) {
        const c = d.cmds[ci + k];
        if (c.id === 0) rows.push({ step, phase: step <= jJ ? 'spawn' : 'late', order: k, player: c.player, bot: botOf.get(c.player) || '', x: W ? c.dX % W : -1, y: W ? Math.floor(c.dX / W) : -1 });
        else if (c.id === 1 && firstAttackStep < 0) firstAttackStep = step;
      }
      ci += n;
      step += 1;
    } else step += n;
  }
  const cols = ['step', 'phase', 'order', 'player', 'bot', 'x', 'y'];
  fs.writeFileSync(path.join(OUT, 'spawn_cmds.tsv'), `# ${mid} 录像里全部出生指令（55_spawn_cmds.mjs）；真人位 ${H}，出生阶段 = 第 0~${jJ} 步，地图宽 ${W}，第一条进攻指令在第 ${firstAttackStep} 步，录像共 ${step} 步\n` + cols.join('\t') + '\n' + rows.map((r) => cols.map((c) => r[c]).join('\t')).join('\n') + '\n');
  const mine = rows.filter((r) => r.bot);
  console.log(`${mid}\t真人位 ${H}\t出生阶段 0~${jJ} 步\t出生指令共 ${rows.length}（阶段内 ${rows.filter((r) => r.phase === 'spawn').length}、阶段后 ${rows.filter((r) => r.phase === 'late').length}）\t我方 ${mine.length}（阶段内 ${mine.filter((r) => r.phase === 'spawn').length}、阶段后 ${mine.filter((r) => r.phase === 'late').length}）\t第一条进攻在第 ${firstAttackStep} 步`);
}
