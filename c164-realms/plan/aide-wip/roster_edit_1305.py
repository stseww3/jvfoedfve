#!/usr/bin/env python3
"""Roster edit of 11-16 13:05: four new chats (c363 orrery, c364 hall, c365 stair, c366 comet) replace the dropped
ones; the director's two largest blanks of B1 (V1 retaining wall -> sdome, the two pavements -> a4, ashlar's yard first);
approver queues are reported every half hour."""
import re

p = "/agent/repos/c164-aide-f3-b9ab/c164-realms/plan/ROSTER.md"
t = open(p, encoding="utf-8").read()


def swap(old, new):
    global t
    assert t.count(old) == 1, (t.count(old), old)
    t = t.replace(old, new)


# the bullet on dropped sessions
a = t.index("**12:52 orrery（c343）也掉了；12:53 总监请总控把四位都重拉了")
b = t.index("十分钟没报到的，总监助理报总监再拉。", a) + len("十分钟没报到的，总监助理报总监再拉。")
t = t[:a] + (
    "**12:52 orrery（c343）也掉了；12:53 总控重拉四位，拉了四次都绑不回聊天。总监 13:00 定：开新聊天接替，代号和机器照旧："
    "orrery = c363（node57）、hall = c364（node62）、stair = c365（node51）、comet = c366（node44）；"
    "旧号 c343、c348、c337、c330 归档，别再发消息、别再点名。**新来的四位先读 `roles/COMMON.md` 第 0 节、`plan/fine.md`、`plan/round2.md`、"
    "这张名单里自己那一行和卡，再私信总监助理报到（节点、审批人、投单的做法）。各人的活写在自己那一行；代着的人把那一块交回："
    "行星仪归 orrery（气象站的风向标、自记气压计和前庭测风杆留给 power，探空气球先放）；星厅归 hall（天花的星座轮流亮、弧光灯、正门的铁门留给 lights，"
    "V4 的门洞和门洞灯留给 vault）；大台阶归 stair（不兼评审）；comet 从 a2 手上接 sky/alive。"
) + t[b:]

swap(
    "interiors：cr4（就是 stair，c337）；**11-16 11:45 起由 cr3（c347）代，到 stair 回来为止**。",
    "interiors：**cr3（c347）**（原来是 cr4，就是掉线的 c337；11-16 11:45 起 cr3 代，13:00 新开的 stair 不兼评审，就定在 cr3）。"
    "**总监 13:00：总监助理每半小时报各审批人手上排着几个包、最老的等了几分钟；谁排到 5 个以上或者等过 10 分钟，总监加副审批人。**",
)

# the four rows
swap(
    "| orrery | c343 | node57 | c236 | machines/orrery（**11-16 12:52 会话掉了，12:53 重拉**；回来还是他的，照 `plan/fine.md` 做到近层：月亮、传动轴、蜗杆；气象站三样和前庭测风杆 12:55 给了 power） | ",
    "| orrery | **c363**（11-16 13:00 开的新聊天，接 12:52 掉线的 c343） | node57 | c236 | machines/orrery：行星仪照 `plan/fine.md` 做到近层（月亮、传动轴、蜗杆、刻度和铭牌；审批人 cr3）；前任做的都在总装里，分支在右边；"
    "子午线镶嵌也是这一行的；气象站三样和前庭测风杆 12:55 给了 power，探空气球先放 | ",
)
swap(
    "| hall | c348 | node62 | c243 | interiors/starhall。**11-16 11:45 会话掉了**：V4 的门洞由 vault（c358）接，做在这个包里；西门的灯 3b09f9d 由 s2 代合了（e10d420c） | ",
    "| hall | **c364**（11-16 13:00 开的新聊天，接 11:45 掉线的 c348） | node62 | c243 | interiors/starhall：星厅的墙、地、回廊、门照 `plan/fine.md` 做到近层（审批人 cr3）；"
    "天花的星座轮流亮、弧光灯、正门的铁门是 lights 的，V4 的门洞和门洞灯是 vault（c358）的，都做在这个包里，动之前先对；傅科摆是 clocks 的。前任：西门的灯 3b09f9d 由 s2 代合了（e10d420c） | ",
)
swap(
    "| stair | c337 | node51 | c225 | **11-16 11:45 会话掉了（interiors 的审批和 V8 到 V10 的分 cr3 代）**；site/stair（两次交付都过了关口）；",
    "| stair | **c365**（11-16 13:00 开的新聊天，接 11:45 掉线的 c337） | node51 | c225 | **现在的活（总监 13:00、13:02）：先帮 sdome 做 V1 正中那面挡墙（上平台的东墙，大台阶两侧）；"
    "再 site/stair 大台阶和两侧挡墙照 `plan/fine.md` 做细；之后帮 a4 做下平台的地。审批人 a4；不兼评审**（interiors 的审批和 V8 到 V10 的分归 cr3）。下面是前任 c337 的记录：site/stair（两次交付都过了关口）；",
)
swap(
    "| comet | c330 | node44 | c230 | **11-16 11:45 会话掉了，手上没有收尾的活，不补人**；sky/comet；然后 sky/ridges",
    "| comet | **c366**（11-16 13:00 开的新聊天，接 11:45 掉线的 c330） | node44 | c230 | **现在的活（总监 13:00）：从 a2 手上接 sky/alive（彗尾做细、星星闪烁、流星）；之后和 scope 做目镜里的彗星像。审批人 cr2**；"
    "着色器只有 a2 那一套，要动找 a2。下面是前任 c330 的记录：sky/comet；然后 sky/ridges",
)

# other mentions of the old chats
swap("hall（c348）：门；m2（c351）：上楼的两根立管", "hall（c364）：门；m2（c351）：上楼的两根立管")
swap("| 星厅 hall（c348） | ", "| 星厅 hall（c364） | ")
swap(
    "每间屋屋主自己列十样；大台阶（stair 掉线）上要补的由 a4 分人 | ",
    "每间屋屋主自己列十样；大台阶归 13:00 新开的 stair（c365）。"
    "**总监 13:02 看了 B1 的 12 张，点了最大的两块空白**：① V1 正中那面挡墙（上平台的东墙，x 60、z −38..38，六十格宽十格高）：sdome 做（天文室收了尾就做），stair 帮，a4 批；"
    "每 6 到 8 格一道扶壁、扶壁之间盲拱、三四个真洞口（库房和煤仓的铁门、亮灯的拱窗）、一根蒸汽干管（m3 的管，红环）、泄水口和水痕、灯托架、铁梯、排水沟盖、台徽；墙顶以上不多出东西，扶壁不挡下平台的路。"
    "② 两块大铺地，a4 管总：前庭铺出图案（子午线铜条通长、方位刻度、收边、雨水口、冒汽格栅、电缆沟盖板），分出去的七处照做；下平台 ashlar 的场子（嵌地窄轨、转车盘、煤斗车、地秤、煤堆）是主角，**ashlar 这一样排到最前**，浑天仪的收尾往后放。"
    "review 13:30 前拿 B1 的 12 张跑一遍空白占比当底数 | ",
)
# sdome's and ashlar's rows
swap(
    "| sdome | c328 | node42 | c224 | main/smalldome（含屋面）；",
    "| sdome | c328 | node42 | c224 | **11-16 13:02 总监：V1 正中那面挡墙归他（见「戊」那一行；a4 批，stair 帮），天文室手上的收了尾就做**；main/smalldome（含屋面）；",
)
swap(
    "| ashlar | c353 | node67 | c204 | materials/ashlar 打磨",
    "| ashlar | c353 | node67 | c204 | **11-16 13:02 总监：下平台的场子（嵌地窄轨、转车盘、煤斗车、地秤、煤堆）排到最前，浑天仪的收尾往后放**；materials/ashlar 打磨",
)
open(p, "w", encoding="utf-8").write(t)
print("ok")
