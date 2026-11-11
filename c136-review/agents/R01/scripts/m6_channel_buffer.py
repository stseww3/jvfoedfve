#!/usr/bin/env python3
"""m6_channel_buffer.py — 15 局：页面放行的令在录像里是按什么规则落地的。

读 out/<局>/shadow_cmds.csv（影子策略逐条：决策拍 t、是否放行 ok、录像里的落地拍 landedAt）、
out/<局>/replay_cmds.csv（录像里的指令；同一拍内的文件顺序就是引擎的执行顺序）、out/<局>/resim_meta.json。

数五件事（第 5 件：一局里各号是不是一起掉队）：
  1. 一个席位一个服务器拍落地的指令条数（各种指令合计）的分布：上限是多少、上限处有没有堆积；
  2. 同一席位同一拍落地 ≥3 条、且各条的 (种类, pct) 互不相同的批次：录像里的执行顺序和决策顺序相同还是相反
     （直接拿录像的批次到影子的放行序列里找连着的一段，两种顺序对称地各试一次；不用落地拍的对账结果）；
  3. 放行了但录像里没有的陆攻令（丢令；影子里的船令没有做落地对账，不在内）：按决策顺序看，它前后最近的落地令所在的那一拍是不是满的（9 条）；
     有没有丢令夹在同一拍落地的两条令之间；一串满批的开头和结尾各有没有丢令（分辨“先发的留下”还是“后发的留下”）。
     这一项用的落地拍来自 shadow.mjs 的对账：同一席位的令跨拍按决策顺序落地、同拍内倒序（第 2 项独立验证了倒序）；
  4. 出生阶段：同一个号同一步落地 ≥2 条出生指令时的执行顺序；收场不在最后一份落点表上的号各属于哪一种。

另写 reports/m6-data/channel_trace.csv：逐条 (局, 号, 席位, 决策拍, 种类, pct, 落地拍, 落地那一拍这个席位的指令条数)，
给模拟器当通道轨迹用（空的落地拍 = 没落地）。

用法：python3 scripts/m6_channel_buffer.py [--no-trace]
"""
import csv
import json
import os
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
R = os.path.join(HERE, '..')
sys.path.insert(0, HERE)
import spawn_layouts as SL  # noqa: E402

GAMES = ['A075', 'A057', 'A059', 'A094', 'A055', 'A054', 'A031', 'A019', 'A009', 'A023', 'A050', 'A003', 'A005', 'B039', 'B043']
C110 = {'B039', 'B043'}
CAP = 9


def landed(x):
    return x not in ('', '-1', 'None')


def med(v):
    v = sorted(v)
    return v[len(v) // 2] if v else None


def one(mid):
    od = os.path.join(R, 'out', mid)
    meta = json.load(open(os.path.join(od, 'resim_meta.json')))
    shadow_rows = list(csv.DictReader(open(os.path.join(od, 'shadow_cmds.csv'), encoding='utf8')))
    squad_seats = {r['p'] for r in shadow_rows}   # 本队 = 有影子的号（A057 的 resim_meta 里还登记了同局另一支编队的号，那些算“其他真人”）
    humans = meta['humans']
    per_tick = Counter()          # (席位, 拍) -> 条数（各种指令）
    rep_sig = defaultdict(list)   # (席位, 拍) -> [(种类, pct)]，文件顺序
    spawn = defaultdict(list)     # 席位 -> [(步, x, y)]，文件顺序
    W = meta['W']
    rep_ab = 0                    # 录像里本队落地的陆攻令
    for r in csv.DictReader(open(os.path.join(od, 'replay_cmds.csv'), encoding='utf8')):
        t = int(r['tick'])
        if r['kind'] == 'spawn':
            px = int(r['dX'])
            spawn[int(r['player'])].append((int(r['step']), px % W, px // W))
            continue
        if t < 0:
            continue
        per_tick[(r['player'], t)] += 1
        if r['kind'] == 'attack' and r['player'] in squad_seats:
            rep_ab += 1
        if r['kind'] in ('attack', 'boat', 'donate'):
            rep_sig[(r['player'], t)].append((r['kind'], int(r['dX'])))
    out = {'mid': mid}
    # 1. 每席位每拍的条数
    sq = Counter(v for (p, t), v in per_tick.items() if p in squad_seats)
    ot = Counter(v for (p, t), v in per_tick.items() if p not in squad_seats and int(p) < humans)
    out['sqHist'] = sq
    out['otHist'] = ot

    rows = [r for r in shadow_rows if r['ok'] == '1']
    # 2. 批次里的执行顺序。不用落地拍的对账结果（那一步本身假定了同拍内倒序），直接拿录像里的批次到影子的放行序列里找：
    #    同一席位同一拍 ≥3 条陆攻/捐兵、(种类, pct) 互不相同的批次，在落地拍之前 950 拍以内的影子放行序列里，
    #    找“连着的一段、顺序相同”和“连着的一段、顺序相反”，两种假设对称地各试一次。
    seq = defaultdict(list)
    for r in rows:
        if r['kind'] in ('attack', 'donate'):
            seq[r['p']].append((int(r['t']), r['kind'], int(r['pct'])))
    order = Counter()
    for (p, t), sig in rep_sig.items():
        sig = [x for x in sig if x[0] in ('attack', 'donate')]
        S = seq.get(p)
        if not S or len(sig) < 3:
            continue
        if len(set(sig)) < len(sig):
            order['ambiguous'] += 1
            continue
        n = len(sig)
        cand = [i for i in range(len(S) - n + 1) if S[i + n - 1][0] <= t and t - S[i][0] <= 950]
        fwd = any([(S[i + k][1], S[i + k][2]) for k in range(n)] == sig for i in cand)
        rev = any([(S[i + k][1], S[i + k][2]) for k in range(n)] == sig[::-1] for i in cand)
        order['both' if fwd and rev else 'issue' if fwd else 'reverse' if rev else 'neither'] += 1
    out['order'] = order

    # 3. 丢令和满批
    by = defaultdict(list)
    for r in rows:
        if r['kind'] == 'attack':     # 影子里的船令（boatTo）没有做落地对账，这里只数陆攻令
            by[(r['bot'], r['p'])].append(r)
    drop = Counter()
    phase = Counter()             # (丢令的决策拍所在时段, 挨着 9 条的批 / 只挨着 7–8 条的批 / 都不挨)
    prev_size = Counter()         # 在满批前面的丢令：它前一条落地令所在那一拍的条数
    runs_none, flush_gap = [], []
    chain, end_gap = Counter(), []
    lag_full, lag_single, span_full = [], [], []
    seen_batch = set()
    for (b, p), L in by.items():
        L.sort(key=lambda r: int(r['t']))
        n = len(L)
        la = [int(r['landedAt']) if landed(r['landedAt']) else None for r in L]
        size = [per_tick[(p, x)] if x is not None else None for x in la]
        for i in range(n):
            if la[i] is None:
                continue
            d = la[i] - int(L[i]['t'])
            if size[i] >= CAP:
                lag_full.append(d)
                if (p, la[i]) not in seen_batch:
                    seen_batch.add((p, la[i]))
                    ts = [int(L[j]['t']) for j in range(n) if la[j] == la[i]]
                    span_full.append(max(ts) - min(ts))
            elif size[i] == 1:
                lag_single.append(d)
        i = 0
        while i < n:
            if la[i] is not None:
                i += 1
                continue
            j = i
            while j < n and la[j] is None:
                j += 1
            m = j - i
            left = size[i - 1] if i > 0 else None
            right = size[j] if j < n else None
            if i > 0 and j < n and la[i - 1] == la[j]:
                drop['inside'] += m
            if right is None:
                drop['tail'] += m          # 这个号之后再没有令落地（页面停住、被移出或阵亡）
            elif left is None:
                drop['head'] += m
            elif left >= CAP and right >= CAP:
                drop['between_full'] += m
            elif left >= CAP:
                drop['after_full'] += m
            elif right >= CAP:
                drop['before_full'] += m
            else:
                drop['no_full'] += m
            if left is not None and right is not None:
                big = max(left, right)
                cls = 'adj9' if big >= CAP else 'adj78' if big >= CAP - 2 else 'none'
                for k in range(i, j):
                    td = int(L[k]['t'])
                    ph = '0–600' if td < 600 else '600–1500' if td < 1500 else '1500–3000' if td < 3000 else '3000+'
                    phase[(ph, cls)] += 1
                if cls == 'none':
                    runs_none.append(m)
                if right >= CAP > left:
                    prev_size[left] += m
            i = j
        # 一串满批的开头和结尾：满批的前一次落地是正常的（那一拍 ≤2 条）时，两者之间有没有丢令；
        # 满批的后一次落地是正常的时，两者之间有没有丢令。“先发的留下”预言：开头没有、结尾有；“后发的留下”相反。
        land_idx = [k for k in range(n) if la[k] is not None]
        groups = []
        for k in land_idx:
            if groups and la[groups[-1][-1]] == la[k]:
                groups[-1].append(k)
            else:
                groups.append([k])
        for gi, gcur in enumerate(groups):
            if size[gcur[0]] < CAP:
                continue
            if gi > 0 and size[groups[gi - 1][0]] <= 2:
                chain['start_drop' if gcur[0] - groups[gi - 1][-1] > 1 else 'start_clean'] += 1
            if gi + 1 < len(groups) and size[groups[gi + 1][0]] <= 2:
                gap = groups[gi + 1][0] - gcur[-1] - 1
                chain['end_drop' if gap > 0 else 'end_clean'] += 1
                if gap > 0:
                    end_gap.append(gap)
        # 同一个号相邻两个满批的落地拍间隔、一个满批里最早那条令的延迟
        fl = sorted({x for x, sz in zip(la, size) if x is not None and sz >= CAP})
        for a, b2 in zip(fl, fl[1:]):
            flush_gap.append(b2 - a)
        drop['released'] += n
        drop['landed'] += sum(1 for x in la if x is not None)
    drop['replayRows'] = rep_ab
    out['drop'] = drop
    out['phase'] = phase
    out['prevSize'] = prev_size
    out['runsNone'] = runs_none
    out['flushGap'] = flush_gap
    out['chain'] = chain
    out['endGap'] = end_gap
    out['lagFull'] = lag_full
    out['lagSingle'] = lag_single
    out['spanFull'] = span_full

    # 4. 出生阶段
    sp = Counter()
    if mid not in C110:
        solves = SL.read_solves([mid])
        roster = {b for sv in solves for b in sv['pos']}
        squad = {b: p for b, p in meta['squad'].items() if b in roster}
        versions = []
        for s in solves:
            key = tuple(sorted(s['pos'].items()))
            if not any(v['key'] == key for v in versions):
                versions.append({'key': key, 'pos': s['pos']})

        def vof(b, xy):
            return [i for i, v in enumerate(versions, 1) if v['pos'].get(b) == xy]

        for b, p in squad.items():
            L = sorted(spawn.get(p, []), key=lambda c: c[0])   # 稳定排序：同一步内保持文件顺序
            if not L:
                sp['noCmd'] += 1
                continue
            steps = defaultdict(list)
            for st, x, y in L:
                steps[st].append((x, y))
            for st, pts in steps.items():
                if len(pts) < 2:
                    continue
                vs = [vof(b, xy) for xy in pts]
                if any(not v for v in vs):
                    sp['multiOffTable'] += 1
                    continue
                first = [v[0] for v in vs]
                if len(set(first)) < len(first):
                    sp['multiSame'] += 1
                elif first == sorted(first, reverse=True):
                    sp['multiReverse'] += 1
                elif first == sorted(first):
                    sp['multiIssue'] += 1
                else:
                    sp['multiMixed'] += 1
            fin = steps[L[-1][0]]
            applied = fin[-1]
            lastpt = versions[-1]['pos'].get(b) if versions else None
            if applied == lastpt:
                sp['onLast'] += 1
                continue
            va = vof(b, applied)
            newest = max((max(vof(b, xy)) if vof(b, xy) else 0) for xy in fin)
            if len(fin) >= 2 and va and max(va) < newest:
                sp['offInStep'] += 1          # 最后一步里，旧表的指令排在新表的指令后面执行
            elif any((x, y) == lastpt for _, x, y in L):
                sp['offLaterStep'] += 1       # 最后一份表的指令落地过，之后的步里又落地了一条旧表的指令
            else:
                sp['offNever'] += 1           # 最后一份表的指令没有落地
    out['spawn'] = sp

    trace = []
    for r in rows:
        if r['kind'] not in ('attack', 'donate'):
            continue
        la = int(r['landedAt']) if landed(r['landedAt']) else None
        trace.append((mid, r['bot'], r['p'], int(r['t']), r['kind'], r['pct'], '' if la is None else la,
                      '' if la is None else per_tick[(r['p'], la)]))
    out['trace'] = trace
    return out


def hist_txt(h, lo=1):
    return ' '.join(f'{k}条×{h[k]}' for k in sorted(h) if k >= lo)


def main():
    res = [one(m) for m in GAMES]
    print('== 1. 一个席位一个服务器拍落地的指令条数（各种指令合计；只列 ≥6 条的拍数）')
    print('局 | 本队：最多 · ≥6 条的分布 | 其他真人：最多 · ≥6 条的分布')
    tot_sq, tot_ot = Counter(), Counter()
    for o in res:
        tot_sq.update(o['sqHist'])
        tot_ot.update(o['otHist'])
        print(f"{o['mid']} | {max(o['sqHist'])} · {hist_txt(o['sqHist'], 6)} | {max(o['otHist']) if o['otHist'] else 0} · {hist_txt(o['otHist'], 6)}")
    print(f"# 15 局合计 本队：最多 {max(tot_sq)} 条；{hist_txt(tot_sq, 6)}；其他真人：最多 {max(tot_ot)} 条；{hist_txt(tot_ot, 6)}")

    print()
    print('== 2. 录像里同一席位同一拍 ≥3 条陆攻/捐兵、各条 (种类, pct) 互不相同的批次：到影子的放行序列里找连着的一段（两种顺序各试一次，不依赖落地拍的对账）')
    print('局 | 只有“和决策顺序相反”对得上 | 只有“和决策顺序相同”对得上 | 两种都对得上 | 都对不上 | 分不出（批里有重复的 pct）')
    T = Counter()
    T110 = Counter()
    for o in res:
        c = o['order']
        (T110 if o['mid'] in C110 else T).update(c)
        print(f"{o['mid']} | {c['reverse']} | {c['issue']} | {c['both']} | {c['neither']} | {c['ambiguous']}")
    A = T + T110
    print(f"# 15 局合计：pct 互不相同的批次 {A['reverse'] + A['issue'] + A['both'] + A['neither']} 个，只有倒序对得上的 {A['reverse']} 个，只有正序对得上的 {A['issue']} 个，两种都对得上的 {A['both']} 个，都对不上的 {A['neither']} 个"
          f"（其中 c110 的 2 局 {T110['neither']} 个）；批里有重复 pct、分不出的 {A['ambiguous']} 个")

    print()
    print('== 3. 放行了但录像里没有的陆攻令（按决策顺序看它前后最近的落地令；船令没有做落地对账，不在内）')
    print('局 | 放行 → 落地 | 丢令 | 前一条落地令所在的拍是满的（9 条） | 后一条所在的拍是满的 | 前后都是满的 | 前后都不满 | 这个号之后再没有令落地 | 夹在同一拍落地的两条令之间 | 满批里的令：决策到落地的拍数 中位 / 最大 · 一批横跨的决策拍 中位 | 单条落地的令：拍数中位')
    D = {'c116': Counter(), 'c110': Counter()}
    LF = {'c116': [], 'c110': []}
    for o in res:
        d = o['drop']
        key = 'c110' if o['mid'] in C110 else 'c116'
        D[key].update(d)
        LF[key] += o['lagFull']
        lost = d['released'] - d['landed']
        lf = o['lagFull']
        print(f"{o['mid']} | {d['released']} → {d['landed']} | {lost} | {d['after_full']} | {d['before_full']} | {d['between_full']} | {d['no_full']} | {d['tail']} | {d['inside']} | "
              f"{med(lf) if lf else '-'} / {max(lf) if lf else '-'} · {med(o['spanFull']) if o['spanFull'] else '-'} | {med(o['lagSingle']) if o['lagSingle'] else '-'}")
    for key, label in (('c116', 'c116 的 13 局'), ('c110', 'c110 的 2 局（影子是近似的）')):
        d = D[key]
        lost = d['released'] - d['landed']
        adj = d['after_full'] + d['before_full'] + d['between_full']
        mid_ = adj + d['no_full']
        print(f"# {label}，陆攻令：放行 {d['released']} 条，落地 {d['landed']} 条，丢 {lost} 条。其中这个号之后再没有令落地的 {d['tail']} 条、之前没有的 {d['head']} 条；"
              f"其余 {mid_} 条里，挨着满批的 {adj} 条（{100 * adj / mid_:.0f}%；紧跟在满批后面的 {d['after_full']}，夹在两个满批之间的 {d['between_full']}，在满批前面的 {d['before_full']}），"
              f"前后都不满的 {d['no_full']} 条；夹在同一拍落地的两条令之间的 {d['inside']} 条；满批里的令从决策到落地的拍数中位 {med(LF[key])}")

    ALL = D['c116'] + D['c110']
    print(f"# 对账的完整程度：15 局录像里本队落地的陆攻令 {ALL['replayRows']} 条，对上影子决策的 {ALL['landed']} 条，没对上的 {ALL['replayRows'] - ALL['landed']} 条（{100 * (ALL['replayRows'] - ALL['landed']) / ALL['replayRows']:.0f}%）")

    print()
    print('== 3b. c116 的 13 局，前后都有落地令的丢令，按决策拍分段：挨着 9 条的批 / 只挨着 7–8 条的批 / 都不挨')
    print('时段 | 丢令 | 挨着 9 条的批 | 只挨着 7–8 条的批 | 都不挨')
    PH, PS, RN, FG = Counter(), Counter(), [], []
    for o in res:
        if o['mid'] in C110:
            continue
        PH.update(o['phase'])
        PS.update(o['prevSize'])
        RN += o['runsNone']
        FG += o['flushGap']
    for ph in ('0–600', '600–1500', '1500–3000', '3000+'):
        a, b, c = PH[(ph, 'adj9')], PH[(ph, 'adj78')], PH[(ph, 'none')]
        n = a + b + c
        if n:
            print(f"{ph} | {n} | {a}（{100 * a / n:.0f}%）| {b}（{100 * b / n:.0f}%）| {c}（{100 * c / n:.0f}%）")
    print(f"# 在满批前面的丢令，它前一条落地令所在那一拍的条数：" + ' '.join(f'{k}条:{v}' for k, v in sorted(PS.items(), reverse=True)))
    big = [x for x in RN if x >= 20]
    print(f"# 前后都不挨 7 条以上的批的丢令共 {sum(RN)} 条、{len(RN)} 段；其中一段连丢 ≥20 条的有 {len(big)} 段、{sum(big)} 条（整段丢弃）")
    CH, EG = Counter(), []
    for o in res:
        if o['mid'] not in C110:
            CH.update(o['chain'])
            EG += o['endGap']
    print(f"# 一串满批的开头（满批的前一次落地是正常的，那一拍 ≤2 条）{CH['start_clean'] + CH['start_drop']} 处：两者之间没有丢令的 {CH['start_clean']} 处，有丢令的 {CH['start_drop']} 处；"
          f"结尾（满批的后一次落地是正常的）{CH['end_clean'] + CH['end_drop']} 处：两者之间有丢令的 {CH['end_drop']} 处（丢的条数中位 {med(EG)}），没有的 {CH['end_clean']} 处")
    FG.sort()
    if FG:
        print(f"# 同一个号相邻两个满批的落地拍间隔：{len(FG)} 个，P25 / 中位 / P75 = {FG[len(FG) // 4]} / {FG[len(FG) // 2]} / {FG[3 * len(FG) // 4]} 拍")

    print()
    print('== 4. 出生阶段（c116 的 13 局）')
    print('局 | 同一个号同一步落地 ≥2 条出生指令：新表的先执行、旧表的后执行 / 顺序相同 / 其他 / 同一个点重复 / 有点不在任何表里 | 收场：在最后一份表上 / 最后一步里旧表的指令排在新表后面执行 / 最后一份表的指令落地过、后面的步又落地了旧表的指令 / 最后一份表的指令没落地 / 没有出生指令落地')
    S = Counter()
    for o in res:
        if o['mid'] in C110:
            continue
        s = o['spawn']
        S.update(s)
        print(f"{o['mid']} | {s['multiReverse']} / {s['multiIssue']} / {s['multiMixed']} / {s['multiSame']} / {s['multiOffTable']} | "
              f"{s['onLast']} / {s['offInStep']} / {s['offLaterStep']} / {s['offNever']} / {s['noCmd']}")
    seats = S['onLast'] + S['offInStep'] + S['offLaterStep'] + S['offNever'] + S['noCmd']
    print(f"# 合计：同一步多条出生指令能分出顺序的 {S['multiReverse'] + S['multiIssue'] + S['multiMixed']} 次，新表先执行、旧表后执行的 {S['multiReverse']} 次，顺序相同的 {S['multiIssue']} 次，其他 {S['multiMixed']} 次。"
          f"{seats} 个号收场：在最后一份表上 {S['onLast']} 个；不在的 {S['offInStep'] + S['offLaterStep'] + S['offNever']} 个 = 最后一步里旧表的指令后执行 {S['offInStep']} 个"
          f" + 最后一份表的指令落地过、后面又落地了旧表的指令 {S['offLaterStep']} 个 + 最后一份表的指令没落地 {S['offNever']} 个；没有出生指令落地 {S['noCmd']} 个")

    print()
    print('== 5. 掉队是不是整局一起的：各号第一次出现延迟 ≥ 50 拍的落地（落地拍，从小到大）；600–1500 拍落地的令各号的延迟中位（从小到大）')
    print('局 | 号数 | 第一次延迟 ≥ 50 拍的落地拍 | 从来没有的号 | 600–1500 拍落地的令：各号延迟中位')
    for o in res:
        by_bot = defaultdict(list)
        for row in o['trace']:
            if row[6] != '':
                by_bot[row[1]].append((row[6], row[6] - row[3]))
        first, meds = [], []
        for b, L in by_bot.items():
            f = [la for la, d in L if d >= 50]
            first.append(min(f) if f else None)
            v = [d for la, d in L if 600 <= la < 1500]
            if v:
                meds.append(med(v))
        ok = sorted(x for x in first if x is not None)
        print(f"{o['mid']} | {len(by_bot)} | {' '.join(map(str, ok)) or '-'} | {sum(1 for x in first if x is None)} | {' '.join(map(str, sorted(meds)))}")

    if '--no-trace' not in sys.argv:
        dst = os.path.join(R, 'reports', 'm6-data', 'channel_trace.csv')
        n = 0
        with open(dst, 'w', newline='', encoding='utf8') as f:
            w = csv.writer(f)
            w.writerow(['mid', 'bot', 'seat', 'tDecide', 'kind', 'pct', 'landedAt', 'seatCmdsThatTick'])
            for o in res:
                for row in sorted(o['trace'], key=lambda x: (x[1], x[3])):
                    w.writerow(row)
                    n += 1
        print()
        print(f'# 已写 reports/m6-data/channel_trace.csv（{n} 行：15 局本队每条放行的陆攻令、捐兵令的决策拍和落地拍；船令没有做落地对账，不在内）')
        # 把逐条轨迹压成“一次落地”一行：同一个号按决策顺序，落在同一拍的令连同它们后面丢掉的令算一次
        dst2 = os.path.join(R, 'reports', 'm6-data', 'channel_bursts.csv')
        nb = 0
        with open(dst2, 'w', newline='', encoding='utf8') as f:
            w = csv.writer(f)
            w.writerow(['mid', 'bot', 'seat', 'landTick', 'kept', 'seatCmdsThatTick', 'firstDecide', 'lastDecideKept', 'lag', 'droppedAfter', 'lastDecideDropped'])
            for o in res:
                by_bot = defaultdict(list)
                for row in o['trace']:
                    by_bot[(row[1], row[2])].append(row)
                for (b, p), L in sorted(by_bot.items()):
                    L.sort(key=lambda x: x[3])
                    cur = None
                    for row in L:
                        la = row[6]
                        if la != '':
                            if cur and cur[3] == la:
                                cur[4] += 1
                                cur[7] = row[3]
                            else:
                                if cur:
                                    w.writerow(cur)
                                    nb += 1
                                cur = [o['mid'], b, p, la, 1, row[7], row[3], row[3], la - row[3], 0, '']
                        elif cur:
                            cur[9] += 1
                            cur[10] = row[3]
                    if cur:
                        w.writerow(cur)
                        nb += 1
        print(f'# 已写 reports/m6-data/channel_bursts.csv（{nb} 行：一个号一次落地一行——落地拍、落地几条、最早和最晚那条的决策拍、延迟、后面连着丢了几条）')


if __name__ == '__main__':
    main()
