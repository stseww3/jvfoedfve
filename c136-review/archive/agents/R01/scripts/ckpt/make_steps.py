#!/usr/bin/env python3
"""make_steps.py — 生成断面归因的批处理步骤文件（给 scripts/run_batch.sh / batch_loop.sh 用）。

每局 5 个首尾相接的窗口：0→630、630→1500、1500→3213、3213→4284、4284→5184（录像不够长就到录像末拍）。
断面拍上我方已经没有活着的席位、或录像放不到的窗口不跑。
臂：C0、C1×3 个种子、C2×3 个种子；窗口结束前出现过页面停摆或掉线离场的局再加 C2w×3 个种子（否则 C2w 与 C2 逐拍相同，不用重复跑）。
按估算的 CPU 把臂分成几个进程（每个进程 ≤ 约 30 秒 CPU），输出 out/_ckpt/runs/<局>-<t0>-<块>.json。

用法：python3 scripts/ckpt/make_steps.py > scripts/steps/ckpt-runs.txt
"""
import csv
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
R01 = os.path.dirname(os.path.dirname(HERE))
OUT = os.path.join(R01, 'out')
MIDS = 'A075 A055 A023 A019 A054 A003 A031 A050 A009 A057 A059 A094 B039 B043'.split()
WINDOWS = [(0, 630), (630, 870), (1500, 1713), (3213, 1071), (4284, 900)]
CPU_BUDGET_MS = 30000


def main():
    mids = [a for a in sys.argv[1:] if not a.startswith('--')] or MIDS
    for mid in mids:
        b = json.load(open(os.path.join(OUT, mid, 'ckpt_base.json')))
        squad = b['squad']
        end = b['endT']
        death = {int(k): v for k, v in b['deathT'].items()}
        page_end = {int(k): v for k, v in b['pageEnd'].items()}
        doomed = set(b['doomed'])
        sq = set(squad)
        left = {}
        for r in csv.DictReader(open(os.path.join(OUT, mid, 'resim_events.csv'))):
            if r['ev'] == 'left' and int(r['p']) in sq:
                left.setdefault(int(r['p']), int(r['t']))
        for t0, ln in WINDOWS:
            if t0 >= end - 100:
                continue
            t1 = min(t0 + ln, end - 1)
            alive = [p for p in squad if death[p] < 0 or death[p] > t0]
            live = [p for p in alive if left.get(p, 10 ** 9) > t0]
            if not live:
                continue
            # 窗口结束前有没有「页面停摆」或「掉线离场」：有才需要把 C2w 单独跑
            page_evt = any(page_end[p] < t1 for p in doomed if p in live) or any(t0 < left.get(p, 10 ** 9) <= t1 for p in live)
            arms = ['C0', 'C1', 'C2'] + (['C2w'] if page_evt else []) + ['C1@2', 'C2@2'] + (['C2w@2'] if page_evt else []) + ['C1@3', 'C2@3'] + (['C2w@3'] if page_evt else [])
            per_arm = len(live) * (0.13 * t0 + 0.11 * (t1 - t0)) + 300
            n = max(1, int(CPU_BUDGET_MS // per_arm))
            chunks = [arms[i:i + n] for i in range(0, len(arms), n)]
            for k, ch in enumerate(chunks):
                tag = chr(ord('a') + k)
                print(f"out/_ckpt/logs/{mid}-{t0}-{tag}.txt node scripts/ckpt/ckpt_run.mjs --match {mid} --t0 {t0} --len {ln} --arms {','.join(ch)} --tag {tag}")


if __name__ == '__main__':
    main()
