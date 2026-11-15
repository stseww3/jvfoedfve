# machines/orrery 大行星仪

**目标**：方案 §7.2「大行星仪」、§8 星厅主角；细化稿 `plan/parts/A5-machines.md` §2.3、锚点 §3.2。星厅正中吊装的黄铜太阳系仪，六行星缓慢转。**V7 星厅主角**。
**优先级**：P1（interiors `starhall` 在做、等它做中心主角；A5 牵头先领）。

**约束**
- 坐标走骨架：中心 x=`S.ROOM_X` 中点=7.5、z=`S.STAR_HALL_Z` 中点=0；吊点顶棚 y=`S.STAR_HALL_CEIL`=14；球体 ⌀7 悬于 y≈6–13（占位 x4–11、z−3.5–3.5）。`from scenes.obs.common import skeleton as S`。
- 色板只走 `palette.mat`：臂/环/底盘=`brass`/`brass_dark`；吊座=`brass`+`iron`；日球=`glow`（emit 收小、不炫）；六行星借色板分色分大小（铸铁/铜绿/旧铜/黄铜）。
- 16 像素一格，`px=scale`：整体 ⌀7→`scale=3`；臂/球细件 scale1–2（密度皆 16/格）。
- 发光：仅中心日球一点暖芯 `emit=15,shade=False`、面收小；摆放函数返回建议 light（室内级别低，交 A2/interiors 对齐）。亮区 <1/3。
- 实体预算：本件 ≈20，machines 全图 ≤400；`build()` 返回实体数。

**件清单**（名字 / 尺寸 / 做法）
- `mach_orrery_hub` 吊座齿轮盘 ⌀2：顶棚挂点，brass 齿盘+iron 吊杆（静，接 interiors 吊点）。
- `mach_orrery_sun` 中心日球 ⌀1：glow 暖芯（emit 收小）。
- `mach_orrery_arm_1..6` 六行星臂 各长1.5–3.5：brass 臂(`beam`)+端头行星 `ball`；水星→土星由小到大。各一件、绕中心立轴（**拆件标轴交 A8**，六臂不同速、极缓）。
- `mach_orrery_ring` 黄铜轨道/经线环 ⌀3–7：2–3 道同心 `ring`（甲/乙差异点）。
- `mach_orrery_gearbase` 齿轮底盘 ⌀3：`kit.gear` 叠放（臂下传动，可露齿）。

**交付物**：`build/scenes/obs/machines/orrery.py`（+ `_kit.py` 的 `gear/grad_circle`）；测试场景 `build/scenes/obs_mach_orrery/`（`__init__.py` 调 `orrery.build`、`mood.py` 复用总装光、`shots.json` 远/近/与星厅同框、`props.py` 出陈列）。
**验收**：评审五项，重点「第一眼」（吊在中心一眼是主角）、「风格和逻辑」（黄铜太阳系仪、看得懂六行星绕转、是机械/电气时代、无禁用物）、「质感和像素」（近 3 格黄铜刻度/齿经得住、像素一致）、「明暗光色」（日球微亮不炫、亮区<1/3）。视角：远看吊在厅中、近看齿与行星、与 interiors 星厅同框。
**版本**：**2 版比选**。甲「平面式：六臂共面、机械感、黄铜齿轮外露」；乙「分层/台式：臂分高度呈碗状、外罩黄铜经线环、近浑天仪观感、更华丽」。两版都六行星+缓转，并排拍，评审挑；偏向写记录栏，交付不写。
**依赖**：palette、skeleton（已有）、`_kit.py`（本卡先写 gear/grad_circle）；**interiors** 顶棚吊点与星厅中心留空（锚点 §3.2，已点名 c191；不阻塞，用占位吊点先做模型）；A8 六臂转（供料，不阻塞）。**被依赖**：interiors `starhall`、看板 V7。
**记录**：A5 领（牵头）。默认：中心 (7.5,0)、吊点 y14、球 ⌀7、日球 emit 收小、六臂长 1.5/1.8/2.2/2.6/3.0/3.5、行星色从暗到亮配大小。退回改法逐条记此。
