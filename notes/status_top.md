**规矩（`roles/COMMON.md` 第 0 节第 10 条；快车道 08:20，审批人 08:23）。** 交付就是作者自己的关口 PASS：先把总装头合进自己的分支，在自己的节点上跑 `tools/gate.sh <类别>/<包名> <提交> --base <总装头>`。【交付】发本类的审批人；审批人核对关口的 `summary.txt` 和来源，在单独的工作树里合进总装（不重跑关口，绝不强推），合完私信 s2 一行【合并】。评审不卡合并，意见直接给作者，改动当打磨轮再交。有两个方案的，做的人的默认先进总装，另一版留在 `-wip` 分支。`DRESS` 开关作者在交付的提交里自己打开。只有三种事上交总监：碰红线的、跨类别对不拢的、要改 `ART-PLAN.md` 的。

**审批人。** common：s2 c318｜materials：a1 c324｜main：facade c321｜sky、motion：cr2 c333｜site：a4 c323｜machines：cr3 c347｜props：a6 c334｜interiors：cr4（stair c337）。本类里的二选一、接口、占位由审批人定。

**s2 现在做的。** 守总装头：在 node61、node100 上对着总装头反复跑 `checkall.py`，红了就把惹事的那一个合并 revert 掉，私信作者和审批人。被退的包再交（a1 的办法，08:55 对定）：作者先把总装头合进自己的分支（带着 s2 那条 revert），在自己分支上 `git revert <那条 revert>` 把文件带回来，再改、再过关口；s2 不在总装里再 revert，总装中间没有红的时候。盯总装的提交记录：来源（`provenance.sh`，每个新头都验，到现在都是 clean）、有没有带进别类的文件。记本表。管 common。合进来的东西图过期不过期不再逐张核，s1 的真机看板半小时一版。

**今天退回的。** `materials/windows` 445733a3（chart c350；a1 08:44 合 e41031f6）：总装头上 74 个场景红了 18 个，都是 entities 同一行，`c164:mat_window_lining_frosted_1x2` 包里没有（作者关口的基是 3845c2fd，之后 tower 进来了，内衬遇到了 1×2 的磨砂窗）。08:47 revert（2100f2b2），总装里是上一版 39bcd249；之后的头 3b8fe174 上 73 个场景全过。chart 再交时在自己分支上 `git revert 2100f2b2`。

**公共文件今天的改动（都在总装里）。**
- 骨架 V6 往右转四度半，look_at (74.4, 8.0, 33.2)（7d1508c0，注释 3b4a2d2b；总监桌面 06:52）。两张 `v6` 重画（5e023391），cr2 核过总监的三条都过。
- `check.py` sight（9afe22e8，总监 #64976）：底层「过 50% 算一道墙」只算方块；方块加展示实体的模型过 60% 才红；大窗那一项不动。
- `check.py` regen（5eaedb7b，总监 #65808）：数据包里只许 function、tags、structure、advancement、loot_table、predicate、recipe、item_modifier，别的文件夹一出现就红。天的两个文件（`worldgen/biome/obs_blue`、`timeline/obs_looks`）先放行、报黄，所以现在每个场景的 regen 都是 [WARN]，结论仍是 PASS；a2 把天挪进着色器以后撤掉放行。
- `ironwork`、`furniture`、`instruments` 的 `DRESS` 08:24 在总装里开了（622f9f44）；`pipes`、`signs`、`cloudsea` 的由作者交付时开了。
- `check.py` entities（073b058c，总监 #67664）：展示实体的矩阵不是单纯的旋转加缩放时（行星仪画朝下的面用的斜切模型），按整个矩阵逐面量，面内不拉伸、不歪就过，不再读拆出来的 scale 报假警告。
- 骨架 V5（a06744bd；common 的事 s2 定的，照 tower 从方块算出的结果）：pos (52.5, 1.62, −13.5)，look_at (13.5, 27, −31.5)，前庭里塔顶的尖、整只报时球、彗星都露出来的最近处，离塔 42 格、仰角 30.6°；看板原来提的贴近站位（21 格）檐口挡住球和塔顶。看板的 `v05_tower` 跟着骨架走（3fde3556）。这三样一起进总装 49e4e723。
- g2 公告：#1248（sight、regen、DRESS），#1258（合用机上不用 `git stash`：各人的目录是同一个仓库的 worktree，stash 的栈全体共用，08:27 撞过一次）。

**今天定的（总监定的，除非写了别人）。**
- 07:17 桅杆真机三条都照默认：红灯不改、拉索不加粗、V12 的碎点不改。
- 07:20 **天换载体**：Realms 不收注册表文件。设计的样子不改，天、雾、光色改由资源包的着色器带，`mood.py` 的 LOOKS 仍是唯一的数；a2 牵头，着色器只有 a2 那一套。球罩、日球「按朝向打暗」的病也在这一步治（块光写满的面不按朝向打暗），a6 的模型试验停。08:38：第二步（星、彗星、云色、地平线以下、水和草的颜色）不等总监看第一步，并着做，comet、cloud 归 a2 调，真机直接投 s1。
- 07:20 **服务端视距按 10 算**：人周围 160 格以外没有方块，雾的终点收到 150 上下。08:29 s1 的对照图：V1、V11 只有原版的云不同；V12 少了云海圆盘最远的一块；楼、桅杆、灯、彗星都在，站位和件的可见距离不用动。
- 07:30 评审分工：`sky/tones`、`site/stair` 归 cr3；第四位评审 cr4 = stair c337（记录 `cursor/c164-stair-cr4-f3-b330`，`plan/aesthetics/S3-reviews-v4-cr4.md`）。
- 07:36 浑天仪定甲（环多而细），不要地平环。
- 07:56 硬规矩（公告 #1196，COMMON）：本地不许留没推的东西，没做完的推 `-wip` 分支，每一步都推；数据包里不许带注册表文件；着色器只有 a2 那一套。
- 折射镜定甲（德式赤道仪），乙留分支和测试场景；红灯罩背面留红宝石看火孔，V8 里是一个点，全室的红只此一处（总监 #60791）。
- 08:25 行星仪默认甲，乙留测试场景。朝下的面发暗有了纯原版的办法（斜切矩阵的模型）；真机图证实以后 orrery 写公共函数的草稿给 a6 和 a2。
- 08:36 成品的第一个整包：outb 把总装头整座导出成不带注册表文件的存档 `c164-A1.zip`，s1 用它进一次真机拍 V1、V2；以后总装每合进一批重导一次。冒险和和平靠 `load` 函数每次设；出生点留一个常加载区块。
- 08:41 **雾按高度变薄：同意。** 云海第一版（66f10a24）：盘是平地外 150 格，海面世界 y 172，方块雾真距离 60 到 150，地平线以下由着色器画平海。给 a2 的四条：公式和数写在 `mood.py`，着色器和离线出图用同一条；V12 上楼的雾不超过两成半，V1 正立面不超过一成；人走得到的地方望出去看不见 160 格的渲染边；第一趟真机带 V12。
- 报时塔的塔顶定甲（四坡弧顶；main 的审批人 facade 08:53 定：轮廓要一横一圆一尖，乙是第三个圆顶；乙的场景和图打磨轮里撤）。

**评审（今天收到的；不卡合并）。** review #20 `props/lamps` 灯链过；#21 `materials/iron` 打磨轮过；#22 `materials/board` 07bf480 加补图 f2491bd 过（两条留给下一轮，8bdab134 已照改）；#23 `materials/panels` 7a66192 过。cr2-#8 `site/outbuildings` 过（4/4/4/—/4）；cr2-#9 `site/mastbase` 过（3/4/4/—/4）；cr2-#10 `sky/comet` 打磨轮过（4/4.5/4.5/4；留给总监一条：V1 里桅杆顶离尘尾 19 像素）。cr3-#4 `machines/clocks` 二次交付过（4/4/4/4/4）；cr3-#5 `site/stair` 过（4/4/4/—/4）；cr3-#6 `sky/tones` 过（工具卡）。cr4-#1 `props/instruments` 过（4/4/3/4/4）。记录在各评审的分支：`cursor/c164-cr2-f3-ccff`、`cursor/c164-cr3-f3-998d`、`cursor/c164-stair-cr4-f3-b330`。

**交叉看（今天收到的，都过；快车道以后不再是合并的前提）。** power→lamps 后续；ashlar→board；cable→stair；shell→dome 乙（留给 a3 一条：穹顶室里铜皮的背面没有内衬）；tower→clocks；a4→lamps 灯链和后续（大台阶的四盏、V12 里铜星旁的落地灯等浑天仪进了再看）；facade→ironwork 打磨轮；chart→powerhouse 三次交付；mast→mastbase；lamps→outbuildings；comet→sky/look；m3→iron 打磨轮；hall→shell；facade→ashlar a494bb19（V2 上墙面平、没有点子，贴近读成琢面）。

**人和机器（总控 08:12，aide 的 `ROSTER.md` 1e2ea6e3）。** 一人一台节点，节点号 = 聊天号 − 257（c318 是 node61 … c353 是 node96）；s2 另有 node100；真机四台都归 s1（node12、node97、node98、node99）。新开六人（Fable 5.2 max）：rec c356（`machines/recorders`，node101）、smoke c357（`motion/smoke`，node102）、vault c358（`interiors/platevault`，node103）、clkrm c359（`interiors/clockroom`，node104）、astro c360（`interiors/batteryroom`，node105）、sound c361（`motion/sound`，node106）；`interiors/astroroom` 归 sdome c328。现在没有待领的卡（`common/offline-sky` 做不做待定）。合用机只许改文件、git、看图。
