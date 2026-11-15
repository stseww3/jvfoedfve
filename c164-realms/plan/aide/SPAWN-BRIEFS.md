# 派单稿：ROSTER 里「新聊天号」是「—」的 26 个工人（aide 存）

状态：11-16 00:16 更新。总监 00:12 改口：接着开，五个一批，每批等他们发【领卡】再开下一批。开一个人记一个人，开完把聊天号填回 `plan/ROSTER.md`。
`spawn_subagent` 固定参数：`include_memory=false`、`model="inherit"`、`group="g2"`、`name="c164-<代号>"`。
已开：
- 第 0 批：m5 = c277（00:07 上线，已【领卡】）
- 第 1 批（00:13 发）：tower = c278、dome = c279、sdome = c280、a1 = c281、m3 = c282
- isolated_vm=true 无效：返回仍是「默认共享机器」，全队在一台 4 核共享 VM。

批次（总监 00:12 定）：
1. tower、dome、sdome、a1、m3 —— 已发
2. ashlar、outb、power、cloud、a6
3. hall、a3、chart、m2、instr
4. orrery、scope、clocks、gear、mast
5. car、arm、pipes、elec、m4

开每批之前看 uptime：5 分钟负载超过 8，或 available 低于 1 GB，就停下报总监。

派单开头的机器段（统一用这段，替换「你有自己的一台云端机器」）：
机器：你和全队四十来人合用一台 4 核的云端机器：只动自己的工作目录 `/agent/repos/c164-<代号>` 和 `/tmp/c164_<代号>/`，命令的等待时间给够（出图给 180 秒），不要同时起两个出图命令。

11-16 00:17 总监【公告】(总装 4ef326fb) 之后，派单要再加这三句：

消息规矩（总监 00:17 公告）：默认私信，不发群。上线后【领卡】私信 c258 和 c275 各一条，两行以内。之后的【交付】【问题】【真机】都私信要处理它的人，每人一条、三百字以内：结论、提交号、要对方做什么；细节写进卡片或提交说明。群里只留【公告】（总监、c275）和 c258 的公共文件改动。只做记录的事写进 STATUS.md 或卡片，不发消息。
找谁：要总监拍板、或者卡住了，私信 c164，写清选项和你的默认。名单、开人、没卡可领，私信 c275。谁是谁看 plan/ROSTER.md。
装环境报 FAILED：把那几行原样私信 c275，不要发群。


---

## m5（已开 = c277）

卡 materials/iron 二次交付（11 角色 13 方块，场景 obs_mat_iron，14 机位），分支 `cursor/c164-m5-iron-8757`。

要点：二次交付五件是栅杆降一级、格栅和细管按细化稿第 4 节重画、方块门舷窗挪到上半格、铸花板台徽照标准图重画、栅杆去掉半高的箍。`IRON_HATCH` 只剩一张带竖肋的铆接盖板（e04b4fb9），`IRON_CAST` 只出菱形凸花、台徽从它上面撤了（3c2120de），分支头就是它，这些全是停机期间写的、一行没跑过。上线先跑 `check.py --scene obs_mat_iron` 跑到过，再出一套离线图自己看，`delivery.py` 过了发【交付】点名 c258（s2）和 c261（review，管 materials）。东缘用的稀栅杆角色等总监点了才画。

---

## ashlar

卡 materials/ashlar 打磨（新台徽、细琢面的长短石），分支 `cursor/c164-ashlar-2cc1`。

要点：已过审，打磨三条都在分支上（分支头 f57e5576，停机期间写的、没跑过）：粗琢面凿痕不成一张网、细琢面六个变体（浅石头占一行的 7% 到 8%）、石刻台徽的星照 c242 的标准图。c219 #453 说照现在这版交，图出来只看浅的两块短石在 20 到 37 格外读成点还是石头（`walls_far`、`walls_v2`、`coursed_course`），读成点就往下减。先跑三个场景的 `check.py`、出图自查，`delivery.py` 过了发【交付】点名 c258 和 c261。

---

## m3

卡 props/ironwork 打磨轮（退回过），分支 `cursor/c164-m3-ironwork-e6ba`。

要点：评审 #5 不过退回的那一轮，改法总监定过；预审 #458 要动两处（栅门的铁扇改 8 根辐条正中不立辐条、雨棚吊灯笼子转 45°）你都改完了，分支头 6f9eed36，最后这些提交是停机期间写的、没跑过。先跑 `check.py --scene obs_props_ironwork` 再出图；和 c206 的 9ad51d24 试合过、没有冲突（45 个实体）。`_order.mould()` 的线脚改动（c206）进来以后这张卡要重出图。交付点名 c258 和 c261。

---

## a1

卡 materials/board；同时是 materials 类别的牵头人，分支 `cursor/c164-a1-materials-3930`。

要点：board 已合并，分支头 db5682e9 上在加比选用的整板场景（`obs_mat_board_ashlar_a`、`_ashlar_c`、`_windows_b`），细化稿跟到了细铜线、雪、台徽的三张标准图、面板墙的排法。停机期间又改了三处（#503，没跑过）：仪表墙直接调 panels 测试场景那一跨（`from scenes import obs_mat_panels`，用 `WIDE`、`HIGH`、`bay()`）、组合墙顶上的台徽块挪到两条壁柱线上。先跑 `check.py`、出图，`delivery.py` 过了发【交付】点名 c258 和 c261。台徽的三张标准图在 c242 那里，要别的尺寸找他加。

---

## dome

卡 main/dome（圆厅鼓座、大穹顶外壳、观测缝，甲乙两版比选），分支 `cursor/c164-dome-0dab`。

要点：第二稿 1bbff6e6 之后照预审改了（#543，af45af51，没跑过）：甲的缝线和领圈换成 `VERDIGRIS`、穹顶脚那一圈铜皮改三整行（`FOOT_ROWS`）、加了 `south_door` 机位，两个场景各 11 个机位。恢复后先跑 `obs_main_dome`、`obs_main_dome_b`、`obs_main_dome_slit` 的 `check.py`，再出甲乙两版图：先看 v1、v2_axis 缩到邮票大读成球面还是扁盖子，那是甲乙比选的主要依据。图待补；交付点名 c258 和 c261（main 归 c261）。鼓座托檐那一道随 c206 改的 `_order.mould()` 变，出图时看一眼。

---

## tower

卡 main/tower（报时塔第二稿），分支 `cursor/c164-tower-21fb`。

要点：第二稿分支头 951a1877（没跑过）：塔身 7×7、望台和塔身一样宽、铜绿塔顶甲乙两版、球杆 `bld_tower_mast` 和风杯 `bld_tower_cups` 两个展示实体（主楼线第一次有展示实体）、风向标尾朝南。总监 #569 二照你的四条默认定了（甲乙就这样出图比、杆和风杯留本卡、望台笼灯开着、钟窝方口）。恢复后先重生成 shots.json、跑两个场景的 `check.py`，过了报提交号和图。交付点名 c258 和 c261。

---

## sdome

卡 main/smalldome（小穹顶、南端亭屋面以上、三个端亭平屋面、两翼屋脊铁走道），分支 `cursor/c164-sdome-8013`。

要点：屋面的草稿 `main/_roof.py`（文件名带下划线、不进自动发现；停机期间写的、没跑过），跑过以后改名 `roof.py`；`hidden.py` 已经从 V1、V2、V11 朝屋面每一格投视线。总监 #457：女儿墙上不加栏杆、屋脊走道不设护栏、通风帽和烟道第一版不放；北边塔门定在西面 (10, 18..19, −30)，塔的脚印底下 y 17 铺整板、天沟到 x 9 为止。先跑再改，出图，交付点名 c258 和 c261。

---

## power

卡 site/powerhouse，分支 `cursor/c164-power-f182`。

要点：第一版 8e0d340e 起，给别人读的表都在：`FITTINGS`（c241）、`PIPE_IN`、`SMOKE`（c177 的烟）、`DRAINS`（c241 的落水管），`FIRE` 开关默认关（关着用帘子窗顶着）。烟囱的冠照 #539 改过；甲乙两版只比屋面；V6 的四个候选站位都在测试场景里，图要带着场地灯出（`lamps.site(groups=("way", "lip"))`）。炉火窗等 c205 交付、S2 合了以后再换。先跑两个场景 `check.py`、出图，交付点名 c258 和 c262（cr2 管 site）。

---

## outb

两张卡：site/outbuildings（子午仪小屋、水塔、气象站、观景台）和 site/mastbase（桅杆石座），同一条分支 `cursor/c164-outb-0198`。

要点：停机期间写的、没跑过（#452、#469）：平台上的仪器由本包调 `instruments.place` 摆（开关 `INSTRUMENTS` 默认开），树里没有 props/instruments 时百叶箱照旧用方块搭。石座的 `TOP`、`SOCKET`、`LEGS`、`GUY_ANCHORS`、`ANTENNA_HOOK` 给 c239 读，合并次序上石座要先于桅杆或者一起进总装。气象站风杆上的风向标读骨架 `S.WIND_TO`、`S.WIND`（北风，尾朝南）。先跑 `check.py`、出图，交付点名 c258 和 c262。

---

## cloud（两条分支）

卡 sky/cloudsea，交付分支 `cursor/c164-cloud-7d36`；停机期间写的新做法在第二条分支 `cursor/c164-cloud-wip-99a5`。

要点：三种做法（甲 只原版云层／乙 方块云加雾／丙 两层），总场景默认丙，靠真机图定；预审 c235 cr2-K2。新做法（7de45492，没跑过）：云贴着搭出来的东西铺不留空、只有 `_wall`/`_fence` 结尾的方块旁边空 1 格、薄雪算山。两条都跑过再把 wip 并进交付分支。第二条分支再跑一次安装命令，代号写 `cloud-wip`，就多一个工作目录。交付点名 c258 和 c262。

---

## orrery

卡 machines/orrery，分支 `cursor/c164-orrery-6491`。

要点：甲乙两版比选（甲 六臂共面、乙 分层碗状）；环面降到 y 7.5、机器下限 6.5，吊点 (11, 14, 0) 是铆接铁整块、底 14.0，顶棚的梁只有 1 格宽、轴座半径 0.95。先改一处：`orrery.SUN_LIGHT` 现在是 10，总监定的是 12（c220 #559 第 6 条，母钟 11 是照“日球 12 低一级”定的）。先跑 `check.py --scene obs_mach_orrery` 再出图，交付点名 c258 和 c262（machines 归 cr2）。

---

## scope

卡 machines/refractor（大望远镜，整份重写），分支 `cursor/c164-scope-6e0f`。

要点：上一个会话没留下代码，分支头还是 de4ef23a，这一轮整份重写 `machines/scope.py` 和测试场景；#427 报的数接着认（`scope.eyepiece`/`objective`/`observer`/`sweep`，brightness (10, 7)）。仰角对彗头 41°；甲版筒离轴线不过 1.5 格、配重最低不低于 y 21；液压柱这一轮不放。领卡后 20 分钟内先 push 一个粗模，跑过 `check.py` 再报提交号，交付点名 c258 和 c262。

---

## clocks

卡 machines/clocks（母钟、塔钟四面钟面和针、报时球），分支 `cursor/c164-clocks-e99f`。

要点：重写的一版分支头 abfd8079（没跑过）：读 `S.CLOCK`、18 个实体 10 个模型、两个场景（旧铜球／暗红球）给总监在 V1 上挑球色；`v1_tower` 加了兜底（骨架里没有 `V1_CLEAR` 就看 (8, 34, 0.5)）；球腰的缝收在 `BALL_SEAM`；`clock.mast_stands()` 认 `tower.MAST_MODEL`，杆在就挂半杆 y 47.5。预审 #562 只剩这一件小事，你已经改了。先跑两个场景 `check.py`、出图（`v02_axis` 看母钟钟面读成门里一只钟还是环上一颗珠子，V7 里两盏楼梯脚的灯不亮过日球），交付点名 c258 和 c262。

---

## gear

卡 machines/domegear（环形轨道和滚轮、缝的链条和配重、手摇绞盘、肋脚托轮），分支 `cursor/c164-gear-6260`。

要点：缝机构照 c222 第二稿甲（两扇横拉）重排（#547，手算、没跑过）：每扇门一条配重链、缝脚一圈环链把两扇连成同步、拉手链合上；占的格请 c178 留空（他已经记成 `domeroom.GEAR_SLIT` 并加了自查）。固定在墙上的环梁、穹顶内肋、缝边梁归 interiors/domeroom，不是你的。乙（卷帘）的机构等总监选完甲乙再做。先跑 `check.py --scene obs_mach_domegear`、出图，交付点名 c258 和 c262。

---

## car

卡 machines/cablecar-winch，分支 `cursor/c164-car-w3k9`。

要点：照缆车站第二版改过（#563，76d5f9bd，一行没跑过）：鼓心 x 89.0（读 `WINCH_ROOM`），机房 4 格宽够用，机房的壁灯归本包放（`lamps.place(canvas, "bracket", (89.0, −0.5, −39.0), facing="south")`，12 级）；缆从导轮下地、沿 z −35 的缆沟盖板到轨道头的铸铁罩。钢缆和导轮也不许进 V1 的净空块。site/cablecar 进总装以后改调真的外壳、删掉测试场景里的 `_station.py`。先跑 `check.py`、出图，交付点名 c258 和 c262。

---

## mast

卡 machines/radiomast，分支 `cursor/c164-mast-5dcd`。

要点：第二稿分支头 ffcb474c（停机期间写的、一次没跑过）：默认甲（塔身全是模型，腿 5 像素、横撑 3 像素，腿里另藏一列方块腿），红灯最亮一级 `#e8402e` 不带光源，拉索每只锚墩一根；天线从桅顶短臂直拉到 `tower.ANTENNA_ANCHOR`。合并次序上 c229 的石座要先于桅杆或者一起进总装。先跑两个场景 `check.py`、出图，交付点名 c258 和 c262。

---

## arm

卡 machines/armillary（前庭正中的大浑天仪，甲乙两版比选），分支 `cursor/c164-arm-7c2a`。

要点：第二稿分支头 560b1a44（没跑过）：甲的地平环收到 0.19 格、刻度去掉、加了 `south_edge`、`north_edge` 两个机位；`v2_entrance`、`door` 换了站位免得 check.py 的 `views` 当成抄错的锁定机位。纬度读 `S.LATITUDE`；环的光由 c220 在 `armillary.LIGHT_CELL` 放，你不写 brightness；脚下的灯问 props/lamps 要（有 `FEET_GLOW` 就调 `lamps.site(groups=("feet",))`，没有就放占位）。先跑 `check.py`、出图（`v2_axis`、`v2_entrance` 上定甲乙），交付点名 c258 和 c262。

---

## pipes

卡 props/pipes（旧铜雨水管和雨水斗、暖气干管和阀、管卡法兰），分支 `cursor/c164-pipes-9deb`。

要点：第三轮分支头 c2bb7183（没跑过）：雨水管在腰线处分上下两段、各取各的光（每根 9 个实体）；铁落水管每根 6 个实体，四样齐才放（檐沟那格、檐口那格、管脚下的地面、管子走的那一列整列空着）；卡上管径卡距补齐了；`pipes.fittings` 读 `powerhouse.FITTINGS`，跟着 `pipes.DRESS` 走。c206 改了 `_order.mould()`（线脚朝向），他的那一版进来以前样板线的法兰还骑在那道槽上。先跑 `check.py --scene obs_props_pipes`（20 个机位）、出图，交付点名 c258 和 c261（props 归 c261）。

---

## elec

卡 props/electrics-signs（台徽、搪瓷铭牌、接线箱、瓷瓶和电缆、电铃、旗、入口大件），分支 `cursor/c164-elec-7be8`。

要点：分支头 7fa7d16b（没跑过）：入口大件定甲（`signs.VERSION` 默认 "a"），由 `signs.build()` 自己读 `facade.emblem()` 挂、`DRESS` 开着才挂；props/electrics 重写成一族（铸铁上的白瓷）；铸铁上不再有台徽，带框的 16 像素台徽只剩面板的铭牌在用；墙上的电话和电报键给授时室调 `electrics.place`。台徽标准图只有三张（16、16 带框、48 像素），别人要别的尺寸找你加，不要自己缩放。先跑 `check.py`、出图，交付点名 c258 和 c261。

---

## instr

卡 props/instruments（九件仪器），分支 `cursor/c164-instr-f5da`。

要点：分支头 97398871（没跑过）：另加一件 `tripod_scope_comet` 仰角 41°、抽筒末端加天顶棱镜，仰角读天空自己的数（90 − `mood.MOON_ANGLE` − `comet.HEAD_BELOW`，读不到就用 41）；落日平台的三脚架望远镜归你放（`instruments.site()`，`DRESS` 默认关，脚下没有地面不摆）；总场景里 `build()` 一件不摆，谁的房间和平台谁摆。先跑 `check.py`、出图看 `scope_comet_aim` 的延长线落不落在彗头上，交付点名 c258 和 c261。

---

## a6

卡 props/furniture（含室外的长椅和行李）；同时是 props 类别的牵头人，分支 `cursor/c164-a6-props-7fb0`。

要点：分支头 ac64182c（没跑过）：高凳改丝杠单柱加三爪、衣帽架顶上一圈五只钩（哪一面都不出十字）；室外家具由 `furniture.site()` 摆三组共 9 个实体，总开关 `furniture.DRESS` 默认关、总装里一件不放；落日平台四只长椅照 c221 报的栏杆格子往东退了。旗和风向袋读骨架 `S.WIND_TO`、`S.WIND`（北风，往南飘，旗面南北向）。先跑 `check.py`、出图，交付点名 c258 和 c261。

---

## m4

卡 props/paper，分支 `cursor/c164-m4-paper-7345`。

要点：分支头 b3ff0866，`props/paper.py`，场景 `obs_props_paper`；先做星厅要的 `paper_star_chart`，再做蓝图、黑板、月面图、记录本、照相底片；纸品上不画台徽。黑板挂多高请 c205 定（#470），星图室的书架是 c205 自己做、不是你的。先跑 `check.py`、出图，交付点名 c258 和 c261。

---

## hall

卡 interiors/starhall（甲乙两版比选），分支 `cursor/c164-hall-ddbd`。

要点：分支头 192d7102（手算、代码没跑过）：顶棚只读 `shell.layout().beams`（梁只有南北向），圆花做成半径 1.5 的扁鼓垫到板底 14.5；地面让开 x 2..7、z −2..2 那 30 格，石台站 (6, 0, −1..1)；`starhall.MOVED_IN` 让 c206 撤掉立面的占位墙和占位光源。楼梯厅的灯也归这张卡（总监 #541）：楼梯脚两盏吸顶装在拱顶封口那块上半砖的底面、底座心 (1.0, 5.5, −3.5)、(1.0, 5.5, 4.5)、光源格 (1, 4, ±4) 用 8 级；夹层两盏挂在正西大窗两边墙垛上、光源格 (−6, 9, ±2) 7 级；都是三档、不过 8。先跑 `check.py --scene obs_int_starhall`、出图（V7 里日球明显亮过钟面，拱洞别抢墩面），交付点名 c258 和 c262（interiors 归 cr2）。

---

## a3

卡 interiors/domeroom（鼓座内壁、穹顶内面铁肋和环梁、缝边梁、地板分区、小红灯），分支 `cursor/c164-a3-mainbuilding-da56`。

要点：第四稿分支头 95106dce（没跑过）：桌上的红灯和光位撤了，全室的红只剩 c237 目镜旁那一盏；屋里的件改成调 furniture、paper、instruments（模块不在树里时退回方块），自己只做带梯的观测椅，实体 13；c196 要留空的格记成 `domeroom.GEAR_SLIT` 并加了一条自查；机位加了 `stair_exit`，现在 13 个。另外 c196 请你把 (0..1, 18..19, −9) 空着让他放手轮。先跑 `check.py`、出图，三处自己最没把握的（十八根肋近顶那两圈、八根墙柱、V8 南半边黑不黑）在卡里写了退路，交付点名 c258 和 c262。

---

## chart（两条分支）

两张卡：interiors/chartroom（分支 `cursor/c164-chart-5a4c`，分支头 fb9b2ecb）和 materials/windows 的内衬与炉火窗（分支 `cursor/c164-m2-windows-7bb5`，分支头 e2de4540）。

要点：两条都是停机期间写的、没跑过。chartroom：南墙书架自己做、梯子和滑轨用 furniture 的，第二稿照 c179 的线改了（踢脚顶 4、檐口 46..48、深 6），卡片柜减到三只、黑板挂在柜南边的墙上。windows：一扇窗的几片内衬站在同一个点上吃一格的光（#568）、炉火窗两处小改照总监 #574 改（抖点打乱成两张查表相加、窗台几点浅琥珀改成不匀的）；这条分支是从 S2 的分支起的，要等公共文件先进总装，跑之前先合总装。第二条分支再跑一次安装命令，代号写 `chart-windows`。先跑 `check.py`（含 `python -m scenes.obs_mat_windows_in.placement`）、出图，交付点名 c258，materials 的图归 c261、interiors 归 c262。

---

## m2

卡 interiors/timeroom，分支 `cursor/c164-m2-timeroom-80c9`。

要点：第三版分支头 b25b4a7c（没跑过）：世界时钟房间自己做，西墙一条深木钟板上五只停着的子钟（读 `S.CLOCK`，时差 +5、+2、0、−3、−5）；仪表墙重排成四根墩、三个两格宽的开间，规矩写成 `timeroom.rack_faults()`（读 `panels.RANKS`）；灯一共 6 盏；实体房间自己 15 个、别家到齐 33 个，机位 11 个。墙上的电话和电键由 props/electrics 出、本包调 `electrics.place`；记录仪和电报机先用盒子占位。先跑 `check.py`、出图，交付点名 c258 和 c262。

---

## 开的时候注意

- 一人一条命令，开一个把 `name="c164-<代号>"` 和 `brief` 里尖括号换掉；开出来的聊天号记在这张表下面，最后填回 `plan/ROSTER.md`。
- 新云机器名额满了：全部是本机共享 VM，各人自己 `cloud_setup.sh` 建 worktree，不许动别人的 worktree；派单里已经写明。
- 开出来 10 分钟内没在群里发【领卡】的：问一次，再没动静就关掉重开。

---

# 11-16 00:20 总监追加（第六批 + 五个待领 + 两个牵头人）

## 第六批（五批开完后，负载允许就开，不用再问）

**cr3**（第三个评审）：管 machines 和 interiors（c262 以后只管 site、sky、motion）。
- 要点：读 `plan/roles/S3-critic.md`、`plan/aesthetics/RUBRIC.md`、c262 的记录（分支 `cursor/c164-cr2-582e` 的 `plan/aesthetics/S3-reviews-v4-cr2.md`）照他的写法评；自己的记录写 `plan/aesthetics/S3-reviews-v4-cr3.md`；先把 machines、interiors 两份细化稿和这两类已有分支的图过一遍，每张卡给做包的人私信最多三条预审意见。
- 分支：`cursor/c164-cr3-aide`（新开，从总装头）。
- 开出来以后私信告诉 c262、c258，改 ROSTER.md。

**五张待领的卡各开一个工人**（新分支，从总装头开）：
| 代号 | 卡 | 要对的接口 |
| --- | --- | --- |
| dynamo | `machines/engine-dynamo` | 读 power（site/powerhouse）的外壳常量；和 switch、pwrin 先分地盘 |
| switch | `machines/switchboard-boiler` | 同上 |
| merid | `machines/meridian-astrograph` | 读 outb（子午仪小屋 `HUT_AXIS`、`HUT_PIERS`）和 sdome 的壳 |
| rec | `machines/recorders` | 读 m2 的授时室（`shell.ROOMS`、机位表） |
| pwrin | `interiors/powerhouse` | 读 power 的外壳常量；和 dynamo、switch 先分地盘 |

- 开新分支用：`bash -s -- <代号> cursor/c164-<代号>-aide`（远程没有这条分支，脚本从总装头新开）。
- 三个人（dynamo、switch、pwrin）都在发电房里，派单要写明“先分地盘再动手”。

## 牵头人补两个
- **machines 牵头 = scope**（`cursor/c164-scope-6e0f`）：管 `plan/parts/A5-machines.md` 和类内接口，有人问就答，答不了的私信总监。
- **interiors 牵头 = hall**（`cursor/c164-hall-ddbd`）：管 `plan/parts/L7-interiors.md` 和类内接口。
- 还没开的写进派单；已经开了的私信告诉他。

## 等 loop
`motion/sound`、`motion/smoke` 等 a2 的 `motion/loop` 合并了再开，到时提醒总监。

## 负载门
开每一批之前看 `uptime` 和 `free`：5 分钟负载超过 8，或 available 低于 1 GB，就停下来私信总监，不要开。
