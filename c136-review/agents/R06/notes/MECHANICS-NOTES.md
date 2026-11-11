# R06 机制与数据笔记（逐局复盘的共同依据）

> 每条都注明：依据（源码位置 / 脚本）和验证程度。只写「是什么」，不写改动方案。

## A. 数据层

### A1 名字不是稳定身份，`me` 才是
- 对局包的 `traj.csv / stories / timeline.csv` 按日志前缀名字分号；名字局内会被换（离开后改成下一局的名字，也有中途改名）。
- 稳定身份：`[HL-GAME-INIT] … me=N`、`results.csv` 的 `meId`、录像头的玩家序号。
- 我的解析库 `scripts/r06lib.py` 全部按 `me` 归并。例：B039 的 Bohemia(45) 在 t=7650 后日志名变成 ErenYeager。

### A2 `card.squadBots / teamSplitCounts` 只数了「有结算行且带队号」的号
- B039 卡片写 `{2:3, 3:4}`，实际 20 个号的分队是 队1=2、队2=7、队3=11（见 B）。

### A3 录像 `replay.txt` 只记录「通过了引擎全部校验、真正执行了」的指令
- 依据：`live_game_js.js` 指令处理器 `bB.qi`：陆攻 `i6`、捐款 `qv`、发船 `iB` 都是先过全部 `if(!…){return}`，最后才 `bC.rg.rh(id, player, …)` 写录像。
- 所以：日志里有 `[HL-DONATE]`、录像里没有对应指令 = 这笔捐款没有执行（没扣手续费、也没到账）。这是捐款是否到账的真值，比 `likelyRejected` 启发式可靠。
- 指令号：0 选点、1 陆攻(pct, 目标；目标已死记成 512 无主地)、2 捐款(pct, 收款人)、3 发船、4 追船/召回(849)、5 撤回、6 表情、7 投票、8 主动认输离开、9 断线（`bT.rf`：在场且未离开 → 变成 AI 托管）、10 山地。
- 录像完整度（我的 15 局）：整局 = B010、B023、B021、B017、B022，以及借同局对手包的 B039（用 `A058`）、B038（用 `A057`，到 t=12009/12461）；只到开局 = B041(1155)、B025(1435)；只有选点 = B045、B018、B014；没有录像 = B002、B001、B003。
- 解码脚本：`scripts/replay_decode.mjs`（位流格式同 `src/sim/tools/c102-replay-lib.mjs`）。

### A4 日志拍号是「客户端本地拍」，执行拍是「服务器拍」，两者会差很多
- `[HL-OPENING] / [HL-DONATE]` 的 `t=` 是做决定时客户端的本地拍；录像里的拍是指令真正执行的拍。
- 正常差 7~20 拍（1~3 个服务器回合，每回合 7 拍）。但 B039 里 t≈600 起差值一路涨到几百拍（Algiers 在本地 t=900 的指令晚了约 600 拍才执行），t≈2250 后恢复。
- 两种等价的解释（都会造成同样的局内后果）：客户端落后于服务器（20 个浏览器页抢 CPU），或发出的指令被压住后成批放行。日志落盘顺序还显示各号之间互相也差 180~540 拍。
- 脚本：`digest.py <id> lag`。

## B. 引擎机制（本轮新核实的）

### B1 分队算法：按「玩家颜色 + 战队标签」，不是随机（`bj.ee → aej/aKa/aek/ael/aem`）
1. 每个真人的颜色到 8 个队色（红绿蓝黄紫青白黑）的曼哈顿距离 → 第一、第二志愿；第一志愿给该色 4 票，第二志愿 1 票。
2. 颜色按票数排序，前 N 个成队（N = 配置队数）。
3. 名字里有 `[标签]`（1~7 字符）的算战队：最大战队人数 > floor(真人数/队数) 时队数减 1；战队整体进「本战队票数最高且在场」的队（除非那队已严格大于其它所有队）。
4. 其余真人按玩家号顺序：先进第一志愿队（未满），再试第二志愿，最后剩下的硬塞进没满的队。每队上限 ceil(真人数/队数)。
5. 队数 < 8：内置 AI 不属于任何队（队号 0，人人可打，结算表里的 `"0"` 就是它们）；队数 = 8：AI 按 `1 + 玩家号 % 8` 分进各队。
- 验证：`scripts/team_assign.py` 用录像头重算，12 局共 156 个有结算队号的我方号 **156/156 一致**。
- 推论（事实陈述）：squad20 的号没有战队标签、颜色各异 → 必然被拆到多支队；带 `[APEX]` 标签的 squad10 整体进同一队。

### B2 断线/离开的号变成 AI 托管的「空壳」，仍在原队
- `cy.aGG`：`aH.nT(player)`（交给内置 AI 驱动）、`a6S[player]=2`；队号不变、领土和兵都还在。
- 空壳不受捐款额度限制（`aOb = 单机 || t>=4284 || kH(收款人)`，`kH = 是 AI 或已离开`）→ 给空壳捐款一定成功（只要它活着、有空间），兵等于送给 AI。
- 策略 c110 的 `tryDonateToTeammate` 只查 `g.alive[p]`、名字池、领土下限，不查对方是否已离开 → 会给空壳做「squad rescue donate」。B039 实例：404→HighPing(空壳) t=2177、Sus→Ashanti(空壳) t=2947/3283、Bohemia→Belgium(空壳) t=2387、Sus→Belgium(空壳) t=3178。

### B3 所有出兵/发船/捐款指令都是「执行那一拍余额的百分比」，同拍多条会连乘
- 陆攻 `n2(player,pct,12,0)`、发船 `n2(player,pct,32,0)`、捐款 `jB`：都按执行时的余额算 `floor(B*(pct+1)/1024)`。
- 「限发额度」`b5.a6i` 只在 `lC===10`（禁全压模式）生效；组队局不限 → 同一拍执行的多条指令逐条按剩余余额的百分比扣，没有总量上限。
- 策略按做决定时的本地余额把「想发的兵」换算成 pct。指令晚到并挤在同一拍时：7 条 12%~44% 的发船同拍执行 = 发掉 95% 的兵（B039 Sus t=1722：188,693 → 9,676）。
- 策略侧的防重发只有「同一目标 15 拍内不重发」且对无主地不设防（`Strategy.send` L526-533）；发船靠 `boatEvery=60` 和 `boatCount>=maxBoats`，但晚到的指令在本地还没生效，`boatCount` 仍是 0。

### B4 捐款
- 手续费 `floor(64B/1024)` = 余额的 6.25%，与 pct 无关；到账 `min(floor(B(pct+1)/1024), B-fee, 对方空间)`。到账/(到账+手续费) = (pct+1)/(pct+65)：pct=55 → 47%，103 → 62%，153 → 71%，185 → 74%，280 → 81%。
- 额度：全场共用上限（开局 15，每 100 拍 +4/+6/+8/+10），每个收款人累计点数不得超过；t<2142 时一笔 6 万多兵的捐款就要 82~90 点，而上限只有 91~121 → 基本「一人一生只能收一笔」。t>=4284 不再检查。
- 被拒的捐款不扣手续费（校验在扣费之前）。

### B5 c110 的关键调用顺序（`Policy.act` L4781-4944）
- 只在 `t%5==0` 决策。t<1500：`analyze → tryEmergencyBossRescue → super.act`（开局租金周期扩张 `dpNeutral`，每周期一条无主地指令）。
- t>=1500：`analyze → tryPeaceVote → tryEmergencyBossRescue → updateGrudges/updateWars → expandNeutral(有无主地时) → buyLand → （没发指令才）tryDonateToTeammate → （还没发指令才）idleBoats`。
- 即：c110 里捐款排在买地之后，不是在 `act` 开头抢占。

### B6 c110 选点 `chooseSpawn`（L4007-4154）
- 没有后台分配（日志里没有 `HL-SPAWN-BACKEND`）。每个号在自己的客户端上：把名字池里的号全部从局面里抹掉 → `spawnVsPeople(gClean,48)` 取 48 个候选 → 按 minSep(=145) 贪心筛出 `chosenSlots` → 取自己固定槽位 `slot` 对应的那个。
- 各号各算各的、时刻不同、看到的外人落点不同 → 候选表不一样 → 不同槽位可能落到同一点。B039：ArthurMorgan(槽10) 与 Thanos(槽11) 最终相距 16 像素，且分属队2/队3。

### B7 被围的号发船：`idleBoats → boatFood / boatOut`
- `boatOut`（L1035）：目标是玩家的地时，一船发 `boatFrac(0.5) × (余额 − 底线)`；目标是无主地时发 `3×块大小+300`。最小 12.5% 余额。
- 触发条件：`neutral==0` 且（没有邻居 或 余额 ≥ 1.25×100×领土）。即「四周全是队友/受保护号」的后排会把一半的兵装船。

### B8 欠账：余额为 0 的挨打号收到的捐款先还账（`src/sim/sim/game.js` `takeBalance` L766-777 / `addBalance` L752-764）
- 守方余额不够扣时，差额 ×1.25 记成欠账；之后任何进账（利息、捐款、退回的兵）先还欠账。
- 所以捐给「余额 0、正在挨打」的号：捐款人照付本金和 6.25% 手续费，对方到账 0。B038：Pele 5 笔 + Golden Horde 1 笔捐给空壳 Roman Empire，到账 0、连本带费丢 3.6 万。
- 验证：真引擎重放里这 6 笔的到账都是 0（`simdigest.py B038 don`）；欠账数组本身没有导出。

### B9 空壳的「整笔转交」（`src/sim/sim/bots.js` `botAttackTeam → botDonate → botGive`）
- 离开的真人由内置 AI 托管。它没有可陆攻的目标、发不了船、没有山地可用时，把**全部余额**交给一个队友（先挑「最近在打仗」的，其次挑有船在外的），条件是余额 >= 领土；手续费 64/1024；不占捐款额度；不是指令，录像里没有。
- 验证：B038 的 4 笔（Carinthia t=1409 +233,151、t=1507 +147,405；Siam t=1988 +154,228；Herobrine t=1334 +94,385）都等于对应空壳余额 ×960/1024（差 0~2 兵）。挑收款人的规则只读了干净模拟器源码，没在真引擎混淆源码里逐行对。
- 脚本：`simdigest.py <id> lumps`（进账：一拍内余额跳涨 >=2 万且 >4%、不是捐款指令也不是船；出账：我方空壳一拍内余额掉 >=80% 而领土不变）。

### B10 清地线跟着峰值走（`game.js` `aliveTick` L1298-1311、`collapse` L1313-1334、`eliminate` L1336-1349）
- 每拍：`peak = terr >= peak ? terr : peak − max(1, (peak − terr)//1000)`；`terr <= peak//4` → 清地。
- 清地时有船在外：只清领土（格子变无主地）、余额和欠账清零、号还活着（船靠岸还能再长）；没有船：直接出局。打它的人的攻击线被改挂到无主地（`redirectAttackToNeutral` L858-872）。
- 后果：短时间冲高会把清地线一起抬高。B038：Carinthia 4,229→10,945 格后被清时手里还有 2,616 格（冲高前的线是 1,057）。
- 验证：`simdigest.py B038 collapse` 用逐拍领土重算衰减峰值，18 次清地全部对上（清地前一拍领土都略高于 peak//4）。

### B11 目标被清地后，攻击线上的兵挂在无主地上不回来；c110 不撤兵
- 目标清地 → 剩余进攻兵留在一条「对无主地（512）」的线上，等这条线打完才回余额。B038 Herobrine：t=2276 起 23.3 万兵挂了 80 拍（只花掉 1,486），期间余额 1.7 万~5.9 万、领土 11,084→4,792。
- 引擎有撤兵指令（`retreat` L1288-1294 → `cancelAttack` L852-856 退兵）；c110 的参数 `holdOn=0`（`V13.act` L1853 不调 `hold`），而且 `hold` L2120-2129 只撤对真人的线。
- 验证：`eng_replay.cjs B038 --to 2360 --trace 44:2180:2356`。

### B12 船落在水格 / 边界格 / 山格（真引擎 `acN`）
- 落点格的值 `(px & 3) << 3` 被当成目标座位（水 16、边界 24、山 8）：开一条对该座位的攻击线（没有接壤就在下一次结算退回），目标是队友就按捐款入账，是自己就退回。
- 干净模拟器原来的 `landAt` 直接 return（兵消失），所以影子探针从第一次这种落点起与真引擎分叉（B038/A057 在 t=2485）。按 R01 的共享库 `src/tools/resim_lib_r01.mjs` 的写法补进 `strat_probe.mjs` 后：B038 全体真人全部采样拍、我方 20 个号每一拍与真引擎一致（t=0~12009）；B039 同样全程一致（t=0~8275）。

### B13 c110 `buyLand`（L5250-5533）的出口阶梯（影子探针 `--tally` 按这些行归类）
- L5258-5267 报价 `c >= worth` 且没超软上限（`over = 兵 > 100×领土`）→ 不打；**over 时这道比价整段跳过**。
- L5271 唯一真人缓冲不打；L5280 crowdedHard。
- L5322 `safe = safeAt`；L5352-5359 over 时 keep 封顶 `overKeepMult×100×领土`；L5358-5361 `avail = 余额 − 手续费 − keep`，`avail <= 0` → 跳过。
- L5363-5368 非真人目标：L5364 已有攻击线则跳过；L5367 `x < minCmd`（minCmd = feeK×手续费 ≈ 余额的 4.7%）→ 跳过。号越大，这道门槛越高。
- L5374 / L5511 的在途兵 `curAtk` 只看本机局面；L5510-5523 脉冲；L5526-5531 出兵 `min(avail, 1.25×need)`（L5528 太小不发）。
- 参数（`params-raw-c110.json`）：dpEnd=coreFrom=1500、period 5、minSend 0.2141、sendFrac 0.746、winR 0.002、oppFloorCap 88、feeK 4、pulseFrac 0.12、holdOn 0、quotaGuardMode 1、flashLoanMode 0。

### B14 t<1500 打内置 AI 的底线（`General.act` L804-845 → `Style.pickTarget` L1180-1213）
- L1196-1197 `avail = 余额 − floorFor`，`avail <= minSend×余额` → 跳过。`V13.floorFor0` L2270-2276 → `winFloor` L2521-2528 = `max(botPx×领土/(winR×t), dpKeep, this.sb)`。
- `this.sb = safeFinite` L2532-2542：对每个内置 AI 邻居，取它所有邻居里兵最多的那个号的兵——不排除队友和保护名单里的号。两个我方号共享同一批内置 AI 邻居时，互相把对方的兵当底线。
- 实测（`simdigest.py <id> gates` 第一段）：B038 2,199 个决策拍里 889 个（40.4%）只因为这一项不出兵（同队 102、异队 787）；B041 见该局复盘。

### B15 c110 `tryDonateToTeammate`（L4369-4499）
- L4372 冷却 18 拍、t>=400；L4374 `boxedIn = 没有邻居 && 没有无主地`；L4385 自己正被真人打或余额 <= 1.10×safeFloor → 不捐。
- L4387-4389 `maxSafePct = floor((余额 − 1.08×safeFloor)×1024/余额)`，`< 55` 才不捐 → 55~63 的捐款手续费不低于到账。
- rescue 循环 L4423-4460：被救的号 = 在场、名字在池里、领土 >= 300（L4424：场上还有「野生外人」时不要求与我同队）；它正被真人打（进攻兵 >= 它余额的 8% 或它密度 < 75）。同队且我密度 >= max(55, 它的密度+15) → L4436-4438 捐 `pct = min(maxSafePct, 纯内陆 ? 240 : 155)`。否则 L4448-4457：主攻手不是我的队友、与我接壤、我对它没有攻击线、有空槽、我密度 >= 65、距上次 >= 25 拍 → 对主攻手发一条 10% 的陆攻（`g.attack(102, …)`，被救的号可以是异队的）。
- surplus：L4462 非 boxedIn 需密度 >= 112；L4463 boxedIn 需密度 >= 55；L4466-4486 候选 = 在场、`isTeammate`、（Boss 或名字在池里）、领土 >= 600、密度 < 132；L4489 `pct = boxedIn ? (密度 > 110 ? 280 : 185) : 153`。
- 函数里没有：收款人余量（150×领土 − 余额）、额度、对方是否已离开、对方是否欠账。`isOurSquadBot` L3973-3976 只比名字。

### B16 「发了没生效」在策略里没有记账
- `Strategy.send` L526-539：同一目标 15 个**本机拍**内不重发；没有「上一条是否已被服务器执行」的状态。本机落后服务器、或指令被压住时，本机局面一直是「没发过」，于是每 15 拍重发一条同样百分比的指令；追上时多条落在同一个服务器拍，按 B3 连乘。
- 实测：B038 `simdigest.py B038 bursts 3 0.5` 29 组、518 万兵；影子探针在同一局面上每次只想发一条（31%~41%）。

## C. 真值流水线与脚本清单（`c136-review/agents/R06/scripts/`）
- **真引擎重放**：`run_truth.sh <id…>`（`sim_prep.py` → `eng_replay.cjs`，套 `run-heavy.sh`）→ `out/<id>/sim_state.json`（每 30 拍全体真人、我方号逐拍、指令、捐款、船、账本、邻居采样）。核对：每条日志快照在重放同一拍找 (领土, 兵) 完全相同的号——B039 475/475、B041 202/202（到 t=1155）、B038 890/890。带 `--to` / `--trace 号:起拍:止拍` 的运行写 `sim_state.partial.json`，不覆盖整局文件。
- **影子探针**：`strat_probe.mjs <id> --me squad|号,号 [--to T] [--dump 号:起拍:止拍:步长,…] [--json] [--tally]`（套 `run-heavy.sh`）：干净模拟器重放全局，同一份策略源码逐拍跑在每个我方号的真实局面上，指令只记不发；每次运行先打印「干净模拟器 vs 真引擎」的逐拍对比。`--tally` 记每个决策拍停在 `buyLand` / `pickTarget` 的哪一行。
- `simdigest.py <id> <段>`：check、teams、dens [t]、roster、medians、gaps、husks、poolai、protbox、boats、landings、gifts、fees、nfs、don、probe、deaths [me]、pair <me> [t0 t1]、cmds、cmdlist <me> [t0 t1]、neigh、front、shadow、gates、dups、crowd、bursts [最少条数] [余额占比]、collapse、lumps、ledger、json。
- `digest.py <id> roster|teams|timeline|picks|spawn|deaths|donations|drops|boxed|attacks|lag|teamwar|bot <me>|json`：只靠对局包（没有录像也能跑）。
- `logdigest.py <id> stale|silent|seqlag|wall|overcap|drop30|oplag|issued|json`：只靠日志的延迟 / 停摆 / 清仓检测。
- `make_review.py <id> [--facts]`：从对局包 + 重放重算事实骨架，合并 `reviews_src/<id>.py` 的人工分析，写 `reviews/<id>.json` 并自检。
- `replay_decode.mjs <id>`、`team_assign.py <id>`、`r06lib.py`（解析库 + 引擎公式）。
