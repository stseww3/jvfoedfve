#!/usr/bin/env python3
# R06 · 决策耗时账（跨局）
# HL-TICK 快照里的 avgMs / maxMs / skip（页面自己记的每次决策耗时、跳过的决策拍数），按局、按本机拍分段汇总，
# 并排列出同一局同一段的指令延迟 P50（crossmatch.json 的 delay 段），看「页面落后」和「策略算得慢」是不是一回事。
# 用法：python3 scripts/tickcost.py            （15 局；只读日志，不跑 node）
# 产物：out/_cross/tickcost.txt
import json
import os
import statistics as st
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from r06lib import OUT, load_match  # noqa: E402

IDS = ['B001', 'B002', 'B003', 'B010', 'B014', 'B017', 'B018', 'B021', 'B022', 'B023', 'B025', 'B038', 'B039', 'B041', 'B045']
BANDS = [(0, 600, '<600'), (600, 1500, '600~1500'), (1500, 3000, '1500~3000'), (3000, 10 ** 9, '>=3000')]


def q(v, p):
    if not v:
        return None
    v = sorted(v)
    return v[min(len(v) - 1, int(p * len(v)))]


def fmt(x, nd=1):
    return '—' if x is None else f"{x:.{nd}f}"


def main():
    delay = {}
    cj = os.path.join(OUT, '_cross', 'crossmatch.json')
    if os.path.exists(cj):
        try:
            d = json.load(open(cj))
            for r in d.get('delay', []):
                if isinstance(r, dict) and r.get('id'):
                    delay[r['id']] = r
        except Exception:
            pass
    lines = []
    lines.append('**决策耗时（HL-TICK 快照的 avgMs / maxMs / skip）按局、按本机拍分段**')
    lines.append('avgMs / maxMs = 页面自己记的每次决策耗时（毫秒）的滑动平均 / 最大；skip = 快照里的累计跳过数。每格 = 该段全部快照的中位 / P90 / 最大。')
    lines.append('')
    lines.append('| 局 | 段 | 快照 | avgMs 中位 / P90 / 最大 | maxMs 中位 / P90 / 最大 | maxMs>=100 的快照 | maxMs>=392（一个服务器回合）的快照 | skip 最大 | 同段指令延迟 P50 |')
    lines.append('|---|---|---|---|---|---|---|---|---|')
    tot = {b[2]: dict(avg=[], mx=[], n=0, ge100=0, ge392=0) for b in BANDS}
    per_match = []
    for mid in IDS:
        try:
            M = load_match(mid, with_replay=False)
        except Exception as e:  # noqa: BLE001
            lines.append(f"| {mid} | 读不了：{e} |")
            continue
        for lo, hi, name in BANDS:
            avg, mx, sk = [], [], []
            for b in M.bots.values():
                for s in b.traj:
                    if lo <= s['t'] < hi and (s.get('avgMs') or s.get('maxMs')):
                        avg.append(s['avgMs'])
                        mx.append(s['maxMs'])
                        sk.append(s['skip'])
            if not avg:
                continue
            ge100 = sum(1 for x in mx if x >= 100)
            ge392 = sum(1 for x in mx if x >= 392)
            T = tot[name]
            T['avg'] += avg
            T['mx'] += mx
            T['n'] += len(avg)
            T['ge100'] += ge100
            T['ge392'] += ge392
            dl = '—'
            r = delay.get(mid)
            if r:
                v = (r.get('bands') or {}).get({'<600': '0~600', '>=3000': '3000+'}.get(name, name))
                if v:
                    dl = f"{v['p50']}（P90 {v['p90']}）"
            per_match.append((mid, name, st.median(avg), st.median(mx)))
            lines.append(f"| {mid} | {name} | {len(avg):,} | {fmt(st.median(avg))} / {fmt(q(avg, 0.9))} / {fmt(max(avg))} | {fmt(st.median(mx))} / {fmt(q(mx, 0.9))} / {fmt(max(mx))} | "
                         f"{ge100}（{100 * ge100 / len(mx):.1f}%） | {ge392}（{100 * ge392 / len(mx):.1f}%） | {max(sk):.0f} | {dl} |")
    lines.append('')
    lines.append('**15 局合计**')
    lines.append('')
    lines.append('| 段 | 快照 | avgMs 中位 / P90 / 最大 | maxMs 中位 / P90 / 最大 | maxMs>=100 | maxMs>=392 |')
    lines.append('|---|---|---|---|---|---|')
    for lo, hi, name in BANDS:
        T = tot[name]
        if not T['n']:
            continue
        lines.append(f"| {name} | {T['n']:,} | {fmt(st.median(T['avg']))} / {fmt(q(T['avg'], 0.9))} / {fmt(max(T['avg']))} | {fmt(st.median(T['mx']))} / {fmt(q(T['mx'], 0.9))} / {fmt(max(T['mx']))} | "
                     f"{T['ge100']}（{100 * T['ge100'] / T['n']:.1f}%） | {T['ge392']}（{100 * T['ge392'] / T['n']:.1f}%） |")
    out = '\n'.join(lines) + '\n'
    os.makedirs(os.path.join(OUT, '_cross'), exist_ok=True)
    open(os.path.join(OUT, '_cross', 'tickcost.txt'), 'w').write(out)
    print(out)


if __name__ == '__main__':
    main()
