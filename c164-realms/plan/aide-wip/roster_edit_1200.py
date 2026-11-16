#!/usr/bin/env python3
"""Roster edit of 12:00: the three dropped sessions and who stands in, the eight machines to the end,
the four closing matters of 11:39, A7's numbers, the lamps closed at 0 dark cells, the guide's progress."""
P = "/agent/repos/c164-aide-f3-b9ab/c164-realms/plan/ROSTER.md"
t = open(P, encoding="utf-8").read()
n = 0


def swap(old, new):
    global t, n
    assert t.count(old) == 1, (t.count(old), old[:40])
    t = t.replace(old, new)
    n += 1


# 1. approvers: cr3 stands in for cr4; a bullet on the dropped sessions before the node bullet
swap("interiors：cr4（就是 stair，c337）。s2 守着总装头是绿的",
     "interiors：cr4（就是 stair，c337）；**11-16 11:45 起由 cr3（c347）代，到 stair 回来为止**。s2 守着总装头是绿的")
swap("- **节点（总控 11-16 08:12 放出共享池",
     "- **掉线的三位（11-16 11:45，桥上显示「没人接手」；总监的公告：不等他们回来）**：stair（cr4，c337）、"
     "hall（c348）、comet（c330）。interiors 的交付发 cr3，V8 到 V10 的分也由他评；s2 11:48 代 cr4 合了两包只加灯的"
     "（m2 授时室壁灯 39d46055、hall 西门 3b09f9d）；V4 的门洞交 vault（c358）：做在 hall 的包里、从总装头拉支，"
     "先在 A8 的图上量一次，够了就不动；comet 手上没有收尾的活，不补人。再有人掉线，总监助理直接报总监谁手上有四件事里的活。\n"
     "- **节点（总控 11-16 08:12 放出共享池")

# 2. the node bullet: eight machines to the end
swap("第一批 11:48 起回来，11:58 回齐，以总监助理在群里的话为准。断着的时候通的机器"
     "（各一次一单；别人把命令原文私信持机器的人代投）：node4 outb（导出，锁 c340）、"
     "node5 和 node6（11:40 前跑点名的短单，之后归 s1）、node7 lights（锁 c331）、"
     "node8 tower（锁 c327，代投 interiors 只加灯的包，顺序听 cr4）、node9 sound（锁 c361，量暗格，替新六位代投）、"
     "node17 facade（锁 c321，走查，替 a4 代投）、node12 s1；总监机（`tools/a0job.sh`）只收 s2 的 checkall 和头一次的本场景 check，"
     "照总监助理点名的顺序。",
     "**管理员 11:37：掉的那批多半回不来；总监 11:39：照手上 8 台干到底，回来了算白捡**"
     "（总控 11:58:30 起分批恢复，先给别的项目，第三批起按原归属还，名单以总监助理在群里的话为准；这 8 台留到 12:50）。"
     "**8 台谁用**（总监助理 11:43，g2 #1662；各一次一单，别人把命令原文私信持机器的人代投；投出 15 分钟没回执找总监助理）："
     "node4 outb（锁 c340；导出，导览进游戏的验证）；node12、node5、node6 s1（验收图、导览验收）；"
     "node17 facade（锁 c321；室外走查，代投 a4 每版的室内账）；node9 sound（锁 c361；对头量暗格）；"
     "node7 lights（锁 c331）和 node8 tower（锁 c327）代投长单。总监机（`tools/a0job.sh --no-push`）收 s2 的 checkall "
     "和四件事里头一次的本场景 check，投前私信总监助理点名，一人一次一单"
     "（已点名、写好就投的：a6、smoke、a4、rec、ashlar、m2，和修室外走查三条小毛病的 cable、sdome）。"
     "都不出图：出图只有 s1 进存档拍的那一套；合用机上不跑任何检查和出图。")
swap("；一行没跑过的先跑一次 check；11:35 取头。共享池没有独占锁",
     "；一行没跑过的先跑一次 check。11:35 取的头 1a0f1af9 是 A7（11:42 交给管理员），12:00 取头导 A8，"
     "赶不上的进 12:30。共享池没有独占锁")

# 3. the closing section: the four matters of 11:39
swap("清单以外的打磨先放下；跨类的事两位审批人直接对。",
     "清单以外的打磨先放下；跨类的事两位审批人直接对。\n\n"
     "**11-16 11:39 起只做收尾的四件事（总监公告；这四件以外的打磨全停：写到一半的推到自己的分支留着，不投单、不交付，"
     "然后长等待待命，有事总监助理点名）**：一、剩下的暗格（11:52 总装 2b7eb71e 上量到 0，A8 起生效；不补的 48 格另列）；"
     "二、没过的图：V4（门洞，vault 接 hall 的）、V5（a4 换小屋的石料，f0925b0c 已合）、V10（m2，只动颜色和灯罩）；"
     "V6 在 A7 上过了；三、导览：mast、rec、ashlar、smoke、cloud，加 a6、outb；四、每版的导出、存档图、走查、打分、合并："
     "outb、s1、a4、facade、s2、各审批人、四个评审、总监助理。A7（总装 1a0f1af9，11:35 取头）已交管理员；"
     "12:00 取头导 A8，目标是给管理员上传的候选版。")
swap("| a4 管室内，facade 管室外，直接派给作者 |",
     "| a4 管室内，facade 管室外，直接派给作者。**A7（1a0f1af9）上室内 0、室外 0**；室外新出的三条不挡人的小毛病"
     "总监定了都修、用屏障块不改外形：卷扬机矮栅（cable）、南观景台台阶脚的墩帽（a4，f8373a4a 已合）、端部露台女儿墙（sdome） |")
swap("| lights（c331），各间室内的主人配合；暗格由 sound 量（每进一批灯重量一趟）；帮手见下表 |",
     "| lights（c331），各间室内的主人配合；暗格由 sound 量（每进一批灯重量一趟）；帮手见下表。"
     "**11:52 总装 2b7eb71e 上暗 0 格**（A7 里还是 39 格：授时室 22、西门里 17，两包 11:48 才合；不补的 48 格另列） |")
swap("V8 到 V10 cr4。天、雾、远景",
     "V8 到 V10 cr4（11:45 起 cr3 代）。**A7 上过 9 张**，没过 V4 3.8、V5 3.8、V10 3.6。天、雾、远景")

# 4. the helpers' table
swap("、授时室两盏（a3，位置 m2 定的）；西门里 19 格随 hall 的包。",
     "；授时室 a3 的两盏罩灯撤了（墙前那格是护墙板，钩子跳过），改成 m2 包里的壁灯 39d46055；"
     "西门里 17 格是 hall 的 3b09f9d；这两包 s2 11:48 代 cr4 合了。")
swap("手空的（谁赶不上私信总监助理点名补）：clocks、clkrm、astro、m1、cable。",
     "**11:52 总装 2b7eb71e 上暗 0 格，这一行收了**：lights 名下没有在途的包，基座墙的洗墙灯照总监 11:39 停着不做。")
swap("授时室 m2←a3（cr4 10:46 派的，灯在 lights 的包里）",
     "授时室 m2←a3（cr4 10:46 派的；a3 的罩灯后来撤了，灯是 m2 自己包里的壁灯 39d46055）")
swap("11:08 派的，g2 #1589、#1591；sound 没动，接着量暗格 |",
     "11:08 派的，g2 #1589、#1591；sound 没动，接着量暗格。**12:00 的进度**：甲 b254fe1 已合（0e6b941a，outb 在 node4 上进游戏验过）；"
     "运动循环的底件（a2，5aae7398）和丙（1272fcbf）已合（e57f5547）；乙的公共件 `props/plaques` 006f0d1a 已合（404dcc3e），"
     "rec 和 ashlar 的两张表 check 过了、等 a6 合；s1 在 node5、node6 上做导览验收 |")

# 5. the three rows of the dropped sessions, and vault's
swap("| stair | c337 | node80 | c225 | site/stair（两次交付都过了关口）；",
     "| stair | c337 | node80 | c225 | **11-16 11:45 会话掉了（interiors 的审批和 V8 到 V10 的分 cr3 代）**；site/stair（两次交付都过了关口）；")
swap("| hall | c348 | node91 | c243 | interiors/starhall |",
     "| hall | c348 | node91 | c243 | interiors/starhall。**11-16 11:45 会话掉了**：V4 的门洞由 vault（c358）接，做在这个包里；"
     "西门的灯 3b09f9d 由 s2 代合了（e10d420c） |")
swap("| comet | c330 | node73 | c230 | sky/comet；然后 sky/ridges",
     "| comet | c330 | node73 | c230 | **11-16 11:45 会话掉了，手上没有收尾的活，不补人**；sky/comet；然后 sky/ridges")
swap("| vault | c358 | node103 | interiors/platevault（南翼底层底片库和暗房，P3，没有前任） |",
     "| vault | c358 | node103 | interiors/platevault（南翼底层底片库和暗房，P3，没有前任）；**11-16 11:45 起接 hall 的 V4 门洞**"
     "（做在 `interiors/starhall` 里，从总装头拉支；先在 A8 的图上量一次，够了就不动；交 cr3） |")

open(P, "w", encoding="utf-8").write(t)
print("swaps:", n)
