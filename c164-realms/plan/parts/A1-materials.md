# A1 细化稿：方块材质

对应总方案 `plan/ART-PLAN.md` 第 6 节（全部）、3.1 色板、5.1 材质用处、10 验证档位、11 A1 行、12 共同规则。

状态：**待 A0 审**（审过再动手，不抢跑）。版本锁定 26.3（数据包格式 121，资源包格式 97，Java 25）。
负责人：A1。文件只改三处：`plan/parts/A1-materials.md`、`build/scenes/obs/materials/`、`build/scenes/obs_a1/`。
分支：`cursor/c164-a1-materials-3930`（worktree `/agent/repos/c164-a1`）。

本稿已把方案里每种材质对照 26.3 游戏文件逐条查实（砂岩族、非蜡 `oxidized_*` 铸铁族、玻璃、带釉陶瓦、竹子族、声音事件），下面的像素规则、占用块、同族与技术做法都是可直接落地的。

---

## 0. 一页结论

- **一条主线技术**：非蜡 `oxidized_*` 铜family 全部改成**铸铁**，带 `waxed_` 的保持**铜绿**。已查实：每个 `waxed_oxidized_*` 的 blockstate 都引用和非蜡**同一套 model/贴图**，所以唯一干净的分家点是 **blockstate 文件**——我重写非蜡块的 blockstate 指向新的 `c164:` 模型+贴图，绝不碰 vanilla 模型、vanilla 贴图、`waxed_*` 的 blockstate。这样蜡封族自动保持原版铜绿。
- **三类改法**：① 只换同名贴图（只有砂岩族能这样）；② 改 blockstate+模型并和 `waxed_` 分家（铸铁族 + 16 面板）；③ 加 `light_emission` 自发光 / 动画贴图 / `sounds.json` 改脚步声。
- **都能验**：每类都有并排出图的验收办法（第 11 节），自查用离线渲染 `build/render.py`。
- **两处占用表勘误**要 A0 定（第 12.1 节）：`cut_sandstone` 没有楼梯；`smooth_sandstone` 没有墙。
- **一个公共工具**建议 A0 合并（第 12.2 节）：`respack.redirect_block()`。

---

## 1. 总原则（守方案 6.1 / 12）

1. 一律 16 像素一格，和模型同密度。
2. 只从 3.1 色板的色阶取色；画法同原版：几个平色 + 1px 明暗，不用渐变。
3. 大面积材质至少 **3 个随机变体**，平铺 8×8 格不起条纹。
4. 贴图全部由脚本生成，可重复生成，不手工传图。
5. 占用表之外的方块不重画；被占用的方块不按原意使用。
6. 每次提交带自查图（离线渲染，和原版/上一版并排），无图不合并。
7. 全原创，无第三方贴图/音效/字体；无暴力宗教、无真实品牌机构人名；文字只用数字、符号、少量英文。

**色阶命名**（下文用缩写，索引从 0=最暗 到 顶=最亮）：
- `A` 灰白石 ashlar：`#847f77 #a09a8e #b7b0a1 #c8c1b0 #d6cfbf #e2dccd`（A0–A5）
- `I` 铸铁 iron：`#12151a #1b2027 #252b34 #303844 #414b59 #5d6877 #8591a0`（I0–I6）
- `R` 黄铜 brass：`#5a3c12 #7a551a #9c7424 #bf9433 #dcb650 #f3d98a`（R0–R5）
- `G` 灯丝琥珀 glow：`#c96a1c #f09a2e #ffc65a #ffe9a6 #fff8dc`（G0–G4）
- `P` 荧光绿 phosphor：`#0f3d2c #1c7a55 #3fd08d #8dffc4 #e3fff0`（P0–P4）
- `S` 信号红 signal：`#5e1410 #a3201a #e8402e #ff8a6a`（S0–S3）
- `E` 搪瓷蓝 enamel：`#0f1e3d #172c57 #1f3a6e #2e4f8f` + 米白 `#f2ead6`
- 暗窗玻璃 night_glass：`#141a36 #1c2548 #27335f #3a4a80 #5a6ea8`

命名空间：新贴图/模型一律放 `c164:`（和现有 `respack.cube_variants` 默认一致），vanilla 命名空间只放"要替换原版同名贴图"的那几张。

色阶权威来源：**`build/scenes/obs/common/palette.py`（由 A0 发布，含方案 3.1 色阶 + `mat(name)` 工厂）**。A1 画方块、A6 画模型都从它取色，各部分不再自建 palette。上面的缩写只是本稿引用用，落地时一律调 `common.palette.mat(...)`。（A0 2026-11-13 定）

---

## 2. 占用表逐项（方案 6.2）——石材（砂岩族）

砂岩族**没有 `waxed_` 问题**，可以"只换同名贴图"，楼梯/台阶/墙自动跟随（原版它们的模型都指向母块贴图）。

| 材质 | 占用块（含同族） | 贴图（变体数） | 图案规则（精确到像素） | 取色阶 |
| --- | --- | --- | --- | --- |
| 灰白石·粗琢面 | `sandstone` + `_stairs` `_slab` `_wall` | `block/sandstone`（替换同名，3 变体靠 blockstate 混图） | 一石一格。四周 1px 深缝=A0；主面 base=A2，随机 ±1 做粗糙凿面（约 12 条 2–3px 凿痕，上沿 A3 亮、下沿 A1 暗）；上/左内缘 +1（A3），下/右内缘 −1（A1）形成浅浮雕 | A0–A4 |
| 灰白石·细琢面 | `smooth_sandstone` + `_stairs` `_slab` | `block/smooth_sandstone`（4 变体） | 一格两层（各 8px 高），石块一格长；两层通缝 1px=A0（第 7、15 行）；竖缝每层一条、两层错开半格（下层缝在 x=7，上层缝在 x=15），1px=A1；每层整体 ±1（base A3）。4 变体循环保证 8×8 平铺竖缝左右错开、不起条纹 | A0–A4 |
| 灰白石·凹板 | `cut_sandstone` + `_slab`（**无楼梯**，见 12.1） | `block/cut_sandstone`（2 变体） | 居中下沉方板：外框 top/left 提亮 A4、bottom/right 压暗 A1；沉底 A2；最底行 A0。做窗下裙板、檐壁饰带 | A0–A4 |
| 灰白石·台徽块 | `chiseled_sandstone`（无同族） | `block/chiseled_sandstone`（2 变体：正/副） | 台徽浮雕（圆环 + 子午竖线 + 右上星）居中，底=细琢面；环/星提亮 A5，阴影 A1。用于门楣、柱头上方 | A0–A5 |

**线脚（腰线/檐口/柱础/柱头）**：优先由 A3 用本族楼梯/台阶几何 + 上面的细琢面/凹板贴图做出剖面（三层进深 + 挑檐）。若几何不足以表达线脚剖面，我另出一张 `block/ashlar_course`（水平线脚，参考 `plan/figs/draft.py` 的 `tex_moulding`），贴在指定台阶/台阶面上。这一项**与 A3 对接后再定**。

石材退路（方案 15 风险）：我会在材质板里把"自绘粗/细琢面"与"原版砂岩"并排出一张图，M1 让管理员选用自绘还是原版。

---

## 3. 占用表逐项（方案 6.2）——铸铁（非蜡 `oxidized_*` 族）

**全部走 blockstate 重定向 + 和 `waxed_` 分家**（第 8 节技术做法 B）。贴图 kind=metal、noise≈0.12–0.16。

| 材质 | 占用块（含同族） | 贴图（变体） | 图案规则（精确到像素） | 取色阶 |
| --- | --- | --- | --- | --- |
| 铸铁·平板 | `oxidized_copper`（无楼梯台阶） | `iron_plate`（3） | 平铁板，base I3，metal 刷纹极轻，四边浅 bevel（上/左 I4，下/右 I2），**无铆钉**。机壳、水箱 | I2–I5 |
| 铸铁·铆接板 | `oxidized_cut_copper` + `_stairs` `_slab` | `iron_riveted`（3，仅刷纹变化、铆钉固定） | base I3；边框 top/left I4、bottom/right I1；铆钉=1px I6 高光 + 其正下 1px I1 阴影，固定 8 点：四角 (2,2)(2,13)(13,2)(13,13) + 四边中 (7,2)(13,7)(2,8)(8,13)。铆钉贴边使相邻块连成行。梁、平台、铁楼梯 | I1–I6 |
| 铸铁·铸花板 | `oxidized_chiseled_copper`（无同族） | `iron_cast`（2） | 外框铆接边 + 中心凸起花纹（小台徽或菱形玫瑰），凸起提亮 I5、阴影 I1。栏板、铭牌座 | I1–I6 |
| 铸铁·格栅 | `oxidized_copper_grate`（镂空） | `iron_grate`（2） | 4px 网格铁条（条 I3，交点 I5），网孔 alpha=0 透空。走道、平台 | I3–I5 |
| 铸铁·门 | `oxidized_copper_door` | `iron_door_top` + `iron_door_bottom`（各 16×16，对齐成 2 格高一扇） | 铆钉包边；下半居中**舷窗**：黄铜圈 R2–R4 + 中心发光琥珀 G1–G3；上半小气窗格。发光见第 8 节 C | I1–I6 + R + G |
| 铸铁·舱盖/百叶 | `oxidized_copper_trapdoor` | `iron_trapdoor`（2：铆接盖 / 横百叶） | 铆接盖=铆接板缩到单张；横百叶=4 条横缝（缝 I0，叶面 I3，上棱 I5） | I0–I5 |
| 铸铁·栏杆 | `oxidized_copper_bars`（multipart post/side/cap） | `iron_bars`（1） | 细竖铁条（条 I2–I3，高光 I5）+ 一道横档（y≈11 行）。栏杆 | I2–I5 |
| 铸铁·细管 | `oxidized_copper_chain`（axis 三向） | `iron_chain`（1，template_chain 十字薄片） | 画成一截细管/绞合电缆：中列 I4 高光、两侧 I1–I2，每 4px 一道法兰环 I5。可朝 3 向 | I1–I5 |
| 铸铁·细杆 | `oxidized_lightning_rod`（facing 六向，用 powered=false） | `iron_rod`（1） | 一截细金属杆/导管短节，中亮 I5、边 I1。可朝 6 向 | I1–I5 |
| 铸铁·铁笼灯 | `oxidized_copper_bulb`（lit/powered 四态） | `iron_bulb` + `iron_bulb_lit`（powered/lit_powered 复用） | 铁笼罩（竖条 I2）+ 内琥珀灯泡；lit 态灯丝 G2–G4 发光（+ light_emission）。**点亮发光度 4**（原版 oxidized 档），正好做方案 5.2 的三级弱光 | I1–I3 + G |
| 铸铁·铁壳吊灯 | `oxidized_copper_lantern`（hanging true/false 两 model 共用一张） | `iron_lantern`（1） | 铁皮灯罩（I2–I3）+ 乳白/琥珀透光缝 G2–G3；发光度 15；+ light_emission。顶/底铁盖 I1 | I1–I3 + G |

**原版直接用、我不碰的**（方案 6.2 末）：深板岩族、凝灰岩族、带 `waxed_` 的铜family、深色橡木/云杉/白橡木（家具结构）、铁栏杆/铁链、山体石头/雪。——但注意"小件"里 `dark_oak_trapdoor` 要重画（第 6 节），需和 A7 确认不冲突。

---

## 4. 窗（方案 6.2 亮窗/暗窗 + 6.3 发光 + 5.1 大拱窗）

玻璃**没有 `waxed_` 问题**，但"自发光"要改模型（第 8 节 C）。亮窗三色各自发光（emissive 渲染），暗窗三色映天色、不发光。窗棂一律在贴图里画。

### 4.1 亮窗（自发光）

| 窗 | 占用块 | 贴图 | 画法 | 色阶 |
| --- | --- | --- | --- | --- |
| 普通暖亮窗（黄） | `yellow_stained_glass` + `_pane` | `block/yellow_stained_glass` + `yellow_stained_glass_pane_top` | 暖黄玻璃 G1–G3，随机格暖度 ±1；窗棂 1px I1 | G + I1 |
| 带帘影暖窗（橙） | `orange_stained_glass` + `_pane` | 同名两张 | 上 2/3 亮 G2，下 1/3 压暗（像半截窗帘）G0–G1；窗棂 I1 | G + I1 |
| 磨砂乳白窗（白） | `white_stained_glass` + `_pane` | 同名两张 | 柔和乳白（G3–G4 加去饱和），格影弱、无硬高光；窗棂 I1 | G3–G4 + I1 |

### 4.2 暗窗/天窗（映天色，不发光）

| 窗 | 占用块 | 画法 | 色阶 |
| --- | --- | --- | --- |
| 暗窗（灰） | `gray_stained_glass` + `_pane` | 斜向映天的冷反光条（左上亮 night_glass[4]，右下暗 night_glass[1]）；窗棂 I1 | night_glass + I1 |
| 百叶/深窗（黑） | `black_stained_glass` + `_pane` | 更暗，近全黑 night_glass[0–1] + 一道弱反光 | night_glass0–2 |
| 铁框天窗（浅灰） | `light_gray_stained_glass` + `_pane` | 偏亮冷反光 + 明显铁框格（天窗格较大，12px 一格） | night_glass + I1 |

### 4.3 窗棂（muntin）规则

- 贴图内 **8px 一格窗格**，窗棂 1px，色 I1。
- 整块玻璃墙平铺时窗棂连成网；一块 3 格宽拱窗（5.1）横向显示 6 列窗格。
- 贴图四边须无缝：相邻块的窗棂接缝正好合成一条线。

### 4.4 玻璃板 vs 整块玻璃两种形状

- **整块玻璃 `*_stained_glass`**：用于 5.1 的齐平大拱窗幕墙（读作一整片发光玻璃平面）。贴图平铺成窗棂网格，要求无缝。模型重定向为 `c164:` 的 `cube_all` 变体，保留 `force_translucent`，发光色加 `light_emission`（亮窗）或不加（暗窗）。
- **玻璃板 `*_stained_glass_pane`**：用于凹进的小窗、地下层铁栅后、需要薄剖面处，以及和铁栏/铁框拼接的窗。pane 的 **面贴图**（`*_stained_glass`）和 **边贴图**（`*_stained_glass_pane_top`）都要画成玻璃+窗棂；重定向 post/side/side_alt/noside/noside_alt 五个 model 到 `c164:`，亮窗同样在这些元素上加 `light_emission`，保留 `force_translucent`。

---

## 5. 16 种仪表面板（方案 6.2 面板行 + 5.3/8 授时室仪表墙）

占用 16 种 **带釉陶瓦 `*_glazed_terracotta`**（无 `waxed_` 问题）。

**做法**：重定向每种 blockstate → `c164:` 模型，模型只在**朝向那一面**放仪表贴图（直立），其余五面放铸铁机壳贴图 `iron_casing`；用 vanilla 已有的 `facing`（N/S/E/W，y 旋转）把正面对准房间。这样把原版带釉陶瓦"四块拼花"的旋转行为去掉，每块都是一台独立仪器，直立可读。参考 `plan/figs/draft.py` 的 `tex_gauge / tex_switches / tex_tubes / tex_scope / tex_counter`。

| # | 名称 | 占用块 | 画什么 | 动画 |
| --- | --- | --- | --- | --- |
| 1 | 表盘 dial | `white_glazed_terracotta` | 黄铜圈 R + 搪瓷盘 E米白 + 黑刻度 + 指针；左下双指示灯（红/绿） | 静态 |
| 2 | 闸刀 knife-switch | `orange_glazed_terracotta` | 石板底 + 三把黄铜闸刀（中间拉下）+ 下排保险丝 | 静态 |
| 3 | 电子管 vacuum tubes | `magenta_glazed_terracotta` | 守护罩后三只发光电子管（G 辉光）+ 下排旋钮 | **动画：辉光脉动** |
| 4 | 示波屏 oscilloscope | `light_blue_glazed_terracotta` | 绿圆屏 P + 网格 + 一条扫描波形；下排旋钮 | **动画：波形扫动** |
| 5 | 计数器 counter | `yellow_glazed_terracotta` | 机械数字轮（搪瓷白底黑字）+ 下排插孔 | **动画：个位跳字** |
| 6 | 接线板 patch panel | `lime_glazed_terracotta` | 端子排 R + 若干跳线（弧线）+ 编号 | 静态 |
| 7 | 保险丝盒 fuse box | `pink_glazed_terracotta` | 一排瓷保险丝（白瓷 + 铜帽）+ 盖铰链 | 静态 |
| 8 | 电铃 bell | `gray_glazed_terracotta` | 黄铜钟形电铃 R + 击锤 + 接线 | 静态 |
| 9 | 指示灯排 pilot lamps | `light_gray_glazed_terracotta` | 一排红/绿/琥珀信号灯（S/P/G）+ 搪瓷标牌 | **动画：轮流闪** |
| 10 | 通风百叶 louver | `cyan_glazed_terracotta` | 横向百叶（铸铁 I + 投影）+ 四角铆钉 | 静态 |
| 11 | 抽屉柜面 drawer | `purple_glazed_terracotta` | 卡片抽屉 + 黄铜拉手 R + 编号牌 | 静态 |
| 12 | 铭牌面板 nameplate | `blue_glazed_terracotta` | 搪瓷蓝铭牌 E + 台徽 + 数字符号（白） | 静态 |
| 13 | 继电器架 relay rack | `brown_glazed_terracotta` | 一列继电器 + 竖排接线 | 静态 |
| 14 | 母线闸 bus switch | `green_glazed_terracotta` | 大刀闸 + 母线铜排 R + 警示红点 S | 静态 |
| 15 | 压力/真空表 gauge pair | `red_glazed_terracotta` | 双圆表盘 + 红指针 S + 黄铜边 R | 静态 |
| 16 | 记录仪面 recorder | `black_glazed_terracotta` | 转鼓 + 记录纸 + 笔；暗底 | 可选**动画：笔/纸微动** |

**朝向怎么用**：墙面仪表设 `facing` 让正面朝房间；成排同 `facing` 码成整面仪表墙（V10 授时室）。四个 `facing` 覆盖四种墙向。
**动画**：#3/4/5/9 必带动画贴图，#16 可选。动画用 `.png.mcmeta` 的 `animation`（纵向堆帧 + `frametime`），帧数与节奏跟 **A8** 对齐。其余静态。

---

## 6. 黄铜（第二批，竹子族）+ 小件（方案 6.2）

**第二批**（样板段/室内用，排在石材铁件之后）。竹子族 → 黄铜，`brass` 色阶 6 级，kind=metal。脚步声改金属（第 8 节 E）。

| 黄铜件 | 占用块 | 画法要点 |
| --- | --- | --- |
| 黄铜板 | `bamboo_planks` + `bamboo_stairs` `bamboo_slab` | 竖纹黄铜板 R2–R4，接缝 R0 |
| 花纹板 | `bamboo_mosaic` + `_stairs` `_slab` | 压花黄铜（菱形/台徽纹）凸起 R5 |
| 粗管/铜柱 | `bamboo_block` | 竖黄铜粗管，中高光 R5、两侧 R1，端面法兰 |
| 栏杆 | `bamboo_fence` + `bamboo_fence_gate` | 黄铜细栏杆 + 球头 |
| 玻璃铜门 | `bamboo_door` | 黄铜框 + 磨砂玻璃芯（白 G3 去饱和） |
| 铜活板门 | `bamboo_trapdoor` | 黄铜检修盖 + 铰链 |
| 铜按钮 | `bamboo_button` | 小黄铜钮/按钮 |
| 铭牌/吊牌 | `bamboo_sign` `bamboo_wall_sign` `bamboo_hanging_sign` | 搪瓷/黄铜铭牌（台徽 + 数字） |
| 架子 | `bamboo_shelf` | 黄铜/木搁架 |
| 压板 | `bamboo_pressure_plate` | （很少用，统一金属外观） |

**小件**（原版方块改专用，注意冲突）：

| 小件 | 占用块 | 用途 | 注意 |
| --- | --- | --- | --- |
| 护墙板 | `dark_oak_trapdoor` | 室内深色木护墙板（细木纹 + 线脚） | `dark_oak` 本身是"原版直接用"的家具/墙板木料；把 `dark_oak_trapdoor` 专用于护墙板需 A7 确认不冲突（见 12.4） |
| 地面黄铜嵌线 | `yellow_carpet` | 前庭/大厅地面的子午线黄铜嵌条 | `yellow_carpet` 原版无他用，安全 |
| 搪瓷铭牌 | `oak_sign`（告示牌） | 门边搪瓷铭牌/告示 | 文字只用数字/符号/少量英文 |

---

## 7. 命名空间与文件布局

- `build/scenes/obs/materials/`（A1 代码，A0 的 `obs` 场景在 `write_pack` 里调它）：
  - **不建 palette.py**：取色一律 `from scenes.obs.common import palette`，用 A0 的 `mat(name)` 工厂（A0 2026-11-13 定）。
  - `textures.py`：各材质 16×16 贴图生成函数（石、铁、窗、面板、黄铜、小件），都带变体与 seed；取色全走 `common.palette`。
  - `blocks.py`：① 砂岩族换同名贴图（`respack.cube_variants`）；② 铸铁族 + 16 面板 blockstate 重定向；③ 玻璃发光模型；④ 动画 `.mcmeta`；⑤ `sounds.json` 脚步声。暴露 `write_pack(pack_dir)`。
  - `redirect.py`：blockstate 重定向的本地实现（在 A0 把公共版合并进 `respack` 前用，合并后切换，见 12.2）。
- `build/scenes/obs_a1/`（材质板测试场景）：`__init__.py`（`build()`+`write_pack()`+`BIOME`）、`shots.json`（材质板相机）。
- 不改公共目录：`build/artkit/`、`tools/`、`plan/ART-PLAN.md`、色板、占用表、`build/scenes/obs/common/`。需要动公共工具时单独提交，群里请 A0 优先合并。

---

## 8. 技术做法与验证（方案 6.3 + 第 10 节档位）

### A. 只换同名贴图（不改 state/model）
- **适用**：仅砂岩族（`sandstone`/`smooth_sandstone`/`cut_sandstone`/`chiseled_sandstone` + 同族楼梯台阶墙）。砂岩无 `waxed_`，楼梯/台阶/墙的原版模型都指向母块贴图，换贴图即全族跟随。多变体用 `respack.cube_variants`（按位置混图）。
- **档位**：已用过（方案 10：重画方块贴图）。
- **验**：材质板摆一面 8×8 墙 + 楼梯 + 台阶 + 墙，看三者贴图一致、平铺无条纹。

### B. 改 blockstate + 模型，并和 `waxed_` 分家
- **已查实**：`waxed_oxidized_*`（copper / cut_copper±stairs±slab / chiseled / grate / door / trapdoor / bars / chain / lantern / bulb）的 blockstate **都引用和非蜡同一套 model**（例：`waxed_oxidized_cut_copper_stairs` 和 `oxidized_cut_copper_stairs` 同指 `block/oxidized_cut_copper_stairs*`；`waxed_oxidized_copper_lantern` 同指 `block/oxidized_copper_lantern*`）。所以改 vanilla 模型或贴图都会殃及蜡封族，**只能改 blockstate**。
- **做法**：用 `artkit.gameassets.Assets`（读 jar：`/agent/realms-study/client26/versions/26.3/26.3.jar`）读非蜡块的 `assets/minecraft/blockstates/<块>.json` 及其引用的全部 model；为每个 model 生成一份 `c164:` 副本（保留 parent、把 textures 指向我的 `c164:` 铁贴图）；重写 `assets/minecraft/blockstates/<块>.json`，把每个变体的 `model` 换成 `c164:` 副本，**原样保留** `facing/half/shape/type/axis/lit/powered/hinge/open` 等所有状态键与 `x/y/uvlock/weight`。不写任何 `waxed_*` 文件、不改 vanilla 模型与贴图。
- **适用**：铸铁族 12 类 + 16 面板（面板另外把朝向面逻辑按第 5 节处理）。
- **档位**：方案 10 第二档"把方块状态改指向新模型，和同族原版分开"——文件格式查实、The Masquerade 在用，我们没试过。**M1 第一时间实测**。
- **验**：材质板上 **并排**摆"非蜡块"和它的 `waxed_` 同族块 → 非蜡=铸铁、waxed=保持铜绿；楼梯/台阶/门/灯笼/灯泡的每个状态都正确显示；再用 `gameassets` 离线渲染两者核对颜色都在色阶内。备选（若不行）：改占别的方块。

### C. 自发光字段 `light_emission`
- **已查实**：原版 `cross_emissive` 系两模型在用，是**元素级**整数 0–15；离线渲染器 `raytrace.py` 已支持（`el_emit`）。它只让该元素**渲染变亮**，不向世界发光。
- **适用**：亮窗玻璃（块 + 板的各元素）、铁笼灯/吊灯的发光件、门舷窗。做 `c164:` 模型时给发光元素加 `light_emission`（亮窗建议 10，灯件按亮度给）。世界照明（照暖窗套/壁柱）由 **A2** 的隐形 `light` 方块给。
- **档位**：方案 10 第二档"方块面自发光，自绘方块上没试过"。**M1 实测**。
- **验**：把一块亮窗放进全黑环境离线出图，玻璃应自亮且颜色正确；和"不加字段"版本、以及备选"窗后常亮模型片"并排比。

### D. 动画贴图 `.mcmeta`
- **适用**：电子管辉光、示波波形、计数器跳字、指示灯闪（+可选记录仪）。纵向堆帧，写 `{"animation":{"frametime":N,"frames":[...]}}`。
- **档位**：方案 10 第二档。**M1/M2 实测**。节奏/帧率与 **A8** 对齐（也计入每刻无开销——动画不占运算）。
- **验**：真机加载看动；改图后 F3+T 热重载确认（约 25s）。

### E. 脚步声改指向 `sounds.json`
- **已查实**：竹子族用 `block.bamboo_wood.*` 声音事件（step/hit/fall 指向 `block/bamboo_wood/step1..6`，place/break 指向 `break1..5`）；原版金属脚步文件是 `block/copper/step1..6`、`block/copper/break1..4`（还有 `copper_grate`、`chain`、`copper_bulb` 可选）。
- **做法**：在资源包 `assets/minecraft/sounds.json` 用 `"replace": true` 把 `block.bamboo_wood.step/hit/fall` 指到 `block/copper/step1..6`，`place/break` 指到 `block/copper/break1..4`；子块事件（`bamboo_wood_door/_trapdoor/_fence/_button/_pressure_plate/_hanging_sign`）同理指到对应 copper 事件。**只引用原版已有的 copper 音频文件，不加任何 .ogg**。
- **档位**：方案 10 第二档"脚步声改指向，没试过"。备选=不改。
- **验**：真机踩黄铜块/敲击听金属声；确认资源包里没有任何音频文件、只有 `sounds.json`。

---

## 9. 材质板测试场景 `build/scenes/obs_a1/`（方案 6.4 验收 + 14 M1）

一个只看材质的场景（"材质板"）：
- 每种石材/铁材一面 **8×8 墙**，配**楼梯 + 台阶 +（有墙的）墙**样例一小段。
- 铸铁族旁边**并排**摆对应 `waxed_` 铜绿块，证明分家成功。
- 亮窗三色 + 暗窗三色各一面（整块玻璃墙 + 玻璃板窗各一处），后面留位给 A2 的隐形光源。
- 16 面板码成一面仪表墙 + 单块陈列。
- 黄铜族、小件各一组（第二批补）。
- 一面"石材退路"对比：自绘粗/细琢面 vs 原版砂岩并排。
- 相机 `shots.json`：正交近景（查像素/缝/铆钉）+ 20 格外一张（查"认得出材质"）+ 整板一张。

**光线依赖**：材质板要在**定稿光**下出图（方案 14 M1）。定稿光（生物群系/时间线/雾/天光）归 **A2**、场景骨架归 **A0**（`build/scenes/obs/common/`）。在它们就绪前，我用 `skyobs` 的 `mood` 作**临时占位**出自查图（仅自查，不作定稿）；A2 的 mood 一到就切换并重出。

出图/打包命令（沿用现有工具，在管理员电脑排队跑，云端只写码）：
```
cd build && python makepack.py obs_a1 --out <client>/resourcepacks/c164art
python place.py obs_a1 --world <server>/<world> --pw-file <server>/.rcon_pw --at 0 200 0
python render.py ...   # 离线自查图
```

---

## 10. 验收标准（方案 6.4）

- 20 格外认得出是什么材质。
- 平铺 8×8 不起条纹。
- 相邻两种材质放一起不打架。
- 颜色全部落在 3.1 色阶内（脚本保证只从色阶取色；出图后再抽样核对）。
- 铸铁族与 `waxed_` 铜绿分家正确（并排图）。
- 亮窗自发光、暗窗映天色；窗棂对齐成网。
- 16 面板朝向可控、动画面板在动。
- 黄铜脚步声为金属声、无外来音频。
- 每次提交带离线自查图，与原版/上一版并排。

---

## 11. 交付物与里程碑

**交付物**（方案 11 A1 行）：材质生成脚本（`build/scenes/obs/materials/`）；资源包里的方块部分（贴图 + blockstate/模型重定向 + `sounds.json` + 动画 `.mcmeta`）；材质板场景（`build/scenes/obs_a1/`）。

**里程碑**：
- M1 基调板：先交 **石材 + 铸铁 + 亮/暗窗** 的材质板，在定稿光下出图，并附"石材退路"对比。重点实测技术做法 B/C（分家、自发光）。
- M2 样板段：配合 A3 把入口一跨三层进深的墙/窗/门/灯/管线材质全上；补 16 面板、黄铜、小件；实测动画与脚步声。
- 之后随总装铺开，按反馈单逐条改。

---

## 12. 待 A0 决定 / 勘误 / 依赖

### 12.1 占用表勘误（请 A0 更新占用表）
1. **`cut_sandstone` 没有楼梯**（原版只有 `cut_sandstone_slab`）。方案 6.2"灰白石·凹板 | cut_sandstone 及其台阶"里的"台阶（楼梯）"不存在。建议：凹板只占 `cut_sandstone` + `cut_sandstone_slab`；窗下裙板若需楼梯轮廓，由 A3 用 `smooth_sandstone_stairs`（细琢面）几何处理，或我给它一张专用贴图。
2. **`smooth_sandstone` 没有墙**（无 `smooth_sandstone_wall`）。方案没要它的墙，这里只是提请占用表措辞对齐：墙只来自 `sandstone_wall`（粗琢面）。

### 12.2 建议新增公共工具（我单独提交，请 A0 优先合并）
在 `build/artkit/respack.py` 增 `redirect_block(pack_dir, block, tex_map, ns="c164")`：读 vanilla `block` 的 blockstate + 引用模型，生成 `c164:` 副本并重写 blockstate（保留全部状态与旋转），textures 按 `tex_map` 重指向。铸铁族 12+ 类、16 面板都要用它。合并前我在 `build/scenes/obs/materials/redirect.py` 放等价实现，合并后切到公共版。

### 12.3 门舷窗发光的取舍（请 A0 在 M2 定）
`light_emission` 是整元素级，门是薄片，无法只亮舷窗一小格。拟给整扇门低 `light_emission`（≈7）让舷窗读作点亮（铁面也略亮，作为"亮着的门口"可接受）；备选=门后放 `light` 方块（A2）。M2 样板段看效果定。

### 12.4 小件 `dark_oak_trapdoor` 的归属（请 A0/A7 确认）
把 `dark_oak_trapdoor` 重画成护墙板，可能与 A7 室内家具用的深色木冲突。请确认 `dark_oak_trapdoor` 可专用于护墙板（或换占别的块）。

### 12.5 依赖
- 色板 `common/palette.py`（`mat(name)` 工厂，已确认由 A0 发布）、方块占用表、场景骨架 `build/scenes/obs/`（含 `common/`）：**A0**。各部分不自建 palette、不提占位骨架（A0 2026-11-13 定）。
- 定稿光线（mood/生物群系/时间线/雾/天光）、亮窗/灯的隐形世界光源摆放：**A2**。
- 动画帧率/节奏、每刻命令预算：**A8**。
- 门窗铁件/灯具等模型（用我的 `palette.py` 取色，保持 16px 一致）：**A6**。

---

## 13. 进度跟踪

- [x] 通读方案（6 全节 / 3.1 / 5.1 / 10 / 11 / 12）、工具链、26.3 游戏文件；定技术路线
- [x] 查实非蜡/蜡封铜族的 blockstate-model 共享关系，定"blockstate 重定向"分家法
- [x] 查实 `light_emission`（元素级）、玻璃 pane 模板、带釉陶瓦模板、竹子/铜脚步声事件
- [x] 交细化稿（本文件）← **当前，待 A0 审**
- [x] 对齐 A0 决定：取色改走 `common/palette.py`（不自建 palette）、不提占位骨架（§7/§12.5 已更新）
- [ ] A0 审核意见、占用表勘误处理
- [ ] 写 `textures.py`（石 + 铁 + 窗；取色走 `common.palette`）
- [ ] 写 `redirect.py` + `blocks.py`（分家 + 发光）
- [ ] 建 `obs_a1` 材质板 + `shots.json`，出 M1 自查图
- [ ] 16 面板 + 动画；黄铜族 + 脚步声；小件（M2）
