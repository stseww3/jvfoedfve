p = "c164-realms/plan/ROSTER.md"
t = open(p, encoding="utf-8").read()
n = 0

def swap(old, new):
    global t, n
    assert t.count(old) == 1, (t.count(old), old[:40])
    t = t.replace(old, new)
    n += 1

swap("m1 和 m5（10:31 起）；地段和文件由 lights 划，各自过关口交 cr2。",
     "m1 和 m5（10:31 起）、comet（10:45 起，cr2 派的）；地段和文件由 lights 划，各自过关口交 cr2。")
swap("| 看板没过线的图（10:00 版）：",
     "| 四间屋补灯（总监 10:43 的快道：屋主改评审点的，帮手只做灯，两个包并着走、各交各的；只加灯的包 check 过了就交，免重画留图，交付写明「只加灯」；会和屋主改到同一个文件的，灯放进 lights 的包。目标 11:30 版暗格到 0，定了不补的 44 格除外） | 星厅 hall←vault；授时室 m2←clkrm；发电房 power←cable；底片库不用帮手（vault 自己的 116 格 10:41 已合）。10:46 派的，g2 #1549 |\n| 看板没过线的图（10:00 版）：")
open(p, "w", encoding="utf-8").write(t)
print("swaps:", n)
