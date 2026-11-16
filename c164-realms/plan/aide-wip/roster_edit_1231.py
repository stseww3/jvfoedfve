#!/usr/bin/env python3
"""Roster edit of 11-16 12:31: section 丙三 of the second round (the director's g2 message of 12:27, plan/round2.md b9f4fd46)."""
p = "/agent/repos/c164-aide-f3-b9ab/c164-realms/plan/ROSTER.md"
t = open(p, encoding="utf-8").read()


def swap(old, new):
    global t
    assert t.count(old) == 1, (t.count(old), old)
    t = t.replace(old, new)


anchor = "facade、cr3（塔钟）；facade（屋顶）。位置打架的审批人当场调，调了告诉总监助理 |\n"
new_row = (
    "| 丙三 第二批（总监 12:27；手上头一样交了就接，不用等总监） "
    "| `machines/difference-engine` 差分机，放星图室的空地板上：clkrm（现在就开；位置和 chart 对；塔钟留给 tower、clocks）；"
    "`interiors/workshop` 发电房里的仪器工坊：power；"
    "`props/gauges` 表和安全阀做成一套件（m3 的管线和各屋都用）：a6；"
    "`machines/recorders-2` 自记仪器（地震仪、自记气压计、日照计）：rec（气动信筒之后）；"
    "`main/semaphore` 北翼屋顶的臂板信号塔：dome（穹顶交了以后）；"
    "`sky/far-lights` 远处山尖的灯、云海边缘一列火车的灯：cloud；"
    "`sky/alive` 天的着色器里星星闪烁、流星：a2（travel 之后）；"
    "`machines/balloon` 气象站的探空气球：orrery（风车之后）；"
    "`site/engine-shed` 下平台边的机车库：m1（机车交了以后）；"
    "`interiors/duty-room` 缆车站房里的值班室：a6（家具）、sound（留声机的旋律）、outb（核导出以后猫在不在）；"
    "`motion/levers` 能动手的（底件加「看拉杆的开关」，头一批七处：汽笛 cable、天窗 dome、大镜 scope、报时球 tower、转车盘 ashlar、星厅弧光灯 lights、电报机 m2）：mast 写底件（开场之后），各家接自己的；"
    "`motion/doors` 正门两扇铁门走近自己开：lights（星厅的两样之后）；塔里能坐的升降机：tower（等载人试出来再定）；"
    "`props/life` 生活痕迹每间屋两样（不出现人）：各屋主，件从 a6 的家具里要。"
    "另：s2 12:20 量出客户端超线，可见距离分四档（做法看 s2 的公告），室内的件一律近档，各屋主 13:00 前改 "
    "| cr3（差分机、工坊、自记仪器、气球、铁门）；a6（表和阀自审换 review 看、值班室、生活痕迹）；facade（信号塔、升降机）；cr2（远处的灯、天、能动手的）；a4（机车库） |\n"
)
swap(anchor, anchor + new_row)
open(p, "w", encoding="utf-8").write(t)
print("ok")
