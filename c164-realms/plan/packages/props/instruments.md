# props/instruments 小仪器

**目标**：方案 §7.3 小仪器族；细化稿 §2.5。统一「黄铜刻度环 + 滚花旋钮 + 木/铁底座」，荧光绿/琥珀只上表盘。
**优先级**：P2（室内铺开时要；精密钟的摆供 A8；interiors 后续各间点名地球仪/天球仪/电报键等——电报键在 electrics 卡）。

**约束**
- 色板：仪器主体 `brass`/`brass_dark`，底座 `dark_wood`/`iron`/`ashlar`(石墩)；表盘 `cream`/`porcelain`+`phosphor` 夜光；透镜用 `night_glass` 或 brass_dark 端面。
- 16 像素一格，`px=scale`。可动件（精密钟摆）拆件、标轴交 A8（本卡出静壳+摆件两件）。

**件清单**
- `inst_tripod_scope` 三脚架望远镜 1×2 落地：改自 skyobs `spyglass`。落日平台/观景台。
- `inst_sextant` 六分仪 1×1、`inst_globe` 地球仪 ⌀1(brass 子午环+verdigris 球)、`inst_celestial_globe` 天球仪 ⌀1.5(星点 `Sprite`)、`inst_barometer` 气压计 1×2 墙、`inst_louvre_box` 百叶箱 1×1×2 落地(`kit.louvre`，ashlar/cream，气象站)、`inst_regulator_clock` 精密钟 1×2 落地/墙（**可动**：木长壳+玻罩+钟摆拆件交 A8+表盘 `Sprite`）、`inst_calc_machine` 手摇计算机 1×1(iron+brass+侧摇 `kit.handwheel`)。

**交付物**：`build/scenes/obs/props/instruments.py`；测试场景 `build/scenes/obs_props_instruments/`。
**验收**：「风格和逻辑」（黄铜刻度看得懂、成族像一套）、「质感和像素」（刻度环近看经得住）。视角：近看每件、和家具并排（室内尺度）、精密钟摆拆件示意。
**版本**：1 版。
**依赖**：palette、`kit.py`（`handwheel/louvre/insulator` 复用）；A8 动画接口（摆件轴，供料不阻塞）。**被依赖**：interiors 星图室/授时室、site 气象站。
**记录**：精密钟摆轴与 A8 对接；默认底座木料 dark_wood。退回改法记此。
