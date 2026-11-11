#!/usr/bin/env node
// jsfn.cjs — 从压缩过的游戏客户端代码里取出一个函数（或一段偏移区间），排版后打印。
//
// 用法（先跑 prep.sh；NODE_PATH=c136-review/agents/R04/tmp/nodetools/node_modules）：
//   NODE_PATH=... node jsfn.cjs a5M.rD                                            # 构造函数.成员
//   NODE_PATH=... node jsfn.cjs bD.gv.rD                                          # 全局访问路径（自动解析到构造函数）
//   NODE_PATH=... node jsfn.cjs @123456+800                                       # 原文件字符串下标 + 长度（原样打印）
//   NODE_PATH=... node jsfn.cjs --who rD                                          # 哪些构造函数有叫 rD 的成员
//   NODE_PATH=... node jsfn.cjs --path a5M                                        # 构造函数 a5M 的全局访问路径
// 环境变量：R04_LIVE（原文件，默认 /agent/repos/c136-data/src/engine/live_game_js.js）、R04_INDEX（默认 ../tmp/pretty/index.json）
const fs = require('fs');
const prettier = require('prettier');

const path = require('path');
const LIVE = process.env.R04_LIVE || '/agent/repos/c136-data/src/engine/live_game_js.js';
const INDEX = process.env.R04_INDEX || path.join(__dirname, '..', 'tmp', 'pretty', 'index.json');
const src = fs.readFileSync(LIVE, 'utf8');
const index = JSON.parse(fs.readFileSync(INDEX, 'utf8'));
const { ctors, globals } = index;

// 构造函数 -> 全局访问路径（宽度优先，最多 3 层）
function pathsOf(ctor) {
  const out = [];
  const queue = Object.entries(globals).flatMap(([g, c]) => c.split('|').map((cc) => ({ path: g, ctor: cc })));
  const seen = new Set();
  while (queue.length) {
    const { path, ctor: c } = queue.shift();
    const key = `${path}:${c}`;
    if (seen.has(key)) continue;
    seen.add(key);
    if (c === ctor) out.push(path);
    if (path.split('.').length >= 3 || !ctors[c]) continue;
    for (const [prop, cc] of Object.entries(ctors[c].news)) queue.push({ path: `${path}.${prop}`, ctor: cc });
  }
  return out;
}

function resolve(spec) {
  const parts = spec.split('.');
  if (parts.length === 2 && ctors[parts[0]] && ctors[parts[0]].members[parts[1]]) return { ctor: parts[0], member: parts[1] };
  // 全局路径：g.a.b.member
  let c = globals[parts[0]];
  if (!c) return null;
  c = c.split('|')[0];
  for (let i = 1; i < parts.length - 1; i++) {
    c = ctors[c] && ctors[c].news[parts[i]];
    if (!c) return null;
  }
  const member = parts[parts.length - 1];
  if (ctors[c] && ctors[c].members[member]) return { ctor: c, member };
  return null;
}

async function main() {
  const args = process.argv.slice(2);
  if (args.length === 0) {
    console.error('用法见文件开头');
    process.exit(2);
  }
  if (args[0] === '--who') {
    for (const [c, info] of Object.entries(ctors)) if (info.members[args[1]]) console.log(`${c}.${args[1]} @${info.members[args[1]].start} (${info.members[args[1]].kind})  paths: ${pathsOf(c).join(', ') || '-'}`);
    return;
  }
  if (args[0] === '--path') {
    console.log(pathsOf(args[1]).join('\n') || '(没有找到全局实例)');
    return;
  }
  for (const spec of args) {
    const m = spec.match(/^@(\d+)\+(\d+)$/);
    if (m) {
      console.log(`// @${m[1]}+${m[2]} (sha256 ${index.sha256.slice(0, 12)})`);
      console.log(src.substr(+m[1], +m[2]));
      continue;
    }
    const r = resolve(spec);
    if (!r) {
      console.log(`// ${spec}: 找不到`);
      continue;
    }
    const { start, end, kind } = ctors[r.ctor].members[r.member];
    const code = src.slice(start, end);
    let out;
    try {
      const wrapped = kind === 'nfn' ? code : `_ = { ${r.member}: ${code.replace(/^this\.[A-Za-z0-9_$]+\s*=\s*/, '')} }`;
      out = await prettier.format(wrapped, { parser: 'babel', printWidth: 140 });
    } catch (e) {
      out = code;
    }
    console.log(`// ${r.ctor}.${r.member} @${start}..${end} (${end - start} bytes; sha256 ${index.sha256.slice(0, 12)}; paths: ${pathsOf(r.ctor).join(', ') || '-'})`);
    console.log(out);
  }
}
main();
