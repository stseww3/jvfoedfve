import test from 'node:test';
import assert from 'node:assert/strict';
import { TeamSpawnCoordinator, T_LAND, T_WATER } from '../squad/spawn-coordinator.mjs';

function makeSyntheticMap(W, H) {
  const mapType = new Uint8Array(W * H).fill(T_WATER);
  let land = 0;
  // Create a main continent and an island
  for (let y = 12; y < H - 12; y++) {
    for (let x = 12; x < W - 12; x++) {
      // Leave a river/bay in the middle-right
      if (x > W * 0.68 && x < W * 0.74 && y > H * 0.25 && y < H * 0.75) continue;
      mapType[y * W + x] = T_LAND;
      land++;
    }
  }
  return { W, H, land, mapType };
}

test('TeamSpawnCoordinator assigns 5 and 10 mutually separated bots respecting Boss exclusion zone', () => {
  const { W, H, land, mapType } = makeSyntheticMap(600, 500);
  const coord = new TeamSpawnCoordinator();
  assert.equal(coord.setMap({ matchKey: 'synth_600x500', W, H, land, mapType }), true);

  const boss = { id: 0, name: '[NPL] npl', team: 1, terr: 12, x: 220, y: 220 };
  const enemies = [
    { id: 1, name: 'EnemyA', team: 2, terr: 12, x: 180, y: 80 },
    { id: 2, name: 'EnemyB', team: 2, terr: 12, x: 380, y: 120 },
    { id: 3, name: 'EnemyC', team: 3, terr: 12, x: 120, y: 400 },
    { id: 4, name: 'EnemyD', team: 3, terr: 12, x: 500, y: 380 },
  ];
  const squad5 = [0, 1, 2, 3, 4].map((i) => ({
    slot: i + 5,
    port: 9305 + i,
    name: `[NPL] Bot${i}`,
    meId: 10 + i,
  }));

  const plan5 = coord.solve({
    squadBots: squad5,
    humans: [boss, ...enemies],
    myTeam: 1,
  });

  assert.equal(plan5.ok, true);
  assert.equal(plan5.list.length, 5);
  assert.ok(plan5.minPairwiseDist >= 90, `Expected minPairwiseDist >= 90, got ${plan5.minPairwiseDist}`);

  const flankGuards = plan5.list.filter((b) => b.role === 'FLANK_GUARD');
  const ecoBanks = plan5.list.filter((b) => b.role === 'ECO_BANK');
  assert.equal(flankGuards.length, 2, 'Expected 2 FLANK_GUARD bots when Boss is present in 5-bot squad');
  assert.equal(ecoBanks.length, 3, 'Expected 3 ECO_BANK bots in 5-bot squad');

  for (const bot of plan5.list) {
    const dBoss = Math.hypot(bot.x - boss.x, bot.y - boss.y);
    assert.ok(
      dBoss >= plan5.scales.bossExcl * 0.72,
      `Bot ${bot.name} spawned too close to Boss: ${dBoss} < ${plan5.scales.bossExcl}`
    );
    assert.ok(bot.voronoiPixels >= 1000, `Bot ${bot.name} Voronoi basin too small: ${bot.voronoiPixels}`);
  }

  // Test stability under Bitmask DP minimum-displacement matching on subsequent frame
  const squad5NextFrame = plan5.list.map((b) => ({
    slot: b.slot,
    port: b.port,
    name: b.name,
    meId: b.meId,
    curX: b.x,
    curY: b.y,
  }));
  const plan5Repeat = coord.solve({
    squadBots: squad5NextFrame,
    humans: [boss, ...enemies],
    myTeam: 1,
  });
  for (let i = 0; i < 5; i++) {
    assert.equal(plan5Repeat.list[i].x, plan5.list[i].x);
    assert.equal(plan5Repeat.list[i].y, plan5.list[i].y);
  }
});
