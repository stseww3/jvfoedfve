// sandbox.mjs — 把线上策略文件原样装进模拟器：编译一次，每个席位一份「浏览器页面」（window、墙钟、g 视图）。
//
// 策略文件按线上的写法读取：两行 import（sim/index.js、sim/map.js）换成注入的模块，export 去掉，整个文件体放进
// 一个函数里执行，函数的形参 window / performance / Date 是本文件的替身：
//   · window      读写都落到「当前席位」的页面对象上（__tsbSquadSlot、__quitPlayers、__hlLog、dictionary …），席位之间互不可见；
//   · performance.now() / Date.now()   返回当前席位的虚拟墙钟 = 56 ms × 服务器拍（本机拍 + 落后拍数），不是真实时间。
// 策略拿到的 g 是世界对象的一个「视图」（Object.create(world)）：读状态直接读世界；发指令的方法被换成通道层的提交；
// g.online 恒为 true；策略往 g 上写的缓存（如 g._wildAlive）落在视图自己身上，一个页面一份。
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { pathToFileURL } from 'node:url';
import { DATA, SIM, NEUTRAL, iV } from './tgame.mjs';

const MAP_MOD = await import(path.join(DATA, 'src/sim/sim/map.js'));
const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor;

// ---- 当前席位（所有策略共用的替身都读它）-------------------------------------------------------
const CUR = { win: {}, clock: 0 };
const EPOCH = 1700000000000;
const windowProxy = new Proxy({}, {
  get(_, k) { return CUR.win[k]; },
  set(_, k, v) { CUR.win[k] = v; return true; },
  has(_, k) { return k in CUR.win; },
  deleteProperty(_, k) { delete CUR.win[k]; return true; },
  ownKeys() { return Reflect.ownKeys(CUR.win); },
  getOwnPropertyDescriptor(_, k) { const d = Object.getOwnPropertyDescriptor(CUR.win, k); if (d) d.configurable = true; return d; },
});
const perfShim = { now: () => CUR.clock };
const RealDate = Date;
function DateShim(...a) { return new.target ? new RealDate(...(a.length ? a : [EPOCH + CUR.clock])) : new RealDate(EPOCH + CUR.clock).toString(); }
DateShim.now = () => EPOCH + Math.floor(CUR.clock);
DateShim.parse = RealDate.parse; DateShim.UTC = RealDate.UTC;

export function enter(win, clockMs) { CUR.win = win; CUR.clock = clockMs; }
export function leaveSeat() { CUR.win = BLANK_WIN; }
const BLANK_WIN = {};

// ---- 编译 ----------------------------------------------------------------------------------
const compiled = new Map();
// 一个进程里连着跑多次运行（tools/g0_batch.mjs）时，每次运行之前清掉：策略文件体重新执行一遍，
// 文件里模块级的变量就和单独起一个进程时一样是全新的，上一次运行留不下任何东西。
export function resetCompiled() { compiled.clear(); }
export async function compileStrategy(file) {
  const abs = strategyPath(file);   // 只编译白名单里的历史策略（内容散列核对过）
  if (compiled.has(abs)) return compiled.get(abs);
  let src = fs.readFileSync(abs, 'utf8');
  const mods = [];
  const pending = [];
  src = src.replace(/^[ \t]*import\s+([^;'"]+?)\s+from\s+["']([^"']+)["'];?[ \t]*$/gm, (m, what, spec) => {
    let ref;
    if (/sim\/index\.js$/.test(spec)) ref = '__tsbSim';
    else if (/sim\/map\.js$/.test(spec)) ref = '__tsbMap';
    else {
      ref = `__mods[${mods.length}]`;
      mods.push(null);
      const at = mods.length - 1;
      const target = spec.startsWith('.') ? pathToFileURL(path.resolve(path.dirname(abs), spec)).href : spec;
      pending.push(import(target).then((mod) => { mods[at] = mod; }));
    }
    what = what.trim();
    const out = [];
    let rest = what;
    const brace = rest.match(/\{([^}]*)\}/);
    if (brace) {
      out.push(`const {${brace[1].replace(/\s+as\s+/g, ': ')}} = ${ref};`);
      rest = rest.replace(brace[0], '').replace(/,\s*$/, '').replace(/^\s*,/, '').trim();
    }
    const star = rest.match(/\*\s*as\s+([\w$]+)/);
    if (star) { out.push(`const ${star[1]} = ${ref};`); rest = rest.replace(star[0], '').replace(/,/g, '').trim(); }
    if (rest) out.push(`const ${rest.replace(/,/g, '').trim()} = ${ref}.default;`);
    return out.join(' ');
  });
  await Promise.all(pending);
  src = src.replace(/^[ \t]*import\s+["'][^"']+["'];?[ \t]*$/gm, '');
  src = src.replace(/^([ \t]*)export\s+default\s+/gm, '$1const __default = ');
  src = src.replace(/^([ \t]*)export\s+(?=(?:const|let|var|class|function|async)\b)/gm, '$1');
  src = src.replace(/^[ \t]*export\s*\{[^}]*\};?[ \t]*$/gm, '');
  const body = `"use strict";\n${src}\nreturn { Policy: typeof Policy !== "undefined" ? Policy : (typeof __default !== "undefined" ? __default : undefined), PARAMS: typeof PARAMS !== "undefined" ? PARAMS : {} };`;
  let fn;
  try {
    fn = new AsyncFunction('__tsbSim', '__tsbMap', '__mods', 'window', 'performance', 'Date', body);
  } catch (err) {
    throw new Error(`策略文件 ${abs} 编译失败：${err.message}`);
  }
  CUR.win = {}; CUR.clock = 0;
  const res = await fn(SIM, MAP_MOD, mods, windowProxy, perfShim, DateShim);
  if (typeof res.Policy !== 'function') throw new Error(`策略文件 ${abs} 里没有 Policy 类`);
  // 策略文件自带的桥接补丁（c110 文件头）：发出一条指令后，450 ms 且 8 个本机拍之内不再调策略
  const guard = /__fixedInflight450/.test(src) ? { ticks: 8, ms: 450 } : null;
  const sha256 = crypto.createHash('sha256').update(fs.readFileSync(abs)).digest('hex');
  const out = { file: abs, name: path.basename(abs).replace(/\.m?js$/, ''), sha256, Policy: res.Policy, PARAMS: res.PARAMS, guard };
  compiled.set(abs, out);
  return out;
}

// 策略白名单（v2.1 纯离线范围）：只装数据包里当年线上跑过、且有录像可核对的四个历史版本，按内容散列核对；
// 其余任何文件（包括改过的历史文件、新写的策略）一律拒绝。这个模拟器只用来验收「离线模拟器把历史旧策略复现得对不对」。
const HISTORICAL = {
  va: ['v27-team-c116-va.js', 'a652ad88d80c818e9e7cc1660b9f4e4f792fc2d832252c369e5d30335743b488'],
  vb: ['v27-team-c116-vb.js', 'f5ccf9806cc4380f36b3104681353b342a22338996832aa92388e4beebc43fb1'],
  vc: ['v27-team-c116.js', '164e4c46a26799800b7e99cf63f8051bf55703748e16791efc06e0faaeaacf93'],
  c110: ['v27-team-c110.js', '7863ad706df61ead16b007bd9205b358ee9980193293aabd40df16c5e38e2657'],
};
const ALIAS = { c116: 'vc' };
const REFUSE = '纯离线范围：只接受历史旧策略 va / vb / vc / c110（数据包 src/strategy 下的原文件），不装载其他策略文件';
export function strategyPath(s) {
  let k = String(s).toLowerCase().trim();
  k = ALIAS[k] || k;
  if (!HISTORICAL[k]) {
    const base = path.basename(String(s));
    k = Object.keys(HISTORICAL).find((x) => HISTORICAL[x][0] === base && path.resolve(String(s)) === path.join(DATA, 'src/strategy', base));
    if (!k) throw new Error(`${REFUSE}（收到：${s}）`);
  }
  const file = path.join(DATA, 'src/strategy', HISTORICAL[k][0]);
  const sha = crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
  if (sha !== HISTORICAL[k][1]) throw new Error(`${REFUSE}（${file} 的内容与入库时的历史文件不一致：sha256 ${sha.slice(0, 12)}…）`);
  return file;
}
export const HISTORICAL_STRATEGIES = Object.fromEntries(Object.entries(HISTORICAL).map(([k, v]) => [k, { file: v[0], sha256: v[1] }]));

// 已停用的开关（v2.1 纯离线范围）。给了就报错退出，不悄悄忽略：
//   处理臂、策略参数覆盖、改桥接保护窗（都是「换一种我方打法」）；给我方席位改战队标签、生成房间、人为指定我方空壳（都不是历史上发生过的房间）。
export function refuseOutOfScope(o, own) {
  const bad = ['candidate', 'cand-params', 'base-params', 'squad-husks', 'tag-name', 'pool', 'clans', 'teams', 'humans', 'squad', 'map'].filter((k) => o[k] !== undefined);
  if (o.arm !== undefined && o.arm !== 'baseline') bad.push(`arm ${o.arm}`);
  if (o['inflight-guard'] !== undefined && o['inflight-guard'] !== 'auto') bad.push(`inflight-guard ${o['inflight-guard']}`);
  if (o.tag !== undefined && o.tag !== 'asis') bad.push(`tag ${o.tag}`);
  if (o.room === 'synth') bad.push('room synth');
  if (bad.length) throw new Error(`纯离线范围：--${bad.join(' / --')} 已停用。本工具只在历史上真实发生过的房间里跑一条复现臂（这一局当年线上那一版历史策略、文件里的原参数），不比较候选策略、不改策略参数或桥接补丁、不改房间`);
  // 复现臂只能是这一局当年线上那一版：换成别的历史版本就没有录像可核对，不属于保真度验收
  if (own && o.baseline !== undefined) {
    const k = String(o.baseline).toLowerCase().trim();
    const want = { c116: 'vc' }[k] || k;
    if (want !== own && path.basename(String(o.baseline)) !== HISTORICAL[own]?.[0]) throw new Error(`纯离线范围：这一局当年线上跑的是 ${own}，复现臂只能是它（收到 --baseline ${o.baseline}）`);
  }
}

// ---- 席位 ----------------------------------------------------------------------------------
// host 要提供：world、chan（通道）、quit（Set：已离场的席位）、onLog(seat, line)、opts
const VIEW_KEEP = new Set(['me', 'online', 'attack', 'boat', 'boatTo', 'donate', 'retreat', 'chase', 'recall', 'clone', 'leave']);

export class Seat {
  constructor(host, p, slot, strat, params) {
    this.host = host;
    this.p = p;
    this.slot = slot;
    this.strat = strat;
    this.live = false;       // false = 影子（指令只做本地预检，不进通道）
    this.sentAt = -1;        // 最近一次受理指令的拍号
    this.sentClock = -1e9;   // 那一刻的虚拟墙钟（ms）
    this.clock = 0;
    this.guarded = 0;        // 被在途保护跳过的决策次数
    this.errors = 0;
    this.firstError = '';
    this.acts = 0;
    this.issued = 0;         // 策略得到 true 的指令条数（策略自己数的 cmds）
    this.refused = 0;        // 同一决策拍第 2 条起被拒的条数
    this.logTags = new Map();
    this.logLines = host.opts.keepLogs ? [] : null;
    this.left = false;
    const seat = this;
    this.win = {
      __tsbSquadSlot: slot,
      __quitPlayers: host.quit,
      __hlLog: (line) => seat.onLog(line),
      dictionary: { game: '__v2game', sbLeave: 'leave', gameState: 'state' },
      __v2game: { state: 1, leave: () => seat.submit({ k: 'leave' }) },
    };
    if (host.opts.aoPct !== undefined && host.opts.aoPct !== null) {
      // 引擎界面侧的捐款预检 ao.iD(q)：按界面滑杆的比例（不是这条捐款的比例）算一笔，问接收方配额够不够；不记账
      const uiPct = host.opts.aoPct;
      this.win.ao = {
        iD: (q) => {
          const w = host.world;
          if (!w.teamGame || !w.canAct(p) || q === p || q >= NEUTRAL || !w.alive[q] || !w.isTeammate(p, q)) return false;
          const B = w.bal[p], fee = iV(64 * B, 1024);
          let v = Math.min(iV(B * (uiPct + 1), 1024), B - fee);
          v = w.receiverRoom(q, v);
          return v >= 1 && w.canReceive(q, v);
        },
      };
    }
    this.pol = new strat.Policy(params || {}, p);
    this.view = this.makeView();
  }

  onLog(line) {
    const m = /^\[([A-Z0-9-]+)\]/.exec(line);
    const tag = m ? m[1] : '?';
    this.logTags.set(tag, (this.logTags.get(tag) || 0) + 1);
    if (this.logLines && this.logLines.length < 4000) this.logLines.push(line);
    if (this.host.onLog) this.host.onLog(this, tag, line);
  }

  // 一条指令从策略手里出来。返回策略看到的返回值。
  submit(cmd) {
    const host = this.host, w = host.world;
    if (this.sentAt === w.t && !host.chan.multi) { this.refused++; return false; }
    if (!this.live) { this.sentAt = w.t; this.sentClock = this.clock; this.issued++; if (host.onShadow) host.onShadow(this, cmd); return true; }
    const ok = host.chan.submit(this, cmd);
    if (ok) { this.sentAt = w.t; this.sentClock = this.clock; this.issued++; }
    return ok;
  }

  makeView() {
    const seat = this, host = this.host, me = this.p;
    const v = Object.create(host.world);
    v.me = me;
    v.online = true;
    v.attack = (pct, target, p = me) => {
      const w = host.world;
      if (p !== me || !w.canAct(me) || me === target) return false;
      pct = Math.max(0, Math.min(1023, pct | 0));
      if (!(w.quote(me, pct, 12) >= 0)) return false;
      target = Math.min(target, NEUTRAL);
      if (target < NEUTRAL && w.alive[target] === 0) target = NEUTRAL;
      if (target < NEUTRAL && !w.isEnemy(me, target)) return false;
      if (!w.hasAttack(me, target) && !w.hasFreeSlot(me)) return false;
      return seat.submit({ k: 'atk', pct, to: target, amt: iV(w.bal[me] * (pct + 1), 1024) });
    };
    v.boat = (pct, water, dir, p = me) => {
      const w = host.world;
      if (p !== me || !w.canAct(me) || !w.boatsAllowed(me)) return false;
      pct = Math.max(0, Math.min(1023, pct | 0));
      if (!(w.quote(me, pct, 32) >= 0)) return false;
      const dest = water + w.dir4[dir & 3];
      const to = dest >= 0 && dest < w.N && w.px[dest] >= 16 ? w.own[dest] : NEUTRAL;
      return seat.submit({ k: 'boat', pct, water, dir, to, amt: iV(w.bal[me] * (pct + 1), 1024) });
    };
    v.boatTo = (pct, target, p = me, radius = 32) => {
      const w = host.world;
      if (p !== me || !w.canAct(me) || !w.boatsAllowed(me)) return false;
      const s = w.boatSpot(target, me, radius);
      if (s === null) return false;
      pct = Math.max(0, Math.min(1023, pct | 0));
      if (!(w.quote(me, pct, 32) >= 0)) return false;
      const to = w.px[target] >= 16 ? w.own[target] : NEUTRAL;
      return seat.submit({ k: 'boat', pct, water: s.water, dir: s.dir, to, tile: target, amt: iV(w.bal[me] * (pct + 1), 1024) });
    };
    v.donate = (pct, q, p = me) => {
      const w = host.world;
      if (p !== me || !w.teamGame || !w.canAct(me) || q === me) return false;
      q = Math.min(q, NEUTRAL);
      if (q >= NEUTRAL || w.alive[q] === 0 || !w.isTeammate(me, q)) return false;
      pct = Math.max(0, Math.min(1023, pct | 0));
      const B = w.bal[me], fee = iV(64 * B, 1024);
      const want = Math.min(iV(B * (pct + 1), 1024), B - fee);
      if (host.opts.donateSubmit === 'quote') {
        // 旧门禁的口径：提交时就按当时的配额判成败（线上没有这个回执）
        if (!(w.donateQuote(pct, q, me) > 0)) return false;
      } else if (!(want >= 1)) return false;
      return seat.submit({ k: 'don', pct, to: q, amt: Math.max(0, want) });
    };
    v.retreat = (target, p = me) => {
      const w = host.world;
      if (p !== me || !w.canAct(me)) return false;
      target = Math.min(target, NEUTRAL);
      if (!w.hasAttack(me, target)) return false;
      return seat.submit({ k: 'ret', to: target });
    };
    v.chase = (a, b, p = me) => {
      const w = host.world;
      if (p !== me || !w.canAct(me)) return false;
      return seat.submit({ k: 'chase', a, b });
    };
    v.recall = (b, p = me) => {
      const w = host.world;
      if (p !== me || !w.canAct(me)) return false;
      return seat.submit({ k: 'recall', b });
    };
    v.leave = () => false;
    v.clone = () => host.world.clone();
    return v;
  }

  // 让策略在世界的当前拍决策一次
  act(clockMs) {
    CUR.win = this.win; CUR.clock = clockMs;
    this.clock = clockMs;
    this.acts++;
    try {
      this.pol.act(this.view);
    } catch (err) {
      if (!this.errors++) this.firstError = `t=${this.host.world.t} ${err && err.stack ? err.stack.split('\n').slice(0, 3).join(' | ') : err}`;
    }
    // 引擎方法经视图调用时写下的草稿标量（attackTroopsTmp 之类）会留在视图上盖住世界的同名字段：每拍清掉；
    // 策略自己挂的缓存（下划线开头）留着，一个页面一份。
    const view = this.view;
    for (const k of Object.keys(view)) {
      if (VIEW_KEEP.has(k) || k.charCodeAt(0) === 95) continue;
      delete view[k];
      if (this.host.viewWrites) this.host.viewWrites.add(k);
    }
  }

  // 出生阶段：让策略选一次落点。返回 {x, y} 或 null（策略没有 chooseSpawn、或这次没给出落点）
  chooseSpawn(clockMs, final) {
    CUR.win = this.win; CUR.clock = clockMs;
    this.clock = clockMs;
    if (typeof this.pol.chooseSpawn !== 'function') return null;
    try {
      const r = this.pol.chooseSpawn(this.view, final);
      return r && Number.isFinite(r.x) && Number.isFinite(r.y) ? { x: r.x | 0, y: r.y | 0 } : null;
    } catch (err) {
      if (!this.errors++) this.firstError = `spawn ${err && err.stack ? err.stack.split('\n').slice(0, 3).join(' | ') : err}`;
      return null;
    }
  }

  retarget(world) { Object.setPrototypeOf(this.view, world); }
}

export { CUR };
