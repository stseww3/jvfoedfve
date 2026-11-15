import sys
PATH = "plan/STATUS.md"
text = open(PATH, encoding="utf-8").read()
SWAPS = [
    ("**汇总（s2 c318 更新，11-16 03:25）：共 59 张卡 —— 待领 9，制作中 28，已交付 2，已合并 9，已出图 3，暂过 1，已过审 4，退回 3。**",
     "**汇总（s2 c318 更新，11-16 03:30）：共 59 张卡 —— 待领 9，制作中 28，已交付 2，已合并 9，已出图 2，暂过 2，已过审 4，退回 3。**"),
    ("`materials/panels` 打磨轮 a52bd566。总装头 42d7ef66（11-16 03:06）：21 个场景 check.py 0 失败。",
     "`materials/panels` 打磨轮 a52bd566；`sky/lights` 在入口 B 下重出的图 5ba3b4b6。总装头 3c0f8e17（11-16 03:27）：21 个场景 check.py 0 失败。"),
    ("25 张图 1a530b6b（lights c331 补的）；交叉看 facade c321 过。",
     "25 张图 1a530b6b（lights c331 补的）；交叉看 facade c321 过。立面换了入口以后 25 张全部重出，5ba3b4b6（合的是 a09556c5）。"),
    ("| facade | P1 | 已出图 | facade c321（接 c206） | 534dc9b6 |", "| facade | P1 | 暂过 | facade c321（接 c206） | 534dc9b6 |"),
    ("交叉看点了 a4 c323，评审 c332 还没评。",
     "交叉看 a4 c323 过（#54072：前庭的条带 z ±6、±26 落在壁柱线上，三条道和门廊前的平台对上入口 B 的三个拱；勒脚和铺地同料同调；V1 里东缘栅杆罩住基座层是 site 这边的事，等图），评审 c332 还没评。"),
    ("（25 张，离线图，node45 出，关口核过；立面换了入口以后 20 张过期，在重出）", "（25 张，离线图，node45 出，入口 B 下重出的，关口核过）"),
    ("评审 cr2 c333 等新图。洗墙轮另交。",
     "立面换了入口以后 25 张全部重出（合的是 a09556c5，合并提交 5ba3b4b6；`blue_door`、`deep_door` 挪到了正对中拱），评审 cr2 c333 还没评。洗墙轮另交。"),
    ("| `obs_sky_lights` | 25 | 5 张对；20 张过期，立面换了入口：`blue_` 八张、`deep_` 七张、`glow_front`、`glow_axis`、`glow_v1`、`glow_slant`、`glow_surround` | lights c331，已点（#53332：`blue_door`、`deep_door` 建议挪到正对中拱） |",
     "| `obs_sky_lights` | 25 | 都对：42d7ef66 上有 20 张过期（立面换了入口），lights c331 全部重出，5ba3b4b6 进总装，关口核过 | — |"),
    ("- 等重新【交付】：`main/shell`（shell c325）、`sky/comet`（comet c330）。等补图：`sky/lights` 过期的 20 张（lights c331）。",
     "- 等重新【交付】：`main/shell`（shell c325）、`sky/comet`（comet c330）。"),
    ("- 等交叉看：`materials/brass-oldcopper-small`（a6 c334）、`main/facade`（a4 c323）、`materials/panels` 打磨轮（m3 c342）。等评审：panels 打磨轮、facade（review c332），lights（cr2 c333，等新图）。",
     "- 等交叉看：`materials/brass-oldcopper-small`（a6 c334）、`materials/panels` 打磨轮（m3 c342）。等评审：panels 打磨轮、facade（review c332），lights（cr2 c333）。"),
]
for old, new in SWAPS:
    n = text.count(old)
    if n != 1:
        sys.exit(f"{n} times, not once: {old[:60]}")
    text = text.replace(old, new)
open(PATH, "w", encoding="utf-8", newline="\n").write(text)
print("ok")
