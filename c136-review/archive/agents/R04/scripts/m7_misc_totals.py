#!/usr/bin/env python3
# m7_misc_totals.py — 议会提案里要用、而现成的表里没有直接给出的几个合计。只做相加，不做别的推算。
# 用法：python3 scripts/m7_misc_totals.py > out/m7/misc_totals.txt
#   1) 真引擎重放与日志快照的对账点数合计（out/engine-replay-check.txt，scripts/engine_replay_check.sh 的输出）
#   2) 纯 JS 模拟器重放 A013 的对账结果原文（out/resim-A013.txt，scripts/resim.mjs 的输出）里的汇总行
import os, re, sys
sys.dont_write_bytecode = True
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    fp = os.path.join(ROOT, 'out', 'engine-replay-check.txt')
    pts = same = n = 0
    bad = []
    mid = None
    for ln in open(fp, encoding='utf8'):
        m = re.match(r'^# (\w+) 真引擎重放', ln)
        if m:
            mid = m.group(1)
        m = re.match(r'^# 与日志快照对账：(\d+) 个点，领土和余额都完全一致 (\d+) 个', ln)
        if m:
            n += 1
            pts += int(m.group(1))
            same += int(m.group(2))
            if m.group(1) != m.group(2):
                bad.append(mid)
    print('真引擎重放（线上客户端原文 live_game_js.js 在 Node 里跑）对日志快照：%d 局、%d 个快照点，领土和余额都完全一致 %d 个；有不一致的局：%s' % (
        n, pts, same, '、'.join(bad) or '无'))
    fp = os.path.join(ROOT, 'out', 'resim-A013.txt')
    if os.path.exists(fp):
        print('纯 JS 模拟器（src/sim/sim）按录像重放 A013 的对账（out/resim-A013.txt 原文摘行）：')
        for ln in open(fp, encoding='utf8'):
            if re.search(r'完全一致|中位|拒|首次不一致|首个不一致', ln):
                print('  ' + ln.rstrip()[:400])


if __name__ == '__main__':
    main()
