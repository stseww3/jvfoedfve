# props/electrics-signs 电气和标识

**目标**：方案 §7.3 电气族 + 标识族、§2 台徽、§5.1 立面铭牌/台徽/接线箱；细化稿 §2.4、§2.8。
**优先级**：P1 —— 其中**样板段跨族小件先做**：`sign_nameplate` 搪瓷铭牌、`sign_emblem` 黄铜台徽、`elec_junction_box` 接线箱、`elec_insulator` 瓷瓶电缆（R1 同意进第一批；interiors 星厅也要台徽/铭牌）。其余件 P2。

**约束**
- 电气母题：瓷白 `porcelain`（绝缘子/保险丝，瓷棕不用）+ 铸铁托架 `iron` + 黄铜端子/刀闸 `brass`。
- 标识母题：搪瓷蓝底反白 `enamel`+`cream`，台徽 `brass`，边框/嵌线 `brass`。台徽=圆环+子午竖线+右上星（`Sprite`）。
- 文字只用数字、符号、少量英文（红线）。铭牌用占用表 `oak_sign` 一族方块承载或作模型挂件（与 A1/占用表对齐，默认模型挂件）。
- 16 像素一格；薄片件正面用 `Sprite`，背面贴墙锚点留空气格。

**件清单（电气）**
- `elec_insulator` 瓷瓶 0.5×0.5：`kit.insulator` 叠 `taper` 脊环(porcelain)。
- `elec_crossarm` 横担 2×0.5、`elec_junction_box` 接线箱 1×1、`elec_knife_switch` 闸刀 1×1(slate 底+brass 刀)、`elec_fuse_box` 保险丝盒 1×1、`elec_bell` 电铃 ⌀1(brass)、`elec_wall_phone` 壁挂电话 1×1.5(dark_wood+brass)、`elec_telegraph_key` 电报键 0.5×0.5(brass+木座)。

**件清单（标识）**
- `sign_emblem` 台徽牌 1×1：brass 圆 `ring`+子午竖+星 `Sprite`。檐下/门楣。
- `sign_nameplate` 搪瓷铭牌 1.5×0.5：enamel 底+cream 字 `Sprite`+brass 边。门边。
- `sign_number` 编号牌 0.5×0.5、`sign_fingerpost` 指路牌 2×2(改自 skyobs `signpost`)、`sign_flag` 旗 1×1.5(cream_cloth+台徽，飘=动画/插值由 A8)、`sign_meridian_marker` 子午线嵌牌 1×0.5 落地(brass)。

**交付物**：`build/scenes/obs/props/electrics.py`、`signs.py`（+`kit.py`：`insulator`）；测试场景 `build/scenes/obs_props_elecsign/`。
**验收**：「风格和逻辑」（瓷瓶/刀闸看得懂、台徽统一、文字合规）、「质感和像素」（铭牌字清晰、近看经得住）。视角：近看台徽+铭牌、接线箱+瓷瓶电缆挂墙、远看一排编号牌。
**版本**：1 版。
**依赖**：palette；占用表 `oak_sign`（铭牌承载，默认模型挂件，待 A1/占用表确认）。**被依赖**：main 样板段、interiors、site 子午线。
**记录**：默认铭牌作模型挂件；台徽为全场通用符号，先在此定稿供各族复用。退回改法记此。
