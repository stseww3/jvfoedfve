import fs from 'node:fs';

let tsb = fs.readFileSync('tsb-apex-squad.mjs', 'utf8').replace(/\r\n/g, '\n');

const oldHot = `  // Hot-import updated strategy file immediately even while bots are in-game!`;
const newHot = `  // Hot-reload spawn-coordinator.mjs whenever it is updated on disk!
  try {
    const scPath = path.join(__dirname, 'spawn-coordinator.mjs');
    const curScSize = fs.existsSync(scPath) ? fs.statSync(scPath).size : 0;
    if (curScSize > 0 && typeof lastSpawnCoordSize === 'number' && curScSize !== lastSpawnCoordSize) {
      lastSpawnCoordSize = curScSize;
      import('./spawn-coordinator.mjs?t=' + Date.now()).then((mod) => {
        if (mod && mod.TeamSpawnCoordinator) {
          spawnCoordinator = new mod.TeamSpawnCoordinator({ port: 0 });
          console.log(\`[HOT-IMPORT] Reloaded TeamSpawnCoordinator (\${curScSize} bytes) live!\`);
        }
      }).catch(() => {});
    }
  } catch {}

  // Hot-import updated strategy file immediately even while bots are in-game!`;

if (tsb.includes(oldHot) && !tsb.includes('Reloaded TeamSpawnCoordinator')) {
  tsb = tsb.replace(oldHot, newHot);
  fs.writeFileSync('tsb-apex-squad.mjs', tsb, 'utf8');
  console.log('Added live hot-reload of spawn-coordinator.mjs to tsb-apex-squad.mjs!');
}
