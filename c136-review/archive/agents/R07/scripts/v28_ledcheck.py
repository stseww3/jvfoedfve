#!/usr/bin/env python3
"""v28_ledcheck.py — R07：把策略在途账本的销账记录和信道真值逐条对账（接管模式 + v28Debug=1 的那次运行）。

用法：python3 c136-review/agents/R07/scripts/v28_ledcheck.py <matchId> <label> [--show N]
输入：out/_cache/v28/<matchId>_<label>_log.txt（v28_shadow.mjs --takeover … --params '{"v28Debug":1}' 写的）
      [V28-LED] … issue #N …   策略把一条指令记进账本
      [V28-LED] … close #N how 策略认为这条指令了结了（land/step = 看到落地；void/soft/weak/drop = 放弃等待）
      [SHADOW-EXEC] …          信道真值：这条指令实际在哪一拍结算、结果（ok / refused / dropped）
对账键：(号, 发出拍)。账本开着时每号每拍最多发一条，所以这个键唯一。

输出（每一类给条数）：
  准时      销账拍 - 结算拍 ∈ [0, 1]，且结算成功
  早销      账本在指令真正结算之前就销了（之后这条指令的兵不再算在途，可能引出重复下单）
  晚销      结算成功后超过 1 拍才销（这段时间账本多算了在途）
  没落地    指令被信道丢弃或结算时被引擎拒绝（账本只能靠超时放弃）
  未了结    运行结束时还在账本里或还在信道里
"""
import os
import re
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(2)
    mid, label = sys.argv[1:3]
    show = int(sys.argv[sys.argv.index('--show') + 1]) if '--show' in sys.argv else 8
    path = os.path.join(HERE, '..', 'out', '_cache', 'v28', f'{mid}_{label}_log.txt')
    issue = {}      # (me, id) -> dict
    by_key = {}     # (me, t_issue) -> (me, id)
    close = {}      # (me, id) -> (t, how)
    execs = {}      # (me, t_issue) -> (t, how)
    re_issue = re.compile(r'\[V28-LED\] t=(\d+) me=(\d+) issue #(\d+) (\w+) q=(\d+) pct=(\d+) exp=(\d+) site=(\S+)')
    re_close = re.compile(r'\[V28-LED\] t=(\d+) me=(\d+) close #(\d+) (\w+) (\w+) q=(\d+) age=(\d+)')
    re_exec = re.compile(r'\[SHADOW-EXEC\] t=(\d+) me=(\d+) (\w+) q=(\d+) issued=(\d+) (\w+)')
    with open(path, encoding='utf-8') as f:
        for ln in f:
            m = re_issue.search(ln)
            if m:
                t, me, i, kind, q, pct, exp, site = m.groups()
                issue[(int(me), int(i))] = dict(t=int(t), kind=kind, q=int(q), pct=int(pct), exp=int(exp), site=site)
                by_key[(int(me), int(t))] = (int(me), int(i))
                continue
            m = re_close.search(ln)
            if m:
                t, me, i, how = m.group(1), m.group(2), m.group(3), m.group(4)
                close[(int(me), int(i))] = (int(t), how)
                continue
            m = re_exec.search(ln)
            if m:
                t, me, kind, q, t0, how = m.groups()
                execs[(int(me), int(t0))] = (int(t), how)
    if not issue:
        print(f'{mid} {label}: 日志里没有 [V28-LED] issue 记录（这次运行要带 --params \'{{"v28Debug":1}}\' 且开着 P1）')
        sys.exit(1)

    cls = Counter()
    by_how = defaultdict(Counter)
    examples = defaultdict(list)
    for key, e in sorted(issue.items(), key=lambda kv: (kv[1]['t'], kv[0])):
        me = key[0]
        ex = execs.get((me, e['t']))
        cl = close.get(key)
        if cl is None or ex is None:
            c = '未了结'
        elif ex[1] != 'ok':
            c = '没落地'
        else:
            d = cl[0] - ex[0]
            c = '早销' if d < 0 else ('准时' if d <= 1 else '晚销')
        cls[c] += 1
        how = cl[1] if cl else '-'
        by_how[c][how] += 1
        if c in ('早销', '晚销', '没落地') and len(examples[c]) < show:
            examples[c].append(f"me={me} #{key[1]} {e['kind']} q={e['q']} pct={e['pct']} 发出t={e['t']} 销账t={cl[0] if cl else '-'}({how}) 结算t={ex[0] if ex else '-'}({ex[1] if ex else '-'})")
    n = sum(cls.values())
    print(f'{mid} {label}: 账本记了 {n} 条在途指令')
    for c in ('准时', '早销', '晚销', '没落地', '未了结'):
        if cls[c]:
            hows = ' '.join(f'{h}×{k}' for h, k in sorted(by_how[c].items()))
            print(f'  {c} {cls[c]}（{100 * cls[c] / n:.1f}%）按销账方式：{hows}')
    for c in ('早销', '晚销', '没落地'):
        for s in examples[c]:
            print(f'    [{c}] {s}')


if __name__ == '__main__':
    main()
