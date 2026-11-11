// lib.mjs — R08 公共解析库。
// 原始数据（数据 A）：jvfoedfve 分支 cursor/c116-winrate-liaison-b3bc 的 c116-winrate/data/
//   取法：bash c136-review/tools/bus-get.sh cursor/c116-winrate-liaison-b3bc c116-winrate/data /tmp/c136-r08/raw
// 所有行号都是 G01-G09-squad.log 的原始行号（1 起）。
import fs from 'node:fs';
import path from 'node:path';

export const RAW_DIR = process.env.R08_RAW || '/tmp/c136-r08/raw';
export const OUT_DIR = process.env.R08_OUT ||
  path.resolve(path.dirname(new URL(import.meta.url).pathname), '..', 'out');

// 与连接、验证、身份有关的行不在项目范围内（LIAISON §9、§10），切片时一律丢弃。
const OUT_OF_SCOPE = /socket close index|Connection to Server|[Tt]urnstile|sendTokenToLobby|SELF-CHECK|Attaching on port|devtools|Donor Chrome/;

export function loadRawLog() {
  const txt = fs.readFileSync(path.join(RAW_DIR, 'G01-G09-squad.log'), 'utf8');
  return txt.split('\n');
}

export function loadRawResults() {
  return fs.readFileSync(path.join(RAW_DIR, 'G01-G09-results.jsonl'), 'utf8')
    .split('\n').filter(Boolean).map((l) => JSON.parse(l));
}

export function inScope(line) { return !OUT_OF_SCOPE.test(line); }

// 把日志按 [HL-GAME-INIT] 的 (mode,map,mapSeed) 切成局。
// 一局 = 该 mapSeed 的第一条 INIT 行（向前回溯到上一条 [SQUAD-SYNC] Entering 行）到下一局第一条 INIT 之前的最后一条 [RESULT 行。
// 命名：日志里第 1 个 mapSeed 是 G01 之前的一局（00:20~00:24 CST，策略报错 rnd is not a function），记作 X00；
//       之后依次是 G01..G09，与 c116-winrate/DISPATCH.md 的结算时刻逐一对应（由 slice.mjs 打印核对表）。
export function indexGames(lines) {
  const games = [];
  let cur = null;
  const initRe = /^\[\[Nope\] ([^\]]+)\] \[HL-GAME-INIT\] mode=(\d+) map=(\d+) mapSeed=(\d+) players=(\d+) me=(\d+)/;
  for (let i = 0; i < lines.length; i++) {
    const m = initRe.exec(lines[i]);
    if (m) {
      const key = `${m[2]}/${m[3]}/${m[4]}`;
      if (!cur || cur.key !== key) {
        cur = { key, mode: +m[2], map: +m[3], mapSeed: +m[4], players: +m[5], firstInit: i + 1, bots: {}, lastResult: 0 };
        games.push(cur);
      }
      cur.bots[m[1]] = { me: +m[6], initLine: i + 1 };
    } else if (cur && lines[i].startsWith('[RESULT ')) {
      cur.lastResult = i + 1;
    }
  }
  // 起点回溯到上一条 SQUAD-SYNC Entering（进房行，含房间人数），终点 = 最后一条 RESULT
  for (let k = 0; k < games.length; k++) {
    const g = games[k];
    const lo = k === 0 ? 1 : games[k - 1].lastResult + 1;
    let start = g.firstInit;
    for (let i = g.firstInit - 1; i >= lo; i--) {
      if (lines[i - 1].startsWith('[SQUAD-SYNC] Entering')) start = i;
    }
    g.start = start;
    g.end = g.lastResult;
    g.label = k === 0 ? 'X00' : 'G' + String(k).padStart(2, '0');
  }
  return games;
}

export function botOf(line) {
  const m = /^\[\[Nope\] ([^\]]+)\] /.exec(line);
  return m ? m[1] : null;
}

export function kv(str) {
  // 解析 "a=1 b=2.5 c=xyz" 这类片段（值到下一个空格为止）
  const o = {};
  for (const m of str.matchAll(/([A-Za-z][A-Za-z0-9]*)=([^\s]+)/g)) {
    const v = m[2];
    o[m[1]] = /^-?\d+(\.\d+)?$/.test(v) ? +v : v;
  }
  return o;
}

export function ensureDir(d) { fs.mkdirSync(d, { recursive: true }); }

export function writeCsv(file, rows, cols) {
  const esc = (v) => {
    if (v === undefined || v === null) return '';
    const s = String(v);
    return /[",\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s;
  };
  const out = [cols.join(',')];
  for (const r of rows) out.push(cols.map((c) => esc(r[c])).join(','));
  fs.writeFileSync(file, out.join('\n') + '\n');
}

export function readCsv(file) {
  const txt = fs.readFileSync(file, 'utf8').trim().split('\n');
  const cols = txt[0].split(',');
  return txt.slice(1).map((l) => {
    const parts = [];
    let cur = '', q = false;
    for (let i = 0; i < l.length; i++) {
      const ch = l[i];
      if (q) { if (ch === '"') { if (l[i + 1] === '"') { cur += '"'; i++; } else q = false; } else cur += ch; }
      else if (ch === '"') q = true;
      else if (ch === ',') { parts.push(cur); cur = ''; }
      else cur += ch;
    }
    parts.push(cur);
    const o = {};
    cols.forEach((c, i) => { const v = parts[i]; o[c] = v !== '' && /^-?\d+(\.\d+)?$/.test(v) ? +v : v; });
    return o;
  });
}
