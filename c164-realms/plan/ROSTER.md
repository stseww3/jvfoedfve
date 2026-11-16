# 名单：第 3 班（11-16 凌晨起）

总监助理（代号 aide，聊天 c320）维护，最近一次更新 11-16 12:58。点名只点「聊天号」一栏；聊天号“—”是还没开出来。前两班的聊天号（c176 到 c246，c258 到 c297）都停了，点了没人醒。

- 总监：A0，聊天 c164。11-16 08:24 起只有三种事找他：碰红线的、跨类别对不拢的、要改 `ART-PLAN.md` 的。
- 总监助理：aide，聊天 c320。名单上的事找他：谁是谁、找谁对接口、新分支报给他、节点不回单了报给他。手上的卡都交付了：11-16 09:12 起先找本类的审批人领他清单上的活，本类没有活的再找总监助理跨类派。
- 总控：`ctrl`。节点的事由总监助理去找它，别人不用找。
- **审批人（总监 11-16 08:24；细则和合并的四步在 `roles/COMMON.md` 第 0 节第 10 条）：每个类别一个，拿本类的合并钥匙。【交付】发给本类的审批人，不再发 s2；本类里的二选一和接口也由他定。**common：s2（c318）；materials：a1（c324）；main：facade（c321）；sky、motion：cr2（c333）；site：a4（c323）；machines：cr3（c347）；props：a6（c334）；interiors：cr4（就是 stair，c337）；**11-16 11:45 起由 cr3（c347）代，到 stair 回来为止**。s2 守着总装头是绿的、记 STATUS、解公共文件上的冲突。
- **掉线的三位（11-16 11:45，桥上显示「没人接手」；总监的公告：不等他们回来）**：stair（cr4，c337）、hall（c348）、comet（c330）。interiors 的交付发 cr3，V8 到 V10 的分也由他评；s2 11:48 代 cr4 合了两包只加灯的（m2 授时室壁灯 39d46055、hall 西门 3b09f9d）；V4 的门洞交 vault（c358）：做在 hall 的包里、从总装头拉支，先在 A8 的图上量一次，够了就不动；comet 手上没有收尾的活，不补人。再有人掉线，总监助理直接报总监谁手上有四件事里的活。**12:52 orrery（c343）也掉了；12:53 总监请总控把四位都重拉了（上下文留着；机器 orrery node57、stair node51、hall node62、comet node44），回来的先私信总监助理报到、读 `plan/fine.md`，代着的人把那一块交回**：行星仪还是 orrery 的（气象站的风向标、自记气压计和前庭测风杆留给 power，探空气球先放）；星厅还 hall（天花的星座轮流亮、弧光灯、正门的铁门留给 lights）；大台阶还 stair；comet 回来找 cr2。十分钟没报到的，总监助理报总监再拉。
- **节点（总控 11-16 08:12 放出共享池，08:14 认了这张固定表）：一人一台，节点号 = 聊天号 − 257**（c321 是 node64，c353 是 node96），「节点」一栏照这个填了。两处例外（总控 11-16 09:33）：node61 总控 09:20 拨给了别的项目的人（c274，独占），**谁也不要再往 node61 投**；s2 改用 node62（独占 c318）和 node100 两台并行，s1 只用真机。**11-16 10:56:30 三台母机挂了，node61～106 整段下线（总控 11:22）**：这一段谁也不要投，单投出去 15 分钟没回执、-wip 也没有提交就当丢了；**管理员 11:37：掉的那批多半回不来；总监 11:39：照手上 8 台干到底，回来了算白捡**（总控 11:58:30 起分批恢复，先给别的项目，第三批起按原归属还，名单以总监助理在群里的话为准；这 8 台留到 12:50）。**8 台谁用**（总监助理 11:43，g2 #1662；各一次一单，别人把命令原文私信持机器的人代投；投出 15 分钟没回执找总监助理）：node4 outb（锁 c340；导出，导览进游戏的验证）；node12、node5、node6 s1（验收图、导览验收）；node17 facade（锁 c321；室外走查，代投 a4 每版的室内账）；node9 sound（锁 c361；对头量暗格）；node7 lights（锁 c331）和 node8 tower（锁 c327）代投长单。总监机（`tools/a0job.sh --no-push`）收 s2 的 checkall 和四件事里头一次的本场景 check，投前私信总监助理点名，一人一次一单（已点名、写好就投的：a6、smoke、a4、rec、ashlar、m2，和修室外走查三条小毛病的 cable、sdome）。都不出图：出图只有 s1 进存档拍的那一套；合用机上不跑任何检查和出图。**12:12 第二轮开工以后（总监助理 g2 #1707、#1712、#1719）**：本场景的短 check 写好先推、直接投总监机，人人都算点过名，一人一次一单（总监机 12:16 起三个工人并着跑：短单三单同时，长单一次一个）；node7、node8 总控 12:14 对 c318–c361 全开了，自己投长单（整山的 check、底件测试；火车这条线和 sky、motion、site 用 node7，其余用 node8），不出图，不用再找 lights、tower 代投；node5、node6 归 s1（总控给新六位也开了，但别投）；进游戏试的找 outb（node4）和 s1。**12:33 池子顶到 106 台，都回来了（总控的定稿；总监助理 g2 #1746；上面那张「聊天号 − 257」的固定表作废，「节点」一栏照新的填了）**：c321 到 c353 一人一台，节点号 = 聊天号 − 286（facade node35……mast node60，cr3 node61……ashlar node67）；rec node68、smoke node69、vault node70、clkrm node71、astro node72；sound node9；s2 node33、node97；s1 跑游戏的 12 台 node34、93–96、98–100、103–106（别人别投）；总监自用 node12、node101、node102（验包和审图）。**总监名下另 16 台交总监助理当公共池（对 c318–c361 全开）**：node73–76 给 s2 跑关口和 checkall；node77–80 是火车这条线的第二台（a2 node77，cable 和 m1 node78，mast node79，a4 node80）；node85–92 公共，自己的机器忙了再投，一台一单。自己的机器上 check、关口、离线自查图都可以跑，一次一单；新盘先探一单，被拒是授权没到，过五分钟再探。**12:49 总控：node43、46、49、52、55、58 是拉不回来的废槽，作废别投，换成 cloud node117、review node118、m1 node119、cable node120、lamps node121、scope node122**（总监助理 g2 #1809）；**12:54 又两台废槽：node41 换成 tower node83，node47 换成 cr2 node8（node8 从此是 cr2 自己的，别人的长单改投自己的机器）**；smoke 的 node69 没死，是卡在前一单上，别重投，等它回执，这期间用 node85。**公共池 12:55 起**（都对 c318–c361 开着）：node73–76 和 node90–92 给 s2 轮着查头，node77–80 是火车线的第二台，node84、85–89、107–116 谁的号不通就私信总监助理要一个，不要自己挑（免得撞单）。谁的号探两次不通就私信总监助理。主 Agent 只剩一台在带七十多个会话（总控 12:33）：派单慢、会话看着卡住多半是排队；谁十分钟没动静，总监助理报总监，总监请总控重拉。8 台留到 16:00；池子第一批 12:25 入网，node97 到 99 在最后一批。池子不通时怎么合，见总监 11-16 11:16 的公告：只加灯、本场景 check 跑过的包审批人先合，合并说明写「关口待跑」；一行没跑过的先跑一次 check。11:35 取的头 1a0f1af9 是 A7（11:42 交给管理员），12:00 取头导 A8，赶不上的进 12:30。共享池没有独占锁，不用授权就能投；池子里可能有别的项目的人，所以一人一次只跑一单，不连投，超时写够，结果推回分支，节点上不留东西。新盘是空的：头一单先投一个 `echo ok`（timeout 60 秒）探一下，一分钟不回就找总监助理；装环境的那一单必须是这台上唯一的一单（`nodejob.sh` 自己装，慢一两分钟不算故障）。**推送（总控 11-16 09:26）**：回执写 `pushed=no`、但节点自己改用 gh 凭据重推成了的，不算事故，继续跑；`pushed=no` 且重推也失败，或者推送后远端没有那个提交的，立刻停下，把节点号、op 号、完整报错（带令牌的先抹掉）私信总监助理，他转总控；谁也不要改节点上的令牌、凭据，也不要改 `nodejob.sh`。
- 别的机器：s2 的 node100（守总装头的 checkall）；真机四台 node12、node97、node98、node99 都归 s1，总装头的整套看板半小时一版，谁要真机图直接私信 s1；node101 到 node106 总控 08:36 独占给了新开的六个人；总监机（`tools/a0job.sh`，说明在它开头和 `roles/COMMON.md`）照旧接单，当后备，一个人一次只放一单。冻住以前的 node33 到 node60 和借用过的 node4、5、6 都不再用。现在没有备用机：哪台不回单（回执过了时限十分钟还不到）就报总监助理，由他找总控要，**谁也不要自己去动那台机器**。
- 「有效头」是第 1 班的前任留下的最后一个提交，**你的新分支从它开**（`roles/COMMON.md` 第 2.1 节的安装命令，第三个参数）。旧分支的头是第 2 班的，不许用（`roles/HANDOVER.md` 第 0 节）。
- 新分支叫 `cursor/c164-<代号>-<包名>-f3`（系统要求你的分支名带固定后缀的，接在 `-f3` 后面）。开出来以后在【领卡】里报给拿合并钥匙的人和总监助理，填进「新分支」。

## 常驻

| 代号 | 聊天号 | 节点 | 接手 | 岗位 | 旧分支 @ 有效头 | 新分支 |
| --- | --- | --- | --- | --- | --- | --- |
| s2 | c318 | node33、node97；公共池 node73–76 跑关口和 checkall | c188 | 技检；common 牵头和审批人；守着总装头是绿的（反复跑 checkall，红了退惹事的那一个合并）、记 STATUS、解公共文件的冲突（11-16 08:24 起各类的包由本类审批人合） | `cursor/c164-s2-integrator-927e` @ `8f626b20` | `cursor/c164-s2-fable-89df` |
| s1 | c319 | 跑游戏的 12 台：node34、93–96、98–100、103–106；另 node12、node5、node6 | c189 | 出图（拿出图钥匙）：整座的看板图、真机图；`common/plots-shuttle`、`common/offline-sky` | `cursor/c164-s1-render-9df7` @ `9cbe672b` | `cursor/c164-s1-render-f3-fd9c` |
| review | c332 | node118（node46 是废槽，12:49 换的） | c219 | 评审：materials、main、props（总监 11-16 07:30 加了 cr4：props/instruments、props/furniture 这两件头一轮的归 cr4） | `cursor/c164-review-0eb8` @ `ef09c638` | `cursor/c164-review-f3-3c69` |
| cr2 | c333 | node8（node47 是废槽，12:54 换的；node8 别人别再投） | c235 | 评审：site、sky、motion（总监 11-16 07:30：sky/tones、site/stair 这两件挪给 cr3） | `cursor/c164-cr2-582e` @ `47be4fe6` | `cursor/c164-cr2-f3-ccff` |
| cr3 | c347 | node61 | （新岗位） | 评审：machines、interiors；总监 11-16 07:30 起另评 cr2 挪来的 sky/tones、site/stair | 从总装开 | `cursor/c164-cr3-f3-998d` |
| aide | c320 | 不用 | （新岗位） | 总监助理：名单、谁闲了给谁派下一张卡、每小时一份进度 | 从总装开 | `cursor/c164-aide-f3-b9ab` |

## 工人

第二张、第三张卡（“然后”后面的）等前一张交付了再开；每张卡一条新分支。

| 代号 | 聊天号 | 节点 | 接手 | 卡 | 旧分支 @ 有效头 | 新分支 |
| --- | --- | --- | --- | --- | --- | --- |
| a1 | c324 | node38 | c176 | materials/board；materials 牵头 | `cursor/c164-a1-materials-3930` @ `db5682e9` | `cursor/c164-a1-board-f3-09d2` |
| m1 | c335 | node119（node49 是废槽，12:49 换的）；火车线第二台 node78（和 cable 合用） | c194 | materials/brass-oldcopper-small（补图）、materials/panels 打磨轮；然后 props/instruments（接 c199） | `cursor/c164-m1-brass-fa68` @ `a2370b00`、`cursor/c164-m1-panels-polish-bc45` @ `baccd973`；`cursor/c164-instr-f5da` @ `97398871` | `cursor/c164-m1-brass-f3-c367`、`cursor/c164-m1-panels-f3-c367`、`cursor/c164-m1-instruments-f3-c367`、`cursor/c164-m1-domeboard-f3-c367`、`cursor/c164-m1-wayspier-f3-c367` |
| snow | c336 | node50 | c194 | materials/snow；然后 props/paper（接 c197；11-16 07:49 交付）（interiors/batteryroom 11-16 07:52 派给过他，没开工，总监 08:36 给了新开的 astro；`cursor/c164-snow-batteryroom-f3-17de` 留着不用） | `cursor/c164-m1-snow-bc45` @ `51f2fd69`；`cursor/c164-m4-paper-7345` @ `b3ff0866` | `cursor/c164-snow-f3-17de`、`cursor/c164-snow-paper-f3-17de`、`cursor/c164-snow-batteryroom-f3-17de`、`cursor/c164-snow-chartshelves-f3-17de`、`cursor/c164-snow-astroroom-f3-17de` |
| m5 | c352 | node66 | c198 | materials/iron 二次交付；然后 machines/domegear（接 c196） | `cursor/c164-m5-iron-8757` @ `3c2120de`；`cursor/c164-gear-6260` @ `c7045d80` | `cursor/c164-m5-iron-f3-b9c1`、`cursor/c164-m5-domegear-f3-b9c1`、`cursor/c164-m5-chartengine-f3-b9c1`、`cursor/c164-m5-walklight-f3-b9c1` |
| ashlar | c353 | node67 | c204 | materials/ashlar 打磨（新台徽、细琢面的长短石）；然后 machines/armillary（接 c246） | `cursor/c164-ashlar-2cc1` @ `f57e5576`；`cursor/c164-arm-7c2a` @ `724d26be` | `cursor/c164-ashlar-polish-f3-799b`、`cursor/c164-ashlar-armillary-f3-799b`、`cursor/c164-ashlar-gallery-f3-799b`、`cursor/c164-ashlar-audit-f3-799b`、`cursor/c164-ashlar-plaques-f3-799b` |
| facade | c321 | node35；另 node17（室外走查，代投 a4 的室内账） | c206 | main/facade；main 牵头；然后 common/walk 的 walk-out（室外走查，P1，11-16 05:30 总监派；手上的短活先收尾） | `cursor/c164-facade-229b` @ `2c482b37` | `cursor/c164-facade-facade-f3-81a0`、`cursor/c164-facade-walkout-f3-81a0` |
| shell | c325 | node39 | c231 | main/shell | `cursor/c164-shell-f063` @ `15b6cf2e` | `cursor/c164-shell-f3-3067`、`cursor/c164-shell-timedoor-f3-3067`、`cursor/c164-shell-battdoor-f3-3067`、`cursor/c164-shell-doorkit-f3-3067` |
| dome | c326 | node40 | c222 | main/dome；然后 machines/engine-dynamo（11-16 04:50 派，没有前任，从总装开；dome 被退回时它优先） | `cursor/c164-dome-0dab` @ `ecda0e1e` | `cursor/c164-dome-f3-a244`、`cursor/c164-dome-engine-f3-a244`、`cursor/c164-dome-roofways-f3-a244` |
| tower | c327 | node83（node41 是废槽，12:54 换的） | c223 | main/tower | `cursor/c164-tower-21fb` @ `951a1877` | `cursor/c164-tower-f3-c402` |
| sdome | c328 | node42 | c224 | main/smalldome（含屋面）；然后 machines/meridian-astrograph（11-16 03:55 派，没有前任，从总装开；smalldome 被退回时它优先）；再 interiors/astroroom（P3，05:30 他要了，留给他；11-16 08:34 两张卡都交了，开工，从照相仪的分支头开；总监 08:36 认了） | `cursor/c164-sdome-8013` @ `98d469e8` | `cursor/c164-sdome-f3-1fe7`、`cursor/c164-sdome-astro-f3-1fe7`、`cursor/c164-sdome-astroroom-f3-1fe7`、`cursor/c164-sdome-astroshell-f3-1fe7` |
| a2 | c322 | node36；火车线第二台 node77 | c177 | sky/tones、motion/loop；sky 和 motion 牵头（motion/smoke、motion/sound 11-16 04:12 派给过他，没开工，总监 08:28 给了新开的 smoke、sound 两人）；**sky/safe-look**（总监 11-16 06:54 加：不带注册表文件的备用天，先交一页方案；头号风险，在他手上排最前，要节点和真机先给他） | `cursor/c164-a2-light-29fe` @ `b107652f` | `cursor/c164-a2-sky-f3-695d`、`cursor/c164-a2-loop-f3-695d`、`cursor/c164-a2-safelook-f3-695d`、`cursor/c164-a2-lookswitch-f3-695d` |
| lights | c331 | node45 | c220 | sky/lights（含洗墙轮）；**11-16 12:17 起星厅（interiors/starhall）的代主人**（hall 掉线；第二轮里星厅的两样会动的、十样细节、V4 和 V7 上圈的空处；交 cr3） | `cursor/c164-lights-007c` @ `8972aa88`、`cursor/c164-lights-wash-0fe3` @ `632a2c09` | `cursor/c164-lights-f3-9479`、`cursor/c164-lights-wash-f3-9479`、`cursor/c164-lights-pools-f3-9479`、`cursor/c164-lights-walk-f3-9479` |
| comet | c330 | node44 | c230 | **11-16 11:45 会话掉了，手上没有收尾的活，不补人**；sky/comet；然后 sky/ridges（P2，11-16 05:30 总监派，没有前任，从总装开；先找 cloud c329 对云海的高度；手上的打磨先收尾） | `cursor/c164-comet-986f` @ `b3950eb4` | `cursor/c164-comet-f3-793d`、`cursor/c164-comet-ridges-f3-793d`、`cursor/c164-comet-skyline-f3-793d`、`cursor/c164-comet-ridges-back-f3-793d`、`cursor/c164-comet-lamps-f3-793d` |
| cloud | c329 | node117（node43 是废槽，12:49 换的） | c227 | sky/cloudsea | `cursor/c164-cloud-wip-99a5` @ `55daddce` | `cursor/c164-cloud-cloudsea-f3-ad5e`、`cursor/c164-cloud-forecast-f3-ad5e`、`cursor/c164-cloud-guide-f3-ad5e` |
| a4 | c323 | node37；火车线第二台 node80 | c221 | site/terrain、site/court 打磨；site 牵头；然后 common/walk 的 walk-in（室内和屋顶走查，P1，11-16 05:30 总监派；手上的短活先收尾） | `cursor/c164-a4-site-2af2` @ `7a18bacc` | `cursor/c164-a4-site-f3-6824`、`cursor/c164-a4-walkin-f3-6824`、`cursor/c164-a4-walka6-f3-6824`、`cursor/c164-a4-walkcand-f3-6824` |
| stair | c337 | node51 | c225 | **11-16 11:45 会话掉了（interiors 的审批和 V8 到 V10 的分 cr3 代）**；site/stair（两次交付都过了关口）；**11-16 07:30 起转第四评审，代号 cr4**（总监定，评审排队过三件）：读 `roles/S3-critic.md`，先评 props/instruments、props/furniture（头一轮的两件，从 review 队里分来），不评自己做过的包；site/stair 被退回时它优先。interiors/batteryroom 现在归新开的 astro（草图、出图脚本、交接说明留在蓄电池室那条分支上，`0aae4ace`） | `cursor/c164-stair-4aad` @ `36220ac4` | `cursor/c164-stair-f3-b330`、`cursor/c164-stair-cr4-f3-b330`；`cursor/c164-stair-batteryroom-f3-b330`（交接用） |
| cable | c338 | node120（node52 是废槽，12:49 换的）；火车线第二台 node78（和 m1 合用） | c226 | site/cablecar（11-16 08:40 交付）；然后 machines/cablecar-winch（接 c240；08:42 开工） | `cursor/c164-cable-a47d` @ `4af8406b`；`cursor/c164-car-w3k9` @ `5a6186cc` | `cursor/c164-cable-cablecar-f3-9cf7`、`cursor/c164-cable-winch-f3-9cf7`、`cursor/c164-cable-outb-f3-9cf7`、`cursor/c164-cable-lights-f3-9cf7` |
| power | c339 | node53 | c228 | site/powerhouse；然后 interiors/powerhouse（11-16 04:14 派，没有前任；外壳被退回时它优先） | `cursor/c164-power-f182` @ `5ae1738e` | `cursor/c164-power-f3-2e4a`、`cursor/c164-power-interior-f3-2e4a`、`cursor/c164-power-darkroom-f3-2e4a` |
| outb | c340 | node54；另 node4（导出、进游戏的验证） | c229 | site/outbuildings、site/mastbase；然后 common/export（成品地图导出，现在空跑，P1，11-16 05:46 派，没有前任，从总装开；两张卡被退回时它们优先；**两个试传存档排最前**：蓝调的天用的注册表文件会让存档带「实验性」标记、Realms 不支持，总监 06:54 定为头号风险，要节点和真机先给他） | `cursor/c164-outb-0198` @ `6d320dd0` | `cursor/c164-outb-f3-f4b8`、`cursor/c164-outb-export-f3-f4b8` |
| a6 | c334 | node48 | c179 | props/furniture、灯的模型；props 牵头；然后入口两盏壁灯的球罩试验（评审 #20，总监 11-16 06:54 加，排在 furniture 交付之后） | `cursor/c164-a6-props-7fb0` @ `8026cccb` | `cursor/c164-a6-furniture-f3-4ad1`、`cursor/c164-a6-lamps-f3-4ad1`、`cursor/c164-a6-lamps2-f3-4ad1`、`cursor/c164-a6-plaques-f3-4ad1` |
| lamps | c341 | node121（node55 是废槽，12:49 换的） | c220 | props/lamps 的位置表和场地灯链；然后 props/electrics-signs（接 c242） | `cursor/c164-lamps-007c` @ `7c270e4c`；`cursor/c164-elec-7be8` @ `5ff667a1` | `cursor/c164-lamps-chain-f3-0dde`、`cursor/c164-lamps-elecsign-f3-0dde`、`cursor/c164-lamps-timeroom-wiring-f3-0dde` |
| m3 | c342 | node56 | c218 | props/ironwork 打磨轮（退回过）；然后 props/pipes（接 c241） | `cursor/c164-m3-ironwork-e6ba` @ `6f9eed36`；`cursor/c164-pipes-9deb` @ `c2bb7183` | `cursor/c164-m3-ironwork-f3-8e52`、`cursor/c164-m3-pipes-f3-8e52`、`cursor/c164-m3-walkroute-f3-8e52` |
| orrery | c343 | node57 | c236 | machines/orrery（**11-16 12:52 会话掉了，12:53 重拉**；回来还是他的，照 `plan/fine.md` 做到近层：月亮、传动轴、蜗杆；气象站三样和前庭测风杆 12:55 给了 power） | `cursor/c164-orrery-6491` @ `f3a7e462` | `cursor/c164-orrery-f3-46d7`、`cursor/c164-orrery-meridian-f3-1cec` |
| scope | c344 | node122（node58 是废槽，12:49 换的） | c237 | machines/refractor | `cursor/c164-scope-6e0f` @ `5c674377` | `cursor/c164-scope-f3-eeae`、`cursor/c164-scope-domechair-f3-eeae` |
| clocks | c345 | node59 | c238 | machines/clocks | `cursor/c164-clocks-e99f` @ `abfd8079` | `cursor/c164-clocks-f3-00d6`、`cursor/c164-clocks-hallwiring-f3-00d6` |
| mast | c346 | node60；火车线第二台 node79 | c239 | machines/radiomast；然后 machines/switchboard-boiler（P2，11-16 06:08 派，没有前任，从总装开；radiomast 被退回或来图时它优先） | `cursor/c164-mast-5dcd` @ `ffcb474c` | `cursor/c164-mast-f3-fc27`、`cursor/c164-mast-switchboard-f3-fc27`、`cursor/c164-mast-guide-f3-fc27` |
| hall | c348 | node62 | c243 | interiors/starhall。**11-16 11:45 会话掉了**：V4 的门洞由 vault（c358）接，做在这个包里；西门的灯 3b09f9d 由 s2 代合了（e10d420c） | `cursor/c164-hall-ddbd` @ `8f93cbdb` | `cursor/c164-hall-starhall-f3-2c05`、`cursor/c164-hall-lamps-f3-2c05` |
| a3 | c349 | node63 | c178 | interiors/domeroom；**11-16 12:56 起帮 cable 做火车客车里的散件**（行李箱和仪器箱、摇着的吊灯、时刻表、搪瓷号牌；单独的模型，跟车走；读 `cursor/c164-cable-train-f3-9cf7` 的 `machines/train.py`；cr3 批）；风暴信号杆排在它后面 | `cursor/c164-a3-mainbuilding-da56` @ `95106dce` | `cursor/c164-a3-domeroom-f3-f4f6`、`cursor/c164-a3-timelamps-f3-f4f6`、`cursor/c164-a3-timelamps-m2-f3-f4f6` |
| chart | c350 | node64 | c205 | interiors/chartroom、materials/windows 的内衬 | `cursor/c164-chart-5a4c` @ `fb9b2ecb`、`cursor/c164-m2-windows-7bb5` @ `bfb5420e` | `cursor/c164-chart-windows-f3-3477`、`cursor/c164-chart-chartroom-f3-3477` |
| m2 | c351 | node65 | c195 | interiors/timeroom | `cursor/c164-m2-timeroom-80c9` @ `6275b60b` | `cursor/c164-m2-timeroom-f3-364e` |

## 新开的六人（总监 11-16 08:36；Fable 5.2 max，聊天号 c356 到 c361）

一人一张开人时没人动的卡；节点是总控独占给他们的。六个人 08:45 到 08:52 都到岗了。

| 代号 | 聊天号 | 节点 | 卡 | 对口 | 审批人 | 新分支 |
| --- | --- | --- | --- | --- | --- | --- |
| rec | c356 | node68 | machines/recorders（第一批剩的那张，没有前任） | clocks（c345）：母钟和记录仪怎么接；m2（c351）：授时室木台上转鼓、电报机、传送管口的位置 | cr3 | `cursor/c164-rec-recorders-f3-aae1`、`cursor/c164-rec-astrodrive-f3-aae1`、`cursor/c164-rec-doorplate-f3-aae1`、`cursor/c164-rec-plaques-f3-aae1` |
| smoke | c357 | node69 | motion/smoke（没有前任） | a2（c322，motion 牵头）：循环和登记怎么用 | cr2 | `cursor/c164-smoke-smoke-f3-e07b`、`cursor/c164-smoke-guide-f3-e07b` |
| vault | c358 | node70 | interiors/platevault（南翼底层底片库和暗房，P3，没有前任）；**11-16 11:45 起接 hall 的 V4 门洞**（做在 `interiors/starhall` 里，从总装头拉支；先在 A8 的图上量一次，够了就不动；交 cr3） | 搭档 power（c339）：暗房的水槽、水管、小道具他来做；m1（c335）：仪器和配电板；shell（c325）：空腔和门洞 | cr4 | `cursor/c164-vault-platevault-f3-4cc1` |
| clkrm | c359 | node71 | interiors/clockroom（报时塔钟室，P3，没有前任） | 搭档 tower（c327）：塔身这一侧（井、沉格背板、窗后光源、开口）他来备 | cr4 | `cursor/c164-clkrm-clockroom-f3-82c8` |
| astro | c360 | node72 | interiors/batteryroom（北翼底层蓄电池室，P3；简报原写 astroroom，总监 08:36 改的）。接 stair 留在 `cursor/c164-stair-batteryroom-f3-b330`（`0aae4ace`）的草图、出图脚本和交接说明 | 搭档 mast（c346）：配电板和铜排他来做；hall（c348）：门；m2（c351）：上楼的两根立管；shell（c325）：空腔的门洞和楼板 | cr4 | `cursor/c164-astro-batteryroom-f3-e786`、`cursor/c164-astro-stairhall-f3-e786` |
| sound | c361 | node9 | motion/sound（没有前任） | a2（c322） | cr2 | `cursor/c164-sound-sound-f3-cbc6`、`cursor/c164-sound-lightaudit-f3-cbc6` |

总监原打算再开四个（n7 到 n10），总控说先别开（没机器），没开。

## 收尾（总监 11-16 09:12 的公告）

目标只有一个：一个能传上 Realms、人能从头走到尾的存档。outb 每半小时导一版整包，10:00 那一版是第一个候选版，以后每半小时一版，直到六条全过。**手上没卡的人不自己找细节磨，找本类的审批人领**；各审批人 09:35 前给本类的人发了一张清单（最多五条，抄总监助理，八份 09:27 到齐），清单以外的打磨先放下；跨类的事两位审批人直接对。

**11-16 11:39 起只做收尾的四件事（总监公告；这四件以外的打磨全停：写到一半的推到自己的分支留着，不投单、不交付，然后长等待待命，有事总监助理点名）**：一、剩下的暗格（11:52 总装 2b7eb71e 上量到 0，A8 起生效；不补的 48 格另列）；二、没过的图：V4（门洞，vault 接 hall 的）、V5（a4 换小屋的石料，f0925b0c 已合）、V10（m2，只动颜色和灯罩）；V6 在 A7 上过了；三、导览：mast、rec、ashlar、smoke、cloud，加 a6、outb；四、每版的导出、存档图、走查、打分、合并：outb、s1、a4、facade、s2、各审批人、四个评审、总监助理。A7（总装 1a0f1af9，11:35 取头）已交管理员；12:00 取头导 A8（8cddfa98），存着当底。**12:12 第二轮开工，「这四件以外的打磨全停」作废，见下一节。**

| 六条 | 谁管 |
| --- | --- |
| 1. 卡的第一版都在总装里（在做的 09:55 前交；赶不上的房间先用真门关着） | 各卡的主人，交本类审批人；关门找 cr4（他找 shell）。**10:24 齐了，这一条销账**：67 张卡全在总装里（最后两张是天文室 10:17、钟室 10:24）；`common/offline-sky` 总监 10:32 砍了，不做 |
| 2. 走查里挡人的全销账，每版候选在新总装头上重走一遍 | a4 管室内，facade 管室外，直接派给作者。**A7（1a0f1af9）上室内 0、室外 0**；室外新出的三条不挡人的小毛病总监定了都修、用屏障块不改外形：卷扬机矮栅（cable）、南观景台台阶脚的墩帽（a4，f8373a4a 已合）、端部露台女儿墙（sdome） |
| 3. 人走的路都有光 | lights（c331），各间室内的主人配合；暗格由 sound 量（每进一批灯重量一趟）；帮手见下表。**11:52 总装 2b7eb71e 上暗 0 格**（A7 里还是 39 格：授时室 22、西门里 17，两包 11:48 才合；不补的 48 格另列） |
| 4. 天进资源包着色器 | a2（c322），comet、cloud 帮 |
| 5. 真的客户端进 outb 导出来的存档拍 12 张，当候选版的验收图 | s1（c319） |
| 6. 12 张看板每张评审不低于 4 分；每张最弱的三处直接私信作者。**怎么算过（总监 10:29）：一张图五项平均不低于 4.0、没有一项低于 3**；过了的图里还是 3 的那一项记进打磨清单，候选版定了以后再做 | 主看的人：V2 到 V5 review（c332）；V1、V6、V11、V12 cr2；V7 cr3；V8 到 V10 cr4（11:45 起 cr3 代）。**A7 上过 9 张**，没过 V4 3.8、V5 3.8、V10 3.6。天、雾、远景以 s1 在存档里拍的那一套为准（他分支的 `renders/real-save/`） |

## 第二轮：细节、复古科技、会动（总监 11-16 12:12 的公告；卡页 `plan/round2.md`，有出入以公告和卡页后来改的为准）

管理员 11:59、12:05：细节不够，不够复古的科技感，加火车，所有东西都要会动；火车是地图的引子，飞艇不要。不急着投稿。版本从 B1 编号，每半小时一版。**12:36 机器回来以后节奏改三处（总监公告）：① 取头提前到每小时的 :40 和 :10，图在整点和半点给管理员**（B1 12:40，B2 13:10，B3 13:40；s2 取手上最新一个查过是绿的头，报 outb 和 s1；取头、导出、拍图三段并着跑）。**② 头要一直有人查**：s2 用 node73–76 轮着对最新的头跑关口和 checkall；审批人照旧先合（场景检查过了就合），合完马上在自己的机器上补跑关口，红了十分钟内修好或者退掉那一笔；s2 查出头是红的就点名是哪一笔，那一笔的审批人退。**③ 给管理员看的要有会动的**：s1 每版除了 12 张再录两三段小片（mp4，10 到 20 秒，720p 以内，8 MB 以下）。

**12:47 管理员 12:40 定了方向（总监公告；新的一页 `plan/fine.md`，和卡页有出入的以它为准）：「当前方案下再加10倍细节和各种内容 内容不要太多但一定要细和贴合地图」。**① **花样冻结**，丙四以后不加卡；下面表里划掉的是砍了的，动了手的把零件并进自己别的东西里。② **做细一样再开下一样**：远（60 格，轮廓）、中（10 格，零件）、近（2 格，痕迹和字）三层都到了才算交；线是任取一块 4×4 格的面，10 格处数得出不少于 10 件零件，2 格处每件上至少一处痕迹或字，室外不留大于 3×3 格、室内 2×2 格的空白面；细顺着结构走，远看的轮廓和明暗不许变花。③ **贴合地图**，设定一处定死、各处照抄：全站的钟一个时刻一个节拍（clocks 的常数），日期 `14 NOV` 不写年份，今晚的编号 `No. 2187`，彗星只叫 `THE COMET`，哪儿都不写台名、用台徽，机器铭牌一个样（号找 a6，`plan/parts/numbers.md`），门牌深蓝底白字，管子的色环和编号找 m3，全站一套字（a6 发取字的函数）。④ **预算**：展示实体全图 2600 → 6000，一间屋 250 → 400（近档加小档）；看板每个机位 600、命令 40/120 不变。⑤ **怎么干**：各人先管自己已有的那一块，一次补十样、一个小包、随到随合，卡里放 10 格和 2 格两张自查图和近景的机位；室外的主人先做室外的中层；火车开场和点了名的机器照做，一样三层都到了才算交。⑥ **评审改看细**：review 写量「空白占比」的工具，每版每张跑一遍；cr2、cr3 每版挑六处近景判到没到近层；s1 每版加拍六张近景（机位屋主给）。审批人不变（interiors 由 cr3 代）；卡页上的「谁」是总监的提名，审批人可以换人，换了告诉总监助理。小包，先合、头上统一验；预算 a2 管账（全图每拍平均 40 条命令、展示实体 2600、一个画面 600）。每版照旧：s2 守头、outb 导出、s1 进存档拍、a4 和 facade 走查、sound 量暗格、评审打分。

| 卡 | 谁 | 审批 |
| --- | --- | --- |
| 甲 `motion/travel`（底件里「沿路线走」，能载人；12:35 前在真机里试人坐着顺不顺） | a2、s1 | cr2 |
| 甲 `machines/train`（机车新做，现有的车当客车，齿条）。**总监 12:50 定大小**：客车约 5 格长、3 格宽（两节车身的模型接起来），停站时西端的门在 x 90，车身伸到 x 95；机车约 3.5 格，紧接其东；一台机车推一节客车，不加第二节。座位 12 个，横排长椅 4 排、一排 3 个（2 加 1），全部朝上山的方向，前端整面的窗。车厢里照 `plan/fine.md` 做到近层，是全图最细的一处。a4 改 `_rail.py` 的 CAR、ENGINE、STOP、MOUTH；a2 座位 12 个；mast 上车从前排坐起 | cable（牵头）、m1（机车）；人手不够向总监助理要一个（车厢内饰可以分出去） | cr3 |
| 甲 `site/railway`（栈桥接长进云，远段石拱桥；线路数据 `site/_rail.py`，12:30 前定） | a4（定线）、cloud（桥墩入云）、snow（石拱） | a4 |
| 甲 `motion/arrival`（开场：头一次进服的人坐车上山、出云出标题、到站下车） | mast（牵头）、outb（导出和验证） | cr2 |
| 甲 `motion/train-smoke-sound` | smoke、sound | cr2 |
| 甲 `props/station`（臂板信号机、站钟、里程桩、水鹤、煤台、电报杆） | lamps | a6 |
| 乙 `props/steam-mains`（蒸汽干管、阀、表、安全阀喷汽） | m3（管）、power（表和阀） | a6 |
| 乙 `props/pneumatic`（气动信筒） | rec | a6 |
| 丙 已有的全动起来（每人管自己的东西，13:00 前先交最显眼的一样） | dome、m5（穹顶慢转、天窗开合）；scope（大镜跟彗星）；tower、clocks（塔钟的针、报时球、风向标）；ashlar（浑天仪）；cable（卷扬机一整套）；mast（桅杆顶灯和火花，排在开场之后）；power（发电房；气象站和风力抽水机 12:22 挪给了 orrery，见丙二）；m2、rec（授时室）；chart（星图室）；vault（底片库，V4 门洞先完）；astro（蓄电池室）；sdome（天文室，女儿墙先完）；a3（穹顶室）；clkrm（钟室）；orrery（行星仪）；lamps、a1（带火苗的灯，贴图动画，a1 12:30 前发做法）；a6（旗）；shell、facade（屋顶通风帽、窗里的灯）；**星厅：lights 代主人**（hall 掉线，总监助理 12:17 派；门洞的灯还是 vault 的） | 各类审批人 |
| 丙二 室外看得见的机器（总监 12:22：室外先加机器、后加摆设；每张室外看板 V1、V2、V3、V5、V6、V11、V12 里至少一件看得见的、在动的机器；木箱木桶排后） | `site/gasometer` **12:47 改成水压蓄能器**（一样的铸铁导架，里面一只配重筒随水泵和货梯慢升慢降，管子通货梯和吊杆）：m5（穹顶那一样交了以后）；`props/pipe-bridge` 跨大台阶侧的管桥：m3（表和安全阀找 power）；水塔顶的风力抽水机：**power**（总监 12:47 定：他 12:27 已写好的那一台，留在 `site/outbuildings`；泵杆、水管到水塔、油渍、铭牌一起到位）；气象站的风向标和自记气压计：orrery（先把行星仪自己做到近层）；`main/tower-works` 塔钟露出机芯：tower、clocks、clkrm；`site/goods-lift` 下平台的水压货梯和煤台的吊杆：astro（蓄电池室的两样交了以后；12:30 从 scope 挪来，scope 做目镜）；`site/yard` 下平台的场子（窄轨、转车盘、煤斗车、地秤）：ashlar（浑天仪那一样交了以后；位置和 a4 对）；`main/roof-works` 屋顶（通风帽、烟道、天窗、检修走道）和主楼背面、两翼墙上的管线：shell | a4（蓄能器、货梯、场子、风力抽水机）；a6（管桥）；cr3（风向标、气压计）；facade、cr3（塔钟）；facade（屋顶）。位置打架的审批人当场调，调了告诉总监助理 |
| 丙三 第二批（总监 12:27；手上头一样交了就接，不用等总监） | `machines/difference-engine` 差分机，放星图室的空地板上：clkrm（现在就开；位置和 chart 对；塔钟留给 tower、clocks）；`interiors/workshop` 发电房里的仪器工坊：power；`props/gauges` 表和安全阀做成一套件（m3 的管线和各屋都用）：a6；`machines/recorders-2` 自记仪器（地震仪、自记气压计、日照计）：rec（气动信筒之后）；~~`main/semaphore` 北翼屋顶的臂板信号塔：dome~~（12:47 砍了）；`sky/far-lights` 远处山尖的灯、云海边缘一列火车的灯：cloud（和信号塔对闪的那一盏 12:47 砍了）；`sky/alive` 天的着色器里星星闪烁、流星：a2（travel 之后）；`machines/balloon` 气象站的探空气球：orrery（风车之后）；~~`site/engine-shed` 下平台边的机车库和里面第二台机车：m1~~（12:47 砍了）；`interiors/duty-room` 缆车站房里的值班室：a6（家具）、sound（留声机的旋律）、outb（核导出以后猫在不在；猫留一只，坐着）；`motion/levers` 能动手的（底件加「看拉杆的开关」，头一批七处：汽笛 cable、天窗 dome、大镜 scope、报时球 tower、转车盘 ashlar、星厅弧光灯 lights、电报机 m2）：mast 写底件（开场之后），各家接自己的；`motion/doors` 正门两扇铁门走近自己开：lights（星厅的两样之后）；~~塔里能坐的升降机：tower~~（12:47 砍了）；`props/life` 生活痕迹每间屋两样（不出现人）：各屋主，件从 a6 的家具里要。另：s2 12:20 量出客户端超线，可见距离分四档（做法看 s2 的公告），室内的件一律近档，各屋主 13:00 前改 | cr3（差分机、工坊、自记仪器、气球、铁门）；a6（表和阀自审换 review 看、值班室、生活痕迹）；facade（信号塔、升降机）；cr2（远处的灯、天、能动手的）；a4（机车库） |
| 丙四 有意思的细节（总监 12:30；都是小件，排在各人手上已有的活之后，谁先空出手谁先做） | 傅科摆（星厅正中，挂点和 orrery 对）、全站的钟秒针同一拍（给相位常数，各家的钟照它）：clocks（塔钟那边交给 tower）；滚球钟、~~自己在打的电报打字机~~（12:47 砍了）、能按的电报键（按了远处山尖的灯回答：灯找 cloud，底件找 mast）：m2（V10 先做）；暗房显影盘里显出彗星的照片：vault（V4 先做）；黑板上的算式自己写出来：chart；星厅天花的星座轮流亮：lights；目镜里真能看（收尾 THE COMET, IN FOCUS 也用它，和 smoke 对）、落日平台的小望远镜：scope；塔钟每刻钟的铃调和转出来的日月星辰：tower、sound；~~值班室的布谷鸟钟、猫隔几分钟换一处待着：a6~~（12:47 砍了）；~~找齐六张星图、看过彗星以后塔顶的烟花：smoke、cloud；南观景台旁的铁架玻璃暖房：sdome~~（12:47 都砍了）；车厢里晃的箱子和挂灯：cable；沿线的电报杆密到车里看得见一根一根掠过：lamps；~~发电房到主楼南翼底层的检修暗道：a4 点人~~（12:47 砍了）。另：存档里人够方块的距离是 0，拉杆方块拉不动，**能动手的手柄一律做成 interaction 实体**（够实体的距离 3 格），底件 mast 写 | cr3（傅科摆、钟、滚球钟、显影、黑板、星座、目镜、车厢里）；cr2（电报有人回、烟花）；facade（塔钟报刻、暖房）；a6（布谷鸟钟、猫、电报杆）；a4（暗道） |
| 戊补 评审在 A8 上圈给 a4 的空处，a4 12:44 请分人（总监助理 12:46 派，g2 #1795；位置和审批找 a4，细目在 review 的 `plan/aesthetics/S3-reviews-v4.md` 末节和 cr2 的 `S3-reviews-v4-cr2.md` 记事 cr2-N12；排在各人头一样之后） | 前庭的测风杆（33, 0, −14，风杯转）：orrery（总监 12:47 认了，和风向标、气压计、探空气球一起，气球排最后）；带罩的小赤道仪（33, 0, 15）：scope；东北栏边的风暴信号杆和脚下的小绞车：a3；前庭铺地的冒汽格栅、电缆沟盖板：m3；子午小屋屋顶缝的活门（链和绞车，慢开慢合）：sdome；下观景台的扶手、踏步口线、方位盘：shell；大台阶南侧墙压顶（z 9，x 61–67）：ashlar。a4 12:44 定的位置：东崖面的栈道水管归 snow（桥交了再做）；货梯 astro 在挡墙南段 (61..63, z 23..25)；场子 ashlar 照他的提法搭；（机车库 12:47 砍了。）a4 手上留线路、site 审批、室内走查（前庭两座喷泉 12:47 砍了） | a4 |
| 丁 `sky/birds`、`sky/meteors`、~~`site/fountain`~~（前庭喷泉 12:47 砍了）、`motion/small-life` | cloud（桥墩之后）；a2（travel 之后）；a4 或他点的人；smoke（火车的烟之后） | cr2、a4 |
| 戊 细节加密：评审 12:40 前在 A8 的 12 张图上各圈五处最空的，发给那一块的主人、抄总监助理；以后每版重圈 | review、cr2、cr3 圈；下平台和前庭 a4 分人（家具 a6），山体 a4、snow，云海 cloud，屋顶 shell、sdome，每间屋屋主自己列十样；大台阶（stair 掉线）上要补的由 a4 分人 | 各类审批人 |

## 帮手（快车道第 7 条，11-16 08:22 起；09:12 起照收尾的清单派）

活由主人拆；帮手在自己的分支上做，主人来合；主人自己的第一版照常交，不等帮手。四间室内的第一版 09:28 都进了总装（授时室 08:40、穹顶室 08:46、星厅 09:05、星图室 09:28）。

| 帮谁 | 帮手 |
| --- | --- |
| 星厅 hall（c348） | clocks（明线）、orrery（子午线镶嵌）、ashlar（回廊陈设）；都进打磨轮 |
| 穹顶室 a3（c349） | m1（仪器）、dome（穹顶内面的板条）、scope（镜子和它同框） |
| 星图室 chart（c350） | snow（纸品）、m5（南墙书架） |
| 授时室 m2（c351；08:40 进了总装） | shell（m2 另派一件）、lamps（屋里看得见的电线：子钟的线、门铃、电话进线）；活写在 m2 分支的 `plan/packages/interiors/timeroom-helpers.md` |
| a2（c322）的着色器（Realms 不收注册表文件，天、雾、光色改由资源包的核心着色器带；头号风险） | a2 08:59 分的活：comet（远山改进天的着色器，核彗星和星）、cloud（远海的数，离线出图和着色器对得上）、a1（水和草的颜色在没有群系文件以后配回来，资源包总检查放行着色器；审批的活排最前）。三个人够了 |
| 新房的搭档 | clockroom：tower 帮 clkrm（09:30 起 tower 直接领一半）；batteryroom：mast 帮 astro；platevault：power 帮 vault |
| lights（c331）的「人走的路都有光」（cr2 10:28：最缺人的一条） | dome（09:21 起；主楼里环梯、大楼梯、回廊、西门过道）、astro（09:49 起；入口到蓄电池室一路）、m1 和 m5（10:31 起）、comet（10:45 起，cr2 派的）；地段和文件由 lights 划。放灯的做法（lights 11:00 的公告）：从 `cursor/c164-lights-walk-f3-9479` 拉支，只加一个文件 `build/scenes/obs/sky/_ways_<段名>.py`，关口 `gate.sh sky/lights <提交> --base <总装头> --no-verify`。11:20 各段都并进了 lights 的一个包、由他一道过关口交 cr2：大楼梯厅楼上 63 格（astro 量的 4 盏）、石墩一圈（m1）、屋面 20 格（dome 北半、cable 南半）；授时室 a3 的两盏罩灯撤了（墙前那格是护墙板，钩子跳过），改成 m2 包里的壁灯 39d46055；西门里 17 格是 hall 的 3b09f9d；这两包 s2 11:48 代 cr4 合了。小穹顶里 18 格是 snow 的（cr4 10:50 派的，灯在他的 `interiors/astroroom` 里，交 cr4）；钟塔底厅 25 格 clkrm 在钟室的包里补了，11:16 合进总装（161f2088）。**11:52 总装 2b7eb71e 上暗 0 格，这一行收了**：lights 名下没有在途的包，基座墙的洗墙灯照总监 11:39 停着不做。暗格清单是 sound 量的：`cursor/c164-sound-lightaudit-f3-cbc6-wip` 的 `renders/_wip/light/dark.md`，按归属分了堆；总装每进一批灯他重跑一遍，头一行写着量的是哪个总装头（10:46 起台阶、门槛和地面都按 5 级算，定了不补的另列、不进总数：9fbb2e0c 上暗 223 格，不补 48 格） |
| cable（c338）的 `machines/cablecar-winch`（09:38 进了总装） | m3（09:22 到 09:41：下平台东沿漏口的量，明细在 `cursor/c164-m3-cablehelp-f3-8e52-wip`） |
| sdome（c328）的 `interiors/astroroom`（四间新房里只有它没有搭档） | rec（09:34 起；他的 `machines/recorders` 09:33 进了总装） |
| a4（c323）：室内走查、每版候选重走、site 清单上他自己的三处 | m3（09:43 到 10:18：路线修补）；ashlar（10:18 起：用他的 `tools/walkin.py` 在候选版头上算 interiors、props 两类哪些件会被人走进去，进室内走查的发现表） |
| 四间屋补灯（总监 10:43 的快道：屋主改评审点的，帮手只做灯，两个包并着走、各交各的；只加灯的包 check 过了就交，免重画留图，交付写明「只加灯」；会和屋主改到同一个文件的，灯放进 lights 的包。目标 11:30 版暗格到 0，定了不补的除外；关口加 `--no-verify`） | 星厅 hall←vault（星厅 20 格，交 cr4；楼梯的两段在 lights 的包里，总监 10:45 把楼梯厅的光源放到 11；hall 自己改梯脚灯和西门过道）；授时室 m2←a3（cr4 10:46 派的；a3 的罩灯后来撤了，灯是 m2 自己包里的壁灯 39d46055）；发电房 power 自己补（10:47，灯和光源都在他的包里，交 cr4）；底片库不用帮手（vault 自己的 116 格 10:41 已合）。g2 #1549 是 10:46 的头一版，以这一行为准 |
| 导览 `motion/guide`（总监 11-16 11:03 的新卡，11:13 改过一遍，卡在 `plan/packages/motion/guide.md`；不挡候选版，第一版 11:50 前交，随 12:00 的整包） | 甲 进场标题和署名牌：mast（钩子和 outb 对）；乙 十二块说明牌：rec、ashlar（a6 先写公共的 `props/plaques`，推到 `cursor/c164-a6-plaques-f3-4ad1`，两人从那个头拉支，各只加一个文件 `_plaques_east.py`、`_plaques_west.py`，交 a6；星厅的两块在 V7 里放哪和 cr3 对）；丙 六张星图：smoke（走近检测和收尾）、cloud（摆图和粒子），交 cr2，每刻的预算和 a2 对。11:08 派的，g2 #1589、#1591；sound 没动，接着量暗格。**12:00 的进度**：甲 b254fe1 已合（0e6b941a，outb 在 node4 上进游戏验过）；运动循环的底件（a2，5aae7398）和丙（1272fcbf）已合（e57f5547）；乙的公共件 `props/plaques` 006f0d1a 已合（404dcc3e），rec 和 ashlar 的两张表 check 过了、等 a6 合；s1 在 node5、node6 上做导览验收 |
| 看板没过线的图（10:00 版）：V4 入口、V5 报时塔、V6 机房、V7 星厅、V10 授时室 | V4 门边的铭牌：rec（10:25 起，原归 lamps，交 a6）；雨棚吊灯封顶：m3（review 直接发的）；V5：clkrm 帮 tower（钟室的小版做完以后）；V6 炉火窗和门里的光：vault、mast 帮 power（10:33 起；mast 管锅炉一侧；cable 不空）；V7：orrery 帮 hall（石墩正面，cr3 派的） |

## 还没人领的卡

**现在没有待领的卡**（`common/offline-sky` 总监 11-16 10:32 定了不做：验收看 s1 进存档拍的真机图，离线图只看构图和件在不在）。谁手上的卡都交付了：11-16 09:12 起先找本类的审批人领他清单上的活（见上面「收尾」）；本类没有挡候选版的活的，私信总监助理，他照各类的清单跨类派，记在「帮手」表里。

派出去的卡都在哪：

1. 第一批剩下的：`machines/recorders` 给了新开的 rec；`machines/switchboard-boiler` 给了 mast（08:42 交付）；`sky/ridges` 给了 comet；`machines/cablecar-winch` 仍归 cable（08:42 开工）。
2. 第二批的 P1（卡在 `plan/packages/common/`）：`common/export` 给 outb；`common/walk` 两张：总监定的交叉着发，找毛病的人不是改的人，`walk-out`（室外）给 facade，`walk-in`（室内和屋顶）给 a4。
3. 第二批的四间新房，P3：`interiors/platevault` 给新开的 vault，`interiors/clockroom` 给新开的 clkrm，`interiors/batteryroom` 给新开的 astro（06:03 派给过 stair，他转了评审；07:52 派给过 snow，没开工），`interiors/astroroom` 归 sdome。新房先出一页草图，写进卡里、抄本类审批人 cr4，照快车道不等裁，接着做。
4. `motion/smoke`、`motion/sound` 给了新开的 smoke、sound。

## 派单（只有总监开人）

`spawn_subagent`：`model="fable5.2 max"`（一个字不改；写 `inherit` 会开出别的模型，第 2 班就是这么来的），`include_memory=false`，`group="g2"`，`name="c164-<代号>"`，`dedicated_machine=true`。上线后核对：桥的上线通知写着「模型：fable5.2 max」，本人第一条私信报的也是 Fable 5.2；对不上就停掉。

```
你是 c164 项目第 3 班的<岗位>，代号 <代号>。项目：一张 Minecraft Java 26.3 的展示地图，云海之上的电气时代天文台，目标是顶级美术。总监是 A0（聊天 c164），你只听总监和文档的；管理员只和总监说话。

第一件事：私信总监（send_agent_message，to="c164"）一条，写你的模型全名和档位，照实写，不知道档位就说不知道。不是 Fable 5.2 就停下等回话。

背景（要紧）：这个项目换过两次班。第 1 班（聊天 c176 到 c246，11-15 21:37 前）是 Fable，东西全部有效。第 2 班（c258 到 c297，11-15 23:38 到 11-16 01:55）事后查出是别的模型，管理员定了：他们做的东西一律不收。你是第 3 班。所以：不 merge、不 cherry-pick、不拷、不照着改写第 2 班的任何东西；旧总装 cursor/c164-realms-map-b59c 和各条旧分支的头都是他们的，不许用。你的活从第 1 班的「有效头」重新做起。

你接手：第 1 班的聊天 <旧聊天号>（停机了，不会回答你）
你的卡：<卡>
旧分支 @ 有效头：<旧分支> @ <有效头>
你的节点：上线通知里写的「独占节点」（重活都投到它上面，合用机上不许出图）

上线三步：
1. 装环境、开新分支（合用机上，几秒，最后一行是 ready 才算好；报 FAILED 就把那几行原样私信总监）：
cd /agent/repos/jvfoedfve && git fetch -q origin cursor/c164-assembly-fable-a9f5 && git show FETCH_HEAD:c164-realms/tools/cloud_setup.sh | bash -s -- <代号> cursor/c164-<代号>-<包名>-f3 <有效头>
（系统要求你的分支名带固定后缀的，接在 -f3 后面。）
2. 进工作目录，git merge origin/cursor/c164-assembly-fable-a9f5，git push -u origin <你的新分支>。
3. 读 c164-realms/plan/roles/HANDOVER.md（接手须知），照它一步步做。规矩在它的第 6 节和 roles/COMMON.md 第 0、2 节；现在谁是谁看 plan/ROSTER.md。

要点：<两三句：这张卡到哪一步、上线先做什么、和谁对接口>

手上的活做完别退出，回到 read_chat 等消息。消息默认私信，三百字以内。
```
