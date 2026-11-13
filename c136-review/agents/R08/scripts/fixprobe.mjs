#!/usr/bin/env node
// fixprobe.mjs — 两处走偏根因的「充分性」检验：把线上引擎原文里的写法补到重放器的对局对象上，看走偏还剩多少。
//
// boatprobe / huskprobe 把 89 局里 3 局走偏（A053、A057、A001）的根因定位到了两处判断条件，但只证明了「引擎在那一步这么走、模拟器那么走」，
// 没有证明「把这两处改成引擎的写法以后，这 3 局别的地方就都对上了」。src/sim 是只读的，所以改法是在重放器这一侧、
// 对局对象的实例上包一层（和 huskprobe / cloneprobe 包壳是同一种做法；src/sim 的文件一个字不动，别的脚本的重演也不受影响）：
//
//   scan  无主地扫描表「要不要重扫」那一步（bots.js scanTick L723）。模拟器：second = 存活 < 2 ? 0 : 第二名个人的地；
//         线上引擎 bD.gv.mf()：存活 < 2 → 0；自由混战 → 第二名的地；组队局 → bk.a6U() > 1（各队总地的 32 拍缓存里，还有地的队多于一个）。
//         这里只在组队局、scanPass ≥ 300 的那一支上换成引擎的写法（那一支的其余语句照抄 bots.js L697-727）。
//   boat  船靠岸要读的那一格既不是无主地、也不是有主的地（boats.js landAt L262-267）。模拟器：直接返回，船上的兵不进任何人的账；
//         线上引擎 acN：不是无主地就按 ad.fR 读「主人号」= ((b0&3)<<7)+((b1&3)<<5)+((b2&3)<<3)+(b3&7)，没有主人的格 b2 存的是地形号、b3 是 0，
//         所以读出来是（地形号 & 3）<< 3（图边的格地形号 3 → 24；boatprobe 看到的 4 次都是 24）。
//         读出来以后走的还是原来那三条路：是自己 → 兵退回；不敌对 → 按受捐上限转交（收不下的作废）；敌对 → 挂成一条进攻。
//         b0、b1 在没有主人的格上是不是总是 0，只有图边格那 4 次观察；山、水两种格没有观察到（这里按同一条公式推，出现了会在输出里单列）。
//         图外的格不在这一处里：模拟器读到的是 undefined，「undefined < 16」不成立所以不会提前返回，接下去 own[c] 也是 undefined，
//         按敌对挂成进攻、目标写进数组以后是 0——和线上引擎读图外格得到 0 号（boatprobe 的 B010 #42）是同一个结果。
//         这种船原样交给模拟器，只记一笔（连同三个边角：船主和 0 号是不是真的敌对、船主是不是已经有对 0 号的进攻、有没有空的进攻栏——
//         这三样引擎是照 0 号查的，模拟器是照 undefined 查的）。
//   both  两处都换。
//   copy  自检：scan 那一支照抄以后规则不换（还是模拟器的 second），应该和 none 逐位相同。
//   none  不换（另外只读地记下：扫描表那一步两种规则不一样的拍、靠在「不是地」的格上的船）。
//
// 没有线上引擎的文件时能用的真值只有本包日志里本编队各号的地和兵（每个快照一行）；所以这里的判据是
// 「参照重演对本包日志快照逐位核对，不一致的行数」，加上每 10 拍全场 512 个玩家地和兵的校验和（和 openloop.mjs 同一个算法，可以互相对）。
// 另外有两处能和线上引擎直接对（清场以前入库的读数，汇总时去比）：
//   boatprobe.txt：5 艘船之后几拍船主的余额和欠账 ←→ 这里每艘船记的 after；
//   huskprobe.txt [HP-A]、[HP-B]：A001 在 4666~4684、4780 拍的随机数状态、扫描表条数和校验和、航线表条数和校验和、终局提速、全场船数、
//   #11 的余额和船数 ←→ 这里的 husk（读法和 huskprobe.mjs 模拟器那一侧逐字相同）。
// 只读 /agent/repos/c136-data（发现集的对局包 + src/sim）；不跑策略，不改任何指令。
//
//   bash c136-review/tools/run-heavy.sh node c136-review/agents/R08/scripts/fixprobe.mjs [--budget 秒] [--arms none,copy,scan,boat,both] <局> [<局> ...]
//   → out/_run/fixprobe/<局>.<臂>.json（已有的跳过）；汇总见 fixprobe.py
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { resim } from './resim_r08.mjs';

const DATA = process.env.C136_DATA || '/agent/repos/c136-data';
const HERE = path.dirname(fileURLToPath(import.meta.url));
const OUT = path.join(HERE, '..', 'out', '_run', 'fixprobe');
const { T_LAND, P_INNER, NEUTRAL } = await import(path.join(DATA, 'src/sim/sim/index.js'));
const argv = process.argv.slice(2);
let budget = 80, arms = ['both'];
const mids = [];
for (let i = 0; i < argv.length; i++) {
  if (argv[i] === '--budget') budget = +argv[++i];
  else if (argv[i] === '--arms') arms = argv[++i].split(',');
  else mids.push(argv[i]);
}
const T0 = Date.now();
const HUSK = { A001: { P: 11, spans: [[4666, 4684], [4780, 4780]] } };
const MOD = 1000000007;

function probe(mid, arm) {
  const fixScan = arm === 'scan' || arm === 'both';
  const fixBoat = arm === 'boat' || arm === 'both';
  const copyScan = fixScan || arm === 'copy';
  let refHash = 2166136261, refHashN = 0;
  const scanNotes = [];      // 扫描表那一步两种规则不一样的拍
  let scanReached = 0;       // 组队局里走到「要不要重扫」那一步的次数
  const boatNotes = [];      // 靠在「不是地」的格上的船
  const husk = [];           // huskprobe 读过的那几拍：同样九项
  const hk = HUSK[mid];
  let G = null;
  const teamsLeft = (g) => {
    let left = 0;
    for (const v of g.teamCacheGet().subarray(0, g.nTeams + 1)) left += v > 0 ? 1 : 0;
    return left;
  };
  const X = resim(mid, {
    onStart: (g) => {
      G = g;
      const scan0 = g.scanTick;
      if (copyScan) {
        g.scanTick = function () {
          if (!this.teamGame || this.scanPass < 300) return scan0.call(this);
          // —— 以下照抄 bots.js scanTick（scanPass ≥ 300 的那一支）——
          let cs = this.scanLen;
          let go;
          if (cs === 0) go = true;
          else {
            if (this.t % 35 === 6) {
              for (let i = cs - 1; i >= 0; i--) {
                if (this.px[this.scanBuf[i]] !== T_LAND) {
                  cs--;
                  this.scanBuf[i] = this.scanBuf[cs];
                }
              }
              this.scanLen = cs;
            }
            go = cs < 512;
          }
          if (!go) return;
          const n = this.scanLen;
          if (n) {
            if (this.t % 350 !== 1) return;
            if (this.scanSeen !== n) {
              this.scanSeen = n;
              return;
            }
            if (!this.isBot(this.rank[0])) return;
          } else if (this.t % 12 !== 8) return;
          const simSecond = this.aliveCount < 2 ? 0 : this.terr[this.rank[1]];
          // —— 线上引擎 bD.gv.mf() 在组队局的写法 ——
          const left = teamsLeft(this);
          const engSecond = this.aliveCount < 2 ? 0 : left > 1 ? 1 : 0;
          scanReached++;
          if (!simSecond !== !engSecond && scanNotes.length < 400) scanNotes.push({ t: this.t, n, alive: this.aliveCount, simSecond, teamsLeft: left });
          const second = fixScan ? engSecond : simSecond;
          if (!second) {
            this.scanPos = this.scanPass = 0;
            this.scanLen = 0;
            this.scanSeen = 0;
          }
        };
      } else {
        // 不换规则：原样调用，调用完按同样的分支条件判断这一拍有没有走到那一步（只读）
        g.scanTick = function () {
          const pass0 = this.scanPass, seen0 = this.scanSeen, len0 = this.scanLen;
          const left = this.teamGame && pass0 >= 300 ? teamsLeft(this) : 0;
          const simSecond = this.aliveCount < 2 ? 0 : this.terr[this.rank[1]];
          scan0.call(this);
          if (!this.teamGame || pass0 < 300) return;
          const reset = this.scanPass === 0;
          const n = reset ? -1 : this.scanLen;
          let reached;
          if (reset) reached = true;
          else if (n >= 512) reached = false;
          else reached = n ? (this.t % 350 === 1 && seen0 === n && this.isBot(this.rank[0])) : this.t % 12 === 8;
          if (!reached) return;
          scanReached++;
          const engSecond = this.aliveCount < 2 ? 0 : left > 1 ? 1 : 0;
          if (!simSecond !== !engSecond && scanNotes.length < 400) scanNotes.push({ t: this.t, n: reset ? len0 : n, alive: this.aliveCount, simSecond, teamsLeft: left });
        };
      }
      const land0 = g.landAt;
      g.landAt = function (p, troops, c, at) {
        const v = this.px[c];
        if (v === T_LAND || v >= P_INNER) return land0.call(this, p, troops, c, at);
        if (v === undefined) {
          // 图外：原样交给模拟器（它会挂成对 0 号的进攻），只记一笔
          if (boatNotes.length < 400) {
            boatNotes.push({ t: this.t, p, troops, c, at, v: null, target: 0, enemy: this.isEnemy(p, 0) ? 1 : 0, tAlive: this.alive[0] ? 1 : 0, tTerr: this.terr[0],
              bal0: this.bal[p], debt0: this.debt[p], hadAtk0: this.hasAttack(p, 0) ? 1 : 0, freeSlot: this.hasFreeSlot(p) ? 1 : 0, how: '图外：模拟器原样处理（读成 0 号）' });
          }
          return land0.call(this, p, troops, c, at);
        }
        // 线上引擎 acN：这一格不是无主地 → k3 = ad.fR(这一格)
        const target = (v & 3) << 3;
        const enemy = this.isEnemy(p, target);
        const note = { t: this.t, p, troops, c, at, v, target, enemy: enemy ? 1 : 0,
          tAlive: this.alive[target] ? 1 : 0, tTerr: this.terr[target], bal0: this.bal[p], debt0: this.debt[p], how: null };
        if (boatNotes.length < 400) boatNotes.push(note);
        if (!fixBoat) { note.how = '模拟器：直接返回'; return land0.call(this, p, troops, c, at); }
        if (target === p) {
          note.how = '读出来是自己：兵退回';
          this.addBalance(p, troops);
          return;
        }
        if (!enemy) {
          const room = this.receiverRoom(target, troops);
          note.how = room >= 1 ? `不敌对：转交 ${room}` : '不敌对：对方收不下，兵作废';
          if (room >= 1 && this.bookDonation(target, room)) this.addBalance(target, room);
          return;
        }
        if (this.hasAttack(p, target) || this.hasFreeSlot(p)) {
          note.how = '敌对：挂成进攻';
          this.front[p].push(at);
          this.addAttack(p, troops, target);
          this.schedule(p, true);
        } else note.how = '敌对：没有空的进攻栏';
      };
    },
    onTick: (g) => {
      if (g.t % 10 === 0) {
        const A = g.terr, B = g.bal;
        let h = refHash;
        for (let p = 0; p < 512; p++) { h = Math.imul(h ^ A[p], 16777619); h = Math.imul(h ^ B[p], 16777619); }
        refHash = h >>> 0;
        refHashN++;
      }
      // 这几艘船：把之后 8 拍船主的余额、对那个号的进攻、欠账记下来（看兵有没有退回、哪一拍退回、是不是拿去还了欠账）
      for (const b of boatNotes) {
        if (g.t - b.t < 1 || g.t - b.t > 8) continue;
        (b.after = b.after || []).push([g.t, g.bal[b.p], g.attackTroopsOn(b.p, b.target), g.debt[b.p]]);
      }
      if (hk && hk.spans.some(([a, b]) => g.t >= a && g.t <= b)) {
        let s = 0;
        for (let i = 0; i < g.scanLen; i++) s = (s * 31 + g.scanBuf[i]) % MOD;
        let rs = 0;
        for (const r of g.routes) rs = (rs * 31 + r[0] * 7 + r[r.length - 1] * 3 + r.length) % MOD;
        husk.push([g.t, g.rng.half(), g.scanLen, s, g.routes.length, rs, Number(g.endgameFast), g.boatN, g.bal[hk.P], g.boatCount[hk.P]]);
      }
    },
  });
  const v = X.validate;
  const byBot = {};
  for (const m of v.mism) byBot[m[1]] = (byBot[m[1]] || 0) + 1;
  return { matchId: mid, arm, H: X.H, nTeams: X.nTeams, teamGame: G.teamGame ? 1 : 0, endTick: G.t, over: G.over ? 1 : 0,
    val: { rows: v.rows, both: v.bothExact, terr: v.terrExact, bal: v.balExact },
    firstMism: v.mism.length ? v.mism[0] : null, mismBots: byBot,
    events: X.engineEvents || [], refHash, refHashN, scanReached, scanNotes, boatNotes, husk: hk ? { P: hk.P, rows: husk } : null };
}

fs.mkdirSync(OUT, { recursive: true });
let done = 0;
outer:
for (const mid of mids) {
  for (const arm of arms) {
    const fp = path.join(OUT, `${mid}.${arm}.json`);
    if (fs.existsSync(fp)) continue;
    if (done && (Date.now() - T0) / 1000 > budget) break outer;
    const mark = path.join(OUT, `${mid}.${arm}.started`);
    fs.writeFileSync(mark, String(Date.now()));
    const t1 = Date.now();
    const R = probe(mid, arm);
    R.sec = Math.round((Date.now() - t1) / 100) / 10;
    fs.writeFileSync(fp, JSON.stringify(R));
    fs.unlinkSync(mark);
    done++;
    console.log(`${mid} ${arm} 到 ${R.endTick} 拍 ${R.sec}s 核对 ${R.val.both}/${R.val.rows}${R.firstMism ? ` 第一处不一致 t=${R.firstMism[0]}` : ''} 校验和 ${R.refHash} `
      + `扫描表规则不同 ${R.scanNotes.length} 次（走到那一步 ${R.scanReached} 次） 靠在不是地的格上的船 ${R.boatNotes.length} 艘`);
  }
}
console.log(`FIXPROBE ${done} 份，用时 ${Math.round((Date.now() - T0) / 1000)}s`);
