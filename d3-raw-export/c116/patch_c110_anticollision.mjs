import fs from 'node:fs';
import { SQUAD_NAME_POOL } from '../c110/name-pool.mjs';

const lowPool = SQUAD_NAME_POOL.map((x) => x.toLowerCase());
let s = fs.readFileSync('tsb-apex-squad.mjs', 'utf8');

s = s.replace(
  /if \(\r?\n\s*lowDisp\.includes\("\[nope\]"\) \|\|\r?\n\s*lowDisp\.includes\("lucas94"\) \|\|\r?\n\s*lowDisp\.includes\("dave_w"\) \|\|\r?\n\s*lowDisp\.includes\("mark07"\) \|\|\r?\n\s*lowDisp\.includes\("kevin_k"\) \|\|\r?\n\s*lowDisp\.includes\("ethan21"\)\r?\n\s*\) \{\r?\n\s*c110NopeInLobby\+\+;\r?\n\s*\}/,
  `if (!lowDisp.includes("[apex]") && (lowDisp.includes("[nope]") || (window.__c110PoolSet || (window.__c110PoolSet = new Set(${JSON.stringify(lowPool)}))).has(lowDisp))) {\n                c110NopeInLobby++;\n              }`
);

s = s.replace('const avoidC110Collision = maxC110NopeInLobby > 0;', 'const avoidC110Collision = maxC110NopeInLobby >= 3;');

fs.writeFileSync('tsb-apex-squad.mjs', s, 'utf8');
console.log('Patched tsb-apex-squad.mjs with c110 name-pool anti-collision');
