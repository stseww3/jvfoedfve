// lib.mjs — R09 公共解析库：把数据 A 的小队日志和结算记录切成局、解析成结构化事件。
//
// 原始数据的取法（只读，放本地临时目录，不进分支）：
//   bash c136-review/tools/bus-get.sh cursor/c116-winrate-liaison-b3bc c116-winrate/data /tmp/c136-r09/raw
// 来源提交：jvfoedfve cursor/c116-winrate-liaison-b3bc @ d9a56dcde66f
//
// 范围说明：日志里与连接、验证有关的行（socket / Connection / Turnstile / token / SELF-CHECK 等）
// 不在本项目范围内。本库不解析它们的内容，只在 countConnLines() 里按号按局数行数，
// 用作「掉线」污染标记，不做任何进一步分析。

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

export const RAW = process.env.C136_RAW || '/tmp/c136-r09/raw';
export const LOG_FILE = path.join(RAW, 'G01-G09-squad.log');
export const RESULTS_FILE = path.join(RAW, 'G01-G09-results.jsonl');
export const HERE = path.dirname(fileURLToPath(import.meta.url));
export const OUT_ROOT = path.resolve(HERE, '..', 'out');

// 日志里的局按 HL-GAME-INIT 的 mapSeed 分段。第 0 段（mapSeed=7652，结算 16:20~16:24Z）
// 在 DISPATCH 明细表的 G01 之前，记为 G00；第 1~9 段依次是 G01~G09。
export const SEG_LABELS = ['G00', 'G01', 'G02', 'G03', 'G04', 'G05', 'G06', 'G07', 'G08', 'G09'];

const OUT_OF_SCOPE = /socket close|Connection to Server|Turnstile|turnstile|sendTokenToLobby|SELF-CHECK|Attaching on port|Donor Chrome/;

export function isOutOfScope(line) {
  return OUT_OF_SCOPE.test(line);
}

export function loadLogLines() {
  return fs.readFileSync(LOG_FILE, 'utf8').split('\n').map((l) => l.replace(/\r$/, ''));
}

export function loadResults() {
  return fs
    .readFileSync(RESULTS_FILE, 'utf8')
    .split('\n')
    .filter(Boolean)
    .map((l, i) => ({ ...JSON.parse(l), _resultsLine: i + 1 }));
}

const RE_INIT = /^\[(\[Nope\] [^\]]+)\] \[HL-GAME-INIT\] mode=(\d+) map=(\d+) mapSeed=(\d+) players=(\d+) me=(\d+)/;
const RE_RESULT = /^\[RESULT (\[Nope\] [^\]]+)\] result=(\w+) event=(\w+) place=(\d+) peak=(\d+) team=(.*)$/;

// 返回每段 { idx, label, seed, map, mode, players, firstInit, lastResult, start, end }（行号从 1 起，闭区间）。
// 一局的范围 = 上一局最后一条 RESULT 的下一行 … 本局最后一条 RESULT。
export function segments(lines) {
  const segs = [];
  for (let i = 0; i < lines.length; i++) {
    const m = lines[i].match(RE_INIT);
    if (!m) continue;
    const seed = m[4];
    if (!segs.length || segs[segs.length - 1].seed !== seed) {
      segs.push({ idx: segs.length, seed, map: +m[3], mode: +m[2], players: +m[5], firstInit: i + 1, lastResult: -1 });
    }
  }
  for (let s = 0; s < segs.length; s++) {
    const from = segs[s].firstInit;
    const to = s + 1 < segs.length ? segs[s + 1].firstInit - 1 : lines.length;
    for (let i = from; i <= to; i++) {
      if (RE_RESULT.test(lines[i - 1])) segs[s].lastResult = i;
    }
  }
  for (let s = 0; s < segs.length; s++) {
    segs[s].label = SEG_LABELS[s] || `G${String(s).padStart(2, '0')}`;
    segs[s].start = s === 0 ? 1 : segs[s - 1].lastResult + 1;
    segs[s].end = segs[s].lastResult;
  }
  return segs;
}

export function segmentByLabel(lines, label) {
  const s = segments(lines).find((x) => x.label === label);
  if (!s) throw new Error(`no segment ${label}`);
  return s;
}

const BOT = String.raw`\[(\[Nope\] [^\]]+)\]`;
const RE = {
  init: RE_INIT,
  result: RE_RESULT,
  tick: new RegExp(
    `^${BOT} \\[HL-TICK\\] t=(\\d+) terr=(\\d+)\\(([\\d.]+)%\\) bal=(-?\\d+) dens=([\\d.]+) nb=(\\d+) neut=(-?\\d+) cmds=(\\d+) boats=(\\d+) avgMs=([\\d.]+) maxMs=([\\d.]+) skip=(\\d+)`
  ),
  slow: new RegExp(`^${BOT} \\[HL-SLOW-TICK\\] t=(\\d+) took ([\\d.]+)ms \\(max=([\\d.]+)ms\\)`),
  opening: new RegExp(`^${BOT} \\[HL-OPENING\\] t=(\\d+) cyc=(\\d+) DP expand rings=(\\d+) spend=(-?\\d+)/(-?\\d+) terr=(\\d+)`),
  spawn: new RegExp(
    `^${BOT} \\[HL-SPAWN-BACKEND\\] me=(\\d+) slot=(\\d+) role=(\\w+) -> \\((\\d+),(\\d+)\\) bossDist=(-?\\d+) minAllyDist=(-?\\d+) voronoi=(-?\\d+)`
  ),
  coord: /^\[BACKEND-SPAWN-COORD\] Solved (\d+) bots in ([\d.]+)ms \(map=(\d+)x(\d+), minSep=(\d+)px, boss=([^)]*)\): (.*)$/,
  donateSurplus: new RegExp(
    `^${BOT} \\[HL-DONATE\\] t=(\\d+) surplus donate pct=(\\d+)/1024 \\(~\\d+%\\) -> ally=(\\d+)\\((.*)\\) boxedIn=(\\w+) myBal=(-?\\d+) dMe=(-?\\d+)`
  ),
  donateRescue: new RegExp(
    `^${BOT} \\[HL-DONATE\\] t=(\\d+) squad rescue donate pct=(\\d+)/1024 \\(~\\d+%\\) -> ally=(\\d+)\\((.*)\\) myBal=(-?\\d+) dMe=(-?\\d+) dAlly=(-?\\d+)`
  ),
  donateOther: new RegExp(`^${BOT} \\[HL-DONATE\\] t=(\\d+) (.*)$`),
  assistRescue: new RegExp(
    `^${BOT} \\[HL-ASSIST\\] t=(\\d+) 10% squad-rescue poke -> enemy=(\\d+)\\((.*)\\) for ally=(\\d+)\\((.*)\\)$`
  ),
  assistOther: new RegExp(`^${BOT} \\[HL-ASSIST\\] t=(\\d+) (.*)$`),
  intercept: new RegExp(
    `^${BOT} \\[HL-INTERCEPT\\] t=(\\d+) unified sea intercept pct=(\\d+)/1024 -> boatId=(\\d+) owner=(\\d+)\\((.*)\\) boatTroops=(-?\\d+)`
  ),
  hlOther: new RegExp(`^${BOT} \\[(HL-[A-Z-]+)\\] (.*)$`),
  openingCheck: /^\[OPENING-CHECK (\d+) bots @ tick (\d+)\] (.*)$/,
  hot: /^\[HOT-IMPORT\] Injected updated (\S+) \((\d+) bytes\) into (\[Nope\] \S+) live!/,
  err: new RegExp(`^${BOT} ERROR: (.*)$`),
};

export function shortBot(name) {
  return name.replace(/^\[Nope\] /, '');
}

// 把一行解析成事件对象；不认识或不在范围内的行返回 null。
export function parseLine(line, lineNo) {
  if (!line || isOutOfScope(line)) return null;
  let m;
  if ((m = line.match(RE.tick))) {
    return {
      kind: 'tick', line: lineNo, bot: shortBot(m[1]), t: +m[2], terr: +m[3], pct: +m[4], bal: +m[5], dens: +m[6],
      nb: +m[7], neut: +m[8], cmds: +m[9], boats: +m[10], avgMs: +m[11], maxMs: +m[12], skip: +m[13],
    };
  }
  if ((m = line.match(RE.init))) {
    return { kind: 'init', line: lineNo, bot: shortBot(m[1]), mode: +m[2], map: +m[3], seed: +m[4], players: +m[5], me: +m[6] };
  }
  if ((m = line.match(RE.result))) {
    let team = null;
    try { team = JSON.parse(m[6]); } catch { team = null; }
    return { kind: 'result', line: lineNo, bot: shortBot(m[1]), result: m[2], event: m[3], place: +m[4], peak: +m[5], team };
  }
  if ((m = line.match(RE.slow))) return { kind: 'slow', line: lineNo, bot: shortBot(m[1]), t: +m[2], took: +m[3], max: +m[4] };
  if ((m = line.match(RE.opening))) {
    return { kind: 'opening', line: lineNo, bot: shortBot(m[1]), t: +m[2], cyc: +m[3], rings: +m[4], spend: +m[5], bal: +m[6], terr: +m[7] };
  }
  if ((m = line.match(RE.spawn))) {
    return {
      kind: 'spawn', line: lineNo, bot: shortBot(m[1]), me: +m[2], slot: +m[3], role: m[4], x: +m[5], y: +m[6],
      bossDist: +m[7], minAllyDist: +m[8], voronoi: +m[9],
    };
  }
  if ((m = line.match(RE.coord))) {
    const assign = m[7].split(' | ').map((s) => {
      const a = s.match(/^(\[Nope\] \S+)\((\w+)\)->\((\d+),(\d+)\)/);
      return a ? { bot: shortBot(a[1]), role: a[2], x: +a[3], y: +a[4] } : { raw: s };
    });
    return { kind: 'coord', line: lineNo, n: +m[1], ms: +m[2], W: +m[3], H: +m[4], minSep: +m[5], boss: m[6], assign };
  }
  if ((m = line.match(RE.donateSurplus))) {
    return {
      kind: 'donate', sub: 'surplus', line: lineNo, bot: shortBot(m[1]), t: +m[2], pct: +m[3], ally: +m[4], allyName: shortBot(m[5]),
      boxedIn: m[6] === 'true', myBal: +m[7], dMe: +m[8],
    };
  }
  if ((m = line.match(RE.donateRescue))) {
    return {
      kind: 'donate', sub: 'rescue', line: lineNo, bot: shortBot(m[1]), t: +m[2], pct: +m[3], ally: +m[4], allyName: shortBot(m[5]),
      myBal: +m[6], dMe: +m[7], dAlly: +m[8],
    };
  }
  if ((m = line.match(RE.donateOther))) return { kind: 'donate', sub: 'other', line: lineNo, bot: shortBot(m[1]), t: +m[2], raw: m[3] };
  if ((m = line.match(RE.assistRescue))) {
    return {
      kind: 'assist', sub: 'rescue', line: lineNo, bot: shortBot(m[1]), t: +m[2], enemy: +m[3], enemyName: m[4], ally: +m[5],
      allyName: shortBot(m[6]),
    };
  }
  if ((m = line.match(RE.assistOther))) return { kind: 'assist', sub: 'other', line: lineNo, bot: shortBot(m[1]), t: +m[2], raw: m[3] };
  if ((m = line.match(RE.intercept))) {
    return {
      kind: 'intercept', line: lineNo, bot: shortBot(m[1]), t: +m[2], pct: +m[3], boatId: +m[4], owner: +m[5], ownerName: m[6],
      boatTroops: +m[7],
    };
  }
  if ((m = line.match(RE.openingCheck))) {
    const bots = m[3].split(' | ').map((s) => {
      const a = s.match(/^(\[Nope\] \S+):tick=(-?\d+),terr=(-?\d+),sent=(-?\d+)\((\w+)\)/);
      return a ? { bot: shortBot(a[1]), tick: +a[2], terr: +a[3], sent: +a[4], status: a[5] } : { raw: s };
    });
    return { kind: 'openingCheck', line: lineNo, n: +m[1], tick: +m[2], bots };
  }
  if ((m = line.match(RE.hot))) return { kind: 'hotImport', line: lineNo, file: m[1], bytes: +m[2], bot: shortBot(m[3]) };
  if ((m = line.match(RE.err))) return { kind: 'error', line: lineNo, bot: shortBot(m[1]), msg: m[2] };
  if ((m = line.match(RE.hlOther))) return { kind: 'hlOther', line: lineNo, bot: shortBot(m[1]), tag: m[2], raw: m[3] };
  if (line.startsWith('[SQUAD-SYNC] Entering Team Room')) {
    const mm = line.match(/room0Players=(\d+)/);
    const names = [...line.matchAll(/\[Nope\] (\w+)/g)].map((x) => x[1]);
    return { kind: 'roomEnter', line: lineNo, bots: names, room0Players: mm ? +mm[1] : null };
  }
  return { kind: 'unparsed', line: lineNo, raw: line.slice(0, 200) };
}

// 一局的全部事件（含行号）。connLines：范围外的连接类行只计数。
export function gameEvents(lines, seg) {
  const events = [];
  const connLines = {};
  for (let n = seg.start; n <= seg.end; n++) {
    const l = lines[n - 1];
    if (!l) continue;
    if (isOutOfScope(l)) {
      const b = l.match(/^\[(\[Nope\] [^\]]+)\]/);
      const key = b ? shortBot(b[1]) : '_squad';
      connLines[key] = (connLines[key] || 0) + 1;
      continue;
    }
    const e = parseLine(l, n);
    if (e) events.push(e);
  }
  return { events, connLines };
}

// 把 RESULT 行和 results.jsonl 的记录按 (bot, result, event, place, peak) 一一对上。
export function joinResults(events, results) {
  const out = [];
  for (const e of events) {
    if (e.kind !== 'result') continue;
    const cands = results.filter(
      (r) => shortBot(r.bot) === e.bot && r.result === e.result && r.event === e.event && r.place === e.place && r.peak === e.peak
    );
    if (cands.length !== 1) throw new Error(`RESULT line ${e.line} (${e.bot}) matches ${cands.length} records`);
    out.push({ logLine: e.line, rec: cands[0] });
  }
  return out;
}

export function ensureDir(d) {
  fs.mkdirSync(d, { recursive: true });
  return d;
}

export function writeCsv(file, rows, cols) {
  const esc = (v) => {
    if (v === undefined || v === null) return '';
    const s = String(v);
    return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  const body = [cols.join(',')].concat(rows.map((r) => cols.map((c) => esc(r[c])).join(','))).join('\n') + '\n';
  fs.writeFileSync(file, body);
}

export function readCsv(file) {
  const txt = fs.readFileSync(file, 'utf8').trimEnd().split('\n');
  const cols = txt[0].split(',');
  return txt.slice(1).map((l) => {
    const cells = [];
    let cur = '', q = false;
    for (let i = 0; i < l.length; i++) {
      const ch = l[i];
      if (q) {
        if (ch === '"' && l[i + 1] === '"') { cur += '"'; i++; } else if (ch === '"') q = false; else cur += ch;
      } else if (ch === '"') q = true;
      else if (ch === ',') { cells.push(cur); cur = ''; } else cur += ch;
    }
    cells.push(cur);
    const o = {};
    cols.forEach((c, i) => { o[c] = cells[i]; });
    return o;
  });
}

export function gitHead() {
  try {
    const top = path.resolve(HERE, '..', '..', '..', '..');
    const head = fs.readFileSync(path.join(top, '.git'), 'utf8');
    return head.trim();
  } catch {
    return 'unknown';
  }
}
