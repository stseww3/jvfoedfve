#!/usr/bin/env python3
"""make_steps_extra.py — 断面归因的附加批次（敏感度与历史版本互换），输出步骤文件。

  r06trace   C2 档的实录阶梯换成 R06 入库的那一份（另一套影子、另一套配对）：A023 / A057 / B039，断面 630 与 1500
  fill       C2 档已知点之间的补法换成 nearest / linear：A031 / A009 / A059 / B043，断面 630
  swap       同一个断面上把我方换成**另外两个历史版本**（只在 c116 家族内：Va / Vb / Vc 互换），C1 与 C2 各 3 个种子，
             断面 0 / 630 / 1500。用来量「历史版本之间既有规则的差」在同一局面、同一通道下值多少，和通道那几段并排比。
             不涉及任何新策略。

  g0         从开局一口气放开跑到 t=1500（14 局；C0 / C1×3 / C2×3，1500 拍前有页面停摆的再加 C2w×3）

用法：python3 scripts/ckpt/make_steps_extra.py [r06trace] [fill] [g0] [swap] > scripts/steps/ckpt-extra.txt
实际跑的步骤文件 scripts/steps/ckpt-all2.txt = make_steps.py 的输出 + 本脚本 r06trace fill + g0 + swap 的输出，
每行末尾补了 --budget-ms 480000（机器忙的时候一条要跑几分钟墙钟）。
"""
import csv
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
R01 = os.path.dirname(os.path.dirname(HERE))
OUT = os.path.join(R01, 'out')
A_MIDS = 'A075 A055 A023 A019 A054 A003 A031 A050 A009 A057 A059 A094'.split()
WIN = {0: 630, 630: 870, 1500: 1713, 3213: 1071, 4284: 900}
CPU_BUDGET_MS = 26000


def hist_ver(mid):
    n = int(mid[1:])
    return 'va' if n <= 17 else 'vb' if n <= 95 else 'vc'


def live_seats(mid, t0):
    b = json.load(open(os.path.join(OUT, mid, 'ckpt_base.json')))
    death = {int(k): v for k, v in b['deathT'].items()}
    sq = set(b['squad'])
    left = {}
    for r in csv.DictReader(open(os.path.join(OUT, mid, 'resim_events.csv'))):
        if r['ev'] == 'left' and int(r['p']) in sq:
            left.setdefault(int(r['p']), int(r['t']))
    return [p for p in b['squad'] if (death[p] < 0 or death[p] > t0) and left.get(p, 10 ** 9) > t0], b['endT']


def chunks(arms, n_live, t0, ln):
    per_arm = n_live * (0.13 * t0 + 0.11 * ln) + 300
    n = max(1, int(CPU_BUDGET_MS // per_arm))
    return [arms[i:i + n] for i in range(0, len(arms), n)]


def main():
    what = set(sys.argv[1:]) or {'r06trace', 'fill', 'g0', 'swap'}
    if 'g0' in what:
        # 从开局一口气放开跑到 1500（不在 630 重新对齐到历史局面）：比分窗口更严的保真度检验
        for mid in A_MIDS + ['B039', 'B043']:
            b = json.load(open(os.path.join(OUT, mid, 'ckpt_base.json')))
            arms = ['C0', 'C1', 'C2', 'C1@2', 'C2@2', 'C1@3', 'C2@3']
            if any(v < 1500 for k, v in b['pageEnd'].items() if int(k) in b['doomed']):
                arms += ['C2w', 'C2w@2', 'C2w@3']
            n = max(1, int(CPU_BUDGET_MS // (len(b['squad']) * 0.11 * 1500 + 300)))
            for i in range(0, len(arms), n):
                tag = 'g0' + chr(97 + i // n)
                print(f"out/_ckpt/logs/{mid}-0-{tag}.txt node scripts/ckpt/ckpt_run.mjs --match {mid} --t0 0 --len 1500 --arms {','.join(arms[i:i + n])} --tag {tag}")
    if 'r06trace' in what:
        for mid in ('A023', 'A057', 'B039'):
            for t0 in (630, 1500):
                live, end = live_seats(mid, t0)
                for k, ch in enumerate(chunks(['C2', 'C2@2', 'C2@3'], len(live), t0, WIN[t0])):
                    tag = f'r06trace{chr(97 + k)}'
                    print(f"out/_ckpt/logs/{mid}-{t0}-{tag}.txt node scripts/ckpt/ckpt_run.mjs --match {mid} --t0 {t0} --len {WIN[t0]} --arms {','.join(ch)} --trace ../../archive/agents/R06/sim-v2/traces/{mid}.json --tag {tag}")
    if 'fill' in what:
        for mid in ('A031', 'A009', 'A059', 'B043'):
            for fill in ('nearest', 'linear'):
                t0 = 630
                live, end = live_seats(mid, t0)
                for k, ch in enumerate(chunks(['C2', 'C2@2', 'C2@3'], len(live), t0, WIN[t0])):
                    tag = f'fill{fill}{chr(97 + k)}'
                    print(f"out/_ckpt/logs/{mid}-{t0}-{tag}.txt node scripts/ckpt/ckpt_run.mjs --match {mid} --t0 {t0} --len {WIN[t0]} --arms {','.join(ch)} --fill {fill} --tag {tag}")
    if 'swap' in what:
        for mid in A_MIDS:
            for ver in ('va', 'vb', 'vc'):
                if ver == hist_ver(mid):
                    continue
                for t0 in (0, 630, 1500):
                    live, end = live_seats(mid, t0)
                    if t0 >= end - 100 or not live:
                        continue
                    for k, ch in enumerate(chunks(['C1', 'C2', 'C1@2', 'C2@2', 'C1@3', 'C2@3'], len(live), t0, WIN[t0])):
                        tag = f'{ver}{chr(97 + k)}'
                        print(f"out/_ckpt/logs/{mid}-{t0}-{tag}.txt node scripts/ckpt/ckpt_run.mjs --match {mid} --t0 {t0} --len {WIN[t0]} --strat {ver} --arms {','.join(ch)} --tag {tag}")


if __name__ == '__main__':
    main()
