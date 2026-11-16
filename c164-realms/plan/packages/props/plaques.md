# props/plaques 说明牌

**来历**：总监 11-16 11:02 开的 `motion/guide`（导览）乙项，文字和要求以那张卡为准（`plan/packages/motion/guide.md`）。十二块英文说明牌，告诉来的人每件东西是什么。
**人**：公共的一半（做牌的函数、十二段文字、两个测试场景）a6；摆在哪两张表：室外六块 ashlar（c353，`props/_plaques_east.py`），室内六块 rec（c356，`props/_plaques_west.py`）。审批 a6。署名牌（`motion/guide` 甲项，mast c346）用同一个函数。

**做法**
- 一块牌全用游戏自带的 `text_display` 拼，不加模型、不加图、不加字体：两块色板（装一个空格的 `text_display`，背景就是一块 5×10 字体像素的矩形，用缩放拉成任意大小：米白的边、搪瓷蓝的面）加每行字一个实体。一块牌四到五个实体。
- 每块牌一样大：0.92 宽 × 0.27 高（格），贴着墙面出 0.018；一格宽的墩挂得下，两边各留 0.04 的石头。米白边 0.01。
- 两段字：第一行名字，全大写，字体像素 0.0075 格（比面宽就自动缩小）；下面一句，不超过九个词，字体像素 0.0055 格，一行放不下就在这里折成两行、两行尽量一样长（不交给游戏折行，所以牌知道字有多宽；字宽是从 26.3 的 jar 里量的）。句子的大写字母高 0.0385 格：三格以内读得清，十格外是个小点。
- 颜色读调色板：面 `enamel` 第 1 级（方案的 `#172c57`），边和名字 `cream` 第 3 级（`#f2ead6`），句子低一级。
- 亮度写死 `SHOWN = (0, 7)`（天光 0、方块光 7）。字不像模型的面那样按朝向打折：门牌是模型，`(15, 12)` 朝东的面只剩一半；字照 `(15, 12)` 画会到 0.85 上下。方块光 7 照游戏自己的曲线、默认亮度下米白约 0.40，评审要的是看板里不过 0.45。**真机上要复量**，不对只改这一个常量。
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
   - 真机上要看的四件：一、牌朝哪边（照推算 `Rotation` 的偏航就是 `K.FACING` 的值，朝南为 0；错了会是背面朝人、看不见）；二、米白的亮度（上面的 0.40 是算的）；三、色板和字三层各隔 0.004 格，远看闪不闪；四、三格外句子读不读得清。
