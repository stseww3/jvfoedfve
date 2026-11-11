#!/usr/bin/env node
// map_export.mjs — 从真引擎宿主里把一局的地图导出成干净模拟器的地图文件（TMAP 格式，和 src/sim/maps/*.bin.gz 一样）。
//
// 为什么要它：strat_probe.mjs（影子策略）跑在干净模拟器上，模拟器按 <地图号>_<种子>.bin.gz 读地图；
// 共享目录 src/sim/maps 里没有某局的种子地图时（例如 B023 的 9_11956），影子策略跑不了。
// 线上引擎自己会按种子生成地图（eng_replay.cjs 的整局重放就是靠它），这里只把生成好的地形读出来，写到自己的目录：
//     out/_maps/<地图号>_<种子>.bin.gz
// strat_probe.mjs 在共享目录找不到地图时读这个目录。
//
// 读数口径（引擎原文的格子访问函数，一格 4 个字节，格子号 = y×宽 + x）：
//     ad.fQ = 无主陆地（码 1） ad.iq = 水（码 2） ad.zr = 地图边（码 3） ad.fe = 山（码 5） ad.h9 = 已有主（只可能是陆地）
//     ad.fH = 水体 / 山体编号（模拟器 map.id，只对水和山有意义）
//
// 用法：
//   bash c136-review/tools/run-heavy.sh node c136-review/agents/R06/scripts/map_export.mjs <matchId>            # 导出
//   bash c136-review/tools/run-heavy.sh node c136-review/agents/R06/scripts/map_export.mjs <matchId> --verify   # 共享目录里已有这张图时：逐格比较，不写文件
import fs from 'node:fs';
import path from 'node:path';
import zlib from 'node:zlib';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import { decodeReplay, mapOf } from '/agent/repos/c136-data/src/sim/tools/c102-replay-lib.mjs';

const require = createRequire(import.meta.url);
const { startReplay } = require('/agent/repos/c136-data/src/tools/engine_replay.cjs');

const HERE = path.dirname(fileURLToPath(import.meta.url));
const OUT = path.resolve(HERE, '../out');
const SHARED = '/agent/repos/c136-data/src/sim/maps';
const mid = process.argv[2];
const verify = process.argv.includes('--verify');
if (!mid) { console.error('用法：map_export.mjs <matchId> [--verify]'); process.exit(2); }

const raw = fs.readFileSync(`/agent/repos/c136-data/bundles/${mid}/replay.txt`, 'utf8');
const { mapIdx, mapSeed } = mapOf(decodeReplay(raw).vu);
const { h } = startReplay(mid);
const m = h.run(`(function () {
  var w = bV.fk, hh = bV.fl, n = w * hh;
  var type = new Uint8Array(n), id = new Uint16Array(n), owned = 0, odd = 0;
  for (var p = 0; p < n; p++) {
    var fD = p * 4, v;
    if (ad.h9(fD)) { v = 1; owned++; }
    else if (ad.fQ(fD)) v = 1;
    else if (ad.iq(fD)) v = 2;
    else if (ad.zr(fD)) v = 3;
    else if (ad.fe(fD)) v = 5;
    else { v = 0; odd++; }
    type[p] = v;
    id[p] = (v === 2 || v === 5) ? ad.fH(fD) : 0;
  }
  return { w: w, h: hh, type: Array.from(type), id: Array.from(id), owned: owned, odd: odd, land: aE.ke };
})()`);
const n = m.w * m.h;
let land = 0;
for (let p = 0; p < n; p++) if (m.type[p] === 1) land++;
console.log(`${mid}: 地图 ${mapIdx}_${mapSeed} ${m.w}×${m.h}，陆地 ${land} 格（引擎自报 ${m.land}），导出时已有主的格子 ${m.owned}，认不出的格子 ${m.odd}`);

const shared = path.join(SHARED, `${mapIdx}_${mapSeed}.bin.gz`);
if (verify) {
  if (!fs.existsSync(shared)) { console.log('共享目录里没有这张图，没法比'); process.exit(1); }
  const buf = zlib.gunzipSync(fs.readFileSync(shared));
  const w = buf.readUInt16LE(4), hh = buf.readUInt16LE(6);
  let dt = 0, di = 0;
  if (w !== m.w || hh !== m.h) { console.log(`尺寸不同：共享 ${w}×${hh}`); process.exit(1); }
  for (let p = 0; p < n; p++) {
    const t = buf[8 + p];
    if (t !== m.type[p]) dt++;
    else if ((t === 2 || t === 5) && buf.readUInt16LE(8 + n + 2 * p) !== m.id[p]) di++;
  }
  console.log(`与共享文件 ${path.basename(shared)} 逐格比较：地形码不同 ${dt} 格，水体/山体编号不同 ${di} 格（共 ${n} 格）`);
  process.exit(dt || di ? 1 : 0);
}
if (m.odd) { console.log('有认不出的格子，不写文件'); process.exit(1); }
const buf = Buffer.alloc(8 + n + 2 * n);
buf.write('TMAP', 0, 'latin1');
buf.writeUInt16LE(m.w, 4);
buf.writeUInt16LE(m.h, 6);
for (let p = 0; p < n; p++) { buf[8 + p] = m.type[p]; buf.writeUInt16LE(m.id[p], 8 + n + 2 * p); }
const dir = path.join(OUT, '_maps');
fs.mkdirSync(dir, { recursive: true });
const file = path.join(dir, `${mapIdx}_${mapSeed}.bin.gz`);
fs.writeFileSync(file, zlib.gzipSync(buf, { level: 9 }));
console.log(`写入 ${file}（${fs.statSync(file).size} 字节）` + (fs.existsSync(shared) ? '；共享目录里也有这张图' : ''));
