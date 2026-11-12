#!/usr/bin/env python3
"""make_trace.py — 把 R01 自己的「影子决策 ↔ 录像落地」配对（out/<局>/shadow_match.csv）写成 C2 通道用的实录阶梯文件。

来源：scripts/shadow.mjs 的 matchReplay()——当年那版策略作影子逐拍决策，录像里我方席位每条落地的陆攻 / 捐款
      按「同席位、同种类、同比例、同目标、落地拍 ≥ 决策拍」定位到唯一的一条影子决策（uniq>0 才收）。
      这套配对与 R06 入库的 traces/<局>.json 互相独立（另一份影子、另一套配对规则），两者重合的三局里 95% 的条目决策拍相同
      （xcheck_trace.py）。
格式与 R06 的 traces/<局>.json 相同，teamgate 的通道库（lib/channel.mjs 的 buildC2）可以直接读：
    seats[席位] = [[决策拍 τ, 落地拍 E, 种类(0 陆攻 / 2 捐款), 影子决策时的目标, 是否生效, 录像里记的目标], …]
写到 reports/ckpt-data/traces/<局>.json（入库，报告里的 C2 档都从这里读）。

用法：python3 scripts/ckpt/make_trace.py [局号…]（缺省 15 局）
"""
import csv
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
R01 = os.path.dirname(os.path.dirname(HERE))
OUT = os.path.join(R01, 'out')
DST = os.path.join(R01, 'reports', 'ckpt-data', 'traces')
MIDS = 'A075 A055 A023 A019 A054 A003 A031 A050 A009 A057 A059 A094 A005 B039 B043'.split()
STRAT = lambda m: 'c110' if m[0] == 'B' else ('va' if int(m[1:]) <= 17 else 'vb' if int(m[1:]) <= 95 else 'vc')


def q(a, p):
    a = sorted(a)
    return a[min(len(a) - 1, int(p * len(a)))] if a else None


def main():
    mids = sys.argv[1:] or MIDS
    os.makedirs(DST, exist_ok=True)
    summ = []
    for mid in mids:
        f = os.path.join(OUT, mid, 'shadow_match.csv')
        if not os.path.exists(f):
            print(f'{mid}: 没有 shadow_match.csv，跳过')
            continue
        rows = list(csv.DictReader(open(f)))
        seats = {}
        n = 0
        for r in rows:
            if int(r['uniq']) <= 0 or r['tDecide'] == '':
                continue
            kind = 0 if r['kind'] == 'attack' else 2
            ok = 1 if str(r['applied']) in ('1', 'true', 'True') else 0
            seats.setdefault(r['p'], []).append([int(r['tDecide']), int(r['tick']), kind, int(r['shTarget']) if r['shTarget'] != '' else int(r['target']), ok, int(r['target'])])
            n += 1
        for v in seats.values():
            v.sort()
        lag = [r[1] - r[0] for v in seats.values() for r in v]
        last = max((r[1] for v in seats.values() for r in v), default=-1)
        out = dict(matchId=mid, strategy=STRAT(mid), source='R01 scripts/shadow.mjs matchReplay (shadow_match.csv, uniq>0)', rows=n,
                   unmatched=sum(1 for r in rows if int(r['uniq']) <= 0), lost=None, last=last, seats=seats)
        json.dump(out, open(os.path.join(DST, mid + '.json'), 'w'), separators=(',', ':'))
        summ.append((mid, len(seats), n, out['unmatched'], q(lag, .1), q(lag, .25), q(lag, .5), q(lag, .75), q(lag, .9), max(lag) if lag else None))
        print(f'{mid}: {len(seats)} 个席位，配上 {n} 条（进录像但没唯一定位 {out["unmatched"]}），落地拍 − 决策拍 P10/P25/中位/P75/P90/最大 = '
              f'{q(lag, .1)}/{q(lag, .25)}/{q(lag, .5)}/{q(lag, .75)}/{q(lag, .9)}/{max(lag) if lag else None}')
    with open(os.path.join(R01, 'reports', 'ckpt-data', 'trace_summary.csv'), 'w') as fo:
        fo.write('mid,seats,pairs,unlocated,lagP10,lagP25,lagP50,lagP75,lagP90,lagMax\n')
        for s in summ:
            fo.write(','.join(str(x) for x in s) + '\n')


if __name__ == '__main__':
    main()
