#!/usr/bin/env python3
"""mass_leave.py — 全量机械计数：一局里编队号的 RESULT 行有多少是 event=left，它们在墙上时间上是否扎堆。
只读每个对局包的 card.json 和 results.csv（不读日志、不读录像）。
用法: python3 mass_leave.py [matchId ...] [--win 30] [--min 3] [--all]
  --win 秒   “扎堆”的墙上时间窗口（默认 30 秒）：窗口内 RESULT(left) 行数最多的那一组算一簇
  --min N    只列出最大一簇 >= N 行的局（默认 3）；--all = 把没有 left 的局也列出来
每局一行：
  rows       results.csv 行数（有 RESULT 的号数）
  left       其中 event=left 的行数
  cluster    最大一簇的行数；span = 这一簇首尾相隔几秒；tick = 这一簇各行的局内拍范围；sec = 各行的 seconds（开局算起）范围
  allLeft    是否全部 RESULT 行都是 left
  first      簇里第一行的墙上时间
末尾汇总：left 行总数、落在簇里的行数、全员离场的局数，以及簇的 seconds 分布。
说明：results.csv 的 tick 是该号客户端本地拍，不是 leave 指令在服务器落地的拍（后者要看录像，见 recon_facts.py --section leave）。
"""
import csv, json, os, sys, datetime, statistics

DATA = '/agent/repos/c136-data/bundles'


def ts(s):
    return datetime.datetime.fromisoformat(s.replace('Z', '+00:00')).timestamp()


def main():
    argv = sys.argv[1:]
    win = float(argv[argv.index('--win') + 1]) if '--win' in argv else 30.0
    mn = int(argv[argv.index('--min') + 1]) if '--min' in argv else 3
    show_all = '--all' in argv
    skip = set()
    for k in ('--win', '--min'):
        if k in argv:
            skip.add(argv.index(k)); skip.add(argv.index(k) + 1)
    ids = [a for i, a in enumerate(argv) if i not in skip and not a.startswith('--')] or sorted(os.listdir(DATA))
    print('matchId cohort label endTick rows left cluster span(s) tick sec allLeft first')
    tot_left = tot_in = n_all = n_match = 0
    secs_all = []
    per_cohort = {}
    for mid in ids:
        rp = os.path.join(DATA, mid, 'results.csv'); cp = os.path.join(DATA, mid, 'card.json')
        if not (os.path.exists(rp) and os.path.exists(cp)):
            continue
        card = json.load(open(cp))
        res = list(csv.DictReader(open(rp)))
        n_match += 1
        left = [r for r in res if r['event'] == 'left' and r.get('at')]
        tot_left += len(left)
        pc = per_cohort.setdefault(card['cohort'], {'matches': 0, 'left': 0, 'inCluster': 0, 'clusterMatches': 0, 'allLeft': 0})
        pc['matches'] += 1; pc['left'] += len(left)
        tt = sorted(((ts(r['at']), i, r) for i, r in enumerate(left)), key=lambda x: (x[0], x[1]))
        best = []
        for a in tt:
            cl = [x for x in tt if 0 <= x[0] - a[0] <= win]
            if len(cl) > len(best):
                best = cl
        if len(best) < mn:
            if show_all:
                print(mid, card['cohort'], card['outcome']['resultLabel'], card['outcome']['endTick'], len(res), len(left), len(best), '-', '-', '-', '-', '-')
            continue
        ticks = [int(float(x[2]['tick'])) for x in best]
        secs = [int(float(x[2]['seconds'])) for x in best]
        all_left = len(left) == len(res) and len(best) == len(res)
        tot_in += len(best); n_all += all_left
        pc['inCluster'] += len(best); pc['clusterMatches'] += 1; pc['allLeft'] += all_left
        secs_all.append((mid, statistics.median(secs)))
        print(mid, card['cohort'], card['outcome']['resultLabel'], card['outcome']['endTick'], len(res), len(left), len(best),
              round(best[-1][0] - best[0][0], 1), f"{min(ticks)}-{max(ticks)}", f"{min(secs)}-{max(secs)}", int(all_left), best[0][2]['at'])
    print(f"# 局数 {n_match}；left 行 {tot_left}；落在 >= {mn} 行的簇里 {tot_in}；全部 RESULT 行同簇离场的局 {n_all}")
    for c, v in sorted(per_cohort.items()):
        print(f"#   {c}: 局 {v['matches']}，left 行 {v['left']}，有簇的局 {v['clusterMatches']}（簇内 {v['inCluster']} 行），全员同簇离场 {v['allLeft']} 局")
    if secs_all:
        print('# 各簇 seconds 中位：' + ' '.join(f"{m}:{int(s)}" for m, s in secs_all))


if __name__ == '__main__':
    main()
