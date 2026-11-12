#!/usr/bin/env python3
"""make_steps_extra.py — 断面归因的附加批次（敏感度与历史版本互换），输出步骤文件。

  r06trace   C2 档的实录阶梯换成 R06 入库的那一份（另一套影子、另一套配对）：A023 / A057 / B039，断面 630 与 1500
  fill       C2 档已知点之间的补法换成 nearest / linear：A031 / A009 / A059 / B043，断面 630
  swap       同一个断面上把我方换成**另外两个历史版本**（只在 c116 家族内：Va / Vb / Vc 互换），C1 与 C2 各 3 个种子，
             断面 0 / 630 / 1500。用来量「历史版本之间既有规则的差」在同一局面、同一通道下值多少，和通道那几段并排比。
             不涉及任何新策略。
  swaplate   同上，断面 3213 / 4284（捐兵配额放开以后；Vb 与 Vc 的差全在捐兵规则里）

  g0         从开局一口气放开跑到 t=1500（14 局；C0 / C1×3 / C2×3，1500 拍前有页面停摆的再加 C2w×3）
  band       C2 / C2w 换成阶梯的上界 / 下界（traces-hi / traces-lo，见 make_trace.py）并按日志次序的地板抬高（floor/，见 logorder_floor.py），
             只跑受影响的窗口（选了哪些见 reports/ckpt-data/band_select.csv）
  c1p        主批次里单独跑了 C2w 的窗口再补 C1p×3（基础延迟 + 实录页面停摆，不带落后波）：检验落后波与页面停摆两段的先后次序

用法：python3 scripts/ckpt/make_steps_extra.py [r06trace] [fill] [g0] [swap] > scripts/steps/ckpt-extra.txt
实际跑的步骤文件 scripts/steps/ckpt-all3.txt = make_steps.py 的输出（主批次，标签 a、b、c…）+ 本脚本各选项的输出，
每行末尾补了 --budget-ms 480000（机器忙的时候一条要跑几分钟墙钟）。band 与 c1p 两个选项要读这个文件里主批次的行。
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


BAND_MIN = 2.0   # 拍


def stairs(seats, floor, N, thr=28, dmid=12):
    """lib/channel.mjs buildC2（fill=auto）的照抄，再按地板抬高（ckpt_run.mjs applyFloor）。→ {席位: S[0..N)}"""
    out = {}
    for p in set(seats) | set(floor or {}):
        rows = seats.get(p) or []
        s = list(range(N))
        if rows:
            pts = sorted([r[0], max(r[0], r[1] - dmid)] for r in rows)
            for i in range(len(pts) - 2, -1, -1):
                if pts[i][1] > pts[i + 1][1]:
                    pts[i][1] = pts[i + 1][1]
            j = 0
            for W in range(N):
                while j < len(pts) and pts[j][0] < W:
                    j += 1
                if j >= len(pts):
                    v = max(W, pts[-1][1])
                elif pts[j][0] == W:
                    v = pts[j][1]
                elif j == 0:
                    v = W
                else:
                    ta, sa = pts[j - 1]
                    tb, sb = pts[j]
                    if max(sa - ta, sb - tb) <= thr:
                        v = int(sa + (sb - sa) * (W - ta) / (tb - ta) + 0.5)
                    else:
                        v = sa if W - ta <= tb - W else sb
                s[W] = max(W, v)
            for W in range(1, N):
                if s[W] < s[W - 1]:
                    s[W] = s[W - 1]
        for t, lb in (floor or {}).get(p, []):
            for W in range(t, min(lb, N)):
                if s[W] < lb:
                    s[W] = lb
        for W in range(1, N):
            if s[W] < s[W - 1]:
                s[W] = s[W - 1]
        out[p] = s
    return out


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
    if 'c1p' in what:
        # 次序敏感度：主批次里单独跑了 C2w 的窗口（窗口结束前有页面停摆 / 掉线离场），再补 C1p（基础延迟 + 实录页面）×3
        import re
        seen = set()
        for line in open(os.path.join(R01, 'scripts', 'steps', 'ckpt-all3.txt')):
            m = re.search(r'--match (\w+) --t0 (\d+) --len (\d+) --arms (\S+) --tag ([a-z]) ', line)
            if not m or 'C2w' not in m.group(4) or (m.group(1), m.group(2)) in seen:
                continue
            seen.add((m.group(1), m.group(2)))
            mid, t0, ln = m.group(1), int(m.group(2)), int(m.group(3))
            live, end = live_seats(mid, t0)
            for k, ch in enumerate(chunks(['C1p', 'C1p@2', 'C1p@3'], len(live), t0, ln)):
                tag = 'pqr'[k]
                print(f"out/_ckpt/logs/{mid}-{t0}-{tag}.txt node scripts/ckpt/ckpt_run.mjs --match {mid} --t0 {t0} --len {ln} --arms {','.join(ch)} --tag {tag}")
    if 'band' in what:
        # 阶梯的上下界：定位不唯一的落地指令取最早 / 最晚放得下的决策（traces-hi / traces-lo），再按日志次序的地板抬高（floor/）。
        # 只重跑受影响的窗口：窗口内（断面时还在的席位 × 每个本机拍）这一口径的落后与主口径平均差出 BAND_MIN 拍以上。
        # 臂与主批次的 C2 / C2w 相同。
        import re
        main_arms = {}
        for line in open(os.path.join(R01, 'scripts', 'steps', 'ckpt-all3.txt')):
            m = re.search(r'--match (\w+) --t0 (\d+) --len (\d+) --arms (\S+) --tag ([a-z]) ', line)
            if m:
                e = main_arms.setdefault((m.group(1), int(m.group(2))), {'len': int(m.group(3)), 'arms': []})
                e['arms'] += m.group(4).split(',')
        data = os.path.join(R01, 'reports', 'ckpt-data')
        sel = []
        cache = {}
        for (mid, t0), e in main_arms.items():
            t1 = t0 + e['len']
            live, end = live_seats(mid, t0)
            if not live:
                continue
            if mid not in cache:
                fl = json.load(open(os.path.join(data, 'floor', mid + '.json')))['seats']
                cache[mid] = {v: stairs(json.load(open(os.path.join(data, sub, mid + '.json')))['seats'], fl if v != 'located' else None, 7400)
                              for v, sub in (('located', 'traces'), ('hi', 'traces-hi'), ('lo', 'traces-lo'))}
            for variant in ('hi', 'lo'):
                d = n = 0
                for p in live:
                    a_ = cache[mid]['located'].get(str(p))
                    b_ = cache[mid][variant].get(str(p))
                    for W in range(t0 + 1, min(t1, 7399) + 1):
                        la = (a_[W] - W) if a_ else 0
                        lb = (b_[W] - W) if b_ else 0
                        d += abs(lb - la); n += 1
                md = d / max(1, n)
                sel.append((mid, t0, variant, md))
                if md < BAND_MIN:
                    continue
                arms = [a for a in ('C2', 'C2@2', 'C2@3', 'C2w', 'C2w@2', 'C2w@3') if a in e['arms']]
                for k, ch in enumerate(chunks(arms, len(live), t0, e['len'])):
                    tag = f'{variant}{chr(97 + k)}'
                    print(f"out/_ckpt/logs/{mid}-{t0}-{tag}.txt node scripts/ckpt/ckpt_run.mjs --match {mid} --t0 {t0} --len {e['len']} --arms {','.join(ch)} --trace reports/ckpt-data/traces-{variant}/{mid}.json --floor reports/ckpt-data/floor/{mid}.json --tag {tag}")
        with open(os.path.join(data, 'band_select.csv'), 'w', newline='') as fo:
            w = csv.writer(fo)
            w.writerow(['mid', 't0', 'variant', 'meanAbsLagDiffVsLocated', 'rerun'])
            for mid, t0, variant, md in sel:
                w.writerow([mid, t0, variant, round(md, 2), int(md >= BAND_MIN)])
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
    if 'swap' in what or 'swaplate' in what:
        # Vb 与 Vc 两个文件只差 1500 拍以后才启用的捐兵规则（tryDonateToTeammate 里 g.t < 1500 直接返回），
        # 1500 拍之前逐字相同 → 断面 0 / 630 上 Vc 不用单独跑（留 A075、A094 的开局窗口各一条当确定性核对：应与 Vb 逐位相同）。
        wins = ((0, 630, 1500) if 'swap' in what else ()) + ((3213, 4284) if 'swaplate' in what else ())
        for mid in A_MIDS:
            for ver in ('va', 'vb', 'vc'):
                if ver == hist_ver(mid):
                    continue
                for t0 in wins:
                    if ver == 'vc' and t0 < 1500 and not (t0 == 0 and mid in ('A075', 'A094')):
                        continue
                    live, end = live_seats(mid, t0)
                    if t0 >= end - 100 or not live:
                        continue
                    for k, ch in enumerate(chunks(['C1', 'C2', 'C1@2', 'C2@2', 'C1@3', 'C2@3'], len(live), t0, WIN[t0])):
                        tag = f'{ver}{chr(97 + k)}'
                        print(f"out/_ckpt/logs/{mid}-{t0}-{tag}.txt node scripts/ckpt/ckpt_run.mjs --match {mid} --t0 {t0} --len {WIN[t0]} --strat {ver} --arms {','.join(ch)} --tag {tag}")

if __name__ == '__main__':
    main()
