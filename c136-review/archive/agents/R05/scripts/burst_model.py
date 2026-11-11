#!/usr/bin/env python3
"""burst_model.py — 没落地的指令丢在哪里：检验「任意连续 3 个回合里一个玩家最多执行 9 条，多出来的丢掉」。

背景（实测，见 round_limit.py）：服务器每 7 拍一个回合，指令只在回合第一拍执行；全部录像、全部玩家，
      任意连续 3 个回合（21 拍）里同一个玩家执行的指令合计从不超过 9 条；一个回合执行满 9 条之后的两个回合，这个玩家一条指令都没有执行过。
要检验的说法：客户端落后时一口气补跑很多本地拍，这些拍里下的指令在同一个回合到达服务器；服务器只收先到的、把 3 回合窗口填满 9 条为止（一批内倒序执行），后面的丢掉。
如果成立，没落地的决策应该紧跟在「这个号的 3 回合窗口已满 9 条」的那一批后面。

输入：/tmp/c136-r05/work/<局>-delay.json 的 decisions[]（delay_account.py 的逐条配对：号、决策拍、类型、目标类别、状态 hit/dead/void/lost、落地拍、延迟…）；
      只看陆攻和出船的决策（捐兵不算）
      /tmp/c136-r05/cmds/<局>.tsv（录像命令流：算每个号每个回合执行了几条，所有指令种类都算，选点和离场除外）
      /tmp/c136-r05/truth/<局>.json（号 ↔ 座位）
做法（每个号独立，按决策拍排序）：
  每条没落地（lost）的决策，找它前面最近一条落地的决策（落地回合 T），看包含 T 的三个 3 回合窗口
      （T−14…T、T−7…T+7、T…T+14）里这个号执行条数合计的最大值：
      = 9 → 「紧跟满窗」（其中 T 这一个回合就满 9 条的另计「紧跟满回合」）；否则看 T 这个回合的条数：3–8 条 → 「紧跟未满的批」；1–2 条 → 「紧跟单条」；
      前面没有落地的 → 「开头」。
  爆发 = 落在同一个回合的一批决策 + 紧跟其后、到下一条落地决策之前的全部没落地决策。
      爆发长度 = 条数、本地拍跨度；爆发起点落后 = 落地拍 − 第一条的决策拍；爆发终点落后 = 落地拍 − 最后一条（含没落地的）的决策拍。
      「满回合爆发」= 回合里执行满 9 条的爆发。
用法：python3 scripts/burst_model.py <局…> [--t0 0 --t1 99999] [--list 局:号] [--json FILE]
"""
import csv
import json
import statistics as st
import sys
from collections import Counter, defaultdict

a = sys.argv[1:]
val = lambda k, d=None: (a[a.index(k) + 1] if k in a else d)
T0, T1 = int(val('--t0', 0)), int(val('--t1', 99999))
lst = val('--list')
jout = val('--json')
skip = set()
for k in ('--t0', '--t1', '--list', '--json'):
    if k in a:
        skip |= {a.index(k), a.index(k) + 1}
mids = [x for i, x in enumerate(a) if i not in skip]
W = '/tmp/c136-r05/work'
med = lambda v: (st.median(v) if v else None)
f0 = lambda v: '–' if v is None else f'{v:.0f}'
pc = lambda x, y: f'{100 * x / y:.0f}%' if y else '–'
OUT = {}
TOT = Counter()
for mid in mids:
    D = json.load(open(f'{W}/{mid}-delay.json'))
    J = json.load(open(f'/tmp/c136-r05/truth/{mid}.json'))
    seat = {s['bot']: s['p'] for s in J['squad']}
    occ = Counter()
    for r in csv.DictReader(open(f'/tmp/c136-r05/cmds/{mid}.tsv', encoding='utf-8'), delimiter='\t'):
        t, i = int(r['tick']), int(r['id'])
        if t >= 0 and i not in (0, 8, 9):
            occ[(int(r['player']), t)] += 1
    by = defaultdict(list)
    for r in D['decisions']:
        if r[2] in ('attack', 'boat'):      # 捐兵另算（没执行的捐兵多数是被受捐方的入账上限挡掉，见捐兵账）
            by[r[0]].append(r)
    cls = Counter()
    bursts = []
    for bot, rows in by.items():
        rows.sort(key=lambda r: r[1])
        p = seat.get(bot)
        prev = None          # 前面最近一条落地的决策
        cur = None           # 当前爆发
        for r in rows:
            t, status, T = r[1], r[4], r[5]
            if status == 'lost':
                if T0 <= t < T1:
                    if prev is None:
                        cls['开头'] += 1
                    else:
                        Tp = prev[5]
                        n = occ[(p, Tp)]
                        w = max(sum(occ[(p, Tp + 7 * j)] for j in range(k0, k0 + 3)) for k0 in (-2, -1, 0))
                        cls['紧跟满回合' if n >= 9 else '紧跟满窗' if w >= 9 else '紧跟未满的批' if n >= 3 else '紧跟单条'] += 1
                if cur is not None:
                    cur['lost'] += 1
                    cur['tLast'] = t
            else:
                if cur is None or cur['T'] != T:
                    if cur is not None:
                        bursts.append(cur)
                    cur = {'bot': bot, 'T': T, 'occ': occ[(p, T)], 'landed': 0, 'lost': 0, 'tFirst': t, 'tLast': t, 'tLastLanded': t,
                           'win': max(sum(occ[(p, T + 7 * j)] for j in range(k0, k0 + 3)) for k0 in (-2, -1, 0))}
                elif cur['lost']:
                    # 同一个回合的决策被没落地的隔开：算进同一个爆发（批内次序不连续的少数情形）
                    pass
                cur['landed'] += 1
                cur['tLast'] = t
                cur['tLastLanded'] = t
                prev = r
        if cur is not None:
            bursts.append(cur)
    bw = [b for b in bursts if T0 <= b['tFirst'] < T1]
    full = [b for b in bw if b['win'] >= 9]                       # 3 回合窗口满 9 条
    part = [b for b in bw if b['win'] < 9 and b['occ'] >= 3]
    single = [b for b in bw if b['win'] < 9 and b['occ'] < 3]
    lost_tot = sum(cls.values())
    o = {
        'lost': lost_tot, 'lostClass': dict(cls),
        'bursts': {'full': len(full), 'partial': len(part), 'single': len(single)},
        'lostAfter': {'full': sum(b['lost'] for b in full), 'partial': sum(b['lost'] for b in part), 'single': sum(b['lost'] for b in single)},
        'fullWithLoss': sum(1 for b in full if b['lost']),
        'partialWithLoss': sum(1 for b in part if b['lost']),
        'singleWithLoss': sum(1 for b in single if b['lost']),
        'fullBurstSize': med([b['landed'] + b['lost'] for b in full]),
        'fullBurstSpan': med([b['tLast'] - b['tFirst'] for b in full]),
        'fullLagStart': med([b['T'] - b['tFirst'] for b in full]),
        'fullLagEnd': med([b['T'] - b['tLast'] for b in full]),
        'fullLagEndMin': min([b['T'] - b['tLast'] for b in full], default=None),
        'singleLag': med([b['T'] - b['tFirst'] for b in single]),
    }
    OUT[mid] = o
    for k2, v in cls.items():
        TOT[k2] += v
    TOT['lost'] += lost_tot
    for k2 in ('full', 'partial', 'single'):
        TOT['b_' + k2] += o['bursts'][k2]
        TOT['l_' + k2] += o['lostAfter'][k2]
    TOT['fullWithLoss'] += o['fullWithLoss']
    TOT['partialWithLoss'] += o['partialWithLoss']
    TOT['singleWithLoss'] += o['singleWithLoss']
    sat = cls['紧跟满回合'] + cls['紧跟满窗']
    print(f"== {mid}（决策拍 {T0}–{T1 if T1 < 99999 else '终局'}）：没落地 {lost_tot} 条｜紧跟「3 回合窗口已满 9 条」的 {sat}（{pc(sat, lost_tot)}；其中单个回合就满 9 条的 {cls['紧跟满回合']}）、"
          f"紧跟未满的批（3–8 条）{cls['紧跟未满的批']}、紧跟单条（1–2 条）{cls['紧跟单条']}、开头 {cls['开头']}")
    print(f"   落地回合：窗口满 9 条的 {len(full)} 个（其中后面跟着没落地决策的 {o['fullWithLoss']} 个）、没满而本回合 3–8 条的 {len(part)} 个（{o['partialWithLoss']} 个）、没满而 1–2 条的 {len(single)} 个（{o['singleWithLoss']} 个）")
    if full:
        print(f"   满窗爆发：条数中位 {f0(o['fullBurstSize'])}（落地的 + 丢掉的）、本地拍跨度中位 {f0(o['fullBurstSpan'])}；落地拍 − 第一条决策拍 中位 {f0(o['fullLagStart'])}、"
              f"落地拍 − 最后一条决策拍 中位 {f0(o['fullLagEnd'])}（最小 {f0(o['fullLagEndMin'])}）｜单条落地的延迟中位 {f0(o['singleLag'])}")
    if lst and lst.split(':')[0] == mid:
        bot = lst.split(':')[1]
        for b in bursts:
            if b['bot'] == bot and T0 <= b['tFirst'] < T1:
                print(f"     {bot} 回合 {b['T']}（执行 {b['occ']} 条）：决策拍 {b['tFirst']}–{b['tLastLanded']} 落地 {b['landed']} 条；随后到 {b['tLast']} 拍没落地 {b['lost']} 条｜"
                      f"落后 起点 {b['T'] - b['tFirst']}、终点 {b['T'] - b['tLast']}")
if len(mids) > 1:
    L = TOT['lost']
    S9 = TOT['紧跟满回合'] + TOT['紧跟满窗']
    print(f"== 合计 {len(mids)} 局：没落地 {L} 条｜紧跟「3 回合窗口已满 9 条」的 {S9}（{pc(S9, L)}；其中单个回合就满 9 条的 {TOT['紧跟满回合']}）、紧跟未满的批 {TOT['紧跟未满的批']}（{pc(TOT['紧跟未满的批'], L)}）、"
          f"紧跟单条 {TOT['紧跟单条']}（{pc(TOT['紧跟单条'], L)}）、开头 {TOT['开头']}")
    print(f"   落地回合后面跟着没落地决策的比例：窗口满 9 条的 {TOT['fullWithLoss']}/{TOT['b_full']}（{pc(TOT['fullWithLoss'], TOT['b_full'])}）、"
          f"没满而本回合 3–8 条的 {TOT['partialWithLoss']}/{TOT['b_partial']}（{pc(TOT['partialWithLoss'], TOT['b_partial'])}）、没满而 1–2 条的 {TOT['singleWithLoss']}/{TOT['b_single']}（{pc(TOT['singleWithLoss'], TOT['b_single'])}）")
if jout:
    json.dump(OUT, open(jout, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('→', jout)
