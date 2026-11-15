# materials/brass-oldcopper-small

## 目标
方案 6.2 第二批：黄铜（bamboo 族）、旧铜（waxed_exposed）、小件（护墙板/黄铜嵌线/搪瓷铭牌）+ 脚步声改金属。

## 约束
- 黄铜 `BRASS_*`（bamboo 族）：`mat("brass")`/`brass_dark`/`brass_flat`，色阶 R0–R5。板/花纹板/粗管/栏杆/玻璃铜门(brass 框+opal 芯)/活板门/按钮/铭牌/架子。重定向（和 vanilla 竹子分家：竹子我们不用，可直接改，但为稳妥仍走 redirect 并自查）。
- 旧铜 `OLD_COPPER`=waxed_exposed_copper、`OLD_COPPER_CUT`=waxed_exposed_cut_copper(+stairs/slab)：`mat("old_copper")`，色阶重画。**只改 waxed_exposed_\***，不碰 `waxed_oxidized_*`/`waxed_weathered_*`。重画前檐沟用原版色占位（R1 §0.2）。
- 小件：`WAINSCOT`=dark_oak_trapdoor（`dark_wood` 护墙板，A7 不当活板门）、`BRASS_INLAY`=yellow_carpet（地面黄铜子午嵌线）、`ENAMEL_SIGN`=oak_sign 族（`enamel`+`cream` 搪瓷铭牌；文字只数字/符号/少量英文）。
- 脚步声（做法 E）：`K.sounds(pack_dir, {"block.bamboo_wood.step": [...], ...})`，写进 `assets/minecraft/sounds.json`（`"replace": true`），把 `block.bamboo_wood.*` 指到 `block/copper/step*`、`break*`，子块同理。只引用原版音频，无 .ogg。
- 注意：`bamboo_shelf` 的图是 32×32 的大图（`paint()` 允许 16 的整数倍见方）；铜灯的图是 16×48 的动画；告示牌在 26.3 里是普通方块模型，和别的方块一样重定向。
- `strays()` 每张过。

## 交付物
- `build/scenes/obs/materials/brass_oldcopper_small.py`（模块名 = 卡名，`-` 写成 `_`；内部分三段：黄铜、旧铜、小件）；`BLOCKS = K.blocks(...)`。
- 测试场景 `build/scenes/obs_mat_brass/`（零件用 `materials/_board.py` 的 `brass`、`twins_plates`；含旧铜并排未上蜡 exposed 铜证明只改 `waxed_exposed_*`、小件样例）；`shots.json`：近看黄铜/旧铜/小件、旧铜分家并排。

## 验收
- 黄铜像一套；旧铜和模型旧铜色阶接得上、只改 `waxed_exposed_*`（并排的未上蜡 exposed、`waxed_weathered_*` 不变）；小件到位；脚步金属声、无外来音频；颜色全在色阶。
- `tools/check.py --scene obs_mat_brass` 全过。

## 版本
1 版。

## 依赖
- 依赖：respack-redirect；旧铜与 A6 模型旧铜色阶对齐（檐沟方块↔雨水管模型）。
- 被依赖：main（檐沟/铭牌/黄铜件）、props、interiors。

## 记录
- 领卡：c194（代号 m1），11-14。分支 `cursor/c164-m1-brass-fa68`，提交前缀 `c164-m1:`。先后按总监的话：① 地面嵌线 ② 穹顶和檐沟的旧铜 ③ 其余小件。
- **地面嵌线改成细线**（总监 11-14 拍板：整格的黄带在夜里读成路标和警示线）。占用表加了三个角色（S2 总装 1cddd064，总监批）：`BRASS_LINE` = rail，`BRASS_CROSS` = activator_rail，`BRASS_STAR` = detector_rail。
  - 画法：格子正中两像素宽的暗铜，两边各一像素石缝阴影（slate 第 2 级），其余透明，底下的铺地照常看得见。铜用旧铜色阶最暗的两级，十六分之一的像素是暗黄铜（brass 第 1 级）。线身平均饱和度 44%（黄铜 73–79%），明度 82，比 polished_tuff 暗。
  - 模型：原版铁轨的平面离地 1 像素，这里降到 0.25 像素（`_flush`）。走 `K.redirect` 写自己的模型，原版的父模型不动（powered_rail 还在用）。坡道那四个 shape 也有模型，但不要用。
  - 拐角画成从一边中点到邻边中点的 45° 斜线。一格横、一格纵轮流走的台阶，两个拐角连放，正好连成一条斜线：半径 7 的环在地上是一个八边形的细环（直边 5 格、斜边 4.5 格）。
  - 环按八边形摆，不按像素圆摆（11-15 改）：像素圆在半径 5、8 和 8 以上台阶不匀，每个不匀的台阶在线上是一个折，环读成疙疙瘩瘩的一圈。测试场景的 `ring(r)` 现在直接摆八边形（四条轴上各一段直边，中间是匀的台阶，直边的长度取八条边最接近等长的那个）。半径 1–4、6、7 和像素圆是同一条路，前庭的半径 7 没变；半径 5 是直边 5 格、斜边 2.5 格。
  - `BRASS_CROSS`（两线相交）和 `BRASS_STAR`（八角星）转 90° 不变，因为游戏里这一格最后朝哪边由摆放先后定。星画成八角是为了不读成十字。
  - `BRASS_INLAY`（黄地毯）留着，是整格的黄铜地板。
- **铁轨的规矩**（S2 11-14，摆线的人都要知道，测试场景的文档里也写了）：脚下必须是整块实心方块，半砖和楼梯上会掉；每格线旁边的铁轨必须正好是它 shape 说的那两格，所以两条线不能贴着走，星旁边一格内不能有线；铁轨落地会自己转向，离线图看不出，记「待实机」。测试场景里的 `line()`、`ring()` 可以直接抄。
- **表面**（三轮图看下来的）：暖色金属上不用色板的短拉丝（读成木纹），不画污渍斑（读成陶砖），不画每块都重复的记号（板上的反光短线在整面墙上读成抽屉面），切板里不留深一级的板（读成补丁）。只留亮暗边、螺钉和几颗麻点。
- **栏杆、栅门、活板门**不再是染色的竹子（染成黄铜还是读成藤条），在模型用到的那几块贴图上重画：栏杆和栅门是圆管，活板门是一块带拉环的盖板，不镂空，翻过来图也对。只有架子和吊牌的横杆、链条还是原版镂空图染进色阶。
- **牌子**：26.3 里告示牌是方块模型。只画牌面，立柱画成两像素的杆。黄铜牌配游戏默认的深色字；搪瓷牌要写白字，摆牌子的人注意。
- **声音**：20 个 `block.bamboo_wood.*` 事件指到原版的 copper、copper_door、copper_trapdoor、stone_button、metal_pressure_plate 事件（`"type": "event"`），没有 .ogg。
- **旧铜**：只重定向 `waxed_exposed_*`。测试场景里并排摆了未上蜡的 exposed 和 waxed_oxidized 的原版方块作证，所以 `check.py` 的 blocks 项有一条预期的黄（5 种不在占用表里的原版方块）。
- 图在管理员电脑上出，收图夹前缀 `m1-obs_mat_brass-`；交付的图在 `renders/obs_mat_brass/`。
- **11-15 交付，图待补**（管理员电脑离线，总监 11-15 公告：能交付的照常交付）。分支已含总装 142f3079。
  - `tools/check.py --scene obs_mat_brass`：过，0 项失败，1 项黄（blocks 项那 5 种作证用的原版方块，见上）。
  - `tools/delivery.py materials/brass-oldcopper-small`（对总装 142f3079）：过，0 项失败，1 项待看（pictures：25 个机位一张图都还没留）。
  - 没有图，这一轮看的是贴图的平面拼图（云端几秒的脚本，不是渲染，不进仓库）：细线的直段、拐角、交叉、八角星都接得上，星不读成十字；黄铜板、花纹板、旧铜、切板、整格铜板、护墙板、活板门、搪瓷板各 8×8 平铺，没有看到条纹。
  - 平面图判不了、等图的：打了光以后黄铜像不像一套、旧铜和原版 exposed 并排的差别、二十格外的平铺。等实机的：铁轨落地会不会自己转向。测试场景里的 130 格线逐格对过 S2 的三条规矩，没有违反的。
  - 电脑上线以后：出 25 张图，看图改，图进 `renders/obs_mat_brass/`，再发一次【交付】。
- **11-16 补图**（第 3 班 m1，聊天 c335，接 c194；新分支 `cursor/c164-m1-brass-f3-c367`，从 a2370b00 开，合总装 ffceb496）。交付 a2370b00 已由 S2 合进总装（合并提交 bd7f25f9）。
  - 25 张离线图在 `renders/obs_mat_brass/`（节点 node49 出，`tools/selfshots.py obs_mat_brass`，画的是 ed465c0e，提交 2e7b29c8；每张的提交和 SHA-256 在同目录 `shots.txt`）。代码一字未改。
  - 节点上 `tools/delivery.py materials/brass-oldcopper-small`（对总装 b16acef）：过，0 项失败、0 项待看，pictures 25/25。`tools/check.py --scene obs_mat_brass`：过，1 项黄（那 5 种作证用的原版方块）。
  - 图上对过的事实：细铜线的直段、45° 拐角、交叉、八角星都接得上，半径 7 的环是一个匀的八边形（`emblem`、`emblem_down`、`court_down`）；线在凝灰岩和板岩两种铺地上都读得出，是一条暗铜线，不读成路标（`emblem_close`、`court_walk`）；旧铜和未上蜡的 exposed、waxed_oxidized 并排，只有 `waxed_exposed_*` 变了（`copper_twins`、`roof`）。
  - 等评审（c332）和真机的：黄铜一套在灯下的饱和度、旧铜的底色偏粉不偏棕（和檐口白石并排时，`roof_gutter`）、铁轨落地会不会自己转向。
- **11-16 打磨轮**（评审 #8，c332：退三处；黄铜一族、地面细线、护墙板、两种铭牌定稿没动。代码 705567f7，合总装 3c0f8e17 以后是 fa0e0fd7，图 e7d6a54e）。
  1. 旧铜两种（总监 11-16 拍板定甲）：板面从色阶正中一级降到 C1，亮边 C2，暗边和麻点 C0；不加铜绿；色板的色阶和默认的 `old_copper` 没动。模型那头的落水管用同一级，归 m3 改（总监已告知）。图：灯下是旧铜币的深褐，和并排的原版 exposed 一眼分得开（`copper_twins`、`wall_copper`）；天光下屋面比檐口石暗一截，檐沟是屋面和檐口石之间一道褐色的深线，不是黑缝（`roof`、`roof_gutter`）。
  2. 麻点只留单颗（`_single()`）：整板第 3 版 x=6、y=4..6 连成竖道的三颗去掉了中间一颗；别处相挨的两颗也只留先画的一颗（整板第 2 版一处，切板三版各一处）。骰子是逐格掷的，偶尔会连着中，所以规矩写进了画法，不是只改那一处。黄铜板定稿，不走这条规矩。
  3. 整格嵌板 `BRASS_INLAY`：暗点 5% 降到 1.5%，亮点 2.5% 降到 0.8%，亮点不挨暗点（连斜角也不挨）；三版各剩 3 到 6 颗暗点、0 到 2 颗亮点。地毯模型从高出地面 1 像素降到 0.25 像素（`_sunk()`，和细线的 `_flush()` 一样高），侧面那道暗边没有了（`brass_line`、`emblem_walk`）。
  4. 吊牌的链：原版的链比牌面暗得多，和整张图一起取色时每一环都落在色阶最暗一级，所以是两只黑扣。现在链单独取色（`_sheet(chain=)`）：黄铜牌的链染 brass，中间调 R2（就是牌子侧边的那一级），亮面 R3、背面 R1；搪瓷牌的链留铁，中间调 I4，亮面 I5、背面 I3，比横杆高一级。横杆两种都还是铁（I3），没动：测试场景里只有顶挂的两块，横杆不在图上（`brass_signs`、`brass_b`）。
  - 节点 node49：`check.py --scene obs_mat_brass` 过，1 项黄（那 5 种作证用的原版方块）；25 张图重出，23 张有变化（凡是带到旧铜、嵌板、吊牌的）。关口 `tools/gate.sh` 的结果写在【交付】消息里。
  - 等真机的不变：铁轨落地会不会自己转向；0.25 像素高的线和嵌板远看闪不闪；黄铜和铜的脚步声；门上乳白玻璃有多亮。
