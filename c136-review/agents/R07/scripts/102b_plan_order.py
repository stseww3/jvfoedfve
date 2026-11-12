#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""102b_plan_order.py — R07：把 102_cp_plan.py 排出的对照清单按「先跑哪一类」重新排序（只改先后，不增不减）。

批处理脚本（102_cp_batch.sh）每一轮都重读清单，跳过已有结果的行，所以可以在它运行时改清单的先后。
类别按下面 PR 的顺序；同一类里按这一断面的局次序（被按住最重的局在前）；都相同时保持原来的先后。
读、写：out/_cache/cp/plan_all.txt（先写 .tmp 再整体替换）
用法：python3 102b_plan_order.py
"""
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
PLAN = os.path.join(HERE, "..", "out", "_cache", "cp", "plan_all.txt")

# 排在最前面的个别行（局 名字），按这里的先后
FIRST = ["A091 C2-t4284-s0", "A033 H-t4284-s0", "A091 H-t4284-s0"]
# 4284 / 4285 断面的对照每条要重演 5184 拍，机器被占满时一次占槽（约 105 秒）跑不完，会把排在它后面的都挡住。
# 所以这一类一律排到最后，先跑只需重演 1500~2400 拍的。
LONG_LAST = re.compile(r'-t428[45]-')
# 之后按类别。已经跑完的类别留在前面不影响（批处理跳过已有结果的行）。
PR = [r'^mt-', r'^C2-t0-s0$', r'^C1-t0-s0$', r'^C0-t0-s0$', r'^C2-t0-s1$', r'^C1-t0-s0-v[ab]$', r'^(C1-t1500-s0|C2-t1500-s1)$', r'^(C1-t630-s0|C2-t630-s1)$',
      r'^C1-t1500-s0-v[ab]$',
      r'^(C1-t428[45]-s0|C2-t428[45]-s1)$',
      r'^C0-t1500-s0$', r'^C0-t630-s0$',
      r'^C2-t630-s0$', r'^C2-t1500-s0$',
      r'^H-t(630|1500)-s1$',
      r'^C2-t428[45]-s0$',
      # 以下是还没跑完的：先补 C1 的第二个种子（后段各断面单局数字的噪声主要来自 C1 自己抽的延迟），再补其余。
      # 机器被占满时一次占槽只能分到很少的 CPU，所以同样要紧的里面，重演拍数少的排前面（断面 0 / 630 的先于 1500 的）。
      r'^C1-t630-s1$', r'^(C1-t0-s1|C2-t0-s2)$', r'^C1-t1500-s1$',
      r'^C1-t0-s0-d0_0$', r'^C1-t0-s0-d10_18$', r'^C0b-t0-s0$', r'^C1-t0-s0-d5_12$',
      r'-nl$',
      r'^C2-t630-s2$',
      r'^H-t0-s1$',
      r'^C2-t1500-s2$',
      r'^C0-t428[45]-s0$',
      r'^H-t428[45]-s0$', r'^H-t428[45]-s1$',
      r'^(C1-t428[45]-s1|C2-t428[45]-s2)$', r'-rp$',
      r'^C1-t1500-s1-v[ab]$', r'^C2-t1500-s1-v[ab]$',
      r'^C1-t0-s2$', r'^(C1-t630-s2|C1-t1500-s2)$']
RANK = {
    0: "A070 A062 A089 A053 A082 A007 A079 A091 A061 A033 A039".split(),
    630: "A039 A070 A062 A089 A061 A053 A082 A033 A079 A091 A007".split(),
    1500: "A070 A039 A089 A082 A062 A053 A091 A079 A061 A033 A007".split(),
    4284: "A082 A007 A079 A039 A033 A089 A061 A062 A053 A091 A070".split(),
}


def key(i, line):
    p = line.split()
    g, tag = p[0], p[1]
    if f"{g} {tag}" in FIRST:
        return (-1, 0, FIRST.index(f"{g} {tag}"), tag, i)
    cls = next((k for k, r in enumerate(PR) if re.search(r, tag)), len(PR))
    m = re.search(r'-t(\d+)-', tag)
    t0 = int(m.group(1)) if m else 0
    if t0 == 4285:
        t0 = 4284
    rk = RANK.get(t0, RANK[0])
    return (1 if LONG_LAST.search(tag) else 0, cls, rk.index(g) if g in rk else 99, tag, i)


def main():
    lines = [x for x in open(PLAN, encoding="utf-8").read().split("\n") if x.strip()]
    out = [x for _, x in sorted(((key(i, x), x) for i, x in enumerate(lines)), key=lambda z: z[0])]
    assert sorted(out) == sorted(lines)
    tmp = PLAN + ".tmp"
    open(tmp, "w", encoding="utf-8").write("\n".join(out) + "\n")
    os.replace(tmp, PLAN)
    print(f"PLAN-ORDER-OK {len(out)} 行")


if __name__ == "__main__":
    main()
