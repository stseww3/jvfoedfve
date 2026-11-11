// attack_pct_signature.mjs — 用录像里「我方号实际被执行的进攻指令」的千分比（pct/1024）分布给策略版本做指纹。
// 原理（v27 买地函数 Policy.buyLand）：对真人的「脉冲」进攻量 = floor(pulseFrac × 兵力)，
//   指令 pct = ceil(量×1024/兵力) − 1 → pulseFrac=0.12 时 pct=122，pulseFrac=0.20 时 pct=204；
//   t≥3800 的补刀下限 floor(0.08×兵力) → pct=81；boss-assist 轻戳 pct=82（c116）/102（c110）。
// 输出：每局我方号对「真人目标」的进攻 pct 直方图前 8 名（带占比），以及对机器人/无主地的条数。
// 用法：node attack_pct_signature.mjs <matchId> [...]   （不带参数=全部有录像的包）
import fs from 'node:fs';
import path from 'node:path';
import { loadReplay, timeline } from './replay_cmds.mjs';

const DATA = process.env.C136_DATA || '/agent/repos/c136-data';
const ids = process.argv.slice(2).length ? process.argv.slice(2) : fs.readdirSync(path.join(DATA, 'bundles')).sort();
const SQUAD_RE = /^(\[[^\]]*\]\s*)?(mishi|matzz|kiholma|leo_99|racoon|zexos|talon|vortex|kronos|nexus|777|sayo|kaito|riku|_alex|tomo|zero_2|sora|lucas94|dave_w|mark07|kevin_k|ethan21|ryan_m|noah88|leo_tx|alex_k|zero_7|kaito9|riku_x|sora_w|zexos1|talon5)$/i;

console.log(['matchId', 'ourInReplay', 'atkHuman', 'atkBot', 'atkNeutral', 'top pct on humans (pct:count:share)'].join('\t'));
for (const id of ids) {
  const dir = path.join(DATA, 'bundles', id);
  if (!fs.existsSync(path.join(dir, 'replay.txt'))) continue;
  let d, tl;
  try { d = loadReplay(id); tl = timeline(d); } catch (e) { continue; }
  const H = d.vu.humanCount;
  const names = d.vu.playerNamesData ? d.vu.playerNamesData.data : [];
  // 我方号：先用日志里的号名（B 系是伪装名），否则用固定名单
  const logBots = new Set();
  const logp = path.join(dir, 'in_game.log');
  if (fs.existsSync(logp)) {
    const re = /\[([^\]]+)\] \[HL-GAME-INIT\]/g; let m; const txt = fs.readFileSync(logp, 'utf8');
    while ((m = re.exec(txt))) logBots.add(m[1].toLowerCase());
  }
  const ours = new Set();
  for (let p = 0; p < H; p++) {
    const n = String(names[p] ?? '').trim();
    const bare = n.replace(/\[[^\]]*\]/g, '').trim().toLowerCase();
    if (logBots.has(bare) || (logBots.size === 0 && SQUAD_RE.test(n))) ours.add(p);
  }
  const hist = new Map(); let nh = 0, nb = 0, nn = 0;
  for (const c of tl.cmds) {
    if (c.id !== 1 || !ours.has(c.player) || c.tick < 0) continue;
    if (c.dZ === 512) { nn++; continue; }
    if (c.dZ >= H) { nb++; continue; }
    nh++; hist.set(c.dX, (hist.get(c.dX) ?? 0) + 1);
  }
  const top = [...hist.entries()].sort((a, b) => b[1] - a[1]).slice(0, 8).map(([p, n]) => `${p}:${n}:${(100 * n / Math.max(1, nh)).toFixed(0)}%`).join(' ');
  console.log([id, ours.size, nh, nb, nn, top].join('\t'));
}
