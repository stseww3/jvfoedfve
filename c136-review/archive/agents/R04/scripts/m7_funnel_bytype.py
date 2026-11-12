#!/usr/bin/env python3
# m7_funnel_bytype.py — 把 13 局延迟账第 2 节的「想发 → 落地」按指令种类（陆攻 / 捐款 / 船）拆开，排成跨局表。
#
# 用法：python3 scripts/m7_funnel_bytype.py > out/m7/FUNNEL-BYTYPE.md
# 数据：out/<局>/latency_ledger.txt（scripts/latency_ledger.py 的输出）第 2 节的四行：
#         时段  想发（陆攻/捐款/船）  落地（陆攻/捐款/船）  落地率 …
#       想发 = 影子策略过闸的意图，按决策拍分段；落地 = 这些意图里在录像中配上了一条同号、同种类、同比例指令的条数（宽配对）。
# 为什么要拆：表 14 / 20 的漏斗（想发 → 受理 → 落地）把三种指令算在一起；被反喂养配额拒掉的捐款也是「受理了没落地」，
#       不拆开就分不清「陆攻没落地」和「捐款被拒」。
# 这里只做逐局相加，不做别的推算；比例由脚本用整数算出。
import os, re, sys
sys.dont_write_bytecode = True
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MATCHES = ['A013', 'A015', 'A022', 'A029', 'A038', 'A047', 'A073', 'A078', 'A081', 'A083', 'A086', 'A099', 'B034']
BANDS = ['0~599', '600~1499', '1500~2999', '3000+']
LINE = re.compile(r'^\s+(0~599|600~1499|1500~2999|3000\+)\s+(\d+)（(\d+)/(\d+)/(\d+)）\s+(\d+)（(\d+)/(\d+)/(\d+)）\s+(\d+)%')


def load(mid):
    fp = os.path.join(ROOT, 'out', mid, 'latency_ledger.txt')
    rows = {}
    with open(fp, encoding='utf8') as f:
        for ln in f:
            m = LINE.match(ln)
            if m and m.group(1) not in rows:
                v = [int(x) for x in m.groups()[1:]]
                rows[m.group(1)] = dict(want=v[0], wa=v[1], wd=v[2], wb=v[3], land=v[4], la=v[5], ld=v[6], lb=v[7])
    return rows


def pct(a, b):
    return '%d%%' % round(100.0 * a / b) if b else '—'


def cell(a, b):
    return '%d → %d（%s）' % (a, b, pct(b, a)) if a else '0'


def main():
    data = {mid: load(mid) for mid in MATCHES}
    miss = [mid for mid in MATCHES if len(data[mid]) != 4]
    if miss:
        raise SystemExit('缺行：%s' % miss)
    print('### F1 影子想发的意图里配上了落地指令的条数，按指令种类拆开（m7_funnel_bytype.py；每格 想发 → 落地（落地率））')
    print()
    for kind, kw, kl in (('陆攻', 'wa', 'la'), ('捐款（调度）', 'wd', 'ld'), ('船', 'wb', 'lb')):
        print('**%s**' % kind)
        print()
        print('| 局 | ' + ' | '.join(BANDS) + ' |')
        print('| :-- | ' + ' | '.join('--:' for _ in BANDS) + ' |')
        tot = {b: [0, 0] for b in BANDS}
        tot2 = {b: [0, 0] for b in BANDS}
        for mid in MATCHES:
            cs = []
            for b in BANDS:
                r = data[mid][b]
                cs.append(cell(r[kw], r[kl]))
                tot[b][0] += r[kw]
                tot[b][1] += r[kl]
                if mid != 'A073':
                    tot2[b][0] += r[kw]
                    tot2[b][1] += r[kl]
            print('| %s | %s |' % (mid, ' | '.join(cs)))
        print('| 13 局合计 | %s |' % ' | '.join(cell(*tot[b]) for b in BANDS))
        print('| 去掉 A073 | %s |' % ' | '.join(cell(*tot2[b]) for b in BANDS))
        print()
    # 三种合在一起（和第 2 节的「落地率」同一个口径），方便和拆开的对照
    print('**三种合计（延迟账第 2 节的口径）**')
    print()
    print('| 局 | ' + ' | '.join(BANDS) + ' |')
    print('| :-- | ' + ' | '.join('--:' for _ in BANDS) + ' |')
    tot = {b: [0, 0] for b in BANDS}
    for mid in MATCHES:
        cs = []
        for b in BANDS:
            r = data[mid][b]
            cs.append(cell(r['want'], r['land']))
            tot[b][0] += r['want']
            tot[b][1] += r['land']
        print('| %s | %s |' % (mid, ' | '.join(cs)))
    print('| 13 局合计 | %s |' % ' | '.join(cell(*tot[b]) for b in BANDS))
    print()
    print('口径：想发按影子策略的决策拍分段；落地 = 这条意图在录像里配上了一条同号、同种类、同比例的指令（宽配对，不看晚了多少拍）。'
          '和表 14 / 20 的「想发 → 受理 → 落地」不是同一个分段（那里按 630 / 1530 / 3060 的快照对齐，落地按服务器拍数），两处的数不能直接相减。')


if __name__ == '__main__':
    main()
