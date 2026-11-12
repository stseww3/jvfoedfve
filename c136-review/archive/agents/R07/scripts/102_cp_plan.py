#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""102_cp_plan.py — R07：生成断面对照的运行清单（每行：局 名字 100_checkpoint.mjs 的参数）。

  主网格（历史上这一局实际用的版本）：断面 0 / 630 / 1500 / 4284 × 通道 C0 / C1 / C2 × 种子 0、1、2
      断面 0 看到 1500 拍，其余看 900 拍；另加 C0b（零延迟 + 一拍一条）种子 0
  噪声底：H（全按录像）在同一断面只扰动引擎随机数，种子 1、2
  版本对照（另一个历史版本 Va ↔ Vb，原文）：断面 0 / 630 / 1500 × C1、C2 × 种子 0、1
  延迟敏感性：C1 的 d 改成 5~12 均匀、10~18 均匀，断面 0 / 630，种子 0
  席位离开敏感性（A061、A062）：不执行录像里我方号的离开，断面 0 / 630 / 1500 × C1、C2，种子 0
用法：python3 102_cp_plan.py [--set main|noise|ver|delay|leave|all] > 清单
"""
import sys

GAMES = ["A007", "A033", "A039", "A053", "A061", "A062", "A070", "A079", "A082", "A089", "A091"]
NATIVE = {g: ("va" if int(g[1:]) <= 17 else "vb") for g in GAMES}
which = sys.argv[sys.argv.index("--set") + 1] if "--set" in sys.argv else "all"
only = sys.argv[sys.argv.index("--games") + 1].split(",") if "--games" in sys.argv else GAMES


def hor(t0):
    return 1500 if t0 == 0 else 900


out = []
for g in only:
    if which in ("main", "all"):
        for t0 in (0, 630, 1500, 4284):
            for ch in ("C0", "C1", "C2"):
                for s in (0, 1, 2):
                    out.append(f"{g} {ch}-t{t0}-s{s} --chan {ch} --t0 {t0} --h {hor(t0)} --seed {s}")
        out.append(f"{g} C0b-t0-s0 --chan C0b --t0 0 --h 1500 --seed 0")
        out.append(f"{g} C0b-t630-s0 --chan C0b --t0 630 --h 900 --seed 0")
    if which in ("noise", "all"):
        for t0 in (0, 630, 1500, 4284):
            for s in (1, 2):
                out.append(f"{g} H-t{t0}-s{s} --chan H --t0 {t0} --h {hor(t0)} --seed {s}")
    if which in ("ver", "all"):
        alt = "vb" if NATIVE[g] == "va" else "va"
        for t0 in (0, 630, 1500):
            for ch in ("C1", "C2"):
                for s in (0, 1):
                    out.append(f"{g} {ch}-t{t0}-s{s}-{alt} --chan {ch} --t0 {t0} --h {hor(t0)} --seed {s} --ver {alt}")
    if which in ("delay", "all"):
        for t0 in (0, 630):
            out.append(f"{g} C1-t{t0}-s0-d5_12 --chan C1 --t0 {t0} --h {hor(t0)} --seed 0 --dmodel uni --dmin 5 --dmax 12")
            out.append(f"{g} C1-t{t0}-s0-d10_18 --chan C1 --t0 {t0} --h {hor(t0)} --seed 0 --dmodel uni --dmin 10 --dmax 18")
    if which in ("leave", "all") and g in ("A061", "A062"):
        for t0 in (0, 630, 1500):
            for ch in ("C1", "C2"):
                out.append(f"{g} {ch}-t{t0}-s0-nl --chan {ch} --t0 {t0} --h {hor(t0)} --seed 0 --leave none")
print("\n".join(out))
