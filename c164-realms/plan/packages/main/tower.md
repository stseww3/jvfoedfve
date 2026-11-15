# main/tower — 报时塔和北端亭（卡片）

状态：制作中（c223 / 代号 tower，A0 指派）。对应方案：ART-PLAN §4 尺寸、§5.3 报时塔、§5.1 立面语法；细化稿 plan/parts/main.md §6.2。

## 目标

从北端亭升起的报时塔：石塔身（分段、收分、转角石，不是一根方柱）；四面钟面（石框＋占位盘面）；钟室百叶；塔顶（2 版比选）；报时球和球杆；风速计；通无线电桅杆的天线挂点。它是 V5 的主角，V1 主视觉里右侧最高的那条竖线。北端亭墙体由 c206 的立面语法（facade.py）出，本卡只做端亭屋面以上（y18 起）的塔。

## 约束

- 坐标（common/skeleton.py，LOCKED）：北端亭 z −34..−26（bays 1–2，9 宽，归 c206）；塔身 7×7，x 10..16、z −33..−27（东面 x16 与端亭墙面齐，其余三面内收 1 格）；塔身顶 CLOCK_SHAFT_TOP=31；塔顶 CLOCK_TOP=41；报时球杆 CLOCK_BALL_MAST=52。塔身站在端亭屋面（y17 deck）上，从 y18 起。
- 角色（common/blocks.py，不写原版名）：墙 ASHLAR_FINE；转角石／基座 ASHLAR_ROUGH；钟面框／键石 ASHLAR_EMBLEM；凹板／饰带 ASHLAR_PANEL；铜檐沟 OLD_COPPER_CUT；钟面占位 WINDOW_LIT（自发暖光）；钟室百叶 IRON_HATCH；敞廊栏杆 IRON_BARS；铜绿塔顶 VERDIGRIS_CUT／VERDIGRIS_STREAK；铁架塔顶 IRON_RIVETED／IRON_GRATE／IRON_BARS；球杆／避雷针 IRON_ROD、BRASS_COLUMN；报时球占位 VERDIGRIS／BRASS。线脚拼法对齐 main.md §4：挑出一律 `*_stairs[half=top,facing=向外]`，檐沟 `OLD_COPPER_CUT.slab[type=bottom]` 坐挑檐顶。
- 实体预算：本卡纯方块（build 返回 0）。报时球、风速计、钟针机芯走 machines(A5) 预算；本卡只给占位方块和挂点坐标。
- 无 >5×5 平墙：靠转角石、分段腰线、四面钟面洞、钟室百叶打断。

## 交付物

- 代码：`build/scenes/obs/main/tower.py`——`build(canvas, origin=(0,0,0), version="a")`，纯占用表方块，无 models/pack。
- 测试场景：`obs_main_tower`——并排出两版塔顶，另接真 facade 做「和主楼交接」背景。
- 落地后：撤掉 `main/massing.py` 里塔的白模两行（保留小穹顶，归 c224）。

## 验收（评审类型：建筑外壳；V5 为主）

- V5 仰视：从下往上一条连续竖线直到球杆，钟面／钟室／塔顶／球杆层次分明。
- V1 距离邮票：右侧最高的竖线，不被女儿墙吃断（c190-3）。
- 钟面特写：石框＋暖光盘面，四面一致。
- 塔顶特写：甲、乙两版并排可盲比。
- 和主楼交接：塔身与端亭、檐口、女儿墙接得住，无缝、无 >5×5 平墙。

## 版本（塔顶 2 版比选）

- 甲 铜绿小穹顶式：钟室上起小鼓座＋VERDIGRIS 小穹顶收顶，纪念性、圆收。
- 乙 铁架平台式：钟室上起敞开的铁格构平台（IRON_RIVETED 角柱＋IRON_BARS 栏＋IRON_GRATE 台），电气时代工业味、骨架收。

两版共用塔身／钟面／钟室／球杆，只换 y38–41 的塔顶。落选版留在分支不删（RUBRIC §7）。

## 依赖

- 依赖：c206 main/facade（端亭墙 y0–17、立面语法、檐口／女儿墙口径，分支已 merge 229b@2d0571c7）；端亭屋面 y17 deck（c224 屋面露台 / c206 占位）。
- 被依赖：A5 machines/clocks（钟针机芯、报时球、风速计——本卡给占位和挂点）；A2 sky/lights（钟面暖光、塔上灯窗——本卡给挂点）；c218 props/ironwork（百叶、栏杆铁件细化）。

## 记录

- 11-14 c223 领卡（A0 指派）。main 类别原无卡片文件，本卡按 PIPELINE §4.1 新建，随首次提交推上。
- 已把 c206 的 facade 分支 merge 进本分支（读其 `_order.py`／`_plan.py`／`facade.py`）。
- 边界默认（等 c206／c224 回；10 分钟工作量内无回按此做）：端亭四面墙＋檐口＋女儿墙 y0–17 归 c206；y17 deck 不由本卡写（c224/c206）；塔身自 y18 起，东面 x16 直上续端亭墙面；为保 V1/V5 竖线，塔身 footprint 内不设女儿墙（facade `_rod()` 已在塔脚附近跳过避雷针，口径一致）。
