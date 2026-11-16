#!/usr/bin/env python3
"""11-16 13:20: the director's 13:16 rule (an owner merges his own small package himself; chart is a second approver
for interiors) into the roster and, at the director's word, into roles/COMMON.md section 0 item 10."""
R = "/agent/repos/c164-aide-f3-b9ab/c164-realms/plan/ROSTER.md"
C = "/agent/repos/c164-aide-f3-b9ab/c164-realms/plan/roles/COMMON.md"


def edit(path, pairs):
    t = open(path, encoding="utf-8").read()
    for old, new in pairs:
        assert t.count(old) == 1, (path, t.count(old), old)
        t = t.replace(old, new)
    open(path, "w", encoding="utf-8").write(t)


RULE = (
    "**只动自己包的小包，屋主自己合（总监 11-16 13:16；审批排队了：cr3 手上 4 个，最老的等了 45 分钟）。**"
    "只动自己包里文件的小包（做细、改可见距离的档、修自己的错），屋主自己合进总装，不过审批人。条件三条：改的文件全在自己的包里（自己的模块、卡、图）；"
    "自己的测试场景在节点上 check 过了；合完马上在自己的机器上跑关口，红了十分钟内修或退。提交说明照旧写 `merge <类别>/<包名> <提交>`，后面加 `(self)`。"
    "**还要过审批人的**：新的包、新的东西第一次进总装；动了别人的文件或者公共的（`_kit`、common、骨架、接口、别人的模块）；占原版方块、加声音事件、加计分板的。"
    "s2 一直在查头：点了谁的名谁立刻修或退；**同一个人弄红两次，收回自己合的资格**，回去排队。取头前五分钟（:05 到 :10、:35 到 :40）只合已经跑过关口的。"
)

edit(R, [
    (
        "interiors：**cr3（c347）**（原来是 cr4，就是掉线的 c337；11-16 11:45 起 cr3 代，13:00 新开的 stair 不兼评审，就定在 cr3）。",
        "interiors：**cr3（c347）和 chart（c350）**（原来是 cr4，就是掉线的 c337；11-16 11:45 起 cr3 代；**13:16 总监加 chart：室内的新包找 cr3 或 chart，谁空找谁，chart 自己的新包找 cr3**）。"
        + RULE,
    ),
])
edit(C, [
    (
        "interiors：cr4（c337）。**【交付】发给本类的审批人，不再发 s2。**",
        "interiors：cr3（c347）和 chart（c350）（原来是 cr4，c337，11-16 11:45 掉线后 cr3 代；13:16 总监加 chart：室内的新包找 cr3 或 chart，谁空找谁，chart 自己的新包找 cr3）。**【交付】发给本类的审批人，不再发 s2。**",
    ),
    (
        "   - **s2 不再逐个合包。**管 common，守着总装头是绿的：",
        "   - " + RULE + "合的做法就是上面第 1 点的四步。\n"
        "   - **s2 不再逐个合包。**管 common，守着总装头是绿的：",
    ),
])
print("ok")
