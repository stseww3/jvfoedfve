# props/pipes 管线

**目标**：方案 §7.3 管线族、§5.1 立面外露管线；细化稿 §2.2。一套可拼接的管件 + 阀门 + 表，统一「三档管径 + 法兰对接 + 红手轮」。
**优先级**：P1（样板段立面要：铜雨水管+水斗、暖气管+红手轮；是立面质感的一部分）。

**约束**
- 色板：管身 `iron`（蒸汽/暖气干管）或 `old_copper`（雨水管/檐沟/细铜管）；法兰/支架 `iron`；活接/表框 `brass`/`brass_dark`；阀轮 `signal`；表盘 `cream`/`porcelain`+夜光 `phosphor`。
- 三档管径：粗 ⌀6、中 ⌀4、细 ⌀2.5 单位（`tube`/`hose`）。接头按管径配套，保证对接一致。
- 拉伸件：直管 `pipe_run_*` 沿 +z、`between` 拉伸、贴图沿轴均匀；**法兰、铁卡、阀门、表是单独件，不跟着拉**（R1-1）。
- 16 像素一格，`px=scale`。管线多贴墙/落地，锚点留空气格免变黑。
- 实体预算：样板段共用额度（见 lamps 卡）。摆放函数返回实体数。

**件清单**
- `pipe_run_L/M/S` 三档直管 沿线：`tube`，`between(a,b)` 拉。
- `pipe_elbow` 弯头、`pipe_tee` 三通：两/三段 `tube` 或 `hose`。
- `pipe_flange` 法兰：`ring`+一圈螺栓小 `box`，接头处套（单独件）。
- `pipe_union` 活接：六角 `tube`(sides=6)+锁母，brass。
- `pipe_bracket` 支架/铁卡：U 形 `box` 抱管+墙脚板（单独件，定距）。
- `pipe_expansion` 膨胀弯：`hose` 走 U 形回弯。
- `valve_wheel` 阀门(红手轮) 1×1：阀体 iron + 阀杆 brass + 手轮 `kit.handwheel`(signal)。勒脚暖气管、室内。
- `pipe_gauge` 压力表 1×1：brass `ring` 框 + `Sprite` 表盘(cream/porcelain) + phosphor 夜光刻度 + 指针。
- `pipe_hopper` 水斗 1×1 墙：漏斗 `taper`(old_copper)，雨水管顶。
- `pipe_eaves` 檐沟 沿线 墙/檐：半圆 `ring` 弧(old_copper)+铁卡。**与 A3 定方块还是模型**（R1-7），默认先出此件。

**交付物**：`build/scenes/obs/props/pipes.py`（+`kit.py` 管件 helper：`flange/elbow/tee/union/handwheel/pipe_run`）；测试场景 `build/scenes/obs_props_pipes/`。
**验收**：评审五项，重点「风格和逻辑」（管线有来去、不断头、红手轮是警示锚点）、「质感和像素」（拉伸件均匀、接头像素一致）。视角：远看一段立面管路、近看阀门+表、和铸铁墙并排。
**版本**：1 版。
**依赖**：palette、`kit.py`。立面挂点（勒脚暖气管位、雨水管位）用 R1 骨架数占位，待 A3 坐标。**被依赖**：main 样板段、site 发电房管桥、interiors 授时室/发电房内。
**记录**：默认管径 6/4/2.5；铁卡定距 6 格；檐沟先出模型件。退回改法记此。
