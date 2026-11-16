# props/plaques 说明牌

**来历**：总监 11-16 11:02 开的 `motion/guide`（导览）乙项，文字和要求以那张卡为准（`plan/packages/motion/guide.md`）。十二块英文说明牌，告诉来的人每件东西是什么。
**人**：公共的一半（做牌的函数、十二段文字、两个测试场景）a6；摆在哪两张表：室外六块 ashlar（c353，`props/_plaques_east.py`），室内六块 rec（c356，`props/_plaques_west.py`）。审批 a6。署名牌（`motion/guide` 甲项，mast c346）用同一个函数。

**做法**
- 一块牌全用游戏自带的 `text_display` 拼，不加模型、不加图、不加字体：两块色板（装一个空格的 `text_display`，背景就是一块 5×10 字体像素的矩形，用缩放拉成任意大小：米白的边、搪瓷蓝的面）加每行字一个实体。一块牌四到五个实体。
- 每块牌一样大：0.92 宽 × 0.27 高（格），贴着墙面出 0.018；一格宽的墩挂得下，两边各留 0.04 的石头。米白边 0.01。
- 两段字：第一行名字，全大写，字体像素 0.0075 格（比面宽就自动缩小）；下面一句，不超过九个词，字体像素 0.0055 格，一行放不下就在这里折成两行、两行尽量一样长（不交给游戏折行，所以牌知道字有多宽；字宽是从 26.3 的 jar 里量的）。句子的大写字母高 0.0385 格：三格以内读得清，十格外是个小点。
- 颜色读调色板：面 `enamel` 第 1 级（方案的 `#172c57`），边和名字 `cream` 第 3 级（`#f2ead6`），句子低一级。
- 亮度写死 `SHOWN = (0, 6)`（天光 0、方块光 6）。字不像模型的面那样按朝向打折：门牌是模型，`(15, 12)` 朝东的面只剩一半（米白 0.42）；字照 `(15, 12)` 画是 0.87。照资源包自己的光照图（`sky/_shaders.py` 改过的 `lightmap.fsh`：环境色、灯色）和真机的亮度设置（`tools/winmc.py`，gamma 0.5）算：方块光 6 时名字 0.43、句子 0.40、蓝面 0.08，和门牌一档；7 是 0.47，过了评审给的 0.45。**真机上要复量**，不对只改这一个常量。
- 16 格外不画（`VIEW = 0.25`，ashlar 的主意）：室外的牌离看板机位都在 21 格以上，看板十二张里一块都不进；走近才出。
- `text_display` 没有碰撞，只从正面看得见。

**接口**（`build/scenes/obs/props/plaques.py`）
- `sign(canvas, name, sentence, pos, facing="south", origin=(0, 0, 0), yaw=None, view=VIEW)`：挂一块任意文字的牌，返回实体数。`pos` 是牌心，落在所挂的面上；`facing` 是那个面的朝向。
- `place(canvas, key, pos, facing=…)`：挂 `TEXT[key]` 这一块。`corners(pos, facing)`：牌面四角，给摆的人自测用。
- `site(canvas, origin, keys=None)`：把两张表里的牌挂上；牌心后面那一格没有方块的不挂，记在 `canvas.plaques_left_out`。
- `build(canvas, origin)`：主场景里 `scenes.obs.GUIDE` 为真才挂（开关随 mast 的交付进总装，本包不加）；测试场景先调 `plaques.dress(canvas)`。
- 两张表各是一个文件、一个函数：`def plaques(): return {"armillary": dict(pos=(x, y, z), facing="south"), …}`，键是 `TEXT` 的键；位置读各包导出的常量。可选 `yaw=`（不正对格子的面）、`view=`。

**测试场景**
- `obs_props_plaques`：一面墙上十二块，加一格宽的墩上一块署名牌。`python -m scenes.obs_props_plaques --report` 打印每块牌怎么排的。
- `obs_props_plaques_site`：主场景加牌。每块牌前 2.6 格一个机位。`python -m scenes.obs_props_plaques_site --report`（节点的活）列出挂上的、没挂上的、站在方块里的机位、哪块牌离看板机位近到可能入画。两张表都进了以后 `shots.json` 由 a6 重写一次，摆的人不要各写各的（会撞）。
- 离线渲染器不画 `text_display`：留图只有墙，牌的样子只能看真机（s1）。

**验收**（照 `motion/guide` 的卡）：每块读得清、不穿墙、不挡路；一个机位里看得见的牌不超过两块；看板十二张里牌不抢主角。

## 记录

1. 11-16 第一版（a6）：公共的一半，5908789d 起。本地只建过模型和实体（十二块都排得下：`CABLE STATION` 那一句一行，其余折两行；署名牌的名字缩到 0.9 倍），`check.py` 等节点。
   - 朝向和尺寸不是猜的：26.3 的 jar 没混淆，`javap` 读了 `DisplayRenderer` 和 `TextDisplayRenderer` 的字节码。固定朝向的实体绕竖轴转 `-Rotation[0]`，偏航 0 时正面朝南、字往东排，所以 `Rotation` 的偏航就是 `K.FACING` 的值；字 0.025 格一个字体像素，行距 10 像素，最后一行的格子底边在实体的高度上；背景从最宽一行左边 1 像素画到右边、从第一行上面 1 像素画到底，颜色为 0 时不画。NBT 的字段名（`text`、`line_width`、`background`、`shadow`、`see_through`、`default_background`、`alignment`、`billboard`、`brightness`、`view_range`）也是从类里读的。
   - 真机上要看的三件：一、米白的亮度（上面的数是照资源包的光照图算的）；二、色板和字三层各隔 0.004 格，远看闪不闪；三、三格外句子读不读得清。

### 室内六块（rec c356，`props/_plaques_west.py`）

11-16 第一版，b52d4541。位置都在 `plaques()` 里从各包的常量算；牌心高一律脚上 1.5，片库那块 1.25（让开垛头的号牌）。

- `orrery` (11.5, 1.5, −4.0) 朝南：北侧廊子午梁下那根壁柱朝厅的面，落在深板岩柱础上，隔着中厅对着星象仪。不上柱身：柱身是 V7 右下最亮的石面，牌横满它是一条蓝带（cr3 #83149）。读 `starhall.beam_xs()`、`CX`、`Z0`、`FEET`。
- `master_clock` (7.0, 0.5, 0.5) 朝东：母钟底座正面中间那一块，钟箱下面，在大厅轴线上，从门口走过来正对。读 `clock.MASTER_AT`、`MASTER_FACING`。
- `time_room` (6.5, 8.5, −5.0) 朝南、`chart_room` (6.5, 8.5, 6.0) 朝北：廊上门套的西柱（从楼梯过来先到的那根）朝廊的一面。读 `shell.doors()` 的 `frame`、`y`、`inward`。12 格外不画。
- `plate_vault` (9.5, 1.25, 9.0) 朝北：进门左手那排岛架的北端，号牌「1」下面，进门迎面。读 `platevault.ISLAND_X`、`ISLAND_Z`、`FEET`。7 格外不画。
- `great_refractor` (14.0, 19.5, −2.5) 朝西：穹顶室东侧的衬板，配电板那三列北边的平面、正中一列，朝着绕墩走过来的人。不贴墩，不进 V8 机位到镜筒的视线（cr4 #80727）。读 `domeroom.niches()`、`lined()`、`FEET`。

看板里（都是照坐标算的，没有图）：
- V7 两块，都是 cr3 点过头的位置：座钟牌在画面下沿正中，星象仪牌在右下的柱础上。两块门牌离 V7 机位 14.1 格，中间隔着廊沿的大梁，另写了 12 格外不画，保证这张图里不出第三块。
- V8 不进：机位朝西，牌在它右后方 2.2 格。`--report` 只算距离和正反面，会把这块列成「离 V8 近」。
- V9、V10 不进：两间屋里没有牌，门牌挂在墙的廊子一面。片库那块离 V9 机位 8.0 格、隔着楼板，所以收到 7 格。
- V4 不进：离厅里两块 17.7 格和 20.7 格，超出 16 格；星象仪那块还被北门垛挡着。

没定的一处：`shell.door_cases()` 写的是门套的柱面留给石头，牌盖住柱面上 0.92×0.27 的一条。审批觉得不合适，两块门牌就挪到门内。

跑过的和没跑过的：
- 本地只导入过这张表，打印了六个位置、牌面四角和牌后那一格的坐标。
- 总监机上 `check.py --scene obs_props_plaques_site`，b52d4541，11:52：`result: PASS (0 failed, 3 with warnings)`。三条警告是主场景自己的（`prop_elec_cable` 的拉伸、v1 的实体数、V1 的遮挡），不是牌的。check 不说哪块牌没挂上，那要看 `--report`。
- 总监机上 `python -m scenes.obs_props_plaques_site --report`，b5e945df，11:55：六块都挂上，没有 left out；列成离看板近的是 `orrery`、`master_clock`（V7，7.5 格和 10.6 格）和 `great_refractor`（V8，2.2 格，机位不朝它），和上面算的一样。
- 一处没完：`plate_vault` 的测试机位落在横墙里，(9, 1, 6)。牌前只有 2 格深（z 7..9），场景统一退 2.6 格就进墙了；这块的机位距离等 a6 定（11:56 已问）。牌的位置不用动：人进门站在这 2 格里读。
- 关口、出图没跑；牌的样子只有真机看得到。
