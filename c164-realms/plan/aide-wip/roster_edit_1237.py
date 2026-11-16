#!/usr/bin/env python3
"""Roster edit of 11-16 12:37: the machine table of 12:33 (ctrl's final list, the director's split of the public pool).

Rewrites the node cell of every person's row and the node bullet's newest part.
"""
import re

p = "/agent/repos/c164-aide-f3-b9ab/c164-realms/plan/ROSTER.md"
t = open(p, encoding="utf-8").read()


def swap(old, new):
    global t
    assert t.count(old) == 1, (t.count(old), old)
    t = t.replace(old, new)


NODE = {
    318: "node33、node97；公共池 node73–76 跑关口和 checkall",
    319: "跑游戏的 12 台：node34、93–96、98–100、103–106；另 node12、node5、node6",
    320: "不用",
    321: "node35；另 node17（室外走查，代投 a4 的室内账）",
    322: "node36；火车线第二台 node77",
    323: "node37；火车线第二台 node80",
    324: "node38", 325: "node39", 326: "node40",
    335: "node49；火车线第二台 node78（和 cable 合用）",
    338: "node52；火车线第二台 node78（和 m1 合用）",
    340: "node54；另 node4（导出、进游戏的验证）",
    346: "node60；火车线第二台 node79",
    361: "node9",
}
for chat in range(327, 354):
    NODE.setdefault(chat, "node%d" % (chat - 286))
for chat in range(356, 361):
    NODE[chat] = "node%d" % (chat - 288)

lines = t.split("\n")
done = 0
for i, line in enumerate(lines):
    m = re.match(r"^\| ([a-z0-9]+) \| c(\d{3}) \| ([^|]*) \| ", line)
    if not m:
        continue
    chat = int(m.group(2))
    if chat not in NODE:
        continue
    lines[i] = "| %s | c%d | %s | %s" % (m.group(1), chat, NODE[chat], line[m.end():])
    done += 1
assert done == 42, done
t = "\n".join(lines)

swap(
    "**12:23 回来八台（总控；总监助理 g2 #1724），各归各人，号和上面那张固定表不一样，以这句为准：s2 node33、s1 node34、facade node35、a2 node36、a4 node37、a1 node38、shell node39、dome node40**（自己的 check、关口、离线自查图都可以在上面跑；新盘先探一单）；别人的还没回来，回来了总监助理在群里发。",
    "**12:33 池子顶到 106 台，都回来了（总控的定稿；总监助理 g2 #1746；上面那张「聊天号 − 257」的固定表作废，「节点」一栏照新的填了）**："
    "c321 到 c353 一人一台，节点号 = 聊天号 − 286（facade node35……mast node60，cr3 node61……ashlar node67）；rec node68、smoke node69、vault node70、clkrm node71、astro node72；sound node9；"
    "s2 node33、node97；s1 跑游戏的 12 台 node34、93–96、98–100、103–106（别人别投）；总监自用 node12、node101、node102（验包和审图）。"
    "**总监名下另 16 台交总监助理当公共池（对 c318–c361 全开）**：node73–76 给 s2 跑关口和 checkall；node77–80 是火车这条线的第二台（a2 node77，cable 和 m1 node78，mast node79，a4 node80）；node85–92 公共，自己的机器忙了再投，一台一单。"
    "自己的机器上 check、关口、离线自查图都可以跑，一次一单；新盘先探一单，被拒是授权没到，过五分钟再探。"
    "主 Agent 只剩一台在带七十多个会话（总控 12:33）：派单慢、会话看着卡住多半是排队；谁十分钟没动静，总监助理报总监，总监请总控重拉。",
)
open(p, "w", encoding="utf-8").write(t)
print("ok", done)
