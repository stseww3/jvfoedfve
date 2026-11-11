// map_ascii.mjs — 把指定拍的领土归属画成字符图，看清本队各号和邻居的相对位置（谁挨着谁、谁被谁围住、海在哪边）。
// 用法：node map_ascii.mjs <matchId> --ticks 630,1530,... [--replay id] [--log id1,id2] [--bots a,b]
//                          [--box x0,y0,x1,y1] [--cell 6] [--pad 60] [--mark "名字片段=字符,#席位号=字符,…"]
//   （--mark 的字符请用小写字母，免得和本队的 A–J 撞车）
//   不给 --box 时取本队出生点的包围盒再外扩 --pad 像素。每个字符代表 cell×cell 像素，取其中出现最多的归属。
//   字符：本队各号 = A–J（图例里列出）；同队其他人类 = m；--mark 指定的玩家用指定字符；其余人类按队号 1–7；
//         离场壳在字符后不另标（图例里有离场名单）；内置 AI = a；无主陆地 = .；水 = ~；山/边界 = #。
// 图例另列出：框内领土最多的 12 个非本队玩家（名字、队、框内格数、全图领土、兵力）。
import fs from 'node:fs';
import { openMatch, readLogSnaps, T_LAND, T_WATER, P_INNER } from './resim_lib.mjs';

const args = process.argv.slice(2);
const mid = args[0];
const opt = (k, d) => (args.includes(`--${k}`) ? args[args.indexOf(`--${k}`) + 1] : d);
const ticks = opt('ticks', '630,1530').split(',').map(Number).sort((a, b) => a - b);
const cell = +opt('cell', 6), pad = +opt('pad', 60);
const m = openMatch(mid, { replay: opt('replay', mid) });
const { g, H } = m;
const onlyBots = opt('bots', '') ? new Set(opt('bots', '').split(',')) : null;
const squad = {};
for (const lb of opt('log', mid).split(',')) {
  const { me } = readLogSnaps(lb, lb === mid ? '' : lb + ':', onlyBots);
  for (const [b, p] of Object.entries(me)) squad[(lb === mid ? '' : lb + ':') + b] = p;
}
const sqIds = Object.values(squad);
const letter = {};
Object.entries(squad).sort((a, b) => a[1] - b[1]).forEach(([b, p], i) => { letter[p] = String.fromCharCode(65 + i); });
const marks = {};
for (const kv of (opt('mark', '') || '').split(',').filter(Boolean)) {
  const [frag, ch] = kv.split('=');
  if (/^#\d+$/.test(frag)) { marks[+frag.slice(1)] = ch; continue; }
  for (let p = 0; p < H; p++) if ((m.names[p] || '').includes(frag)) marks[p] = ch;
}
let box = opt('box', null);
if (box) box = box.split(',').map(Number);
else {
  const xs = sqIds.filter((p) => m.spawn[p]).map((p) => m.spawn[p][0]), ys = sqIds.filter((p) => m.spawn[p]).map((p) => m.spawn[p][1]);
  box = [Math.max(0, Math.min(...xs) - pad), Math.max(0, Math.min(...ys) - pad), Math.min(g.W - 1, Math.max(...xs) + pad), Math.min(g.H - 1, Math.max(...ys) + pad)];
}
const myTeam = g.teams[sqIds[0]];
const chOf = (c) => {
  const v = g.px[c];
  if (v === T_WATER) return '~';
  if (v === T_LAND) return '.';
  if (v < P_INNER) return '#';
  const o = g.own[c];
  if (letter[o]) return letter[o];
  if (marks[o]) return marks[o];
  if (o >= H) return 'a';
  return g.teams[o] === myTeam ? 'm' : String(g.teams[o]);
};
const draw = () => {
  console.log(`\n== ${mid} t=${g.t} 框 x ${box[0]}–${box[2]}, y ${box[1]}–${box[3]}，每字符 ${cell}×${cell} 像素`);
  const inBox = new Map();
  for (let y = box[1]; y <= box[3]; y += cell) {
    let line = '';
    for (let x = box[0]; x <= box[2]; x += cell) {
      const cnt = {};
      for (let dy = 0; dy < cell; dy++) for (let dx = 0; dx < cell; dx++) {
        const xx = x + dx, yy = y + dy;
        if (xx >= g.W || yy >= g.H) continue;
        const c = yy * g.W + xx, ch = chOf(c);
        cnt[ch] = (cnt[ch] || 0) + 1;
        if (g.px[c] >= P_INNER) { const o = g.own[c]; inBox.set(o, (inBox.get(o) || 0) + 1); }
      }
      let best = ' ', bn = -1;
      for (const [ch, n] of Object.entries(cnt)) if (n > bn) { bn = n; best = ch; }
      line += best;
    }
    console.log(line);
  }
  console.log('本队：' + Object.entries(squad).sort((a, b) => a[1] - b[1]).map(([b, p]) => `${letter[p]}=${b}(${g.alive[p] ? g.terr[p] : '亡'})`).join(' '));
  const others = [...inBox.entries()].filter(([o]) => !letter[o] && o < H).sort((a, b) => b[1] - a[1]).slice(0, 12);
  console.log('框内其他人类（名字/队 框内格数 全图领土 兵力 状态）：' + others.map(([o, n]) => `${marks[o] ? marks[o] + '=' : ''}${m.names[o]}/T${g.teams[o]} ${n} ${g.terr[o]} ${g.bal[o]}${g.state[o] === 2 ? ' 壳' : ''}`).join('；'));
};
let ti = 0;
while (ti < ticks.length) {
  if (g.t >= ticks[ti]) { draw(); ti++; continue; }
  if (!m.tick()) { draw(); break; }
}
