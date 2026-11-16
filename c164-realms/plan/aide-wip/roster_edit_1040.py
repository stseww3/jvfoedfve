p = "c164-realms/plan/ROSTER.md"
t = open(p, encoding="utf-8").read()
n = 0

def swap(old, new):
    global t, n
    assert t.count(old) == 1, (t.count(old), old[:40])
    t = t.replace(old, new)
    n += 1

swap("**10:24 齐了**：68 张卡 67 张在总装里（最后两张是天文室 10:17、钟室 10:24），剩 `common/offline-sky` 待定 |",
     "**10:24 齐了，这一条销账**：67 张卡全在总装里（最后两张是天文室 10:17、钟室 10:24）；`common/offline-sky` 总监 10:32 砍了，不做 |")
swap("**现在没有待领的卡**（`common/offline-sky` 做不做待定，不算）。",
     "**现在没有待领的卡**（`common/offline-sky` 总监 11-16 10:32 定了不做：验收看 s1 进存档拍的真机图，离线图只看构图和件在不在）。")
swap("| lights（c331）的「人走的路都有光」（cr2 10:28：最缺人的一条） | dome（09:21 起；主楼里环梯、大楼梯、回廊、西门过道）、astro（09:49 起；入口到蓄电池室一路）、m1 和 m5（10:31 起）；地段和文件由 lights 划，各自过关口交 cr2 |",
     "| lights（c331）的「人走的路都有光」（cr2 10:28：最缺人的一条） | dome（09:21 起；主楼里环梯、大楼梯、回廊、西门过道）、astro（09:49 起；入口到蓄电池室一路）、m1 和 m5（10:31 起）；地段和文件由 lights 划，各自过关口交 cr2。暗格清单是 sound 量的：`cursor/c164-sound-lightaudit-f3-cbc6-wip` 的 `renders/_wip/light/dark.md`，按归属分了堆 |")
swap("V6 炉火窗和门里的光：cable 帮 power（10:32 起）；",
     "V6 炉火窗和门里的光：vault、mast 帮 power（10:33 起；mast 管锅炉一侧；cable 不空）；")
open(p, "w", encoding="utf-8").write(t)
print("swaps:", n)
