#!/usr/bin/env python3
"""overlap.py — 某一局的某个墙上时刻，还有哪些局正在进行（只读各包的 card.json 和 results.csv）。
用法: python3 overlap.py <matchId> [--at ISO时间] [--pad 60]
  不给 --at 时取这一局第一条 event=left 的 RESULT 行的时间。
  一局的“进行区间”= card.timestampMs … 最后一条 RESULT 行的 at。--pad 秒：区间两头各放宽多少秒。
输出：同一时刻在跑的其他局（局号、分组、开局时间、最后一条 RESULT 时间、RESULT 行数、left 行数、
      离给定时刻 ±pad 秒内写下的 RESULT 行数及其 event）。
用来判断“全队同时离场”是不是同一时刻别的局也出事（主机或网络层面的事）。
"""
import csv, json, os, sys, datetime

DATA = '/agent/repos/c136-data/bundles'


def ts(s):
    return datetime.datetime.fromisoformat(s.replace('Z', '+00:00')).timestamp()


def main():
    argv = sys.argv[1:]
    mid = argv[0]
    pad = float(argv[argv.index('--pad') + 1]) if '--pad' in argv else 60.0
    res = list(csv.DictReader(open(os.path.join(DATA, mid, 'results.csv'))))
    if '--at' in argv:
        T = ts(argv[argv.index('--at') + 1])
    else:
        T = min(ts(r['at']) for r in res if r['event'] == 'left' and r.get('at'))
    iso = datetime.datetime.fromtimestamp(T, datetime.timezone.utc).isoformat()
    print(f'# {mid} 的时刻 {iso}；找同一时刻（±{pad:.0f} 秒）在跑的其他局')
    n = 0
    for m in sorted(os.listdir(DATA)):
        cp = os.path.join(DATA, m, 'card.json'); rp = os.path.join(DATA, m, 'results.csv')
        if m == mid or not (os.path.exists(cp) and os.path.exists(rp)):
            continue
        card = json.load(open(cp))
        rr = [r for r in csv.DictReader(open(rp)) if r.get('at')]
        if not rr:
            continue
        t0 = card['timestampMs'] / 1000.0; t1 = max(ts(r['at']) for r in rr)
        if not (t0 - pad <= T <= t1 + pad):
            continue
        n += 1
        near = [r for r in rr if abs(ts(r['at']) - T) <= pad]
        ev = {}
        for r in near:
            ev[r['event']] = ev.get(r['event'], 0) + 1
        print(m, card['cohort'], card['timeUtc'], datetime.datetime.fromtimestamp(t1, datetime.timezone.utc).strftime('%H:%M:%S'),
              f"RESULT {len(rr)} 行，left {sum(r['event'] == 'left' for r in rr)} 行；±{pad:.0f} 秒内写下 {len(near)} 行 {ev if ev else ''}")
    print(f'# 同一时刻在跑的其他局：{n} 局')


if __name__ == '__main__':
    main()
