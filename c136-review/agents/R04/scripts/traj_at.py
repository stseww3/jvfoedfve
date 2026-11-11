#!/usr/bin/env python3
# traj_at.py — 从对局包的 traj.csv（各号自己日志里的快照）取某几个号在某几拍的一行，
# 供没有录像的房间 / 号核对「领土、余额、密度、累计指令数、累计发船数」。
#
# 用法：
#   python3 scripts/traj_at.py <局号> <号名,号名,…|all> <拍,拍,…>      取离每个拍最近的一行
#   python3 scripts/traj_at.py <局号> <号名,…|all> <t0>-<t1> [步长]     取 [t0,t1] 内的行（默认每行都出）
# 口径：traj.csv 的 t 是日志拍；密度 = bal / terr；cmds、boats 是累计值。
import sys, os, csv, collections

DATA = '/agent/repos/c136-data/bundles'


def main():
    a = sys.argv[1:]
    if len(a) < 3:
        raise SystemExit(__doc__ or '用法见文件头')
    mid, bots, spec = a[0], a[1], a[2]
    step = int(a[3]) if len(a) > 3 else 0
    rows = collections.defaultdict(list)
    with open(os.path.join(DATA, mid, 'traj.csv'), encoding='utf8') as f:
        for r in csv.DictReader(f):
            try:
                rows[r['bot']].append((int(float(r['t'])), int(float(r['terr'])), float(r['bal']), int(float(r['cmds'] or 0)), int(float(r['boats'] or 0))))
            except ValueError:
                continue
    names = sorted(rows) if bots == 'all' else bots.split(',')
    for n in names:
        lst = sorted(rows.get(n, []))
        if not lst:
            print(f'{n}：traj.csv 里没有这个号')
            continue
        if '-' in spec:
            t0, t1 = (int(x) for x in spec.split('-'))
            pick = [r for r in lst if t0 <= r[0] <= t1 and (not step or r[0] % step == 0)]
        else:
            pick = []
            for t in (int(x) for x in spec.split(',')):
                pick.append(min(lst, key=lambda r: abs(r[0] - t)))
        for t, terr, bal, cmds, boats in pick:
            dens = bal / terr if terr else 0
            print(f'{n:8s} 拍 {t:>5d} 领土 {terr:>7d} 余额 {int(bal):>10d} 密度 {dens:6.1f} 累计指令 {cmds:>4d} 累计发船 {boats:>3d}')
        print(f'{n:8s} 最后一行：拍 {lst[-1][0]} 领土 {lst[-1][1]} 余额 {int(lst[-1][2])}')


if __name__ == '__main__':
    main()
