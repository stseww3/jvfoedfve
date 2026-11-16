#!/usr/bin/env python3
"""Roster edit of 11-16 12:48: the seven empty places a4 asked to have distributed (aide, g2 #1795), a4's notes of 12:44."""
p = "/agent/repos/c164-aide-f3-b9ab/c164-realms/plan/ROSTER.md"
t = open(p, encoding="utf-8").read()


def swap(old, new):
    global t
    assert t.count(old) == 1, (t.count(old), old)
    t = t.replace(old, new)


anchor = "facade（塔钟报刻、暖房）；a6（布谷鸟钟、猫、电报杆）；a4（暗道） |\n"
new_row = (
    "| 戊补 评审在 A8 上圈给 a4 的空处，a4 12:44 请分人（总监助理 12:46 派，g2 #1795；位置和审批找 a4，细目在 review 的 `plan/aesthetics/S3-reviews-v4.md` 末节和 cr2 的 `S3-reviews-v4-cr2.md` 记事 cr2-N12；排在各人头一样之后） "
    "| 前庭的测风杆（33, 0, −14，风杯转）：orrery；带罩的小赤道仪（33, 0, 15）：scope；东北栏边的风暴信号杆和脚下的小绞车：a3；"
    "前庭铺地的冒汽格栅、电缆沟盖板：m3；子午小屋屋顶缝的活门（链和绞车，慢开慢合）：sdome；下观景台的扶手、踏步口线、方位盘：shell；"
    "大台阶南侧墙压顶（z 9，x 61–67）：ashlar。"
    "a4 12:44 定的位置：东崖面的栈道水管归 snow（桥交了再做）；货梯 astro 在挡墙南段 (61..63, z 23..25)；场子 ashlar 照他的提法搭；机车库 m1 在下平台东沿 x 86..90、z −23..−15。"
    "a4 手上留线路、site 审批、室内走查、前庭两座喷泉 | a4 |\n"
)
swap(anchor, anchor + new_row)
open(p, "w", encoding="utf-8").write(t)
print("ok")
