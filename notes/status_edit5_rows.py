# ---- common ----------------------------------------------------------------------------------------
row("common", "interface（接口说明 + 总场景框架）", commit=pick(BARRIER, "3a3c6efc"),
    front="11-16 又补了三次：第二次（fc997791、b21cc789：`check.py` 的 `motion` 一项，`build/place.py` 摆完起循环，叠着合的关口 "
          "`tools/gatestack.sh`）；第三次（3a3c6efc：骨架 `S.V6`、`SMALL_DOME_APEX` 26、测试场景的 `write_pack` 带上 `sky.pack`、"
          "离线的星星按亮度的平方画）；第四次（" + BARRIER_AT + "：占用表的屏障 `B.BARRIER`，只当关着的模型门的碰撞）。")
row("common", "skeleton（骨架）", commit="8db6e43c",
    front="11-16 又改两处：`V6`（总监 03:49，#55097：大台阶南半边看电力房，站位 (66.5, −1.38, 6.5)，看 (76.5, 8.0, 32.5)；e8af28a3）；"
          "`SMALL_DOME_APEX` 25→26（总监 04:40，#57140；8db6e43c）。锁定的机位现在是 V1、V2、V6、V7、V11。")
row("common", "check（检查脚本）", commit=pick(BARRIER, "c4829ad1"),
    front="11-16 又加三处，现在十一项：`motion`（fc997791，motion/loop 的补丁：登记了会动的件的场景，查件数、链数、每刻的命令数）；"
          "`views` 对用地图的时刻、包里却留着游戏自带太阳的场景给 WARN（c4829ad1）；`blocks` 管屏障（" + BARRIER_AT + "：竖着超过两格 FAIL，"
          "三格以内没有模型 WARN）。叠着合的关口 `tools/gatestack.sh`（225421af；`--until` 8a5a9eaf）。")
row("common", "plots-shuttle（地块表和班车脚本）",
    front="看板的清单 `tools/win/shots/obs-board.json` 11-16 重出了两行（e8af28a3：`v06_power`、`v07_hall` 都读骨架），s1 c319 照新清单重拍 V6、V7。")

# ---- materials -------------------------------------------------------------------------------------
row("materials", "ashlar", state="已过审", commit="a494bb19",
    pics="`renders/obs_mat_ashlar/`（a）、`obs_mat_ashlar_b/`（b，默认）、`obs_mat_ashlar_c/`（c），各 19 张，离线图，打磨轮的，node46 出，关口核过",
    front="打磨轮 11-16 合并 a494bb19（合的是 d308767b，分支 `cursor/c164-ashlar-polish-f3-799b`；关口过，三个场景各 19 张逐像素一致）："
          "有效头 f57e5576 上没跑过的 ashlar c353 头一回跑通；细琢面去掉浅石头（20 格外读成点），六个变体每层只断一条缝；"
          "两种端面重画，各 3 个变体，俯看没有重复的花样；样板加了 paved 站，flight 站原来只露两级，修了；样板末尾调 `sky.build`，"
          "壁灯的光回来了；粗琢面、台徽（星是 2×2 的点）、凹板没动。细节在卡片“第四轮”。评审 c332 #19 过（#60331，评的是 d308767b 的 b：质感 4、风格 4，"
          "没有红线；#6 留下的三处（台徽的星、粗琢面凿痕、细琢面浅石）都关了，没有要改的；待真机：走动时横缝和凿痕闪不闪）。"
          "交叉看点了 facade c321（他补图的时候看）。第一版 3380299e 是过了审的。ashlar c353 接着做 machines/armillary。下面是第 1 班的记录：")
row("materials", "iron", state="已过审", commit="3387d99c",
    pics="`renders/obs_mat_iron/`（14 张，离线图，三次交付的，node12 出，关口核过）",
    front="三次交付 11-16 合并 3387d99c（合的是 6a5cb30d；关口过，14 张逐像素一致）：评审 #12 退的灯泡重画了（亮、灭各一张自己的图，"
          "小了不成十字），平板的刷纹手排（六个变体，两块素板）。评审 c332 #15 过（#58034：十一个角色定稿，质感 4、风格 4，没有红线；"
          "留一条不卡的：铆接板的刷纹以后照平板的办法手排）。二次交付的交叉看 m3 c342 过（#57055），评审 #12 只退灯泡一处（#55701）。",
    swap=[("交叉看点了 m3 c342，评审 c332 还没评。", "")])
row("materials", "panels", state="已过审",
    front="评审 c332 #10 过（#55264），交叉看 m3 c342 过（#57055）。",
    swap=[("交叉看点了 m3 c342，评审 c332 复看。", "")])
row("materials", "brass-oldcopper-small", state="已过审",
    front="评审 c332 复评过（#55264：质感 4、风格 4，没有红线，#8 的三处都了了；真楼上的檐沟是一道深线，不是黑缝；不用再交）。",
    swap=[("，评审 c332 复评还没回", "")])
if not G:
    row("materials", "board", state="已交付", commit="07bf4808",
        pics="`renders/obs_mat_board/`（35 张）、`obs_mat_board_ashlar_a/`、`_ashlar_c/`（各 9 张）、`obs_mat_board_windows_b/`（10 张），"
             "离线图，在他的分支上，s2 的关口还没核",
        front="第 3 班：a1 c324 11-16 06:30 交付 07bf4808（#62082，分支 `cursor/c164-a1-board-f3-09d2`；来源干净，他自己的关口 PASS，基 "
              "e5d14d2a）：合了 snow、ashlar、iron 以后整套重画；三个比选的整板场景 `obs_mat_board_ashlar_a`、`_ashlar_c`、`_windows_b`；"
              "他自己说的最弱三处：云和炉火窗还是占位；`all` 里铁墙和背板分不开（金属层要不要换浅背板，请评审定）；`ground_right` 右下是空的；"
              "板上量的：躺着的雪和天一个色，云最浅两阶不比细琢石墙暗（数在卡的记录栏）。排在这一批后面过关口。第 1 班的记录：")
row("materials", "snow", state="已过审", commit="3be01d94",
    pics="`renders/obs_mat_snow/`（13 张，离线图，node50 出，关口核过）",
    front="11-16 合并 3be01d94（合的是 eb997a4e，分支 `cursor/c164-snow-f3-17de`；关口过，13 张逐像素一致）：只动 `materials/snow.py` 和卡；"
          "薄雪层的光由本包定，侧面照顶面的光；侧面的图深一级（`#747d8f` 做底），最下面 2 像素乘 0.8（总监 03:41 定的 A，#54784）；"
          "顶面的图和色阶没动。另存了两条对照图 `cmp_slope`、`cmp_mountain`，不在机位表里。交叉看 a4 c323 过（#57250；留一条："
          "从上往下看，雪面 (53, 63, 114) 和天 (56, 58, 116) 几乎一个颜色，雪块读成通到天上的洞，侧面看也有，不只 V12；"
          "是总监挂着的那一条，见“等总监定的”）。评审 c332 #18 过（#59377，评的是 eb997a4e：质感 4、风格 4，没有红线；俯视时雪和离线的天"
          "一个调子，等真机，已经向 s1 要图，色阶不动）。snow c336 接着做 props/paper。")

# ---- sky -------------------------------------------------------------------------------------------
row("sky", "look", state="已出图", commit=V["LOOK"],
    pics="`renders/obs_sky_look/`（31 张，离线图，蓝调改动以后重画的，总监机出，" + V["LOOK_PICS"] + "）",
    front="蓝调改动 11-16 合并 " + V["LOOK"] + "（合的是 41e88d9d，分支 `cursor/c164-a2-sky-f3-695d`；" + V["LOOK_GATE"] + "）：总监 04:30"
          "（#56724，在第 3 班自己的真机图上定的）朝西的天用 thin_soft，写进 blue：`sky_fog_end` 96→128、余晖不透明度 0.45→0.35"
          "（`sky_color` `#070f2a`、`fog_color` `#434485`；不朝西时天顶和地平线不变，中段的渐变陡一点），blue 的星 0.60；deep 的星 1.0→0.80"
          "（加到天上的是平方 0.64，在彗头内晕 0.84 以下），`star_angle` 0→133（全天唯一一对叠着的亮星沉到地平线下）；thin、thin_soft "
          "两个试验时刻撤了；31 张是合过总装（离线的星星按亮度的平方画，3a3c6efc；comet c330 #56134 查的）以后重画的；量图的两个脚本 "
          "`plan/parts/figs/sky_stars.py`、`sky_west.py`。delivery 的 `scope` 黄是 `sky/mood.py`（天色和雾归 a2）。"
          "**光线版本锁 blue（14000）**，deep、glow 留在时间线上。全场拍到天的旧图都跟着过期（见“等各线报的”重画一条）。"
          "评审 cr2 c333 还没评这一次。第 1 班的记录：")
row("sky", "lights",
    front="评审 cr2 c333 暂评转正（#58497，11-16 05:19：真机 8 张核过，过，最弱三处照旧）。总监 05:00：两翼亮窗窗后的光定 12 级"
          "（真机 V2、V3 上看的；不许再往上加，正中三跨仍是立面上最暖最亮的），lights c331 随洗墙轮改。门后的占位墙照 D（总监 03:44）："
          "壳进总装以后墙留到 lights 给出 `OPEN_HALL`，墩东面前和两条侧廊的临时光源归 lights，不加看得见的灯具，和 facade 撤墙同一批进；"
          "星厅搬进来时门洞的替身源 (16, 1, 0) 由 hall 撤（总监 05:05）。sky/tones 的交叉看点了 lights c331。")
row("sky", "comet", state="已过审",
    front="评审 cr2 c333 过（cr2-#4，#55956：评的是甲，乙、丙的光等真机；第一眼 4、轮廓 4、明暗 4、风格 4，没有红线；最弱三处："
          "`v1_deep` 里彗星亮的部分是亮窗的 33%，真机 18000 第一眼要是落在彗星上就照方案压；真机 v01、v02 两条尾巴一样长，是一个窄 V"
          "（`dust_len` 12、`curve` 0.020，离子尾再宽再淡，不卡）；`v1_*` 里桅杆顶碰到尘尾，等桅杆的真机图，挪桅杆不挪彗星）。"
          "**总监 04:17 定甲**，乙、丙留在分支上；没完的一条：deep 的真机星星纯白、和彗核一样亮，彗核要是天上最亮的一点（comet 和 a2）。"
          "离线的星星改了（3a3c6efc）、a2 的蓝调改动也进了总装（" + V["LOOK"] + "），comet c330 合总装重画一次，照 s1 的真机图再量彗核和星的亮度，按补图交。")
row("sky", "tones", state="暂过", commit="40e27461",
    pics="`plan/parts/figs/tones/`（5 张对照图）；样张是 `renders/obs_sky_look/` 的 31 张",
    front="11-16 合并 40e27461（合的是 a7493ed5，分支 `cursor/c164-a2-sky-f3-695d`，和 motion/loop 同一个提交；关口过）：整张卡重新交付，"
          "`--diff`、多边形取样框、逐帧的像素数都跑过；工具只读图，不进总场景。评审 cr2 c333 试用过验收第 2 条（#58497），还没正式评。"
          "交叉看 lights c331 过（#60390，看的是 `_tones.py` @ 71f31bca：拿洗墙轮的 5 张草图跑，带 cr2 的量框、`--out`、`--ladder`、`--diff`；"
          "12 个框和整图三档的数和他另写的 numpy 逐项相同；`order` 一行和眼睛看的次序一致；梯子里“7 级洗到的东面 0.31”偏高，实量 0.28；"
          "不顺手三处：`--probes` 按图名找框，草图的名字对不上时一个都找不到也不提示；小框挤在一起时图上的名字叠成一团；`order` 按均值排，"
          "评审报的是中位数，带窗棂的窗差得远。抄了 cr2、a2）。下面是第 1 班的记录：")

# ---- main ------------------------------------------------------------------------------------------
row("main", "facade", state="已过审", commit="167260ee",
    pics="`renders/obs_main_facade/`（B，10 张）、`obs_main_facade_a/`（4 张）、`obs_main_facade_c/`（4 张）、`obs_main_facade_nocrown/`（5 张），"
         "离线图，node35 出，交付时关口核过，现在全部过期",
    front="打磨轮第一批 11-16 合并 167260ee（合的是 51947080；关口过：23 张和交付的提交对得上，合进总装时已经过期）：`_plan.py` 去掉室内"
          "那一半（没人读，前后逐格比过）；占位亮墙的新规矩 `facade.screened()`（总监 03:44 的 D）：壳在树里、lights 给了 `OPEN_HALL` 才撤墙，"
          "谁先进总装门里都不是黑洞；新机位 `v11_south`、`v7_door`。入口轮评审 c332 #9 过（#55264），打磨轮第一批评审 #17 过（#58853：石头没动，分数和 #9 一样，没有红线）。" + pick("壳 11-16 进了总装，", "壳 11-16 在关口上，")
          + "墙还留着（见“合的时候要留神的”）。a2 的蓝调改动和大穹顶的默认乙进了总装（" + V["LOOK"] + "、" + V["DOME2"] + "），补图现在一次画，ashlar 打磨轮的交叉看那时一起看。入口两侧栅门的屏障"
          "（总监 05:07）是他问的，由 m3 放。入口轮的记录：",
    swap=[("，评审 c332 还没评。下面是第 1 班的记录", "。下面是第 1 班的记录")])
row("main", "dome", state="已过审", commit=V["DOME2"],
    pics="`renders/obs_main_dome/`（乙，地图用的，11 张）、`obs_main_dome_a/`（甲，留档，11 张）、`obs_main_dome_slit/`（10 张），离线图，"
         "二次交付时全部重画的，" + V["DOME2_PICS"],
    front="11-16 合并 ec9ac975（合的是 4734497f，分支 `cursor/c164-dome-f3-a244`；卡 b1ee550e，合的是 529f72e9；关口过：32 张和交付的提交对得上），"
          "二次交付 " + V["DOME2"] + "（合的是 ad0c352b；" + V["DOME2_GATE"] + "）：**地图用乙（八条主肋）**，`dome.VERSION = \"b\"`（总监 04:56，#57775）；"
          "场景改了名：`obs_main_dome` 是地图用的乙，`obs_main_dome_a` 是甲、留档，`obs_main_dome_b` 没有了；32 张全部重画，场景的包带上了 "
          "`sky.pack`；别的包的图里照到大穹顶的从甲变成乙，要重画。头一次交付："
          "第二稿头一回跑通；环廊的立柱全撤（`POSTS = 0`，总监 04:21、#56253：一道铆接的铁走道加铜沟，#294 的“栏杆换稀的”作废，"
          "细扶手现在不做）；机位 `south_door` 换成 `ridge`。评审 c332 #14 甲乙都过（#57628：第一眼 4、轮廓 4、明暗 4，没有红线，"
          "真机 V1、V2、V11、V12 核过甲；排名乙第一）。**总监 04:56 定乙（八条主肋）**：真机图上肋读不出就加深一级，review 说了算。"
          "交叉看 sdome c328（#57716）：是一家；三处不一样里，分层和深铜"
          "小穹顶跟大的改，缝各留各的。dome c326 接着做 machines/engine-dynamo。下面是第 1 班的记录：")
row("main", "tower",
    front="第 3 班：tower c327 的分支合过总装 2f597026（7ece55c8，`massing.py` 两段都没了）；交叉看过 smalldome（#55677）。还没交付。")
row("main", "smalldome", state="已过审", commit="825ec1ef",
    pics="`renders/obs_main_smalldome/`（18 张，离线图，node42 出，交付时关口核过）",
    front="11-16 合并 825ec1ef（合的是 ab28afba，分支 `cursor/c164-sdome-f3-1fe7`；关口过，18 张逐像素一致）：屋面是 `main/roof.py`"
          "（草稿改了名），`massing.py` 里小穹顶的白模删了；缝南的铁门扇和铜皮平齐，料还是铁（总监 03:21；第 1 班 #23752 的“高出铜皮半格”"
          "作废）；铁裙上 8 只轴箱。交叉看 tower c327 过（#55677：塔门 (10, 18..19, −30)、屋脊走道落在门前、塔的脚印底下 y 17 是整板，"
          "逐格对过）。评审 c332 #13 过（#57057：第一眼 4、轮廓 4、明暗 4，没有红线，真机 V1、V2、V11、V12 核过）。之后总监又定三件："
          "顶点 26（04:40，骨架 `SMALL_DOME_APEX` 25→26，8db6e43c）；素皮，脚上三块散的深铜板换回铜皮，#23752 这一条作废（05:00）；"
          "铜皮按环分层、脚一条平线，跟大穹顶。sdome c328 三件一起改、重出图，按打磨轮交，V11、V2 报 review c332 复核。"
          "他同时在做 machines/meridian-astrograph。下面是第 1 班的记录：")
row("main", "shell", state=pick(V["SHELL_STATE"], "已交付"), commit=pick("f54bf237", "4336bc18"),
    pics="`renders/obs_main_shell/`（29 张，离线图，node39 出，" + pick(V["SHELL_PICS"], "在他的分支上，关口还没核") + "）",
    swap=[("第 3 班：70a1966a 不单独合，shell c325 把有效头 15b6cf2e 跑过、出了图，在总装 42d7ef66（facade 已经在里面）上面重新【交付】。",
           pick("11-16 合并 f54bf237（合的是 4336bc18，分支 `cursor/c164-shell-f3-3067`，顶替 70a1966a；" + V["SHELL_GATE"] + "）",
                "11-16 交付 4336bc18（分支 `cursor/c164-shell-f3-3067`，顶替 70a1966a；来源干净，叠着合在 s2 的分支上 f54bf237，"
                "技检等节点，还没进总装）") + "：有效头 15b6cf2e "
           "上没跑过的 shell c325 头一回跑通，出了 29 个机位的图，在总装 8fcb3c0e 上面交；`shell.ROOMS` 没变，接口的改动他私信了 "
           "hall c348、chart c350。评审 c332 #16 过（#58537：第一眼 4、轮廓 4、明暗 4（暂），没有红线；留一条不卡的：环梯两个口各加一根灯柱，"
           "他改了再报）。" + pick("交叉看点了 hall c348。", "交叉看合并以后点 hall c348。") + "门后的占位亮墙还留着（见“合的时候要留神的”）。")])

# ---- site ------------------------------------------------------------------------------------------
row("site", "court", commit="8b7735eb",
    pics="`renders/obs_site_court/`（9 张，离线图，node37 出，交付时关口核过，现在全部过期）",
    front="打磨轮 11-16 合并 8b7735eb（合的是 ca810cc1，分支 `cursor/c164-a4-site-f3-6824`，和山体三稿同一个提交；关口过：图和交付的提交"
          "对得上）：评审 #3 的三条；地面的铜嵌线压暗、改细，只走南北（总监 #255、#365；`BRASS_LINE`、`BRASS_CROSS`、`BRASS_STAR`），"
          "整格的 `BRASS_INLAY` 兜底删了。交叉看 facade c321 过（#55984：条带 z ±6、±26 落在壁柱线上；中间的道 z −2..2 对门跨；"
          "铜线只有子午线和台徽的环，离立面最近八格）。评审 cr2 c333 过（cr2-#6，#57277，记录 c03815b8；最弱三处：铜线远看读不出"
          "（贴图是 materials/brass 的）、中间的道和檐壁一样亮、矮柱是一排浅点（总监：不改））。a4 c323 在做评审点的打磨，和 terrain "
          "一次合、一次重画。下面是第 1 班的记录：")
row("site", "terrain", state="已过审", commit="8b7735eb",
    pics="`renders/obs_site_terrain/`（9 张）、`obs_site_terrain_nosnow/`（4 张），离线图，node37 出，交付时关口核过，现在全部过期",
    front="三稿 11-16 合并 8b7735eb（合的是 ca810cc1，和前庭打磨轮同一个提交；关口过：图和交付的提交对得上）：`site/ground.py` 删了"
          "（框架演示用的平地，平台由 `terrain.py` 铺）；那圈占位的云留到 cloudsea 进来；雪的颜色归 materials/snow。交叉看 stair c337 过"
          "（#56243：在 `obs_site_stair` 里合着总装看的，`sight` 被挡的从 11.7% 降到 9.5%；下平台西南角外 x ≤ 60、z 40..42 的岩面和铺地齐平，"
          "雪贴到铺地边上）。评审 cr2 c333 过（cr2-#5，#57277，记录 c03815b8：4／4／4／—／4，没有红线；最弱三处：雪像薄冰片"
          "（亮度过：真机 V11 最亮的 1% 是 0.28，浅石 0.31）、船头崖脚一道薄台和直崖、下平台的裸岩等 stair）。a4 c323 在做评审点的打磨，"
          "和 court 一次合、一次重画，画好告诉 cr2（他要量雪那一条）。下面是第 1 班的记录：")
row("site", "powerhouse", state="已过审", commit="4b538dbe",
    pics="`renders/obs_site_powerhouse/`（甲，13 张）、`obs_site_powerhouse_b/`（乙，13 张），离线图，二次交付时重画的，交付时关口核过，现在过期",
    front="11-16 合并 ff8ea061（合的是 5a0158ba，分支 `cursor/c164-power-f3-2e4a`），二次交付 4b538dbe（合的是 a863dc2e）；关口都过，图和交付的"
          "提交对得上。总监 03:49（#55097）：屋面定甲（锯齿），齿形的侧影朝北对着 V6，采光面朝西，评审不扣“天窗该朝北”；乙留着不再做。"
          "V6 定在 `stair_south`：骨架 `S.V6` 站位 (66.5, −1.38, 6.5)、看 (76.5, 8.0, 32.5)（e8af28a3），看板的 `v06_power` 跟着改了。"
          "门灯（总监 04:30，#56796）：过梁正中一盏铁笼壁灯，7 级，`DOOR_LAMP` 默认开、位置 `LAMP_AT`，多 1 个实体，不许加第二盏；"
          "原来的候选机位 `v6_power` 改名 `door_axis`；两个场景各加了 `v1` 机位。交叉看 stair c337 过（#57260：V6 的落脚实在，踏面 x 66、"
          "面 y −3；总装里 V6 的前景多了台阶的两样：最左的梯脚灯、右下的垂带压顶；管桥接得上，管 y 2 从 z 30、34 两墩之间的栏杆上过）。"
          "评审 cr2 c333 过（暂评，#58497，评的是 a863dc2e：第一眼 3（参）、轮廓 4、明暗 4（暂）、风格 4（参），没有红线；V6 整幅现在只到 3，"
          "炉火窗的图和窗后的光进来（`FIRE` 打开）以后照 V6 复评，到时报他；最弱三处：炉火窗一跨只有玻璃亮、不照墙和地，大门是正中最暗的"
          "一块，烟囱筒身斜看角上一道黑槽）。还要来一个两行的小改（`build()` 不再自己挂炉火窗的内衬，chart c350 #58343）。"
          "power c339 接着做 interiors/powerhouse。下面是第 1 班的记录：")
row("site", "stair", state=pick("已出图", "已交付"), commit=pick(STAIR, "8e302456"),
    pics="`renders/obs_site_stair/`（12 张）、`obs_site_stair_noband/`（5 张）、`obs_site_stair_nolamps/`（5 张），离线图，node4 出，"
         + pick(V["STAIR_PICS"], "在他的分支上，s2 的关口还没核"),
    front=pick("11-16 合并 " + STAIR + "（合的是 8e302456，分支 `cursor/c164-stair-f3-b330`；" + V["STAIR_GATE"] + "）",
               "11-16 05:48 交付 8e302456（分支 `cursor/c164-stair-f3-b330`，合过总装 a4d2c377；他自己在 node4 上跑过关口，PASS；来源干净，"
               "叠着合在 s2 的分支上 dd61614d，s2 的技检等节点，还没进总装）")
          + "：第二版和发电房的交界头一回跑通（stair c337 接 c225，node51 掉线以后在 node4 上跑）。踏面的浅带留，开关默认开"
            "（总监 03:35，#54523）；梯脚灯座的帽换成座身的料（光面凝灰岩的阶，灯站在正中的小台上，`stair.LAMP_POINTS` 梯脚两个点的 y "
            "从 −3.5 到 −3.0，lamps 读表）；垂带墙和四个灯座的勒脚换成光面深板岩，和挡土墙的勒脚一层；新加通发电房北门的走道"
            "（三格宽，`lowerplatform.door_walk()` 读 `powerhouse.DOOR_AT`；a4 #55419、power #55216 同意）；三个场景的包加了 `sky.pack`；"
            "机位 12 个（加了 `axis_high`、`pedestal`、`v6`，`v6` 读骨架的 `S.V6`）。delivery 的 `scope` 把 `site/lowerplatform.py` 算成别家的，"
            "是黄，它是本卡的交付物。山体三稿、发电房、灯链进总装以后的交界他都对过（卡上“第 3 班”一段）。"
            + pick("交叉看点了 cable c338，", "交叉看合并以后点 cable c338，") + "评审 cr2 c333 还没评第二版。下面是第 1 班的记录：")
row("site", "outbuildings", state=pick("已出图", "已交付"), commit=pick("064dbc57", "5c2b6ec9"),
    pics="`renders/obs_site_outbuildings/`（14 张，离线图，node54 出，" + pick(V["OUTB_PICS"], "在他的分支上，关口还没核") + "）",
    front=pick("11-16 合并 064dbc57（合的是 69b57fe8，分支 `cursor/c164-outb-f3-f4b8`，和 mastbase 同一个提交；卡上一处改动 " + CARD + "，合的是 "
               "5c2b6ec9；" + V["OUTB_GATE"] + "）。",
               "11-16 交付 69b57fe8（分支 `cursor/c164-outb-f3-f4b8`，和 mastbase 同一个提交），卡上一处改动 5c2b6ec9；来源干净，叠着合在 "
               "s2 的分支上（064dbc57、" + CARD + "），技检等节点，还没进总装。") + "气象站有本包自己的 3 个展示实体（风杆头带风向标、风杯轮、雨量筒；总监 04:56、#57678：留，"
          "读得出是气象仪器，不成十字；卡上“展示实体 0”改成 3）；风杯轮在 motion 里登记了一行 `MK.spin`（1 件，平均每刻 0.6 条命令）。"
          "机位 14 个（加了 `hut_inside`、`weather_head`）。props/instruments 进总装以后平台上再摆 3 件（三脚架望远镜、百叶箱、日照计），"
          "那时重出图。灯位表 `LAMP_POINTS` 给 lamps c341。" + pick("交叉看点了 lamps c341，", "交叉看合并以后点 lamps c341，") + "评审 cr2 c333 在评（5c2b6ec9）。"
          "outb c340 11-16 05:46 又领了 common/export。下面是第 1 班的记录：")
row("site", "mastbase", state=pick("已出图", "已交付"), commit=pick("064dbc57", "69b57fe8"),
    pics="`renders/obs_site_mastbase/`（6 张，离线图，node54 出，" + pick(V["MASTBASE_PICS"], "在他的分支上，关口还没核") + "）",
    front=pick("11-16 合并 064dbc57（合的是 69b57fe8，和 outbuildings 同一个提交；" + V["MASTBASE_GATE"] + "）。石座先于桅杆进的总装"
               "（桅杆 3b87af9d 在同一批后面）。交叉看点了 mast c346，",
               "11-16 交付 69b57fe8（和 outbuildings 同一个提交；来源干净，叠着合在 s2 的分支上 064dbc57，技检等节点，还没进总装）。"
               "石座合在桅杆前面。交叉看合并以后点 mast c346，") + "评审 cr2 c333 在评。下面是第 1 班的记录：")

# ---- machines --------------------------------------------------------------------------------------
row("machines", "clocks", state=pick("已过审", "已交付"), commit=pick("7acc80db", "1269f914"),
    pics="`renders/obs_mach_clocks/`（15 张）、`obs_mach_clocks_b/`（5 张），离线图，" + pick(V["CLOCKS_PICS"], "在他的分支上，关口还没核"),
    front=pick("11-16 合并 7acc80db（合的是 1269f914，分支 `cursor/c164-clocks-f3-00d6`；" + V["CLOCKS_GATE"] + "）",
               "11-16 交付 1269f914（分支 `cursor/c164-clocks-f3-00d6`；来源干净，叠着合在 s2 的分支上 7acc80db，技检等节点，还没进总装）")
          + "：母钟、塔钟四面的钟面和针、"
          "报时球。报时球定旧铜（总监 04:03，#55695：`clock.BALL = \"copper\"`，暗红留作开关；球用默认的 `old_copper`，不跟着方块降级；"
          "#449 第 3 条到此定了）。母钟的钟摆在 motion 里登记了一行（`MK.swing`）。scope 的黄是 `machines/clock.py`（卡的文件名，"
          "hall、tower 读它）。评审 cr3 c347 过（cr3-#2，#58450，记录 `cursor/c164-cr3-f3-998d` df9016f0：质感 4、风格 4，参考项都 4，"
          "没有红线；最弱三处是近看的小修：母钟的针色、塔钟的八个时标、球的色带，不挡合并）。桅杆进总装以后，clocks c345 小修、连同"
          "重出的 `v1_tower`、`tower_far` 再交。" + pick("交叉看点了 tower c327。", "交叉看合并以后点 tower c327。") + "下面是第 1 班的记录：")
row("machines", "engine-dynamo", state="制作中", who="dome c326",
    front="第 3 班：dome c326 11-16 领卡（总监助理 #57536），分支 `cursor/c164-dome-engine-f3-a244`，从总装起，评审 cr3 c347。卡：")
row("machines", "meridian-astrograph", state="制作中", who="sdome c328",
    front="第 3 班：sdome c328 11-16 03:53 领卡（总监助理 #55288），分支 `cursor/c164-sdome-astro-f3-1fe7`，从总装起，没有前任，评审 cr3 c347。卡：")
row("machines", "radiomast", state=pick("已过审", "已交付"), commit=pick(V["MAST2"], "d98865b7"),
    pics="`renders/obs_mach_radiomast/`（甲，14 张）、`obs_mach_radiomast_b/`（乙，14 张），离线图，二次交付的，node5 出，"
         + pick(V["MAST_PICS"], "在他的分支上，关口还没核"),
    front=pick("11-16 合并 3b87af9d（合的是 cffdf4e7 = 交付的 e065bd84 加一个只改卡的提交，分支 `cursor/c164-mast-f3-fc27`；" + V["MAST_GATE"] + "），"
               "二次交付 " + V["MAST2"] + "（合的是 d98865b7 = 交付的 72961289 加一个只改卡的提交；" + V["MAST2_GATE"] + "）；"
               "石座（site/mastbase）同一批先进。",
               "11-16 交付 cffdf4e7（= e065bd84 加一个只改卡的提交，分支 `cursor/c164-mast-f3-fc27`），二次交付 d98865b7（= 72961289 加一个只改卡的"
               "提交）；来源干净，叠着合在 s2 的分支上（3b87af9d、8ff02862），还没进总装；石座（site/mastbase）合在它前面。")
          + "二次交付是评审 cr3-#1 以后的一轮：脚下的球隙、铜馈线、节点板朝外的面各加两颗铆钉、拉线从铁第 0 级提到第 1 级；"
            "**不挂天线**（总监 06:01，#60746，在单线、笼形、不挂线三版并排的图上定的：V1 里单线是彗头旁的第二根竖线，笼形断成虚线；"
            "杆身自己就是天线，脚下馈电；顶上的臂去掉，报时塔上那根铁杆和瓷瓶由 tower c327 去掉）；实体 23→20，模型 11 个，"
            "机位各 14 个（`tower` 撤了）。总监 04:40（#57179）：脚上四条腿直着落下、各垫一只白瓷座，y 16.6 的白瓷瓶留着，六面的红灯照做，"
          "定甲，乙留在分支上；开着一条：V1 里红灯和格构紧挨彗头，等 s1 的真机 V1，要动只动灯（降一级）。评审 cr3 c347 过（cr3-#1，#57480，"
          "评的是分支上的 e065bd84，记录 `cursor/c164-cr3-f3-998d` ef884efc：甲质感 4、风格 4，没有红线；乙质感 3 不过；最弱三处留给打磨轮："
          "球隙和馈线、节点板的铆钉和拉索的暗面、天线像吊索；红灯和细线等真机），三处二次交付都照改了；二次交付评审 cr3 c347 过（cr3-#3，#61971，评的是 72961289 的甲：五项都 4，"
          "没有红线，三处小修不卡合并；记录 `cursor/c164-cr3-f3-998d` f0ddcb28）。mast c346 接着做 machines/switchboard-boiler。scope 的黄是 `machines/mast.py`（卡的文件）。"
          + pick("交叉看点了 outb c340。", "交叉看合并以后点 outb c340。") + "下面是第 1 班的记录：")
row("machines", "switchboard-boiler", state="制作中", who="mast c346", commit="3eb614d5（总装头，分支从这里开）",
    front="第 3 班：mast c346 11-16 06:11 领卡（#61332，总监助理派），分支 `cursor/c164-mast-switchboard-f3-fc27`，从总装 3eb614d5 开，没有前任。卡：")
row("machines", "refractor",
    front="**总监 11-16 06:03 定甲（德式赤道仪）**：从南面和 V8 都一眼是墩上的长折射镜，筒指着缝里的彗星；乙（英式轭架）的北支架挡筒、基座挡轭，"
          "留在分支和测试场景里，交付物只放甲。目镜旁的红灯加一个看火孔：灯罩朝东一个模型像素，信号红，自发光面，不加光源；V8 里是一个点"
          "（720p 下不超过 3×3 屏幕像素），读成一块就缩；全室的红仍只此一处。第 1 班的记录：")
row("machines", "armillary", who="ashlar c353（接 c246）",
    front="第 3 班：ashlar c353 11-16 领卡（#56867），分支 `cursor/c164-ashlar-armillary-f3-799b`，从有效头 724d26be 起，合过总装（20a49c32），node46。")

# ---- props -----------------------------------------------------------------------------------------
row("props", "lamps", commit="b5faa03a",
    pics="`renders/obs_props_lamps/`（26 张）、`obs_props_lamps_site/`（15 张）、`obs_props_lamps_site_nearpair/`（6 张），离线图，node55 出，"
         "交付时关口核过，现在全部过期",
    front="场地灯链 11-16 合并 b5faa03a（合的是 546c070e，分支 `cursor/c164-lamps-chain-f3-0dde`；关口过：47 张和交付的提交对得上，"
          "合进总装时已经过期）。**`lamps.DRESS` 开了**（总监 04:14，#56091）：总装里场地灯是摆着的，26 盏里 19 盏立起来了，另 7 盏等 "
          "stair、outbuildings、cablecar；拍到真楼或场地的旧图都过期，各包的测试场景不要再自己调 `lamps.site()`。前庭的第一对灯撤了"
          "（总监 03:34，#54472：`lamps.NEAR_PAIR = False`，对照场景 `obs_props_lamps_site_nearpair` 留着，球罩没动）；甲的铁笼灯两道箍挪到 "
          "x ±2.5。试的图在 `cursor/c164-lamps-trial-f3-0dde` 的 `renders/trial/`，只给人看。他查出一件（#56843）：只带 `materials.pack` 的"
          "测试场景天上是游戏自带的太阳，规矩进了 INTERFACE，`check.py` 给 WARN（c4829ad1）。交叉看点了 a4 c323，评审 c332 还没评。"
          "lamps c341 接着做 props/electrics-signs。下面是第 1 班的记录：")
row("props", "electrics-signs", who="lamps c341（接 c242）",
    front="第 3 班：lamps c341 11-16 领卡（#57080），分支 `cursor/c164-lamps-elecsign-f3-0dde`，从有效头 5ff667a1 起，合过总装 5319a037，node55。")
row("props", "paper", who="snow c336（接 c197）",
    front="第 3 班：snow c336 11-16 03:59 领卡（#55584），分支 `cursor/c164-snow-paper-f3-17de`，从有效头 b3ff0866 起，合过总装 2f597026，node50。")
row("props", "ironwork",
    front="第 3 班：入口两侧拱（8、10 号跨）的栅门关着，是模型，门洞里放屏障当碰撞（总监 05:07）：(16, 0..1, z −5..−3 和 3..5) 共 12 格，"
          "由 `ironwork.doors()` 在清掉 facade 的占位铁栏的同一步放，用 `B.BARRIER`（" + BARRIER_AT + "）。打磨轮 m3 c342 在做。")

# ---- interiors -------------------------------------------------------------------------------------
row("interiors", "powerhouse", state="制作中", who="power c339",
    front="第 3 班：power c339 11-16 领卡（总监助理 #56110、#56937），分支 `cursor/c164-power-interior-f3-2e4a`，从 5a0158ba 起，评审 cr3 c347。卡：")
row("interiors", "chartroom", who="chart c350（接 c205）", commit="fb9b2ecb（有效头，分支从这里开）",
    front="第 3 班：chart c350 11-16 05:55 开了这张卡（#60317），分支 `cursor/c164-chart-chartroom-f3-3477`，从有效头 fb9b2ecb 起，合过总装 "
          "5d047bc1 之后的头。窗的补件不变：头 af4e2107，等 power c339 的小改进总装、节点回来再过关口。")
row("interiors", "starhall",
    front="总监 05:05（11-16）：V7 的次序是母钟钟面和墩的东面第一、日球是最暖的一点、地面第三；钟面提到 0.35 以上，台徽上的落点留着但级数降到"
          "地面正中低于钟面；lights 在门洞放的替身源 (16, 1, 0) 在星厅搬进来的同一次交付里撤掉。调好交评审，不用再问总监。")

# ---- motion ----------------------------------------------------------------------------------------
row("motion", "loop", state="暂过", commit="40e27461",
    pics="`renders/obs_mot_loop/`（24 张）、`obs_mot_load/`（4 张），离线图，node36 出，关口核过；会动的等真机看",
    front="11-16 合并 40e27461（合的是 a7493ed5，分支 `cursor/c164-a2-sky-f3-695d`，和 sky/tones 同一个提交；关口过，28 张逐像素一致）；"
          "跟进在新分支 `cursor/c164-a2-loop-f3-695d`（aide #62203）；"
          "公共文件那三处 s2 照他给的补丁改了（fc997791）。两个测试场景的 `motion` 一项是故意的黄（`obs_mot_loop` 12 件 6 条链、102 个函数文件、"
          "最忙一刻 9 条命令；`obs_mot_load` 200 件、最忙一刻 36 条（上限 60）、平均 34.4（上限 40），是压力测试）。离线图只画静止的姿态。"
          "交叉看 clocks c345 过（#57520：给母钟的钟摆登记了一行 `MK.swing`，接口好用；没登记的不动，同一个实体登记两次报错，"
          "两只相叠的钟摆 FAIL；留一条：摆动切不切到邻件 check 不管）。评审 cr2 c333 在评。" + pick("总装里登记了的件：母钟的钟摆（clocks）、"
          "气象站的风杯轮（outbuildings）。", "登记了的件：母钟的钟摆（clocks）、气象站的风杯轮（outbuildings），两个包都在关口上。") + "下面是第 1 班的记录：")
row("motion", "sound", state="制作中", who="a2 c322（交了 smoke 再开）",
    front="第 3 班：a2 c322 11-16 领卡（总监助理 #56110），交了 smoke 再开，一张卡一条新分支。")
row("motion", "smoke", state="制作中", who="a2 c322",
    front="第 3 班：a2 c322 11-16 领卡（总监助理 #56110），一张卡一条新分支。")
print("rows done")

# ---- the second batch of cards (the director, 11-16 05:24) -------------------------------------------
lo, hi = section("common")
after("| offline-sky（离线渲染补天空） | ", [
    "| walk-out（室外走查） | P1 | 制作中 | facade c321 | db1ec43d（总装头，分支从这里开） | — | facade c321 11-16 05:34 领卡（#59171，总监 05:29 派），"
    "分支 `cursor/c164-facade-walkout-f3-81a0`，node35。卡 `plan/packages/common/walk.md`（总监 11-16 05:24 立，第二批）：沿游客的路每隔几格拍一张，"
    "找 12 张看板照不到的毛病，只找、只报、改完复查，不改别人的东西。路线：出生点（缆车站站台）→ 下平台 → 大台阶 → 前庭一圈 → 子午仪小屋 → "
    "桅杆石台 → 气象站 → 水塔 → 主楼西侧、落日平台 → 南观景台 → 发电房一圈、管桥 → 回到下平台；每一段栏杆边往外、往下看 |",
    "| walk-in（室内和屋顶走查） | P1 | 制作中 | a4 c323 | — | — | 总监 05:29 派给 a4 c323（总监助理 #59118），分支从总装开。"
    "同一张卡 `plan/packages/common/walk.md`：正门 → 星厅 → 西门过道 → 楼梯厅、大楼梯 → "
    "回廊一圈 → 授时室 → 星图室 → 环梯 → 大圆顶室 → 转角露台 → 两条屋脊走道 → 发电房里面、缆车站候车室、子午仪小屋里面；"
    "哪里走不通、哪扇门是关的，本身就是要报的事 |",
    "| export（成品地图导出） | P1 | 制作中 | outb c340 | a758fa9f（总装头，分支从这里开） | — | outb c340 11-16 05:50 领卡（#60070，总监助理 05:46 派），"
    "分支 `cursor/c164-outb-export-f3-f4b8`，node54。卡 `plan/packages/common/export.md`（总监 11-16 05:24 立，第二批）：一条命令把总装导出成能直接上传的"
    "存档，现在先空跑，评审都过了以后做正式的一次；设置照本文件“成品地图交付清单”逐条做，清单里没定的列成表问总监；成品世界里只有整场 `obs` |",
], lo, hi)
lo, hi = section("interiors")
after("| powerhouse | ", [
    "| batteryroom | P3 | 制作中 | stair c337 | —（分支从总装开） | — | stair c337 11-16 06:03 领卡（总监助理派，名单 73d94b25），分支 "
    "`cursor/c164-stair-batteryroom-f3-b330`；先交一页草图给总监，site/stair 被退回时它优先。卡 `plan/packages/interiors/batteryroom.md`（第二批，规矩见“总监定过的 / 11-16”05:24 一条）：北翼底层的蓄电池室，"
    "授时室的正下方；现在是封死的空腔，门洞和楼板由 shell c325 开，开在哪里和他、和 hall c348 一起定 |",
    "| platevault | P3 | 待领 | — | — | — | 卡 `plan/packages/interiors/platevault.md`（第二批）：南翼底层的底片库和暗房，星图室的正下方；"
    "门洞和楼板由 shell c325 开，开在哪里和他、和 hall c348 一起定 |",
    "| clockroom | P3 | 待领 | — | — | — | 卡 `plan/packages/interiors/clockroom.md`（第二批）：报时塔钟室，四面钟面的背后；塔身能不能掏空、从走道的哪里进，"
    "先和 tower c327 对；钟面的位置、大小、材质以他和 clocks c345 的为准 |",
    "| astroroom | P3 | 待领 | — | — | — | 卡 `plan/packages/interiors/astroroom.md`（第二批）：小穹顶室，天体照相仪站的地方；外壳、缝、缝门归 `main/smalldome`；"
    "卡上建议 sdome c328 接着领 |",
], lo, hi)
row("sky", "ridges", prio="P2", state="制作中", who="comet c330",
    front="总监 11-16 05:24 提到 P2，05:29 派给 comet c330（总监助理 #59118），没有前任，分支从总装开。卡：")
print("second batch done")
