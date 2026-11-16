#!/usr/bin/env python3
"""Roster edit of 11-16 12:38: the director's three changes of rhythm (g2, 12:36)."""
p = "/agent/repos/c164-aide-f3-b9ab/c164-realms/plan/ROSTER.md"
t = open(p, encoding="utf-8").read()


def swap(old, new):
    global t
    assert t.count(old) == 1, (t.count(old), old)
    t = t.replace(old, new)


swap(
    "版本从 B1 编号，每半小时一版，**13:00 取头导 B1**。",
    "版本从 B1 编号，每半小时一版。**12:36 机器回来以后节奏改三处（总监公告）：① 取头提前到每小时的 :40 和 :10，图在整点和半点给管理员**（B1 12:40，B2 13:10，B3 13:40；s2 取手上最新一个查过是绿的头，报 outb 和 s1；取头、导出、拍图三段并着跑）。"
    "**② 头要一直有人查**：s2 用 node73–76 轮着对最新的头跑关口和 checkall；审批人照旧先合（场景检查过了就合），合完马上在自己的机器上补跑关口，红了十分钟内修好或者退掉那一笔；s2 查出头是红的就点名是哪一笔，那一笔的审批人退。"
    "**③ 给管理员看的要有会动的**：s1 每版除了 12 张再录两三段小片（mp4，10 到 20 秒，720p 以内，8 MB 以下）。",
)
open(p, "w", encoding="utf-8").write(t)
print("ok")
