// Merges the shards of a paired comparison (see shard.mjs) and prints for
// every arm the win rate, against the first arm the difference with its
// standard error over the seeds and the seeds only one of the two won, how
// often we led the people at 2000 / 3000 ticks and our mean best share.
// node tools/merge.mjs SPEC DIR
import fs from 'node:fs';
import path from 'node:path';

const [specFile, dir] = process.argv.slice(2);
const spec = JSON.parse(fs.readFileSync(specFile, 'utf8'));
const shards = fs.readdirSync(dir).filter((f) => f.endsWith('.json')).map((f) => JSON.parse(fs.readFileSync(path.join(dir, f), 'utf8')));
if (shards.some((s) => 'wrapped' in s)) {
  fs.mkdirSync('results', { recursive: true });
  fs.writeFileSync('results/c22-key.json', JSON.stringify({ wrapped: shards.find((s) => s.wrapped)?.wrapped ?? null }));
  console.log('key hand-over written to results/c22-key.json');
  process.exit(0);
}
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
  console.log(`${line} ${JSON.stringify(a.params)}`);
}
