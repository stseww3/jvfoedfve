# props/lamps 灯具

**目标**：方案 §7.3 灯具族、§3.2 灯光分级；细化稿 `plan/parts/A6-props.md` §2.1。一族电气时代灯具，统一「铸铁支架语 + 玻璃灯罩 + 黄铜灯头/开关键」。
**优先级**：P1（样板段入口+前庭、室内星厅都要；interiors/L7 已点名要 pendant/bracket/cage）。

**约束**
- 色板只走 `from scenes.obs.common.palette import mat`：杆/架=`iron`/`iron_dark`；灯头/颈/链=`old_copper`/`brass`/`brass_dark`；罩：乳白=`opal`、绿台灯=`phosphor`、信号=`signal_glow`；裸灯泡=`glow`。
- 16 像素一格，`px=scale`（细化稿 §1.6）。超 3 格的件取最小整数 scale（路灯 4 格→scale2）。
- 发光：罩/灯泡面 `emit=15, shade=False`（只那面亮）。**emit 面压小**——收成罩内一小粒暖灯丝/一圈灯口，不把整只罩面做成「发光贴纸」；emit 色与 A2 暖光（`#ffb45e`）对齐，保证亮区 <1/3（S3 预审 3）。真实照明由 A2 放隐形 `light` 方块；**摆放函数返回每盏灯的 light 坐标与级别**：一级 13–14（入口/路灯）、二级 9–10（壁灯）、三级 5–8（走道/台灯）。
- 拉伸件：`lamp_festoon` 电线 `between` 拉伸、贴图沿轴均匀；灯泡是单独件按固定间距摆（R1-1）。
- 实体预算：样板段每跨道具均 ≤20、整段 ≤120（与管线铁件共用）；室外共 1100。摆放函数返回实体数。

**件清单**（名字 / 尺寸 / 挂法 / 光级）
- `lamp_street` 铸铁路灯 ⌀1×4 落地 一级：竖杆 iron，球罩 opal，黄铜颈 brass。前庭、大台阶。
- `lamp_bracket_white` 铁架白玻璃壁灯 1.5×1 墙 二级：卷涡托架 iron(`ring` 弧)+白玻罩 opal。入口门两侧、室内。
- `lamp_cage` 铁笼壁灯 1×1 墙 三级：铁笼(细 `box`/`tube` 绕)+裸灯泡 glow。走道。
- `lamp_pendant_enamel` 搪瓷伞罩吊灯 ⌀2×1.5 吊顶 三级：旧铜链+伞罩(enamel 外、opal 内，`ball` 下半)。星厅、室内。
- `lamp_desk_green` 绿玻璃台灯 1×1 落地/台 三级：brass 座+phosphor 罩(`ball` 压扁)。写字台。
- `lamp_signal` 信号灯 0.5×0.5 墙/顶 闪：iron 壳+signal_glow 镜。闪=动画贴图(A1)+计时(A8)，本卡只出静件并标注接口。
- `lamp_festoon` 裸灯泡串 沿线 一级：old_copper 电线(`between` 拉)+glow 灯泡(单独件定距)。雨棚下、缆车站。

**交付物**：`build/scenes/obs/props/lamps.py`（+ 用到的 `kit.py`）；测试场景 `build/scenes/obs_props_lamps/`（`props.py`：`build_models/GALLERY/SCALE` + `shots.json`）。
**验收**：评审五项，重点「质感和像素」（近 3 格经得住、像素一致）、「风格和逻辑」（成族像一套、是电气时代、灯是暖的）、「明暗光色」（光级别对、不死黑）。视角：远看一排、近看单灯、和铸铁墙并排看接缝。
**版本**：**2 版比选（灯罩+支架母题）**。甲「乳白球罩+卷涡铸铁」偏古典；乙「棱锥搪瓷罩+直角铁架」偏工业。两版都覆盖 bracket/pendant/cage 三件，并排拍，评审挑。
**依赖**：palette（已有）、`kit.py`（本族先写）；A2 光源级别（摆放函数供料，不阻塞）；门两侧壁灯位、吊顶高用 R1 骨架数占位。**被依赖**：main 样板段、interiors 星厅、site 前庭。
**记录**：A6 领（牵头）。默认：乳白罩用 opal；light 级别按 §3.2；灯泡定距 8 格。退回改法逐条记此。
