#!/usr/bin/env node
// verify-evidence.cjs — 逐条复核 /agent/repos/c136-data/src/engine/engine-evidence.txt 的 78 条定位
// 在本机 live_game_js.js（c136-data 镜像）里是否仍然成立。
//
// 用法（先跑 prep.sh 生成 tmp/pretty/index.json）：
//   NODE_PATH=c136-review/agents/R04/tmp/nodetools/node_modules node verify-evidence.cjs [engine-evidence.txt] [live_game_js.js]
// 输出：每条 [编号] 状态；末行汇总。退出码 0 = 没有 FAIL。
//
// 三级复核：
//   SAME   「定位：名字 @偏移+长度」原样取片段，证据里的每一行文本（去空白）都在片段（去空白）里 → 偏移没变
//   MOVED  偏移处对不上，但按名字（构造函数.成员 / 嵌套函数 / 顶层函数）在索引里重新找到同名函数，
//          证据里的每一行文本都在新位置的函数体里 → 逻辑没变，只是偏移漂移（打印新偏移和漂移量）
//   FAIL   按名字找到了但文本不全，或按名字找不到 → 该条在本机版本上需要人工重核（打印缺失的行）
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const EV = process.argv[2] || '/agent/repos/c136-data/src/engine/engine-evidence.txt';
const LIVE = process.argv[3] || '/agent/repos/c136-data/src/engine/live_game_js.js';
const INDEX = process.env.R04_INDEX || path.join(__dirname, '..', 'tmp', 'pretty', 'index.json');
const src = fs.readFileSync(LIVE, 'utf8');
const sha = crypto.createHash('sha256').update(fs.readFileSync(LIVE)).digest('hex');
const { ctors } = JSON.parse(fs.readFileSync(INDEX, 'utf8'));
const ev = fs.readFileSync(EV, 'utf8').split('\n');

const entries = [];
let cur = null;
for (const line of ev) {
  let m = line.match(/^\[([A-Z]\d+)\]\s*(.*)$/);
  if (m) {
    cur = { id: m[1], title: m[2], loc: null, lines: [] };
    entries.push(cur);
    continue;
  }
  if (!cur) continue;
  m = line.match(/^\s+定位：(\S+) @(\d+)\+(\d+)/);
  if (m) {
    cur.loc = { name: m[1], off: +m[2], len: +m[3] };
    continue;
  }
  m = line.match(/^\s+L(\d+): (.*)$/);
  if (m) cur.lines.push({ n: +m[1], text: m[2] });
}

// 去掉空白和分号再比（压缩代码里 `}` 前的最后一条语句没有分号，排版后的证据行有）
const strip = (s) => s.replace(/[\s;]+/g, '');
const missing = (frag, lines) => {
  const sf = strip(frag);
  return lines.filter((l) => !sf.includes(strip(l.text)));
};

// 名字 → 本机文件里的 [start,end)
function locate(name) {
  const parts = name.split('.');
  if (parts.length === 2) {
    const c = ctors[parts[0]];
    if (c && c.members[parts[1]]) return [c.members[parts[1]].start, c.members[parts[1]].end];
    return null;
  }
  if (ctors[name]) return [ctors[name].start, ctors[name].end];
  const hits = [];
  for (const [cn, c] of Object.entries(ctors)) if (c.members[name]) hits.push([c.members[name].start, c.members[name].end, cn]);
  if (hits.length === 1) return hits[0];
  return null;
}

const ver = src.match(/var dz=(\d+);var e0=(\d+);var e1=(\d+);/);
const date = src.match(/this\.e3="([^"]+)"/);
console.log(`# verify-evidence  本机 live sha256=${sha} chars=${src.length} 版本=${ver ? ver.slice(1).join('.') : '?'} 构建日期串="${date ? date[1] : '?'}"`);
console.log(`# evidence 头部声明：${ev[0]}`);
let same = 0, moved = 0, fail = 0;
const deltas = [];
for (const e of entries) {
  if (!e.loc) {
    console.log(`[${e.id}] FAIL  没有定位`);
    fail++;
    continue;
  }
  const frag = src.substr(e.loc.off, e.loc.len);
  if (missing(frag, e.lines).length === 0) {
    same++;
    console.log(`[${e.id}] SAME  ${e.loc.name} @${e.loc.off}+${e.loc.len}  (${e.lines.length} 行)`);
    continue;
  }
  const loc = locate(e.loc.name);
  if (!loc) {
    fail++;
    console.log(`[${e.id}] FAIL  ${e.loc.name} @${e.loc.off}：偏移处对不上，索引里也找不到同名函数`);
    continue;
  }
  const miss = missing(src.slice(loc[0], loc[1]), e.lines);
  if (miss.length === 0) {
    moved++;
    deltas.push([e.loc.off, loc[0] - e.loc.off]);
    console.log(`[${e.id}] MOVED ${e.loc.name} @${e.loc.off} → @${loc[0]}+${loc[1] - loc[0]}  (漂移 ${loc[0] - e.loc.off >= 0 ? '+' : ''}${loc[0] - e.loc.off}；${e.lines.length} 行文本一致)`);
  } else {
    fail++;
    console.log(`[${e.id}] FAIL  ${e.loc.name} @${e.loc.off} → @${loc[0]}：缺 ${miss.length}/${e.lines.length} 行：${miss.map((l) => `L${l.n}: ${l.text}`).join(' | ').slice(0, 400)}`);
  }
}
deltas.sort((a, b) => a[0] - b[0]);
const steps = [];
for (const [off, d] of deltas) if (!steps.length || steps[steps.length - 1][1] !== d) steps.push([off, d]);
console.log(`# 条目 ${entries.length}：SAME ${same}，MOVED ${moved}，FAIL ${fail}`);
console.log(`# 漂移台阶（旧偏移起 → 漂移量）：${steps.map(([o, d]) => `@${o}:${d >= 0 ? '+' : ''}${d}`).join('  ') || '无'}`);
process.exit(fail ? 1 : 0);
