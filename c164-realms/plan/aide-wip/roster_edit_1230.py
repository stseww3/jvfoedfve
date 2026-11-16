#!/usr/bin/env python3
"""Roster edits of 11-16 12:30: section 丙二 of the second round, the eight nodes that came back at 12:23."""
p = "/agent/repos/c164-aide-f3-b9ab/c164-realms/plan/ROSTER.md"
t = open(p, encoding="utf-8").read()


def swap(old, new):
    global t
    assert t.count(old) == 1, (t.count(old), old)
    t = t.replace(old, new)


swap(
    "8 台留到 16:00；池子第一批 12:25 入网",
    "**12:23 回来八台（总控；总监助理 g2 #1724），各归各人，号和上面那张固定表不一样，以这句为准：s2 node33、s1 node34、facade node35、a2 node36、a4 node37、a1 node38、shell node39、dome node40**（自己的 check、关口、离线自查图都可以在上面跑；新盘先探一单）；别人的还没回来，回来了总监助理在群里发。8 台留到 16:00；池子第一批 12:25 入网",
)
swap(
    "power（发电房，另接 outb 的气象站和风力抽水机）",
    "power（发电房；气象站和风力抽水机 12:22 挪给了 orrery，见丙二）",
)
old_row_end = "**星厅：lights 代主人**（hall 掉线，总监助理 12:17 派；门洞的灯还是 vault 的） | 各类审批人 |\n"
new_row = (
    "| 丙二 室外看得见的机器（总监 12:22：室外先加机器、后加摆设；每张室外看板 V1、V2、V3、V5、V6、V11、V12 里至少一件看得见的、在动的机器；木箱木桶排后） "
    "| `site/gasometer` 煤气柜：m5（穹顶那一样交了以后）；`props/pipe-bridge` 跨大台阶侧的管桥：m3（表和安全阀找 power）；"
    "`machines/wind-engine` 水塔顶的风力抽水机，加气象站的风向标和自记气压计：orrery（行星仪自己的几样交了以后；从 power 挪来）；"
    "`main/tower-works` 塔钟露出机芯：tower、clocks、clkrm；`site/goods-lift` 下平台的水压货梯和煤台的吊杆：scope（大镜那一样交了以后）；"
    "`site/yard` 下平台的场子（窄轨、转车盘、煤斗车、地秤）：ashlar（浑天仪那一样交了以后；位置和 a4 对）；"
    "`main/roof-works` 屋顶（通风帽、烟道、天窗、检修走道）和主楼背面、两翼墙上的管线：shell "
    "| a4（煤气柜、货梯、场子）；a6（管桥）；cr3（风力抽水机）；facade、cr3（塔钟）；facade（屋顶）。位置打架的审批人当场调，调了告诉总监助理 |\n"
)
swap(old_row_end, old_row_end + new_row)
open(p, "w", encoding="utf-8").write(t)
print("ok")
