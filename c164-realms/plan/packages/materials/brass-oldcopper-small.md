# materials/brass-oldcopper-small

## 目标
方案 6.2 第二批：黄铜（bamboo 族）、旧铜（waxed_exposed）、小件（护墙板/黄铜嵌线/搪瓷铭牌）+ 脚步声改金属。

## 约束
- 黄铜 `BRASS_*`（bamboo 族）：`mat("brass")`/`brass_dark`/`brass_flat`，色阶 R0–R5。板/花纹板/粗管/栏杆/玻璃铜门(brass 框+opal 芯)/活板门/按钮/铭牌/架子。重定向（和 vanilla 竹子分家：竹子我们不用，可直接改，但为稳妥仍走 redirect 并自查）。
- 旧铜 `OLD_COPPER`=waxed_exposed_copper、`OLD_COPPER_CUT`=waxed_exposed_cut_copper(+stairs/slab)：`mat("old_copper")`，色阶重画。**只改 waxed_exposed_\***，不碰 `waxed_oxidized_*`/`waxed_weathered_*`。重画前檐沟用原版色占位（R1 §0.2）。
- 小件：`WAINSCOT`=dark_oak_trapdoor（`dark_wood` 护墙板，A7 不当活板门）、`BRASS_INLAY`=yellow_carpet（地面黄铜子午嵌线）、`ENAMEL_SIGN`=oak_sign 族（`enamel`+`cream` 搪瓷铭牌；文字只数字/符号/少量英文）。
- 脚步声（做法 E）：`K.sounds(pack_dir, {"block.bamboo_wood.step": [...], ...})`，写进 `assets/minecraft/sounds.json`（`"replace": true`），把 `block.bamboo_wood.*` 指到 `block/copper/step*`、`break*`，子块同理。只引用原版音频，无 .ogg。
- 注意：`bamboo_shelf` 的图是 32×32 的大图（`paint()` 允许 16 的整数倍见方）；铜灯的图是 16×48 的动画；告示牌在 26.3 里是普通方块模型，和别的方块一样重定向。
- `strays()` 每张过。

## 交付物
- `build/scenes/obs/materials/brass_oldcopper_small.py`（模块名 = 卡名，`-` 写成 `_`；内部分三段：黄铜、旧铜、小件）；`BLOCKS = K.blocks(...)`。
- 测试场景 `build/scenes/obs_mat_brass/`（零件用 `materials/_board.py` 的 `brass`、`twins_plates`；含旧铜并排未上蜡 exposed 铜证明只改 `waxed_exposed_*`、小件样例）；`shots.json`：近看黄铜/旧铜/小件、旧铜分家并排。

## 验收
- 黄铜像一套；旧铜和模型旧铜色阶接得上、只改 `waxed_exposed_*`（并排的未上蜡 exposed、`waxed_weathered_*` 不变）；小件到位；脚步金属声、无外来音频；颜色全在色阶。
- `tools/check.py --scene obs_mat_brass` 全过。

## 版本
1 版。

## 依赖
- 依赖：respack-redirect；旧铜与 A6 模型旧铜色阶对齐（檐沟方块↔雨水管模型）。
- 被依赖：main（檐沟/铭牌/黄铜件）、props、interiors。

## 记录
- （领卡后填）
