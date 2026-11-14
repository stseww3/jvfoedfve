# 状态表：任务池总览

只有拿合并钥匙的人（S2，c188）改。依据是群 g2 里的固定格式消息（【立项】【领卡】【放回】【交付】【技检】【合并】【真机】【评审】），每处理一批更新一次。发现和事实不符，群里发【问题】点名 c188。

**汇总（c188/S2 更新，11-14 10:05；VM 重启后恢复，合并钥匙已从 A0 接回，已并 sky/look；检查脚本和出图工具按 c189 的技检补完）：共 50 张卡 —— 待领 28，制作中 12，已交付 0，已合并 8，已出图 2，暂过 0，已过审 0，退回 0。**

- P1 待领（先领这些）：`machines/refractor`。
- 还没切卡：`main`（c178 在按 R1 补逐格平面图）、`motion`（后期，c177 牵头）。

状态：待领 → 制作中 → 已交付 → 已合并 → 已出图 → 已过审；旁路：退回（回到制作中）、暂过（交叉看过了、评审还没评）。
“提交”一栏：制作中写做包的人分支上最新的提交，合并以后写总装分支上的合并提交。图在 `/agent/realms-study/inbox/`。

## common（牵头 c188）

| 包 | 优先级 | 状态 | 谁 | 提交 | 图 | 备注 |
| --- | --- | --- | --- | --- | --- | --- |
| interface（接口说明 + 总场景框架） | P1 | 已合并 | c188 | ce56eb2 | — | `plan/roles/INTERFACE.md` 第二版；不另设技检，由第一批用它建包的人验证，撞到不对发【问题】点 c188 和 c164 |
| skeleton（骨架） | P1 | 已合并 | c188 | 3f5b683c | — | `build/scenes/obs/common/skeleton.py`，R1 0.3；“格和点”约定（对称轴 z=0.5）、site 提议锚点；11-14 加机械锚点（c193 #95、A0 #97）：ORRERY_CENTRE(11.5,0.5)、ORRERY_R2.5、ORRERY_HANG_Y14、ORRERY_RING_Y8.5、PIER_TOP_Y18；母钟锚点 x、PIER_R 定稿等 c178 报；大台阶/下平台/缆车站/发电房的数总监在重算（V1 视线），先别照着盖 |
| check（检查脚本） | P1 | 已合并 | c188 | 142d5b90 | — | `tools/check.py`（9 项：regen、conflicts、strays、refs、repaint、blocks、flatwall、entities、views）和合并前看交付分支的 `tools/delivery.py`；技检 c189 过（#16486）。11-14 按它的清单补完：会漏判的 4 处和小项都改了，PIPELINE 第 6 节剩的两项（5×5 平墙、拉长件贴图均匀）已加；新加的 refs 查“点到的模型、贴图在不在”。两条标“待证实”等 c189 真机补测：展示实体水平 160 格外服务器不发；没设宽高的展示实体画面外也照画。出图工具同一批改：没写时间的机位按 14000（f431e4d5） |
| status（状态表） | P1 | 已合并 | c188 | — | — | 本文件 |
| rubric（评分标准） | P1 | 已合并 | c190 | a9e21f5 | — | `plan/aesthetics/`；v1.1 总监已批，是现行标准（加了离线图和真机图各怎么评）；c199 是第二评审，他的校准和速查也在这个文件夹 |
| plots-shuttle（地块表和班车脚本） | P1 | 制作中 | c189 | 1c3260a0 | — | 分支 `cursor/c164-s1-render-9df7`；游戏自己存截图的助手（`tools/win/CamHelper.java`）总监已批，显示器休眠时也能出真机图；等【交付】 |
| offline-sky（离线渲染补天空） | P3 | 待领 | — | b58b9f5 | — | 卡 `plan/packages/common/offline-sky.md`（c177 提的；做不做待定）。其中月亮位贴图朝向那一处 c177 已给改法（`plan/packages/sky/look.md` 记录），S2 等 obs_sky_look 的真机箭头图（`card_comet`）核对朝向后改 |

## materials（牵头 c176；细化稿 `plan/parts/materials.md`）

| 包 | 优先级 | 状态 | 谁 | 提交 | 图 | 备注 |
| --- | --- | --- | --- | --- | --- | --- |
| respack-redirect | P1 | 已出图 | c176 | 873f40f | `s1-d423f44-obs_mat_redirect-*.jpg`（16 张，真机） | 交付 7cdbe26；83 个重画方块全部重定向，没人画的先占位（图名 `ph_`）；真机 c189 #92 三件都对（原版方块没变、亮窗朝西朝南同亮、无紫黑格）；交叉看 c179 过（#99）；待 c190/c199 正评 |
| board | P1 | 已合并 | c176 | c3b75f9a | `a1-board-d666c10-*.jpg`（27 张，离线图） | 方案 6.4 的材质板（每种材质一面 8×8 的墙加楼梯、台阶），给管理员的第一张图；场景 `obs_mat_board`；现全占位色，材质包合并后重出图换真材质 |
| ashlar | P1 | 制作中 | c176 | — | — | 3 版比选，含原版砂岩对照；第一张材质板的主角；总监 00:53 指派给 c176 |
| windows | P1 | 制作中 | c195 | 7451ab80 | — | 分支 `cursor/c164-m2-windows-7bb5`（重启后重建）；亮窗 2 版、六种窗；亮窗发光 15、不带面阴影、不要角落变暗、贴图不透明；暗窗不透明不发光；SKYLIGHT 不透明度 0.5；还差亮窗三档云端复量、场景 obs_mat_windows、check.py |
| iron | P2 | 已合并 | c198 | 9f09b11 | `m5-b8436a3b-*.jpg`（9 张，离线图） | 铸铁 11 角色/13 方块：非蜡 oxidized_* 改铸铁、waxed_* 留铜绿；IRON_PLATE 浅 bevel、IRON_CAST 凸花整圈；场景 `obs_mat_iron`。c198 二次交付在路上（栅杆降一级、格栅/细管按 §4 重画、门舷窗移上半格，A0 #116 裁定）：真机先不拍，二次合并后一轮；台徽对 c197 回来定 |
| panels | P2 | 制作中 | c194 | — | — | 领卡 #17405；16 仪表面板（V10 仪表墙）；照 iron 的 redirect 口径，釉陶每块重定向，facing(south) 放仪表贴图、其余五面 iron 机壳；4 块带动画；交叉看找 props |
| brass-oldcopper-small | P2 | 待领 | — | — | — | 第二批 |

## sky（牵头 c177；细化稿 `plan/parts/sky.md`、`sky-notes.md`）

| 包 | 优先级 | 状态 | 谁 | 提交 | 图 | 备注 |
| --- | --- | --- | --- | --- | --- | --- |
| look | P1 | 已合并 | c177 | ec29851a | — | 交付 693701b；一个生物群系 obs_blue + 一条时间线，三版用时间选（A14000/B18000/C12900）；sky/mood.py、sky/comet.py（占位）、场景 obs_sky_look（31 机位）。合并后 check obs + obs_sky_look 全过。所有真机图都要它；新光第一次进测试服要重启一次；真机 obs_sky_look 由 c189 出、c178 交叉看 |
| lights | P1 | 制作中 | c177 | — | — | 领卡 #91；光源摆放工具和分级、亮暗窗规则；第一个提交 sky/_lightkit.py（window_lit、suggest、take）；入口样板段要它 |
| comet | P2 | 待领 | — | — | — | 3 版比选 |
| cloudsea | P2 | 待领 | — | — | — | 3 种做法比选；`B.CLOUD` 和 `cloud` 色阶已加（暂定，随真机图定稿）；云的五块由这张卡画（图名 `sky_` 开头），开工前是 materials 的占位 |
| tones | P2 | 待领 | — | — | — | 明暗检查脚本，评审和看板回看用 |
| ridges | P3 | 待领 | — | — | — | 远山剪影 |

## main（牵头 c178；细化稿第一稿在分支 `cursor/c164-a3-mainbuilding-da56`，按 R1 修订中，还没切卡）

| 包 | 优先级 | 状态 | 谁 | 提交 | 图 | 备注 |
| --- | --- | --- | --- | --- | --- | --- |
| 细化稿修订和切卡（逐格平面图 y0 / y7） | P1 | 制作中 | c178 | d3f2d23 | — | 切好以后按 `PIPELINE.md` 3.1 是六个包：立面语法引擎；入口样板段（3 版）；圆厅和大穹顶外壳（2 版）；报时塔和北端亭（2 版）；小穹顶和南端亭；平面、楼板、楼梯和室内空壳。另欠骨架：瘦墩（3×3 墩身+环楼梯）和墩帽定稿、母钟墩东面格位 |

## site（牵头 c192，代号 a4；细化稿 `plan/parts/A4-site.md`）

| 包 | 优先级 | 状态 | 谁 | 提交 | 图 | 备注 |
| --- | --- | --- | --- | --- | --- | --- |
| court | P1 | 制作中 | c192 | — | — | 前庭铺地、黄铜子午线（x=35）、中央台徽嵌花、东缘栏杆；全方块，0 实体 |
| terrain | P2 | 待领 | — | — | — | 山体轮廓和云线；西侧落日平台外壳 |
| stair | P2 | 待领 | — | — | — | 大台阶、挡土墙、下平台铺地 |
| powerhouse | P2 | 待领 | — | — | — | 发电房外壳、烟囱、管桥；2 版比选（室内归 `interiors/powerhouse`） |
| cablecar | P2 | 待领 | — | — | — | 缆车站外壳和铁栈桥；出生点 |
| outbuildings | P2 | 待领 | — | — | — | 子午仪小屋、水塔、气象站、观景台的外壳和平台 |
| mastbase | P3 | 待领 | — | — | — | 无线电桅杆的石台基座和拉索锚（桅杆铁构归 machines） |

## machines（牵头 c193，代号 a5；细化稿 `plan/parts/A5-machines.md`）

实体预算 machines ≤ 400，各卡的份额在细化稿第 2 节。

| 包 | 优先级 | 状态 | 谁 | 提交 | 图 | 备注 |
| --- | --- | --- | --- | --- | --- | --- |
| orrery | P1 | 制作中 | c193 | — | — | 大行星仪，星厅主角（V7）；2 版比选；测试场景 `obs_mach_orrery`；锚点已进骨架（ORRERY_CENTRE/R/HANG_Y/RING_Y），可改读骨架 |
| refractor | P1 | 待领 | — | — | — | 大折射望远镜，大圆顶室主角（V8）；2 版比选；锚点 DOME_AXIS + PIER_TOP_Y 已在骨架 |
| clocks | P2 | 待领 | — | — | — | 母钟、塔钟、报时球 |
| domegear | P2 | 待领 | — | — | — | 穹顶机构：轨道和滚轮、开缝链条和配重、手摇绞盘 |
| engine-dynamo | P2 | 待领 | — | — | — | 蒸汽机和发电机（发电房） |
| switchboard-boiler | P2 | 待领 | — | — | — | 配电板和锅炉（发电房） |
| cablecar-winch | P2 | 待领 | — | — | — | 缆车和卷扬机（缆车站） |
| radiomast | P2 | 待领 | — | — | — | 无线电桅杆 |
| meridian-astrograph | P2 | 待领 | — | — | — | 子午环（子午仪小屋）和天体照相仪（小穹顶） |
| recorders | P2 | 待领 | — | — | — | 记录仪器（授时室） |

## props（牵头 c179；细化稿 `plan/parts/A6-props.md`）

| 包 | 优先级 | 状态 | 谁 | 提交 | 图 | 备注 |
| --- | --- | --- | --- | --- | --- | --- |
| lamps | P1 | 已出图 | c179 | 4e28997 | `s1-d423f44-obs_props_lamps-*.jpg`（21 张，真机） | 交付 9bd3edb；14 个模型，母题 2 版比选（甲 乳白球罩+卷涡铸铁托架，乙 搪瓷伞罩裸灯泡），默认甲；带 props 公用底座 `props/_kit.py`；真机 c189 #93 三件都对；交叉看 c176 过（甲>乙，#98）；待 c190/c199 两版盲比正评 |
| pipes | P1 | 制作中 | c179 | — | — | 三档管径的直管（拉伸件）、弯头、三通、法兰、阀、压力表、水斗、檐沟；两头不留断头；测试场景 `obs_props_pipes` |
| ironwork | P1 | 制作中 | c196 | — | — | 拱窗框 2 版比选；门扇和扇形亮窗在这张卡；分支里带着 c179 的 `_kit` 和 lamps，合并排在 lamps 之后或一起 |
| electrics-signs | P1 | 制作中 | c197 | — | — | 样板段和星厅要的四件先做：铭牌、台徽、接线箱、瓷瓶；其余随后 |
| instruments | P2 | 待领 | — | — | — | |
| furniture | P2 | 待领 | — | — | — | `furn_bench` 先做 |
| paper | P2 | 待领 | — | — | — | `paper_star_chart` 先做 |

## interiors（牵头 c191；细化稿 `plan/parts/L7-interiors.md`）

| 包 | 优先级 | 状态 | 谁 | 提交 | 图 | 备注 |
| --- | --- | --- | --- | --- | --- | --- |
| starhall | P2 | 制作中 | c191 | ed35f57 | — | 2 版比选；盒子场景 `obs_int_starhall`；接口要对齐（见群里 S2 的说明）；井 z−3..3 留空给行星仪（中心 11.5,0.5、⌀5） |
| domeroom | P2 | 待领 | — | — | — | |
| chartroom | P2 | 待领 | — | — | — | |
| timeroom | P2 | 待领 | — | — | — | |
| powerhouse | P2 | 待领 | — | — | — | 发电房内；外壳归 site |

## motion（后期；c177 牵头）

还没有卡。`PIPELINE.md` 3.1 的包：循环框架（变换插值、计时）；声音摆放；烟和蒸汽。

## 分支

| agent | 代号 | 分支 |
| --- | --- | --- |
| c176 | a1 | `cursor/c164-a1-materials-3930` |
| c177 | a2 | `cursor/c164-a2-light-29fe` |
| c178 | a3 | `cursor/c164-a3-mainbuilding-da56` |
| c179 | a6 | `cursor/c164-a6-props-7fb0` |
| c191 | interiors | `cursor/c164-interiors-1d4a` |
| c192 | a4 | `cursor/c164-a4-site-2af2` |
| c193 | a5 | `cursor/c164-a5-machines-a70c` |
| c194 | m1 | （待推；panels） |
| c195 | m2 | `cursor/c164-m2-windows-7bb5` |
| c196 | m3 | `cursor/c164-m3-ironwork-e6ba` |
| c197 | m4 | `cursor/c164-m4-electrics-signs-abe1` |
| c198 | m5 | `cursor/c164-m5-iron-8757` |
| c199 | cr2 | `cursor/c164-cr2-review-ec4d` |
| c188 | s2 | `cursor/c164-s2-integrator-8e9b`（总装：`cursor/c164-realms-map-b59c`） |
| c189 | s1 | `cursor/c164-s1-render-9df7` |
| c190 | s3 | `cursor/c164-s3-rubric-859e` |

## 总监定过的（11-14）

- 评分标准 v1：批了，现行。
- `check.py` 由 c189 技检；接口、框架、骨架不另设关口，由第一批用它们建包的人验证。
- 占用表的 `CLOUD` 和色板的 `cloud` 色阶：批了，标“暂定”，随 `sky/cloudsea` 的比选在真机图上定稿。
- 天空贴图（`assets/minecraft/textures/environment/`）不查色板外颜色，结果里写明跳过几张。
- 真机图由游戏自己存截图（c189 的助手），显示器休眠时也能出；交付包的评审优先用真机图，真机排不上队时或各人自查用离线图，标“离线图”。
- 仓库里唯一允许的非图片二进制文件是 `tools/win/helper/*.class`：源码并排、带源码指纹、能从源码重编出一样的文件。`tools/delivery.py` 合并前会重编一遍逐字节比；别的二进制一律拦。
- 云的五个方块（`B.CLOUD`）的贴图由 sky 写，是“只有 materials 写方块贴图”的唯一例外；走 materials 的 `_kit.paint`、`_kit.redirect`，图名以 `sky_` 开头。
- 评分的“第一眼”只量一眼的可读性和吸引力，不判概念对错（已写进 RUBRIC 第 1 节）。
- 西门：批。圆厅正西底层开门通落日平台，在轴上；是次门，不做雨棚和扇形亮窗，门洞不高过底层，最多一盏三级小壁灯。
- 方块门（`IRON_DOOR`）的舷窗放上半格、对着眼高（1.62），下半格是百叶气窗。细化稿原来写的是“下半舷窗、上半气窗”，离线图上舷窗落在膝盖高，读成炉门观察孔。随 materials/iron 的补交改图，`materials.md` §4 那一行一并改（g2 #116）。
- 行星仪/望远镜锚点进骨架（c193 #95、A0 #97）：ORRERY_CENTRE(11.5,0.5)、ORRERY_R2.5、ORRERY_HANG_Y14、ORRERY_RING_Y8.5（行星/太阳灯那圈降到回廊眼高）、PIER_TOP_Y18；总装 3f5b683c。
- 合并关口：c188（S2）11-14 回岗，合并钥匙从 A0 接回（sky/look 起）；各线【交付】重新点 @c188。A0 兜底期间已代合 materials/iron（9f09b11）。

## 等总监定的

- 大台阶、下平台、缆车站的位置和落差（总监在按 V1 的视线重算；`site/court` 不受影响，`site/stair`、`site/cablecar` 先别照细化稿第 2 节的数盖）。
- 大台阶的宽：方案写 16，轴线穿过 z=0 这一排的正中，偶数宽对不了中；骨架里现在是 17（z −8..8）。

## 等各线报的

- 瘦墩（3×3 墩身+环楼梯）和墩帽定稿、母钟挂点墩东面格位：等 c178，定了报 c188 进骨架改 PIER_R、加母钟常量。
