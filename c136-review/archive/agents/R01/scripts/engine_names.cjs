// engine_names.cjs — 从真引擎（线上客户端原文，经总部 engine_replay.cjs 起录像）取出一局全部 512 个席位的名字。
// 录像头里的 playerNamesData 只有真人席位；内置 AI 席位的名字是引擎装载时自己起的（ah.a3o）。
// B 组策略（v27-team-c110.js）用名字判断“是不是本队的号”（isOurSquadBot：名字在 SQUAD_POOL_SET 里），
// 而名字池里的名字和内置 AI 的名字是同一批国名，所以影子策略要喂全 512 个名字才能和线上一致。
//
// 用法（要套 run-heavy.sh）：node scripts/engine_names.cjs <录像所在局号> [--out 局号]
//   写 out/<局号>/names512.json：{ replay, humans, names: [512 个] }
const fs = require('fs');
const path = require('path');
const { startReplay } = require('/agent/repos/c136-data/src/tools/engine_replay.cjs');

const args = process.argv.slice(2);
const rmid = args[0];
const oi = args.indexOf('--out');
const mid = oi >= 0 ? args[oi + 1] : rmid;
if (!rmid) { console.error('用法：engine_names.cjs <录像所在局号> [--out 局号]'); process.exit(2); }

const { info, api } = startReplay(rmid);
const names = api.names();
const dir = path.join(__dirname, '..', 'out', mid);
fs.mkdirSync(dir, { recursive: true });
fs.writeFileSync(path.join(dir, 'names512.json'), JSON.stringify({ replay: rmid, humans: info.ku, names }));
const ai = names.slice(info.ku);
const uniq = new Set(ai.map((s) => String(s).toLowerCase()));
console.log(`# ${rmid} 真引擎席位名：共 ${names.length} 个，真人 ${info.ku} 个，内置 AI ${ai.length} 个（不同的名字 ${uniq.size} 个）`);
console.log(`# 前 12 个 AI 席位：${ai.slice(0, 12).map((s, i) => `${info.ku + i}=${s}`).join(' | ')}`);
console.log(`# 已写 out/${mid}/names512.json`);
