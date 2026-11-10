import fs from 'node:fs';

let sc = fs.readFileSync('spawn-coordinator.mjs', 'utf8').replace(/\r\n/g, '\n');

sc = sc.replace(
  'allyMinSep: clamp(Math.round(1.48 * rCell), 72, 118), 118, 168),',
  'allyMinSep: clamp(Math.round(1.48 * rCell), 72, 118),'
);
sc = sc.replace(
  'clusterMax: clamp(Math.round(3.35 * rCell), 190, 320), 340, 580),',
  'clusterMax: clamp(Math.round(3.35 * rCell), 190, 320),'
);

fs.writeFileSync('spawn-coordinator.mjs', sc, 'utf8');
console.log('Fixed spawn-coordinator.mjs lines 837 and 839!');
