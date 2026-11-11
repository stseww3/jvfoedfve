// map_from_engine.cjs — 从真引擎（线上客户端原文，经总部 engine_replay.cjs 起录像）取出一局的地图，
// 写成 sim 镜像 loadMap 读的 TMAP 格式。sim 镜像的 maps/ 里没有这张图的局（A005：5_9294）靠它才能整局重演。
//
// 用法（都要套 run-heavy.sh）：
//   node scripts/map_from_engine.cjs <局号> --verify <图号_种子>   这局的图 sim 镜像里有：逐像素对比，验证取法
//   node scripts/map_from_engine.cjs <局号>                        写 out/<局号>/map_<图号>_<种子>.bin
//
// 取法（线上原文）：像素状态在全局数组 aFA 里，每像素 4 字节 [a, b, 地形, 归属]。
//   归属字节为 0 = 无主：地形 1 陆地 / 2 水 / 3 边界 / 5 山；水体编号 = (a>>1<<8)+b（原文 this.fH）。
//   录像装载后内置 AI 已经落位（每个 12 格），这些像素归属字节不为 0，按陆地记（--verify 会数它们在镜像里是不是都是陆地）。
const fs = require('fs');
const path = require('path');
const zlib = require('zlib');
const { startReplay } = require('/agent/repos/c136-data/src/tools/engine_replay.cjs');

const args = process.argv.slice(2);
const mid = args[0];
const vi = args.indexOf('--verify');
const verify = vi >= 0 ? args[vi + 1] : null;
if (!mid) { console.error('用法：map_from_engine.cjs <局号> [--verify 图号_种子]'); process.exit(2); }

const { h, info } = startReplay(mid);
const a = h.run('aFA');
const seed = h.run('bV.mapSeed');
const w = info.w, hh = info.h, n = w * hh;
if (!a || a.length !== 4 * n) throw new Error(`aFA 长度不对：${a && a.length}，应为 ${4 * n}`);

const type = new Uint8Array(n), id = new Uint16Array(n);
let owned = 0, land = 0;
const cnt = {};
for (let p = 0; p < n; p++) {
  const T = a[4 * p + 2], O = a[4 * p + 3];
  if (O !== 0) { type[p] = 1; owned++; } else {
    type[p] = T;
    if (T === 2 || T === 5) id[p] = ((a[4 * p] >> 1) << 8) + a[4 * p + 1];
  }
  if (type[p] === 1) land++;
  cnt[type[p]] = (cnt[type[p]] || 0) + 1;
}
console.log(`# ${mid} 真引擎地图：图 ${info.map}，种子 ${seed}，${w}x${hh}；地形像素数 ${JSON.stringify(cnt)}；陆地 ${land}（引擎自报 ${info.ke}）；装载时已有主的像素 ${owned}（按陆地记）`);
const bodies = new Set(); for (let p = 0; p < n; p++) if (id[p]) bodies.add(id[p]);
console.log(`# 水体/山体编号 ${bodies.size} 个`);

if (verify) {
  const buf = zlib.gunzipSync(fs.readFileSync(`/agent/repos/c136-data/src/sim/maps/${verify}.bin.gz`));
  const w2 = buf.readUInt16LE(4), h2 = buf.readUInt16LE(6);
  if (w2 !== w || h2 !== hh) throw new Error(`尺寸不同：镜像 ${w2}x${h2}`);
  let tBad = 0, iBad = 0, ownedNotLand = 0;
  for (let p = 0; p < n; p++) {
    const t2 = buf[8 + p], i2 = buf.readUInt16LE(8 + n + 2 * p);
    if (t2 !== type[p]) tBad++;
    if (i2 !== id[p]) iBad++;
    if (a[4 * p + 3] !== 0 && t2 !== 1) ownedNotLand++;
  }
  console.log(`# 与镜像 ${verify} 逐像素对比（${n} 像素）：地形不同 ${tBad}，水体编号不同 ${iBad}；已有主的像素在镜像里不是陆地的 ${ownedNotLand}`);
} else {
  const out = Buffer.alloc(8 + n + 2 * n);
  out.write('TMAP', 0, 'latin1');
  out.writeUInt16LE(w, 4); out.writeUInt16LE(hh, 6);
  Buffer.from(type.buffer).copy(out, 8);
  for (let p = 0; p < n; p++) out.writeUInt16LE(id[p], 8 + n + 2 * p);
  const dir = path.join(__dirname, '..', 'out', mid);
  fs.mkdirSync(dir, { recursive: true });
  const f = path.join(dir, `map_${info.map}_${seed}.bin`);
  fs.writeFileSync(f, out);
  console.log(`# 已写 ${path.relative(path.join(__dirname, '..'), f)}（${out.length} 字节）`);
}
