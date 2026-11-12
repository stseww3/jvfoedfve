#!/usr/bin/env python3
"""patterns.py — R06 的跨局模式检测：对一批对局包机械计数（默认 = 发现集 bundles/ 下全部对局包）。

只用每个对局包都有的日志侧文件（in_game.log 里的 HL-TICK 快照 / 捐款行 / 协防行、results.csv、card.json、spawn.csv），
不需要录像，所以每一局都能跑。要录像才数得出的模式（确认窗内重复下单、同拍清仓批、safeFinite 参照我方号、保护名单围住的是谁）
不在这里，见 crossmatch.py（只覆盖 R06 复盘过、有录像的 9 局）。

用法：
  python3 patterns.py count   [--set S] [matchId ...]   每个模式：命中的局 / 号 / 实例，按分层列出
  python3 patterns.py hazard  [--set S]                  有邻居而零指令：命中后 600 拍内「阵亡或领土跌 >=25%」的比例，对同局同时段、在发令的对照快照
  python3 patterns.py overcap [--set S]                  超软上限且有邻居的快照：下一个间隔出手 / 不出手，之后的领土
  python3 patterns.py dump    [--set S]                  一个快照间隔里余额跌到纯利息预测的一半以下（清仓）：之后 300 拍内阵亡的比例，对照
  python3 patterns.py deaths  [--set S]                  阵亡的号：死前 >=450 拍零指令的占多少
  python3 patterns.py boxed   [--set S]                  被围（nb=0 且 neut=0）的时段：多长、其中超软上限 / 顶硬上限多少、发船换到地没有
  python3 patterns.py cost    [--set S]                  钱：超软上限少拿的利息、捐款手续费与各类捐款（日志侧估算）
  python3 patterns.py lag     [--set S]                  日志侧墙上时钟对表：哪些局在服务器拍 600~2100 有号落后 >=90 拍
  python3 patterns.py lagwho  [--set S]                  卡顿波核心时段（服务器拍 700~1750）的每条读数：这局有谁在场、当时还有哪些局在跑
  python3 patterns.py spawn   [--set S]                  选点：日志最后一个选点相距 <80 格的号对、每个号的选点日志条数
  python3 patterns.py split   [--set S]                  拆队与结果（card.json）
  python3 patterns.py list <模式> [--set S]             列出实例
  python3 patterns.py json    [--set S]                  写 out/_cross/patterns.json
  python3 patterns.py all     [--set S]
  --set：all（默认）｜mine（R06 复盘过的 15 局）｜rest（squad20 里 R06 没复盘过的）｜B｜A｜G
数据根目录 = 环境变量 R06_DATA（默认 /agent/repos/c136-data/bundles）；换到别的目录时「mine」分层自然为空。

分层：mine = R06 复盘过的 15 局（squad20，策略 c110）；B·其余 = 同编队 R06 没看过的局；A = squad10（c116 的 Va/Vb/Vc）；G = squad8（g09）。
模式是在 mine 上看出来的，所以 mine 的计数不算独立证据；B·其余 是同一份策略代码上的样本外计数；A / G 是别的策略版本，只当旁证。
统计单位是「局」：同一局里的号互相关联，按号 / 按快照合计的比例只作描述；推断只用按局配对的符号检验和以局为分层的 CMH。
"""
import csv
import json
import math
import os
import sys
from collections import defaultdict, OrderedDict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import r06lib            # noqa: E402
import logdigest as LD   # noqa: E402

sys.path.insert(0, '/agent/repos/c136-data/src/stats')
try:
    import stats as ST   # R10 的统计口径工具（Wilson、CMH）
except Exception:        # 没有这份工具时只打印计数
    ST = None

OUT = os.path.join(r06lib.OUT, '_cross')
MINE = ['B001', 'B002', 'B003', 'B010', 'B014', 'B017', 'B018', 'B021', 'B022', 'B023', 'B025', 'B038', 'B039', 'B041', 'B045']
LAYERS = ['mine', 'B·其余', 'A', 'G']
BANDS = ['630~1500', '1500~3000', '3000~4284', '>=4284']

PASSIVE_LEN = 450       # 零指令连续多少拍
HAZ_WIN = 600           # 之后看多少拍
HAZ_DROP = 0.75         # 领土跌到锚点的多少倍以下算「垮」
MIN_TERR = 200          # 太小的号不看（刚出生 / 只剩残地）
BOX_LEN = 180           # 被围连续多少拍
DUMP_BAL = 20000
DUMP_DROP = 0.5
DUMP_DEATH = 300
STACK_DIST = 80
CHURN_LINES = 8
LAG_TICKS = 90


def layer_of(mid, card):
    if mid in MINE:
        return 'mine'
    c = card.get('cohort')
    return {'squad20': 'B·其余', 'squad10': 'A', 'squad8': 'G'}.get(c, c or '?')


def band_of(t):
    return BANDS[0] if t < 1500 else BANDS[1] if t < 3000 else BANDS[2] if t < 4284 else BANDS[3]


def wan(x):
    if x is None:
        return '—'
    a = abs(x)
    if a >= 1e8:
        return f"{x / 1e8:.2f} 亿"
    if a >= 1e4:
        return f"{x / 1e4:.1f} 万" if a < 1e6 else f"{x / 1e4:.0f} 万"
    return f"{x:,.0f}"


def pc(a, b, d=1):
    return '—' if not b else f"{100 * a / b:.{d}f}%"


def wil(k, n):
    if not n:
        return '—'
    if ST is None:
        return pc(k, n)
    lo, hi = ST.wilson(k, n)
    return f"{100 * k / n:.1f}%（{100 * lo:.0f}~{100 * hi:.0f}）"


def table(head, rows, note=None):
    print('| ' + ' | '.join(head) + ' |')
    print('|' + '---|' * len(head))
    for r in rows:
        print('| ' + ' | '.join('—' if c is None else str(c) for c in r) + ' |')
    if note:
        print(f"\n   {note}")
    print()


def sign_p(pos, neg):
    """双侧符号检验（精确二项，p=0.5）。"""
    n = pos + neg
    if not n:
        return None
    k = max(pos, neg)
    tail = sum(math.comb(n, i) for i in range(k, n + 1)) / 2 ** n
    return min(1.0, 2 * tail)


# ------------------------------------------------------------------ 结局（从一条快照往后看）
def outcome(b, s, win=HAZ_WIN, drop=HAZ_DROP, died_only=False):
    """从快照 s 起 win 拍内：'bad' = 阵亡（结算行 event=died 的拍 <= s.t+win），或领土跌到 s 的 drop 倍以下；
    'ok' = 窗口内快照齐、没有上面两件事；None = 日志在窗口结束前断了、又没看到阵亡（离开 / 失联 / 终局），不计。"""
    d = LD.death_tick(b)
    if d is not None and s['t'] < d <= s['t'] + win:
        return 'bad'
    later = [x for x in b.traj if s['t'] < x['t'] <= s['t'] + win]
    if not died_only and any(x['terr'] <= drop * s['terr'] for x in later):
        return 'bad'
    if not later or later[-1]['t'] < s['t'] + win - 90:
        return None
    return 'ok'


def other_cmds(b, a, c):
    """a→c 之间的出兵 / 发船指令条数（cmds 增量里去掉捐款日志和协防戳日志；boats 计数另加，两种记法都不会漏）。"""
    return max(LD._other_cmds(b, a, c), 0) + max(c['boats'] - a['boats'], 0)


# ------------------------------------------------------------------ 检测器
def passive_segments(M):
    """有邻居而零指令：cmds 与 boats 计数连续 >= PASSIVE_LEN 拍不变，这段里从某条快照（t>=630、领土>=MIN_TERR）起的 PASSIVE_LEN 拍内每条快照 nb>=1。
    每个零指令段只记一次；锚点 = 起点之后第一条 t >= 起点+PASSIVE_LEN 的快照（条件第一次成立的时刻）。
    锚点密度 >=100 → EG-giant-neighbor-freeze（超软上限还不出手），否则 → AT-worth-gate。"""
    out = []
    for me, b in sorted(M.bots.items()):
        tr = b.traj
        i = 0
        while i < len(tr):
            j = i
            while j + 1 < len(tr) and tr[j + 1]['cmds'] == tr[i]['cmds'] and tr[j + 1]['boats'] == tr[i]['boats']:
                j += 1
            if tr[j]['t'] - tr[i]['t'] >= PASSIVE_LEN:
                seg = tr[i:j + 1]
                for k, s0 in enumerate(seg):
                    if s0['t'] < 630 or s0['terr'] < MIN_TERR:
                        continue
                    an = next((x for x in seg[k:] if x['t'] >= s0['t'] + PASSIVE_LEN), None)
                    if an is None:
                        break
                    if all(x['nb'] >= 1 for x in seg[k:] if x['t'] <= an['t']):
                        out.append(dict(me=me, name=LD.name_of(b), t0=s0['t'], t=an['t'], segEnd=tr[j]['t'], dens=an['dens'], terr=an['terr'], bal=an['bal'],
                                        pid='EG-giant-neighbor-freeze' if an['dens'] >= 100 else 'AT-worth-gate', out=outcome(b, an)))
                        break
            i = j + 1
    return out


def active_controls(M):
    """对照快照：t>=1080 且 t 是 450 的倍数、领土>=MIN_TERR、此前 PASSIVE_LEN 拍内每条快照 nb>=1（和命中的号一样一直有邻居），
    而且这 PASSIVE_LEN 拍里 cmds 或 boats 计数动过（在发令）。"""
    out = []
    for me, b in sorted(M.bots.items()):
        tr = b.traj
        for idx, s in enumerate(tr):
            if s['t'] < 630 + PASSIVE_LEN or s['t'] % 450 or s['terr'] < MIN_TERR:
                continue
            back = [x for x in tr[:idx + 1] if s['t'] - PASSIVE_LEN <= x['t'] <= s['t']]
            if back[0]['t'] > s['t'] - PASSIVE_LEN or not all(x['nb'] >= 1 for x in back):
                continue
            if back[0]['cmds'] == s['cmds'] and back[0]['boats'] == s['boats']:
                continue
            out.append(dict(me=me, name=LD.name_of(b), t=s['t'], dens=s['dens'], terr=s['terr'], out=outcome(b, s)))
    return out


def passive_deaths(M):
    """阵亡的号（有快照的）：最后一条快照之前 cmds / boats 计数连续多少拍没动；>= PASSIVE_LEN 且这段里 nb 到过 >=1、领土在掉 → DF-passive-death。
    hitAtk = 宽一档：最后 >= PASSIVE_LEN 拍没有出兵 / 发船指令（这段里只发了捐款 / 协防戳的也算）。"""
    out = []
    for me, b in sorted(M.bots.items()):
        d = LD.death_tick(b)
        tr = b.traj
        if d is None or not tr:
            continue
        j = len(tr) - 1
        i = j
        while i > 0 and tr[i - 1]['cmds'] == tr[j]['cmds'] and tr[i - 1]['boats'] == tr[j]['boats']:
            i -= 1
        seg = tr[i:j + 1]
        quiet = tr[j]['t'] - tr[i]['t']
        hit = quiet >= PASSIVE_LEN and max(x['nb'] for x in seg) >= 1 and tr[j]['terr'] < tr[i]['terr']
        # 宽一档：只看出兵 / 发船（捐款、协防戳不算）——最后一次有出兵 / 发船指令的间隔之后过了多久
        k = j
        while k > 0 and other_cmds(b, tr[k - 1], tr[k]) == 0:
            k -= 1
        seg2 = tr[k:j + 1]
        quiet2 = tr[j]['t'] - tr[k]['t']
        hit2 = quiet2 >= PASSIVE_LEN and max(x['nb'] for x in seg2) >= 1 and tr[j]['terr'] < tr[k]['terr']
        out.append(dict(me=me, name=LD.name_of(b), t=d, quiet=quiet, t0=tr[i]['t'], terr0=tr[i]['terr'], terr1=tr[j]['terr'], bal1=tr[j]['bal'],
                        densMax=max(x['dens'] for x in seg), nbMax=max(x['nb'] for x in seg), hit=hit, band=band_of(d),
                        quietAtk=quiet2, hitAtk=hit2, donOnly=(hit2 and not hit)))
    return out


def boxed_segments(M):
    """被围（策略眼里没有可打的邻居、也没有无主邻格）：t>=630、领土>=MIN_TERR、连续快照（相隔 <=270 拍）nb=0 且 neut=0，首尾相隔 >= BOX_LEN 拍。
    只靠日志分不出围住它的是谁（海、同队、名字在池里的异队号 / 空壳 / 内置 AI）；有录像的局见各局复盘的 PL-protect-box。"""
    out = []
    for me, b in sorted(M.bots.items()):
        tr = b.traj
        i = 0
        while i < len(tr):
            s = tr[i]
            if not (s['t'] >= 630 and s['terr'] >= MIN_TERR and s['nb'] == 0 and s['neut'] == 0):
                i += 1
                continue
            j = i
            while j + 1 < len(tr) and tr[j + 1]['nb'] == 0 and tr[j + 1]['neut'] == 0 and tr[j + 1]['t'] - tr[j]['t'] <= 270:
                j += 1
            seg = tr[i:j + 1]
            ln = seg[-1]['t'] - seg[0]['t']
            if ln >= BOX_LEN:
                hard = best = 0
                for a, c in zip(seg, seg[1:]):
                    if a['dens'] >= 149 and c['dens'] >= 149:
                        hard += c['t'] - a['t']
                        best = max(best, hard)
                    else:
                        hard = 0
                out.append(dict(me=me, name=LD.name_of(b), t0=seg[0]['t'], t=seg[-1]['t'], len=ln, densMax=max(x['dens'] for x in seg),
                                over100=sum(c['t'] - a['t'] for a, c in zip(seg, seg[1:]) if a['dens'] > 100), hardLen=best,
                                boats=seg[-1]['boats'] - seg[0]['boats'], cmds=seg[-1]['cmds'] - seg[0]['cmds'], terr=seg[0]['terr'],
                                toEnd=(j == len(tr) - 1), died=LD.death_tick(b)))
            i = j + 1
    return out


def overcap_snaps(M):
    """超软上限且有邻居的快照 a（t>=630、密度>100、nb>=1、领土>=MIN_TERR），下一条快照 c 在 180 拍内：
    acted = a→c 之间有出兵 / 发船指令。之后：grow = a 之后 300 拍内领土到过 >= 1.1 倍；out = outcome(a)。"""
    out = []
    for me, b in sorted(M.bots.items()):
        tr = b.traj
        for a, c in zip(tr, tr[1:]):
            if a['t'] < 630 or a['dens'] <= 100 or a['nb'] < 1 or a['terr'] < MIN_TERR or c['t'] - a['t'] > 180:
                continue
            later = [x['terr'] for x in tr if a['t'] < x['t'] <= a['t'] + 300]
            out.append(dict(me=me, name=LD.name_of(b), t=a['t'], dens=a['dens'], acted=other_cmds(b, a, c) > 0,
                            grow=bool(later) and max(later) >= 1.1 * a['terr'], out=outcome(b, a)))
    return out


def dump_intervals(M):
    """相邻快照 a→c（相隔 <=180 拍）且 a 的余额 >= DUMP_BAL、领土 >= MIN_TERR、t>=630：
    dump = c 的余额 <= DUMP_DROP × 纯利息预测、领土没丢（>=0.9 倍）、这段里发过出兵 / 发船指令（一个间隔里把一半以上的兵打出去）。
    之后：died = c 之后 DUMP_DEATH 拍内阵亡；grew = c 或下一条快照的领土 >= 1.1 × a。其余间隔作对照。"""
    out = []
    for me, b in sorted(M.bots.items()):
        tr = b.traj
        d = LD.death_tick(b)
        for k in range(1, len(tr)):
            a, c = tr[k - 1], tr[k]
            if a['t'] < 630 or a['bal'] < DUMP_BAL or a['terr'] < MIN_TERR or c['t'] - a['t'] > 180:
                continue
            dump = c['bal'] <= DUMP_DROP * LD.pure_interest(a, c, M.land) and c['terr'] >= 0.9 * a['terr'] and other_cmds(b, a, c) > 0
            nxt = tr[k + 1]['terr'] if k + 1 < len(tr) else c['terr']
            o = outcome(b, c, win=DUMP_DEATH, died_only=True)
            out.append(dict(me=me, name=LD.name_of(b), t=c['t'], dump=dump, bal=a['bal'], dens=a['dens'], cmds=other_cmds(b, a, c),
                            grew=max(c['terr'], nxt) >= 1.1 * a['terr'], out=o, died=(d is not None and c['t'] < d <= c['t'] + DUMP_DEATH)))
    return out


def lag_reading(M):
    """日志侧墙上时钟对表（logdigest.wallms_rows：按阵亡行拟合 at = A + 0.056×tick，A 取最小值 = 假定至少有一条阵亡行是准点写的）。两种读数：
    others = 每条结算行落盘时，其余在场号的日志位置比服务器拍落后多少（各号中位；下界 ~ 上界；要靠日志行号对位）；
    own    = 阵亡行自己的「服务器拍 − 本机拍」：这个号知道自己阵亡时，本机比服务器慢了多少拍（不靠行号，每条阵亡行都有）。
    left   = 离开行（event=left 且带本机拍）的「服务器拍 − 本机拍」：这个号被登记离开时本机停在哪一拍；单列，不参与 lag 的判定
             （离开行什么时候写下不清楚：可能是页面卡死若干秒之后才写）。
    服务器拍 600~2100 里有 others 读数的下界 >= LAG_TICKS（对得上的号 >=3 个），或有 own 读数 >= LAG_TICKS → lag；
    这一段里一条读数也没有 → unknown；有读数而都不到 → below（读数只在有人阵亡 / 离开的时刻才有，below 不等于整段都不落后）。"""
    try:
        W = LD.wallms_rows(M)
    except Exception:
        W = None
    if not W:
        return dict(state='nofit', rows=[], own=[], left=[])
    rows, own, left = [], [], []
    for r in W['rows']:
        st = r.get('serverTick')
        if st is None:
            continue
        if r['event'] == 'died' and r['tick']:
            own.append(dict(t=r['tick'], srv=round(st), lag=round(st - r['tick']), name=r['bot']))
        if r['event'] == 'left' and r['tick']:
            left.append(dict(t=r['tick'], srv=round(st), lag=round(st - r['tick']), name=r['bot']))
        if not (600 <= st < 2100) or not r.get('after'):
            continue
        aft, bef = sorted(r['after']), sorted(r['before'])
        rows.append(dict(t=round(st), n=len(aft), lb=round(st - aft[len(aft) // 2]), ub=round(st - bef[len(bef) // 2])))
    rows.sort(key=lambda x: x['t'])
    own.sort(key=lambda x: x['t'])
    win = [x for x in own if 600 <= x['srv'] < 2100]
    if any(x['lb'] >= LAG_TICKS and x['n'] >= 3 for x in rows) or any(x['lag'] >= LAG_TICKS for x in win):
        state = 'lag'
    elif rows or win:
        state = 'below'
    else:
        state = 'unknown'
    return dict(state=state, rows=rows, own=own, left=left, peak=max([x['lb'] for x in rows if x['n'] >= 3] + [x['lag'] for x in win], default=None))


def spawn_picks(mid):
    """spawn.csv（统筹从日志的选点行整理的：每条选点日志一行）→ 每个 me 的选点行数和最后一个选点。"""
    p = os.path.join(r06lib.DATA, mid, 'spawn.csv')
    picks = OrderedDict()
    if not os.path.exists(p):
        return picks
    with open(p) as f:
        for r in csv.DictReader(f):
            try:
                me, x, y = int(r['me']), int(r['x']), int(r['y'])
            except Exception:
                continue
            d = picks.setdefault(me, dict(me=me, name=r['bot'], n=0))
            d['n'] += 1
            d['x'], d['y'] = x, y
    return picks


def donation_rows(M):
    rows = LD.donlog_rows(M)
    ex = [r for r in rows if r['exec']]
    inst = defaultdict(list)
    for r in ex:
        base = dict(me=r['me'], name=r['name'], t=r['t'], to=r['toName'], pct=r['pct'], fee=r['fee'], want=r['vmax'], byRule=r['byRule'])
        if r['pct'] < 150:
            inst['DN-small-pct'].append(base)
        if r['byRule'] is not None and r['byRule'] < r['fee']:
            inst['DN-fee-exceeds-delivery'].append(base)
        if r['recvDens'] is not None and r['recvDens'] >= 100:
            inst['DN-to-overcap'].append(base)
        if r['recvHusk']:
            inst['DN-husk-donate'].append(base)
    for a, b_ in LD.pingpong_pairs(rows):
        inst['DN-pingpong'].append(dict(me=a['me'], name=a['name'], t=b_['t'], to=a['toName'], pct=a['pct'], fee=a['fee'] + b_['fee'], want=a['vmax'] + b_['vmax'], byRule=None))
    for r in LD.dondying_rows(M, rows):
        if not r['undetermined']:
            inst['DN-dying-donor'].append(dict(me=r['me'], name=r['name'], t=r['t'], to=r['toName'], pct=r['pct'], fee=r['fee'], want=r['vmax'], byRule=None))
    run = defaultdict(list)
    for r in sorted(rows, key=lambda r: (r['me'], r['to'], r['t'])):
        k = (r['me'], r['to'])
        if r['exec'] is False:
            run[k].append(r)
            continue
        if len(run[k]) >= 5:
            x = run[k]
            inst['DN-quota-retry-loop'].append(dict(me=x[0]['me'], name=x[0]['name'], t=x[0]['t'], to=x[0]['toName'], pct=x[0]['pct'], fee=0, want=0, byRule=None, n=len(x), t1=x[-1]['t']))
        run[k] = []
    for k, x in run.items():
        if len(x) >= 5:
            inst['DN-quota-retry-loop'].append(dict(me=x[0]['me'], name=x[0]['name'], t=x[0]['t'], to=x[0]['toName'], pct=x[0]['pct'], fee=0, want=0, byRule=None, n=len(x), t1=x[-1]['t']))
    tot = dict(lines=len(rows), ex=len(ex), no=sum(1 for r in rows if r['exec'] is False), fee=sum(r['fee'] for r in ex),
               byRule=sum(r['byRule'] or 0 for r in ex), want=sum(r['vmax'] for r in ex))
    return tot, inst


# ------------------------------------------------------------------ 扫一局
def scan(mid):
    M = r06lib.load_match(mid, with_replay=False, use_sim=False)
    bots = [b for b in M.bots.values() if b.traj]
    rec = dict(id=mid, layer=layer_of(mid, M.card), cohort=M.card.get('cohort'), seats=len(M.bots), bots=len(bots), endTick=M.endTick,
               card=dict(distinct=M.card.get('distinctSquadTeams'), split=M.card.get('teamSplitCounts'), label=(M.card.get('outcome') or {}).get('resultLabel'),
                         primaryWon=(M.card.get('outcome') or {}).get('primaryTeamWon'), anyWon=(M.card.get('outcome') or {}).get('anyBotWon'),
                         base=M.card.get('baseWinExpectation'), teams=M.card.get('actualTeams'), humans=M.card.get('seededPlayers'),
                         squadBots=M.card.get('squadBots'), replay=(M.card.get('dataCompleteness') or {}).get('replay'),
                         timeUtc=M.card.get('timeUtc'), peer=(M.card.get('sameMatchPeer') or {}).get('peerMatchId'),
                         peerCohort=(M.card.get('sameMatchPeer') or {}).get('peerCohort')))
    inst = defaultdict(list)
    ps = passive_segments(M)
    for r in ps:
        inst[r['pid']].append(r)
    rec['passive'] = ps
    rec['controls'] = active_controls(M)
    rec['deaths'] = passive_deaths(M)
    inst['DF-passive-death'] = [r for r in rec['deaths'] if r['hit']]
    rec['capidleBase'] = sum(1 for r in LD.silent_rows(M, LD.CAPIDLE_LEN) if r['densMax'] >= LD.CAPIDLE_DENS)
    inst['EG-cap-idle-death'] = [dict(me=r['me'], name=r['name'], t=r['t1'], t0=r['t0'], len=r['len'], densMax=r['densMax'], died=r['died']) for r in LD.capidle_rows(M)]
    bx = boxed_segments(M)
    rec['boxed'] = bx
    inst['PL-boxed'] = bx
    inst['EG-boxed-hardcap'] = [r for r in bx if r['hardLen'] >= 450]
    rec['overcapSnaps'] = overcap_snaps(M)
    rec['dumps'] = dump_intervals(M)
    inst['AT-dump-then-dead'] = [r for r in rec['dumps'] if r['dump'] and r['died']]
    st = LD.stale_rows(M)
    inst['IO-stale-pulse-dump'] = [dict(me=r['me'], name=r['name'], t=r['tDump1'], t0=r['t0'], cmdsRun=r['cmdsRun'], cmdsDump=r['cmdsDump'], bal=r['balBefore'],
                                        died=(r['deathT'] is not None and r['deathT'] <= r['tDump1'] + DUMP_DEATH)) for r in st if r['cmdsRun'] > 0]
    inst['IO-late-effect'] = [dict(me=r['me'], name=r['name'], t=r['t1'], gapMin=r['lastCmdGapMin'], gapMax=r['lastCmdGap'], bal=r['bal0']) for r in LD.zerodrop_rows(M)
                              if r.get('lastCmdGapMin') is not None and r['lastCmdGapMin'] >= LAG_TICKS]
    bb = LD.boxboat_rows(M)
    inst['BT-boxed-breakout'] = [dict(me=r['me'], name=r['name'], t=r['t0'], boats=r['boats'], ratio=r['ratio']) for r in bb if r['kind'] == 'breakout']
    inst['BT-boxed-no-gain'] = [dict(me=r['me'], name=r['name'], t=r['t0'], boats=r['boats'], ratio=r['ratio']) for r in bb if r['kind'] == 'flat']
    rec['boxboats'] = dict(n=len(bb), boats=sum(r['boats'] for r in bb))
    inst['AT-collapse-harvest'] = [dict(me=r['me'], name=r['name'], t=r['t'], terr0=r['terr0'], terrTop=r['terrTop']) for r in LD.harvest_rows(M)]
    oc = LD.overcap_rows(M)
    rec['overcap'] = dict(snaps=sum(r['n'] for r in oc), n100=sum(r['n100'] for r in oc), n125=sum(r['n125'] for r in oc), n149=sum(r['n149'] for r in oc),
                          lost=sum(r['lost'] for r in oc), got=sum(r['got'] for r in oc))
    inst['EC-overcap'] = [dict(me=r['me'], name=r['name'], t=(r['spans'][0][0] if r['spans'] else 0), n100=r['n100'], lost=r['lost']) for r in oc if r['n100'] >= 5]
    tot, dn = donation_rows(M)
    rec['don'] = tot
    for k, v in dn.items():
        inst[k] = v
    rec['lag'] = lag_reading(M)
    if rec['lag']['state'] == 'lag':
        inst['IO-client-behind'] = ([dict(me=None, name='(其余在场号)', t=x['t'], lb=x['lb'], ub=x['ub'], n=x['n']) for x in rec['lag']['rows'] if x['lb'] >= LAG_TICKS and x['n'] >= 3]
                                    + [dict(me=None, name=x['name'], t=x['srv'], own=x['lag'], localTick=x['t']) for x in rec['lag']['own'] if 600 <= x['srv'] < 2100 and x['lag'] >= LAG_TICKS])
    picks = spawn_picks(mid)
    rec['spawn'] = dict(bots=len(picks), lines=sum(p['n'] for p in picks.values()))
    pl = list(picks.values())
    for i in range(len(pl)):
        for j in range(i + 1, len(pl)):
            dd = math.hypot(pl[i]['x'] - pl[j]['x'], pl[i]['y'] - pl[j]['y'])
            if dd < STACK_DIST:
                inst['SP-squad-stack'].append(dict(me=pl[i]['me'], name=f"{pl[i]['name']}+{pl[j]['name']}", t=0, dist=round(dd, 1), other=pl[j]['me']))
    rec['spawn']['churn'] = sum(1 for p in pl if p['n'] >= CHURN_LINES)
    if (rec['card']['distinct'] or 1) >= 2:
        sp = rec['card']['split'] or {}
        inst['TS-team-split'] = [dict(me=None, name='(全局)', t=0, teams=rec['card']['distinct'], split='/'.join(str(v) for v in sorted(sp.values(), reverse=True)))]
    rec['inst'] = {k: v for k, v in inst.items() if v}
    return rec


DEFS = OrderedDict([
    ('TS-team-split', '编队被分到 >=2 个队（card.json 的 distinctSquadTeams）'),
    ('SP-squad-stack', f'两个我方号日志里最后一个选点相距 <{STACK_DIST} 格（spawn.csv；实例 = 号对）'),
    ('IO-client-behind', f'服务器拍 600~2100 的墙上时钟读数 >={LAG_TICKS} 拍：结算行落盘时其余在场号的日志位置落后，或阵亡行自己的「服务器拍 − 本机拍」（实例 = 读数）'),
    ('IO-stale-pulse-dump', '发令不见效（cmds 在涨、余额贴着纯利息预测、领土不动）之后一个间隔里余额跌到预测的一半以下而领土没丢'),
    ('IO-late-effect', f'零新令的间隔里余额明显低于纯利息预测、领土没丢，而上一批指令至少早 {LAG_TICKS} 拍（支出只能来自更早下的令）'),
    ('AT-dump-then-dead', f'一个间隔里把一半以上的兵打出去（领土没丢），之后 {DUMP_DEATH} 拍内阵亡'),
    ('AT-worth-gate', f'密度 <100、一直有邻居（nb>=1），cmds / boats 连续 >={PASSIVE_LEN} 拍不动'),
    ('EG-giant-neighbor-freeze', f'密度 >=100、一直有邻居（nb>=1），cmds / boats 连续 >={PASSIVE_LEN} 拍不动'),
    ('DF-passive-death', f'阵亡前 cmds / boats 连续 >={PASSIVE_LEN} 拍不动，这段里 nb 到过 >=1、领土在掉'),
    ('EG-cap-idle-death', '连续 >=600 拍零指令、密度到过 >=140，段内或之后 600 拍领土跌掉 >=25% 或阵亡'),
    ('PL-boxed', f'nb=0 且 neut=0 连续 >={BOX_LEN} 拍（t>=630、领土>={MIN_TERR}）'),
    ('EG-boxed-hardcap', '被围的时段里密度 >=149 连续 >=450 拍'),
    ('EC-overcap', '单号密度 >100 的快照 >=5 条（少拿的利息见 cost）'),
    ('BT-boxed-breakout', '被围时发船，之后 500 拍内领土到过 >=1.5 倍'),
    ('BT-boxed-no-gain', '被围时发船，之后 500 拍内最高领土 <1.05 倍'),
    ('AT-collapse-harvest', '无主邻格从 0 跳到 >=8（邻居崩盘），270 拍内领土 >=1.2 倍'),
    ('DN-small-pct', '已执行（估）的捐款 pct<150'),
    ('DN-fee-exceeds-delivery', '已执行（估）的捐款按引擎规则到账 < 手续费'),
    ('DN-to-overcap', '已执行（估）的捐款，收款人之前最近一条快照密度 >=100'),
    ('DN-husk-donate', '已执行（估）的捐款，收款人的页面已停住或离开'),
    ('DN-pingpong', 'A→B 执行后 150 拍内 B→A 也执行（实例 = 一对）'),
    ('DN-dying-donor', '捐款人领土 300 拍内已跌 >=25% 或捐后 300 拍内阵亡'),
    ('DN-quota-retry-loop', '同一捐款人对同一收款人连续 >=5 条没执行'),
])
DON_PATTERNS = [k for k in DEFS if k.startswith('DN-')]


# ------------------------------------------------------------------ 各段输出
def by_layer(recs):
    d = OrderedDict((L, []) for L in LAYERS)
    for r in recs:
        d.setdefault(r['layer'], []).append(r)
    return OrderedDict((k, v) for k, v in d.items() if v)


def applicable(pid, r):
    if pid in DON_PATTERNS:
        return r['don']['lines'] > 0
    if pid == 'IO-client-behind':
        return r['lag']['state'] != 'nofit'
    if pid == 'SP-squad-stack':
        return r['spawn']['bots'] > 0
    return True


def sec_count(recs):
    L = by_layer(recs)
    print('### 模式计数（每格 = 命中的局 / 能判的局｜命中的号｜实例数）')
    head = ['模式', '定义'] + [f"{k}（{len(v)} 局）" for k, v in L.items()]
    rows = []
    for pid, desc in DEFS.items():
        row = [pid, desc]
        for k, v in L.items():
            app = [r for r in v if applicable(pid, r)]
            hit = [r for r in app if r['inst'].get(pid)]
            bots = sum(len({x['me'] for x in r['inst'][pid]}) for r in hit)
            n = sum(len(r['inst'][pid]) for r in hit)
            row.append(f"{len(hit)}/{len(app)}｜{bots}｜{n}" if app else '判不了')
        rows.append(row)
    table(head, rows, '能判的局：捐款类只算日志里解析得出捐款行的局；IO-client-behind 只算结算行带毫秒时间戳、能拟合的局；选点类只算 spawn.csv 有行的局。'
                      '「号」对全局性的模式（TS、IO-client-behind）没有意义。')
    print('   各分层的号数（有快照的号）：' + '；'.join(f"{k} {sum(r['bots'] for r in v)}" for k, v in L.items()))
    print()


def _haz_tab(recs, key_inst, key_ctrl, filt_i, filt_c, label):
    """每个分层：实例的坏结局比例 vs 对照的坏结局比例（合计，描述用），按局配对的符号检验，局×时段分层的 CMH。"""
    rows = []
    for k, v in by_layer(recs).items():
        ki = ni = kc = nc = cen_i = 0
        pos = neg = tie = 0
        strata = defaultdict(lambda: [0, 0, 0, 0])
        for r in v:
            ii = [x for x in r[key_inst] if filt_i(x)]
            cc = [x for x in r[key_ctrl] if filt_c(x)]
            cen_i += sum(1 for x in ii if x['out'] is None)
            ii = [x for x in ii if x['out'] is not None]
            cc = [x for x in cc if x['out'] is not None]
            a, b = sum(1 for x in ii if x['out'] == 'bad'), sum(1 for x in cc if x['out'] == 'bad')
            ki += a
            ni += len(ii)
            kc += b
            nc += len(cc)
            if ii and cc:
                d = a / len(ii) - b / len(cc)
                pos += d > 0
                neg += d < 0
                tie += d == 0
            for x in cc:
                s = strata[(r['id'], band_of(x['t']))]
                s[1] += 1
                s[0] += x['out'] == 'bad'
            for x in ii:
                s = strata[(r['id'], band_of(x['t']))]
                s[3] += 1
                s[2] += x['out'] == 'bad'
        p = sign_p(pos, neg)
        cm = ST.cmh([tuple(s) for s in strata.values()]) if ST and strata else None
        rows.append([k, f"{ki}/{ni}：{wil(ki, ni)}", f"{kc}/{nc}：{wil(kc, nc)}", cen_i, f"{pos} / {neg} / {tie}", f"{p:.3f}" if p is not None else None,
                     (f"{100 * cm['rd_mh']:+.1f} 个百分点（p={cm['p']:.3g}，{cm['used']} 层）" if cm and cm['used'] else None)])
    table(['分层', f'{label}：坏结局 / 实例（95% Wilson）', '对照：坏结局 / 快照', '实例里看不到结局的（不计）', '按局：实例比例 高于 / 低于 / 等于 对照', '符号检验 p（双侧）', 'CMH 合并差（局×时段分层）'], rows)


def sec_hazard(recs):
    print(f'### 有邻居而零指令 >={PASSIVE_LEN} 拍，之后 {HAZ_WIN} 拍内「阵亡或领土跌到 {HAZ_DROP:.0%} 以下」的比例')
    print(f'   实例 = 条件第一次成立的那条快照；对照 = 同样一直有邻居（nb>=1）、但这 {PASSIVE_LEN} 拍里发过指令的快照（每 450 拍取一条）。')
    print('   这是观察对比不是实验：不出手的号可能本来就更弱 / 邻居更强，所以差值是上界性质的描述，不是「改成出手就能少这么多」。')
    print()
    print('**全部（不分密度）**')
    _haz_tab(recs, 'passive', 'controls', lambda x: True, lambda x: True, '零指令')
    print('**密度 <100（AT-worth-gate）对 密度 <100 的对照**')
    _haz_tab(recs, 'passive', 'controls', lambda x: x['dens'] < 100, lambda x: x['dens'] < 100, '零指令')
    print('**密度 >=100（EG-giant-neighbor-freeze）对 密度 >=100 的对照**')
    _haz_tab(recs, 'passive', 'controls', lambda x: x['dens'] >= 100, lambda x: x['dens'] >= 100, '零指令')
    rows = []
    for k, v in by_layer(recs).items():
        for bd in BANDS:
            ii = [x for r in v for x in r['passive'] if band_of(x['t']) == bd and x['out'] is not None]
            cc = [x for r in v for x in r['controls'] if band_of(x['t']) == bd and x['out'] is not None]
            rows.append([k, bd, f"{sum(1 for x in ii if x['out'] == 'bad')}/{len(ii)}：{pc(sum(1 for x in ii if x['out'] == 'bad'), len(ii))}",
                         f"{sum(1 for x in cc if x['out'] == 'bad')}/{len(cc)}：{pc(sum(1 for x in cc if x['out'] == 'bad'), len(cc))}"])
    print('**按时段（合计，描述用）**')
    table(['分层', '锚点所在时段', '零指令：坏结局 / 实例', '对照：坏结局 / 快照'], rows)


def sec_overcap(recs):
    print('### 超软上限（密度>100）且有邻居的快照：下一个间隔出手 / 不出手')
    print('   grow = 之后 300 拍内领土到过 >=1.1 倍；坏结局 = 之后 600 拍内阵亡或领土跌到 75% 以下。按快照合计只作描述；推断看按局配对。')
    rows = []
    for k, v in by_layer(recs).items():
        A = [x for r in v for x in r['overcapSnaps'] if x['acted']]
        N = [x for r in v for x in r['overcapSnaps'] if not x['acted']]
        Ao = [x for x in A if x['out'] is not None]
        No = [x for x in N if x['out'] is not None]
        pg = ng = pb = nb_ = 0
        for r in v:
            a = [x for x in r['overcapSnaps'] if x['acted']]
            n = [x for x in r['overcapSnaps'] if not x['acted']]
            if a and n:
                d = sum(x['grow'] for x in a) / len(a) - sum(x['grow'] for x in n) / len(n)
                pg += d > 0
                ng += d < 0
            a2 = [x for x in a if x['out'] is not None]
            n2 = [x for x in n if x['out'] is not None]
            if a2 and n2:
                d = sum(x['out'] == 'bad' for x in a2) / len(a2) - sum(x['out'] == 'bad' for x in n2) / len(n2)
                pb += d > 0
                nb_ += d < 0
        p1, p2 = sign_p(pg, ng), sign_p(pb, nb_)
        rows.append([k, len(A) + len(N), f"{len(A)}（{pc(len(A), len(A) + len(N))}）",
                     f"{sum(x['grow'] for x in A)}/{len(A)}：{wil(sum(x['grow'] for x in A), len(A))}", f"{sum(x['grow'] for x in N)}/{len(N)}：{wil(sum(x['grow'] for x in N), len(N))}",
                     f"{pg} / {ng}" + (f"（p={p1:.3f}）" if p1 is not None else ''),
                     f"{sum(x['out'] == 'bad' for x in Ao)}/{len(Ao)}：{wil(sum(x['out'] == 'bad' for x in Ao), len(Ao))}",
                     f"{sum(x['out'] == 'bad' for x in No)}/{len(No)}：{wil(sum(x['out'] == 'bad' for x in No), len(No))}",
                     f"{pb} / {nb_}" + (f"（p={p2:.3f}）" if p2 is not None else '')])
    table(['分层', '快照数', '其中下一个间隔出手', '出手：grow', '不出手：grow', '按局 grow：出手 高于 / 低于 不出手', '出手：坏结局', '不出手：坏结局', '按局 坏结局：出手 高于 / 低于 不出手'], rows)


def sec_dump(recs):
    print(f'### 清仓（一个快照间隔里余额跌到纯利息预测的 {DUMP_DROP:.0%} 以下、领土没丢、这段里发过出兵 / 发船指令）之后 {DUMP_DEATH} 拍内阵亡')
    rows = []
    for k, v in by_layer(recs).items():
        D = [x for r in v for x in r['dumps'] if x['dump'] and x['out'] is not None]
        C = [x for r in v for x in r['dumps'] if not x['dump'] and x['out'] is not None]
        G = [x for x in D if x['grew']]
        F = [x for x in D if not x['grew']]
        pos = neg = 0
        strata = defaultdict(lambda: [0, 0, 0, 0])
        for r in v:
            d = [x for x in r['dumps'] if x['dump'] and x['out'] is not None]
            c = [x for x in r['dumps'] if not x['dump'] and x['out'] is not None]
            if d and c:
                dd = sum(x['out'] == 'bad' for x in d) / len(d) - sum(x['out'] == 'bad' for x in c) / len(c)
                pos += dd > 0
                neg += dd < 0
            for x in c:
                s = strata[(r['id'], band_of(x['t']))]
                s[1] += 1
                s[0] += x['out'] == 'bad'
            for x in d:
                s = strata[(r['id'], band_of(x['t']))]
                s[3] += 1
                s[2] += x['out'] == 'bad'
        p = sign_p(pos, neg)
        cm = ST.cmh([tuple(s) for s in strata.values()]) if ST and strata else None
        f = lambda X: f"{sum(x['out'] == 'bad' for x in X)}/{len(X)}：{wil(sum(x['out'] == 'bad' for x in X), len(X))}"
        rows.append([k, f"{len(D)}（{len({(r['id'], x['me']) for r in v for x in r['dumps'] if x['dump']})} 个号、{sum(1 for r in v if any(x['dump'] for x in r['dumps']))} 局）",
                     f(D), f(G), f(F), f(C), f"{pos} / {neg}" + (f"（p={p:.3f}）" if p is not None else ''),
                     (f"{100 * cm['rd_mh']:+.1f} 个百分点（p={cm['p']:.3g}）" if cm and cm['used'] else None)])
    table(['分层', '清仓间隔', f'清仓后 {DUMP_DEATH} 拍内阵亡', '其中换到地的（领土 >=1.1 倍）', '其中没换到地的', '对照（余额 >=2 万、没清仓的间隔）', '按局：清仓 高于 / 低于 对照', 'CMH 合并差（局×时段）'], rows,
          '对照间隔远多于清仓间隔，且同一个号贡献很多条对照；合计比例只作描述。')


def sec_deaths(recs):
    print(f'### 阵亡的号：最后一条快照之前 cmds / boats 计数多久没动（DF-passive-death = >={PASSIVE_LEN} 拍、有过邻居、领土在掉）')
    rows = []
    for k, v in by_layer(recs).items():
        D = [x for r in v for x in r['deaths']]
        H = [x for x in D if x['hit']]
        q = sorted(x['quiet'] for x in D)
        per = [sum(x['hit'] for x in r['deaths']) / len(r['deaths']) for r in v if r['deaths']]
        per.sort()
        H2 = [x for x in D if x['hitAtk']]
        rows.append([k, len(D), f"{len(H)}（{pc(len(H), len(D))}）", f"{len(H2)}（{pc(len(H2), len(D))}）", f"{sum(1 for r in v if any(x['hit'] for x in r['deaths']))}/{sum(1 for r in v if r['deaths'])}",
                     f"{100 * per[len(per) // 2]:.0f}%" if per else None, q[len(q) // 2] if q else None,
                     ' / '.join(f"{sum(1 for x in H if x['band'] == bd)}/{sum(1 for x in D if x['band'] == bd)}" for bd in BANDS),
                     f"{sum(1 for x in H if x['densMax'] >= 100)}/{len(H)}", wan(sum(x['bal1'] for x in H))])
    table(['分层', '阵亡的号（有快照）', 'DF-passive-death', '宽一档：死前 >=450 拍没有出兵 / 发船（只捐款 / 戳的也算）', '命中的局 / 有阵亡的局', '按局占比的中位', '死前零指令拍数中位（全部阵亡）', '按阵亡时段 命中/阵亡：' + ' / '.join(BANDS),
           '命中的号里这段密度到过 >=100', '命中的号最后一条快照手里的兵（合计）'], rows)


def sec_boxed(recs):
    print(f'### 被围（nb=0 且 neut=0 连续 >={BOX_LEN} 拍；t>=630、领土>={MIN_TERR}）')
    rows = []
    for k, v in by_layer(recs).items():
        B = [x for r in v for x in r['boxed']]
        tot = sum(x['len'] for x in B)
        bots = len({(r['id'], x['me']) for r in v for x in r['boxed']})
        br = sum(len(r['inst'].get('BT-boxed-breakout', [])) for r in v)
        fl = sum(len(r['inst'].get('BT-boxed-no-gain', [])) for r in v)
        bb = sum(r['boxboats']['n'] for r in v)
        rows.append([k, f"{len(B)} 段 / {bots} 个号 / {sum(1 for r in v if r['boxed'])} 局", f"{tot:,}", pc(sum(x['over100'] for x in B), tot),
                     f"{sum(1 for x in B if x['hardLen'] >= 450)} 段 / {sum(x['hardLen'] for x in B if x['hardLen'] >= 450):,} 拍",
                     f"{sum(1 for x in B if x['boats'] == 0)}（{pc(sum(1 for x in B if x['boats'] == 0), len(B))}）",
                     f"{sum(1 for x in B if x['cmds'] == 0 and x['boats'] == 0)}",
                     f"{bb} 段：突围 {br}（{pc(br, bb)}）、没换到地 {fl}（{pc(fl, bb)}）"])
    table(['分层', '被围时段', '合计拍数', '其中密度 >100 的拍数占比', '密度 >=149 连续 >=450 拍（EG-boxed-hardcap）', '整段没发船的段', '整段零指令的段', '被围发船的段（logdigest.boxboat_rows）：之后 500 拍领土 >=1.5 倍 / <1.05 倍'], rows,
          '只靠日志分不出围住它的是海、同队号，还是名字在池里的异队号 / 空壳 / 内置 AI。')


LONG_MATCH = 20000      # 终局拍超过这个数的局（赢了以后挂着不结束）单列，不进合计


def sec_cost(recs):
    print('### 钱（日志侧估算）：超软上限少拿的利息（logdigest.overcap_rows）与捐款（logdigest.donlog_rows：按捐款人自己的余额读数判执行与否）')
    print('   少拿的利息只对「密度到过 >100 的号」估（相邻快照间线性插值，按引擎利率公式算「不封顶本来的利息 − 实得」）；占应得 = 少拿 ÷ (少拿 + 实得)，分母也只是这些号。')
    rows = []
    for k, v in by_layer(recs).items():
        long_ = [r for r in v if (r['endTick'] or 0) > LONG_MATCH]
        vv = [r for r in v if r not in long_]
        o = defaultdict(int)
        for r in vv:
            for kk, x in r['overcap'].items():
                o[kk] += x
        sh = sorted(r['overcap']['lost'] / (r['overcap']['lost'] + r['overcap']['got']) for r in vv if r['overcap']['lost'] + r['overcap']['got'] > 0)
        d = defaultdict(int)
        dm = [r for r in v if r['don']['lines'] > 0]
        for r in dm:
            for kk, x in r['don'].items():
                d[kk] += x
        fs = sorted(r['don']['fee'] / (r['don']['fee'] + r['don']['byRule']) for r in dm if r['don']['fee'] + r['don']['byRule'] > 0)
        rows.append([k, f"{o['snaps']:,}", f"{o['n100']:,}（{pc(o['n100'], o['snaps'])}）", f"{o['n149']:,}（{pc(o['n149'], o['snaps'])}）", f"{wan(o['lost'])}（{pc(o['lost'], o['lost'] + o['got'])}）",
                     f"{100 * sh[len(sh) // 2]:.1f}%（{100 * sh[len(sh) // 4]:.1f}~{100 * sh[(3 * len(sh)) // 4]:.1f}）" if sh else None,
                     '、'.join(f"{r['id']}（终局拍 {r['endTick']:,}，少拿 {wan(r['overcap']['lost'])}）" for r in long_) or '无',
                     f"{len(dm)}/{len(v)}", f"{d['lines']:,}", f"{d['ex']:,}（{pc(d['ex'], d['lines'])}）", wan(d['fee']), wan(d['byRule']), pc(d['fee'], d['fee'] + d['byRule']),
                     f"{100 * fs[len(fs) // 2]:.1f}%" if fs else None])
    table(['分层', '快照', '密度 >100', '密度 >=149', '少拿的利息（占应得）', '按局占比：中位（四分位）', f'终局拍 >{LONG_MATCH:,} 的局（不进前面几列）', '有捐款行的局', '捐款日志', '判为执行', '手续费（估）', '到账（按引擎规则估）',
           '手续费 ÷ (手续费 + 到账)', '同左，按局中位'], rows)
    rows = []
    for pid in DON_PATTERNS:
        row = [pid, DEFS[pid]]
        for k, v in by_layer(recs).items():
            X = [x for r in v for x in r['inst'].get(pid, [])]
            ex = sum(r['don']['ex'] for r in v)
            row.append(f"{len(X)}" + (f"（占执行的 {pc(len(X), ex)}）" if pid not in ('DN-pingpong', 'DN-quota-retry-loop') else '') + f"｜手续费 {wan(sum(x['fee'] for x in X))}"
                       + (f"｜到账 {wan(sum(x['byRule'] or 0 for x in X))}" if pid in ('DN-small-pct', 'DN-fee-exceeds-delivery', 'DN-to-overcap', 'DN-husk-donate') else ''))
        rows.append(row)
    table(['模式', '定义'] + list(by_layer(recs).keys()), rows, 'A 组的捐款行是 [HL-DISPATCH]（c116 的调度），G 组是 g09 的 [HL-DONATE]；执行与否的估法在这两组上没有用录像核对过。')


def _q(v, q):
    v = sorted(v)
    return v[min(len(v) - 1, int(q * len(v)))] if v else None


def sec_lag(recs):
    print('### 日志侧墙上时钟对表（logdigest.wallms_rows）')
    print('   others = 结算行落盘时其余在场号的日志位置落后多少；own = 阵亡行自己的「服务器拍 − 本机拍」。A 取各阵亡行的最小值，所以每局至少有一条 own = 0，读数是下界。')
    rows = []
    for k, v in by_layer(recs).items():
        st = defaultdict(list)
        for r in v:
            st[r['lag']['state']].append(r)
        pk = sorted(r['lag']['peak'] for r in st['lag'] if r['lag'].get('peak') is not None)
        rows.append([k, len(v), len(st['lag']), len(st['below']), len(st['unknown']), len(st['nofit']),
                     f"{pk[len(pk) // 2]}（{pk[0]}~{pk[-1]}）" if pk else None, ' '.join(r['id'] for r in st['below'])[:150]])
    table(['分层', '局', f'服务器拍 600~2100 有读数 >={LAG_TICKS} 拍（lag）', '有读数、都不到（below）', '这一段没有读数（unknown）', '拟合不了（nofit）', 'lag 局的最大读数：中位（范围），拍', 'below 的局'], rows,
          '「日志位置落后」可能是本机真的落后，也可能是日志晚落盘，日志侧分不开；有录像的 9 局用指令延迟核对过（crossmatch.py delay）：8 局落后、B021 不落后。')
    rows = []
    for k, v in by_layer(recs).items():
        for lo, hi in ((600, 1500), (1500, 2100), (2100, 3000), (3000, 4284), (4284, 10 ** 9)):
            X = [(r['id'], x) for r in v for x in r['lag']['own'] if lo <= x['srv'] < hi]
            lg = [x['lag'] for _, x in X]
            ms = {i for i, _ in X}
            hit = {i for i, x in X if x['lag'] >= LAG_TICKS}
            rows.append([k, f"{lo}~{hi if hi < 10 ** 9 else ''}", len(lg), len(ms), _q(lg, 0.5), _q(lg, 0.9), max(lg) if lg else None,
                         f"{sum(1 for x in lg if x >= LAG_TICKS)}（{pc(sum(1 for x in lg if x >= LAG_TICKS), len(lg))}）", f"{len(hit)}/{len(ms)}"])
    table(['分层', '阵亡时的服务器拍', '阵亡行', '局', 'own 中位（拍）', 'P90', '最大', f'own >={LAG_TICKS} 拍的阵亡行', '有这种阵亡行的局 / 这一段有阵亡行的局'], rows,
          'own 读数按阵亡行合计只作描述（同一局的号互相关联）；最后一列是按局的口径。')
    rows = []
    for k, v in by_layer(recs).items():
        allleft = sum(1 for r in v for x in r['lag']['left'])
        for lo, hi in ((0, 600), (600, 2100), (2100, 10 ** 9)):
            X = [(r['id'], x) for r in v for x in r['lag']['left'] if lo <= x['srv'] < hi]
            lg = [x['lag'] for _, x in X]
            rows.append([k, f"{lo}~{hi if hi < 10 ** 9 else ''}", f"{len(lg)}（共 {allleft}）", len({i for i, _ in X}), _q(lg, 0.5), _q(lg, 0.9), max(lg) if lg else None,
                         f"{sum(1 for x in lg if x >= LAG_TICKS)}（{pc(sum(1 for x in lg if x >= LAG_TICKS), len(lg))}）"])
    table(['分层', '离开行写下时的服务器拍', '带本机拍的离开行', '局', '服务器拍 − 本机拍：中位', 'P90', '最大', f'>={LAG_TICKS} 拍的'], rows,
          '离开行的本机拍 = 这个号被登记离开时本机走到哪；差值大 = 页面停住很久之后才被登记离开（或离开行写得晚）。只有能拟合的局。')
    rows = []
    for k, v in by_layer(recs).items():
        for pid in ('IO-stale-pulse-dump', 'IO-late-effect'):
            hit = [r for r in v if r['inst'].get(pid)]
            X = [x for r in hit for x in r['inst'][pid]]
            ts = sorted(x['t'] for x in X)
            inwave = sum(1 for t in ts if 600 <= t < 2100)
            rows.append([k, pid, f"{len(hit)}/{len(v)}", len({(r['id'], x['me']) for r in hit for x in r['inst'][pid]}), len(X), f"{inwave}（{pc(inwave, len(X))}）", ts[len(ts) // 2] if ts else None])
    table(['分层', '模式', '命中的局', '号', '实例', '其中 t 在 600~2100', '实例拍的中位'], rows)


CORE = (700, 1750)      # 卡顿波的核心时段（R06 有录像的 8 局里延迟中位 >=90 的格子都落在 600~2100，峰在 900~1350）


def _epoch(s):
    import datetime
    try:
        return datetime.datetime.strptime(s, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=datetime.timezone.utc).timestamp()
    except Exception:
        return None


def sec_lagwho(recs):
    print(f'### 卡顿波跟谁在场有关：服务器拍 {CORE[0]}~{CORE[1]} 的 others 读数（对得上的号 >=3 个），逐条')
    print('   同局的另一个编队 = card.json 的 sameMatchPeer；同时在跑的局 = 发现集里按开局时刻 + 终局拍×56ms 推出当时还没结束的其它局（留出集里的局看不到，所以「没有」不等于真的没有）。')
    span = {}
    for r in recs:
        t0 = _epoch(r['card'].get('timeUtc') or '')
        if t0 is not None:
            span[r['id']] = (t0, t0 + 20 + (r['endTick'] or 0) * 0.056, r['card'].get('squadBots') or 0, r['cohort'])
    rows, per = [], OrderedDict()
    for r in recs:
        for x in r['lag']['rows']:
            if x['n'] < 3 or not (CORE[0] <= x['t'] < CORE[1]):
                continue
            w = span[r['id']][0] + 20 + x['t'] * 0.056 if r['id'] in span else None
            conc = [(o, v) for o, v in span.items() if o != r['id'] and w is not None and v[0] <= w <= v[1]]
            withB = r['cohort'] == 'squad20' or r['card'].get('peerCohort') == 'squad20' or any(v[3] == 'squad20' and o == r['card'].get('peer') for o, v in conc)
            rows.append([r['id'], r['layer'], x['t'], x['n'], f"{x['lb']:+d}~{x['ub']:+d}", r['card'].get('squadBots'), r['card'].get('humans'), r['card'].get('peer') or '无',
                         ' '.join(f"{o}（{v[2]} 个号，走到 t≈{int((w - v[0] - 20) / 0.056)}）" for o, v in conc) or '没有'])
            d = per.setdefault(r['id'], dict(layer=r['layer'], cohort=r['cohort'], withB=withB, lag=False, n=0))
            d['n'] += 1
            d['lag'] = d['lag'] or x['lb'] >= LAG_TICKS
    table(['局', '分层', '服务器拍', '对得上的号', '落后（下界~上界）', '本编队在这局的号', '全场真人', '同局的另一个编队', '发现集里同时在跑的其它局'], rows)
    tab = []
    for lab, f in (('squad20 的局（本编队 20 个页面）', lambda d: d['cohort'] == 'squad20'),
                   ('squad10 / squad8 的局，同局有 squad20 编队', lambda d: d['cohort'] != 'squad20' and d['withB']),
                   ('squad10 / squad8 的局，同局没有 squad20 编队', lambda d: d['cohort'] != 'squad20' and not d['withB'])):
        sub = [(i, d) for i, d in per.items() if f(d)]
        k = sum(1 for _, d in sub if d['lag'])
        tab.append([lab, len(sub), f"{k}（{wil(k, len(sub))}）", ' '.join(i for i, d in sub if d['lag'])[:120], ' '.join(i for i, d in sub if not d['lag'])[:120]])
    yes = [d for d in per.values() if d['withB']]
    no = [d for d in per.values() if not d['withB']]
    fp = ST.fisher_exact(sum(d['lag'] for d in no), len(no), sum(d['lag'] for d in yes), len(yes)) if ST and yes and no else None
    table(['这一段有读数的局', '局', f'有读数 >={LAG_TICKS} 拍', '落后的局', '不落后的局'], tab,
          f"squad20 在场（前两行）{sum(d['lag'] for d in yes)}/{len(yes)} 对 不在场 {sum(d['lag'] for d in no)}/{len(no)}"
          + (f"，Fisher 精确检验双侧 p={fp:.2g}" if fp is not None else '') + '。读数只在有号阵亡 / 离开的时刻才有，每局 1~6 条；局数少，且「同局没有 squad20」不排除同一时刻别的局里有（留出集的局看不到）。')


def sec_spawn(recs):
    print(f'### 选点（spawn.csv = 日志里的选点行）：最后一个选点相距 <{STACK_DIST} 格的号对；选点日志 >={CHURN_LINES} 条的号')
    rows = []
    for k, v in by_layer(recs).items():
        a = [r for r in v if r['spawn']['bots'] > 0]
        pairs = sum(len(r['inst'].get('SP-squad-stack', [])) for r in a)
        same = sum(1 for r in a for x in r['inst'].get('SP-squad-stack', []) if x['dist'] == 0)
        ch = sum(r['spawn']['churn'] for r in a)
        bots = sum(r['spawn']['bots'] for r in a)
        lines = sum(r['spawn']['lines'] for r in a)
        rows.append([k, f"{len(a)}/{len(v)}", bots, f"{lines}（每号 {lines / max(1, bots):.1f}）", f"{pairs} 对（同一格 {same}）", f"{sum(1 for r in a if r['inst'].get('SP-squad-stack'))}/{len(a)}",
                     f"{ch}（{pc(ch, bots)}）"])
    table(['分层', '有选点行的局', '号', '选点日志', f'最后选点 <{STACK_DIST} 格的号对', '命中的局', f'选点日志 >={CHURN_LINES} 条的号'], rows,
          '日志里的最后一个选点不等于录像里的出生点（R06 有录像的 12 局：211 个号里只有 39 个出生在最后一个选点上），这里数的是「策略想站哪」，真实出生点的扎堆见 crossmatch.py spawn。')


def sec_split(recs):
    print('### 拆队与结果（card.json）')
    rows = []
    for k, v in by_layer(recs).items():
        for lab, sub in (('没拆（1 个队）', [r for r in v if (r['card']['distinct'] or 1) < 2]), ('拆成 >=2 个队', [r for r in v if (r['card']['distinct'] or 1) >= 2])):
            if not sub:
                continue
            pw = sum(1 for r in sub if r['card']['primaryWon'])
            aw = sum(1 for r in sub if r['card']['anyWon'])
            base = sum(r['card']['base'] or 0 for r in sub)
            mx = []
            for r in sub:
                sp = r['card']['split'] or {}
                tot = sum(sp.values())
                if tot:
                    mx.append(max(sp.values()) / tot)
            mx.sort()
            rows.append([k, lab, len(sub), f"{pw}（{wil(pw, len(sub))}）", f"{aw}（{pc(aw, len(sub))}）", f"{base:.1f}", f"{100 * mx[len(mx) // 2]:.0f}%" if mx else None])
    table(['分层', '拆队情况', '局', '主队赢', '任一我方号所在的队赢', '基础期望胜局（Σ 1/队数）', '最大一队占我方号的比例（中位）'], rows,
          '「任一我方号所在的队赢」在拆队局里包含落单的号跟着别人的队赢（card 的 split_straggler_won），不等于编队赢。')


def sec_list(recs, pid):
    if pid not in DEFS:
        print('没有这个模式；可选：' + ' '.join(DEFS))
        return
    print(f"### {pid}：{DEFS[pid]}")
    for r in recs:
        for x in r['inst'].get(pid, []):
            ext = ' '.join(f"{k}={('%.1f' % v) if isinstance(v, float) else v}" for k, v in x.items() if k not in ('me', 'name', 't', 'pid'))
            print(f"   {r['id']}（{r['layer']}） {x['name']} t={x['t']} {ext}")


def to_json(recs):
    os.makedirs(OUT, exist_ok=True)
    doc = dict(dataRoot=r06lib.DATA, matches=len(recs), defs=DEFS, layers={k: [r['id'] for r in v] for k, v in by_layer(recs).items()},
               perMatch=[dict(id=r['id'], layer=r['layer'], cohort=r['cohort'], bots=r['bots'], card=r['card'], lag=dict(state=r['lag']['state'], peak=r['lag'].get('peak')),
                              overcap=r['overcap'], don=r['don'], spawn=r['spawn'],
                              counts={k: dict(n=len(v), bots=len({x['me'] for x in v})) for k, v in r['inst'].items()},
                              passive=dict(n=len(r['passive']), bad=sum(1 for x in r['passive'] if x['out'] == 'bad'), cens=sum(1 for x in r['passive'] if x['out'] is None)),
                              controls=dict(n=len(r['controls']), bad=sum(1 for x in r['controls'] if x['out'] == 'bad'), cens=sum(1 for x in r['controls'] if x['out'] is None)),
                              deaths=dict(n=len(r['deaths']), passive=sum(1 for x in r['deaths'] if x['hit'])),
                              instances={k: v for k, v in r['inst'].items()}) for r in recs])
    p = os.path.join(OUT, 'patterns.json')
    json.dump(doc, open(p, 'w'), ensure_ascii=False, default=str)
    print('写入', p)


SECS = OrderedDict([('split', sec_split), ('spawn', sec_spawn), ('lag', sec_lag), ('lagwho', sec_lagwho), ('count', sec_count), ('hazard', sec_hazard), ('overcap', sec_overcap),
                    ('dump', sec_dump), ('deaths', sec_deaths), ('boxed', sec_boxed), ('cost', sec_cost)])


def main():
    a = sys.argv[1:]
    if not a:
        print(__doc__)
        return 2
    sec = a[0]
    rest = a[1:]
    which = 'all'
    if '--set' in rest:
        i = rest.index('--set')
        which = rest[i + 1]
        rest = rest[:i] + rest[i + 2:]
    pid = None
    if sec == 'list':
        pid, rest = (rest[0] if rest else None), rest[1:]
    ids = rest or sorted(d for d in os.listdir(r06lib.DATA) if os.path.exists(os.path.join(r06lib.DATA, d, 'card.json')))
    recs, bad = [], []
    for mid in ids:
        try:
            card = json.load(open(os.path.join(r06lib.DATA, mid, 'card.json')))
            L = layer_of(mid, card)
            if which != 'all' and not ((which == 'mine' and L == 'mine') or (which == 'rest' and L == 'B·其余') or (which == 'B' and card.get('cohort') == 'squad20')
                                       or (which == 'A' and L == 'A') or (which == 'G' and L == 'G')):
                continue
            recs.append(scan(mid))
        except Exception as e:      # 解析不了的包单列，不让一局坏掉整批
            bad.append((mid, repr(e)[:160]))
    print(f"数据根目录 {r06lib.DATA}；扫了 {len(recs)} 局" + (f"；解析失败 {len(bad)} 局：{bad}" if bad else ''))
    print()
    if sec == 'json':
        to_json(recs)
    elif sec == 'list':
        sec_list(recs, pid)
    elif sec == 'all':
        for f in SECS.values():
            f(recs)
    elif sec in SECS:
        SECS[sec](recs)
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
