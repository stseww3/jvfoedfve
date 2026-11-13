#!/usr/bin/env node
// boatwhy.mjs — 「一发出就走到头、位置是地图下标 0」的船是怎么发出来的（走偏第一处根因的上游；只读模拟器）
//
// boatprobe / fixprobe 查的是这种船靠岸以后兵的去向；这里查它为什么会停在地图左上角。读 src/sim/sim/boats.js 得到的猜想：
//   真人发船 boat(pct, water, dir) → findBoatRoute → boatRouteIndex：先找本方离 water 最近的海岸格 → 它旁边的水格 start；
//   start ≠ water、两点之间又没有直线 / 折线水路时走 searchRoute(water, p)——从 water 向外一圈圈搜，搜到「上下左右挨着本方的地」的水格为止。
//   如果 water 自己就挨着本方的地，第一圈就停，回溯的路径只有 [water] 一个点（boats.js L743-758 的 dh）。
//   航线只有一个点：moveBoats 取 rb[k+1] 是 undefined，算出来的位置是 NaN，写进 Uint32Array 变成 0——船的位置成了地图下标 0，
//   进度当拍到 65535；下一拍靠岸读的是「下标 0 按发船方向挪一格」：上 → −W（图外），右 → 1，下 → W（图边的格），左 → −1（图外）。
// 这一步模拟器和线上引擎是一致的（两边都发出了这艘船，boatprobe 在引擎里读到的位置也是下标 0），所以只用模拟器就能查。
//
// 做法：在重放器的对局对象实例上包几个函数（src/sim 不动、不改任何指令）：
//   boat()        记下真人这条发船指令的 water、dir；成了的指令按「water 四邻里有没有本方的地、那些地在不在海岸表里」分三类计数；
//   boatRouteIndex() / searchRoute()  记这条指令的航线是从寻路的哪一步出来的（表里现成的 / 反向的 / 起点就是 water / 直线 / 搜出来的）；
//   launchBoat()  每艘船发出时记航线的点数；点数 < 2 的，把上面那条猜想里的每一步读出来（最近的海岸格、start、water 四邻里本方的地在不在海岸表里）。
//   landAt()      只读：这艘船靠岸要读的那一格、读到的值。
//
//   bash c136-review/tools/run-heavy.sh node c136-review/agents/R08/scripts/boatwhy.mjs [--budget 秒] <局> [<局> ...]
//   → out/_run/boatwhy/<局>.json（已有的跳过）；汇总见 boatwhy.py
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { resim } from './resim_r08.mjs';

const DATA = process.env.C136_DATA || '/agent/repos/c136-data';
const HERE = path.dirname(fileURLToPath(import.meta.url));
const OUT = path.join(HERE, '..', 'out', '_run', 'boatwhy');
const { T_LAND, T_WATER, P_INNER } = await import(path.join(DATA, 'src/sim/sim/index.js'));
const argv = process.argv.slice(2);
let budget = 80;
const mids = [];
for (let i = 0; i < argv.length; i++) {
  if (argv[i] === '--budget') budget = +argv[++i];
  else mids.push(argv[i]);
}
const T0 = Date.now();

function probe(mid) {
  let G = null, H = 0;
  const cnt = { boatCmd: 0, boatCmdOk: 0, launch: 0, launchHuman: 0, launchBot: 0, lenHist: {},
    // 真人发船指令（成了的）按「water 四邻里有没有本方的地、那些地在不在海岸表里」分：
    //   adj0 没有本方的地；adjCoast 有、至少一格在海岸表里；adjNoCoast 有、但没有一格在海岸表里
    adj0: 0, adjCoast: 0, adjNoCoast: 0, adj0Len1: 0, adjCoastLen1: 0, adjNoCoastLen1: 0,
    // 同一批指令再按 boatRouteIndex 里航线是从哪一步出来的分：br[类][步] = [指令数, 其中航线只有一个点的]
    //   table 航线表里现成的（起点→water）；reversed 表里有反向的；same 起点就是 water，建 [water, water]；
    //   straight 直线或「斜一段再直一段」；search 走到 searchRoute
    br: {} };
  const notes = [];      // 航线点数 < 2 的船
  const lands = [];      // 靠岸要读的那一格不是无主地也不是有主的地（和 fixprobe [FX-D] 同一个口径，用来对账）
  let cur = null;        // 正在执行的真人发船指令
  const X = resim(mid, {
    onStart: (g, ctx) => {
      G = g;
      H = ctx.H;
      const boat0 = g.boat;
      g.boat = function (pct, water, dir, p = this.me) {
        cnt.boatCmd++;
        cur = { pct, water, dir: dir & 7, p, len: -1 };
        // 调用以前先读（发船会改海岸表以外的东西，不改地；这里只读）
        let ownAdj = 0, ownAdjCoast = 0;
        const C = this.coast[p];
        if (C) {
          const d = this.dir4, px = this.px, own = this.own;
          for (let g4 = 0; g4 < 4; g4++) {
            const c = water + d[g4];
            if (px[c] >= P_INNER && own[c] === p) {
              ownAdj++;
              if (C.indexOf(c) >= 0) ownAdjCoast++;
            }
          }
        }
        const me = cur;
        const ok = boat0.call(this, pct, water, dir, p);
        cur = null;
        if (ok) {
          cnt.boatCmdOk++;
          const key = ownAdj === 0 ? 'adj0' : ownAdjCoast ? 'adjCoast' : 'adjNoCoast';
          cnt[key]++;
          if (me.len === 1) cnt[key + 'Len1']++;
          const br = me.br === 'straight?' ? 'straight' : me.br || 'unknown';
          const B = cnt.br[key] || (cnt.br[key] = {});
          const e = B[br] || (B[br] = [0, 0]);
          e[0]++;
          if (me.len === 1) e[1]++;
        }
        return ok;
      };
      // 航线是从 boatRouteIndex 的哪一步出来的：先照它的顺序只读地走一遍（这几个函数都不改状态），再调原函数
      const bri0 = g.boatRouteIndex;
      g.boatRouteIndex = function (p, u9, bfs) {
        if (cur && cur.p === p && cur.water === u9) {
          const o5 = this.nearestCoast(p, u9);
          const start = o5 >= 0 ? this.waterNextTo(o5, u9) : -1;
          cur.br = o5 < 0 || start < 0 ? 'nocoast'
            : this.findRoute(start, u9) >= 0 ? 'table'
              : this.routesFull() ? 'full'
                : this.findRoute(u9, start) >= 0 ? 'reversed'
                  : start === u9 ? 'same' : 'straight?';
        }
        return bri0.call(this, p, u9, bfs);
      };
      const search0 = g.searchRoute;
      g.searchRoute = function (start, p) {
        const k = search0.call(this, start, p);
        if (cur && cur.p === p && cur.water === start) cur.br = k >= 0 ? 'search' : 'searchfail';
        return k;
      };
      const launch0 = g.launchBoat;
      g.launchBoat = function (p) {
        const r = this.routeTmp;
        const n = r ? r.length : -1;
        cnt.launch++;
        if (p < H) cnt.launchHuman++; else cnt.launchBot++;
        cnt.lenHist[n] = (cnt.lenHist[n] || 0) + 1;
        if (cur && cur.p === p) cur.len = n;
        if (n < 2) {
          const W = this.W, d = this.dir4, px = this.px, own = this.own;
          const note = { t: this.t, p, human: p < H ? 1 : 0, type: this.boatType, len: n, r0: n > 0 ? r[0] : null, troops: this.attackTroopsTmp, W, H: this.H,
            fromCmd: cur && cur.p === p ? 1 : 0 };
          if (cur && cur.p === p) {
            const u9 = cur.water;
            note.water = u9;
            note.dir = cur.dir;
            note.waterIs = px[u9] === T_WATER ? 1 : 0;
            // water 四邻：本方的地有几格，其中在海岸表里的有几格、在边界表里的有几格、四邻里有无主地或别人的地的有几格
            const C = this.coast[p], Bd = this.border[p];
            let ownAdj = 0, ownAdjCoast = 0, ownAdjBorder = 0, ownAdjHostile = 0;
            for (let g4 = 0; g4 < 4; g4++) {
              const c = u9 + d[g4];
              if (px[c] >= P_INNER && own[c] === p) {
                ownAdj++;
                if (C.indexOf(c) >= 0) ownAdjCoast++;
                if (Bd.indexOf(c) >= 0) ownAdjBorder++;
                let hostile = false;
                for (let h4 = 0; h4 < 4; h4++) if (this.hostileTo(c + d[h4], p)) hostile = true;
                if (hostile) ownAdjHostile++;
              }
            }
            note.ownAdj = ownAdj;
            note.ownAdjCoast = ownAdjCoast;
            note.ownAdjBorder = ownAdjBorder;
            note.ownAdjHostile = ownAdjHostile;
            note.br = cur.br === 'straight?' ? 'straight' : cur.br || null;
            note.coastLen = C.length;
            // boatRouteIndex 的前两步（只读的两个函数）
            const o5 = this.nearestCoast(p, u9);
            note.nearestCoast = o5;
            note.coastDist2 = o5 >= 0 ? this.dist2(o5, u9) : null;
            const start = o5 >= 0 ? this.waterNextTo(o5, u9) : -1;
            note.start = start;
            note.startIsWater = start === u9 ? 1 : 0;
            note.startDist2 = start >= 0 ? this.dist2(start, u9) : null;
            // 靠岸的那一格本来该是哪一格（water 按方向挪一格）、是谁的
            const land = u9 + d[cur.dir & 3];
            note.wantCell = land;
            note.wantOwner = px[land] >= P_INNER ? own[land] : px[land] === T_LAND ? 'neutral' : null;
            note.routeIsWater = n === 1 && r[0] === u9 ? 1 : 0;
          }
          if (notes.length < 400) notes.push(note);
        }
        return launch0.call(this, p);
      };
      const land0 = g.landAt;
      g.landAt = function (p, troops, c, at) {
        const v = this.px[c];
        if (!(v === T_LAND || v >= P_INNER) && lands.length < 400) lands.push({ t: this.t, p, troops, c, at, v: v === undefined ? null : v });
        return land0.call(this, p, troops, c, at);
      };
    },
  });
  const v = X.validate;
  return { matchId: mid, H: X.H, nTeams: X.nTeams, endTick: G.t, val: { rows: v.rows, both: v.bothExact }, cnt, notes, lands };
}

fs.mkdirSync(OUT, { recursive: true });
let done = 0;
for (const mid of mids) {
  const fp = path.join(OUT, `${mid}.json`);
  if (fs.existsSync(fp)) continue;
  if (done && (Date.now() - T0) / 1000 > budget) break;
  const mark = path.join(OUT, `${mid}.started`);
  fs.writeFileSync(mark, String(Date.now()));
  const t1 = Date.now();
  const R = probe(mid);
  R.sec = Math.round((Date.now() - t1) / 100) / 10;
  fs.writeFileSync(fp, JSON.stringify(R));
  fs.unlinkSync(mark);
  done++;
  console.log(`${mid} 到 ${R.endTick} 拍 ${R.sec}s 核对 ${R.val.both}/${R.val.rows} 真人发船指令 ${R.cnt.boatCmd} 条（成 ${R.cnt.boatCmdOk}） 发出的船 ${R.cnt.launch} 艘 `
    + `航线不到两个点的 ${R.notes.length} 艘 靠在不是地的格上的 ${R.lands.length} 艘`);
}
console.log(`BOATWHY ${done} 局，用时 ${Math.round((Date.now() - T0) / 1000)}s`);
