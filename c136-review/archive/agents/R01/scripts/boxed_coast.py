#!/usr/bin/env python3
"""boxed_coast.py — 被围死的号有没有海岸（能不能出海）。读 out/<mid>/resim_squad.csv（30 拍一个采样点）。
“围死”= 该采样点没有敌方邻居、没有 AI 邻居、没有离场壳邻居、没有无主地接壤，且自己还在场（state=0），t >= 600。
waterC = 该号领土里挨着水的边界格数（resim_lib 的统计）；0 = 内陆，一条船也出不了。
用法: python3 boxed_coast.py <matchId> [--dens 115]
  --dens  另数“围死且密度 >= 这个值”的采样点（Vb idleBoats L5031：还有队友在陆上有前线时，密度不到 115 不出海）
输出：每个号 围死采样点数、其中有水边的、全程 waterC 最大值、围死且高密度的采样点数及其中有水边的；末行合计。
"""
import csv, os, sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    a = sys.argv[1:]
    mid = a[0]
    dth = float(a[a.index('--dens') + 1]) if '--dens' in a else 115.0
    rows = list(csv.DictReader(open(os.path.join(HERE, '..', 'out', mid, 'resim_squad.csv'))))
    by = defaultdict(list)
    for r in rows:
        by[r['bot']].append(r)
    tot = [0, 0, 0, 0]
    print(f'== {mid} 围死的号与海岸（采样间隔 30 拍；密度门槛 {dth:g}）')
    for b, xs in by.items():
        live = [x for x in xs if int(x['t']) >= 600 and x['state'] == '0']
        box = [x for x in live if x['enemyNb'] == '' and x['aiNb'] in ('', '0:0') and x['huskNb'] == '' and int(x['neutralC'] or 0) == 0]
        wet = [x for x in box if int(x['waterC'] or 0) > 0]
        hi = [x for x in box if float(x['dens']) >= dth]
        hiw = [x for x in hi if int(x['waterC'] or 0) > 0]
        mx = max((int(x['waterC'] or 0) for x in live), default=0)
        tot[0] += len(box); tot[1] += len(wet); tot[2] += len(hi); tot[3] += len(hiw)
        first = min((int(x['t']) for x in box), default=None)
        print(f"   {b:8s} 围死采样点 {len(box):3d}（最早 t={first}）其中有水边 {len(wet):3d} | 全程 waterC 最大 {mx:3d} | 围死且密度>={dth:g} 的 {len(hi):3d}，其中有水边 {len(hiw)}")
    print(f"   合计：围死采样点 {tot[0]}，有水边 {tot[1]}；围死且高密度 {tot[2]}，有水边 {tot[3]}")


if __name__ == '__main__':
    main()
