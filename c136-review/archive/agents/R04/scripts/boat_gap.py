#!/usr/bin/env python3
# boat_gap.py — 发船：影子策略想发的条数 对 真号自己记的发船计数 对 录像里执行的发船指令。
#
# 用法：python3 scripts/boat_gap.py <局号> [--edges 630,1500,3000,4284]
#   先要有 tmp/shadow/<局号>/intents.tsv、tmp/truth/<局号>/{cmd.tsv,meta.json}
# 三个口径：
#   影子   = 影子策略（真值状态 + 本局策略源码）在这一段想发的船（kind=boat）条数与兵数
#   真号   = 真实日志 [HL-TICK] 行里 boats= 计数在这一段的增量（策略只在适配层返回真值后才加一）
#   录像   = 这一段里录像执行的发船指令（指令 3）条数
# 影子多、真号不加：分支条件在影子里成立，但真号没走到或适配层没受理（日志里看不出是哪一种）。
import sys, os, csv, json, re, collections

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = '/agent/repos/c136-data/bundles'


def main():
    a = sys.argv[1:]
    mid = a[0]
    edges = [int(x) for x in (a[a.index('--edges') + 1] if '--edges' in a else '630,1500,3000,4284').split(',')]
    bounds = [0] + edges + [10 ** 9]
    check = json.load(open(os.path.join(ROOT, 'tmp', 'shadow', mid, 'check.json')))
    ours = {b['p']: b['bot'] for b in check['bots']}
    ints = collections.defaultdict(list)
    with open(os.path.join(ROOT, 'tmp', 'shadow', mid, 'intents.tsv'), encoding='utf8') as f:
        for r in csv.DictReader(f, delimiter='\t'):
            if r['kind'] == 'boat':
                ints[int(r['p'])].append((int(r['t']), int(r['troops']), int(r['target'])))
    rec = collections.defaultdict(list)
    with open(os.path.join(ROOT, 'tmp', 'truth', mid, 'cmd.tsv'), encoding='utf8') as f:
        for r in csv.DictReader(f, delimiter='\t'):
            if int(r['spawnStep']) < 0 and int(r['id']) == 3:
                rec[int(r['p'])].append(int(r['t']))
    logc = collections.defaultdict(list)   # bot -> [(t, boats)]
    pat = re.compile(r'\[([^\]]+)\] \[HL-TICK\] t=(\d+) .* boats=(\d+)')
    with open(os.path.join(DATA, mid, 'in_game.log'), encoding='utf8', errors='replace') as f:
        for L in f:
            m = pat.search(L)
            if m:
                logc[m.group(1)].append((int(m.group(2)), int(m.group(3))))
    print(f'# {mid} 发船：影子想发 / 真号计数增量 / 录像执行（按时段；兵 = 影子想装的兵）')
    head = '号       ' + ' | '.join(f'[{bounds[i]},{bounds[i+1] if bounds[i+1] < 10**9 else "末"})' for i in range(len(bounds) - 1)) + ' | 全场'
    print(head)
    tot = [0, 0, 0, 0]
    for p, b in ours.items():
        cells = []
        s = sorted(logc.get(b, []))
        for i in range(len(bounds) - 1):
            lo, hi = bounds[i], bounds[i + 1]
            si = [x for x in ints.get(p, []) if lo <= x[0] < hi]
            ri = [t for t in rec.get(p, []) if lo <= t < hi]
            inside = [v for (t, v) in s if lo <= t < hi]
            before = [v for (t, v) in s if t < lo]
            base = before[-1] if before else 0
            d = (inside[-1] - base) if inside else 0
            cells.append(f'{len(si)}（{sum(x[1] for x in si)/1000:.0f}k）/ {d} / {len(ri)}')
        si = ints.get(p, [])
        last = s[-1][1] if s else 0
        cells.append(f'{len(si)}（{sum(x[1] for x in si)/1000:.0f}k）/ {last} / {len(rec.get(p, []))}')
        tot[0] += len(si); tot[1] += sum(x[1] for x in si); tot[2] += last; tot[3] += len(rec.get(p, []))
        print(f'{b:8s} ' + ' | '.join(cells))
    print(f'合计：影子想发 {tot[0]} 条 {tot[1]/1000:.0f}k 兵；真号计数 {tot[2]}；录像执行 {tot[3]}')
    # 影子连发同一落点的最长串
    print('影子对同一落点连发的串（≥5 条）：')
    for p, b in ours.items():
        si = sorted(ints.get(p, []))
        i = 0
        while i < len(si):
            j = i
            while j + 1 < len(si) and si[j + 1][2] == si[i][2] and si[j + 1][0] - si[j][0] <= 240:
                j += 1
            if j - i + 1 >= 5:
                t0, t1 = si[i][0], si[j][0]
                s = sorted(logc.get(b, []))
                c0 = [v for (t, v) in s if t <= t0]
                c1 = [v for (t, v) in s if t <= t1 + 90]
                nrec = sum(1 for t in rec.get(p, []) if t0 <= t <= t1 + 300)
                print(f'  {b} 拍 {t0}~{t1}：{j-i+1} 条，落点像素 {si[i][2]}，想装 {sum(x[1] for x in si[i:j+1])/1000:.0f}k 兵；真号计数 {c0[-1] if c0 else 0}→{c1[-1] if c1 else 0}；录像同段执行 {nrec} 条')
            i = j + 1


main()
