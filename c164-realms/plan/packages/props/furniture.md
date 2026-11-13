# props/furniture 家具

**目标**：方案 §7.3 家具族；细化稿 §2.6。统一「深色木面 + 铸铁腿脚 + 黄铜拉手/包角」。
**优先级**：P2，但 **`furn_bench` 长椅先做**（R1-6；site 落日平台、缆车站与 interiors 星厅已点名）。

**约束**
- 色板：木面/框 `dark_wood`，腿脚 `iron`，五金 `brass`；行李箱帆布 `cream_cloth`、皮带 `dark_wood`。
- 16 像素一格，`px=scale`。多落地，锚点在脚下空气格。

**件清单**
- `furn_bench` 长椅 2×0.5×1 **（R1 新增，先做）**：木条座靠+铸铁弯腿(`hose`)。
- `furn_writing_desk` 写字台 2×1×1、`furn_drafting_table` 制图桌 2×1.5(斜面)、`furn_swivel_chair` 转椅 1×1、`furn_stool` 高凳 0.5×1.5、`furn_card_cabinet` 卡片柜 1×1×2(一排黄铜拉手)、`furn_library_ladder` 书架梯 0.5×3、`furn_coat_stand` 衣帽架 1×2、`furn_trunk` 行李箱 1.5×1(改自 skyobs `trunk`)、`furn_crate` 木箱 1×1(改自 skyobs `crate`)。

**交付物**：`build/scenes/obs/props/furniture.py`；测试场景 `build/scenes/obs_props_furniture/`。
**验收**：「风格和逻辑」（木+铁+黄铜成族）、「质感和像素」（木纹/铁腿近看经得住）。视角：近看每件、成组摆（室内一角）、和仪器并排看尺度。
**版本**：1 版。
**依赖**：palette、`kit.py`；室内尺度/摆位（interiors 对清单，不阻塞）。**被依赖**：interiors 各间、site 平台。
**记录**：先交 `furn_bench` 供 site/interiors；默认腿脚 iron 弯脚。退回改法记此。
