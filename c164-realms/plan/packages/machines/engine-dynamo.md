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

---

## 记录（snow / c264，11-16）

A5 停机后这张卡一直空着。这一轮做出来了：模块 `build/scenes/obs/machines/engine.py`，场景 `build/scenes/obs_mach_engine_dynamo/`（8 个机位）。

**件与尺寸**
| 件 | 实际大小（格） | 画法 |
| --- | --- | --- |
| `mach_engine_base` | 床板 5.5 × 2.5 × 0.19 | **两节**拼起来（一个模型最多 3 格，见下） |
| `mach_engine_flywheel` | 直径 **5.0**（卡上写的数） | 画在 44 单位里（半径 22），`scale = 5×16/44 = 1.818`，`px = scale` |
| `mach_engine_cylinder` | 长 2.9 × 直径 0.69 | 画在 44 单位里，`scale 1.05` |
| `mach_engine_rod` | 连杆，随飞轮 | 与飞轮同 scale |
| `mach_engine_governor` | 高 2.0 | `scale 1.1` |
| `mach_engine_dynamo` | 2.5 × 1.9 × 2.1 | `px = 1`（本来就在 48 单位内） |
| `mach_engine_armature` | 电枢 + 皮带轮 | `px = 1` |

**一条吃过的亏，留给后面做机械的人**：`model.shift()` 硬限一个模型三轴都不超 **48 单位**（3 格）。更大的件只有两条路：(a) 拆成多节（床板这么做，一节 2.75 格、两节拼）；(b) 画在 48 单位里再放大——**但放大时 `px` 必须等于 `scale`**，否则 16 像素不成立（我先写成 `px=1` 又 `scale=1.8`，check 的 entities 项报 10/10/10 像素一格；反过来先 `px=scale` 又 `scale=scale` 报 26/26/26）。正确关系：`像素/格 = 16 × px / scale`，要它等于 16，就令 `px = scale`；而世界尺寸 = `画的单位 / 16 × scale`。

**摆位**：机组中心 `(76.0, 31.0)`（房内 x 67..89、z 20..42，脚 y −6），床板两节沿 x 铺开；飞轮在东（x +4.3），汽缸在西（x −2.6），调速器在汽缸侧（x −3.0、南 0.95），发电机在飞轮之外（x +6.4）由皮带带。`build(canvas, origin, facing, centre)`，`centre` 可覆盖。

**锚点给 A8（全部静止，总监 #505）**
- `mach_engine_flywheel`：锚点在轮心、轴上（轴沿 z）——绕 z 转就是飞轮连同曲柄销一起转。
- `mach_engine_rod`：锚点在曲柄销，跟着飞轮走。
- `mach_engine_governor`：锚在立轴根部，绕 y 转。
- `mach_engine_armature`：锚在电枢轴，沿 z。

**发光**：本包不发光（火光归 boiler 卡）；发电机的指示小灯 `LAMP` 默认关，开时按 6 级交给 A2。

**自查**：`check.py --scene obs_mach_engine_dynamo` PASS 0 失败 1 黄（flatwall 8 面，盒子发电房的墙）；`motion` PASS；8 个实体；`--verify` 8/8；`delivery.py` 七项全 PASS。

**已知最弱三处**
1. `set`·从门口看：飞轮和汽缸在房间尽头读得出是机器，但**缸体和十字头挤在一起**，八格外分不出哪是汽缸哪是滑道——要拉开得占更多床板，可床板只有 5.5 格。
2. `flywheel`·辐条：开了之后读得出八根辐，但辐条是直杆，没有蒸汽机飞轮那种**断面渐粗**的型；像素密度限制下只能这样。
3. `belt`·皮带没有画（这一版）：卡上写皮带用 `between` 扁带 + 动画贴图，动画贴图归 A1，还没到。飞轮和发电机之间现在是空的，读成“两个独立的机器”。

**待真机**：飞轮转起来时贴图会不会走样；`LAMP` 开了以后在 V6 的窗里看不看得到。
