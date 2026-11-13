# materials/panels

## 目标
方案 6.2 仪表面板十六种（5.3/8 授时室仪表墙）：重定向带釉陶瓦，正面显仪表、facing 控朝向，4 种带动画。

## 约束
- 角色 `B.PANELS[...]`（16 种 glazed terracotta，无 waxed 问题）。重定向每块 blockstate → `c164:` 模型：**只在 facing 那一面**放仪表贴图（直立），其余五面 `mat("iron")` 机壳；用 vanilla facing 的 y 旋转把正面对房间，去掉原版拼花旋转。做法已在占位里跑通：`K.redirect(pack_dir, 方块, {原版图: {"south": "panel_xxx", "*": "panel_case"}}, edit=upright)`——模型自己的 `south` 面就是 `facing` 那一面，`upright` 去掉面上的 `rotation`（见 `_standin.py`）。
- 十六种摆成一面墙容易变成一片闪烁的花（c190 预评第 5 条）：按明暗分三级（暗底的占多数，白瓷面的少数，发光的最多 4 种），动画只有本卡列的 4 种且节奏慢，绿和红只做零星的指示灯；在一整面墙上确认，不只看单块。
- 取色：黑刻度/字=`colour("iron",0)`，白瓷=`porcelain`，示波/辉光=`phosphor`/`glow`，警示=`signal`，搪瓷=`enamel`+`cream`。`strays()` 每张过。
- 动画（做法 D，`.mcmeta` 纵向堆帧）：`tubes` 辉光脉动、`scope` 波形扫动、`counter` 个位跳字、`pilot_lamps` 轮流闪；`recorder` 可选。帧率/节奏与 A8 对齐。
- 清单与画什么见 materials.md §6 / `blocks.py` 注释。

## 交付物
- `build/scenes/obs/materials/panels.py`：16 贴图（4 带动画帧，`K.paint(..., meta={"animation": {...}})`）+ 重定向；`BLOCKS = K.blocks(*B.PANELS.values())`。
- 测试场景 `build/scenes/obs_mat_panels/`：16 块码成一面仪表墙（按授时室的排法，约 8×4，重复摆满）+ 单块陈列（四个朝向）；`shots.json`：正面近看每种、整墙远看、侧看（机壳）、动画面板（真机看动）。

## 验收
- 每种正面直立可读、facing 可控；动画四种在动；颜色全在色阶；成排像一套；整面墙不花不闪。
- `tools/check.py --scene obs_mat_panels` 全过。

## 版本
1 版。

## 依赖
- 依赖：respack-redirect；A8（动画节奏）。
- 被依赖：interiors（授时室仪表墙 V10）、main。

## 记录
- （领卡后填）
