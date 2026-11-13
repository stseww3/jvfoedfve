#!/usr/bin/env python3
# restore_check.py — 数据包被清掉又回到原处之后，核对回来的这一份和原来那一份是不是给出同样的结果。
#
# 背景：11 月 12 日 20:53（UTC）这台机器上各人的工作区和数据包 /agent/repos/c136-data/ 被整个清掉，21:42 数据包回到原处。
# 谁恢复的、是不是原来那一份，R06 不知道；数据包里的文件（除四个历史策略文件有内容散列以外）R06 手里没有清掉之前的散列可以对。
# 能对的是结果：全部有录像的局的实盘签名（--mode live：只放录像，过引擎移植，对日志快照）清掉之前算过一遍、入了库（calib/live/）。
# 数据包回来之后经闸门重算一遍到 calib/batchcheck/restore/live/（bash sim-v2/tools/g0_all.sh restore），这里逐字段比（计时字段除外）。
# 重算用到数据包里的：每一局的录像 replay.txt、日志 in_game.log，引擎移植 src/sim/，以及地图。
#
# 用法（在 c136-review/agents/R06 下）：python3 sim-v2/tools/restore_check.py
# 结果：sim-v2/calib/restore-check.json
#   total 入库的局数；n 已重算并比过的；same 逐字段相同的；leaves 比过的数（叶子）个数；pending 还没重算的；
#   extra 重算目录里有、入库目录里没有的局（数据包里多出来的局）；bad 不同的局（头几处不同）；
#   firstAt / lastAt 重算结果文件的时间范围（第一次核对完整时记下，之后工作区再重新检出、文件时间变了也不改）
import json
import os
import subprocess
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
CALIB = os.path.normpath(os.path.join(HERE, '..', 'calib'))
A = os.path.join(CALIB, 'live')
B = os.path.join(CALIB, 'batchcheck', 'restore', 'live')
OUT = os.path.join(CALIB, 'restore-check.json')


def names(d):
    return sorted(f for f in os.listdir(d) if f.endswith('.json')) if os.path.isdir(d) else []


def iso(ts):
    return datetime.fromtimestamp(ts, timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def main():
    a, b = names(A), names(B)
    res = {'total': len(a), 'n': 0, 'same': 0, 'leaves': 0, 'pending': len([f for f in a if f not in b]),
           'extra': [f[:-5] for f in b if f not in a], 'bad': []}
    if b:
        out = subprocess.run(['node', os.path.join(HERE, 'same_result.mjs'), '--json', A, B],
                             capture_output=True, text=True, timeout=100).stdout.strip().split('\n')
        j = json.loads(out[-1])
        res['n'], res['same'], res['leaves'] = j['n'], j['same'], j['leaves']
        res['bad'] = out[:-1]
        res['onlyOld'], res['onlyNew'] = j.get('onlyA', []), j.get('onlyB', [])
        mt = [os.path.getmtime(os.path.join(B, f)) for f in b]
        res['firstAt'], res['lastAt'] = iso(min(mt)), iso(max(mt))
    # 已经有一份完整的核对、这次比出来的个数也一样：重算时刻沿用那一份里记的（工作区重新检出以后文件时间不可信）
    if os.path.exists(OUT):
        try:
            old = json.load(open(OUT, encoding='utf8'))
        except ValueError:
            old = {}
        if old.get('pending') == 0 and res['pending'] == 0 and old.get('n') == res['n'] and old.get('same') == res['same'] and old.get('firstAt'):
            res['firstAt'], res['lastAt'] = old['firstAt'], old['lastAt']
    tmp = OUT + '.tmp'
    with open(tmp, 'w', encoding='utf8') as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1)
    os.replace(tmp, OUT)
    print('数据包恢复后的核对：入库 %d 局，已重算并比过 %d 局，逐字段相同 %d 局（比了 %d 个数），还没重算 %d 局，不同 %d 局，数据包里多出来的局 %d 个' % (
        res['total'], res['n'], res['same'], res['leaves'], res['pending'], len(res['bad']), len(res['extra'])))
    for x in res['bad'][:8]:
        print('  ' + x[:240])
    return 0 if res['pending'] == 0 and res['n'] == res['total'] and res['same'] == res['n'] else 1


if __name__ == '__main__':
    sys.exit(main())
