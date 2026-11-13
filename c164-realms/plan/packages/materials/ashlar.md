# materials/ashlar

## 目标
方案 6.2 灰白石四种 + R1 §2 石材重写：用 `redirect_block` 把砂岩族改成灰白石（粗琢面/细琢面/凹板/台徽块），不换同名贴图。

## 约束
- 角色 `B.ASHLAR_ROUGH`(sandstone+stairs/slab/wall)、`B.ASHLAR_FINE`(smooth_sandstone+stairs/slab)、`B.ASHLAR_PANEL`(cut_sandstone+slab)、`B.ASHLAR_EMBLEM`(chiseled_sandstone)。
- 贴图映射（见 materials.md §3 表）：rough 侧/顶/底分开；fine **立面 `ashlar_fine`、上下面 `ashlar_fine_top`**（踏面和压顶上不许有砖缝：c190 预评第 1 条；工具按面映射，`{"side": ..., "end": ...}`）；panel 侧 panel、端 fine_top；emblem 侧 emblem、端 fine_top；rough 的矮墙顶面用 `ashlar_rough_top`。
- `mat("ashlar")`，色阶 A0–A5；16px；`strays()` 每张过。像素规则见 materials.md §3（rough 四边 1px 缝→拼成 2px；fine 两层 8px 通缝 1px、竖缝错半格；panel 下沉板；emblem 台徽浮雕）。
- 变体覆盖楼梯/台阶/墙，不只整块。
- 粗琢面 2px 缝和细琢面 1px 缝并排时要读成“同一种石头的两种加工”，不是两种石头（c190 预评第 2 条）：两者用同一段色阶、同一个基准明度，交界处由腰线（main 的线脚）盖住；样板上必须有一段“下粗上细、中间一道腰线”的墙来确认。

## 交付物
- `build/scenes/obs/materials/ashlar.py`：贴图生成 + `_kit.paint()` / `_kit.redirect()`；模块里写 `BLOCKS = K.blocks(B.ASHLAR_ROUGH, B.ASHLAR_FINE, B.ASHLAR_PANEL, B.ASHLAR_EMBLEM)`，这四族就退出占位。比选写成 `pack(pack_dir, version="a")`。
- 测试场景 `build/scenes/obs_mat_ashlar/`（零件用 `materials/_board.py`）：四种各一面 8×8 墙 + 楼梯/台阶/（rough 的）墙样例 + 一段下粗上细带腰线的墙 + 一跑细琢石台阶（从上往下看踏面）；`shots.json`：正交近看（缝/凿痕）+ 20 格远看（认得出）+ 四种并排 + 踏面俯看。

## 验收
- 20 格外认得出；8×8 平铺不起条纹；颜色全在色阶（`strays` 空）；楼梯台阶墙贴图一致；踏面没有砖缝；粗细两种并排读成一种石头。
- `tools/check.py --scene obs_mat_ashlar` 全过。
- 比选并排：甲/乙/丙三版（见版本），含"原版砂岩直接用"对照。

## 版本
3 版比选（不同想法，不是调参）：甲 自绘粗/细琢面（本稿规则）；乙 另一种石缝节奏/凿面质感；丙 原版砂岩直接用（石材退路对照，R1 要并排给管理员挑）。

## 依赖
- 依赖：respack-redirect。
- 被依赖：main（立面）、site、interiors 的石材外观。

## 记录
- （领卡后填）
- 备忘：三版比选每一版是一整套图，不能同时进一个资源包；测试场景按版本各出一组图（`shots` 一样，`write_pack` 的版本不同），图名带版本。
