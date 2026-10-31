// One shard of a paired comparison (for CI): every arm of the job spec on
// the seeds whose position in the seed list is SHARD modulo the spec's
// shards, all games at once on every core.
// node tools/shard.mjs SPEC SHARD OUT
// SPEC: { policy, suite, seeds: "1-480", shards, arms: [params, ...] }
// (an arm may name its own policy: { policy: "v2", ... })
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { Pool, parseSeeds } from '../strategy/bench.js';
import { scenarioOpts } from '../strategy/suite.js';

const [specFile, shardArg, out] = process.argv.slice(2);
const spec = JSON.parse(fs.readFileSync(specFile, 'utf8'));
const shard = Number(shardArg);
const seeds = parseSeeds(spec.seeds).filter((_, i) => i % spec.shards === shard);
const pool = new Pool(os.cpus().length);
const keep = (r) => ({
  seed: r.seed, map: r.map, humans: r.humans, win: r.win ? 1 : 0, deathT: r.deathT, t: r.t,
  maxShare: +r.maxShare.toFixed(4), at: r.at, bestRank: r.bestRank, top3T: r.top3T, duelT: r.duelT,
});
const t0 = performance.now();
// the output carries no parameters (it may be public)
const arms = await Promise.all(spec.arms.map(async (params) => ({
  res: (await Promise.all(seeds.map((seed) => pool.run({ seed, policy: spec.policy, params, ...scenarioOpts(spec.suite, seed) })))).map(keep),
})));
pool.close();
fs.mkdirSync(path.dirname(out), { recursive: true });
fs.writeFileSync(out, JSON.stringify({ shard, cpus: os.cpus().length, seconds: Math.round((performance.now() - t0) / 1000), arms }));
console.log(`shard ${shard}: ${seeds.length} seeds x ${arms.length} arms in ${((performance.now() - t0) / 1000).toFixed(0)} s on ${os.cpus().length} cpus`);
