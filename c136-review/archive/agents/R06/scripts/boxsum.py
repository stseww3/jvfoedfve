#!/usr/bin/env python3
"""R06 被围账（录像真值）：我方在场号「策略眼里没有可打的邻居、也没有无主邻格」的时段，围住它的是谁。

用法：python3 boxsum.py <matchId> [<matchId> ...]
  不带局号 = 录像过了 t=1500 的 7 局（B010 B017 B021 B022 B023 B038 B039）。

口径（simdigest.protbox_rows；t>=600，段长 >=180 拍，快照间隔 90 拍）
  被围 = 邻居表里没有可打的对象（敌方真人 / 普通内置 AI）且没有无主邻格。
  围住它的三类地：同队的地（引擎规则，本来就不能打）；异队但名字在池里的号（含我方在场号、我方空壳、撞名的外人）；名字在池里的内置 AI。
  后两类只在「场上还有野生外人」时被挡（isProtectedSquadMate L3993-3996）。
  「只挨着同队」= 这一段从头到尾没有挨着后两类。
  顶格少拿 = 这一段里因为兵超过软上限少拿的利息（引擎账）。
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import simdigest as SD  # noqa: E402

DEFAULT = ['B010', 'B017', 'B021', 'B022', 'B023', 'B038', 'B039']


def wan(n):
    n = float(n)
    if abs(n) >= 1e8:
        return f'{n / 1e8:.2f} 亿'
    if abs(n) >= 1e6:
        return f'{n / 1e4:,.0f} 万'
    if abs(n) >= 1e4:
        return f'{n / 1e4:.1f} 万'
    return f'{n:,.0f}'


def one(mid):
    X = SD.Sim(mid)
    rows = SD.protbox_rows(X)
    ln = lambda r: r['t1'] - r['t0'] + 90
    prot = [r for r in rows if r['xsquad'] or r['poolai']]
    mate = [r for r in rows if not (r['xsquad'] or r['poolai'])]
    hi = [r for r in rows if max(r['dens']) >= 140]
    return dict(id=mid, seg=len(rows), bots=len({r['p'] for r in rows}), ticks=sum(ln(r) for r in rows),
                protSeg=len(prot), protTicks=sum(ln(r) for r in prot), protCap=sum(r['capLoss'] for r in prot), protInc=sum(r['inc'] for r in prot),
                poolaiSeg=sum(1 for r in rows if r['poolai']), mateSeg=len(mate), mateTicks=sum(ln(r) for r in mate), mateCap=sum(r['capLoss'] for r in mate),
                hiSeg=len(hi), hiTicks=sum(ln(r) for r in hi), cap=sum(r['capLoss'] for r in rows), inc=sum(r['inc'] for r in rows),
                longest=max(((ln(r), X.name(r['p']), r['t0'], r['t1']) for r in rows), default=None))


def main():
    ids = [a for a in sys.argv[1:] if not a.startswith('-')] or DEFAULT
    out = [one(m) for m in ids]
    print('| 局 | 被围：段 / 号 / 号·拍 | 其中挨着被保护名单挡住的地：段 / 号·拍 | 其中挨着撞名内置 AI 的段 | 只挨着同队：段 / 号·拍 | 密度到过 >=140 的段 / 号·拍 | 被围时段的顶格少拿（÷ 这些时段的实得利息） | 其中挨着保护名单的那些段 | 最长的一段 |')
    print('|---|---|---|---|---|---|---|---|---|')
    for o in out:
        lg = o['longest']
        print(f"| {o['id']} | {o['seg']} / {o['bots']} / {o['ticks']:,} | {o['protSeg']} / {o['protTicks']:,} | {o['poolaiSeg']} | {o['mateSeg']} / {o['mateTicks']:,} | {o['hiSeg']} / {o['hiTicks']:,} | "
              f"{wan(o['cap'])}（{100 * o['cap'] / max(1, o['inc']):.0f}%） | {wan(o['protCap'])} | " + (f"{lg[1]} t={lg[2]}~{lg[3]}（{lg[0]:,} 拍）" if lg else '—') + ' |')
    s = lambda k: sum(o[k] for o in out)
    print(f"| 合计 | {s('seg')} / {s('bots')} / {s('ticks'):,} | {s('protSeg')} / {s('protTicks'):,}（{100 * s('protTicks') / max(1, s('ticks')):.0f}% 的号·拍） | {s('poolaiSeg')} | {s('mateSeg')} / {s('mateTicks'):,} | "
          f"{s('hiSeg')} / {s('hiTicks'):,} | {wan(s('cap'))}（{100 * s('cap') / max(1, s('inc')):.0f}%） | {wan(s('protCap'))} | — |")


if __name__ == '__main__':
    main()
