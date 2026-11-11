#!/usr/bin/env python3
"""m6_all_coload.py — 页面掉队和“同一时段另一支编队也在开局”的并排表（全量，只读 card.json 和 out/_all/joined.csv）。

问题：指令通道差的局（600–1500 拍陆攻+船的落地/放行比 < 0.7）在时间上是成片出现的。包里没有宿主机的记录，能机械对上的只有开局时刻：
  对每个 squad10 的包，看它开局前后 ±W 分钟（默认 10）里有没有 squad20 的包开局（两支编队共 30 个页面同时在跑的代理指标）。
输出：
  1. 2×2：±W 分钟内有 / 没有 squad20 的包 × 通道比值（中位、< 0.7 的局数、≥ 0.9 的局数）、1530 拍人均相对值、决策耗时 avgMs 中位；
  2. 同一张表按大厅人数（card.seededPlayers < 50 / 50–80 / > 80）再分，看是不是人多的局本来就慢；
  3. 按日期、按时间顺序的清单（--list）。
用法：python3 scripts/m6_all_coload.py [--win 10] [--list]
先跑：python3 scripts/m6_all_outcomes.py --csv
说明：这是时间上的并排，不是因果检验。“没有 squad20 的包”只说明数据集里那个时段没有 squad20 的对局包，不保证机器上没有别的负载
     （2026-11-08 晚上的 7 局只有 squad10，一样掉队，单列）。
"""
import csv, json, os, statistics, sys

HERE = os.path.dirname(os.path.abspath(__file__))
R = os.path.join(HERE, '..')
DATA = '/agent/repos/c136-data/bundles'


def main():
    argv = sys.argv[1:]
    W = float(argv[argv.index('--win') + 1]) if '--win' in argv else 10
    J = {r['mid']: r for r in csv.DictReader(open(os.path.join(R, 'out', '_all', 'joined.csv')))}
    rows = []
    for m in sorted(os.listdir(DATA)):
        c = json.load(open(os.path.join(DATA, m, 'card.json')))
        j = J.get(m, {})
        fl = lambda k: float(j[k]) if j.get(k) not in (None, '') else None
        rows.append({'mid': m, 't0': c['timestampMs'] / 1000, 'co': c['cohort'], 'day': c['timeUtc'][:10], 'time': c['timeUtc'][5:16], 'humans': c.get('seededPlayers') or 0,
                     'nd': fl('nd600_1500'), 'rel': fl('rel1530'), 'ms': fl('avgMs'), 'won': int(j.get('won') or 0), 'multi': j.get('multi') == '1'})
    rows.sort(key=lambda r: r['t0'])
    bs = [r for r in rows if r['co'] == 'squad20']
    for r in rows:
        r['near'] = int(any(o is not r and abs(o['t0'] - r['t0']) <= W * 60 for o in bs))

    def line(name, L):
        v = [r['nd'] for r in L if r['nd'] is not None]
        if not v:
            print(f'   {name:<38s} 没有可用的局')
            return
        rel = [r['rel'] for r in L if r['rel'] is not None]
        ms = [r['ms'] for r in L if r['ms'] is not None]
        print(f"   {name:<38s} {len(v):3d} 局 | 落地/放行 中位 {statistics.median(v):.2f}，< 0.7 的 {sum(1 for x in v if x < 0.7)} 局（{100 * sum(1 for x in v if x < 0.7) / len(v):.0f}%），≥ 0.9 的 {sum(1 for x in v if x >= 0.9)} 局"
              f" | 1530 拍人均相对值 {statistics.median(rel):.2f} | 决策耗时 {statistics.median(ms):.2f} 毫秒/拍 | 主队赢 {sum(r['won'] for r in L if r['nd'] is not None)}")

    A = [r for r in rows if r['co'] == 'squad10' and not r['multi'] and r['nd'] is not None]
    d8 = [r for r in A if r['day'] == '2026-11-08']
    rest = [r for r in A if r['day'] != '2026-11-08']
    print(f'#### squad10，有通道比值的 {len(A)} 局；W = ±{W:g} 分钟')
    line('2026-11-08 晚（数据集里只有 squad10）', d8)
    line('11-09 起：W 内有 squad20 的包开局', [r for r in rest if r['near']])
    line('11-09 起：W 内没有 squad20 的包', [r for r in rest if not r['near']])
    print('   —— 按大厅人数再分（11-09 起）')
    for name, lo, hi in (('< 50 人', 0, 50), ('50–80 人', 50, 81), ('> 80 人', 81, 10 ** 6)):
        line(f'{name}，有 squad20', [r for r in rest if r['near'] and lo <= r['humans'] < hi])
        line(f'{name}，没有 squad20', [r for r in rest if not r['near'] and lo <= r['humans'] < hi])
    S = [r for r in rows if r['co'] == 'squad20' and not r['multi'] and r['nd'] is not None]
    print(f'#### squad20，有通道比值的 {len(S)} 局')
    line('全部', S)
    if '--list' in argv:
        print('#### 按开局时间（局 时刻 编队 大厅人数 落地/放行 W内有squad20）')
        for r in rows:
            print(f"   {r['mid']} {r['time']} {r['co']} {r['humans']} {'-' if r['nd'] is None else format(r['nd'], '.2f')} {r['near']}")


if __name__ == '__main__':
    main()
