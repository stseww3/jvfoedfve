// instance_split.mjs — 检查一个「对局包」里的我方号是不是真的在同一个游戏实例（同一盘）里。
// 背景：A017/A043 的录像里只出现 1~2 个 [APEX] 号，其余号的开局指令在录像命令流里一条都配不上，
//   而日志里 kaito9 捐款的对象 ally=6([APEX] leo_tx) 在录像里 6 号是别人 —— 说明小队被大厅拆进了多个并行实例
//   （同图同种子同 seeded 人数），包里的 replay.txt 只是其中一个实例。
// 三路证据（互相印证）：
//   A. [HL-SPAWN] … (squad=N,rankIdx=k)：该号在自己那盘里看到的我方号总数 N（Policy.chooseSpawn 自主兜底分支打印）。
//   B. 录像：该号的 [HL-OPENING] 指令（pct 由 spend/bal 反推）在录像里按 me 号能否配上 → 该号是否在录像这一盘。
//   C. results.csv：teamMine 与 teamTotals 里出现的队号集合（不同实例的队伍数/队号集合不同）。
// 输出 TSV（每局一行）：matchId cohort nBots seeded squadSeen分布 inReplay/有开局日志的号数 replayApexNames 结论(split?) 分组明细
// 用法：node instance_split.mjs [matchId ...] > out/instance-split.tsv
import fs from 'node:fs';
import path from 'node:path';
import { loadReplay, timeline } from './replay_cmds.mjs';

const DATA = process.env.C136_DATA || '/agent/repos/c136-data';
const ids = process.argv.slice(2).length ? process.argv.slice(2) : fs.readdirSync(path.join(DATA, 'bundles')).sort();

function parseCsv(p) {
  if (!fs.existsSync(p)) return [];
  const lines = fs.readFileSync(p, 'utf8').split('\n').filter(Boolean);
  const head = lines[0].split(',');
  const out = [];
  for (const ln of lines.slice(1)) {
    const cells = []; let cur = '', inQ = false;
    for (let i = 0; i < ln.length; i++) {
      const ch = ln[i];
      if (inQ) { if (ch === '"' && ln[i + 1] === '"') { cur += '"'; i++; } else if (ch === '"') inQ = false; else cur += ch; }
      else if (ch === '"') inQ = true; else if (ch === ',') { cells.push(cur); cur = ''; } else cur += ch;
    }
    cells.push(cur);
    const o = {}; head.forEach((h, i) => (o[h] = cells[i] ?? ''));
    out.push(o);
  }
  return out;
}

console.log(['matchId', 'cohort', 'nBots', 'seeded', 'squadSeen', 'inReplay', 'withOpening', 'replayHumans', 'replaySquadNames', 'split', 'groups'].join('\t'));
for (const id of ids) {
  const dir = path.join(DATA, 'bundles', id);
  if (!fs.existsSync(path.join(dir, 'in_game.log'))) continue;
  const card = JSON.parse(fs.readFileSync(path.join(dir, 'card.json'), 'utf8'));
  const text = fs.readFileSync(path.join(dir, 'in_game.log'), 'utf8').split('\n');
  const me = new Map(), seeded = new Map(), squadSeen = new Map(), opens = new Map();
  const reInit = /\[([^\]]+)\] \[HL-GAME-INIT\].* seeded=(\d+) me=(\d+)/;
  const reSp = /\[([^\]]+)\] \[HL-SPAWN\] me=(\d+) slot=(\d+) \(squad=(\d+),rankIdx=(\d+)\)/;
  const reOpen = /\[([^\]]+)\] \[HL-OPENING\] t=(\d+) cyc=(\d+) DP expand rings=(\d+) spend=(\d+)\/(\d+)/;
  for (const line of text) {
    let m = reInit.exec(line);
    if (m) { if (!me.has(m[1])) { me.set(m[1], +m[3]); seeded.set(m[1], +m[2]); } continue; }
    m = reSp.exec(line);
    if (m) { squadSeen.set(m[1], Math.max(squadSeen.get(m[1]) ?? 0, +m[4])); if (!me.has(m[1])) me.set(m[1], +m[2]); continue; }
    m = reOpen.exec(line);
    if (m) { if (!opens.has(m[1])) opens.set(m[1], []); opens.get(m[1]).push({ t: +m[2], pct: Math.ceil((+m[5]) * 1024 / (+m[6])) - 1 }); }
  }
  const bots = [...new Set([...me.keys(), ...opens.keys()])];
  // B: 录像
  let inReplay = new Map(), replayHumans = '', replaySquad = '';
  if (fs.existsSync(path.join(dir, 'replay.txt'))) {
    try {
      const d = loadReplay(id);
      const tl = timeline(d);
      replayHumans = d.vu.humanCount;
      const names = d.vu.playerNamesData ? d.vu.playerNamesData.data.slice(0, d.vu.humanCount) : [];
      replaySquad = names.filter((n) => bots.some((b) => String(n).toLowerCase().endsWith(b.toLowerCase()))).length;
      const byP = new Map();
      for (const c of tl.cmds) if (c.id === 1 && c.dZ === 512) { if (!byP.has(c.player)) byP.set(c.player, []); byP.get(c.player).push(c); }
      for (const b of bots) {
        const O = opens.get(b) || [];
        if (!O.length || !me.has(b)) continue;
        const R = byP.get(me.get(b)) || [];
        let hit = 0;
        for (const o of O) if (R.some((r) => r.dX === o.pct && r.tick >= o.t && r.tick - o.t <= 600)) hit++;
        inReplay.set(b, hit >= Math.max(1, Math.ceil(0.5 * O.length)));
      }
    } catch (e) { /* 无录像 */ }
  }
  // C: results
  const res = parseCsv(path.join(dir, 'results.csv'));
  const teamKey = new Map();
  for (const r of res) {
    let keys = '';
    try { keys = Object.keys(JSON.parse(r.teamTotals || '{}')).filter((k) => k !== '0').join('/'); } catch (e) { keys = ''; }
    teamKey.set(r.bot, `${r.teamMine || '-'}@${keys || '-'}`);
  }
  // 分组：先按 squadSeen（号数），再按是否在录像里
  const groups = new Map();
  for (const b of bots) {
    const k = `seen=${squadSeen.get(b) ?? '?'}|rep=${inReplay.has(b) ? (inReplay.get(b) ? 'Y' : 'N') : '?'}`;
    if (!groups.has(k)) groups.set(k, []);
    groups.get(k).push(`${b}#${me.get(b) ?? '?'}[${teamKey.get(b) ?? ''}]`);
  }
  const seenVals = [...new Set(bots.map((b) => squadSeen.get(b)).filter((x) => x !== undefined))].sort((a, b) => a - b);
  const repY = [...inReplay.values()].filter(Boolean).length, repN = [...inReplay.values()].filter((x) => !x).length;
  const split = (repY > 0 && repN > 0) || seenVals.some((v) => v < bots.length - 1) ? 'SPLIT' : (inReplay.size ? 'one' : '?');
  console.log([id, card.cohort, bots.length, [...new Set(seeded.values())].join('/'), seenVals.join('/'), repY, inReplay.size, replayHumans, replaySquad, split,
    [...groups.entries()].map(([k, v]) => `{${k}: ${v.join(' ')}}`).join(' ')].join('\t'));
}
