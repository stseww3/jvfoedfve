#!/usr/bin/env python3
"""council_fill.py — 把会审稿模板里的填空换成脚本输出里的数，生成 reports/COUNCIL-PROPOSAL.md。

    timeout 120 python3 c136-review/agents/R08/scripts/council_fill.py [--check]

为什么要有这一步：议题 2 里「四分之一线」「名字池」两节用的是整局重演的真相口径（deathbank / namepool），重演在后台分批跑，
覆盖的局数会变。数字不手抄：deathbank.py、namepool.py 各自把会审稿要用的数按打印时的写法放进自己 JSON 的 report 字段，
这里只做替换。模板里的填空写成 __名字__；有一个填空找不到来源就报错，不写文件。

克隆续跑（cloneprobe）、四个断面开环可信期（openloop）、两处走偏根因的充分性检验（fixprobe）的数也走这条路。

读：scripts/council_src/council.tpl.md、out/_cross/deathbank.json、out/_cross/namepool.json、out/_cross/cloneprobe.json、out/_cross/openloop.json、
    out/_cross/fixprobe.json
写：reports/COUNCIL-PROPOSAL.md（--check 时只报告、不写）
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TPL = os.path.join(HERE, "council_src", "council.tpl.md")
DST = os.path.join(ROOT, "reports", "COUNCIL-PROPOSAL.md")
SOURCES = ["deathbank.json", "namepool.json", "cloneprobe.json", "openloop.json", "fixprobe.json", "boatwhy.json"]
KEY = re.compile(r"__([A-Z][A-Z0-9_]*?)__")


def main():
    check = "--check" in sys.argv
    vals = {}
    for name in SOURCES:
        J = json.load(open(os.path.join(ROOT, "out", "_cross", name), encoding="utf-8"))
        rep = J.get("report")
        if not rep:
            sys.exit(f"{name} 里没有 report 字段：先重跑对应的汇总脚本")
        dup = set(rep) & set(vals)
        if dup:
            sys.exit(f"填空重名：{sorted(dup)}")
        vals.update(rep)
    text = open(TPL, encoding="utf-8").read()
    used, missing = set(), set()

    def sub(m):
        k = m.group(1)
        if k not in vals:
            missing.add(k)
            return m.group(0)
        used.add(k)
        return vals[k]

    out = KEY.sub(sub, text)
    if missing:
        sys.exit("模板里有来源里没有的填空：" + " ".join(sorted(missing)))
    print(f"填空 {len(used)} 种；来源里有、模板没用到的 {len(set(vals) - used)} 种：{' '.join(sorted(set(vals) - used))}")
    if check:
        return
    tmp = DST + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(out)
    os.replace(tmp, DST)
    print(f"写了 {os.path.relpath(DST, ROOT)}（{out.count(chr(10))} 行）")


if __name__ == "__main__":
    main()
