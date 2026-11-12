#!/usr/bin/env python3
"""logorder_floor.py — 从局内日志的收集顺序给每个页面的「本机拍 → 服务器拍」定一个下界（地板），并拿唯一定位的指令配对来核它。

依据：/agent/repos/c136-data/bundles/<局>/in_game.log 每行开头是收集器给的全局流水号（按收到的先后）。
页面 p 记下本机拍 t 的那一刻，凡是流水号更小的行里出现过的本机拍（任何一个我方页面的）都已经算过了，
而本机拍不可能超过服务器拍，所以这一刻的服务器拍 ≥ Tmax = 流水号更小的行里最大的本机拍：
    S_p(t) ≥ Tmax，也就是 p 在本机拍 t 至少落后 Tmax − t 拍。
S_p 对 t 不降，所以这个下界对 t 之后的本机拍同样成立。

只用 HL-TICK 行（每个页面每 90 个本机拍一行），所以下界的粒度是 90 拍。
这个下界成立的前提是日志行送到收集器的耽搁可以忽略（否则谁的日志送得慢，谁就显得落后）。
核对办法：唯一定位的配对 (下令拍 τ, 落地拍 E) 给出 S_p(τ) ≤ E − 最小在途拍数；
取 τ 之前最近的一个日志点 t ≤ τ，就该有 Tmax(t) ≤ S_p(t) ≤ S_p(τ) ≤ E − MIN_TRANSIT。数一数违反的有多少。

用法：python3 scripts/ckpt/logorder_floor.py [局号…]
输出：reports/ckpt-data/floor/<局>.json   {seats: {席位: [[本机拍, 服务器拍下界], …]}}（只留下界 − 本机拍 ≥ MIN_FLOOR 的点）
      reports/ckpt-data/floor_check.csv    每局：日志点数、有落后下界的点数、拿配对核对的条数与违反的条数
"""
import bisect
import csv
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
R01 = os.path.dirname(os.path.dirname(HERE))
DATA = os.path.join(R01, 'reports', 'ckpt-data')
BUNDLES = '/agent/repos/c136-data/bundles'
MIDS = ['A075', 'A055', 'A023', 'A019', 'A054', 'A003', 'A005', 'A031', 'A050', 'A009', 'A057', 'A059', 'A094', 'B039', 'B043']
MIN_FLOOR = 45      # 下界 − 本机拍 不到这么多的点不当作地板（粒度 90 拍，小于半格的没有信息量）
MIN_TRANSIT = 5     # 不落后时下令到落地最少也要这么多拍（实测 P10 ≈ 7）
LINE = re.compile(r'^(\d+)\t\[(.+?)\] \[HL-TICK\] t=(\d+) ')


def seat_map(mid):
    """日志里的名字 → 席位号。"""
    m = {}
    with open(os.path.join(R01, 'out', mid, 'resim_check.csv')) as f:
        for r in csv.DictReader(f):
            m[r['bot']] = r['p']
    return m


def log_points(mid):
    """→ {席位: [(本机拍, Tmax), …]}（按日志出现的先后）。"""
    names = seat_map(mid)
    rows = []
    with open(os.path.join(BUNDLES, mid, 'in_game.log'), errors='replace') as f:
        for line in f:
            m = LINE.match(line)
            if m and m.group(2) in names:
                rows.append((int(m.group(1)), names[m.group(2)], int(m.group(3))))
    rows.sort()
    out = {}
    tmax = 0
    for seq, p, t in rows:
        out.setdefault(p, []).append((t, max(tmax, t)))
        if t > tmax:
            tmax = t
    return out


def main():
    mids = sys.argv[1:] or MIDS
    os.makedirs(os.path.join(DATA, 'floor'), exist_ok=True)
    summary = []
    for mid in mids:
        if not os.path.exists(os.path.join(BUNDLES, mid, 'in_game.log')):
            print(f'{mid}: 没有 in_game.log')
            continue
        pts = log_points(mid)
        located = json.load(open(os.path.join(DATA, 'traces', mid + '.json')))['seats']
        n_pts = n_floor = 0
        checked = viol = viol_big = 0
        worst = 0
        floor = {}
        lags = []
        for p, v in pts.items():
            v.sort()
            # 同一个本机拍多行时取最小的下界；再做成对 t 不降（S 不降，所以较早的点的下界不能高过较晚的点——高了说明那一行的次序不可靠，削平）
            ts, lb = [], []
            for t, s in v:
                if ts and ts[-1] == t:
                    lb[-1] = min(lb[-1], s)
                else:
                    ts.append(t); lb.append(s)
            for i in range(len(lb) - 2, -1, -1):
                if lb[i] > lb[i + 1]:
                    lb[i] = lb[i + 1]
            n_pts += len(ts)
            keep = [[t, s] for t, s in zip(ts, lb) if s - t >= MIN_FLOOR]
            n_floor += len(keep)
            lags += [s - t for t, s in keep]
            if keep:
                floor[p] = keep
            # 拿唯一定位的配对核对
            for row in located.get(p, []):
                tau, E = row[0], row[1]
                i = bisect.bisect_right(ts, tau) - 1
                if i < 0:
                    continue
                checked += 1
                over = lb[i] - (E - MIN_TRANSIT)
                if over > 0:
                    viol += 1
                    worst = max(worst, over)
                    if over > 20:
                        viol_big += 1
        json.dump({'matchId': mid, 'source': 'in_game.log 的收集顺序（HL-TICK 行）', 'minFloor': MIN_FLOOR, 'seats': floor},
                  open(os.path.join(DATA, 'floor', mid + '.json'), 'w'), separators=(',', ':'))
        lags.sort()
        q = lambda f: lags[min(len(lags) - 1, int(f * len(lags)))] if lags else ''
        summary.append(dict(mid=mid, logPoints=n_pts, floorPoints=n_floor, floorSeats=len(floor), floorLagP50=q(.5), floorLagP90=q(.9), floorLagMax=lags[-1] if lags else '',
                            pairsChecked=checked, violations=viol, violationsOver20=viol_big, worstOver=worst))
        print(f"{mid}: 日志点 {n_pts}，其中有落后下界（≥{MIN_FLOOR} 拍）的 {n_floor} 个、涉及 {len(floor)} 个席位，下界 P50/P90/最大 = {q(.5)}/{q(.9)}/{lags[-1] if lags else ''}；"
              f"拿 {checked} 条唯一定位的配对核对：违反 {viol} 条（超出 20 拍以上的 {viol_big} 条，最多超 {worst} 拍）")
    with open(os.path.join(DATA, 'floor_check.csv'), 'w', newline='') as fo:
        w = csv.DictWriter(fo, fieldnames=list(summary[0].keys()))
        w.writeheader()
        w.writerows(summary)


if __name__ == '__main__':
    main()
