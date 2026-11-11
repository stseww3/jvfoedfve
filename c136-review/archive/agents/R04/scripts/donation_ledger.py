#!/usr/bin/env python3
"""donation_ledger.py — 捐款对账：日志里每一次“发起捐款”到底有没有被引擎接受，以及拒单能不能用配额公式解释。

真值来源：录像（replay.txt）。引擎在全部校验（含配额）通过之后才把捐款记进录像，所以录像里的捐款指令（指令号 2）= 被接受的捐款。
日志来源：events.csv 的 DISPATCH / DONATE 行 = 策略“发出”捐款的时刻（策略自己不知道后面是否被拒）。

步骤：
  1. 配对：同一发起人的日志事件与录像捐款，按 (比例, 收款人) 相同、0 <= 执行拍 - 发出拍 <= MAXD、先后次序不交叉 的条件做最大配对
     （动态规划；并列时取总延迟最小）。配上 = 接受；日志事件配不上 = 被拒；录像捐款配不上 = 日志缺行。
  2. 配额重建：按录像顺序逐笔累加每个收款人已用点数（规格书 B 的公式；公式与线上原文的一致性见 live-donation-check.cjs）。
     金额用发起人余额估：配上的用日志里的 myBal，日志缺行的用 traj.csv 插值，队里别人的捐款金额未知（按最低点数记，并单独计数）。
  3. 对每一次被拒的发起，用当时的已用点数和上限判断“公式是否也会拒”，给出吻合率。
     重建的误差来源：余额是发出时的不是执行时的；别人给的金额未知；船靠岸移交也占配额（录像里看不出）。

用法：cd c136-review/agents/R04 && timeout 120 python3 scripts/donation_ledger.py A022 [A038 ...] [--tsv DIR] [--quiet]
"""
import csv
import json
import os
import sys
from bisect import bisect_right
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from replay_lib import load_replay, g0  # noqa: E402

BUNDLES = '/agent/repos/c136-data/bundles'
MAXD = 150  # 发出到执行最多隔多少拍还算同一笔


def cap_at(t):
    """全场配额上限在第 t 拍指令执行时的值（上限在每拍结算里逢 t%100==99 增长；指令先于当拍结算执行）。"""
    cap = 15
    for k in range(99, t, 100):
        cap += 4 if k < 1071 else 6 if k < 2142 else 8 if k < 3213 else 10
    return cap


def cost_of(t, v, ke, land_q):
    if t >= 3213:
        return 4 + g0(100 * v, max(1, min(100 * land_q, 10 ** 9)))
    uv = 1 + g0(ke, 300)
    m = 1 if t < 357 else 4 if t < 714 else 10 if t < 1071 else 30 if t < 2142 else 100
    return 2 + g0(100 * v, m * uv)


def match_seq(ev, rp):
    """ev: [(t, key)]，rp: [(tick, key)]，都按时间排好。返回 {ev下标: rp下标} 的最大不交叉配对（并列取总延迟最小）。"""
    n, m = len(ev), len(rp)
    # dp[i][j] = (配对数, -总延迟)，只用 ev[i:], rp[j:]
    dp = [[(0, 0)] * (m + 1) for _ in range(n + 1)]
    for i in range(n - 1, -1, -1):
        row, nxt = dp[i], dp[i + 1]
        for j in range(m - 1, -1, -1):
            best = nxt[j] if nxt[j] >= row[j + 1] else row[j + 1]
            d = rp[j][0] - ev[i][0]
            if ev[i][1] == rp[j][1] and 0 <= d <= MAXD:
                c = nxt[j + 1]
                cand = (c[0] + 1, c[1] - d)
                if cand > best:
                    best = cand
            row[j] = best
    out = {}
    i = j = 0
    while i < n and j < m:
        d = rp[j][0] - ev[i][0]
        if ev[i][1] == rp[j][1] and 0 <= d <= MAXD and dp[i][j] == (dp[i + 1][j + 1][0] + 1, dp[i + 1][j + 1][1] - d):
            out[i] = j
            i += 1
            j += 1
        elif dp[i][j] == dp[i + 1][j]:
            i += 1
        else:
            j += 1
    return out


def squad_ids(r, bots):
    out = {}
    for bot in bots:
        hit = [p for p, n in enumerate(r['names']) if bot in n]
        if len(hit) == 1:
            out[bot] = hit[0]
    return out


def run(mid, tsv_dir=None, quiet=False):
    d = os.path.join(BUNDLES, mid)
    r = load_replay(os.path.join(d, 'replay.txt'))
    card = json.load(open(os.path.join(d, 'card.json')))
    ke = card['mapLand']
    ev_all = [x for x in csv.DictReader(open(os.path.join(d, 'events.csv'), encoding='utf8')) if x['type'] in ('DISPATCH', 'DONATE') and x['pct'] and x['target']]
    traj = defaultdict(list)
    for x in csv.DictReader(open(os.path.join(d, 'traj.csv'), encoding='utf8')):
        try:
            traj[x['bot']].append((int(x['t']), int(x['terr']), int(x['bal'])))
        except ValueError:
            pass
    for v in traj.values():
        v.sort()
    bots = set(traj) | {x['bot'] for x in ev_all}
    ids = squad_ids(r, bots)
    for x in csv.DictReader(open(os.path.join(d, 'results.csv'), encoding='utf8')):
        ids.setdefault(x['bot'], int(x['meId']))
    id2bot = {v: k for k, v in ids.items()}
    ours = set(ids.values())

    def state_of(pid, t):
        """(领土, 余额) 的最近快照（不晚于 t），没有则 None。"""
        arr = traj.get(id2bot.get(pid, ''), [])
        k = bisect_right(arr, (t, 10 ** 12, 10 ** 12)) - 1
        if k < 0:
            return (arr[0][1], arr[0][2]) if arr else None
        return arr[k][1], arr[k][2]

    dons = [x for x in r['rows'] if x[2] == 2]  # (step, tick, 2, donor, pct, recipient)，已按执行先后
    ev_by = defaultdict(list)
    for x in ev_all:
        ev_by[ids.get(x['bot'], -1)].append(x)
    rp_by = defaultdict(list)
    for i, x in enumerate(dons):
        rp_by[x[3]].append(i)
    ev_match = {}  # id(event) -> replay idx
    rp_match = {}  # replay idx -> event
    for me, evs in ev_by.items():
        evs.sort(key=lambda e: int(e['t']))
        E = [(int(e['t']), (int(e['pct']), int(e['target']))) for e in evs]
        R = [(dons[i][1], (dons[i][4], dons[i][5])) for i in rp_by.get(me, [])]
        for ei, rj in match_seq(E, R).items():
            gi = rp_by[me][rj]
            ev_match[id(evs[ei])] = gi
            rp_match[gi] = evs[ei]
    # 每个发起人的延迟（配上的），用于估计被拒事件“本该执行”的拍
    delays_by = defaultdict(list)
    for gi, e in rp_match.items():
        delays_by[dons[gi][3]].append((int(e['t']), dons[gi][1] - int(e['t'])))
    all_delays = sorted(dl for v in delays_by.values() for _, dl in v)
    med_all = all_delays[len(all_delays) // 2] if all_delays else 13

    def delay_near(me, t):
        arr = delays_by.get(me)
        if not arr:
            return med_all
        return min(arr, key=lambda a: abs(a[0] - t))[1]

    # 统一时间线：录像捐款（执行拍）与被拒事件（估计执行拍）
    items = []
    for gi, x in enumerate(dons):
        items.append((x[1], 0, gi, 'rp', x))
    for e in ev_all:
        if id(e) not in ev_match:
            me = ids.get(e['bot'], -1)
            items.append((int(e['t']) + delay_near(me, int(e['t'])), 1, 0, 'rej', e))
    items.sort(key=lambda a: (a[0], a[1], a[2]))
    used = defaultdict(int)
    unknown_pts = defaultdict(int)  # 收款人收到的“金额未知”的笔数
    rows = []
    for te, _, gi, kind, x in items:
        cap = cap_at(te)
        free = te >= 4284
        if kind == 'rp':
            donor, pct, q = x[3], x[4], x[5]
            e = rp_match.get(gi)
            if e is not None:
                bal, src = int(e['myBal'] or 0), 'log'
            else:
                st = state_of(donor, te) if donor in ours else None
                bal, src = (st[1], 'traj') if st else (None, 'unknown')
            stq = state_of(q, te) if q in ours else None
            if bal is None:
                v = fee = None
                c = cost_of(te, 0, ke, stq[0] if stq else 1)
                if q in ours and not free:
                    unknown_pts[q] += 1
            else:
                fee = g0(64 * bal, 1024)
                v = min(g0(bal * (pct + 1), 1024), bal - fee)
                if stq:
                    v = min(v, max(min(stq[0] * 150 - stq[1], 15 * 10 ** 8 - stq[1]), 0))
                c = cost_of(te, v, ke, stq[0] if stq else 10 ** 7)
            ok_pred = free or used[q] + c <= cap
            rows.append({'t': int(e['t']) if e is not None else '', 'execTick': te, 'donor': donor, 'bot': id2bot.get(donor, r['names'][donor] if donor < r['H'] else f'AI{donor}'), 'pct': pct, 'q': q,
                         'qname': id2bot.get(q, r['names'][q] if q < r['H'] else f'AI{q}'), 'kind': e['kind'] if e is not None else '(日志无此行)', 'bal': bal, 'balSrc': src, 'v': v, 'fee': fee,
                         'cost': c, 'cap': cap, 'usedBefore': used[q], 'accepted': True, 'predOk': ok_pred, 'flagRej': (e['likelyRejected'] == 'True') if e is not None else '',
                         'dMe': e['dMe'] if e is not None else '', 'dAlly': e['dAlly'] if e is not None else '', 'boxedIn': e['boxedIn'] if e is not None else '', 'ours': donor in ours, 'qOurs': q in ours})
            if not free:
                used[q] += c
        else:
            e = x
            donor = ids.get(e['bot'], -1)
            pct, q, bal = int(e['pct']), int(e['target']), int(e['myBal'] or 0)
            fee = g0(64 * bal, 1024)
            v0 = min(g0(bal * (pct + 1), 1024), bal - fee)
            stq = state_of(q, te) if q in ours else None
            room = max(min(stq[0] * 150 - stq[1], 15 * 10 ** 8 - stq[1]), 0) if stq else v0
            v = min(v0, room)
            c = cost_of(te, v, ke, stq[0] if stq else 10 ** 7)
            ok_pred = v >= 1 and (free or used[q] + c <= cap)
            why = '收款方到顶' if v < 1 else ('配额：单笔就超上限' if (not free and c > cap) else ('配额：累计用满' if not ok_pred else '公式解释不了'))
            rows.append({'t': int(e['t']), 'execTick': te, 'donor': donor, 'bot': e['bot'], 'pct': pct, 'q': q, 'qname': e['targetName'], 'kind': e['kind'], 'bal': bal, 'balSrc': 'log', 'v': v, 'fee': fee,
                         'cost': c, 'cap': cap, 'usedBefore': used[q], 'accepted': False, 'predOk': ok_pred, 'flagRej': e['likelyRejected'] == 'True', 'dMe': e['dMe'], 'dAlly': e['dAlly'],
                         'boxedIn': e['boxedIn'], 'ours': True, 'qOurs': q in ours, 'why': why, 'unknownToQ': unknown_pts[q]})
    mine = [o for o in rows if o['ours'] and o['kind'] != '(日志无此行)']
    acc = [o for o in mine if o['accepted']]
    rej = [o for o in mine if not o['accepted']]
    nolog = [o for o in rows if o['ours'] and o['kind'] == '(日志无此行)']
    foreign_in = [o for o in rows if not o['ours'] and o['qOurs']]
    S = {'match': mid, 'ke': ke, 'replayDonations': len(dons), 'dispatches': len(mine), 'accepted': len(acc), 'rejected': len(rej), 'noLog': len(nolog), 'foreignToUs': len(foreign_in),
         'medDelay': med_all, 'delayRange': (all_delays[0], all_delays[-1]) if all_delays else None,
         'accPredOk': sum(1 for o in acc if o['predOk']), 'rejExplained': sum(1 for o in rej if not o['predOk']),
         'why': Counter(o['why'] for o in rej), 'flag': Counter((o['accepted'], o['flagRej']) for o in mine)}
    bands = [(0, 1071), (1071, 2142), (2142, 3213), (3213, 4284), (4284, 10 ** 9)]
    S['bands'] = []
    for a, b in bands:
        sub = [o for o in mine if a <= o['t'] < b]
        ok = [o for o in sub if o['accepted']]
        S['bands'].append((a, b, len(sub), len(ok), sum(o['v'] or 0 for o in ok), sum(o['fee'] or 0 for o in ok)))
    S['sentV'] = sum(o['v'] or 0 for o in acc)
    S['sentFee'] = sum(o['fee'] or 0 for o in acc)
    if not quiet:
        print(f"== {mid}  陆地 {ke}；录像里捐款 {len(dons)} 笔（我方发起 {sum(1 for x in dons if x[3] in ours)}，队里别人给我方 {len(foreign_in)}，其余 {sum(1 for x in dons if x[3] not in ours and x[5] not in ours)}）")
        n = len(mine)
        print(f"   日志里我方发起 {n} 次：被接受 {len(acc)}（{100 * len(acc) / max(1, n):.1f}%），被拒 {len(rej)}；录像里有、日志里没有的我方捐款 {len(nolog)} 笔")
        print(f"   发出到执行的延迟：中位 {med_all} 拍，范围 {S['delayRange']}")
        f = S['flag']
        print(f"   与 events.csv 的 likelyRejected 标记对照：接受且未标拒 {f[(True, False)]}，接受却被标拒 {f[(True, True)]}，被拒且标拒 {f[(False, True)]}，被拒却未标拒 {f[(False, False)]}")
        print(f"   配额公式重建：接受的 {len(acc)} 笔里公式也判接受 {S['accPredOk']}；被拒的 {len(rej)} 次里公式也判拒 {S['rejExplained']}（{100 * S['rejExplained'] / max(1, len(rej)):.1f}%）")
        print(f"   被拒原因（按公式）：{dict(S['why'])}")
        for a, b, ns, nk, v, fee in S['bands']:
            if ns:
                print(f"   t∈[{a},{b if b < 10 ** 9 else '∞'})：发起 {ns}，接受 {nk}（{100 * nk / ns:.0f}%），被拒 {ns - nk}；接受的合计到账约 {v}，手续费约 {fee}")
        print('   逐号：发起/接受/被拒 | 作为收款人收到的笔数与估计兵数（含队里别人给的笔数）')
        for bot, me in sorted(ids.items(), key=lambda kv: kv[1]):
            sub = [o for o in mine if o['bot'] == bot]
            a = sum(1 for o in sub if o['accepted'])
            got = [o for o in rows if o['accepted'] and o['q'] == me]
            if sub or got:
                print(f"     {bot:8s} me={me:3d} 发起 {len(sub):3d} 接受 {a:3d} 被拒 {len(sub) - a:3d} | 收到 {len(got):3d} 笔 约 {sum(o['v'] or 0 for o in got)} 兵（别人给 {sum(1 for o in got if not o['ours'])} 笔）")
    if tsv_dir:
        os.makedirs(tsv_dir, exist_ok=True)
        cols = ['t', 'execTick', 'bot', 'donor', 'kind', 'pct', 'q', 'qname', 'bal', 'balSrc', 'boxedIn', 'dMe', 'dAlly', 'v', 'fee', 'cost', 'cap', 'usedBefore', 'accepted', 'predOk', 'why', 'flagRej']
        with open(os.path.join(tsv_dir, f'{mid}.donations.tsv'), 'w', encoding='utf8') as fh:
            fh.write('\t'.join(cols) + '\n')
            for o in rows:
                fh.write('\t'.join(str(o.get(c, '')) for c in cols) + '\n')
    return S, rows


if __name__ == '__main__':
    args = sys.argv[1:]
    tsv = None
    quiet = '--quiet' in args
    if quiet:
        args.remove('--quiet')
    if '--tsv' in args:
        i = args.index('--tsv')
        tsv = args[i + 1]
        del args[i:i + 2]
    tot = [0, 0, 0, 0]
    for m in args:
        S, _ = run(m, tsv, quiet)
        tot[0] += S['dispatches']
        tot[1] += S['accepted']
        tot[2] += S['rejected']
        tot[3] += S['rejExplained']
    if len(args) > 1:
        print(f"# 合计 {len(args)} 局：我方发起 {tot[0]} 次，被执行 {tot[1]}（{100 * tot[1] / max(1, tot[0]):.1f}%），被拒 {tot[2]}；被拒里配额公式（只算捐款指令）也判拒 {tot[3]}（{100 * tot[3] / max(1, tot[2]):.1f}%）")
