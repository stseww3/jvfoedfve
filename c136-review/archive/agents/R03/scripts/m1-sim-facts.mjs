#!/usr/bin/env node
// m1-sim-facts.mjs — M1：把模拟器（fdvg cursor/c58-v24-95b7 的 territorial-sim/sim，单机 2.16.65 的移植）
// 对经济与战斗的「说法」变成数字。第 2~6 节直接调用模拟器自己的函数；
// 第 7 节的 def 在模拟器里是 expandAttack 内的一行内联公式（game.js 第 800 行），这里照抄那一行。
// 用法：node m1-sim-facts.mjs > ../out/m1-sim-facts.txt   （先跑 fetch-inputs.sh）
import path from 'node:path';

const SIM = process.env.SIM || '/tmp/c136-r03/c58/territorial-sim/sim';
const { Game, iV, NEUTRAL } = await import(path.join(SIM, 'index.js'));

// 一张 64x64 的全陆地小图（最外圈是水），只为了能构造 Game 对象去调它的经济函数。
function tinyMap(w = 64, h = 64) {
  const type = new Uint8Array(w * h);
  const id = new Uint16Array(w * h);
  let land = 0;
  for (let y = 0; y < h; y++) {
    for (let x = 0; x < w; x++) {
      const edge = x === 0 || y === 0 || x === w - 1 || y === h - 1;
      type[y * w + x] = edge ? 2 : 1;
      if (!edge) land++;
    }
  }
  return { index: 0, seed: 0, w, h, type, id, land, mountains: false };
}

const g = new Game({ map: tinyMap(), humans: 2, players: 2, selectableSpawn: true, spawnSeed: 1 });
const out = [];
const P = (s) => out.push(s);

P('# m1-sim-facts：模拟器里的经济/战斗数字（由模拟器自己的函数算出）');
P(`# sim=${SIM}`);

P('\n## 1. iV(a,b) 对非负整数等于向下取整的整数除法');
let bad = 0;
for (let a = 0; a < 3000; a++) for (let b = 1; b < 60; b++) if (iV(a, b) !== Math.floor(a / b)) bad++;
P(`iV(a,b) != floor(a/b) 的个数（a<3000, 1<=b<60）：${bad}`);

P('\n## 2. 利息率 interestRate(p)（单位：万分之一 / 每 10 拍），t>=1920、余额不超软上限');
g.alive[0] = 1;
g.land = 100000;
g.t = 5000;
P('领土份额% | 领土 | 利息率 | 相当于每 10 拍 %');
for (const pct of [0, 0.1, 0.5, 1, 2, 5, 10, 20, 30, 50, 75, 100]) {
  g.terr[0] = Math.round((g.land * pct) / 100);
  g.bal[0] = 1;
  const r = g.interestRate(0);
  P(`${String(pct).padStart(5)} | ${String(g.terr[0]).padStart(6)} | ${String(r).padStart(4)} | ${(r / 100).toFixed(2)}`);
}

P('\n## 3. 开局利息下限：t<1920 时 max(floor(100*(13440-6t)/1920), 查表值)');
g.terr[0] = 100; // 份额 0.1% → 查表值接近最低
g.bal[0] = 1;
P('t | 利息率');
for (const t of [0, 100, 300, 600, 900, 1200, 1500, 1800, 1900, 1919, 1920, 3000]) {
  g.t = t;
  P(`${String(t).padStart(5)} | ${g.interestRate(0)}`);
}

P('\n## 4. 软上限与硬上限：余额超过 100*领土 后利息率线性下降，到 150*领土 归零');
g.t = 5000;
g.terr[0] = 1000; // 软上限 100000，硬上限 150000
P(`领土=${g.terr[0]} 软上限=${g.softCap(0)}`);
P('余额/软上限 | 余额 | 利息率 | 本次利息入账(受 150*领土 硬顶限制)');
for (const m of [0.5, 0.9, 1.0, 1.01, 1.05, 1.1, 1.2, 1.25, 1.3, 1.4, 1.49, 1.5]) {
  g.bal[0] = Math.round(g.softCap(0) * m);
  const r = g.interestRate(0);
  const want = Math.max(iV(r * g.bal[0], 1e4), 1);
  const before = g.bal[0];
  const got = g.addBalance(0, want);
  g.bal[0] = before;
  P(`${m.toFixed(2).padStart(5)} | ${String(before).padStart(7)} | ${String(r).padStart(4)} | ${got}`);
}

P('\n## 5. 陆攻报价 quote(p,pct,12)：兵 = min(floor(B*(pct+1)/1024), B-费)，费 = floor(12*B/1024)');
g.bal[0] = 100000;
P(`余额 B=${g.bal[0]}`);
P('pct | 兵 | 费 | 费/B % | 费/兵 %');
for (const pct of [0, 9, 50, 101, 204, 511, 767, 1010, 1011, 1012, 1023]) {
  const troops = g.quote(0, pct, 12);
  const fee = g.attackFeeTmp;
  P(`${String(pct).padStart(4)} | ${String(troops).padStart(6)} | ${fee} | ${((100 * fee) / g.bal[0]).toFixed(3)} | ${troops ? ((100 * fee) / troops).toFixed(2) : 'inf'}`);
}

P('\n## 6. 推进节拍 resetWait：按领土分档的「每多少拍推进一步」');
P('领土 | 等待值 | 每步间隔(拍)');
for (const terr of [12, 999, 1000, 9999, 10000, 59999, 60000, 200000]) {
  g.terr[0] = terr;
  g.schedWait[0] = 0;
  g.resetWait(0);
  P(`${String(terr).padStart(6)} | ${g.schedWait[0]} | ${g.schedWait[0] + 1}`);
}
g.schedWait[0] = 64;
g.resetWait(0);
P(`新发进攻首次等待：64 → ${g.schedWait[0]}（之后再等这么多拍才走第一步）`);

P('\n## 7. 打玩家每格防御量 def = floor(cnt*B_def / (1+floor(10*L_def/16)))：以 cnt=1 为例');
P('防守方领土 L | 防守方余额 B | 密度 B/L | def(每格) | def/密度 | 进攻方每格成本 2+2*def | 防守方每格掉兵 def');
for (const [L, B] of [[1000, 20000], [1000, 50000], [1000, 100000], [1000, 150000], [5000, 250000], [20000, 2000000], [16, 1600], [1, 512]]) {
  const def = iV(1 * B, 1 + iV(10 * L, 16));
  P(`${L} | ${B} | ${(B / L).toFixed(1)} | ${def} | ${(def / (B / L)).toFixed(3)} | ${2 + 2 * def} | ${def}`);
}

P('\n## 8. 常量（读自模拟器源码，行号见 M1 报告）');
P(`NEUTRAL=${NEUTRAL}  真人进攻槽=${g.slotsHuman}（humans<16 → 12，否则 8） 内置 AI 进攻槽=${g.slotsBot}`);

console.log(out.join('\n'));
