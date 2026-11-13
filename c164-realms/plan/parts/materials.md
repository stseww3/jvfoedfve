# 细化稿：方块材质（materials 类别）

牵头人：a1（c176）。对应方案 `ART-PLAN.md` 第 6 节（全部）、3.1 色板、5.1、第 10 节验证、第 12 节红线。
已按 `plan/reviews/R1-first-designs.md` 第 2 节修订（石材重写、色板走公共、面板用色、旧铜第二批、自查用 strays）。
状态：技术路线 R1 已通过，**石材一节已按要求重写**。本稿是类别参考；逐项像素规则进各卡片，卡片在 `plan/packages/materials/`。

版本锁定 26.3（数据包 121，资源包 97，Java 25）。代码放 `build/scenes/obs/materials/`，测试场景 `build/scenes/obs_mat_<包名>/`。

---

## 0. 一页结论

- **一条主线技术**：被占用的方块绝大多数不能"只换同名贴图"，要**重定向方块状态 + 模型到 `c164:` 新贴图**。原因有二：
  - 铸铁族：非蜡 `oxidized_*` 和它的 `waxed_` 同胞共用同一套 model/贴图，只能靠改**非蜡的 blockstate** 分家（非蜡→铸铁，蜡封→铜绿）。
  - 石材族（R1 指出）：`smooth_sandstone` 是 `cube_all` 指向 `sandstone_top`，根本没有 `smooth_sandstone.png`；而 `sandstone_top` 被 sandstone 顶面、cut/chiseled 两端、全族楼梯台阶顶面共用。换一张图四种石材一起变。所以石材也走重定向。
- **一个公共工具** `redirect_block()`（R1 批准，单独提交请 c188 优先合并）：从游戏文件读 blockstate+模型，生成 `c164:` 副本并重写**被占用方块**的 blockstate，保留全部状态与旋转，带自查。石材族、铸铁族、16 面板、旧铜、黄铜都用它。
- **色板唯一来源** `build/scenes/obs/common/palette.py`（A0 发布）：`mat(name)`、`colour(name,i)`、`strays(pixels)`。我不自建 palette。每张生成的贴图都过 `strays()`，不得有色板外颜色。
- **占用表唯一来源** `build/scenes/obs/common/blocks.py`（A0 发布）：只用角色名（`B.ASHLAR_FINE`、`B.IRON_RIVETED`、`B.PANELS["dial"]`…），不写原版方块名。
- 自查用离线渲染（管理员电脑的出图工位，`COMMON.md` 第 3 节）；`place.py`/打包到客户端只有出图工位能跑。云端只写码、提交、跑几秒的小脚本（画贴图、`strays`、平铺预览）。

R1 已澄清：我之前提的占用表两条"勘误"是译名误会——方案里"台阶"=slab、"楼梯"=stairs。`cut_sandstone` 有 slab、无 stairs；`smooth_sandstone` 有 stairs+slab、无 wall，都正确，占用表不改。

---

## 1. 色板角色（都在 `common/palette.py`，R1 批准）

本类别用到的 `mat()` 名：`ashlar`、`iron` / `iron_dark` / `iron_flat`、`old_copper`、`brass` / `brass_dark` / `brass_flat`、`glow`、`phosphor`、`signal` / `signal_glow`、`enamel`、`cream` / `cream_cloth`、`slate`、`night_glass`、`porcelain`、`opal`。
- 黑刻度/黑字 = `iron` 最暗一级（`colour("iron",0)` = `#12151a`）。
- 白瓷（保险丝、表盘、瓷瓶）= `porcelain`。
- 磨砂亮窗 / 乳白灯罩 = `opal`（我原稿的"琥珀去饱和"作废，改用 `opal`，R1 定）。
- 暗窗映天色 = `night_glass`。搪瓷 = `enamel` + `cream`。
- 新增颜色一律群里向 A0 提，不自己加。

---

## 2. 技术做法与验证（方案 6.3 + 第 10 节档位；R1 第 2 节）

### B1. 重定向 + 和 `waxed_` 分家（主线）
- **已查实**：全部非蜡 `oxidized_*`（copper / cut_copper±stairs±slab / chiseled / grate / door / trapdoor / bars / chain / lightning_rod / bulb / lantern）的 `waxed_` 同胞 blockstate 都引用**同一套** `block/oxidized_*` 模型/贴图。只能改**非蜡的 blockstate**。
- **已查实**：砂岩族顶面/端面共用 `sandstone_top`（见第 3 节映射表），必须整族重定向。
- **做法**：`redirect_block(pack, block, tex_map, variants=N, ns="c164")`
  - 用 `artkit.gameassets.Assets` 读 `blockstates/<block>.json` 及其引用的全部 model（含 parent 链）。
  - `tex_map`：{vanilla 贴图引用 → c164 贴图基名}，例如 `{"minecraft:block/oxidized_cut_copper":"block/iron_riveted"}`。对每个引用到该贴图的 model，生成 `c164:` 副本（保留 parent 与其它纹理键），把纹理键指到 `c164:` 新图。
  - `variants=N`：每个 model 出 N 份副本（`…__v0..vN-1`，贴图用 `f"{基名}{v}"`），blockstate 里**每个状态键**的 apply 改成 N 个副本的加权表（楼梯/台阶/墙的所有状态都带变体，不只整块）。
  - 重写 `blockstates/<block>.json`，逐状态把 `model` 换成 `c164:` 副本，**原样保留** `facing/half/shape/type/axis/lit/powered/hinge/open` 与 `x/y/uvlock/weight`。
  - **自查**：只写 `blockstates/<block>.json` 和 `c164:` 下的文件；绝不写 vanilla 贴图、vanilla 模型、也不写 `waxed_oxidized_*`/`waxed_weathered_*` 的任何文件（旧铜的 `waxed_exposed_*` 是显式单独调用，见第 6 节）。断言输出文件名集合符合预期。
- **验**：材质板上把"被占用块"和它该保持原状的同胞（铸铁↔`waxed_oxidized_*` 铜绿、旧铜↔`waxed_weathered` 暗铜）并排；离线出图确认分家、每状态正确、颜色全在色阶内。
- **档位**：方案第 10 节第二档（状态改指向，没在我们包里试过）。M1 第一时间实测。

### C. 自发光 `light_emission`（元素级 0–15）
- **已查实**：原版 `cross_emissive` 系在用，元素级字段；离线渲染器 `raytrace.py` 已支持（`el_emit`）。只让该元素渲染变亮，不发世界光（世界照明由 A2 的隐形 `light` 方块给）。
- **用在**：亮窗玻璃（块+板各元素）、`IRON_BULB`/`IRON_LANTERN` 发光件、门舷窗（M2 再定整扇低亮 vs 窗后 light）。
- **验**：全黑环境离线出图，发光件自亮、颜色对；与不加字段/备选（窗后常亮片）并排。

### D. 动画贴图 `.mcmeta`
- **用在**：面板 `tubes`/`scope`/`counter`/`pilot_lamps`（R1 与 `blocks.py` 已标），`recorder` 可选。纵向堆帧 + `{"animation":{"frametime":N}}`。帧率/节奏与 A8（motion）对齐；不占运算。
- **验**：真机加载看动，F3+T 热重载确认。

### E. 脚步声改指向 `sounds.json`
- **已查实**：黄铜族（bamboo）用 `block.bamboo_wood.*`；原版金属脚步文件 `block/copper/step1..6`、`break1..4`。
- **做法**：资源包 `assets/minecraft/sounds.json` 用 `"replace":true` 把 `block.bamboo_wood.step/hit/fall`→`block/copper/step*`，`place/break`→`block/copper/break*`；子块（door/trapdoor/fence/button/pressure_plate/hanging_sign）同理。**只引用原版已有音频，不加任何 .ogg**。
- **验**：真机踩/敲听金属声；确认资源包无音频文件。

---

## 3. 石材（灰白石，ASHLAR_* 四种）—— R1 要求重写

**全部走 `redirect_block`**（不换同名贴图）。砂岩族 vanilla 贴图映射（已对照 26.3 jar）：

| 角色（占用块+同族） | vanilla 模型用的贴图键 → 我画的 c164 贴图 |
| --- | --- |
| `ASHLAR_ROUGH` = sandstone + stairs/slab/wall | 侧 `sandstone`→`ashlar_rough`；顶 `sandstone_top`→`ashlar_rough_top`；底 `sandstone_bottom`→`ashlar_rough_top`；wall 用 `sandstone`→`ashlar_rough` |
| `ASHLAR_FINE` = smooth_sandstone + stairs/slab | 全面 `sandstone_top`→`ashlar_fine`（统一一张，和原版 smooth 一致；两层通缝图案在竖面读得对，顶面作接缝线可接受） |
| `ASHLAR_PANEL` = cut_sandstone + slab | 侧 `cut_sandstone`→`ashlar_panel`；端 `sandstone_top`→`ashlar_fine_top` |
| `ASHLAR_EMBLEM` = chiseled_sandstone | 侧 `chiseled_sandstone`→`ashlar_emblem`；端 `sandstone_top`→`ashlar_fine_top` |

因为每块各出自己的 `c164:` 模型副本，同一个 vanilla 引用（如 `sandstone_top`）在不同块里可指向不同 c164 图，互不干扰；vanilla `sandstone_top.png` 始终不动。

像素规则（`mat("ashlar")`，色阶 A0–A5；精确到像素）：
- `ashlar_rough`（粗琢面侧，3 变体，比选要 3 版）：一石一格；**四边各 1px 深缝 A0，拼起来 2px 宽缝**（R1 同意，材质板确认）；主面 base A2，约 12 条 2–3px 凿痕（上沿 A3 亮、下沿 A1 暗）；上/左内缘 +1、下/右内缘 −1。
- `ashlar_rough_top`：粗石顶/底，弱横向层理，base A2。
- `ashlar_fine`（细琢面，4 变体）：一格两层各 8px；两层通缝 1px A0（第 7、15 行）；竖缝每层一条、两层错开半格（下层 x=7、上层 x=15），**1px A1**；每层整体 ±1（base A3）。4 变体循环，8×8 平铺竖缝错开不起条纹。
- `ashlar_fine_top`：细琢面端面（给 panel/emblem 端），平整 base A3、浅接缝。
- `ashlar_panel`（凹板，2 变体）：居中下沉方板，外框 top/left A4、bottom/right A1，沉底 A2，底行 A0。
- `ashlar_emblem`（台徽块，2 变体）：台徽浮雕（圆环+子午竖线+右上星）居中，底=细琢面，环/星 A5、阴影 A1。

**石材退路**（方案 15 风险）：`ashlar` 卡做 3 版比选，其中一版是"原版砂岩直接用"的对照，M1 给管理员并排挑。

线脚（腰线/檐口/柱础柱头）由 A3（main）用本族楼梯/台阶几何承载这些贴图实现；几何不足再加一张 `ashlar_course`，与 A3 对接。

---

## 4. 铸铁（IRON_*，十二种）

全部 `redirect_block`。`mat("iron")` / `iron_dark` / `iron_flat`，色阶 I0–I6。逐项像素规则进 `iron` 卡；要点：
- `IRON_PLATE`(oxidized_copper，无同族)：平铁板，无铆钉，base I3，轻刷纹，浅 bevel。3 变体。机壳/水箱。
- `IRON_RIVETED`(oxidized_cut_copper+stairs/slab)：铆接板，边框 I4/I1，铆钉 1px I6 高光+下 1px I1 阴影，固定 8 点（四角+四边中），贴边使相邻块连成行。3 变体（仅刷纹变化、铆钉固定）。变体覆盖楼梯台阶。
- `IRON_CAST`(oxidized_chiseled_copper)：铸花板，外框铆接+中心凸花（小台徽/菱形），I5/I1。2 变体。
- `IRON_GRATE`(oxidized_copper_grate，镂空)：4px 网格条 I3、交点 I5，网孔 alpha=0。2 变体。
- `IRON_DOOR`(oxidized_copper_door)：`iron_door_top`+`iron_door_bottom`（各 16×16 对齐成 2 格）；铆钉包边，下半舷窗（`brass` 圈 + `glow` 中心，发光 M2 定）；上半气窗。
- `IRON_HATCH`(oxidized_copper_trapdoor)：铆接盖 / 横百叶，2 变体。
- `IRON_BARS`(oxidized_copper_bars，multipart)：细竖铁条 I2–I3、高光 I5 + 一道横档。
- `IRON_PIPE`(oxidized_copper_chain，axis)：细管/绞合电缆，中列 I4、两侧 I1–I2、每 4px 法兰环 I5。
- `IRON_ROD`(oxidized_lightning_rod，facing)：细金属杆，中亮 I5、边 I1。
- `IRON_BULB`(oxidized_copper_bulb，lit/powered)：铁笼罩+琥珀灯泡，lit 加 `glow`+`light_emission`；**点亮发光度 4**，正好做三级弱光。
- `IRON_LANTERN`(oxidized_copper_lantern，hanging/standing)：铁皮灯罩+`glow` 透光缝，发光度 15，加 `light_emission`。

---

## 5. 窗（WINDOW_*/SKYLIGHT，六种）

玻璃无 `waxed_` 问题，但自发光要改模型（做法 C）。窗棂一律在贴图里画（8px 一格窗格，窗棂 1px `colour("iron",1)`，四边无缝，拼成网；3 格宽拱窗横显 6 列）。
- 亮窗（自发光，加 `light_emission≈10`）：`WINDOW_LIT`（黄，暖亮 `glow`）、`WINDOW_CURTAIN`（橙，上亮下压暗作半帘）、`WINDOW_FROSTED`（白，`opal` 柔光、格影弱）。亮窗卡做 2 版比选。
- 暗窗（不发光，映天色 `night_glass`）：`WINDOW_DARK`（灰，斜向冷反光）、`WINDOW_BLIND`（黑，近全黑+弱反光）、`SKYLIGHT`（浅灰，偏亮+大铁框格 12px）。
- 两种形状：**整块玻璃** `*_stained_glass`（齐平大拱窗幕墙，贴图平铺成窗棂网，无缝）；**玻璃板** `*_stained_glass_pane`（凹窗/小窗/薄剖面，重定向 post/side/side_alt/noside/noside_alt 五模型，面贴图=`*_stained_glass`、边贴图=`*_stained_glass_pane_top`，亮窗同样加 `light_emission`，保留 `force_translucent`）。
- 模型窗框分工（R1 与 A6）：玻璃贴图只画细窗棂；A6 的模型窗框只做拱头/外框/一道中横档或中竖梃，压在我的窗棂线上，不另起网格。

---

## 6. 面板、黄铜、旧铜、小件

**16 仪表面板** `B.PANELS[...]`（glazed terracotta，无 waxed 问题）：重定向每块 blockstate→`c164:` 模型，**只在 facing 那一面**放仪表贴图（直立），其余五面 `iron` 机壳；用 vanilla 的 facing（N/S/E/W，y 旋转）把正面对房间，去掉原版拼花旋转。清单与动画见 `blocks.py` 的 `PANELS`（`tubes/scope/counter/pilot_lamps` 带动画，`recorder` 可选）。黑刻度=`iron[0]`，白瓷=`porcelain`，示波/辉光=`phosphor`/`glow`，警示=`signal`。逐种画法进 `panels` 卡。

**黄铜（第二批，bamboo 族）** `BRASS_*`：`mat("brass")`。板/花纹板/粗管/栏杆/玻璃铜门/活板门/按钮/铭牌/架子。脚步声改金属（做法 E）。

**旧铜（第二批）** `OLD_COPPER`=`waxed_exposed_copper`、`OLD_COPPER_CUT`=`waxed_exposed_cut_copper`(+stairs/slab)：`mat("old_copper")` 重画（檐沟/泛水，和模型旧铜色阶接得上）。**注意**：这是显式重画 `waxed_exposed_*`；不碰 `waxed_oxidized_*`/`waxed_weathered_*`。重画前檐沟用原版色占位（R1）。

**小件**：`WAINSCOT`=dark_oak_trapdoor（护墙板，`dark_wood`，R1 定专用，A7 不当活板门）、`BRASS_INLAY`=yellow_carpet（地面黄铜子午嵌线）、`ENAMEL_SIGN`=oak_sign 族（搪瓷铭牌，`enamel`+`cream`，文字只数字/符号/少量英文）。

---

## 7. 接口与依赖

- 色板 `common/palette.py`（A0）；占用表 `common/blocks.py`（A0）；骨架 `common/skeleton`（c188/common 在写，没出来前用 R1 第 0.3 节的数写成模块顶常量）。
- 资源包组装：材质部分暴露 `write_pack(pack_dir)`，由总场景 `obs` 调；贴图/模型放 `c164:` 命名空间 materials 子目录，不与别包写同名文件（`tools/check.py` 会查）。
- A2（sky）：亮窗/灯的隐形世界光源摆放与分级；定稿光线（材质板要在定稿光下出图）。
- A6（props）：门扇/窗框/灯具模型用 `common/palette` 取色，16px 一致；windows 卡与 A6 对窗棂分工。materials↔props 互为交叉看。
- A3（main）：线脚几何承载石材贴图；门洞留洞与挂点。
- A8（motion）：动画面板帧率/节奏。

实体预算：材质基本是方块，极少实体（仅材质板摆样例用）。遵守 R1 第 0.4 节总预算。

---

## 8. 工作包（卡片在 `plan/packages/materials/`）

| 包 | 内容 | 优先级 | 版本 | 依赖 |
| --- | --- | --- | --- | --- |
| `respack-redirect` | `redirect_block` 工具 + 材质 `write_pack` 组装 + `sounds.json` 脚手架 | P1 | 1 | palette/blocks(已就位) |
| `ashlar` | 灰白石四种（重定向，逐面贴图，变体覆盖楼梯台阶墙）+ 原版砂岩对照 | P1 | 3（含原版对照） | respack-redirect |
| `windows` | 亮窗暗窗六种（块+板，窗棂，发光 vs 映天色） | P1 | 亮窗 2 | respack-redirect, C |
| `iron` | 铸铁十二种（重定向 + 灯件发光） | P2（样板段要用，偏高） | 1 | respack-redirect |
| `panels` | 仪表面板十六种（重定向，facing 正面，4 带动画） | P2 | 1 | respack-redirect, D |
| `brass-oldcopper-small` | 黄铜族 + 旧铜 + 小件 + 脚步声（第二批） | P2 | 1 | respack-redirect, E |

---

## 9. 验收（方案 6.4 + RUBRIC 质感项）

20 格外认得出材质；8×8 平铺不起条纹；相邻材质不打架；颜色全在色阶内（`strays` 自查）；铸铁↔铜绿、旧铜↔暗铜分家正确（并排图）；亮窗自发光、暗窗映天、窗棂成网；面板朝向可控、动画面板在动；黄铜脚步金属声、无外来音频。每次交付带离线自查图并与原版/上一版并排，对着 RUBRIC 先自评到线再交。

---

## 10. 进度

- [x] 通读方案/工具链/游戏文件/流水线/R1，定技术路线
- [x] 查实非蜡↔蜡封共享、砂岩族顶面共享、light_emission、pane/terracotta 模板、脚步声事件
- [x] 对齐 R1：石材改为重定向（第 3 节重写）；取色走 common；面板用色；旧铜第二批；strays 自查；测试场景改 `obs_mat_*`
- [x] 交细化稿（本文件）
- [ ] 切卡并发【立项】；领 `respack-redirect` 开工
- [ ] `redirect_block` + 材质 `write_pack`（公共工具单独提交请 c188 优先合并）
- [ ] `ashlar`（3 版）、`windows`（亮窗 2 版）出 M1 材质板
- [ ] `iron`、`panels`、`brass-oldcopper-small`
