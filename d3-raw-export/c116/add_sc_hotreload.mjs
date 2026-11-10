import fs from 'node:fs';

let tsb = fs.readFileSync('tsb-apex-squad.mjs', 'utf8').replace(/\r\n/g, '\n');

const oldLine = `const spawnCoordinator = new TeamSpawnCoordinator({ port: 8299 });
spawnCoordinator.startHttpServer();`;

const newLine = `let spawnCoordinator = new TeamSpawnCoordinator({ port: 8299 });
spawnCoordinator.startHttpServer();
let lastSpawnCoordSize = fs.existsSync(path.join(__dirname, 'spawn-coordinator.mjs')) ? fs.statSync(path.join(__dirname, 'spawn-coordinator.mjs')).size : 0;`;

if (tsb.includes(oldLine)) {
  tsb = tsb.replace(oldLine, newLine);
  fs.writeFileSync('tsb-apex-squad.mjs', tsb, 'utf8');
  console.log('Prepared tsb-apex-squad.mjs for hot-reloadable spawnCoordinator!');
}
