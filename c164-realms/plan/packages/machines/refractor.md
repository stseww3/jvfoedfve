# machines/refractor 大折射望远镜

**目标**：方案 §7.2「大折射望远镜」、§5.2/§8 大圆顶室主角；细化稿 §2.1、锚点 §3.1。墩顶赤道仪长镜筒，指向西方观测缝。**V8 大圆顶室主角**。
**优先级**：P1（主视角主角；依赖 A3 墩与穹顶壳，可占位先做）。

**约束**
- 坐标走骨架：独立墩 `S.PIER_CENTRE=(4,0)`、半径 `S.PIER_R=3`、墩顶 `S.ROOF_STAND=18`；缝 `S.SLIT_W=5` 朝西（`S.SLIT_FACING`）自鼓顶 `S.DRUM[1]`=23 过顶点 `S.DOME_APEX`=37+2。
- 色板：镜筒 `iron` 铆接 + 两端 `brass` 箍；叉架 `iron`+`brass_dark` 刻度环；配重 `iron`+`old_copper`；转仪钟 `brass`+`old_copper`，调速飞球点 `signal`。
- 16 像素一格，`px=scale`：镜筒 15 格→`scale=5`（画 48 单位）、叉架~5 格→`scale=2`、小件 scale1。铆钉行距、受光同 A1 铁板。
- 发光：无（夜观，暗）；仅目镜旁小红灯可选（三级，摆放函数返回 light）。
- 实体预算：本件 ≈60；`build()` 返回实体数。

**件清单**：`mach_scope_tube` 镜筒 ⌀1.5×15（整条一件，`riveted_tube`）；`mach_scope_finder` 寻星镜 ⌀0.5×4；`mach_scope_mount` 赤道仪叉架/支轴（极轴按纬度倾斜，两 `grad_circle`）；`mach_scope_cw` 配重杆+配重；`mach_scope_drive` 转仪钟（重锤+调速飞球，**飞球拆件交 A8**）；`mach_scope_cap` 墩顶铁盖/地脚 ⌀6（扣 A3 墩顶）；`mach_scope_piston` 升降台露出的液压柱×4+边栏（标升降接口 A8）。镜筒整体随赤道仪两轴动（**拆件标轴交 A8**）。
**交付物**：`build/scenes/obs/machines/scope.py`（+ `_kit.py` 的 `riveted_tube/grad_circle/governor/cradle/fork_mount`）；测试场景 `build/scenes/obs_mach_refractor/`（含盒子穹顶占位、朝西缝；`shots.json` 远/近/缝外）。
**验收**：五项，重点「第一眼/风格逻辑」（一眼是大折射镜、看得懂赤道仪驱动跟星、铆接铁筒+黄铜箍是电气时代）、「质感像素」（15 格镜筒像素一致不糊、铆钉连 A1 铁板）、「轮廓」（圆顶室里的斜长主角）。视角：墩上全貌、镜筒近景、从东经缝看镜筒（接 V2/V8）。
**版本**：**2 版比选**。甲「德式赤道仪：长镜筒+侧配重，古典台式」；乙「英式/摇篮轭架：镜筒居中、刻度环更重、工业味」。并排拍，评审挑。
**依赖**：skeleton、palette；**A3** 墩（§3.1，已点名 c178）、穹顶壳/缝接口（可盒子占位先做）；A8 两轴+飞球（供料）。**被依赖**：`domegear`（同框）、看板 V8。
**记录**：A5 领（牵头，排 orrery 之后）。默认：墩顶 y18、镜筒 15、极轴倾角按中纬度占位、升降台半升起。退回改法逐条记此。
