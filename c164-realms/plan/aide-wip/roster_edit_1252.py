#!/usr/bin/env python3
"""Roster edit of 11-16 12:52: the admin's direction of 12:40 (the director's announcement of 12:47, plan/fine.md):
the variety is frozen, what is cut, the gas holder becomes a hydraulic accumulator, the wind engine is power's."""
p = "/agent/repos/c164-aide-f3-b9ab/c164-realms/plan/ROSTER.md"
t = open(p, encoding="utf-8").read()


def swap(old, new):
    global t
    assert t.count(old) == 1, (t.count(old), old)
    t = t.replace(old, new)


# the section's opening paragraph
swap(
    "**③ 给管理员看的要有会动的**：s1 每版除了 12 张再录两三段小片（mp4，10 到 20 秒，720p 以内，8 MB 以下）。",
    "**③ 给管理员看的要有会动的**：s1 每版除了 12 张再录两三段小片（mp4，10 到 20 秒，720p 以内，8 MB 以下）。\n\n"
    "**12:47 管理员 12:40 定了方向（总监公告；新的一页 `plan/fine.md`，和卡页有出入的以它为准）：「当前方案下再加10倍细节和各种内容 内容不要太多但一定要细和贴合地图」。**"
    "① **花样冻结**，丙四以后不加卡；下面表里划掉的是砍了的，动了手的把零件并进自己别的东西里。"
    "② **做细一样再开下一样**：远（60 格，轮廓）、中（10 格，零件）、近（2 格，痕迹和字）三层都到了才算交；线是任取一块 4×4 格的面，10 格处数得出不少于 10 件零件，2 格处每件上至少一处痕迹或字，室外不留大于 3×3 格、室内 2×2 格的空白面；细顺着结构走，远看的轮廓和明暗不许变花。"
    "③ **贴合地图**，设定一处定死、各处照抄：全站的钟一个时刻一个节拍（clocks 的常数），日期 `14 NOV` 不写年份，今晚的编号 `No. 2187`，彗星只叫 `THE COMET`，哪儿都不写台名、用台徽，机器铭牌一个样（号找 a6，`plan/parts/numbers.md`），门牌深蓝底白字，管子的色环和编号找 m3，全站一套字（a6 发取字的函数）。"
    "④ **预算**：展示实体全图 2600 → 6000，一间屋 250 → 400（近档加小档）；看板每个机位 600、命令 40/120 不变。"
    "⑤ **怎么干**：各人先管自己已有的那一块，一次补十样、一个小包、随到随合，卡里放 10 格和 2 格两张自查图和近景的机位；室外的主人先做室外的中层；火车开场和点了名的机器照做，一样三层都到了才算交。"
    "⑥ **评审改看细**：review 写量「空白占比」的工具，每版每张跑一遍；cr2、cr3 每版挑六处近景判到没到近层；s1 每版加拍六张近景（机位屋主给）。",
)

# 丙二
swap(
    "`site/gasometer` 煤气柜：m5（穹顶那一样交了以后）；",
    "`site/gasometer` **12:47 改成水压蓄能器**（一样的铸铁导架，里面一只配重筒随水泵和货梯慢升慢降，管子通货梯和吊杆）：m5（穹顶那一样交了以后）；",
)
swap(
    "`machines/wind-engine` 水塔顶的风力抽水机，加气象站的风向标和自记气压计：orrery（行星仪自己的几样交了以后；从 power 挪来）；",
    "水塔顶的风力抽水机：**power**（总监 12:47 定：他 12:27 已写好的那一台，留在 `site/outbuildings`；泵杆、水管到水塔、油渍、铭牌一起到位）；气象站的风向标和自记气压计：orrery（先把行星仪自己做到近层）；",
)
swap(
    "a4（煤气柜、货梯、场子）；a6（管桥）；cr3（风力抽水机）；",
    "a4（蓄能器、货梯、场子、风力抽水机）；a6（管桥）；cr3（风向标、气压计）；",
)

# 丙三
swap(
    "`main/semaphore` 北翼屋顶的臂板信号塔：dome（穹顶交了以后）；",
    "~~`main/semaphore` 北翼屋顶的臂板信号塔：dome~~（12:47 砍了）；",
)
swap(
    "`sky/far-lights` 远处山尖的灯、云海边缘一列火车的灯：cloud；",
    "`sky/far-lights` 远处山尖的灯、云海边缘一列火车的灯：cloud（和信号塔对闪的那一盏 12:47 砍了）；",
)
swap(
    "`site/engine-shed` 下平台边的机车库：m1（机车交了以后）；",
    "~~`site/engine-shed` 下平台边的机车库和里面第二台机车：m1~~（12:47 砍了）；",
)
swap(
    "`interiors/duty-room` 缆车站房里的值班室：a6（家具）、sound（留声机的旋律）、outb（核导出以后猫在不在）；",
    "`interiors/duty-room` 缆车站房里的值班室：a6（家具）、sound（留声机的旋律）、outb（核导出以后猫在不在；猫留一只，坐着）；",
)
swap(
    "塔里能坐的升降机：tower（等载人试出来再定）；",
    "~~塔里能坐的升降机：tower~~（12:47 砍了）；",
)

# 丙四
swap(
    "滚球钟、自己在打的电报打字机、能按的电报键",
    "滚球钟、~~自己在打的电报打字机~~（12:47 砍了）、能按的电报键",
)
swap(
    "值班室的布谷鸟钟、猫隔几分钟换一处待着：a6（猫和 outb 对）；",
    "~~值班室的布谷鸟钟、猫隔几分钟换一处待着：a6~~（12:47 砍了）；",
)
swap(
    "找齐六张星图、看过彗星以后塔顶的烟花：smoke、cloud；南观景台旁的铁架玻璃暖房：sdome（天文室的两样之后）；",
    "~~找齐六张星图、看过彗星以后塔顶的烟花：smoke、cloud；南观景台旁的铁架玻璃暖房：sdome~~（12:47 都砍了）；",
)
swap(
    "发电房到主楼南翼底层的检修暗道：a4 点人（排在 B3 以后，两头找 power、vault）。",
    "~~发电房到主楼南翼底层的检修暗道：a4 点人~~（12:47 砍了）。",
)

# 丁
swap("`sky/birds`、`sky/meteors`、`site/fountain`、`motion/small-life`", "`sky/birds`、`sky/meteors`、~~`site/fountain`~~（前庭喷泉 12:47 砍了）、`motion/small-life`")

# 戊补
swap(
    "前庭的测风杆（33, 0, −14，风杯转）：orrery；",
    "前庭的测风杆（33, 0, −14，风杯转）：orrery（总监 12:47 认了，和风向标、气压计、探空气球一起，气球排最后）；",
)
swap(
    "机车库 m1 在下平台东沿 x 86..90、z −23..−15。a4 手上留线路、site 审批、室内走查、前庭两座喷泉",
    "（机车库 12:47 砍了。）a4 手上留线路、site 审批、室内走查（前庭两座喷泉 12:47 砍了）",
)
open(p, "w", encoding="utf-8").write(t)
print("ok")
