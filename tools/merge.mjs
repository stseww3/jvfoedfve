// Merges the shards of a paired comparison (see shard.mjs) and prints for
// every arm the win rate, against the first arm the difference with its
// standard error over the seeds and the seeds only one of the two won, how
// often we led the people at 2000 / 3000 ticks, our mean best share, mean
// place among the people and how often we were the biggest living person
// at tick 8000.
// node tools/merge.mjs SPEC DIR
// (SPEC with kind "wg": the war games' summary, tools/c22/wgsum.mjs)
import fs from 'node:fs';
import path from 'node:path';
import { execFileSync } from 'node:child_process';

const [specFile, dir] = process.argv.slice(2);
const spec = JSON.parse(fs.readFileSync(specFile, 'utf8'));
if (spec.kind === 'wg') {
  const sum = new URL('./c22/wgsum.mjs', import.meta.url);
  if (!fs.existsSync(sum) && fs.existsSync('secret/code.bin')) execFileSync(process.execPath, ['tools/crypt.mjs', 'open', 'secret/code.bin', '.'], { stdio: 'inherit' });
  const { readRecs, summary } = await import(sum.href);
  console.log(summary(readRecs([dir]), spec.arms.map(([n]) => n)));
  process.exit(0);
}
const shards = fs.readdirSync(dir).filter((f) => f.endsWith('.json')).map((f) => JSON.parse(fs.readFileSync(path.join(dir, f), 'utf8')));
const arms = spec.arms.map((params, i) => ({ params, res: shards.flatMap((s) => s.arms[i].res).sort((a, b) => a.seed - b.seed) }));
const n = arms[0].res.length;
const pct = (x) => (100 * x).toFixed(1);
const mean = (a) => a.reduce((s, v) => s + v, 0) / Math.max(1, a.length);
console.log(`${spec.policy} on ${spec.suite}, ${n} seeds (${spec.seeds}), ${shards.length} shards, slowest ${Math.max(...shards.map((s) => s.seconds))} s`);
for (const a of arms) {
  if (a.res.length !== n) throw new Error('shards disagree on the seeds');
  const w = a.res.map((r) => r.win);
  let line = `${pct(mean(w))}%`;
  if (a !== arms[0]) {
    const d = w.map((v, i) => v - arms[0].res[i].win);
    const m = mean(d);
    const sd = Math.sqrt(d.reduce((s, v) => s + (v - m) ** 2, 0) / (n - 1));
    line += ` ${m >= 0 ? '+' : ''}${pct(m)} ± ${pct(sd / Math.sqrt(n))} (+${d.filter((v) => v > 0).length} -${d.filter((v) => v < 0).length})`;
  }
  const lead = (t) => pct(mean(a.res.map((r) => (r.at?.[t]?.rank === 1 ? 1 : 0))));
  line += ` lead@2000 ${lead(2000)}% lead@3000 ${lead(3000)}% maxShare ${pct(mean(a.res.map((r) => r.maxShare)))}%`;
  if (a.res.some((r) => r.place)) line += ` place ${mean(a.res.map((r) => r.place)).toFixed(2)} top@8000 ${pct(mean(a.res.map((r) => r.top?.[8000] ?? 0)))}%`;
  console.log(`${line} ${JSON.stringify(a.params)}`);
}
// per-seed outcomes for offline analysis: [seed, win, deathT, maxShare, place, top@8000]
console.log('--- per seed');
for (const a of arms) console.log(JSON.stringify(a.res.map((r) => [r.seed, r.win, r.deathT, r.maxShare, r.place, r.top?.[8000]])));
