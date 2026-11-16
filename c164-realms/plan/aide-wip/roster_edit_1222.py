#!/usr/bin/env python3
"""Roster edit of 12:22: the second round is on (the director's announcement of 12:12, plan/round2.md):
who does which card, the stand-in for the star hall, the machines as they are used now."""
P = "/agent/repos/c164-aide-f3-b9ab/c164-realms/plan/ROSTER.md"
t = open(P, encoding="utf-8").read()
n = 0


def swap(old, new):
    global t, n
    assert t.count(old) == 1, (t.count(old), old[:40])
    t = t.replace(old, new)
    n += 1


# 1. the machines of the node bullet
swap("都不出图：出图只有 s1 进存档拍的那一套；合用机上不跑任何检查和出图。",
     "都不出图：出图只有 s1 进存档拍的那一套；合用机上不跑任何检查和出图。"
     "**12:12 第二轮开工以后（总监助理 g2 #1707、#1712、#1719）**：本场景的短 check 写好先推、直接投总监机，"
     "人人都算点过名，一人一次一单（总监机 12:16 起三个工人并着跑：短单三单同时，长单一次一个）；"
     "node7、node8 总控 12:14 对 c318–c361 全开了，自己投长单（整山的 check、底件测试；火车这条线和 sky、motion、site 用 node7，"
     "其余用 node8），不出图，不用再找 lights、tower 代投；node5、node6 归 s1（总控给新六位也开了，但别投）；"
     "进游戏试的找 outb（node4）和 s1。8 台留到 16:00；池子第一批 12:25 入网，node97 到 99 在最后一批。")

# 2. the closing section: the stop of 11:39 is lifted
swap("12:00 取头导 A8，目标是给管理员上传的候选版。",
     "12:00 取头导 A8（8cddfa98），存着当底。**12:12 第二轮开工，「这四件以外的打磨全停」作废，见下一节。**")

# 3. the new section, before the helpers' table
swap("## 帮手（快车道第 7 条，11-16 08:22 起；09:12 起照收尾的清单派）",
     "## 第二轮：细节、复古科技、会动（总监 11-16 12:12 的公告；卡页 `plan/round2.md`，有出入以公告和卡页后来改的为准）\n\n"
     "管理员 11:59、12:05：细节不够，不够复古的科技感，加火车，所有东西都要会动；火车是地图的引子，飞艇不要。"
     "不急着投稿。版本从 B1 编号，每半小时一版，**13:00 取头导 B1**。审批人不变（interiors 由 cr3 代）；"
     "卡页上的「谁」是总监的提名，审批人可以换人，换了告诉总监助理。小包，先合、头上统一验；"
     "预算 a2 管账（全图每拍平均 40 条命令、展示实体 2600、一个画面 600）。"
     "每版照旧：s2 守头、outb 导出、s1 进存档拍、a4 和 facade 走查、sound 量暗格、评审打分。\n\n"
     "| 卡 | 谁 | 审批 |\n"
     "| --- | --- | --- |\n"
     "| 甲 `motion/travel`（底件里「沿路线走」，能载人；12:35 前在真机里试人坐着顺不顺） | a2、s1 | cr2 |\n"
     "| 甲 `machines/train`（机车新做，现有的车当客车，齿条） | cable（牵头）、m1（机车） | cr3 |\n"
     "| 甲 `site/railway`（栈桥接长进云，远段石拱桥；线路数据 `site/_rail.py`，12:30 前定） | a4（定线）、cloud（桥墩入云）、snow（石拱） | a4 |\n"
     "| 甲 `motion/arrival`（开场：头一次进服的人坐车上山、出云出标题、到站下车） | mast（牵头）、outb（导出和验证） | cr2 |\n"
     "| 甲 `motion/train-smoke-sound` | smoke、sound | cr2 |\n"
     "| 甲 `props/station`（臂板信号机、站钟、里程桩、水鹤、煤台、电报杆） | lamps | a6 |\n"
     "| 乙 `props/steam-mains`（蒸汽干管、阀、表、安全阀喷汽） | m3（管）、power（表和阀） | a6 |\n"
     "| 乙 `props/pneumatic`（气动信筒） | rec | a6 |\n"
     "| 丙 已有的全动起来（每人管自己的东西，13:00 前先交最显眼的一样） | dome、m5（穹顶慢转、天窗开合）；scope（大镜跟彗星）；"
     "tower、clocks（塔钟的针、报时球、风向标）；ashlar（浑天仪）；cable（卷扬机一整套）；mast（桅杆顶灯和火花，排在开场之后）；"
     "power（发电房，另接 outb 的气象站和风力抽水机）；m2、rec（授时室）；chart（星图室）；vault（底片库，V4 门洞先完）；"
     "astro（蓄电池室）；sdome（天文室，女儿墙先完）；a3（穹顶室）；clkrm（钟室）；orrery（行星仪）；"
     "lamps、a1（带火苗的灯，贴图动画，a1 12:30 前发做法）；a6（旗）；shell、facade（屋顶通风帽、窗里的灯）；"
     "**星厅：lights 代主人**（hall 掉线，总监助理 12:17 派；门洞的灯还是 vault 的） | 各类审批人 |\n"
     "| 丁 `sky/birds`、`sky/meteors`、`site/fountain`、`motion/small-life` | cloud（桥墩之后）；a2（travel 之后）；a4 或他点的人；smoke（火车的烟之后） | cr2、a4 |\n"
     "| 戊 细节加密：评审 12:40 前在 A8 的 12 张图上各圈五处最空的，发给那一块的主人、抄总监助理；以后每版重圈 | review、cr2、cr3 圈；"
     "下平台和前庭 a4 分人（家具 a6），山体 a4、snow，云海 cloud，屋顶 shell、sdome，每间屋屋主自己列十样；"
     "大台阶（stair 掉线）上要补的由 a4 分人 | 各类审批人 |\n\n"
     "## 帮手（快车道第 7 条，11-16 08:22 起；09:12 起照收尾的清单派）")

# 4. lights' row: the star hall
swap("| lights | c331 | node74 | c220 | sky/lights（含洗墙轮） |",
     "| lights | c331 | node74 | c220 | sky/lights（含洗墙轮）；**11-16 12:17 起星厅（interiors/starhall）的代主人**"
     "（hall 掉线；第二轮里星厅的两样会动的、十样细节、V4 和 V7 上圈的空处；交 cr3） |")

open(P, "w", encoding="utf-8").write(t)
print("swaps:", n)
