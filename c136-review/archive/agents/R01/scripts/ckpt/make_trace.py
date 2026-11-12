#!/usr/bin/env python3
"""make_trace.py — 把 R01 自己的「影子决策 ↔ 录像落地」配对写成 C2 通道用的实录阶梯文件。

来源：scripts/shadow.mjs 的 matchReplay()——当年那版策略作影子逐拍决策，录像里我方席位每条落地的陆攻 / 捐款
      按「同席位、同种类、同比例、同目标、落地拍 ≥ 决策拍、同席位先发先到」去对影子决策。
      这套配对与 R06 入库的 traces/<局>.json 互相独立（另一份影子、另一套配对规则），对照见 xcheck_trace.py。

三种口径，各写一个目录（格式都与 R06 的 traces/<局>.json 相同，lib/channel.mjs 的 buildC2 可以直接读）：

  traces/      只收「唯一定位」的（shadow_match.csv 里 uniq>0）。一条落地指令在影子序列里只有一个位置放得下。
  traces-hi/   再加上「定位不唯一」的陆攻，取最早放得下的那条决策（先发先到、留先发的——与通道模型自己的 9 条顶规则一致）。
               这是落后的上界：同一条落地指令配得越早，落后越大。捐款例外，仍取最晚的（没落地的捐款多是被配额拒掉的）。
  traces-lo/   再加上「定位不唯一」的，取最晚放得下的那条决策。这是落后的下界。

为什么要后两种：落后最深的那几段，策略每个决策拍都在重发同一条指令，落地时成批到、只活下来几条，
活下来的是哪几条定不了位。只收唯一定位的话，这几段在阶梯上是空的，通道模型只能拿两头的值去补，补出来偏健康。
真值夹在 lo 与 hi 之间（前提：影子的决策序列对、同席位先发先到）。

后两种口径配的时候还用了日志次序给的地板（logorder_floor.py → floor/<局>.json）：页面算到本机拍 τ 时服务器至少已经到了 fl(τ)，
τ 发出的指令不可能早于 fl(τ) + 5 拍落地，这样的配法排除。地板本身不写进阶梯文件（阶梯文件里只有真实的指令配对），
由 ckpt_run.mjs --floor 在建好的阶梯上取 max。先跑 logorder_floor.py 再跑本脚本。

    seats[席位] = [[决策拍 τ, 落地拍 E, 种类(0 陆攻 / 2 捐款), 影子决策时的目标, 是否生效, 录像里记的目标], …]

用法：python3 scripts/ckpt/make_trace.py [局号…]（缺省 15 局）
输出：reports/ckpt-data/traces{,-hi,-lo}/<局>.json 与 reports/ckpt-data/trace_summary.csv
"""
import bisect
import csv
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
R01 = os.path.dirname(os.path.dirname(HERE))
OUT = os.path.join(R01, 'out')
DATA = os.path.join(R01, 'reports', 'ckpt-data')
MIDS = 'A075 A055 A023 A019 A054 A003 A031 A050 A009 A057 A059 A094 A005 B039 B043'.split()
STRAT = lambda m: 'c110' if m[0] == 'B' else ('va' if int(m[1:]) <= 17 else 'vb' if int(m[1:]) <= 95 else 'vc')
NEUTRAL = 512
MAX_LAG = 1500     # 与 matchReplay 相同
MIN_LAG = 6        # 定位不唯一的那些：落地拍至少比决策拍晚这么多（不到一个回合的配法不要）
MIN_TRANSIT = 5    # 与 logorder_floor.py 相同


def q(a, p):
    a = sorted(a)
    return a[min(len(a) - 1, int(p * len(a)))] if a else None


def same(r, c, fl=None):
    """录像里落地的 r 与影子决策 c 是不是「同一条」：同种类、同比例、同目标（陆攻打中立时影子的目标可以是某个玩家）。
    fl(τ) = 日志次序给的服务器拍下界（logorder_floor.py）：页面算到本机拍 τ 时服务器至少已经到了 fl(τ)，
    所以 τ 发出的指令不可能在 fl(τ) + 最小在途拍数 之前落地——这样的配法排除。"""
    if r['kind'] != c['kind'] or r['pct'] != c['pct']:
        return False
    if not (c['target'] == r['target'] or (r['kind'] == 'attack' and r['target'] == NEUTRAL and c['target'] < NEUTRAL)):
        return False
    lag = r['tick'] - c['t']
    if not (MIN_LAG <= lag <= MAX_LAG):
        return False
    return fl is None or fl(c['t']) <= r['tick'] - MIN_TRANSIT


def load_floor(mid):
    """→ {席位: fl(τ)}：τ 之前最近一个地板点的服务器拍下界（没有就是 0）。"""
    path = os.path.join(DATA, 'floor', mid + '.json')
    if not os.path.exists(path):
        return {}
    out = {}
    for p, pts in json.load(open(path))['seats'].items():
        ts = [a for a, _ in pts]
        lb = [b for _, b in pts]

        def fl(tau, ts=ts, lb=lb):
            i = bisect.bisect_right(ts, tau) - 1
            return lb[i] if i >= 0 else 0
        out[p] = fl
    return out


def load_match(mid):
    """→ {席位: (S 影子决策列表, R 落地指令列表)}；R 的顺序与 shadow_match.csv 相同（同席位按落地拍、同拍内按发出先后）。"""
    S, R = {}, {}
    for r in csv.DictReader(open(os.path.join(OUT, mid, 'shadow_cmds.csv'))):
        if r['ok'] != '1' or r['kind'] not in ('attack', 'donate'):
            continue
        S.setdefault(r['p'], []).append({'t': int(r['t']), 'kind': r['kind'], 'pct': int(r['pct']), 'target': int(r['target'])})
    for r in csv.DictReader(open(os.path.join(OUT, mid, 'shadow_match.csv'))):
        R.setdefault(r['p'], []).append({
            'tick': int(r['tick']), 'kind': r['kind'], 'pct': int(r['pct']), 'target': int(r['target']), 'n': int(r['n']),
            'uniq': int(r['uniq']), 'tDecide': int(r['tDecide']) if r['tDecide'] != '' else None,
            'shTarget': int(r['shTarget']) if r['shTarget'] != '' else None,
            'ok': 1 if str(r['applied']) in ('1', 'true', 'True') else 0,
        })
    return {p: (S.get(p, []), R[p]) for p in R}


def assign(S, R, variant, fl=None):
    """→ 每条落地指令配到的影子决策下标（没配上的是 None）。唯一定位的照抄；其余按 variant 在前后两个已定位的之间贪心。"""
    idx_by_t = {}
    for k, c in enumerate(S):
        idx_by_t.setdefault((c['t'], c['kind'], c['pct']), k)
    fixed = [None] * len(R)
    for i, r in enumerate(R):
        if r['uniq'] > 0 and r['tDecide'] is not None:
            fixed[i] = idx_by_t.get((r['tDecide'], r['kind'], r['pct']))
    if variant == 'located':
        return fixed
    out = fixed[:]
    if variant == 'hi':
        nxt = [len(S)] * len(R)
        b = len(S)
        for i in range(len(R) - 1, -1, -1):
            nxt[i] = b
            if fixed[i] is not None:
                b = fixed[i]
        j = 0
        for i, r in enumerate(R):
            if fixed[i] is not None:
                j = max(j, fixed[i] + 1)
                continue
            k = j
            while k < nxt[i] and not same(r, S[k], fl):
                k += 1
            if k < nxt[i]:
                out[i] = k
                j = k + 1
        # 捐款不适用「留先发的」：没落地的捐款绝大多数是被配额静默拒掉的（不进录像），落地的那条应是最近一次尝试。
        # 所以 hi 口径里捐款仍取最晚放得下的（与 lo 相同）。
        lo = assign(S, R, 'lo', fl)
        for i, r in enumerate(R):
            if fixed[i] is None and r['kind'] == 'donate':
                out[i] = lo[i]
    elif variant == 'lo':
        prv = [-1] * len(R)
        b = -1
        for i in range(len(R)):
            prv[i] = b
            if fixed[i] is not None:
                b = fixed[i]
        j = len(S) - 1
        for i in range(len(R) - 1, -1, -1):
            r = R[i]
            if fixed[i] is not None:
                j = min(j, fixed[i] - 1)
                continue
            k = j
            while k > prv[i] and not same(r, S[k], fl):
                k -= 1
            if k > prv[i]:
                out[i] = k
                j = k - 1
    else:
        raise ValueError(variant)
    return out


def main():
    mids = [a for a in sys.argv[1:] if not a.startswith('--')] or MIDS
    summ = []
    for mid in mids:
        if not os.path.exists(os.path.join(OUT, mid, 'shadow_match.csv')):
            print(f'{mid}: 没有 shadow_match.csv，跳过')
            continue
        M = load_match(mid)
        FL = load_floor(mid)
        row = {'mid': mid, 'seats': len(M)}
        for variant, sub in (('located', 'traces'), ('hi', 'traces-hi'), ('lo', 'traces-lo')):
            seats = {}
            n = added = 0
            total = sum(len(R) for S, R in M.values())
            lag_added = []
            for p, (S, R) in M.items():
                a = assign(S, R, variant, FL.get(p))
                for i, r in enumerate(R):
                    if a[i] is None:
                        continue
                    c = S[a[i]]
                    kind = 0 if r['kind'] == 'attack' else 2
                    sh_t = r['shTarget'] if (r['uniq'] > 0 and r['shTarget'] is not None) else c['target']
                    seats.setdefault(p, []).append([c['t'], r['tick'], kind, sh_t, r['ok'], r['target']])
                    n += 1
                    if r['uniq'] <= 0:
                        added += 1
                        lag_added.append(r['tick'] - c['t'])
            for v in seats.values():
                v.sort()
            lag = [r[1] - r[0] for v in seats.values() for r in v]
            last = max((r[1] for v in seats.values() for r in v), default=-1)
            src = {'located': 'R01 scripts/shadow.mjs matchReplay (shadow_match.csv, uniq>0)',
                   'hi': 'R01 matchReplay 唯一定位的 + 定位不唯一的取最早放得下的决策（落后上界）',
                   'lo': 'R01 matchReplay 唯一定位的 + 定位不唯一的取最晚放得下的决策（落后下界）'}[variant]
            out = dict(matchId=mid, strategy=STRAT(mid), source=src, variant=variant, rows=n, unmatched=total - n, lost=None, last=last, seats=seats)
            os.makedirs(os.path.join(DATA, sub), exist_ok=True)
            json.dump(out, open(os.path.join(DATA, sub, mid + '.json'), 'w'), separators=(',', ':'))
            if variant == 'located':
                row.update(pairs=n, unlocated=total - n, lagP10=q(lag, .1), lagP25=q(lag, .25), lagP50=q(lag, .5), lagP75=q(lag, .75), lagP90=q(lag, .9), lagMax=max(lag) if lag else None)
            else:
                row.update({f'{variant}Added': added, f'{variant}Left': total - n, f'{variant}AddedLagP50': q(lag_added, .5), f'{variant}AddedLagP90': q(lag_added, .9),
                            f'{variant}LagP75': q(lag, .75), f'{variant}LagP90': q(lag, .9)})
        summ.append(row)
        print(f"{mid}: {row['seats']} 席，唯一定位 {row['pairs']} 条（落后 P50/P75/P90 = {row['lagP50']}/{row['lagP75']}/{row['lagP90']}），定位不唯一 {row['unlocated']} 条；"
              f"hi 补上 {row['hiAdded']}（这些的落后 P50/P90 = {row['hiAddedLagP50']}/{row['hiAddedLagP90']}，全体 P75/P90 = {row['hiLagP75']}/{row['hiLagP90']}），"
              f"lo 补上 {row['loAdded']}（{row['loAddedLagP50']}/{row['loAddedLagP90']}，全体 {row['loLagP75']}/{row['loLagP90']}）")
    # 只重做了部分局时，别把别的局的行冲掉
    path = os.path.join(DATA, 'trace_summary.csv')
    cols = list(summ[0].keys()) if summ else []
    old = []
    if os.path.exists(path):
        old = [r for r in csv.DictReader(open(path)) if r['mid'] not in {s['mid'] for s in summ}]
    rows = sorted(old + summ, key=lambda r: MIDS.index(r['mid']) if r['mid'] in MIDS else 99)
    with open(path, 'w', newline='') as fo:
        w = csv.DictWriter(fo, fieldnames=cols, extrasaction='ignore')
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, '') for c in cols})


if __name__ == '__main__':
    main()
