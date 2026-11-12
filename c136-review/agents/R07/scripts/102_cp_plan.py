#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""102_cp_plan.py — R07：生成断面对照的运行清单（每行：局 名字 100_checkpoint.mjs 的参数）。

默认只出「实际在跑的清单」（重计算槽位紧张以后收窄过的）；加 --full 时连同已经删掉、不再补的次要对照一起出。

  主网格（历史上这一局实际用的版本）：断面 0 / 630 / 1500 / 4284 × 通道 C0 / C1 / C2
      断面 0 看到 1500 拍，其余看 900 拍
      种子：C0 只跑种子 0；C1 跑种子 0、1（4284 断面只跑种子 0）；C2 跑种子 0（不扰动）、1、2（4284 断面只到 1）
      A082 的 4284 断面从 4285 拍接管（--t0 4285 --h 899，窗末仍是 5184 拍；原因见报告 §3），名字里写 t4285；
          这一局这一窗不计入汇总，所以不跑 C0，另加 C1 种子 1 看离散程度
      另加 C0b（零延迟 + 一拍一条）断面 0 种子 0
  历史重放：H（全按录像）
      只在断面那一拍扰动引擎随机数（噪声底）：断面 0 / 630 / 1500 种子 1
          （4284 断面不跑：这个断面扰动前后的 C2 已经逐拍相同或几乎相同，报告 §8）
      不扰动、到 5184 拍为止（取 4284 断面窗末的历史值；历史基线每 30 拍记一次，5184 拍不在其中）：H-t4284-s0，只跑 A033、A091
          （其余 8 局不扰动的 C2 到 5160 拍每个记录拍都与历史相同，直接取那条 C2 在 5184 拍的值，不必再跑）
  版本对照（另一个历史版本 Va ↔ Vb，原文）：C1 种子 0，断面 0 和断面 1500
      （两个版本在 1500 拍以前走同一段早期逻辑，断面 0 的 11 条已经验证逐拍相同，所以断面 630 不跑）
  延迟敏感性：断面 0，种子 0：C1 的 d 改成 10~18 均匀；d = 0（在途 0 拍，只等到下一个回合边界）
  席位离开敏感性（A061、A062）：不执行录像里我方号的离开，断面 0 / 630 / 1500 × C1、C2，种子 0
  验证用的几条：
      mt-a / mt-b：A089 的两条对照换一个进程重跑（同样的输入是否得到同样的结果）
      mt-bd4285：A079、A082 的 C2 不扰动、从 4285 拍接管（4284 拍落地的指令照录像执行）能否复现历史
      A079 另跑 C1 / C2 从 4285 拍接管（看接管拍对这一局的读数有没有影响）
      A082 另跑 C1 / C2 从 4284 拍接管（说明这一局为什么改从 4285 拍接管、为什么不计入汇总，报告 §6.2 的表）
      -rp：C2 的帧内先后改成随机（--pos rand），与放回历史原位置的同一条相比
用法：python3 102_cp_plan.py [--full] [--games A007,A033] > 清单
      之后用 102b_plan_order.py 排先后（只改先后，不增不减）
"""
import sys

GAMES = ["A007", "A033", "A039", "A053", "A061", "A062", "A070", "A079", "A082", "A089", "A091"]
NATIVE = {g: ("va" if int(g[1:]) <= 17 else "vb") for g in GAMES}
SHIFT = {"A082": 4285}                      # 这一局的 4284 断面实际从哪一拍接管
EXCL_WIN = {4284: ("A082",)}                # 不计入窗口汇总的局（103_cp_table.py 里同名）
HIST_END_5184 = ("A033", "A091")            # 4284 断面窗末的历史值要另跑全录像重放的局
full = "--full" in sys.argv
only = sys.argv[sys.argv.index("--games") + 1].split(",") if "--games" in sys.argv else GAMES


def hor(t0):
    return 1500 if t0 == 0 else 900


def arm(g, ch, t0, s, extra="", sfx=""):
    """一行。4284 断面的局如果在 SHIFT 里，接管拍换成 SHIFT[g]，窗末不变。"""
    t, h = t0, hor(t0)
    if t0 == 4284 and g in SHIFT and ch != "H":
        t, h = SHIFT[g], 4284 + 900 - SHIFT[g]
    return f"{g} {ch}-t{t}-s{s}{sfx} --chan {ch} --t0 {t} --h {h} --seed {s}{extra}"


core, more = [], []
for g in only:
    alt = "vb" if NATIVE[g] == "va" else "va"
    for t0 in (0, 630, 1500, 4284):
        if t0 == 4284 and g == "A070":
            continue        # A070 历史上在 4284 拍前我方已经全灭，这个断面没有可接管的号
        excl = g in EXCL_WIN.get(t0, ())
        # C0
        (more if excl else core).append(arm(g, "C0", t0, 0))
        more += [arm(g, "C0", t0, 1), arm(g, "C0", t0, 2)]
        # C1
        core.append(arm(g, "C1", t0, 0))
        (core if t0 != 4284 or excl else more).append(arm(g, "C1", t0, 1))
        more.append(arm(g, "C1", t0, 2))
        # C2
        core += [arm(g, "C2", t0, 0), arm(g, "C2", t0, 1)]
        (core if t0 != 4284 else more).append(arm(g, "C2", t0, 2))
        # H：只扰动随机数
        (core if t0 != 4284 else more).append(arm(g, "H", t0, 1))
        more.append(arm(g, "H", t0, 2))
        if t0 == 4284:
            (core if g in HIST_END_5184 else more).append(arm(g, "H", t0, 0))
    core.append(arm(g, "C0b", 0, 0))
    more.append(arm(g, "C0b", 630, 0))
    # 版本对照
    core.append(arm(g, "C1", 0, 0, f" --ver {alt}", f"-{alt}"))
    core.append(arm(g, "C1", 1500, 0, f" --ver {alt}", f"-{alt}"))
    more.append(arm(g, "C1", 0, 1, f" --ver {alt}", f"-{alt}"))
    more.append(arm(g, "C1", 1500, 1, f" --ver {alt}", f"-{alt}"))
    for s in (0, 1):
        more.append(arm(g, "C1", 630, s, f" --ver {alt}", f"-{alt}"))
        for t0 in (0, 630, 1500):
            more.append(arm(g, "C2", t0, s, f" --ver {alt}", f"-{alt}"))
    # 延迟敏感性
    core.append(arm(g, "C1", 0, 0, " --dmodel uni --dmin 10 --dmax 18", "-d10_18"))
    core.append(arm(g, "C1", 0, 0, " --dmodel uni --dmin 0 --dmax 0", "-d0_0"))
    more.append(arm(g, "C1", 0, 0, " --dmodel uni --dmin 5 --dmax 12", "-d5_12"))
    more.append(arm(g, "C1", 630, 0, " --dmodel uni --dmin 5 --dmax 12", "-d5_12"))
    more.append(arm(g, "C1", 630, 0, " --dmodel uni --dmin 10 --dmax 18", "-d10_18"))
    # 席位离开
    if g in ("A061", "A062"):
        for t0 in (0, 630, 1500):
            for ch in ("C1", "C2"):
                core.append(arm(g, ch, t0, 0, " --leave none", "-nl"))
# 验证用的几条
extra = [
    "A089 mt-a --chan C1 --t0 0 --h 1500 --seed 1",
    "A089 mt-b --chan C2 --t0 630 --h 900 --seed 0",
    "A079 mt-bd4285 --chan C2 --t0 4285 --h 899 --seed 0",
    "A082 mt-bd4285 --chan C2 --t0 4285 --h 899 --seed 0",
    "A079 C2-t4285-s0 --chan C2 --t0 4285 --h 899 --seed 0",
    "A079 C1-t4285-s0 --chan C1 --t0 4285 --h 899 --seed 0",
    "A082 C1-t4284-s0 --chan C1 --t0 4284 --h 900 --seed 0",
    "A082 C2-t4284-s0 --chan C2 --t0 4284 --h 900 --seed 0",
    "A082 C2-t4284-s1 --chan C2 --t0 4284 --h 900 --seed 1",
    "A070 C2-t1500-s1-rp --chan C2 --t0 1500 --h 900 --seed 1 --pos rand",
    "A082 C2-t4285-s1-rp --chan C2 --t0 4285 --h 899 --seed 1 --pos rand",
]
core += [x for x in extra if x.split()[0] in only]
print("\n".join(core + (more if full else [])))
