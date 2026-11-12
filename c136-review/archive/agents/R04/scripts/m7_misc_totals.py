#!/usr/bin/env python3
# m7_misc_totals.py — 议会提案里要用、而现成的表里没有直接给出的几个合计。只做相加，不做别的推算。
# 用法：python3 scripts/m7_misc_totals.py > out/m7/misc_totals.txt
#   1) 真引擎重放与日志快照的对账点数合计（out/engine-replay-check.txt，scripts/engine_replay_check.sh 的输出）
#   2) hub 的纯 JS 重放脚本对日志快照的核对合计（out/hub-resim-check.txt，scripts/hub_resim_check.sh 的输出）
#   3) 我早先的重放脚本重放 A013 的对账结果原文（out/resim-A013.txt，scripts/resim.mjs 的输出）里的汇总行
#   4) 表 14 里「贴着内置 AI 的号·决策拍：总数 / 出手 / 被闸门卡住」一行的两个占比（out/m7/TABLES.md 只给了条数）
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
    fp = os.path.join(ROOT, 'out', 'hub-resim-check.txt')
    if os.path.exists(fp):
        last = {}
        mid = None
        for ln in open(fp, encoding='utf8'):
            m = re.match(r'^(\w+): H=(\d+) land=\d+ teams=(\d+)', ln)
            if m:
                mid = m.group(1)
                last[mid] = dict(H=int(m.group(2)), teams=int(m.group(3)))
            m = re.match(r'^\s+traj 核对：(\d+) 行，地一致 (\d+)，兵一致 (\d+)，都一致 (\d+)', ln)
            if m and mid:
                last[mid].update(rows=int(m.group(1)), both=int(m.group(4)))
        team = {k: v for k, v in last.items() if v.get('teams', 0) > 0 and 'rows' in v}
        solo = {k: v for k, v in last.items() if v.get('teams', 0) == 0 and 'rows' in v}
        print('hub 的纯 JS 重放（c136-data/src/tools/resim.mjs，带组队配色和分队的移植）对日志快照：组队局 %d 局、%d 行，地和兵都一致 %d 行；逐行全对的 %d 局；不全对的：%s' % (
            len(team), sum(v['rows'] for v in team.values()), sum(v['both'] for v in team.values()),
            sum(1 for v in team.values() if v['rows'] == v['both']),
            '、'.join('%s %d/%d' % (k, v['both'], v['rows']) for k, v in team.items() if v['rows'] != v['both']) or '无'))
        for k, v in solo.items():
            print('  不分队的局 %s（真人 %d 个）：%d 行里都一致 %d 行' % (k, v['H'], v['rows'], v['both']))
    fp = os.path.join(ROOT, 'out', 'resim-A013.txt')
    if os.path.exists(fp):
        print('我自己早先写的重放脚本（scripts/resim.mjs：直接用 src/sim/sim 的 Game，没有组队配色的移植）重放 A013 的对账（out/resim-A013.txt 原文摘行）：')
        for ln in open(fp, encoding='utf8'):
            if re.search(r'完全一致|中位|拒|首次不一致|首个不一致', ln):
                print('  ' + ln.rstrip()[:400])
    fp = os.path.join(ROOT, 'out', 'm7', 'TABLES.md')
    if os.path.exists(fp):
        for ln in open(fp, encoding='utf8'):
            if not ln.startswith('| 贴着内置 AI 的号·决策拍 600~1499 拍：总数 / 出手 / 被闸门卡住'):
                continue
            cells = [c.strip() for c in ln.strip().strip('|').split('|')]
            for name, cell in (('13 局合计', cells[2]), ('去掉 A073', cells[3])):
                tot, act, blk = [int(x) for x in re.findall(r'\d+', cell)]
                print('表 14「贴着内置 AI 的号·决策拍 600~1499 拍」%s：总数 %d，出手 %d（%.0f%%），被闸门卡住 %d（%.0f%%）' % (
                    name, tot, act, 100.0 * act / tot, blk, 100.0 * blk / tot))


if __name__ == '__main__':
    main()
