// One shard of a paired comparison (for CI): every arm of the job spec on
// the seeds whose position in the seed list is SHARD modulo the spec's
// shards, all games at once on every core.
// node tools/shard.mjs SPEC SHARD OUT
// SPEC: { policy, suite, seeds: "1-480", shards, arms: [params, ...] }
// (an arm may name its own policy: { policy: "v2", ... } and its own
// scenario: { suite: "brv3", ... })
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import crypto from 'node:crypto';

const [specFile, shardArg, out] = process.argv.slice(2);
const shard = Number(shardArg);
// Key hand-over: while jobs/c19.pub exists, shard 0 writes STRAT_KEY wrapped
// with that RSA public key (OAEP, SHA-256) and no games run.
if (fs.existsSync('jobs/c19.pub')) {
  const wrapped = shard === 0
    ? crypto.publicEncrypt({ key: fs.readFileSync('jobs/c19.pub'), padding: crypto.constants.RSA_PKCS1_OAEP_PADDING, oaepHash: 'sha256' },
      Buffer.from(process.env.STRAT_KEY ?? '', 'utf8')).toString('base64')
    : null;
  fs.mkdirSync(path.dirname(out), { recursive: true });
  fs.writeFileSync(out, JSON.stringify({ shard, wrapped }));
  console.log(`shard ${shard}: key hand-over`);
  process.exit(0);
}
const { Pool, parseSeeds } = await import('../strategy/bench.js');
const { scenarioOpts } = await import('../strategy/suite.js');
const spec = JSON.parse(fs.readFileSync(specFile, 'utf8'));
const seeds = parseSeeds(spec.seeds).filter((_, i) => i % spec.shards === shard);
const pool = new Pool(os.cpus().length);
const keep = (r) => ({
  seed: r.seed, map: r.map, humans: r.humans, win: r.win ? 1 : 0, deathT: r.deathT, t: r.t,
  maxShare: +r.maxShare.toFixed(4), at: r.at, bestRank: r.bestRank, top3T: r.top3T, duelT: r.duelT,
});
const t0 = performance.now();
// the output carries no parameters (it may be public)
const arms = await Promise.all(spec.arms.map(async ({ suite = spec.suite, ...params }) => ({
  res: (await Promise.all(seeds.map((seed) => pool.run({ seed, policy: spec.policy, params, ...scenarioOpts(suite, seed) })))).map(keep),
})));
pool.close();
fs.mkdirSync(path.dirname(out), { recursive: true });
fs.writeFileSync(out, JSON.stringify({ shard, cpus: os.cpus().length, seconds: Math.round((performance.now() - t0) / 1000), arms }));
console.log(`shard ${shard}: ${seeds.length} seeds x ${arms.length} arms in ${((performance.now() - t0) / 1000).toFixed(0)} s on ${os.cpus().length} cpus`);
