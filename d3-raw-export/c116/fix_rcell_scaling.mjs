import fs from 'node:fs';

let sc = fs.readFileSync('spawn-coordinator.mjs', 'utf8').replace(/\r\n/g, '\n');

sc = sc.replace(
  /allyMinSep:\s*clamp\([^;]+?\),/,
  'allyMinSep: clamp(Math.round(1.48 * rCell), 72, 118),'
);
sc = sc.replace(
  /clusterMax:\s*clamp\([^;]+?\),/,
  'clusterMax: clamp(Math.round(3.35 * rCell), 190, 320),'
);
sc = sc.replace(
  'if (distToOurCluster(x, y) > scales.allyMinSep * (2.6 - 0.8 * relax)) continue;',
  'if (distToOurCluster(x, y) > scales.allyMinSep * (2.1 - 0.5 * relax)) continue;'
);

fs.writeFileSync('spawn-coordinator.mjs', sc, 'utf8');
console.log('Updated spawn-coordinator.mjs: allyMinSep=clamp(1.48*rCell, 72, 118), clusterMax=clamp(3.35*rCell, 190, 320)!');
