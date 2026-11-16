#!/usr/bin/env python3
"""Roster edit of 10:52: the lamp helpers after cr4's and power's changes, clocks and cable to the dark heaps."""
P = "/agent/repos/c164-aide-f3-b9ab/c164-realms/plan/ROSTER.md"
t = open(P, encoding="utf-8").read()
n = 0


def swap(old, new):
    global t, n
    assert t.count(old) == 1, (t.count(old), old[:40])
    t = t.replace(old, new)
    n += 1


swap("目标 11:30 版暗格到 0，定了不补的 44 格除外） | 星厅 hall←vault；授时室 m2←clkrm；发电房 power←cable；"
     "底片库不用帮手（vault 自己的 116 格 10:41 已合）。10:46 派的，g2 #1549 |",
     "目标 11:30 版暗格到 0，定了不补的除外；关口加 `--no-verify`） | 星厅 hall←vault、clkrm（楼梯 39 格，"
     "总监 10:45 把楼梯厅的光源放到 11）；授时室 m2←a3（cr4 10:46 派的，clkrm 让出来改去星厅）；"
     "发电房 power 自己补（10:47，灯和光源都在他的包里，交 cr4）；底片库不用帮手（vault 自己的 116 格 10:41 已合）。"
     "g2 #1549 是 10:46 的头一版，以这一行为准 |")

swap("m1 和 m5（10:31 起）、comet（10:45 起，cr2 派的）；地段和文件由 lights 划，各自过关口交 cr2。",
     "m1 和 m5（10:31 起）、comet（10:45 起，cr2 派的）、clocks（10:49 起：lights 名下还没人管的堆）；"
     "地段和文件由 lights 划，各自过关口交 cr2。dome 一人背屋面和小穹顶两堆，cable 10:50 起接其中一堆。")

swap("暗格清单是 sound 量的：`cursor/c164-sound-lightaudit-f3-cbc6-wip` 的 `renders/_wip/light/dark.md`，按归属分了堆 |",
     "暗格清单是 sound 量的：`cursor/c164-sound-lightaudit-f3-cbc6-wip` 的 `renders/_wip/light/dark.md`，按归属分了堆；"
     "总装每进一批灯他重跑一遍，头一行写着量的是哪个总装头（10:46 起台阶、门槛和地面都按 5 级算，"
     "定了不补的另列、不进总数：9fbb2e0c 上暗 223 格，不补 48 格） |")

open(P, "w", encoding="utf-8").write(t)
print("swaps:", n)
