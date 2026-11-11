#!/usr/bin/env python3
"""perf_vs_lag.py — 「策略每拍耗时」能不能当客户端主机负载的温度计：它和指令迟到是不是一起涨。

背景：[HL-TICK] 行尾的 avgMs = 策略 act() 开局以来的平均耗时（毫秒/拍，外层 window.__hlPerf 统计）。策略本身只花 0.3–2 毫秒，
      远小于一拍 56 毫秒，所以它不会「算得慢到迟到」；但同一份代码在同样的局面规模下耗时翻倍，说明这台机器当时更慢/更挤。
做法（只读对局包 + 录像命令流，和 pattern_scan.py 的 L 项同一套口径）：
  1) 局级：每局 600–1500 拍各号 avgMs 的中位 对 该局 600–1500 拍「迟到采样占比」（迟到 ≥90 拍或永远没到）的秩相关（Spearman）。
  2) 窗口级：同一个号相邻两条 [HL-TICK]（t1→t2）之间的窗口耗时 = (avg2×t2 − avg1×t1) ÷ (t2 − t1)；
     窗口的迟到 = t2 这条采样的迟到（最新一条指令还要多少拍才执行；窗口里没有新指令的不算）。
     每局内把窗口分成「迟到 ≥90 拍」和「没迟到」两组，比两组窗口耗时的中位；跨局统计「迟到组更高」的局数。
     两组只取同一时段（--t0…--tmax，默认 600–1500 拍）的窗口：策略耗时本身随局面变大而涨，不同时段不能比。
     avgMs 只有两位小数，t 越大窗口耗时的舍入误差越大（±0.005×(t1+t2)÷(t2−t1)，1500 拍处约 ±0.17 毫秒）。
  1b) 局级再按真人数分层（≤40 / 41–70 / >70）：人多的局策略本来就算得久，分层后看同一规模内耗时与迟到是否仍相关。
  3) 号级：每局内各号 600–1500 拍的迟到采样占比 对 该号同期 avgMs 中位 的秩相关，跨局取中位。
用法：python3 scripts/perf_vs_lag.py [局…] [--only A] [--t0 600] [--tmax 1500] [--list]
"""
import bisect
import collections
import csv
import json
import os
import re
import statistics
import sys

SRC = '/agent/repos/c136-data'
CMDS = '/tmp/c136-r05/cmds'
a = sys.argv[1:]
opt = lambda k, d=None: a[a.index(k) + 1] if k in a else d
ids = [x for i, x in enumerate(a) if not x.startswith('--') and (i == 0 or a[i - 1] not in ('--only', '--tmax', '--t0'))]
tmax, tmin = int(opt('--tmax', 1500)), int(opt('--t0', 600))
HEAD = json.load(open(f'{CMDS}/headers.json'))
if not ids:
    ids = sorted(m for m in HEAD if 'error' not in HEAD[m])
if opt('--only'):
    ids = [m for m in ids if m[0] in opt('--only')]
bare = lambda n: re.sub(r'\[[^\]]*\]', '', n or '').strip().lower()
IDMAP = collections.defaultdict(list)
for r in csv.DictReader(open(f'{SRC}/src/tools/identity-map-discovery.csv', encoding='utf-8')):
    IDMAP[r['matchId']].append(r)


def rank(v):
    s = sorted(range(len(v)), key=lambda i: v[i])
    r = [0.0] * len(v)
    i = 0
    while i < len(s):
        j = i
        while j + 1 < len(s) and v[s[j + 1]] == v[s[i]]:
            j += 1
        for q in range(i, j + 1):
            r[s[q]] = (i + j) / 2
        i = j + 1
    return r


def spearman(x, y):
    if len(x) < 4:
        return None
    rx, ry = rank(x), rank(y)
    n = len(x)
    mx, my = sum(rx) / n, sum(ry) / n
    den = (sum((p - mx) ** 2 for p in rx) * sum((q - my) ** 2 for q in ry)) ** 0.5
    return sum((p - mx) * (q - my) for p, q in zip(rx, ry)) / den if den else None


def load(mid):
    B = f'{SRC}/bundles/{mid}'
    hd = HEAD[mid]
    H, names, total = hd['humans'], hd['names'], hd['totalTicks']
    alias = {}
    for r in IDMAP.get(mid, []):
        ch = [x for x in (r.get('nameChain') or '').split('→') if x]
        for n in ch[1:]:
            alias[n] = ch[0]
    al = lambda n: alias.get(n, n)
    me = {}
    for ln in open(f'{B}/in_game.log', encoding='utf-8', errors='replace'):
        m = re.match(r'\d+\t\[([^\]]+)\] \[HL-GAME-INIT\].* me=(\d+)', ln)
        if m:
            me.setdefault(al(m.group(1)), int(m.group(2)))
    traj = collections.defaultdict(list)
    for r in csv.DictReader(open(f'{B}/traj.csv', encoding='utf-8')):
        try:
            traj[al(r['bot'])].append((int(r['t']), int(r['cmds']), float(r['avgMs'])))
        except (ValueError, KeyError, TypeError):
            continue
    don = collections.defaultdict(list)
    if os.path.exists(f'{B}/events.csv'):
        for r in csv.DictReader(open(f'{B}/events.csv', encoding='utf-8')):
            if r['type'] in ('DISPATCH', 'DONATE'):
                try:
                    don[al(r['bot'])].append(int(r['t']))
                except ValueError:
                    pass
    don_logged = sum(len(v) for v in don.values()) > 0
    inrep = {b: p for b, p in me.items() if p < H and p < len(names) and bare(names[p]) == b.lower()}
    pid2bot = {p: b for b, p in inrep.items()}
    ab = collections.defaultdict(list)
    for r in csv.DictReader(open(f'{CMDS}/{mid}.tsv', encoding='utf-8'), delimiter='\t'):
        b = pid2bot.get(int(r['player']))
        if b is None:
            continue
        i = int(r['id'])
        if i in (1, 3, 5) or (i == 2 and not don_logged):
            ab[b].append(int(r['tick']))
    wins = []      # (号, t1, t2, 窗口耗时, 迟到 or None, 没到?)
    for b in inrep:
        L = sorted(traj.get(b, []))
        ex = sorted(ab.get(b, []))
        dl = sorted(don.get(b, []))
        kprev = None
        for j, (t, c, avg) in enumerate(L):
            if t > total:
                break
            k = c - (bisect.bisect_right(dl, t) if don_logged else 0)
            if j > 0:
                t1, _c1, a1 = L[j - 1]
                if t > t1:
                    ms = (avg * t - a1 * t1) / (t - t1)
                    lag = None
                    if kprev is not None and k > kprev:
                        if k > len(ex):
                            lag = 10 ** 6 if t <= total - 600 else None
                        else:
                            lag = max(0, ex[k - 1] - t)
                    wins.append((b, t1, t, ms, lag))
            kprev = k if kprev is None else max(kprev, k)
    return wins, total


G = []
for mid in ids:
    try:
        wins, total = load(mid)
    except Exception as e:  # noqa: BLE001
        print(mid, '出错', e)
        continue
    w1 = [w for w in wins if 600 <= w[2] <= 1500 and w[4] is not None]
    if total < 1500 or len(w1) < 8:
        continue
    late_share = sum(1 for w in w1 if w[4] >= 90) / len(w1)
    ms1 = statistics.median(w[3] for w in wins if 600 <= w[2] <= 1500)
    wl = [w[3] for w in wins if tmin <= w[2] <= tmax and w[4] is not None and w[4] >= 90]
    wo = [w[3] for w in wins if tmin <= w[2] <= tmax and w[4] is not None and w[4] < 90]
    by = collections.defaultdict(lambda: [0, 0, []])
    for w in wins:
        if 600 <= w[2] <= 1500:
            by[w[0]][2].append(w[3])
            if w[4] is not None:
                by[w[0]][1] += 1
                by[w[0]][0] += 1 if w[4] >= 90 else 0
    bx = [(v[0] / v[1], statistics.median(v[2])) for v in by.values() if v[1] >= 3]
    G.append({'m': mid, 'late': late_share, 'ms': ms1, 'humans': HEAD[mid]['humans'], 'msLate': statistics.median(wl) if len(wl) >= 5 else None, 'msOk': statistics.median(wo) if len(wo) >= 5 else None,
              'nLate': len(wl), 'nOk': len(wo), 'rhoBots': spearman([x[0] for x in bx], [x[1] for x in bx]) if len({x[0] for x in bx}) > 1 else None})
for grp in sorted({g['m'][0] for g in G}):
    R = [g for g in G if g['m'][0] == grp]
    lag = [g for g in R if g['late'] >= 0.25]
    ok = [g for g in R if g['late'] < 0.25]
    print(f"===== {grp} 组：{len(R)} 局（录像盖到 1500 拍、600–1500 拍有 ≥8 个可判窗口）=====")
    print(f"  1) 局级秩相关（迟到采样占比 对 600–1500 拍窗口耗时中位）：ρ = {spearman([g['late'] for g in R], [g['ms'] for g in R]):.2f}")
    if lag and ok:
        print(f"     迟到局（占比 ≥25%，{len(lag)} 局）窗口耗时中位的中位 {statistics.median(g['ms'] for g in lag):.2f} 毫秒（{min(g['ms'] for g in lag):.2f}–{max(g['ms'] for g in lag):.2f}）；"
              f"其余 {len(ok)} 局 {statistics.median(g['ms'] for g in ok):.2f} 毫秒（{min(g['ms'] for g in ok):.2f}–{max(g['ms'] for g in ok):.2f}）")
        thr = statistics.median(g['ms'] for g in R)
        hi = [g for g in R if g['ms'] >= thr]
        lo = [g for g in R if g['ms'] < thr]
        print(f"     按窗口耗时中位（{thr:.2f} 毫秒）对半分：耗时高的 {len(hi)} 局里迟到局 {sum(1 for g in hi if g['late'] >= 0.25)} 局；耗时低的 {len(lo)} 局里迟到局 {sum(1 for g in lo if g['late'] >= 0.25)} 局")
    for name, lo_, hi_ in (('真人 ≤40', 0, 40), ('真人 41–70', 41, 70), ('真人 >70', 71, 10 ** 6)):
        S = [g for g in R if lo_ <= g['humans'] <= hi_]
        if len(S) >= 6:
            rho = spearman([g['late'] for g in S], [g['ms'] for g in S])
            sl, so = [g['ms'] for g in S if g['late'] >= 0.25], [g['ms'] for g in S if g['late'] < 0.25]
            print(f"  1b) {name}：{len(S)} 局，ρ = {rho:.2f}；迟到局 {len(sl)} 局窗口耗时中位 {statistics.median(sl) if sl else float('nan'):.2f}，其余 {len(so)} 局 {statistics.median(so) if so else float('nan'):.2f}")
    both = [g for g in R if g['msLate'] is not None and g['msOk'] is not None]
    if both:
        up = sum(1 for g in both if g['msLate'] > g['msOk'])
        print(f"  2) 窗口级（{tmin} ≤ t2 ≤ {tmax}）：同一局里两组窗口都 ≥5 个的 {len(both)} 局中，「迟到 ≥90 拍」的窗口耗时中位高于「没迟到」的 {up} 局；"
              f"差值（迟到 − 没迟到）的中位 {statistics.median(g['msLate'] - g['msOk'] for g in both):+.2f} 毫秒，比值的中位 {statistics.median(g['msLate'] / g['msOk'] for g in both if g['msOk'] > 0):.2f}")
    rb = [g['rhoBots'] for g in R if g['rhoBots'] is not None]
    if rb:
        print(f"  3) 号级：{len(rb)} 局里「各号迟到占比 对 各号窗口耗时中位」的秩相关，中位 {statistics.median(rb):+.2f}，为正的 {sum(1 for x in rb if x > 0)} 局")
    if '--list' in a:
        for g in sorted(R, key=lambda g: -g['ms']):
            f = lambda v: '–' if v is None else f'{v:.2f}'
            print(f"     {g['m']} 迟到占比 {100 * g['late']:.0f}%｜窗口耗时中位 {g['ms']:.2f}｜迟到窗口 {g['nLate']} 个 {f(g['msLate'])}｜没迟到 {g['nOk']} 个 {f(g['msOk'])}｜号级 ρ {f(g['rhoBots'])}")
