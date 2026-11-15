import sys
PATH = "plan/STATUS.md"
text = open(PATH, encoding="utf-8").read()
SWAPS = [
    ("**汇总（s2 c318 更新，11-16 03:15）：共 59 张卡 —— 待领 9，制作中 28，已交付 2，已合并 9，已出图 4，暂过 1，已过审 4，退回 2。**",
     "**汇总（s2 c318 更新，11-16 03:25）：共 59 张卡 —— 待领 9，制作中 28，已交付 2，已合并 9，已出图 3，暂过 1，已过审 4，退回 3。**"),
    ("| brass-oldcopper-small | P1 | 已出图 | m1 c335（接 c194） | bd7f25f9 |",
     "| brass-oldcopper-small | P1 | 退回 | m1 c335（接 c194） | 95e21ea8 |"),
    ("| 11-16 合并（合的是 a2370b00，关口过）；图是 m1 c335 补的（e67687ac，25 张逐像素一致）；交叉看点了 a6 c334，评审 c332 还没评。",
     "| 11-16 合并 bd7f25f9（合的是 a2370b00，关口过）；图是 m1 c335 补的（e67687ac，25 张逐像素一致）；交叉看点了 a6 c334。评审 c332 #8（记录在他分支的 c1e7f104）：退，打磨轮，只退三处：旧铜两种、整格嵌板、吊牌的链；黄铜一族、地面细线、护墙板、两种铭牌定稿，不要再动。旧铜总监定甲（#53871，在“总监定过的 / 11-16”）。"),
    ("- 旧总装封存（0ef4b284：FROZEN.md，README 和 STATUS 顶上各一段）；那个提交在第 2 班的历史上面，谁也不合它（#53059）。",
     "- 旧总装封存（0ef4b284：FROZEN.md，README 和 STATUS 顶上各一段）；那个提交在第 2 班的历史上面，谁也不合它（#53059）。\n"
     "- 旧铜定甲（#53871；review c332 评审 #8 第 1 条，总监看的是总装里 `obs_mat_brass` 的图）：两种方块板面 C1、亮边 C2、暗边和麻点 C0（m1 c335 改）；室外落水管同一级（m3 c342；a6 c334 在 `props/_kit.py` 加 `COPPER_D`）；不加铜绿；palette 的色阶和默认的 `old_copper`（base 2）都不动，公共文件不用改。第 2 班时说的“旧铜带一点绿”就此作废。"),
    ("等评审：brass、panels 打磨轮、facade（review c332），lights（cr2 c333，等新图）。",
     "等评审：panels 打磨轮、facade（review c332），lights（cr2 c333，等新图）。等打磨轮：brass（m1 c335：旧铜两种、整格嵌板、吊牌的链）。"),
]
for old, new in SWAPS:
    n = text.count(old)
    if n != 1:
        sys.exit(f"{n} times, not once: {old[:60]}")
    text = text.replace(old, new)
open(PATH, "w", encoding="utf-8", newline="\n").write(text)
print("ok")
