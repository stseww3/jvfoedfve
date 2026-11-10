import fs from 'node:fs';

let sc = fs.readFileSync('spawn-coordinator.mjs', 'utf8').replace(/\r\n/g, '\n');

sc = sc.replace(
  'allyMinSep: clamp(Math.round(Math.max(1.22 * rCell, 0.088 * diag)), 84, 142),',
  'allyMinSep: clamp(Math.round(Math.max(1.42 * rCell, 0.105 * diag)), 118, 168),'
);
sc = sc.replace(
  'clusterMax: clamp(Math.round(Math.max(3.60 * rCell, 0.320 * diag)), 260, 480),',
  'clusterMax: clamp(Math.round(Math.max(4.40 * rCell, 0.380 * diag)), 340, 580),'
);

fs.writeFileSync('spawn-coordinator.mjs', sc, 'utf8');
console.log('Updated spawn-coordinator.mjs: allyMinSep=118~168px, clusterMax=340~580px so 10-bot 2D disc claims >= 110k~150k base territory!');
