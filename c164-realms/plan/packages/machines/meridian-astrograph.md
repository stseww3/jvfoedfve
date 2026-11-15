# machines/meridian-astrograph 子午环和天体照相仪

**目标**：方案 §7.2「子午环、天体照相仪」；细化稿 §2.9。子午仪小屋的子午环（只在子午面俯仰）、小穹顶的天体照相仪。**子午仪小屋近景、小穹顶（V11 侧面可带）**。
**优先级**：P2（次要视角；依赖 A4 子午仪小屋、A3 小穹顶；可占位）。

**约束**
- 坐标：子午环在 `S.MERIDIAN_HUT` centre=(35,-30)（顶南北缝）；天体照相仪在 `S.SMALL_DOME_*`（南端亭上、顶点 `S.SMALL_DOME_APEX`=25）。
- 色板：筒 `iron`+`brass`；大刻度环 `brass`；石墩包 `iron`；照相机背 `dark_wood`+`brass`。
- 16 像素一格，`px=scale`：子午环筒 ⌀0.8×4→scale2、照相仪筒 ⌀1.2×6→scale2、刻度环 scale1。
- 发光：无（夜观暗）；读数显微镜旁小灯可选（三级，返回 light）。
- 实体预算：本件 ≈25；`build()` 返回实体数。

**件清单**：`mach_meridian_tube` 子午环望远镜 ⌀0.8×4（**只在南北子午面俯仰、东西向水平轴，拆件交 A8**）；`mach_meridian_circle` 子午大刻度环 ⌀3（竖直，读天顶距）+读数显微镜；`mach_meridian_pier` 东西两石墩包（夹轴，配小屋南北缝）；`mach_astro_tube` 天体照相仪筒 ⌀1.2×6（比大折射镜短粗，`riveted_tube`，**跟踪交 A8**）；`mach_astro_back` 照相机背/底片盒；`mach_astro_mount` 赤道仪小架。
**交付物**：`build/scenes/obs/machines/meridian.py`、`astro.py`（+ `_kit.py` 的 `riveted_tube/grad_circle`）；测试场景 `build/scenes/obs_mach_meridian_astrograph/`（小屋/小穹顶占位 + 缝；`shots.json` 子午环近景、照相仪、各自开缝对位）。
**验收**：五项，重点「风格逻辑」（看得懂子午环只南北摆、照相仪在拍、黄铜刻度环、是电气时代天文仪器）、「质感像素」（刻度环/筒近看、与大折射镜成一套）。视角：子午环近景、照相仪近景、各开缝对位。
**版本**：1 版（两件成一套，像素/黄铜母题与 `refractor` 对齐）。
**依赖**：skeleton、palette、`refractor`（黄铜/铆钉母题对齐）；**A4** 子午仪小屋、**A3** 小穹顶（可占位）；A8 俯仰/跟踪（供料）。**被依赖**：看板 V11 侧带。
**记录**：A5 领（牵头）。默认：子午环东西轴、小屋南北缝对位；照相仪在小穹顶朝缝。退回改法逐条记此。
