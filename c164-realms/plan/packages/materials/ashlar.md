# materials/ashlar

## 目标
方案 6.2 灰白石四种 + R1 §2 石材重写：用 `redirect_block` 把砂岩族改成灰白石（粗琢面/细琢面/凹板/台徽块），不换同名贴图。

## 约束
- 角色 `B.ASHLAR_ROUGH`(sandstone+stairs/slab/wall)、`B.ASHLAR_FINE`(smooth_sandstone+stairs/slab)、`B.ASHLAR_PANEL`(cut_sandstone+slab)、`B.ASHLAR_EMBLEM`(chiseled_sandstone)。
- 贴图映射（见 materials.md §3 表）：rough 侧/顶/底分开；fine 全面统一；panel 侧 panel、端 fine_top；emblem 侧 emblem、端 fine_top。
- `mat("ashlar")`，色阶 A0–A5；16px；`strays()` 每张过。像素规则见 materials.md §3（rough 四边 1px 缝→拼成 2px；fine 两层 8px 通缝 1px、竖缝错半格；panel 下沉板；emblem 台徽浮雕）。
- 变体覆盖楼梯/台阶/墙，不只整块。

## 交付物
- `build/scenes/obs/materials/ashlar.py`：贴图生成 + 调 `redirect_block`。
- 测试场景 `build/scenes/obs_mat_ashlar/`：四种各一面 8×8 墙 + 楼梯/台阶/（rough 的）墙样例；`shots.json`：正交近看（缝/凿痕）+ 20 格远看（认得出）+ 四种并排。

## 验收
- 20 格外认得出；8×8 平铺不起条纹；颜色全在色阶（`strays` 空）；楼梯台阶墙贴图一致。
- 比选并排：甲/乙/丙三版（见版本），含"原版砂岩直接用"对照。

## 版本
3 版比选（不同想法，不是调参）：甲 自绘粗/细琢面（本稿规则）；乙 另一种石缝节奏/凿面质感；丙 原版砂岩直接用（石材退路对照，R1 要并排给管理员挑）。

## 依赖
- 依赖：respack-redirect。
- 被依赖：main（立面）、site、interiors 的石材外观。

## 记录
- （领卡后填）
