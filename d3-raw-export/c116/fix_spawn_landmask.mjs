import fs from 'node:fs';

let sc = fs.readFileSync('spawn-coordinator.mjs', 'utf8').replace(/\r\n/g, '\n');

const oldSetMap = `      for (let i = 0; i < N; i++) {
        const t = mapType[i];
        if (t === T_LAND || t >= 16) {
          this.landMask[i] = 1;
          landCount++;
        } else if (t === T_WATER) {
          this.waterMask[i] = 1;
        }
      }`;

const newSetMap = `      let zeroCount = 0, oneCount = 0;
      for (let i = 0; i < N; i += 17) {
        if (mapType[i] === 0) zeroCount++;
        else if (mapType[i] === 1) oneCount++;
      }
      const isLivePx = zeroCount > oneCount;
      for (let i = 0; i < N; i++) {
        const t = mapType[i];
        if (isLivePx ? (t === 0 || t >= 16) : (t === T_LAND || t >= 16)) {
          this.landMask[i] = 1;
          landCount++;
        } else if (isLivePx ? (t === 1) : (t === T_WATER)) {
          this.waterMask[i] = 1;
        }
      }`;

if (sc.includes(oldSetMap)) {
  sc = sc.replace(oldSetMap, newSetMap);
  fs.writeFileSync('spawn-coordinator.mjs', sc, 'utf8');
  console.log('FIXED T_LAND=0 vs T_WATER=1 inversion in spawn-coordinator.mjs!');
} else {
  console.log('Already patched or not found!');
}
