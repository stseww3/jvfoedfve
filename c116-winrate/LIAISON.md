# c116 ⇄ 10 子 Agent 胜率根因分析与核心变量联络总纲（`c116-winrate/LIAISON.md`）

> **总控（Coordinator）**：聊天 `c116「胜率分析总控」`
> **核心目标**：用严格的逐局量化解剖与跨版本对照，查明 **为什么实盘胜率一直无法稳定达到 80%**（从阶段性 80% 跌至昨晚全自动 9 局 `1/9 = 11.1%`），并锁定决定胜负的 **核心变量（Core Variables）** 及其精确数学阈值。
> **协同规模**：`c116`（总控） + `S01 ~ S10`（10 个判断单局问题与专项变量的子 Agent，兼容旧编号 `A01 ~ A10`）。

---

## 一、双仓同步与零冲突文档联络协议（必读）

为了确保所有子 Agent 无论挂载在哪个仓库都能无缝通信，本联络体系在两个仓库同名分支同步维护：

- **主仓库（Team 小队源码 / 选点协调器 / 实盘日志）**：
  - 仓库：`stseww3/jvfoedfve`
  - 分支：`cursor/c116-winrate-liaison-b3bc`
  - 路径：`c116-winrate/`
- **镜像仓库（模拟器 / 历史录像 / A01-A10 分析工具链）**：
  - 仓库：`stseww3/fdvg`
  - 分支：`cursor/c116-winrate-liaison-b3bc`
  - 路径：`c116-winrate/`（同时在 `territorial-sim/results/c58-review/C116-LIAISON.md` 留有索引）

### 1.1 目录结构与读写权限（严格零冲突）

| 路径 | 写入方 | 读取方 | 用途 |
| :--- | :---: | :---: | :--- |
| `c116-winrate/LIAISON.md` | **仅 `c116`** | `S01~S10` | 本联络总纲、全局核心变量矩阵、阶段性汇总结论 |
| `c116-winrate/DISPATCH.md` | **仅 `c116`** | `S01~S10` | 每局实盘派单表、10 个子 Agent 的包干对局与专项任务 |
| `c116-winrate/SCHEMA.json` | **仅 `c116`** | `S01~S10` | 子 Agent 提交结构化数据 `s0X-data.json` 的标准 JSON Schema |
| `c116-winrate/data/` | `c116` | `S01~S10` | 同步的实盘结算表 `tsb-team-results.jsonl`、日志切片、版本 diff |
| `c116-winrate/msgs/s0X.md` | **仅 `c116`** | 对应 `S0X` | `c116` 给单个子 Agent `S0X`（`s01`~`s10`）下发的点对点指令与追问 |
| `c116-winrate/reports/s0X-report.md` | **仅 `S0X`** | `c116` & 全员 | 子 Agent `S0X` 的单局显微镜解剖报告 + 核心变量因果论证 |
| `c116-winrate/reports/s0X-data.json` | **仅 `S0X`** | `c116` | 子 Agent `S0X` 的标准化量化指标（供 `c116` 自动聚合计算相关系数与胜率弹性） |

### 1.2 子 Agent 工作流（三步闭环）

1. **拉取派单**：
   ```bash
   git fetch origin cursor/c116-winrate-liaison-b3bc
   git checkout cursor/c116-winrate-liaison-b3bc
   git pull --rebase origin cursor/c116-winrate-liaison-b3bc
   ```
   读取 `c116-winrate/LIAISON.md`、`c116-winrate/DISPATCH.md` 以及你自己的信箱 `c116-winrate/msgs/s0X.md`（若你是第 `k` 个子 Agent，对应 `s01`~`s10`）。
2. **执行单局解剖与变量归因**：
   - 对照你包干的对局与代码版本，逐拍/逐阶段提取量化证据（严禁主观臆测，必须给出具体 `tick`、坐标、兵力 `B`、领土 `L`、密度 `d = B/L`、税费损耗、源码行号）。
   - **铁律**：所有本地终端命令一律加 `timeout 120`，严禁在 VM 本地跑无头浏览器或重型全量模拟防 OOM。
3. **写回报告并推送 GitHub**：
   - 只修改你专属的两个文件：`c116-winrate/reports/s0X-report.md` 和 `c116-winrate/reports/s0X-data.json`。
   - 提交并推送（也可同时推到你自己的独立分支 `cursor/c116-s0X-<suffix>` 作为双保险）：
     ```bash
     git add c116-winrate/reports/s0X-report.md c116-winrate/reports/s0X-data.json
     git commit -m "s0X: game dissection and core variable quantification"
     git pull --rebase origin cursor/c116-winrate-liaison-b3bc
     git push origin HEAD:cursor/c116-winrate-liaison-b3bc
     ```

---

## 二、待检验的 12 个核心候选变量（Core Variable Hypotheses `V1 ~ V12`）

为什么同样是 8~10 个号组队，有时能打出 80% 胜率，而昨晚自动挂机 9 局却只有 `1/9 = 11.1%`（其中多局中盘团队领土排第 1 却在 `t=4500~5800` 被翻盘）？
我们建立以下 **4 大维度、12 个可量化核心变量**，由 `S01 ~ S10` 逐局实测打分：

### A. 空间与开局维度（`t = 0 ~ 1800`）
- **`V1` 主大陆出生率与虚拟锚点位置（`MainContinentSpawnRatio`）**：
  - 定义：我方 8 个 Bot 落在最大主大陆（面积 $\ge 45\%$ 最大连通陆地）的人数比例，以及锚点是否选在地图边缘窄角/小岛。
  - 待验假设：无 Boss 自动局中，旧版 `findVirtualSquadAnchor`（`d590acd` 之前）把锚点选在边缘死角甚至 500 格小岛，导致开局天然丢失 $>70\%$ 主大陆发育空间。
- **`V2` 兄弟间距与内部挤压度（`AllySepAndInternalCrowd`）**：
  - 定义：我方 8 个 Bot 两两测地线距离中位数 `medianAllyDist` 与开局各自 Voronoi 空腔面积 `voronoiPixels`。
  - 待验假设：`fd868f3` 把 `allyMinSep` 从 `176px` 压到 `68~112px`、`clusterMax <= 350px` 后，8 个兄弟挤在半径 350px 内互相抢完空地即被自家队友包死，外围只剩 2~3 个前线点，全队总接壤面与总空地获取量暴跌。
- **`V3` 开局无主地收割率与 `t=1500` 团队领土份额（`TeamLandShareAt1500`）**：
  - 定义：`t = 1500`（无主空地结束时刻）我方团队总领土占全图陆地比例 `L_team(1500) / L_map`。
  - 待验假设：吃鸡局是否满足 `L_team(1500) / L_map >= 22%`？低于多少阈值时胜率断崖式下跌？

### B. 经济、税费与利息雪球维度（`t = 1500 ~ 4500`）
- **`V4` 决策周期与指令税费损耗率（`CommandTaxBurnRate`）**：
  - 定义：`e20db6b` 将 `P.period` 从 `5` 拍（`280ms`）改为 `2` 拍（`112ms`）、`inflight` 锁从 `8` 拍降为 `2` 拍后，单局总指令数 `totalCmds` 及累计攻击税/船税占总产出兵力的比例。
  - 待验假设：每次发兵扣除 `1.17% B` 陆攻税（船扣除 `3.125% B` 船税），高频微脉冲是否在不知不觉中烧掉了 20%~35% 的复利雪球？
- **`V5` 跨海占岛与海防撞船净收益（`BoatTaxVsNetLandROI`）**：
  - 定义：`tryClaimNearTeamIslands` + `tryInterceptEnemyBoats` + `idleBoats` 全局发船次数、扣税总额 `sum(3.125% * B)` 与实际阻止的敌方登陆兵力 / 占岛收益比。
  - 待验假设：对 `<=1800` 格小岛发船或中盘高余额兄弟发船，是否因 `3.125% * B` 船税过高而亏本？
- **`V6` 团队捐款抽血阈值与后排输血效率（`DonationDrainVsFrontlineDensity`）**：
  - 定义：捐款发生时捐出方密度 `d_donor`、受捐方密度 `d_receiver`、10% 捐款系统税损耗，以及后排内陆队友（`nb === 0`）的闲置满仓时间占比。
  - 待验假设：过早捐款（`d_donor < 98`）抽干前线；反之，完全被自家队友包在内陆的后排（`nb === 0`）若不及时把兵传给前线，又会坐满 `150*L` 浪费利息。最优后排/前线传递公式是什么？

### C. 前线攻防、密度底线与反蚕食维度（`t = 2500 ~ 6000`）
- **`V7` 交战期防御保留密度底线（`EffectiveFrontlineKeepDensity`）**：
  - 定义：`e20db6b / 32c5689 / 514a041` 组合修改（`oppFloorCap: 128 -> 38`、`collapseFloorCap: 85 -> 16`、`totB = B + myOut`、优质地 `keep <= 10*L~26*L` + 单目标追击上限 `16% B`）后，前线兄弟出刀后的实际留守密度 `d_after = B_home / L`。
  - 待验假设：**头号翻盘嫌犯**——把在途兵力 `myOut` 算进可用预算且将 `oppFloorCap` 降到 `38` 后，前线兄弟在连续出刀抢地时家里真实留守密度 `B_home / L` 跌破 `35~45`，被旁边满密度（`d = 100~130`）的敌方主力看准虚弱窗口一波 `20% B` 直接推平！
- **`V8` 优质地/崩盘地抢夺转化率（`PrimeLandConversionEfficiency`）**：
  - 定义：场上出现崩盘玩家（`nearCollapse`）或投降 `[Bot]` 时，我方抢到的地块占比 vs 为抢地付出的密度透支代价。
  - 待验假设：抢优质地时若不看周围第三方强敌（`max3rdB` / `otherEnemyD`）无脑压低 `keep` 到 `10*L`，是否“吃下 1 万格肉、丢掉 5 万格命”？
- **`V9` 反蚕食威慑与避免主动戳巨无霸（`AntiNibbleVsPokeGiant`）**：
  - 定义：被敌方试探时是否及时等比例威慑反击，以及是否误触 `isFreshBeachhead` / 低门槛脉冲主动戳了 `B_enemy > 1.3 * B_me` 的满密度强敌。

### D. 团队集火协同与对局环境维度
- **`V10` 8 兄弟集火协同度（`TeamFocusFireConcentration`）**：
  - 定义：同一时间窗口（`100 ticks`）内，我方前线兄弟攻击的目标是否集中在同一个敌方队伍/同一个残血玩家，还是各自打各自的邻居（同时惹毛 3~4 个敌方大队）。
  - 待验假设：没有团队级集火目标锁定时，8 个兄弟四面出击同时树敌，导致我方在 `t=4500` 被全图多队联合围剿。
- **`V11` 中盘领先局（峰值第 1）收口失败机制（`MidgameLeadThrowMechanism`）**：
  - 定义：专门针对 `00:30`（Team 4 领先被翻）、`00:50`（Team 1 领先到 `t=5422` 被翻）、`01:01`（存活到终局领土惜败）等对局，定位从“团队份额第 1”到“开始净丢地”的精确拐点 `t_inflection` 及其触发事件。
- **`V12` 房间队伍数、有效在场人数与掉线/CF 稳定性（`LobbyTeamCountAndActiveBots`）**：
  - 定义：当局是 `2 队局` 还是 `5~6 队局`、我方实际进场存活的 `[Nope]` 人数（是否满 8 人、有无中途 `1006` 闪断或未核验名字）。

---

## 三、10 个子 Agent（`S01 ~ S10`）职责分配总表

详见 `c116-winrate/DISPATCH.md`。每个子 Agent 同时负责 **「指定实盘对局的逐拍解剖」** + **「1~2 个核心变量的全样本量化验证」**：

| 子 Agent | 兼容旧名 | 包干实盘对局（第一批） | 负责深挖的核心变量 | 交付文件 |
| :---: | :---: | :--- | :--- | :--- |
| **S01** | `A01` | **第 1 局 (`00:30`, 6队局, 峰值第1被Team 6翻盘)** | `V1` 主大陆出生率 & `V2` 团簇间距 `allyMinSep` 内卷度 | `reports/s01-report.md`<br>`reports/s01-data.json` |
| **S02** | `A02` | **第 2 局 (`00:35`, 6队局, 败) & 第 3 局 (`00:41`, 4队局, 败)** | `V3` 开局扩张效率与 `t=1500` 团队领土份额生死了线 | `reports/s02-report.md`<br>`reports/s02-data.json` |
| **S03** | `A03` | **第 4 局 (`00:50`, 3队局, 领先到 `t=5422` 被Team 2翻盘)** | `V7` 前线防御底线 `oppFloorCap=38` + `totB=B+myOut` 抽虚崩盘机制 | `reports/s03-report.md`<br>`reports/s03-data.json` |
| **S04** | `A04` | **第 5 局 (`00:54`, 6队局, 败)** | `V6` 团队捐款抽血阈值与内陆后排（`nb=0`）输血效率 | `reports/s04-report.md`<br>`reports/s04-data.json` |
| **S05** | `A05` | **第 6 局 (`01:01`, 5队局, 3人活到终局 `ethan21` 5.9万地仍惜败)** | `V5` 海防撞船与近岸小岛发船的 `3.125%B` 船税 ROI 审计 | `reports/s05-report.md`<br>`reports/s05-data.json` |
| **S06** | `A06` | **第 7 局 (`01:07`, 2队局, 唯一吃鸡局 54.5万地) 正向对照解剖** | `V4` 决策周期 (`period=2 vs 5`) & `V8` 优质地收割与守成平衡 | `reports/s06-report.md`<br>`reports/s06-data.json` |
| **S07** | `A07` | **第 8 局 (`01:13`, 6队局, 终局第4败)** | `V9` 反蚕食威慑、防戳强敌与多面受敌防守锁 | `reports/s07-report.md`<br>`reports/s07-data.json` |
| **S08** | `A08` | **第 9 局 (`01:28`, 5队局, `t=14666` 超长局第3败)** | `V10` 8 兄弟团队集火协同度（Focus Fire vs 分散树敌） | `reports/s08-report.md`<br>`reports/s08-data.json` |
| **S09** | `A09` | **历史 80% 胜率批次 vs 昨晚 11.1% 批次全量结算对比（`tsb-team-results.jsonl`）** | `V11` 中盘领先被翻盘拐点规律 & `V12` 队伍规模/在场人数影响 | `reports/s09-report.md`<br>`reports/s09-data.json` |
| **S10** | `A10` | **源码级逐行 Diff 审计（原版 80% 胜率 `v27team` vs 昨晚 `917e6b1`）** | 汇总 `V1~V12` 权重排序、参数级回退/修正清单与 A/B 门禁方案 | `reports/s10-report.md`<br>`reports/s10-data.json` |

---

## 四、子 Agent 报告必答的「五问模板」（`reports/s0X-report.md`）

每个子 Agent 的报告必须严格按以下 5 节撰写，拒绝空话套话，全部用数字说话：

1. **【单局时间线与胜负拐点（Timeline & Inflection Point）】**：
   - 列出你负责对局在 `t = 600 / 1500 / 2500 / 3500 / 峰值拍 / 崩盘拍 / 终局` 的我方存活人数、团队总领土 `L_team`、全图占比、平均密度 `d_team`、头号对手团队数据。
   - 精确定位 **「哪一拍（`t_turn`）、哪一个或哪几个 Bot、因为哪几条指令或哪次选点/漏防」** 导致局势从顺风/均势转为不可逆败势。
2. **【核心死因分类（Primary & Secondary Root Causes）】**：
   - 从 `V1 ~ V12` 中选出该局最致命的 **第一主因（权重 $\ge 50\%$）** 和 **第二诱因**，给出源码行号（`tsb/squad/v27-team-live.js`、`tsb/squad/make_v27_team.py` 或 `tsb/squad/spawn-coordinator.mjs`）与日志原句证据。
3. **【专项核心变量全样本量化（Core Variable Quantification）】**：
   - 对你负责的专项变量 `Vk`，给出在赢局 vs 输局中的数值分布对比，计算该变量变化对胜率/存活率/峰值转化率的影响，并推导 **最优数学阈值区间**。
4. **【反事实推演（Counterfactual Verdict）】**：
   - 如果把你负责的变量改回 80% 胜率基线值（或你推导的最优阈值），在你解剖的这局关键拐点 `t_turn` 会少死哪几个 Bot、多留多少万兵力/密度？
5. **【一行可验证改动建议（Minimal Actionable Fix）】**：
   - 给出精确到函数名、参数名、修改前后数值的最小改动建议，并标明是否与其它变量正交。
