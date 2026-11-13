# props/paper 纸品

**目标**：方案 §7.3 纸品族；细化稿 §2.7。统一「米白纸面 + 台徽/星图抬头 + 卷边/图钉」，蓝图用搪瓷蓝反白。
**优先级**：P2，但 **`paper_star_chart` 星图先做**（interiors 星厅已点名）。

**约束**
- 色板：纸面 `cream`，蓝图/星图底 `enamel`+`cream` 反白，黑板 `slate`+`cream`+`dark_wood` 框，底片玻璃+`glow`（灯台发光）。
- 多为薄片，正面 `Sprite`；挂墙锚点留空气格。文字只用数字/符号/少量英文。

**件清单**
- `paper_star_chart` 星图 2×1 墙 **（先做）**：enamel 底+cream 星点 `Sprite`+brass 框。
- `paper_blueprint` 蓝图 1.5×1、`paper_logbook` 记录本 0.5×0.5、`paper_photo_plate` 照相底片 0.5×0.5(发光灯台上)、`paper_blackboard` 黑板 2×1.5(slate+cream 粉笔轨道草图+dark_wood 框)、`paper_moon_map` 月面图 1.5×1.5。

**交付物**：`build/scenes/obs/props/paper.py`；测试场景 `build/scenes/obs_props_paper/`。
**验收**：「风格和逻辑」（纸品成族、抬头统一、文字合规）、「第一眼/质感」（星图/蓝图图案清晰）。视角：近看每件、挂墙成组、和家具（桌面）并排。
**版本**：1 版。
**依赖**：palette；台徽 `Sprite`（复用 electrics-signs 的台徽）。**被依赖**：interiors 星图室/星厅。
**记录**：先交 `paper_star_chart`；台徽/星图抬头与 signs 卡共用一套 `Sprite`。退回改法记此。
