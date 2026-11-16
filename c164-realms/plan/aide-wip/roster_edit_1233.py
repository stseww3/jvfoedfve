#!/usr/bin/env python3
"""Roster edit of 11-16 12:33: section 丙四 of the second round (the director's g2 message of 12:30, plan/round2.md 7d91d06c); the goods lift moves from scope to astro."""
p = "/agent/repos/c164-aide-f3-b9ab/c164-realms/plan/ROSTER.md"
t = open(p, encoding="utf-8").read()


def swap(old, new):
    global t
    assert t.count(old) == 1, (t.count(old), old)
    t = t.replace(old, new)


swap(
    "`site/goods-lift` 下平台的水压货梯和煤台的吊杆：scope（大镜那一样交了以后）；",
    "`site/goods-lift` 下平台的水压货梯和煤台的吊杆：astro（蓄电池室的两样交了以后；12:30 从 scope 挪来，scope 做目镜）；",
)
anchor = "cr2（远处的灯、天、能动手的）；a4（机车库） |\n"
new_row = (
    "| 丙四 有意思的细节（总监 12:30；都是小件，排在各人手上已有的活之后，谁先空出手谁先做） "
    "| 傅科摆（星厅正中，挂点和 orrery 对）、全站的钟秒针同一拍（给相位常数，各家的钟照它）：clocks（塔钟那边交给 tower）；"
    "滚球钟、自己在打的电报打字机、能按的电报键（按了远处山尖的灯回答：灯找 cloud，底件找 mast）：m2（V10 先做）；"
    "暗房显影盘里显出彗星的照片：vault（V4 先做）；黑板上的算式自己写出来：chart；星厅天花的星座轮流亮：lights；"
    "目镜里真能看（收尾 THE COMET, IN FOCUS 也用它，和 smoke 对）、落日平台的小望远镜：scope；"
    "塔钟每刻钟的铃调和转出来的日月星辰：tower、sound；值班室的布谷鸟钟、猫隔几分钟换一处待着：a6（猫和 outb 对）；"
    "找齐六张星图、看过彗星以后塔顶的烟花：smoke、cloud；南观景台旁的铁架玻璃暖房：sdome（天文室的两样之后）；"
    "车厢里晃的箱子和挂灯：cable；沿线的电报杆密到车里看得见一根一根掠过：lamps；"
    "发电房到主楼南翼底层的检修暗道：a4 点人（排在 B3 以后，两头找 power、vault）。"
    "另：存档里人够方块的距离是 0，拉杆方块拉不动，**能动手的手柄一律做成 interaction 实体**（够实体的距离 3 格），底件 mast 写 "
    "| cr3（傅科摆、钟、滚球钟、显影、黑板、星座、目镜、车厢里）；cr2（电报有人回、烟花）；facade（塔钟报刻、暖房）；a6（布谷鸟钟、猫、电报杆）；a4（暗道） |\n"
)
swap(anchor, anchor + new_row)
open(p, "w", encoding="utf-8").write(t)
print("ok")
