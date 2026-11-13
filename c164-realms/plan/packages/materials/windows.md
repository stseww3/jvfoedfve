# materials/windows

## 目标
方案 6.2 亮窗/暗窗 + 6.3 发光：六种窗（亮三、暗三），块+板两形状，窗棂在贴图里画。

## 约束
- 角色 `B.WINDOW_LIT`(黄)、`B.WINDOW_CURTAIN`(橙)、`B.WINDOW_FROSTED`(白) = 亮窗；`B.WINDOW_DARK`(灰)、`B.WINDOW_BLIND`(黑)、`B.SKYLIGHT`(浅灰) = 暗窗/天窗。各含 `.block`(整块玻璃) 与 `.pane`(玻璃板)。
- 亮窗：`glow`/`opal`（白=`opal`），自发光 = 重定向块+板模型加 `light_emission≈10`，保留 `force_translucent`（做法 C）。暗窗：`night_glass`，不发光，映天色斜向冷反光。
- 窗棂：贴图内 8px 一格、1px `colour("iron",1)`，四边无缝拼成网；3 格宽拱窗横显 6 列。
- 玻璃板：重定向 post/side/side_alt/noside/noside_alt 五模型；面贴图=`*_stained_glass`、边贴图=`*_stained_glass_pane_top`。
- A6 模型窗框只做拱头/外框/中横档，压在窗棂线上，不另起网格（windows 卡与 A6 对齐）。
- `strays()` 每张过。

## 交付物
- `build/scenes/obs/materials/windows.py`：贴图 + 发光模型重定向。
- 测试场景 `build/scenes/obs_mat_windows/`：亮三+暗三各一面整块玻璃墙 + 一处玻璃板窗；后面留位给 A2 隐形光源；`shots.json`：全黑环境看自发光、暗窗看映天、近看窗棂、远看亮暗分布。

## 验收
- 亮窗自发光且颜色对（全黑离线图）；暗窗映天色不发光；窗棂拼成连续网格；亮区不铺满（配合 A2）。
- 亮窗 2 版比选并排。

## 版本
亮窗 2 版（甲 暖黄为主 + 橙帘影 + 白磨砂三件套按本稿；乙 另一种窗棂密度/发光节奏/帘影处理）。暗窗 1 版。

## 依赖
- 依赖：respack-redirect；A2（隐形光源摆放、定稿光）。
- 被依赖：main（立面大拱窗）、interiors、A6（窗框模型）。

## 记录
- （领卡后填）
