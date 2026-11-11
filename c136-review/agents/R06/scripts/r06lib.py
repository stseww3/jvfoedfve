#!/usr/bin/env python3
"""r06lib.py — R06 的对局包解析库（按局内玩家号 me 归并，不按名字）。

为什么不直接用包里的 traj.csv / stories：那些表按日志前缀的「名字」分号，而名字在局内会被改（离开、重连后重抽），
同一个玩家会被拆成两个「号」。这里统一用 [HL-GAME-INIT] 的 me=N、results.csv 的 meId、录像头的玩家序号归并。

主要入口：
    M = load_match('B039')           # 解析日志、结算、录像（含同局对手包的更完整录像）、重算全员队号
    M.bots[me]                        # 我方每个号：名字、轨迹、事件、结算
    M.cmds                            # 录像里全部「已被引擎接受」的指令（陆攻/捐款/发船/撤回/离开），带拍号
引擎公式（来源 /agent/repos/c136-data/src/engine/engine-evidence.txt、live-donation-check.txt）也放在这里：
    donation_fee(B) = floor(64B/1024)；donation_amount(B,pct) = min(floor(B(pct+1)/1024), B-fee)
    quota_limit(t)、quota_points(t, v, mapLand, recvTerr)、interest_rate(t, terr, land, bal)
"""
import csv
import json
import os
import re
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.normpath(os.path.join(HERE, '..', 'out'))
DATA = '/agent/repos/c136-data/bundles'

import sys
sys.path.insert(0, HERE)
from team_assign import assign_teams, clan_tag  # noqa: E402

# 同一局被两个编队各录了一份时，取对手包里更完整的录像（只限发现集 bundles/ 里的包）
PEER_REPLAY = {'B039': 'A058', 'B038': 'A057'}

RE_LINE = re.compile(r'^(\d+)\t\[(.+?)\] \[(HL-[A-Z-]+)\] (.*)$')
RE_RESULT = re.compile(r'^(\d+)\t\[RESULT (.+?)\] result=(\S+) event=(\S+) place=(\S+) peak=(\S+) team=(.*)$')
RE_TICK = re.compile(r't=(\d+) terr=(\d+)\(([\d.]+)%\) bal=(\d+) dens=([\d.]+) nb=(\d+) neut=(\d+) cmds=(\d+) boats=(\d+)(?: avgMs=([\d.]+) maxMs=([\d.]+) skip=(\d+))?')
RE_INIT = re.compile(r'mode=(\d+) map=(\d+) mapSeed=(\d+) seeded=(\d+) me=(\d+)')
RE_SPAWN = re.compile(r'me=(\d+) slot=(\d+) \(squad=(\d+),rankIdx=(-?\d+)\) -> \((\d+),(\d+)\)(?: chosenSlots=(\d+)/(\d+))?(?: minSep=(\d+))?')
RE_OPEN = re.compile(r't=(\d+) cyc=(\d+) DP expand rings=(\d+) spend=(\d+)/(\d+) terr=(\d+)')
RE_DON = re.compile(r't=(\d+) (squad rescue donate|surplus donate|boss donate) pct=(\d+)/1024 -> (?:ally|boss)=(\d+)\((.*?)\)(?: boxedIn=(true|false))? myBal=(\d+) dMe=(\d+)(?: dAlly=(\d+))?')
RE_AST = re.compile(r't=(\d+) 10% squad-rescue poke -> enemy=(\d+)\((.*?)\) for ally=(\d+)\((.*?)\)$')
RE_SLOW = re.compile(r't=(\d+) took ([\d.]+)ms')


# ---------------------------------------------------------------- 引擎公式
def donation_fee(B):
    return (64 * B) // 1024


def donation_amount(B, pct):
    return max(0, min((B * (pct + 1)) // 1024, B - donation_fee(B)))


def donation_efficiency(pct):
    """到账 / (到账 + 手续费)，对方有空间、pct<=959 时成立。"""
    return (pct + 1) / (pct + 65)


def attack_fee(B):
    return (12 * B) // 1024


def attack_amount(B, pct):
    return max(0, min((B * (pct + 1)) // 1024, B - attack_fee(B)))


def quota_limit(t):
    """受捐额度上限（全场共用）：开局 15，每逢 tick%100==99 增加 4 / 6 / 8 / 10。t>=4284 不再检查。"""
    lim = 15
    k = 99
    while k <= t:
        lim += 4 if k < 1071 else 6 if k < 2142 else 8 if k < 3213 else 10
        k += 100
    return lim


def quota_points(t, v, map_land, recv_terr):
    """一笔到账 v 的捐款消耗的额度点。t>=4284 返回 0（不检查）。"""
    if t >= 4284:
        return 0
    uv = 1 + map_land // 300
    if t < 357:
        return 2 + (100 * v) // uv
    if t < 714:
        return 2 + (100 * v) // (4 * uv)
    if t < 1071:
        return 2 + (100 * v) // (10 * uv)
    if t < 2142:
        return 2 + (100 * v) // (30 * uv)
    if t < 3213:
        return 2 + (100 * v) // (100 * uv)
    return 4 + (100 * v) // max(1, min(100 * recv_terr, 10 ** 9))


def isqrt(n):
    import math
    return math.isqrt(max(0, int(n)))


def interest_rate(t, terr, land, bal):
    """每 10 拍的利率（万分比）。"""
    i = (511 * terr) // max(1, land)
    r = 100 + isqrt(25600 * i // 508)
    if t < 1920:
        r = max((100 * (13440 - 6 * t)) // 1920, r)
    cap = min(100 * terr, 10 ** 9)
    if bal > cap and cap > 0:
        r -= (2 * r * (bal - cap)) // cap
    return max(0, r)


# ---------------------------------------------------------------- 数据结构
class Bot:
    def __init__(self, me):
        self.me = me
        self.names = []          # 局内先后用过的名字
        self.init = None
        self.spawns = []         # HL-SPAWN 各次选点
        self.opening = []        # HL-OPENING
        self.traj = []           # HL-TICK 快照（按 t 排序去重）
        self.donations = []      # 我发出的捐款日志
        self.assists = []        # 我发出的协防戳
        self.slow = []
        self.result = None       # results.csv 的行（dict）
        self.team = None         # 重算或观察到的队号
        self.teamObserved = None

    @property
    def name(self):
        return self.names[0] if self.names else f'#{self.me}'

    def last(self):
        return self.traj[-1] if self.traj else None

    def at(self, t, max_age=None):
        """t 拍及之前最近的一条快照。"""
        best = None
        for s in self.traj:
            if s['t'] <= t:
                best = s
            else:
                break
        if best is None or (max_age is not None and t - best['t'] > max_age):
            return None
        return best

    def end_tick(self):
        """这个号最后出现在数据里的拍：结算拍（离开的号结算拍不可靠，取快照）或最后快照。"""
        lt = self.traj[-1]['t'] if self.traj else 0
        if self.result and self.result['event'] in ('died', 'end'):
            return max(lt, int(self.result['tick']))
        return lt


class Match:
    pass


def _num(x, d=None):
    try:
        return int(x)
    except Exception:
        try:
            return float(x)
        except Exception:
            return d


def load_match(mid, with_replay=True, use_sim=True):
    M = Match()
    M.id = mid
    base = os.path.join(DATA, mid)
    M.card = json.load(open(os.path.join(base, 'card.json')))
    M.land = M.card['mapLand']
    M.endTick = M.card['outcome']['endTick']
    M.bots = {}
    name2me = {}
    pending = []       # 暂时解析不出 me 的行
    M.results_log = []  # 日志里的 [RESULT …] 行（带队伍领土表）
    M.peace = []
    M.other = []
    rows = []
    with open(os.path.join(base, 'in_game.log'), encoding='utf8', errors='replace') as f:
        for raw in f:
            raw = raw.rstrip('\n')
            m = RE_LINE.match(raw)
            if m:
                rows.append((int(m.group(1)), m.group(2), m.group(3), m.group(4)))
                continue
            m = RE_RESULT.match(raw)
            if m:
                try:
                    team = json.loads(m.group(7))
                except Exception:
                    team = None
                M.results_log.append(dict(line=int(m.group(1)), name=m.group(2), result=m.group(3), event=m.group(4),
                                          place=_num(m.group(5)), peak=_num(m.group(6)), team=team))
                continue
            M.other.append(raw)
    # 第一遍：名字 → me
    for line, name, tag, rest in rows:
        if tag == 'HL-GAME-INIT':
            mm = RE_INIT.search(rest)
            if mm:
                me = int(mm.group(5))
                name2me.setdefault(name, me)
                b = M.bots.setdefault(me, Bot(me))
                if name not in b.names:
                    b.names.append(name)
                b.init = dict(line=line, mode=int(mm.group(1)), map=int(mm.group(2)), mapSeed=int(mm.group(3)), seeded=int(mm.group(4)))
        elif tag == 'HL-SPAWN':
            mm = RE_SPAWN.search(rest)
            if mm:
                me = int(mm.group(1))
                name2me.setdefault(name, me)
                b = M.bots.setdefault(me, Bot(me))
                if name not in b.names:
                    b.names.append(name)
    # 结算表
    M.results = []
    with open(os.path.join(base, 'results.csv')) as f:
        for r in csv.DictReader(f):
            r['tick'] = _num(r['tick'], 0)
            r['meId'] = _num(r['meId'])
            for k in ('seconds', 'place', 'alivePlayers', 'territory', 'lastTerritory', 'lastRank', 'peak', 'land', 'balance', 'sent', 'accepted', 'teamMine', 'teamBest'):
                r[k] = _num(r.get(k))
            try:
                r['teamTotals'] = json.loads(r['teamTotals']) if r.get('teamTotals') else None
            except Exception:
                r['teamTotals'] = None
            M.results.append(r)
            if r['meId'] is not None:
                b = M.bots.setdefault(r['meId'], Bot(r['meId']))
                b.result = r
                b.teamObserved = r['teamMine']
                if r['bot'] not in b.names:
                    b.names.append(r['bot'])
                name2me.setdefault(r['bot'], r['meId'])
    M.name2me = name2me
    M.squadIds = sorted(set(name2me.values()))   # 只来自 HL-GAME-INIT / HL-SPAWN / results.csv 的 me（可靠）
    M.unresolved = defaultdict(list)
    # 原始快照行（不依赖名字归并；sim_prep.py 拿它去和重演逐行对指纹）
    M.tickRows = []
    for line, name, tag, rest in rows:
        if tag == 'HL-TICK':
            mm = RE_TICK.search(rest)
            if mm:
                M.tickRows.append(dict(line=line, name=name, t=int(mm.group(1)), terr=int(mm.group(2)), bal=int(mm.group(4))))
    # 有重演真值时：每条快照按 (拍, 领土, 兵力) 指纹在全体真人里找唯一对得上的玩家 → 这行日志是谁的（比名字可靠：
    # 名字局内会轮换、也会被别的号接着用）。同名的其它日志行按行号就近归到最近一条有指纹的快照。
    M.sim = None
    M.lineP = {}
    anchors = defaultdict(list)
    sp = os.path.join(OUT, mid, 'sim_state.json')
    if with_replay and use_sim and os.path.exists(sp):
        try:
            M.sim = json.load(open(sp))
        except Exception:
            M.sim = None
        if M.sim and M.sim.get('lineId') is not None:
            M.lineP = {int(k): v for k, v in M.sim['lineId'].items()}
            # 歧义行（同拍多个我方号状态完全相同）：名字对应的号在候选里就用它，否则不当锚点
            amb = {int(k): v for k, v in (M.sim.get('lineAmb') or {}).items()}
            for r in M.tickRows:
                c = amb.get(r['line'])
                if c and name2me.get(r['name']) in c:
                    M.lineP[r['line']] = name2me[r['name']]
            for r in M.tickRows:
                q = M.lineP.get(r['line'])
                if q is not None:
                    anchors[r['name']].append((r['line'], q))
            for nm in anchors:
                anchors[nm].sort()
    M.nameAnchors = anchors
    M.nameReuse = {nm: sorted(set(q for _, q in a)) for nm, a in anchors.items() if len(set(q for _, q in a)) > 1}
    import bisect

    def who(name, line):
        if line in M.lineP:
            return M.lineP[line]
        a = anchors.get(name)
        if a:
            i = bisect.bisect_right(a, (line, 1 << 30))
            prev = a[i - 1] if i > 0 else None
            nxt = a[i] if i < len(a) else None
            if prev and nxt:
                return prev[1] if (prev[1] == nxt[1] or line - prev[0] <= nxt[0] - line) else nxt[1]
            return (prev or nxt)[1]
        return name2me.get(name)

    M.who = who
    # 第二遍：事件
    for line, name, tag, rest in rows:
        me = who(name, line)
        if me is not None and me not in M.bots:
            M.bots[me] = Bot(me)
        if me is not None and name not in M.bots[me].names:
            M.bots[me].names.append(name)
        if tag == 'HL-TICK':
            mm = RE_TICK.search(rest)
            if not mm:
                continue
            s = dict(t=int(mm.group(1)), terr=int(mm.group(2)), pct=float(mm.group(3)), bal=int(mm.group(4)), dens=float(mm.group(5)),
                     nb=int(mm.group(6)), neut=int(mm.group(7)), cmds=int(mm.group(8)), boats=int(mm.group(9)),
                     maxMs=_num(mm.group(11), 0), skip=_num(mm.group(12), 0), line=line, name=name)
            if me is None:
                M.unresolved[name].append(('TICK', s))
            else:
                M.bots[me].traj.append(s)
        elif tag == 'HL-OPENING':
            mm = RE_OPEN.search(rest)
            if mm and me is not None:
                M.bots[me].opening.append(dict(t=int(mm.group(1)), cyc=int(mm.group(2)), rings=int(mm.group(3)), spend=int(mm.group(4)),
                                               bal=int(mm.group(5)), terr=int(mm.group(6)), line=line))
        elif tag == 'HL-SPAWN':
            mm = RE_SPAWN.search(rest)
            if mm:
                M.bots[int(mm.group(1))].spawns.append(dict(slot=int(mm.group(2)), squad=int(mm.group(3)), rankIdx=int(mm.group(4)),
                                                            x=int(mm.group(5)), y=int(mm.group(6)), chosen=_num(mm.group(7)), cand=_num(mm.group(8)),
                                                            minSep=_num(mm.group(9)), line=line))
        elif tag == 'HL-DONATE':
            mm = RE_DON.search(rest)
            if mm:
                e = dict(t=int(mm.group(1)), kind={'squad rescue donate': 'rescue', 'surplus donate': 'surplus', 'boss donate': 'boss'}[mm.group(2)],
                         pct=int(mm.group(3)), to=int(mm.group(4)), toName=mm.group(5), boxedIn=mm.group(6), myBal=int(mm.group(7)),
                         dMe=int(mm.group(8)), dAlly=_num(mm.group(9)), line=line, name=name)
                if me is None:
                    M.unresolved[name].append(('DONATE', e))
                else:
                    e['me'] = me
                    M.bots[me].donations.append(e)
        elif tag == 'HL-ASSIST':
            mm = RE_AST.search(rest)
            if mm:
                e = dict(t=int(mm.group(1)), enemy=int(mm.group(2)), enemyName=mm.group(3), ally=int(mm.group(4)), allyName=mm.group(5), line=line, name=name)
                if me is None:
                    M.unresolved[name].append(('ASSIST', e))
                else:
                    e['me'] = me
                    M.bots[me].assists.append(e)
        elif tag == 'HL-SLOW-TICK':
            mm = RE_SLOW.search(rest)
            if mm and me is not None:
                M.bots[me].slow.append((int(mm.group(1)), float(mm.group(2))))
        elif tag == 'HL-PEACE':
            M.peace.append((line, name, rest))
    # 解析不出 me 的名字：按「前一个号的快照到此为止、领土接得上」推断改名
    M.inferredRenames = []
    for name, items in list(M.unresolved.items()):
        ticks = [x[1] for x in items if x[0] == 'TICK']
        if not ticks:
            continue
        first = min(ticks, key=lambda s: s['t'])
        best, bestScore = None, None
        for me, b in M.bots.items():
            if not b.traj:
                continue
            prev = [s for s in b.traj if s['t'] < first['t']]
            later = [s for s in b.traj if s['t'] >= first['t']]
            if not prev or later:
                continue
            p = prev[-1]
            gap = first['t'] - p['t']
            if gap > 400:
                continue
            rel = abs(first['terr'] - p['terr']) / max(1, p['terr'])
            score = rel + gap / 4000
            if bestScore is None or score < bestScore:
                best, bestScore = me, score
        if best is not None and bestScore < 0.6:
            name2me[name] = best
            M.bots[best].names.append(name)
            M.inferredRenames.append((name, best, round(bestScore, 3)))
            for kind, e in items:
                if kind == 'TICK':
                    M.bots[best].traj.append(e)
                elif kind == 'DONATE':
                    e['me'] = best
                    M.bots[best].donations.append(e)
                elif kind == 'ASSIST':
                    e['me'] = best
                    M.bots[best].assists.append(e)
            del M.unresolved[name]
    for b in M.bots.values():
        seen = {}
        for s in sorted(b.traj, key=lambda s: (s['t'], s['line'])):
            seen[s['t']] = s
        b.traj = [seen[t] for t in sorted(seen)]
        b.donations.sort(key=lambda e: (e['t'], e['line']))
        b.assists.sort(key=lambda e: (e['t'], e['line']))
        b.opening.sort(key=lambda e: (e['t'], e['line']))
    M.squad = sorted(me for me, b in M.bots.items() if b.init is not None or b.traj or me in M.squadIds)
    # 队伍领土表（来自各号结算时刻）
    M.teamSnaps = []
    for r in M.results:
        if r.get('teamTotals'):
            tot = {int(k): v for k, v in r['teamTotals'].items()}
            M.teamSnaps.append(dict(t=r['tick'], totals=tot, by=r['bot'], mine=r['teamMine'], event=r['event']))
    M.teamSnaps.sort(key=lambda x: x['t'])
    # 录像
    M.replay = None
    M.cmds = []
    M.replaySrc = None
    M.replayLast = 0
    M.names = {}
    M.humans = M.card.get('seededPlayers')
    M.team = {}
    M.teamInfo = None
    M.spawnXY = {}
    M.mapW = None
    if with_replay:
        for src in (PEER_REPLAY.get(mid), mid):
            if not src:
                continue
            p = os.path.join(OUT, src, 'replay_decoded.json')
            if os.path.exists(p):
                d = json.load(open(p))
                if M.replay is None or d['lastTick'] > M.replay['lastTick']:
                    M.replay = d
                    M.replaySrc = src
        if M.replay:
            d = M.replay
            M.humans = d['settings']['humanCount']
            M.names = {i: n for i, n in enumerate(d['names'])}
            M.cmds = [c for c in d['cmds'] if c['phase'] == 'game']
            M.replayLast = d['lastTick'] if d['lastTick'] > 5 else 0
            if d.get('colors'):
                M.teamInfo = assign_teams(d['names'], d['colors'], M.humans, d['settings']['numberTeams'], d['settings']['playerCount'])
                M.team = {p: M.teamInfo['team'][p] for p in range(d['settings']['playerCount'])}
            # 出生点：每个玩家最后一次选点；地图宽度由我方日志坐标反推
            last_pick = {}
            for c in d['cmds']:
                if c['id'] == 0:
                    last_pick[c['player']] = c['dX']
            W = None
            for me, b in M.bots.items():
                if b.spawns and me in last_pick:
                    s = b.spawns[-1]
                    if s['y'] > 0 and (last_pick[me] - s['x']) % s['y'] == 0:
                        cand = (last_pick[me] - s['x']) // s['y']
                        if cand > s['x']:
                            W = cand if W is None else W
                            if cand != W:
                                W = min(W, cand)
            M.mapW = W
            if W:
                for p, idx in last_pick.items():
                    M.spawnXY[p] = (idx % W, idx // W)
            M.lastPick = last_pick
    for me, b in M.bots.items():
        b.team = M.team.get(me) or b.teamObserved
    return M


def pname(M, p):
    """玩家显示名：我方号加 *，内置 AI 标 bot。"""
    if p == 512:
        return '无主地'
    if p in M.bots:
        return f"*{M.bots[p].name}"
    if M.humans is not None and p >= M.humans:
        return f'bot{p}'
    return M.names.get(p, f'#{p}')


def pteam(M, p):
    return M.team.get(p, M.bots[p].team if p in M.bots else None)


def is_squad_name(name):
    """c110 的 isOurSquadBot 是按名字判的（名字池 + [NPL]/[NOPE]）。这里读源码首行的名字池。"""
    global _POOL
    try:
        _POOL
    except NameError:
        src = open('/agent/repos/c136-data/src/strategy/v27-team-c110.js', encoding='utf8').readline()
        _POOL = set(json.loads(src[src.index('['):src.rindex(']') + 1]))
    raw = (name or '').strip()
    return raw.lower() in _POOL or '[NPL]' in raw.upper() or '[NOPE]' in raw.upper()


def donation_truth(M, window=90, late_window=420):
    """把每条 HL-DONATE 日志和录像里的捐款指令（只有通过引擎全部校验的才会进录像）配对。
    返回列表：每条日志加上 accepted(True/False/None)、execT、延迟。录像没覆盖到的拍 → None。"""
    rep = defaultdict(list)
    for c in M.cmds:
        if c['id'] == 2:
            rep[c['player']].append(dict(t=c['t'], pct=c['dX'], to=c['dZ'], used=False))
    out = []
    for me in sorted(M.bots):
        for e in M.bots[me].donations:
            rec = dict(e)
            rec['accepted'] = None
            if M.replayLast and e['t'] + window <= M.replayLast:
                rec['accepted'] = False
                for x in rep.get(me, []):
                    if not x['used'] and x['pct'] == e['pct'] and x['to'] == e['to'] and 0 <= x['t'] - e['t'] <= window:
                        x['used'] = True
                        rec['accepted'] = True
                        rec['execT'] = x['t']
                        break
            out.append(rec)
    # 第二遍：客户端落后几百拍时，执行拍会比日志拍晚很多；把剩下没配上的录像捐款按顺序配给同号同 pct 同收款人的日志（最晚 late_window 拍）
    for rec in out:
        if rec['accepted'] is False:
            for x in rep.get(rec['me'], []):
                if not x['used'] and x['pct'] == rec['pct'] and x['to'] == rec['to'] and 0 <= x['t'] - rec['t'] <= late_window:
                    x['used'] = True
                    rec['accepted'] = True
                    rec['execT'] = x['t']
                    rec['late'] = True
                    break
    M.unloggedDonations = [(p, x) for p, xs in rep.items() if p in M.bots for x in xs if not x['used']]
    return out


def heuristic_rejected(M, me, e, horizon=40):
    """没有录像时判断一条捐款是否被拒：看同一个号在 horizon 拍内的下一次余额读数（下一条捐款日志的 myBal 或 HL-TICK 的 bal）。
    若被接受，余额应立即少掉 (pct+65)/1024；读数仍 >= 0.97×原余额 → 判为被拒。读不到 → None。"""
    b = M.bots[me]
    obs = []
    for d in b.donations:
        if e['t'] < d['t'] <= e['t'] + horizon:
            obs.append((d['t'], d['myBal']))
    for s in b.traj:
        if e['t'] < s['t'] <= e['t'] + horizon:
            obs.append((s['t'], s['bal']))
    if not obs:
        return None
    obs.sort()
    t, bal = obs[0]
    return bal >= 0.97 * e['myBal']
