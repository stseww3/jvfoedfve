# STRATEGY-MAP — v27 组队策略「局内决策树」代码地图（R05 / M1）

口径：只陈述源码与数据里能复核的事实，不含任何改动意见。行号默认指 `/agent/repos/c136-data/src/strategy/v27-team-c116.js`（Vc，5737 行）；
`v27-team-c116-vb.js`（Vb）行号与它完全相同，`v27-team-c116-va.js`（Va）在 4297 行之后少 1 行。其它文件写全名。
所有数字的出处脚本在 `agents/R05/scripts/`，产物在 `agents/R05/out/`（见 §11）。

## 0. 先读这个：哪一局跑的是哪一版代码

| 纪元 | 对局 | 调度句式指纹（`[HL-DISPATCH]`） | 对真人进攻的主流千分比 | 源码（`c136-data/src/strategy/`） | 日志套源码门槛的违例数 |
|---|---|---|---|---|---|
| E1 = Va | A001–A017 | 内陆号 进攻·收益 225、协防 260；前线 170/190；最小 128 | 204（=`pulseFrac` 0.20） | `v27-team-c116-va.js` + `spawn-coordinator-c116-va.mjs` | 1131 条里 0 |
| E2 = Vb | A018–A095 | 内陆号 320/380；前线 220/240；最小 180；内陆号最低密度 进攻 58 / 协防 30 | 122（=`pulseFrac` 0.12） | `v27-team-c116-vb.js` + `spawn-coordinator-c116-vb.mjs` | 16253 条里 0 |
| E3 = Vc | A097–A099 | 内陆号 220/260；前线 170/190；最小 150；冷却 24 拍 | 122 | `v27-team-c116.js` + `spawn-coordinator-c116.mjs` | 750 条里 0 |
| B | B001–B050 | `[HL-DONATE] surplus 280/185/153`、`squad rescue 240/155`、`[HL-ASSIST]` | 102（10% 轻戳）与 122 | `v27-team-c110.js` + `spawn-coordinator-c110.mjs` | — |
| G | G00–G09 | `[HL-DONATE] … pct=51 (~5%)`、`[HL-INTERCEPT]` | — | `v27-team-g09.js` | — |

- 版本核实（`dispatch_source_check.py` → `out/dispatch-source-check.txt`）：把每条调度日志分别套三份源码的门槛数违例——E1 日志套 Va 0 条、套 Vc 923 条；E2 日志套 Vb 0 条、套 Va 15975 条、套 Vc 16181 条；
  E3 日志套 Vc 0 条、套 Vb 86 条。三份源码与各自时期的日志逐条相容。
- **更正**：我在警报 0002/0003 里说「E1 = `v27-apex-live.js@d9a56dc`」不成立——那份文件的调度门槛（内陆号协防 58、进攻 95）与 E1 日志（最小 30 / 82）矛盾；以 hub 补齐的 `v27-team-c116-va.js` 为准（参数表两者相同）。
- 指纹脚本：`dispatch_signature.py`（18134 条调度句，同号相邻调度最小间隔 25 拍）、`attack_pct_signature.mjs`（录像里实际执行的进攻指令）。
- 我的 13 局：A014、A017 = Va；A021/A026/A030/A034/A037/A043/A058/A065/A093/A095 = Vb；B010 = B。
- 任务卡说的「31 个差异参数」来自 hub 的 `params-diff.txt`，它的 c116 列是 **Va** 的值；Vb 与 Vc 的 226 个参数**完全相同**，Vc 与 c110 只差 2 个键。见 §6。

## 1. 代码是怎么拼出来的

- 生成链：单人版 `v27-live.js` →（`make_v27_team.py` 8 组文本替换）→ `v27-team-live.js`。8 组：①`analyze` 邻居里剔除队友/自家号；②`peopleOf` 同；③`searchWater` 同；
  ④海上采样（`doorHarvestCandidates/seaPeople/bankAct`）同；⑤加入组队函数（`isTeammate/isOurSquadBot/findBossId/chooseSpawn/tryPeaceVote/tryEmergencyBossRescue/tryDonateToTeammate`…）；
  ⑥`offers` 里的集火折扣；⑦在 `act` 里挂上救 boss、投票、捐款；⑧开局 DP 日志与组队收尾 `isMopUp`。（`make_v27_team.py` 254–1105 行）
- 类层级（outline-c116.txt）：`Strategy`(209) → `General`(660) → `Style`(1100) → `V13`(1632) → `V17`(2685) → `Policy`(3770)。
- 参数层（后者覆盖前者）：`DEFAULT_PARAMS`(95) → `BASE`(572) → `GENERAL_PARAMS`(574) → `STYLE_PARAMS`(1092) → `PARAMS13`(1301) → `P17`(2664) → `PARAMS`(3695)。生效值共 226 个键（`params.cjs` 真正加载模块后 dump `this.p`）。
- 关键生效值（三份源码相同，除非注明）：`period 5`（g09=2）、`coreFrom 1500`、`dpEnd 1500`、`dpSpend 0.5`、`maxTargets 4`（g09=6）、`feeK 4`、`chunk 0.2`、`pulseFrac 0.12`、`pulseMinShare 0.04`、
  `oppFloorCap 88`（g09=38）、`maxW 0.5`、`winT [[1500,3],[2000,2.85],[2500,1.8]]`、`hold 0.9`、`idleCap 1.25`、`boatEvery 60`、`maxBoats 2`、`boatRange 200`、`killW 1`、`counterClearMode 6`、`aggMemMode 8`、`guardMode 1`、`quotaGuardMode 1`、`seaCore 0`（g09=1）、`flashLoanMode 0`（g09=3）。

## 2. `Policy.act(g)` 每拍执行顺序（E3 源码 4801–4984）

每一拍（不管是不是决策拍）：
1. `canAct(me)` 不成立就返回（4803）。`updateShadowQuota`（4804，→3800）：维护「禁止全额出兵」模式下的影子配额。
2. `flashLoanMode>0` 才走闪电贷状态机（4807，本版=0，不走）；`seaCore>0` 才做登陆点交接、跳岛船（4813–4836，本版=0，不走）。
3. **只有 `t % period(5) === 0` 才往下**（4838）。所以一个号每 5 拍最多做一次决策；`g.online` 下一拍只发一条指令。

t < 1500（`coreFrom`，4839–4879）：
4. `analyze`（→373：只把**非队友**记进 `nb`，无主地像素数 `neutral`）；每 90 拍打 `[HL-TICK]`（4845）。
5. `tryEmergencyBossRescue`（4847，→4215）：局里没有 boss 名字的号就直接返回 false（A 系 10 人编队无 boss）。
6. `super.act` = `V17.act`(2690) → `V13.act`(1813) → `General.act`(752)：`analyze` → `tryPeaceVote`（无 boss 立即返回，4167）→ t>8500 残局自动离场判定（769–784）→ `updateGrudges/updateWars` → `floors`
   → `expandNeutral`（792）→ 因为 `t < dpEnd`，走 **`dpNeutral`**（2383：每个 100 拍地租周期只发一次，量 = 能在第 98 拍前落地的整圈数；发出就打 `[HL-OPENING]`，2409）
   → `pickTarget`（`Style.pickTarget` 1144：按「每像素成本」挑最便宜的邻居；机器人要 `botOk` 且 `price ≤ botMax(60)`；真人因 `preyKill=1` 允许，底线是通用底线的一半 `preyFloor 0.5`）→ `send`（796）
   → 没有无主地且兵力 ≥ `idleCap×100×领土` 时才考虑出船（804–809）。之后 `V13.act` 末尾 `boatFood`（1822）。
   **t<1500 不会调用 `tryDonateToTeammate`**（它自己也在 4329 行拒绝 t<1500）。

t ≥ 1500（4880–4984）：
7. `analyze`；每 90 拍 `[HL-TICK]`（4887）；t≥2700 且每 630 拍由存活的最小编号自家号上报一次录像（4888–4909）。
8. `tryPeaceVote`（4911）。9. t>8500 且自己 <4% 领土且存活自家号 ≤2、合计 <5% → 调用 `sbLeave` **主动离场**（4912–4927）。
10. `tryEmergencyBossRescue`（4928）。11. `updateGrudges/updateWars`（4929–4930）。
12. `cmdsBefore = this.cmds`（4939）→ 有无主地就 `expandNeutral(bal − safeAt(-1))`（4941，→2373→944：维持下一圈所需兵力）→ **`buyLand`**（4942，→5342）。
13. **仅当这一拍前面没有发出任何指令**（`this.cmds === cmdsBefore`）才 `tryDonateToTeammate`（4962），再没有才 `idleBoats`（4963）。
    即：**买地优先于调度，调度优先于出船**；`g.donate()` 返回 true 就 `cmds++`，同拍不再出船。Va/Vb/Vc 三份的 `Policy.act`、`offers`、`buyLand`、`idleBoats` 逐字相同（`diff` 只在参数表与 `tryDonateToTeammate`/救 boss 轻戳处有差异）；c110、g09 结构相同（c110: 4901/4902/4922/4923；g09: 5349/5350/5373/5374）。

c110 与 E3 的 `act` 差异：c110 多 `tryPrivateBossEmoji`（4819）；没有 t>8500 自动离场；录像上报门槛 t≥3960/每 1350 拍。
g09 的差异：决策周期 2 拍；每拍先 `tryInterceptEnemyBoats`（t≥350）与 `tryClaimNearTeamIslands`；买地后多一个 `tryDeterrentCounter`；救 boss 排在买地之后。

## 3. 买地：`offers`（5072）→ `buyLand`（5342）→ `send`（3838 → 479）

- `offers`：对每个邻居 q（已在打的不占名额；新目标受 `maxTargets 4` 与空闲进攻槽限制）算
  `rawNeed = elimCost(q) + q打我的兵 − 我打q的兵`，`c = (rawNeed + 手续费) / 可得像素`（5100）。真人目标再乘各种系数后得到排序价 `rankC`：
  - `nearCollapse`（领土 ≤ `collapseRatio 1.4` × 峰值/4，或别人已压上 ≥65% 所需兵，或「空城全压」）→ 用脉冲预算重算 c（5151–5155）；
  - `bleeding`（有别的真人在打且密度比 <0.75 或压上 ≥15% 兵）→ 乘 `bleedDiscount`（Vb/Vc=1，Va=0.72）；瘦目标乘 `thinDiscount`（Vb/Vc=1，Va=0.78）；
  - 正在打我的 `aggQ`（→`peerAggressor` 4606）→ 按 `defendDiscount 0.85 / defendDiscountMid 0.88` 封顶（5171–5175）；
  - 接触面 <25 像素且吃完要走很多步 → `contactPenalty`（5177–5180）；队友也在打 → 所需兵减去 85% 队友兵（5182–5185）；
  - **集火系数**（5200–5217）：路人队友在打 ×0.68；自家号 ≥1 个在打或压上 ≥15% → ×0.58；q 在打队友 → ×0.75；
    **自家已与某队开战而 q 不属于那一队、q 没打我、也不濒死 → ×1.45（不开第二战线）**；
  - `soleBufferPenalty`（t≥2500、只有 1 个真人邻居且吃掉会暴露新邻居，×1.6；Va=1.15）；`isCrowdedHard` → `crowdedHardPenalty 1.35`（Va=1.08）。
- `buyLand`：`worth = maxW × winRatio(t) × 参考密度`（5350–5352；t≥2500 后参考密度取 max(自己, 0.85×其它真人中位密度)）。
  报价从便宜到贵逐个看：`c ≥ worth` 且 `c ≥ cheap` 且兵力没超过 100×领土 → **停止（这一拍不买）**（5359）。
  留底 `keep = max(预算留底, safe)`，`safe = safeAt(q)`（4543：`max(机器人威胁底线, killW×dpKeep)`，上限 `oppFloorCap × 领土`；
  `dpKeep`(2459) = (最强真人邻居兵力+它压在我身上的兵 − 1.5×我领土)/1.78）。兵力超过软上限（`over`）时 `keep ≤ hold(0.9)×100×领土`（5440–5443）。
  - 机器人：一次送 `1.25×need + 3×接触像素`，凑不够且不足 20% 兵力就跳过（5449–5454）。
  - 真人：满足脉冲条件走**脉冲**——t≥3800 且目标在流血/濒死：补到 `min(0.85need+3cnt, pulseFrac×兵)`，最少 8% 兵（→ 指令千分比 81）（5574–5586）；
    濒死：`max(pulseFrac×兵, min(avail, 0.3need))`（5588–5593）；普通脉冲：`min(1.2need+3cnt, pulseFrac×兵)`（→ 千分比 122；Va 为 204）（5595–5608）；
    已压在 q 身上的兵 ≥4% 自己兵力就不再加（5596）。非脉冲：`1.25need+3cnt`，凑不够且 <20% 兵力跳过（5611–5616）。
- `Strategy.send`(479)：`pct = ceil(兵×1024/余额) − 1`，再 `g.attack(pct, 目标, me)`。只有 c110 在这里加了「联机时同一目标 15 拍内不重复下令」（`v27-team-c110.js` 529–533 的 `_lastTargetSendTick`）；Va/Vb/Vc、g09 没有这道闸。
- `Policy.send`(3838)：`quotaGuardMode` 下若判定本局是「禁止全额出兵」模式且影子配额不足，对真人新目标改发 `attack(0)` 或直接不发。

## 4. 调度（捐兵）函数 `tryDonateToTeammate`：三版源码对照（4325–4518）

共同骨架：`t<1500`/领土<1200/兵力不足/冷却未到 → 返回（4329）；**拍相位门**：`((t/5)|0) % 5 === 槽位 % 5`（4331：每个号每 25 拍只有 1 个决策拍能调度）；
自己正被真人打、或自己打真人的兵 >8% 兵力 → 返回（4343）；`boxedIn`（下称「内陆号」）= 没有任何非队友邻居且没有无主地（4355）；`hasExposedCoast` = 自己有海岸（4356）；
遍历存活自家号 p（领土 ≥1200；自家陆上战线 ≤2 条时放宽到 150，4414）：p 密度 ≥142（我是内陆号）/115（我是前线号）跳过（4418）；
p「没有敌邻居、没被真人打、没打真人」一般跳过（4453）；`isDoomedPocket`（被压 >1.65×兵）跳过（4455–4456）；
`underFire`（p 被真人压上 ≥6% 兵或密度 <88）→ 情形 A `defense_dispatch`（4463–4473）；否则情形 B → `offense_dispatch`（p 在主动打人 `activePush` 或旁边有流血猎物 `hasPreyOpening`）/`yield_opt_dispatch`（4474–4495）；按得分取最高；
`pct = min(floor((兵−留底)×1024/兵), 理想值)`，低于最小值不发（4500–4506）；`g.donate(pct, 目标, me)` 返回 true 就记冷却、`cmds++`、打 `[HL-DISPATCH]`（4508–4514；日志里的 `dAlly` 是发令时受援号的密度）。
**日志是在「发出指令」时打的，不代表引擎执行了**（见 §8）。

| 项 | Va（A001–A017） | Vb（A018–A095） | Vc（A097–A099） |
|---|---|---|---|
| 冷却 / 最低兵力（4329；同号相邻调度实测最小间隔都是 25 拍，由拍相位门决定） | 12 拍 / 30000 | 12 拍 / 30000 | 24 拍 / 35000 |
| 理想千分比 进攻·收益（内陆/前线，4502–4504） | 225 / 170 | **320 / 220** | 220 / 170 |
| 理想千分比 协防（内陆/前线） | 260 / 190 | **380 / 240** | 260 / 190 |
| 最小千分比（4506） | 128 | 180 | 150 |
| 捐出方密度门槛 情形 A 协防（内陆·有海岸 / 内陆·无海岸 / 前线，4465） | 42 / 30 / 102 | 42 / 30 / 102 | 68 / 58 / 102 |
| 捐出方密度门槛 情形 B 进攻·收益（内陆 / 前线，4479） | 82 / 108 | **58** / 108 | 96 / 108 |
| 受援方密度上限 情形 B（内陆：受援号在推进或有敌邻居 / 否则；前线，4480） | 140 / 128；96 | 140 / 128；96 | 94 / 88；88 |
| 受援方密度上限 情形 A | 只有 4418 的 142/115 | 同 Va | 另加 `dAlly < 85`（4466） |
| 「捐出方必须比受援方密」（4466、4481） | 只约束前线号：`dMe ≥ dAlly+16` | 同 Va（**内陆号不受约束**） | 所有号：`dMe ≥ dAlly+15` |
| 留底 情形 B `prodOptFloor`（内陆·海岸 / 内陆·无海岸 / 前线，4382–4384） | 72L / 66L / max(94L, safeAt) | **44L / 34L** / max(92L, safeAt) | 76L / 70L / max(94L, safeAt) |
| 留底 情形 A `emergDefFloor`（4386–4388） | 32L / 22L / max(88L, safeAt) | 32L / 22L / max(88L, safeAt) | 58L / 48L / max(88L, safeAt) |
| 兵力须高于留底的倍数 | A：1.12×；B：1.14× | 同 | 同 |

日志侧的直接后果（`out/dispatch-source-check.txt`，**日志条数，不是执行条数**）：「倒挂」（捐出方密度低于受援方）的调度句 Va 162/1131（14.3%）、Vb 2970/16253（18.3%，其中内陆号协防 1505/3504）、Vc 0/750。
每条被执行的调度让捐出方失去 `pct/1024 + 6.25%` 的兵力（Vb 内陆号进攻型：31.3% + 6.25%）。执行了多少要看录像（§8）。

c110（B 系，`tryDonateToTeammate` 4369–4499）：t≥400、冷却 18；先 boss 捐款，再「小队互救」（队友被真人压上 ≥8% 兵或密度 <75：我密度 ≥ max(55, 对方+15) 就捐 240/155，否则对主攻者发 10% 轻戳 `attack(102)`，打 `[HL-ASSIST]`）；
最后「富余捐款」：前线号密度 ≥112、围死号 ≥55 才捐，千分比 280（围死且密度>110）/185（围死）/153（前线）。g09：同结构，所有捐款固定 51（约 5%）。

## 5. 其它组队函数

- `isOurSquadBot`（3960）：按名字白名单认自家号（去掉方括号前缀后全等）；`isTeammate`（3927）：同队号。`findBossId`（3953）：名字含 kazerd/npl 的队友。A 系无 boss → 所有 boss 分支不触发。
- `tryPeaceVote`（4166）：没有 boss 直接返回（4167，「自治模式永不议和」）。
- `idleBoats`（5019）：围死号（无邻居无无主地）若存在「有陆上战线的自家号」且自己密度 <115 → **不出船**（5031）；否则留底 92L（有战线兄弟）/68L 出远船（航程 2500）。
- t>8500 自动离场（4912–4927）是策略里**唯一**主动调用离场的地方；t<8500 的 `left` 不是策略发出的（见 §8）。

## 6. 参数差异（`out/params-diff.txt`：c110/g09/Vc；`out/params-diff-va-vb-vc.txt`：Va/Vb/Vc；生效值 `out/params-raw-*.json`）

c110 / g09 / Vc 三版 226 键，208 键相同，**18 键不同**：
- 只有 Vc（Va、Vb 同）与另外两版不同（2 个）：`a06AloneSafe`（1,1,**0**：t≥4800 时对「背后还有更强邻居」的目标抬高留底，4549；A 系关）、`a06AggMemGate`（1,1,**0**：陈旧仇家不享受防守折扣，5163；A 系关）。
- 只有 g09 不同（16 个）：`period 2`（决策周期）、`maxTargets 6`、`oppFloorCap 38`（留底上限，其它版 88）、`collapseFloorCap 16`、`collapseRatio 1.45`、`bleedDiscount 0.65`、`thinDiscount 0.72`、`thinMaxTD 0.62`、
  `pulseMinShare 0.03`、`zeroPulseMode 1`、`seaCore 1`（整套海战：登陆点、跳岛、扩面船）、`reigniteBorders 1`、`atkFreshBoats 1`、`narrowBoatFirstMode 1`、`frogHopOverMode 1`、`flashLoanMode 3`。

Va 相对 Vb/Vc 有 **16 键不同**（Vb 与 Vc 参数完全相同；hub 表里的「c116 列」就是 Va 这一组）：
`pulseFrac 0.20`（Vb/Vc 0.12：对真人单次脉冲占兵力比例）、`bleedDiscount 0.72`（1）、`thinDiscount 0.78`（1）、`focusBonus 0.78`（1：对最近打过的目标打折）、`pocket0Mult 0.76` / `pocket1Rank 0.88`（1/1：t<2500 吃掉后不暴露新邻居的目标打折）、
`oppFloorCap 78`（88）、`bleedSafeCap 0`（1）、`crowdedHardCap 1.10`（1.26）、`crowdedHardPenalty 1.08`（1.35）、`soleBufferPenalty 1.15`（1.6）、`overHumanCap 1.12`（1.28）、`overHumanKeep 0.92`（1.12）、
`leaderHardFrom 0`（5000）、`siegeShrinkRatio 0`（0.72）、`overPulseMode 1`（0，Vc 源码里已无读取点）。合计 18 ∪ 16 = 31 键（3 键重叠），与任务卡数字吻合。
方向：Va 对真人更敢打（脉冲大、折扣多、留底低）；Vb 起买地参数回到 c110 的保守值，同时调度函数改成「内陆号更低门槛、更大比例」（§4）；Vc 只改回调度函数与选点半径。
救 boss 轻戳（4291–4298，A 系无 boss 不触发）：Va `B≥8000 且 dMe≥38` 发 `attack(102)`；Vb/Vc `B≥25000 且 dMe≥86`、36 拍冷却、`attack(82)`。

## 7. 日志句式 → 源码位置（`out/logcalls-*.txt`）

| 句式 | E3 行 | 函数 | 触发条件 |
|---|---|---|---|
| `[HL-GAME-INIT] mode= map= mapSeed= seeded= me=` | — | 宿主包装层（不在三份源码里） | 进局时 |
| `[HL-SPAWN-BACKEND] me= slot= role= -> (x,y) bossDist= minAllyDist= voronoi=` | 4036 | `Policy.chooseSpawn` | 后台协调器返回的点位变化 >4 像素时 |
| `[HL-SPAWN] me= slot= (squad=N,rankIdx=k) -> … chosenSlots= minSep=` | 4124 | `Policy.chooseSpawn` 自主兜底 | 后台点位还没到（或不可用）时；`squad=N` = 该号在本盘看到的自家号数 |
| `[HL-OPENING] t= cyc= DP expand rings= spend=X/bal terr=` | 2409 | `V13.dpNeutral` | t<1500 每个地租周期发出一次无主地进攻 |
| `[HL-TICK] t= terr= bal= dens= nb= neut= cmds= boats= avgMs= maxMs= skip=` | 766/2699/4845/4887 | 各层 `act` | 本地拍号 t%90==0 的决策拍 |
| `[HL-DISPATCH] t= <kind> pct= -> ally= boxedIn= myBal= dMe= dAlly=` | 4513 | `tryDonateToTeammate` | `g.donate` 返回 true（=指令已发出） |
| `[HL-DONATE] … emergency boss donate` / `[HL-ASSIST] … boss-assist poke` | 4282 / 4301 | `tryEmergencyBossRescue` | 有 boss 的局 |
| `[HL-PEACE] …` | 4200 / 4208 | `tryPeaceVote` | 有 boss 的局 |
| `[HL-DONATE] … boss / squad rescue / surplus donate`、`[HL-ASSIST] … squad-rescue poke` | c110 4413/4442/4494/4454 | c110 `tryDonateToTeammate` | B 系 |
| `[HL-INTERCEPT]`、`[HL-ISLAND-GUARD]` | g09 4664/4777 | g09 | G 系 |
| `[HL-SLOW-TICK]` | — | 宿主包装层 | 单拍决策耗时超阈值 |

注意：**进攻/出船没有任何日志句**，只能从录像命令流看（§8）。`cmds=` 是策略自己数的「已发出指令数」。

## 8. 执行层：日志 ≠ 执行（本轮新证据，脚本 `replay_cmds.mjs` 等）

- 引擎记录录像的调用点在全部校验之后（`live_game_js.js`：捐款 `qj.qv` 依次过 `hk/hl/iT/rj/rn/rD/ao.ei` 才 `bC.rg.rh(2,…)`）→ **`replay.txt` 的命令流 = 被引擎执行的指令**，被拒的不在里面。不需要地图即可解码。
- 服务器每 7 拍结算一帧（录像命令拍号全部 ≡ 0 mod 7）；正常「发令→执行」延迟中位 12–14 拍（`cmd_latency.mjs`）。
- 调度真账（`donation_ledger.mjs`，日志条数 → 录像里执行条数）：A014 734→157，A065 249→89，A058 49→28，A037（赢）247→151。「录像有而日志没有」的我方捐款为 0。
- 客户端落后：A058 全队延迟从 t≤470 的 7–20 拍恶化到 t=700–900 的 182–509 拍；7 个号的离场指令出现在服务器拍 784/1120/1680/1904，而它们本地最后一条 `[HL-TICK]` 是 360–1350。
  全量体检表 `out/exec-layer.tsv`（每局：延迟分位、离场号的 服务器拍/本地拍、调度 日志数/执行数）。
- 拆盘：同一个「对局包」里的号可能在不同的游戏实例里（A017 是 1+9，A043 是 2+8；`out/instance-split.tsv`，`instance_split.mjs`）。包里的录像只覆盖其中一盘。
- 捐款引擎规则（`src/engine/live-donation-check.txt` 与引擎源码一致）：手续费 = floor(64×余额/1024)（6.25%，与千分比无关）；到账 = floor(余额×(pct+1)/1024)，受对方上限（150×领土 − 余额）截断；
  反喂养配额：每个受捐人累计点数 ≤ 全局上限（开局 15，逐百拍 +4/+6/+8/+10），t≥4284 后不限。

## 9. 与 hub `PLAN.md` 假设的对照（仅事实）

- 「`g.donate()` 返回 true 后在 `act` 开头直接 return、跳过 `buyLand`」：Va/Vb/Vc、c110、g09 五份源码都不是这样——调度在 `buyLand` 之后，且仅当同拍没有别的指令（§2 第 13 步）。
- 「调度被拒」：日志无法区分「被引擎拒」与「指令根本没到/迟到」。要用录像对账（§8）。
- 「内陆号憋死」：`idleBoats` 5031 行的条件（有战线兄弟且密度 <115 就不出船）+ 调度门槛（内陆号做收益型调度的密度门槛 Va 82 / Vb 58 / Vc 96）共同决定内陆号的出口，属于代码事实。

## 10. 未解 / 待核

1. 宿主包装层（`g.online/canAct/donate` 的实现、`[HL-SLOW-TICK]`、`[HL-GAME-INIT]`、离场触发）不在 `c136-data`。hub 广播 0002 口述「`left` = worker 断线或连续 3 次求值超时（4.5 秒看门狗）后外层调用离场」，我没有源码可核，复盘里按「口述」引用。
2. 出生指令没有被执行的号（A026 八个、A070 十个等，见 SPAWN-MAP §5）原因未明。
3. 地图二进制已补到 `c136-data/src/sim/maps/`（62 份）。模拟器的组队模式与真实对局的差异（队伍分配、组队配色的随机数消耗）要先补齐才能逐拍重演，M2 第一步做，吻合度随复盘给出。

## 11. 复算入口

`dispatch_signature.py`、`dispatch_source_check.py`、`attack_pct_signature.mjs`、`params.cjs` + `params-diff.cjs`、`logcalls.cjs`、`outline.cjs`、`replay_cmds.mjs`、`donation_ledger.mjs`、`cmd_latency.mjs`、`exec_layer_scan.mjs`、`instance_split.mjs`、`spawn_roles.py`（均在 `agents/R05/scripts/`，node 脚本用 `bash c136-review/tools/run-heavy.sh node …` 跑）。
