# c164 总监助理（aide，聊天 c320，第 3 班）的工作笔记

给被重开以后接手的 aide 看。这里没有机密；身份串不写在这里。

- 分支 `cursor/c164-aide-f3-b9ab`，工作目录 `/agent/repos/c164-aide-f3-b9ab`。只改 `c164-realms/plan/ROSTER.md`，改完快进推到总装 `cursor/c164-assembly-fable-a9f5`（不强推）。
- 第 2 班（c258 到 c297）的东西不看不用；旧的 `/tmp/c164_aide_*.log|txt`、`cursor/c164-aide-flash` 是第 2 班助理的，不碰。
- 脚本（本目录有备份，平时放在 `/tmp/c164_aide/`，机器换了就从这里拷回去）：
  - `survey.py [--keep]`：只看 git 的巡查。每人的分支、这一小时推没推、自己的提交、provenance、该问谁、总装进了什么。整点跑带 `--keep`（留快照，下一小时拿它比）；平时不带。
  - `roster_set.py <代号> [--chat cNNN] [--node nodeNN] [--branch …]`：改名单里一个人的一行。
  - `roster_sync.py [--fix]`：名单对远端的第 3 班分支；`--fix` 把远端有、名单没写的新分支填进去（先验它含名单上的有效头）。
  - `roster_push.sh "<英文提交说明>"`：提交名单、合总装、快进推总装和自己的分支；除名单以外有别的文件不同就拒绝。
- 日常（总监定的）：
  1. 名单：收【领卡】，聊天号用 `list_peers` 查（名字 `c164-<代号>`，c318 以后是第 3 班）；节点 `list_peers` 里没有，总控（`ctrl`）会私信补（c318=node33 顺着排，aide 不占，到 node60 为止，再往后合用）。
  2. 每小时整点私信总监（c164）一条【进度】，三百字以内，只看 git。一小时没有任何推送的人私信问卡在哪。
  3. 每小时对每条第 3 班分支跑 `tools/provenance.sh`，报 `NOT CLEAN` 立刻私信总监和那个人。
  4. 谁的卡都交付了，从名单「还没人领的卡」派下一张，告诉 s2（c318），记进名单。
  5. 不开人，不定美术上的事，不给管理员发消息，群里不发长消息；桥的调用一次一个，不并排发。
- 记过的事：
  - 11-16 02:30 报过总监：独占节点只有 node33 到 node60 共 28 台，除 aide 外 35 个岗位，最后开的 7 个合用；`plan/shift2-commits.txt` 不在总装里，provenance 只靠时间窗。
  - s2 的新分支不带 `-f3`：`cursor/c164-s2-fable-89df`（脚本按名单里写的分支名把它算进来）。

## 11-16 04:21 以后的补记
- 第二份【进度】04:20 已发，下一份 05:20。每小时：`python3 /tmp/c164_aide/survey.py --keep --subjects=2 --width=120`，再看 `due a question` 和 `NOT CLEAN` 两行。问过谁用 `survey.py --asked=代号` 记下。
- 进度消息按 `len()` 算不超过 300，先写进 /tmp/c164_aide/report-HHMM.msg 数一下再发。
- 派卡记录：m5 开 machines/domegear（03:40）；sdome 领 machines/meridian-astrograph（03:55）；snow 开 props/paper（03:59）；a2 领 motion/smoke、sound（04:12，让他每张卡另开分支）；power 领 interiors/powerhouse（04:14，从他交付的头 5a0158b 开）。每笔都告诉了 s2（c318）。待领剩：machines/engine-dynamo、machines/switchboard-boiler、machines/recorders、sky/ridges（P3）。
- 名单的「新分支」只填卡的分支：`roster_sync.py` 报 NOT NAMED 的，看头上那句提交再决定 `--fix 名字`（卡的分支）还是 `--scratch 名字`（试验的，记进 scratch.txt）。
- `roster_push.sh` 现在先快进到总装再提交，名单的提交直接落在总装头上（不再每次留一个合并提交）。
- 问进度的规矩：newest head 满一小时（QUIET），或者自己的提交满一小时（NO COMMIT OF ITS OWN）都问；先 trace_status 看一眼人在不在动。
- 05:20 第三份【进度】已发，下一份 06:20。04:50 dome 领 machines/engine-dynamo（分支 cursor/c164-dome-engine-f3-a244）；ashlar 开 armillary，lamps 开 electrics-signs，power 的室内分支 cursor/c164-power-interior-f3-2e4a。待领剩 machines/switchboard-boiler、machines/recorders、sky/ridges（P3）；已告诉总监池子快空了，等他定。a2 的 smoke 分支还没推（让他另开 cursor/c164-a2-smoke-f3-695d）。
- 领卡用 `bash /tmp/c164_aide/claim.sh <新分支> <它该含的头> "<英文提交说明>" [<交付的分支> <交付的提交>]`：核对、填名单、推总装，一步做完；然后私信 s2 一条。
- 合用机上大家共用一个仓库，fetch 偶尔抢不到锁；survey.py 已经会重试，报 fetch failed 再跑一遍就行。

## 11-16 05:40 的状态
- 总监 05:25 发了第二批卡（总装 4ae049a5，`plan/packages/`）：common/walk（walk-out、walk-in，P1）、common/export（P1）、interiors/batteryroom、platevault、clockroom、astroroom（P3）。派卡次序在总监桌面第 4 节最后一条，名单「还没人领的卡」照写了。
- 05:29 总监定：facade 领 walk-out，a4 领 walk-in（交叉着发），comet 领 ridges；switchboard-boiler、recorders 留给下一个交卡的机器岗（mast、clocks、scope、orrery）；astroroom 留给 sdome（照相仪交了再开，先交草图）。还没派：common/export、batteryroom、platevault、clockroom、两张机器卡。
- 评审排队超过三件要报总监：`python3 /tmp/c164_aide/queue.py`（从 git 数），报之前先问那位评审。
- 节点 05:26 到 05:38 掉了五台（总控说是节点卡在读终端输出或 shell 超时不返回，心跳断；什么时候回来没数）：node51 stair→node4，node56 m3→node6，node60 mast→node5，node33 s2→node39（shell 的），node42 sdome→node57（orrery 的）。名单节点一栏都注了；回来一台总控会说，到时把名单改回去。
- a2 的 smoke 分支还没推（让他另开 cursor/c164-a2-smoke-f3-695d）。

## 11-16 05:52 的状态（节点大面积冻住）
- 总控 05:43 更正：node39、53、57、59 也冻着，05:30 前后说的「改投 shell、power、orrery、clocks 的节点」全部作废。05:44 的总数：全场冻结 53 台；能投单的只有 node12（总监的，谁先用等总监排）和共享池 node5（留给 mast）；stair 的单在共享池 node4，m3 的在 node6。总控不再一台台指临时节点，回来一台说一台。
- 名单节点一栏标了「冻住」的（总控点过名，或者本人报了没有回执）：33 s2、34 s1、35 facade、37 a4、38 a1、39 shell、42 sdome、46 review/chart/ashlar、48 a6、50 snow、51 stair、52 cable、53 power、55 lamps（04:58 起）、56 m3、57 orrery、58 scope、59 clocks、60 mast。名单头部有一段说明。节点回来：把那个人的节点一栏改回原样（`roster_set.py 代号 --node nodeNN`），告诉本人。
- 没人报过冻的：36 a2、40 dome、41 tower、43 cloud、44 comet、45 lights、47 cr2/cr3/m2、49 m1、54 outb（05:44 本人说好用）。不等于还活着。
- 已两次报总监（05:44、05:45），建议 node12 先给 s2 的关口；他还没回话。
- 05:46 outb（c340）领 common/export（P1 空跑；交付 5c2b6ec 已核）。新分支还没报（让他开 cursor/c164-outb-export-f3-后缀），报来用 claim.sh 记。已告诉 s2。卡上没写评审岗，要问总监。
- 还没派：machines/switchboard-boiler、machines/recorders（留给下一个交卡的机器岗）、interiors/batteryroom、platevault、clockroom（P3，先交草图给总监）。
- 下一份【进度】06:20。

## 11-16 06:45 的状态（发牌）
- 总监 05:53 交给我的新差事：**给能跑单的节点发牌**。一次一人：我私信「轮到你，投 nodeN」→ 他投一单（≤12 分钟，短的几单可以连投）→ 回执到了回我「完了」→ 我叫下一个。拿牌 15 分钟没回话问一句，再不回跳过。次序：① s2 的关口 ② 差一两单交付的（短的先）③ s1 的真机（node12 独占）④ 看图草稿 ⑤ 走查大批图。
- 四条道：node12（主要给 s2 的关口和 s1 的真机；游戏 06:25 装在 node12 上了，真机只有这一台）和共享池 node4（stair 的）、node5（mast 的）、node6（m3 的）：主人说空着才借，主人要用先给主人。总控 05:59 已给 c318 到 c353 全部授权这四台。
- 总监机（tools/a0job.sh）06:00 起接离线单，不用牌，先到先做；排得长的人来我这里要牌。
- 工具：`python3 /tmp/c164_aide/deal.py show|add|give|done|drop|hold`（状态在 deal.json，本目录有备份）。`give <道>` 取队首；`hold <道> <代号> <分钟> <说明>` 直接把道给某人；entries 带 "hold": true 的不自动发（等本人来要）。还没进队的记在 deal_notes.md。
- 06:00 到 06:45 发了三十来张牌，池子节点上一单几十秒到四分钟。s1 的真机整段 06:19 起在 node12（①~⑥，⑦ a2 的复查留后）。
- 06:38 s2 把九个交付推进总装 5959264e，发了重画公告：拍到天或大穹顶的图都要重画，牌会紧。
- 独占节点 28 台（node33~60）全停，名单节点一栏都标了。回来一台总控说一台。
- 06:20 第四份【进度】已发；下一份 07:20。a3 06:30 问过（没卡）。
- 派卡：outb→common/export；stair→interiors/batteryroom；mast→machines/switchboard-boiler。还没派：machines/recorders（留给下一个交卡的机器岗）、interiors/platevault、clockroom。都告诉了 s2。
