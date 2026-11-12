// common.mjs — R01 断面归因 / 模拟器保真度核验的公共部分（纯离线）。
//
// 只读地引用 R06 入库的离线模拟器库（c136-review/archive/agents/R06/sim-v2/lib/*.mjs）：不改它、不往它的目录里写东西。
// 我方席位、录像来源、页面寿命、出局拍用 R01 自己重演出来的数据（out/<局>/resim_*.csv、resim_meta.json）另行核定后盖上去，
// 这样「物理底座 / 决策层 / 通道层」三层的核对用的是两套互相独立的数据来源。
//
// 策略只允许历史上真实跑过的四个版本（Va / Vb / Vc / c110），别的文件一律拒绝：本目录的工具只做历史归因与模拟器验收。
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

export const HERE = path.dirname(fileURLToPath(import.meta.url));
export const R01 = path.resolve(HERE, '../..');
export const SIMV2 = path.resolve(R01, '../../archive/agents/R06/sim-v2');
export const OUT = path.join(R01, 'out');
export const DATA = '/agent/repos/c136-data';

const lib = (f) => import(path.join(SIMV2, 'lib', f));
export const LM = await lib('match.mjs');
export const LS = await lib('sandbox.mjs');
export const LC = await lib('channel.mjs');
export const LA = await lib('arm.mjs');
export const LX = await lib('metrics.mjs');
export const LU = await lib('util.mjs');
export const LT = await lib('tgame.mjs');

// 历史版本：局号 → 当年跑的那一版（VERSION-TIMELINE.md）
export function historicalStrategy(mid) {
  if (/^B/.test(mid)) return 'c110';
  const n = +mid.slice(1);
  if (n <= 17) return 'va';
  if (n <= 95) return 'vb';
  return 'vc';
}
const ALLOWED = new Set(['va', 'vb', 'vc', 'c110']);
export async function loadHistoricalStrategy(short) {
  const k = String(short).toLowerCase();
  if (!ALLOWED.has(k)) throw new Error(`只允许历史版本 va / vb / vc / c110，收到 ${short}`);
  return LS.compileStrategy(LS.strategyPath(k));
}

export function readCsv(file) {
  if (!fs.existsSync(file)) return [];
  const lines = fs.readFileSync(file, 'utf8').split('\n').filter(Boolean);
  const head = lines[0].split(',');
  return lines.slice(1).map((l) => {
    const c = splitCsv(l);
    const o = {};
    head.forEach((k, i) => { o[k] = c[i]; });
    return o;
  });
}
function splitCsv(l) {
  if (l.indexOf('"') < 0) return l.split(',');
  const out = [];
  let cur = '', q = false;
  for (let i = 0; i < l.length; i++) {
    const ch = l[i];
    if (ch === '"') q = !q;
    else if (ch === ',' && !q) { out.push(cur); cur = ''; } else cur += ch;
  }
  out.push(cur);
  return out;
}

// R06 的对局包里已有、且我方席位与 R01 一致的局：席位沿用包里的（A057 的 resim_meta 把同房间 B038 的 20 个号也记在一起了）
const USE_PACK_SQUAD = new Set(['A057']);

// 装一局。返回 R06 loadMatch 的对象，另加：
//   M.r01 = { meta, squadSrc, pageEndSrc, deathSrc }
// 盖掉的字段：squad（R01 的 resim_meta）、pageEnd（R01 逐点核对过的日志快照末拍 + 89）、deathT / doomed（R01 重演的出局事件）。
export function loadR01(mid) {
  const dir = path.join(OUT, mid);
  const metaF = path.join(dir, 'resim_meta.json');
  if (!fs.existsSync(metaF)) throw new Error(`${mid}: 没有 out/${mid}/resim_meta.json（先跑 scripts/resim.mjs）`);
  const meta = JSON.parse(fs.readFileSync(metaF, 'utf8'));
  const replayFrom = meta.replayOf && meta.replayOf !== mid ? meta.replayOf : undefined;
  const metaSquad = [...new Set(Object.values(meta.squad || {}))].sort((a, b) => a - b);
  const opts = { replayFrom };
  if (!USE_PACK_SQUAD.has(mid) && metaSquad.length) opts.squad = metaSquad;
  const M = LM.loadMatch(mid, opts);
  const squadSet = new Set(M.squad);

  // AI 名字（只有 B039 / B043 存了；策略只在日志里用到）
  const namesF = path.join(dir, 'names512.json');
  if (fs.existsSync(namesF)) {
    const nm = JSON.parse(fs.readFileSync(namesF, 'utf8'));
    const arr = Array.isArray(nm) ? nm : nm.names;
    if (Array.isArray(arr)) for (let p = M.H; p < arr.length && p < M.names.length; p++) if (!M.names[p]) M.names[p] = String(arr[p] ?? '');
  }

  // 页面寿命：R01 核对过的日志快照（resim_check.csv：t,bot,p,…）每个席位最后一条的拍 + 89，与录像最后一条指令取大
  const check = readCsv(path.join(dir, 'resim_check.csv'));
  const lastSnap = new Map();
  for (const r of check) {
    const p = +r.p, t = +r.t;
    if (!squadSet.has(p)) continue;
    if ((lastSnap.get(p) ?? -1) < t) lastSnap.set(p, t);
  }
  const pageEnd = new Map();
  for (const p of M.squad) pageEnd.set(p, Math.max(lastSnap.has(p) ? lastSnap.get(p) + 89 : -1, M.lastCmd.get(p) ?? -1));
  const pageEndR06 = new Map(M.pageEnd);
  M.pageEnd = pageEnd;

  // 出局拍：R01 重演的 died 事件
  const ev = readCsv(path.join(dir, 'resim_events.csv'));
  const deathT = {};
  for (const p of M.squad) deathT[p] = -1;
  for (const r of ev) if (r.ev === 'died' && squadSet.has(+r.p) && deathT[+r.p] < 0) deathT[+r.p] = +r.t;
  M.deathT = deathT;
  const doomed = new Set();
  for (const p of M.squad) {
    const dt = deathT[p];
    if (pageEnd.get(p) + 1 < (dt >= 0 ? dt : M.replayTicks - 90)) doomed.add(p);
  }
  M.doomed = doomed;
  M.r01 = { meta, replayFrom: replayFrom || mid, metaSquad, lastSnap, pageEndR06 };
  return M;
}

export function cpuMs(c0) { const c = process.cpuUsage(c0); return Math.round((c.user + c.system) / 1000); }
export function writeJson(file, obj, pretty = false) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, pretty ? JSON.stringify(obj, null, 1) : JSON.stringify(obj));
}
