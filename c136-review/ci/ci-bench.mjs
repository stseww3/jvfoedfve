#!/usr/bin/env node
// ci-bench.mjs — Parallel GitHub Actions runner & summarizer for c136 teamgate-v2 benchmarks
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, '../..');
const JOB_FILE = path.join(ROOT, 'sim-jobs/c136-bench.json');

const args = process.argv.slice(2);

if (args[0] === '--summarize') {
  const outDir = path.resolve(args[1] || 'c136-ci-out');
  const files = fs.readdirSync(outDir).filter((f) => f.startsWith('shard-') && f.endsWith('.json')).sort();
  const rows = [];
  for (const f of files) {
    const data = JSON.parse(fs.readFileSync(path.join(outDir, f), 'utf8'));
    if (Array.isArray(data.results)) rows.push(...data.results);
  }
  const byArm = new Map();
  for (const r of rows) {
    if (!byArm.has(r.arm)) byArm.set(r.arm, []);
    byArm.get(r.arm).push(r);
  }
  const lines = [];
  lines.push(`# c136 Cloud Parallel Benchmark Summary (${rows.length} runs across ${files.length} shards)\n`);
  lines.push(`| Arm | Rooms | Wins vs Base | Mean Land Share | Delta Land vs Base | Mean Dup Share | Mean Quota Reject | Total Net Prod | Pre-3000 Deaths | Errors |`);
  lines.push(`|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|`);
  const baseMap = new Map();
  for (const r of byArm.get('baseline (v27)') || []) baseMap.set(`${r.room}_${r.channel}`, r);

  for (const [arm, list] of byArm.entries()) {
    let wins = 0, sumLand = 0, sumDelta = 0, sumDup = 0, sumQRej = 0, qRejN = 0, sumProd = 0, sumDead = 0, sumErr = 0;
    for (const r of list) {
      const b = baseMap.get(`${r.room}_${r.channel}`);
      sumLand += r.landShare;
      if (b) {
        if (r.landShare > b.landShare) wins++;
        sumDelta += r.landShare - b.landShare;
      }
      sumDup += r.dupShare || 0;
      if (typeof r.quotaRej === 'number') { sumQRej += r.quotaRej; qRejN++; }
      sumProd += r.netProd || 0;
      sumDead += r.dead3000 || 0;
      sumErr += r.errors || 0;
    }
    const n = Math.max(1, list.length);
    lines.push(
      `| **${arm}** | ${list.length} | ${arm === 'baseline (v27)' ? '-' : `${wins}/${list.length}`} | ${(sumLand / n).toFixed(4)} | ${arm === 'baseline (v27)' ? '0.0000' : (sumDelta / n >= 0 ? '+' : '') + (sumDelta / n).toFixed(4)} | ${(100 * sumDup / n).toFixed(2)}% | ${qRejN ? (100 * sumQRej / qRejN).toFixed(2) + '%' : '-'} | ${(sumProd / 1e6).toFixed(2)}M | ${sumDead} | ${sumErr} |`
    );
  }
  lines.push(`\n## Per-Room Full Breakdown (\`v28-full\` vs \`baseline (v27)\`)\n`);
  lines.push(`| Room | Channel | Base Strategy | Base Land | v28 Land | Delta Land | Base Dup | v28 Dup | Base QuotaRej | v28 QuotaRej | Base NetProd | v28 NetProd |`);
  lines.push(`|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|`);
  for (const r of (byArm.get('v28-full (P1..P8)') || []).sort((a, b) => a.room.localeCompare(b.room))) {
    const b = baseMap.get(`${r.room}_${r.channel}`);
    if (!b) continue;
    const d = r.landShare - b.landShare;
    lines.push(
      `| **${r.room}** | ${r.channel} | \`${b.strategy}\` | ${b.landShare.toFixed(4)} | **${r.landShare.toFixed(4)}** | **${d >= 0 ? '+' : ''}${d.toFixed(4)}** | ${(100 * (b.dupShare || 0)).toFixed(1)}% | **${(100 * (r.dupShare || 0)).toFixed(1)}%** | ${typeof b.quotaRej === 'number' ? (100 * b.quotaRej).toFixed(1) + '%' : '-'} | **${typeof r.quotaRej === 'number' ? (100 * r.quotaRej).toFixed(1) + '%' : '-'}** | ${(b.netProd / 1e6).toFixed(2)}M | **${(r.netProd / 1e6).toFixed(2)}M** |`
    );
  }
  const md = lines.join('\n') + '\n';
  fs.writeFileSync(path.join(outDir, 'all-results.json'), JSON.stringify(rows, null, 2));
  process.stdout.write(md);
  process.exit(0);
}

const shardIdx = Number(args[0] || 0);
const outDir = path.resolve(args[1] || 'c136-ci-out');
fs.mkdirSync(outDir, { recursive: true });

const job = JSON.parse(fs.readFileSync(JOB_FILE, 'utf8'));
const task = job.tasks[shardIdx];
if (!task) {
  console.log(`No task for shard ${shardIdx}`);
  process.exit(0);
}

const { loadMatch, buildWorld, ReplayStepper, execRecorded } = await import('./sim-v2/lib/match.mjs');
const { assignTeams, clanOf } = await import('./sim-v2/lib/tgame.mjs');
const { compileStrategy, strategyPath } = await import('./sim-v2/lib/sandbox.mjs');
const { makeProfile } = await import('./sim-v2/lib/channel.mjs');
const { Arm } = await import('./sim-v2/lib/arm.mjs');
const { naturalShares } = await import('./sim-v2/lib/metrics.mjs');
const { Crowd, assignArches, parseMix } = await import('./sim-v2/lib/opponents.mjs');
const { chanOptsOf, armOptsOf } = await import('./sim-v2/lib/checkpoint.mjs');
const { hashInt, strHash, cohortOf } = await import('./sim-v2/lib/util.mjs');

const mid = task.room;
const len = task.len || 3210;
const channel = task.channel || 'C1';
const M = loadMatch(mid);
const H = M.H, names = M.names.slice(), squad = M.squad.slice();
const ta = assignTeams(names, M.colors, H, M.vu.numberTeams);
const squadSet = new Set(squad);
const seed = hashInt(1, 2147483646, 1, strHash(mid) | 0, 799);
const others = [];
for (let p = 0; p < H; p++) if (!squadSet.has(p)) others.push(p);
const idle = new Set(others.filter((p) => !M.lastCmd.has(p)));
const leaveAt = new Map();
{
  const w = buildWorld({ ...M, names, ta });
  const st = new ReplayStepper(M, w);
  st.runSpawnPhase();
  st.exec = (c) => {
    if ((c.id === 8 || c.id === 9) && c.player < H && w.alive[c.player] && w.state[c.player] !== 2 && !squadSet.has(c.player)) leaveAt.set(c.player, w.t);
    return execRecorded(w, c);
  };
  while (w.t < len && st.step()) w.tick();
}
const clanMembers = new Map();
for (const p of others) { const c = clanOf(names[p]); if (c) { if (!clanMembers.has(c)) clanMembers.set(c, []); clanMembers.get(c).push(p); } }
const clans = [...clanMembers.entries()].filter(([, m]) => m.length >= 2).map(([tag, m], i) => ({ id: i, tag, members: m }));
const members = assignArches(seed, others, clans, parseMix(), ['O2', 'O6'], idle);
const seatDefs = squad.map((p) => ({ p, slot: M.slotOf.get(p) ?? p % 20 }));

const baseStrat = await compileStrategy(strategyPath(cohortOf(mid)));
const v28File = path.resolve(__dirname, '../archive/v28/v28-team-organism.js');
const v28Strat = await compileStrategy(v28File);

const arms = task.arms || [
  { name: 'baseline (v27)', strat: 'base', params: {} },
  { name: 'v28-full (P1..P8)', strat: 'v28', params: {} },
  { name: 'no-P1 (InflightLedger=0)', strat: 'v28', params: { enableInflightLedger: 0 } },
  { name: 'no-P3 (AiFloorCap=0)', strat: 'v28', params: { enableAiFloorCap: 0 } },
  { name: 'no-P4 (CoordinatedStrike=0)', strat: 'v28', params: { enableCoordinatedStrike: 0 } },
  { name: 'no-P5 (SmartOverCap=0)', strat: 'v28', params: { enableSmartOverCap: 0 } },
  { name: 'no-P6 (QuotaExactDonate=0)', strat: 'v28', params: { enableQuotaExactDonate: 0 } },
  { name: 'no-P7 (SeaPrecision=0)', strat: 'v28', params: { enableSeaPrecision: 0 } },
  { name: 'no-P8 (CollapseGuard=0)', strat: 'v28', params: { enableCollapseGuard: 0 } },
];

const results = [];
for (const a of arms) {
  const strat = a.strat === 'base' ? baseStrat : v28Strat;
  const w = buildWorld({ ...M, names, ta });
  const profile = makeProfile(channel, { seed, seats: squad, Wmax: len + 2000 });
  const crowd = new Crowd(null, { seed, members, startT: 0, squad, rateScale: 1, leaveAt });
  const arm = new Arm({ name: a.name, world: w, strat, params: a.params || {}, seats: seatDefs, profile, chanOpts: chanOptsOf({}), opts: { ...armOptsOf({}), ourLeaves: 'ignore' }, actors: [crowd] });
  crowd.arm = arm;
  const stepper = new ReplayStepper(M, w);
  stepper.runSpawnPhase();
  w.teamCache = null;
  for (let p = 0; p < H; p++) if (w.state[p] === 2) arm.quit.add(p);
  const nat = naturalShares(w);
  const deadAt = new Map();
  arm.takeover();
  for (let t = 0; t < len && !w.over; t++) {
    arm.tickOnce();
    if ((t & 15) === 0) for (const p of squad) if (!w.alive[p] && !deadAt.has(p)) deadAt.set(p, w.t);
  }
  const m = arm.finish(nat, { file: strat.file, sha256: strat.sha256 });
  const dead3000 = [...deadAt.values()].filter((x) => x < 3000).length;
  results.push({
    shard: shardIdx,
    room: mid,
    channel,
    arm: a.name,
    strategy: m.strategy,
    landShare: m.landShare1,
    dupShare: m.dupShare,
    quotaRej: m.quotaRejectRate,
    donOk: m.don.ok,
    netProd: Math.round(m.netProd),
    dead3000,
    errors: m.stratErrors.length,
  });
  console.log(`[shard ${shardIdx}] ${mid} ${a.name}: land=${m.landShare1} dup=${m.dupShare} quotaRej=${m.quotaRejectRate} netProd=${Math.round(m.netProd)}`);
}

fs.writeFileSync(path.join(outDir, `shard-${String(shardIdx).padStart(2, '0')}.json`), JSON.stringify({ shard: shardIdx, room: mid, results }, null, 2));
