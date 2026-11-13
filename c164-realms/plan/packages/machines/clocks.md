# machines/clocks 母钟 / 塔钟 / 报时球

**目标**：方案 §7.2「母钟和塔钟」、§5.3 报时塔；细化稿 §2.4、锚点 §3.3。星厅落地母钟、报时塔钟面走针、塔顶报时球整点落下。**V7 母钟、V5 塔钟/报时球**。
**优先级**：P2（母钟入星厅锚点已在细化稿对给 interiors；塔钟/报时球依赖 A3 报时塔外壳）。

**约束**
- 坐标：母钟在星厅（锚点 §3.3，位由 interiors 定）；塔钟/报时球走 `S.CLOCK_SHAFT_X/Z`、`S.CLOCK_SHAFT_TOP`=31、`S.CLOCK_TOP`=41、`S.CLOCK_BALL_MAST`=52（面朝东）。
- 色板：母钟 `dark_wood` 壳+`brass` 饰+玻璃罩；塔钟 `brass` 圈+`cream` 面；指针 `iron_dark`；报时球 `brass`（或 `verdigris`）。表盘数字只用数字/罗马数字符号（红线）。
- 16 像素一格，`px=scale`：母钟 scale2、塔钟面 scale1（大圈分段）、报时球 scale1。
- 发光：塔钟面夜间暖光底（`glow` 收小）、母钟表盘微亮；摆放函数返回 light（塔钟二级、母钟三级）。
- 实体预算：本件 ≈40；`build()` 返回实体数。

**件清单**：`mach_clock_master` 母钟机身 1.5×1×4（玻璃罩见机芯）+ `mach_clock_pendulum` 钟摆（**拆件交 A8**，顶部水平摆轴，1 秒级）；`mach_clock_face` 塔钟面 ⌀3 + `mach_clock_hand_h/_m` 时/分针（**拆件交 A8**，绕面法向，分针可见走）；`mach_clock_ball` 报时球 ⌀1.5（**拆件交 A8**，沿杆竖直落下复位）+ `mach_clock_mast` 球杆；`mach_clock_anemo` 塔顶风速计+避雷针（风杯慢转）。
**交付物**：`build/scenes/obs/machines/clock.py`（+ `_kit.py` 的 `clock_face/pendulum`）；测试场景 `build/scenes/obs_mach_clocks/`（母钟盒子 + 塔段占位；`shots.json` 母钟近景、塔自下而上）。
**验收**：五项，重点「风格逻辑」（看得懂报时：钟在走、球会落、母钟是精密摆钟）、「质感像素」（钟面刻度/罗马数字近看经得住）、「轮廓」（塔上一竖的钟面+报时球）。视角：母钟近景（V7 带）、报时塔自下而上（V5）。
**版本**：1 版（母钟/塔钟/报时球各一款，成一套）。
**依赖**：skeleton、palette；**interiors** 母钟位（§3.3，已点名 c191）、**A3** 报时塔外壳挂位（可占位）；A8 摆/针/落球（供料）。**被依赖**：interiors `starhall`（母钟）、看板 V5/V7。
**记录**：A5 领（牵头，排 refractor 之后）。默认：母钟靠星厅侧位占位、塔钟面 y≈28–31、报时球杆到 52。退回改法逐条记此。
