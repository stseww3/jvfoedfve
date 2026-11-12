#!/usr/bin/env python3
"""capchk.py — 指令通道的三个硬事实（录像真值，只读解码后的录像，不重放）

  1. 结算拍：对局阶段的指令执行拍是不是都落在 7 的倍数上。
  2. 单拍上限：同一个玩家同一拍最多执行几条（有没有 >9 的）。
  3. 顶到 9 条以后：同一个玩家在下一个结算拍（+7）、再下一个（+14）还有没有指令 —— 用来判断超出上限的部分是「顺延到下一拍」还是「没了」。
     只是旁证：下一拍有指令也可能是新发的；下一拍没有，说明至少这一次没有顺延出来的尾巴。

用法：python3 scripts/capchk.py            产物：out/_cross/capchk.txt
"""
import os
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import simdigest as SD  # noqa: E402
import team_assign as TA  # noqa: E402
from r06lib import OUT, PEER_REPLAY  # noqa: E402

IDS = ['B010', 'B017', 'B021', 'B022', 'B023', 'B025', 'B038', 'B039', 'B041']


def main():
    out = []
    out.append('| 局 | 对局阶段指令 | 执行拍是 7 的倍数 | 我方号：同拍批的大小分布（条数：批数） | 我方号单拍最多 | 外人真人单拍最多 | 我方号 9 条批：批数 / 涉及的号 | 9 条批之后 +7 拍还有指令的批（条数） | +14 拍还有的批 |')
    out.append('|---|---|---|---|---|---|---|---|---|')
    tot_sizes = Counter()
    tot9 = tot9n7 = tot9n14 = 0
    tail_sizes = Counter()
    allmod = Counter()
    mx_foe_all = 0
    kinds9 = Counter()
    for mid in IDS:
        X = SD.Sim(mid)
        squad = set(X.squad)
        dec = TA.load_decoded(PEER_REPLAY.get(mid, mid))
        per = defaultdict(list)
        n = 0
        mod = Counter()
        for c in dec['cmds']:
            if c.get('phase') != 'game':
                continue
            p = c['player']
            if p >= X.H:
                continue
            n += 1
            mod[c['t'] % 7] += 1
            per[(p, c['t'])].append(c)
        allmod.update(mod)
        sizes = Counter()
        mx_s = mx_f = 0
        nine = []
        for (p, t), cs in per.items():
            k = len(cs)
            if p in squad:
                if k >= 2:
                    sizes[k] += 1
                mx_s = max(mx_s, k)
                if k >= 9:
                    nine.append((p, t, cs))
            else:
                mx_f = max(mx_f, k)
        mx_foe_all = max(mx_foe_all, mx_f)
        tot_sizes.update(sizes)
        n7 = n14 = 0
        tails = []
        for p, t, cs in nine:
            a = len(per.get((p, t + 7), []))
            b = len(per.get((p, t + 14), []))
            if a:
                n7 += 1
                tails.append(a)
                tail_sizes[a] += 1
            if b:
                n14 += 1
            for c in cs:
                kinds9[{1: '陆攻', 2: '捐款', 3: '发船'}.get(c['id'], f"其它{c['id']}")] += 1
        tot9 += len(nine)
        tot9n7 += n7
        tot9n14 += n14
        out.append(f"| {mid} | {n:,} | {mod[0]:,}（{100 * mod[0] / max(1, n):.1f}%） | " + '、'.join(f"{k}：{v}" for k, v in sorted(sizes.items())) +
                   f" | {mx_s} | {mx_f} | {len(nine)} / {len(set(p for p, _, _ in nine))} | {n7}（{'、'.join(map(str, tails)) if tails else '—'}） | {n14} |")
    out.append('')
    N = sum(allmod.values())
    out.append(f"9 局合计：对局阶段指令 {N:,} 条，执行拍是 7 的倍数的 {allmod[0]:,} 条（{100 * allmod[0] / max(1, N):.2f}%）；余数分布 " + '、'.join(f"{k}:{v}" for k, v in sorted(allmod.items())))
    out.append('我方号同拍批（>=2 条）的大小分布：' + '、'.join(f"{k} 条 {v} 批" for k, v in sorted(tot_sizes.items())) + f"；超过 9 条的批 {sum(v for k, v in tot_sizes.items() if k > 9)} 个；外人真人单拍最多 {mx_foe_all} 条")
    out.append(f"我方号的 9 条批 {tot9} 个（指令种类：" + '、'.join(f"{k} {v}" for k, v in kinds9.most_common()) + f"）；其中下一个结算拍（+7）同一个号还有指令的 {tot9n7} 个（条数分布 " +
               ('、'.join(f"{k} 条 {v} 批" for k, v in sorted(tail_sizes.items())) or '—') + f"），+14 拍还有的 {tot9n14} 个")
    txt = '\n'.join(out) + '\n'
    os.makedirs(os.path.join(OUT, '_cross'), exist_ok=True)
    open(os.path.join(OUT, '_cross', 'capchk.txt'), 'w').write(txt)
    print(txt)


if __name__ == '__main__':
    main()
