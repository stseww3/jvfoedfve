#!/usr/bin/env python3
# flat_windows.py — 只用对局包的 traj.csv（每 90 拍一行的日志快照）找每个号「地不动、指令也几乎不发、余额却在涨」的最长一段。
#
# 用法：python3 scripts/flat_windows.py <局号> [--from 1500] [--tol 0.04] [--cmds 12] [--min 360] [--all]
#   --all   另外列出每个号全部的平台段（从左到右、互不重叠）
#   --from  只看这一拍之后的快照（默认 1500，避开开局）
#   --tol   段内领土相对段首的变化幅度上限（默认 4%）
#   --cmds  段内指令计数（cmds 列）最多增加多少（默认 12）
#   --min   至少持续多少拍才列出（默认 360）
# 输出：每个号最长的一段：起止拍、领土、指令数增量、发船数增量、余额与密度的起止值、段末余额是不是超过 100×领土。
# 读法：这是日志口径（没有录像的房间也能用）。一段里密度从个位数涨到几十上百而领土不动，就是「有兵不用」。
import sys, os, csv

DATA = '/agent/repos/c136-data/bundles'


def opt(k, d):
    return type(d)(sys.argv[sys.argv.index(k) + 1]) if k in sys.argv else d


def main():
    mid = sys.argv[1]
    t_from, tol, max_cmds, min_len = opt('--from', 1500), opt('--tol', 0.04), opt('--cmds', 12), opt('--min', 360)
    rows = {}
    # B 组的号中途会换号名：后来的名字并回录像里的名字（log_alias.py），不然一段平台会被拆成几段
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import log_alias
    ren = log_alias.first_names(mid)
    with open(os.path.join(DATA, mid, 'traj.csv'), encoding='utf8') as f:
        for r in csv.DictReader(f):
            rows.setdefault(ren.get(r['bot'], r['bot']), []).append((int(r['t']), int(r['terr']), int(float(r['bal'])), float(r['dens']), int(r['cmds']), int(r['boats']), int(r['nb']), int(r['neut'])))
    print(f'# {mid} 地不动、指令几乎不发的最长一段（日志快照；领土变化 ≤{tol:.0%}、指令增量 ≤{max_cmds}、持续 ≥{min_len} 拍、起点 ≥{t_from} 拍）')
    tot = 0
    for bot in sorted(rows):
        rows[bot].sort()
        rs = [x for x in rows[bot] if x[0] >= t_from]
        best = None
        for i in range(len(rs)):
            t0, terr0, bal0, d0, c0, b0 = rs[i][:6]
            if terr0 <= 0:
                continue
            j = i
            while j + 1 < len(rs) and abs(rs[j + 1][1] - terr0) <= tol * terr0 and rs[j + 1][4] - c0 <= max_cmds:
                j += 1
            if rs[j][0] - t0 >= min_len and (best is None or rs[j][0] - t0 > best[1][0] - best[0][0]):
                best = (rs[i], rs[j])
        if best is None:
            print(f'  {bot:8s} 没有这样的段（末行 拍 {rows[bot][-1][0]} 领土 {rows[bot][-1][1]}）')
            continue
        a, b = best
        tot += b[0] - a[0]
        over = '，段末余额已超过 100×领土' if b[2] > 100 * b[1] else ''
        print(f'  {bot:8s} 拍 {a[0]}~{b[0]}（{b[0] - a[0]} 拍）：领土 {a[1]}→{b[1]}，指令 +{b[4] - a[4]}，发船 +{b[5] - a[5]}；'
              f'余额 {a[2]}→{b[2]}（{b[2] / max(1, a[2]):.1f} 倍），密度 {a[3]}→{b[3]}；邻居数 {a[6]}→{b[6]}{over}')
    print(f'合计 {tot} 号·拍')
    if '--all' in sys.argv:
        # 每个号从左到右、互不重叠的全部平台段（上面只列最长的一段）
        print('全部平台段（从左到右、互不重叠）：')
        tot2 = 0
        for bot in sorted(rows):
            rs = [x for x in rows[bot] if x[0] >= t_from]
            i = 0
            segs = []
            while i < len(rs):
                t0, terr0, bal0, d0, c0, b0 = rs[i][:6]
                if terr0 <= 0:
                    i += 1
                    continue
                j = i
                while j + 1 < len(rs) and abs(rs[j + 1][1] - terr0) <= tol * terr0 and rs[j + 1][4] - c0 <= max_cmds:
                    j += 1
                if rs[j][0] - t0 >= min_len:
                    segs.append((rs[i], rs[j]))
                    i = j + 1
                else:
                    i += 1
            for a, b in segs:
                tot2 += b[0] - a[0]
                print(f'  {bot:8s} 拍 {a[0]}~{b[0]}（{b[0] - a[0]} 拍）：领土 {a[1]}→{b[1]}，指令 +{b[4] - a[4]}，发船 +{b[5] - a[5]}；余额 {a[2]}→{b[2]}，密度 {a[3]}→{b[3]}；邻居数 {a[6]}→{b[6]}')
        print(f'  合计 {tot2} 号·拍')


if __name__ == '__main__':
    main()
