#!/usr/bin/env python3
"""Roster edit of 11:26: the guide card's five people, the dark heaps as they stand, the pool outage of 10:56:30."""
P = "/agent/repos/c164-aide-f3-b9ab/c164-realms/plan/ROSTER.md"
t = open(P, encoding="utf-8").read()
n = 0


def swap(old, new):
    global t, n
    assert t.count(old) == 1, (t.count(old), old[:40])
    t = t.replace(old, new)
    n += 1


swap("、clocks（10:49 起：lights 名下还没人管的堆）；地段和文件由 lights 划，各自过关口交 cr2。"
     "dome 一人背屋面和小穹顶两堆，cable 10:50 起接其中一堆。",
     "；地段和文件由 lights 划。放灯的做法（lights 11:00 的公告）：从 "
     "`cursor/c164-lights-walk-f3-9479` 拉支，只加一个文件 `build/scenes/obs/sky/_ways_<段名>.py`，"
     "关口 `gate.sh sky/lights <提交> --base <总装头> --no-verify`。"
     "11:20 各段都并进了 lights 的一个包、由他一道过关口交 cr2：大楼梯厅楼上 63 格（astro 量的 4 盏）、"
     "石墩一圈（m1）、屋面 20 格（dome 北半、cable 南半）、授时室两盏（a3，位置 m2 定的）；"
     "西门里 19 格随 hall 的包。小穹顶里 18 格是 snow 的（cr4 10:50 派的，灯在他的 `interiors/astroroom` 里，交 cr4）；"
     "钟塔底厅 25 格 clkrm 在钟室的包里补了，11:16 合进总装（161f2088）。"
     "手空的（谁赶不上私信总监助理点名补）：clocks、clkrm、astro、m1、cable。")

swap("星厅 hall←vault、clkrm（楼梯 39 格，总监 10:45 把楼梯厅的光源放到 11）；"
     "授时室 m2←a3（cr4 10:46 派的，clkrm 让出来改去星厅）；",
     "星厅 hall←vault（星厅 20 格，交 cr4；楼梯的两段在 lights 的包里，总监 10:45 把楼梯厅的光源放到 11；"
     "hall 自己改梯脚灯和西门过道）；授时室 m2←a3（cr4 10:46 派的，灯在 lights 的包里）；")

swap("| 看板没过线的图（10:00 版）：",
     "| 导览 `motion/guide`（总监 11-16 11:03 的新卡，11:13 改过一遍，卡在 `plan/packages/motion/guide.md`；"
     "不挡候选版，第一版 11:50 前交，随 12:00 的整包） | 甲 进场标题和署名牌：mast（钩子和 outb 对）；"
     "乙 十二块说明牌：rec、ashlar（a6 先写公共的 `props/plaques`，推到 `cursor/c164-a6-plaques-f3-4ad1`，"
     "两人从那个头拉支，各只加一个文件 `_plaques_east.py`、`_plaques_west.py`，交 a6；星厅的两块在 V7 里放哪和 cr3 对）；"
     "丙 六张星图：smoke（走近检测和收尾）、cloud（摆图和粒子），交 cr2，每刻的预算和 a2 对。"
     "11:08 派的，g2 #1589、#1591；sound 没动，接着量暗格 |\n"
     "| 看板没过线的图（10:00 版）：")

swap("s1 只用真机。共享池没有独占锁",
     "s1 只用真机。**11-16 10:56:30 三台母机挂了，node61～106 整段下线（总控 11:22）**：这一段谁也不要投，"
     "单投出去 15 分钟没回执、-wip 也没有提交就当丢了；第一批 11:48 起回来，11:58 回齐，以总监助理在群里的话为准。"
     "断着的时候通的机器（各一次一单；别人把命令原文私信持机器的人代投）：node4 outb（导出，锁 c340）、"
     "node5 和 node6（11:40 前跑点名的短单，之后归 s1）、node7 lights（锁 c331）、"
     "node8 tower（锁 c327，代投 interiors 只加灯的包，顺序听 cr4）、node9 sound（锁 c361，量暗格，替新六位代投）、"
     "node17 facade（锁 c321，走查，替 a4 代投）、node12 s1；总监机（`tools/a0job.sh`）只收 s2 的 checkall 和头一次的本场景 check，"
     "照总监助理点名的顺序。池子不通时怎么合，见总监 11-16 11:16 的公告：只加灯、本场景 check 跑过的包审批人先合，"
     "合并说明写「关口待跑」；一行没跑过的先跑一次 check；11:35 取头。共享池没有独占锁")

open(P, "w", encoding="utf-8").write(t)
print("swaps:", n)
