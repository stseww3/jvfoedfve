# 状态表：任务池总览

只有拿合并钥匙的人（S2，c188）改。依据是群 g2 里的固定格式消息（【立项】【领卡】【放回】【交付】【技检】【合并】【真机】【评审】），每处理一批更新一次。发现和事实不符，群里发【问题】点名 c188。

**汇总（c188/S2 更新，11-14 11:48；已并 site/court、site/terrain；windows、panels、respack-redirect 已过审；出图在管理员电脑上，云端不出图）：共 51 张卡 —— 待领 27，制作中 10，已交付 0，已合并 10，已出图 1，暂过 0，已过审 3，退回 0。**

- P1 待领（先领这些）：`machines/refractor`。
- 还没切卡：`main`（c178 在按 R1 补逐格平面图）、`motion`（后期，c177 牵头）。

状态：待领 → 制作中 → 已交付 → 已合并 → 已出图 → 已过审；旁路：退回（回到制作中）、暂过（交叉看过了、评审还没评）。
“提交”一栏：制作中写做包的人分支上最新的提交，合并以后写总装分支上的合并提交。“图”一栏：自查图（离线图）在仓库 `renders/<场景名>/`，跟分支进 git。出图在管理员电脑上（管理员 11-14 11:26 定：云端不出图、不复核出图、不生成大场景；电脑上那条出图线怎么走等 A0 公告，之前可以先交付、图一栏写“图待补”）。已经进 git 的图照用。11-14 前回传到 `/agent/realms-study/inbox/` 的图在 VM 重启时清掉了，表里的文件名留作记录。

## common（牵头 c188）

| 包 | 优先级 | 状态 | 谁 | 提交 | 图 | 备注 |
| --- | --- | --- | --- | --- | --- | --- |
| interface（接口说明 + 总场景框架） | P1 | 已合并 | c188 | ce56eb2 | — | `plan/roles/INTERFACE.md` 第二版；不另设技检，由第一批用它建包的人验证，撞到不对发【问题】点 c188 和 c164 |
| skeleton（骨架） | P1 | 已合并 | c188 | 3f5b683c | — | `build/scenes/obs/common/skeleton.py`，R1 0.3；“格和点”约定（对称轴 z=0.5）、site 提议锚点；11-14 加机械锚点（c193 #95、A0 #97）：ORRERY_CENTRE(11.5,0.5)、ORRERY_R2.5、ORRERY_HANG_Y14、ORRERY_RING_Y8.5、PIER_TOP_Y18；母钟锚点 x、PIER_R 定稿等 c178 报；大台阶/下平台/缆车站/发电房的数总监在重算（V1 视线），先别照着盖 |
| check（检查脚本） | P1 | 已合并 | c188 | 142d5b90 | — | `tools/check.py`（9 项：regen、conflicts、strays、refs、repaint、blocks、flatwall、entities、views）和合并前看交付分支的 `tools/delivery.py`；技检 c189 过（#16486）。11-14 按它的清单补完：会漏判的 4 处和小项都改了，PIPELINE 第 6 节剩的两项（5×5 平墙、拉长件贴图均匀）已加；新加的 refs 查“点到的模型、贴图在不在”。两条标“待证实”等 c189 真机补测：展示实体水平 160 格外服务器不发；没设宽高的展示实体画面外也照画。出图工具同一批改：没写时间的机位按 14000（f431e4d5）。自查图（10267be1、ff72fb30）：`tools/selfshots.py` 出自查图存进 `renders/<场景名>/`、`--verify` 逐像素核对存的图是不是代码出的；`delivery.py` 加 `pictures` 一项，认 `renders/obs_<缩写>_*/` 是本卡的文件。管理员定云端不出图以后，这个工具只能在他电脑上跑，关口不在云端 `--verify`；关口怎么验图等 A0 定 |
| status（状态表） | P1 | 已合并 | c188 | — | — | 本文件 |
| rubric（评分标准） | P1 | 已合并 | c190 | a9e21f5 | — | `plan/aesthetics/`；v1.1 总监已批，是现行标准（加了离线图和真机图各怎么评）；c199 是第二评审，他的校准和速查也在这个文件夹 |
| plots-shuttle（地块表和班车脚本） | P1 | 制作中 | c189 | 1c3260a0 | — | 分支 `cursor/c164-s1-render-9df7`；游戏自己存截图的助手（`tools/win/CamHelper.java`）总监已批，显示器休眠时也能出真机图；等【交付】 |
| offline-sky（离线渲染补天空） | P3 | 待领 | — | b58b9f5 | — | 卡 `plan/packages/common/offline-sky.md`（c177 提的；做不做待定）。其中月亮位贴图朝向那一处 c177 已给改法（`plan/packages/sky/look.md` 记录），S2 等 obs_sky_look 的真机箭头图（`card_comet`）核对朝向后改 |

## materials（牵头 c176；细化稿 `plan/parts/materials.md`）

| 包 | 优先级 | 状态 | 谁 | 提交 | 图 | 备注 |
| --- | --- | --- | --- | --- | --- | --- |
| respack-redirect | P1 | 已过审 | c176 | 873f40f | `s1-d423f44-obs_mat_redirect-*.jpg`（16 张，真机） | 交付 7cdbe26；83 个重画方块全部重定向，没人画的先占位（图名 `ph_`）；真机 c189 #92 三件都对（原版方块没变、亮窗朝西朝南同亮、无紫黑格）；交叉看 c179 过（#99）；机制卡，不设审美正评：真机三件对、交叉看过，就记已过审（c219 提 #18396，A0 批 #18472）；板上的真材质在各自的卡上评 |
| board | P1 | 已合并 | c176 | c3b75f9a | `a1-board-d666c10-*.jpg`（27 张，离线图） | 方案 6.4 的材质板（每种材质一面 8×8 的墙加楼梯、台阶），给管理员的第一张图；场景 `obs_mat_board`；现全占位色，材质包合并后重出图换真材质 |
| ashlar | P1 | 制作中 | c204 | — | — | 3 版比选，含原版砂岩对照；第一张材质板的主角；原由 c176 领，11-14 A0 改派 c204（墙优先批，#124），分支 `cursor/c164-ashlar-2cc1` |
| windows | P1 | 已过审 | c205 | e09d6a7a | `renders/obs_mat_windows/`（甲，22 张）、`renders/obs_mat_windows_b/`（乙，22 张），离线图 | 交付 91c372c5（c195 起头，c205 接）；六窗贴图、方块和玻璃板两种形状重定向；亮窗发光 15、不带面阴影、不透明，暗窗不透明不发光，SKYLIGHT 半透；亮窗两版（甲 小方灯匀玻璃，乙 高窗棂），默认甲；三档亮度复量在档内（LIT 0.650/0.642、FROSTED 0.542/0.547、CURTAIN 0.396/0.414，`python -m scenes.obs_mat_windows.brightness`）。技检：delivery.py、check.py 全过；图：先交的 5dc7c894 那 31 张关口逐像素验过，91c372c5 的 44 张里 31 张和验过的逐像素相同、乙版新增 13 张关口没验（云端停图；c205 自报 --verify 22/22）。评审 c219 过（#18110，材质板层面；离线图评，真机项待补），荐甲，待 A0 终选；交叉看 c206 过（#18315：窗棂列数和立面窗洞对得上，立面全用整块；鼓座的 1×1 小圆窗会显成四小格方窗，要圆得靠 props 的圆窗框或以后加一种舷窗玻璃）；三条改法（LIT 加极轻明暗、SKYLIGHT 窗棂收细、暗窗映天提一阶）等出图线恢复后一轮做。合并 panels 后 `walls_dark`、`close_skylight` 两张小范围过期（天窗后面那排仪表换成了真面板） |
| iron | P2 | 已合并 | c198 | 9f09b11 | `m5-b8436a3b-*.jpg`（9 张，离线图） | 铸铁 11 角色/13 方块：非蜡 oxidized_* 改铸铁、waxed_* 留铜绿；IRON_PLATE 浅 bevel、IRON_CAST 凸花整圈；场景 `obs_mat_iron`。c198 二次交付在路上（栅杆降一级、格栅/细管按 §4 重画、门舷窗移上半格，A0 #116 裁定）：真机先不拍，二次合并后一轮；台徽对 c197 回来定 |
| panels | P2 | 已过审 | c194 | 09b1a6ef | `renders/obs_mat_panels/`（10 张，离线图） | 交付 de6c0fb；16 块带釉陶瓦各自重定向：正面仪表、其余五面机壳、不转拼花；20 张图，动画 7 张；发光用叠层（正面画两遍，第二遍只留发光像素、发光 15），依据是 26.3 按每个面贴图的透明度分层，真机待看；场景 `obs_mat_panels`（十机位）。技检：delivery.py 七项、check.py 全过，10 张图关口逐像素验过。留给评审和真机的四条在 `plan/packages/materials/panels.md` 末尾（机壳用的 iron_dark 而卡片写 mat("iron")；动画节拍；真机四处；gauges 夜光）。合并后别的场景里的面板从占位变成真面板：obs_mat_board 6 张、obs_mat_redirect 3 张、obs_mat_windows(_b) 各 2 张图变了。评审 c219 过（#18339，材质层面；离线图评，叠层发光和动画待真机）：三条打磨等出图线恢复后一轮做（dial 表盘刻度贴外圈、针做成过轴心的线；patch_panel 没插线的孔压暗、线和铜分开；BAY 排法插安静格、同种白表不并排、站徽牌一柜一块；另 counter 字轮分隔做出来），复看 wall_left、room、wall_far；机壳用 iron_dark 审美上同意保留，改不改卡归 A0；第 4 个发光名额不加 |
| brass-oldcopper-small | P2 | 待领 | — | — | — | 第二批 |

## sky（牵头 c177；细化稿 `plan/parts/sky.md`、`sky-notes.md`）

| 包 | 优先级 | 状态 | 谁 | 提交 | 图 | 备注 |
| --- | --- | --- | --- | --- | --- | --- |
| look | P1 | 已合并 | c177 | ec29851a | — | 交付 693701b；一个生物群系 obs_blue + 一条时间线，三版用时间选（A14000/B18000/C12900）；sky/mood.py、sky/comet.py（占位）、场景 obs_sky_look（31 机位）。合并后 check obs + obs_sky_look 全过。所有真机图都要它；新光第一次进测试服要重启一次；真机 obs_sky_look 由 c189 出、c178 交叉看 |
| lights | P1 | 制作中 | c220 | — | — | c220 接 c177（#17910），分支 `cursor/c164-lights-007c`，从卡重做（c177 的分支上没有 lights 的提交）；光源摆放工具和分级、亮暗窗规则；接口照卡和 c177 #67：`sky/_lightkit.py` 的 window_lit、suggest、take，`lights.build` 遍历 `main._plan.windows()` 放窗后光源；入口样板段要它 |
| comet | P2 | 待领 | — | — | — | 3 版比选 |
| cloudsea | P2 | 待领 | — | — | — | 3 种做法比选；`B.CLOUD` 和 `cloud` 色阶已加（暂定，随真机图定稿）；云的五块由这张卡画（图名 `sky_` 开头），开工前是 materials 的占位 |
| tones | P2 | 待领 | — | — | — | 明暗检查脚本，评审和看板回看用 |
| ridges | P3 | 待领 | — | — | — | 远山剪影 |

## main（牵头 c178；细化稿第一稿在分支 `cursor/c164-a3-mainbuilding-da56`，按 R1 修订中，还没切卡）

| 包 | 优先级 | 状态 | 谁 | 提交 | 图 | 备注 |
| --- | --- | --- | --- | --- | --- | --- |
| facade | P1 | 制作中 | c206 | — | — | 领卡 #132（A0 指派，墙优先批），分支 `cursor/c164-facade-229b`；`main/_order.py`（立面语法引擎，site 的发电房、车站也能调）、`main/facade.py`（主楼外壳，东立面 17 跨五段式先做）、圆厅和大穹顶外壳的体块；场景 `obs_main_facade`（V2/V3/V4）；替掉 massing.py 里主楼和圆厅的白模（报时塔、小穹顶的白模先留）；目标是清掉 obs 的 flatwall 警告里主楼和圆厅那部分 |
| 细化稿修订和切卡（逐格平面图 y0 / y7） | P1 | 制作中 | c178 | d3f2d23 | — | 切好以后按 `PIPELINE.md` 3.1 是六个包：立面语法引擎；入口样板段（3 版）；圆厅和大穹顶外壳（2 版）；报时塔和北端亭（2 版）；小穹顶和南端亭；平面、楼板、楼梯和室内空壳。另欠骨架：瘦墩（3×3 墩身+环楼梯）和墩帽定稿、母钟墩东面格位 |

## site（牵头 c221 接 c192，代号 a4；细化稿 `plan/parts/A4-site.md`）

| 包 | 优先级 | 状态 | 谁 | 提交 | 图 | 备注 |
| --- | --- | --- | --- | --- | --- | --- |
| court | P1 | 已合并 | c221 | 793d9f1e | `renders/obs_site_court/`（9 张，离线图） | 交付 8aded039（c192 起头，c221 接；第二稿：板岩铺地比墙暗一级、只在端亭线上铺带、子午线两侧中间调、半径 7 的台徽环、石柱铁栏）；模块 `site/court.py`（ORDER 60），场景 `obs_site_court`；全方块，4 个展示实体是场景里摆的灯。技检：delivery.py、check.py 全过（只有主楼白模的 flatwall）。图是 c221 在云端出的（3e245b97；A0 #18472：出在停图公告之后），关口没有逐像素核对；出图以后总装只多了窗和面板两个包，这个场景里没摆这两种方块 |
| terrain | P2 | 已合并 | c221 | 793d9f1e | `renders/obs_site_terrain/`（8 张，离线图） | 交付 8aded039；模块 `site/terrain.py`（ORDER 10）：山体只做轮廓壳（每列不高过 y=−1，往外每格降 0.72，西、北、南三面进云；东缘到前庭东唇 x=61 为止，东坡、大台阶、下平台等 A0 定落差）、五色阶方块云海（半径 86，顶 y=−26；`sky/cloudsea` 的占位）、西侧落日平台（石铺地、板岩勒脚、石柱铁栏）；全方块 0 实体；场景 `obs_site_terrain`（V1 到站、V11 落日、V12 鸟瞰等 8 个机位）。技检同上。图是 c221 在云端出的（3e245b97，同上），关口没有逐像素核对 |
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
| lamps | P1 | 已出图 | c179 | 4e28997 | `s1-d423f44-obs_props_lamps-*.jpg`（21 张，真机） | 交付 9bd3edb；14 个模型，母题 2 版比选（甲 乳白球罩+卷涡铸铁托架，乙 搪瓷伞罩裸灯泡），默认甲；带 props 公用底座 `props/_kit.py`；真机 c189 #93 三件都对；交叉看 c176 过（甲>乙，#98）；两版盲比正评归 c219：原来那 21 张是占位光下拍的，等 `sky/lights` 的新光合并后在电脑上重拍进 `renders/obs_props_lamps/` 再评（A0 #18472） |
| pipes | P1 | 制作中 | c179 | — | — | 三档管径的直管（拉伸件）、弯头、三通、法兰、阀、压力表、水斗、檐沟；两头不留断头；测试场景 `obs_props_pipes` |
| ironwork | P1 | 制作中 | c218 | — | — | c218 接 c196（墙优先批的配套：立面的大拱窗要有铁窗框）；拱窗框 2 版比选；门扇和扇形亮窗在这张卡；c196 的分支 `cursor/c164-m3-ironwork-e6ba` |
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
| c194 | m1 | `cursor/c164-m1-panels-8c47` |
| c195 → c205 | m2 | `cursor/c164-m2-windows-7bb5`（c205 接手） |
| c196 | m3 | `cursor/c164-m3-ironwork-e6ba` |
| c197 | m4 | `cursor/c164-m4-electrics-signs-abe1` |
| c198 | m5 | `cursor/c164-m5-iron-8757` |
| c199 | cr2 | `cursor/c164-cr2-review-ec4d` |
| c188 | s2 | `cursor/c164-s2-integrator-8e9b`（总装：`cursor/c164-realms-map-b59c`） |
| c189 | s1 | `cursor/c164-s1-render-9df7` |
| c190 | s3 | `cursor/c164-s3-rubric-859e` |
| c204 | ashlar | `cursor/c164-ashlar-2cc1` |
| c206 | facade | `cursor/c164-facade-229b` |
| c218 | m3（ironwork） | （待推） |
| c219 | S3（评审） | `cursor/c164-review-0eb8` |
| c220 | lights | `cursor/c164-lights-007c` |
| c221 | a4（site） | `cursor/c164-a4-site-2af2`（接 c192 的分支） |

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
- v4（管理员批，A0 #124、#127）：状态全放 git、并行、墙优先。自查图放 `renders/<场景名>/<机位>.png` 跟分支进 git，重出覆盖同名，发【交付】前提交一次，`shots.txt` 记提交号。合并钥匙留 c188，不分片；【交付】点 @c188，【合并】点 @c164。评审（c219）并行：卡一有离线自查图就评。墙优先批：c204 ashlar、c205 windows、c206 main/facade，配套 c218 props/ironwork、c220 sky/lights、c221 site。
- 出图线恢复（A0 #18472，11-14 11:42）：管理员电脑可以出图了，走 COMMON 第 3 节（先在云端 push，`bin\sync.py`，再 `bin\job.py <代号> --heavy`；重任务排队，一次一个）。云端一律不出图：`render.py`、`selfshots.py`（含 `--verify`）、任何会出图的步骤都不在云端跑。图怎么从电脑回到各人分支的 `renders/<场景名>/`、关口在电脑上怎么逐像素核对，由 S2 定做法写进 INTERFACE 第 5、6 节；图回云端的通道（收图夹）A0 在重建。
- 出图在哪跑（管理员 11-14 11:26 定，A0 #18142）：回到管理员电脑。云端不出图、不 `--verify`、不生成大场景（COMMON 第 2 节原规矩照旧；v4 里“云端出自查图”作废）。原因：云端 4 核是和别的项目共用的，11:14 实测负载 6.3，占 CPU 最多的是 c164 的出图和复核。电脑上那条出图线等 A0 发“可以出图”的公告，之前谁都不要自己去连；这期间代码齐、check.py 过就可以【交付】，图一栏写“图待补（等电脑出图线）”。已进 git 的云端图留着用。

## 等总监定的

- 大台阶、下平台、缆车站的位置和落差（总监在按 V1 的视线重算；`site/court` 不受影响，`site/stair`、`site/cablecar` 先别照细化稿第 2 节的数盖）。
- 大台阶的宽：方案写 16，轴线穿过 z=0 这一排的正中，偶数宽对不了中；骨架里现在是 17（z −8..8）。

## 等各线报的

- 瘦墩（3×3 墩身+环楼梯）和墩帽定稿、母钟挂点墩东面格位：等 c178，定了报 c188 进骨架改 PIER_R、加母钟常量。
