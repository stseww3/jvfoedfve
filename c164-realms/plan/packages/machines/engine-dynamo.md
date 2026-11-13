# machines/engine-dynamo 蒸汽机和发电机

**目标**：方案 §7.2「蒸汽机和发电机」、§5.3/§8 发电房；细化稿 §2.5。卧式蒸汽机大飞轮、皮带、发电机、调速飞球都在转。**V6 发电房外（透窗）+ 发电房内室**。
**优先级**：P2（依赖 A4 发电房外壳、A6 管件；可盒子占位先做机组）。

**约束**
- 坐标：`S.POWER_HOUSE` box=(67,20,89,42)、墙高 10、烟囱 30；机组落地在房内铁底板。
- 色板：飞轮/汽缸/机座 `iron`/`iron_flat`；汽缸盖/铭牌 `brass`；发电机绕组 `old_copper`+瓷端子 `porcelain`；调速飞球点 `signal`；皮带 `dark_wood`（走动用动画贴图，A1）。
- 16 像素一格，`px=scale`：飞轮 ⌀5→scale2、机体 scale2、小件 scale1。
- 发光：无（火光在 `boiler` 卡）；发电机指示小灯可选（三级，返回 light）。
- 实体预算：本件 ≈50；`build()` 返回实体数。

**件清单**：`mach_engine_flywheel` 大飞轮 ⌀5（`kit.flywheel`，**主视觉动点、拆件标主轴交 A8**）；`mach_engine_cylinder` 汽缸+活塞+十字头；`mach_engine_rod` 曲柄连杆（**随飞轮动**）；`mach_engine_governor` 调速飞球（`kit.governor`，**转**）；`mach_engine_belt` 皮带（`between` 扁带，纹走动画贴图不占实体）；`mach_engine_dynamo` 发电机机座+磁极+电枢飞轮（**随皮带转**）；`mach_engine_base` 共用铁底板。进汽口/出线留接口给 A6 管件。
**交付物**：`build/scenes/obs/machines/engine.py`（+ `_kit.py` 的 `flywheel/governor`）；测试场景 `build/scenes/obs_mach_engine_dynamo/`（盒子发电房占位；`shots.json` 机组全貌、飞轮/连杆近景、透窗 V6 角度）。
**验收**：五项，重点「风格逻辑」（看得懂蒸汽机驱动发电机、皮带连飞轮与电枢、管线有来去、是电气时代）、「质感像素」（飞轮辐/铆钉近看、像素一致）。视角：机组全貌、飞轮连杆近景、透拱窗（接 V6）。
**版本**：1 版（机组一套；飞轮是比选焦点可留档不并卡）。
**依赖**：skeleton、palette；**A4** 发电房外壳/拱窗位（可占位）、**A6** 蒸汽/暖气管+红手轮阀（留接口）、**A1** 皮带纹动画贴图；A8 飞轮/连杆/飞球/电枢（供料）。**被依赖**：`switchboard-boiler`（同房）、interiors `powerhouse`、看板 V6。
**记录**：A5 领（牵头）。默认：卧式单缸、飞轮 ⌀5 在东、发电机皮带相连、调速飞球立于机侧。退回改法逐条记此。
