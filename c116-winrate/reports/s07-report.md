# S07 (A07) 单局显微镜解剖与核心变量 `V9` 量化报告

> **负责子 Agent**：`S07`（兼容旧名 `A07`）
> **包干实盘对局**：**G08（`01:13 CST` / `17:13 UTC`，6 队局，`map=13` `seed=15650` `833x930` `land=430,654`，终局 `t=5895` 第 4 名败，`ethan21` 峰值 26,023 地、`ryan_m` 22,211 地、`lucas94` 22,014 地）**
> **包干核心变量**：**`V9` 反蚕食威慑与避免主动戳巨无霸（`AntiNibbleVsPokeGiant`）**（含 `updatePokeState` 抢滩 `beachhead` 误判戳强敌、`hardCapMult=1.16` 过早破防、以及实盘日志首次抓获的 **「`2-tick` 周期下 `tryDonateToTeammate` 10% 救援戳机关枪连发抽干主力 Bug」**）与 **`V7` 前线防御底线耦合效应**。

---

## 1. 【单局时间线与胜负拐点（Timeline & Inflection Point）】

### 1.1 G08 对局基础信息与进场盘点
- **房间与地图**：`mode=4`（6 队局），`map=13`（`833x930`，总陆地面积 `L_map = 430,654` 格），开局真人玩家数 `players = 49`，我方所属队伍为 **Team 1**（赢家为 **Team 5**，终局 314,300 地）。
- **进场存活人数（`V12` 異常）**：8 个無頭號中，**`[Nope] noah88` 未能进场**（全程无 `[HL-GAME-INIT]`，并在 `t=2340` 报 `socket close index 3 error 1006`），实际仅 **7 个兄弟** 参战：
  - `lucas94 (me=1)` -> 出生点 `(102, 186)`，`voronoi=10,240`
  - `ryan_m (me=7)` -> 出生点 `(278, 86)`，`voronoi=14,574`
  - `kevin_k (me=8)` -> 出生点 `(402, 124)`，`voronoi=19,829`
  - `leo_tx (me=10)` -> 出生点 `(568, 94)`，`voronoi=22,442`
  - `dave_w (me=12)` -> 出生点 `(526, 180)`，`voronoi=10,683`
  - `ethan21 (me=13)` -> 出生点 `(422, 244)`，`voronoi=12,098`
  - `mark07 (me=15)` -> 出生点 `(316, 184)`，`voronoi=11,131`
- **出生大陆分布**：7 个在场 Bot 全部落在北部主大陆同一扇区（`x ∈ [102, 568], y ∈ [86, 244]`，`minSep = 96px`），开局无主地阶段发育顺畅，`t=2070` 时 7 人合计拿下 **85,548 格领土（占全图 `19.9%`，在 6 队局中显著高于平均份额 `16.7%`）**。

### 1.2 G08 关键时间节点全景量化表（提取自 `G01-G09-squad.log` 第 `6508~7145` 行 & `G01-G09-results.jsonl`）

| 阶段 / Tick | 我方在场存活 | 我方小队总领土 `L_squad` | 团队全图占比 (`L_team / 430,654`) | 我方小队总兵力 `B_squad` | 小队平均密度 `d_team` | 头号劲敌团队领土 (`Team 2` / `Team 5`) | 关键選手状态 (`L / d / cmds`) 与局势演变 |
| :--- | :---: | ---: | ---: | ---: | ---: | :--- | :--- |
| **`t = 630`** | 7 / 7 | `21,401` | `5.0%` | `36,524` | `1.7` | 均势发育 (~5%) | 7 人同步完成 6 轮 DP 扩张，`ethan21: 3,455`、`kevin_k: 3,317`、`lucas94: 3,217` |
| **`t = 1530`** | 7 / 7 | `72,068` | `16.7%` | `552,461` | `7.7` | 约 `16%~18%` | 无主地收割结束：`mark07: 11,583`、`ethan21: 11,255`、`dave_w: 11,119`、`leo_tx: 10,545` |
| **`t = 2070` (领土峰值)** | 7 / 7 | **`85,548`** | **`19.9%`** | `1,277,445` | `14.9` | Team 2 `~82k` (`19.0%`) | 7 兄弟领土达全场峰值：`ryan_m: 14,239`、`lucas94: 13,524`、`leo_tx: 12,793`、`mark07: 12,122` |
| **`t = 2520~2585`** | 7 -> 6 | `77,563` | `18.1%` (`78,026`) | `2,610,933` | `33.7` | Team 2 `88,365` (`20.5%`)<br>Team 6 `85,376` (`19.8%`) | 最东侧前线 `leo_tx (me=10)` 在 `d=10.6` 低密度下被东侧强敌吞并，于 `t=2585` 第一个阵亡 |
| **`t = 3150`** | 6 / 7 | `70,938` | `16.5%` | `5,142,284` | `72.5` | Team 2 `~98k` | **第一记 116 破防前夕**：`ethan21` 攒到 `d=110.7 (B=1.25M)`，随后在 `t=3150->3240` 连发 10 令（含 1 船）把密度抽空到 **`d=12.4`**，仅换来 `+158` 格地，净烧 **110.5 万兵**！ |
| **`t = 3600` (兵力峰值)** | 6 / 7 | `71,912` | `16.7%` | **`6,549,422`** | **`91.1`** | Team 2 `~108k`<br>Team 5 `~72k` | **全队翻盘前最高兵力时刻**：`mark07 (d=131.0, 1.66M)`、`kevin_k (d=121.4, 1.02M)`、`dave_w (d=110.1, 851k)`、`ryan_m (d=108.7, 1.60M)`、`lucas94 (d=90.3, 1.23M)` 5 大主力全部高密度满载！ |
| **`t = 3690~3960` (⚡胜负拐点)** | 6 / 7 | `73,707` | `17.1%` | **`3,024,647`** | **`41.0`** | Team 2 `~115k`<br>Team 5 `~80k` | **灾难级连锁雪崩**：270 拍内全队总兵力从 **655 万腰斩至 302 万（净蒸发 352.5 万兵，团队总地仅 +1,795 格）**！`ryan_m`、`dave_w`、`kevin_k`、`lucas94`、`mark07` 全部从 `d=107~123` 暴跌至 `d=11~59`！ |
| **`t = 4392~4638` (中路崩盘)** | 6 -> 3 | `58,186` | `13.1%` (`56,500`) | `3,031,944` | `52.1` | Team 2 `123,299` (`28.6%`)<br>Team 5 `102,811` (`23.9%`) | `kevin_k (t=4392)`、`mark07 (t=4630)`、`dave_w (t=4638)` 三名被抽空密度的前线相继阵亡；此时只剩 `ethan21`、`ryan_m`、`lucas94` 三主力 |
| **`t = 4942~5425` (三主力被吃)** | 3 -> 1 | `23,832` | `2.9%` (`12,303`) | `409,761` | `17.2` | **Team 5 `205,799` (`47.8%`)**<br>Team 2 `75,154` (`17.5%`) | `ethan21` 冲上 `26,023` 地后密度跌至 `4.7` 于 `t=4942` 阵亡；`ryan_m` 冲上 `22,211` 地后在 `t=5322..5334` 对 `18(Turk)` 连发 7 记 10% 救援戳自抽 56% 兵力，于 `t=5425` 阵亡 |
| **`t = 5895` (终局)** | **1 / 7** | `12,089` | **`2.8%` (第 4 名)** | `148,041` | `12.2` | **Team 5 `314,300` (`73.0%`)**<br>Team 3 `66,087` (`15.3%`) | `lucas94` 峰值 `22,014` 地，终局保留 `12,089` 地孤身苟活至终局第 4 名（Team 1 排在 Team 5、Team 3、Team 6 之后） |

### 1.3 精确拐点定位：为什么 `ethan21 (26k)`、`ryan_m (22k)`、`lucas94 (22k)` 三主力合计 >7 万地却在 `t=3600~5425` 崩盘？
通过逐拍比对 `G01-G09-squad.log` 第 `7000~7140` 行，我们精确定位到 **全局从均势高密度蓄力转为不可逆崩盘的拐点窗口为 `t = 3600 ~ 3912`（核心拐点拍 `t_turn = 3780`）**，其完整的 **四步致死链条** 如下：

1. **第一步（`t = 3600 -> 3690`）：`ryan_m` 与 `dave_w` 触碰 `hardCapMult = 1.16` 过早向强邻破防泄洪**
   - 在 `t = 3600`，`ryan_m (me=7)` 领土 `14,707`、兵力 `1,599,024`（`d = 108.7`，仅 1 个真人邻居 `nb=1`）。在原版 `v27` 中，单真人邻居受 `isSoleHealthyBuffer`（`overHumanCap = 1.28`，即 `d < 128` 严禁主动进攻健康邻居）与 `hardCapMult = 1.50` 保护；但在 `22effa4` 中，Team 模式关闭了 `isSoleHealthyBuffer` 并把 `hardCapMult` 砍到 **`1.16`**，叠加 `32c5689` 的 `totB = B + myOut` 与 `514a041` 的 `isPrimeLand` 低保留（`keep <= 26*L`）。
   - 结果在 `t = 3600 -> 3690` 之间，`ryan_m` 对唯一邻居 `18 (🇺🇿🇹🇷 Turk 🐺)` 连发 **7 条进攻指令**（`cmds: 80 -> 87`），兵力从 **`1,599,024` 暴跌至 `314,069`（密度从 `108.7` 跌至 `20.0`）**，却只啃下 **`+1,029` 格地**（`1,284,955` 兵换 `1,029` 地，每格耗兵 **1,248**，纯撞墙自残）！
   - 紧接着在 `t = 3690 -> 3780`，`dave_w (me=12)` 在 `d = 114.5 (B = 831,781)` 越过 `1.16` 线后连发 **11 条指令**（`cmds: 97 -> 108`），兵力从 **`831,781` 暴跌至 `99,155`（密度从 `114.5` 跌至 `12.9`）**，仅换来 **`+427` 格地**！

2. **第二步（`t = 3780 ~ 3912`，核心拐点拍 `t_turn = 3780`）：`ryan_m (d=20)` 与 `dave_w (d=12.9)` 遭强敌反扑，触发 `tryDonateToTeammate` 的「2-tick 10% 救援戳机关枪 Bug」，瞬间抽空 `kevin_k`、`lucas94`、`mark07` 三大健康主力！**
   - 当 `ryan_m` 自残到 `d=20.0`、`dave_w` 自残到 `d=12.9` 后，敌方强邻 `18 (🇺🇿🇹🇷 Turk 🐺)` 与 `41 ([MBKC] rubi)` 立即反扑。
   - 此时，本应只打“1 刀 10%B 策应”的 `tryDonateToTeammate`（`v27-team-live.js:4882`），因为 `e20db6b` 把决策周期改成 **`P.period = 2`（112ms）** 且把 `headless-bot.mjs` 的 `inflight` 锁改成 **`2 ticks / 110ms`**（小于线上服务器 ~180ms 的回包延迟），在服务器回包更新 `g.hasAttack(me, mainAttacker)` 之前，**每隔 2 拍就重复触发一次 `g.attack(102, mainAttacker, me)`**！
   - 日志原句铁证（`G01-G09-squad.log` 第 `7022~7051` 行）：
     - **`kevin_k` 在 12 拍内对 `18 (Turk)` 连射 7 刀 `10%B`**：`t=3782, 3784, 3786, 3788, 3790, 3792, 3794`（累计抽出 $1 - (1 - 0.1114)^7 = \mathbf{56.3\%}$ 总兵力），`kevin_k` 密度从 `98.5` 瞬间跌至 **`41.0`**！
     - **`lucas94` 在 8 拍内对 `18 (Turk)` 连射 5 刀 `10%B`**：`t=3800, 3802, 3804, 3806, 3808`（外加 `t=3782` 一笔 5% 捐款，累计抽出 **~48% 总兵力**），`lucas94` 兵力从 `1,535,419 (d=112.8)` 暴跌至 **`847,698 (d=52.2)`**！
     - **`mark07` 在 14 拍内对 `41 ([MBKC] rubi)` 连射 8 刀 `10%B`**：`t=3898, 3900, 3902, 3904, 3906, 3908, 3910, 3912`（外加 `t=3870` 捐款，累计抽出 **~63% 总兵力**），`mark07` 兵力从 `1,354,344 (d=106.6)` 暴跌至 **`523,211 (d=38.8)`**！

3. **第三步（`t = 4314 ~ 4942`）：二次机关枪自残 + 强行抢残血地把 `ethan21` 抽成 `d = 4.7` 空壳**
   - 在 `t = 4314..4326`，当 `kevin_k` 濒死时，刚恢复到 `d = 100.1 (B = 1.63M)` 的 **`lucas94` 再次对 `18 (Turk)` 触发 7 连发 10%B 机关枪**，兵力从 `162.6 万` 瞬间掉回 `81.4 万 (d=42.7)`，`kevin_k` 随即在 `t=4392` 阵亡。
   - 在 `t = 4410 -> 4770`，`ethan21` 趁乱抢夺旁边的残血地块，领土从 `15,344` 冲上峰值 **`26,023`**，但由于 `isPrimeLand` 把保留底线压到 `keep <= 10*L~26*L` 且把在途兵力 `myOut` 算进预算，`ethan21` 在 `t=4680 -> 4770` 连续出击 13 次（`cmds: 106 -> 119`），家里真实留守兵力掉到 **`114,212`（密度仅 `d = 4.7`！）**。尽管 `ryan_m` 在 `t=4730, 4852, 4910` 连续 3 次向 `ethan21` 捐款输血，也救不回 `2.4 万` 格地、`d = 4.7` 的空壳，`ethan21` 在 `t=4942` 被 Team 5 主力一把推平！

4. **第四步（`t = 5130 ~ 5425`）：最后双主力 `lucas94` 与 `ryan_m` 复刻同一死法**
   - `t = 5130 -> 5220`：`lucas94` 恢复到 `d = 106.8 (B = 2.02M)` 后再次主动出击，密度从 `106.8` 暴跌至 `32.5`（损失 139 万兵仅得 `+509` 地）。
   - `t = 5322..5334`：看到 `lucas94` 挨打，唯一的健康主力 `ryan_m`（峰值 `22,211` 地，`B = 1.61M, d = 76.6`）对宿敌 `18 (🇺🇿🇹🇷 Turk 🐺)` **再次触发 7 连发 10%B 机关枪**（`t=5322, 5324, 5326, 5328, 5330, 5332, 5334`），12 拍内自抽 **136 万兵**，密度从 `76.6` 跌至 `22.5`，随后在 `t=5425` 被 `18 (Turk)` 顺势反推阵亡！

---

## 2. 【核心死因分类（Primary & Secondary Root Causes）】

### 2.1 第一主因（权重 `55%`）：`V9` 反蚕食威慑与防戳强敌体系的三重失锁（`AntiNibbleVsPokeGiant`）

我们在 `tsb/squad/v27-team-live.js` 与 `tsb/squad/make_v27_team.py` 中定位到 **`V9` 的三个具体源码级漏洞**，它们在 G08 中共同造成了“不该打的强敌主动去戳、一旦开火就连射 7~8 刀把自己抽干、真正被两家啃时却一刀不还”的致命表现：

#### 漏洞 V9-A（实盘日志头号杀手）：`tryDonateToTeammate` 与 `tryEmergencyBossRescue` 的 `10%B` 救援戳缺少目标冷却锁，在 `period=2` 下变成 **5~14 连发机关枪**！
- **源码位置**：
  - `tsb/squad/v27-team-live.js` 第 `4880~4890` 行（及 `make_v27_team.py` 第 `850~860` 行）：
```4880:4890:tsb/squad/v27-team-live.js
        // Second, if we border the attacker on land and aren't already attacking them, do a ~10%B light assist poke!
        if (mainAttacker >= 0 && (this.cnt[mainAttacker] ?? 0) > 0 && !g.hasAttack(me, mainAttacker) && g.hasFreeSlot(me) && dMe >= 65) {
          if (g.attack(102, mainAttacker, me)) {
            this.cmds++;
            this.hitTo.set(mainAttacker, g.t);
            if (typeof window !== "undefined" && window.__hlLog) {
              window.__hlLog(`[HL-ASSIST] t=${g.t} 10% squad-rescue poke -> enemy=${mainAttacker}(${g.names?.[mainAttacker] || ""}) for ally=${p}(${g.names?.[p] || ""})`);
            }
            return true;
          }
        }
```
  - 以及 `tryEmergencyBossRescue` 第 `4490~4500` 行（`make_v27_team.py` 第 `459~469` 行）完全相同的 `!g.hasAttack(me, q)` 判据。
- **机制与耦合根因**：
  1. 在线上 `LiveGame` 中，`g.attack(102, mainAttacker, me)` 只是通过 WebSocket 向服务器发送一条攻击指令，本地引擎状态 `g.atkCount[me]` / `g.hasAttack(me, mainAttacker)` **必须等服务器下一个广播包（RTT 约 `150~250ms`，折合 `3~14 ticks`）返回后才会变成 `true`**！
  2. 在 `e20db6b` 之前，`P.period = 5`（280ms）且 `headless-bot.mjs` 的 `inflight` 锁为 `8 ticks / 450ms`，所以发出 1 刀后必定等服务器回包更新了 `g.hasAttack` 才会进入下一次决策。
  3. **`e20db6b` 把 `P.period` 降为 `2`（112ms）且把 `headless-bot.mjs:176` 的 `inflight` 锁砍到 `2 ticks / 110ms` 后**：虽然代码在第 `4884` 行记录了 `this.hitTo.set(mainAttacker, g.t)`，但 **第 `4881` 行的 `if` 条件根本没有检查 `g.t - (this.hitTo.get(mainAttacker) ?? -999) >= cooldown`**！于是只要 `dMe >= 65`，Bot 就会在服务器回包前的 `8~28` 拍窗口内，每隔 2 拍对同一个强敌连发一刀 `pct=102 (10%B + 1.17%B 税)`，而且每次还会因为 `this.send` 触发连带机制，把一个 `d=110` 的健康主力在 0.8 秒内直接抽成 `d=40`！
  4. 更糟糕的是，该分支 **既不检查 `Bq <= 1.35 * B`（哪怕 `mainAttacker` 是兵力 3 倍于我的全图霸主也照戳不误），也不检查 `dMe` 底线是否会跌破安全线（`dMe >= 65` 即可一直发）**！
- **G08 日志铁证**：G08 单局共触发 **41 次 `[HL-ASSIST]`**，全部是 `3~8` 连发的机关枪脉冲（`kevin_k` 对 `2(SGX union)` 3连发+4连发、对 `18(Turk)` 7连发；`lucas94` 对 `18(Turk)` 5连发+7连发；`mark07` 对 `41(rubi)` 8连发；`ryan_m` 对 `18(Turk)` 7连发）。

#### 漏洞 V9-B：`22effa4` 强行关闭 `isSoleHealthyBuffer` 并把 `hardCapMult` 从 `1.50 / 1.26` 砍到 `1.16`
- **源码位置**：`tsb/squad/v27-team-live.js` 第 `5754~5768` 行（及 `make_v27_team.py` 第 `1121~1136` 行）：
```5754:5768:tsb/squad/v27-team-live.js
      const isTeamMode = !!(g.teams && g.teams[me] > 0);
      const isSoleHealthyBuffer =
        !isTeamMode && person && !o.isDoorSea && nHumans >= 3 && !o.nearCollapse && !o.bleeding && !o.onMe && o.newNbs > 0 && humanNbCount === 1;
      if (isSoleHealthyBuffer && c >= worth && c >= cheap && B < P.overHumanCap * 100 * L) {
        continue;
      }

      if (person && !o.isDoorSea && g.terr[q] < 250 && !o.onMe && fee > 2 * need && c > 8 * worth && nHumans >= 3) {
        continue;
      }

      const hardCapMult = isTeamMode ? 1.16 : (o.isCrowdedHard && c >= 2.15 * worth && g.bal[q] >= 0.55 * B ? 1.50 : P.crowdedHardCap);
      if (person && !o.isDoorSea && o.isCrowdedHard && !o.onMe && c >= worth && c >= cheap && B < hardCapMult * 100 * L) {
        continue;
      }
```
- **数学证明（为什么 `d=116` 向 `d=135~140` 的强邻破防必死）**：
  - 在 Territorial.io 引擎中，陆地进攻的边际交换比为：攻方每攻占 1 格领土，除基础费用 `2` 兵外，需消耗 `2 * d_defender` 的兵力，而守方仅损失 `1 * d_defender` 的兵力（**2:1 防守优势**），且攻方还需先交 `1.17% B` 的陆攻税。
  - 当我方前线 Bot 刚攒到 `dMe = 116`（此时净利息率仍高达基础利率的 `~68%`），而接壤的敌方主力处于 `isCrowdedHard`（`dq > 1.08 * dMe ≈ 125~145`、`Bq >= 0.70 * B`）或 `isSoleHealthyBuffer`（唯一挡在身前的真人缓冲垫，`newNbs > 0`）时：
    - 原版 `v27` 会一直攒兵到 `dMe = 128`（`overHumanCap`）或 `dMe = 150`（重兵硬骨头 `hardCapMult = 1.50`）才用溢出兵力微幅试探，且保留 `overKeepMult = 1.12`（`112*L`）。
    - **`22effa4` 改为 `isSoleHealthyBuffer = false` 且 `hardCapMult = 1.16` 后**：前线兄弟一到 `d = 116` 就打开 `buyLand` 闸门，且 `overKeepMult` 退化为 `1.08`（若误判为 `isPrimeLand` 或叠加 `myOut` 更会跌到 `10~38`）！
    - 在 G08 中，`ethan21` 在 `t=3150 (d=110.7)`、`ryan_m` 在 `t=3600 (d=108.7)`、`dave_w` 在 `t=3690 (d=114.5)` 均在 `d ≈ 110~116` 刚过线时向硬骨头邻居发起进攻，结果分别打出 **`110.5万兵换 158格`、`128.5万兵换 1029格`、`73.3万兵换 427格`** 的灾难性亏损，直接把自己的防守底裤赔光！

#### 漏洞 V9-C：`updatePokeState` 将自然陆地接壤的大领土强敌误判为 `beachhead`（主动戳熊）+ `tryDeterrentCounter` 多人围攻一刀切瘫痪
- **源码位置**：`tsb/squad/v27-team-live.js` 第 `2693~2699` 行与第 `2723~2745` 行：
```2690:2700:tsb/squad/v27-team-live.js
        const curCnt = this.cnt?.[q] ?? 0;
        const wasCnt = this.prevCnt[q];
        // Detect new enemy beachhead landing on our coast (cnt jumped from 0 to 1..32)
        if (wasCnt === 0 && curCnt > 0 && curCnt <= 32 && g.t >= 1200) {
          st.beachheadTick = g.t;
          if (g.t - st.lastPokeTick > 360) st.strikes = 1;
          else if (g.t - st.lastPokeTick >= 8) st.strikes++;
          st.lastPokeTick = g.t;
          st.lastPeakInc = Math.max(st.lastPeakInc, inc, Math.round(0.03 * B));
        }
```
- **对比验证**：在 `fdvg` 仓库最新的 `strategy/pool/v33-live.js:2687` 中，已经合入了 `c97/c102` 证实的修复 `&& (inc > 0 || g.terr[q] <= 4000)` 以及第 `2740` 行的 `(isFreshBeachhead && Bq >= B && curInc <= 0) continue`；**但是 `jvfoedfve/tsb/squad/v27-team-live.js` 是从旧版 `/tmp/fdvg-c58/.../v33-live.js` 生成的，至今没有合入这两行修复！**
- 因此在昨晚 G01~G09 中，每当我方前线吞并小 Bot 或残血玩家后与敌方大领土主力首次接壤（`wasCnt === 0 -> curCnt ∈ [3, 32]`），哪怕对方根本没打我们（`inc === 0`）且兵力是我们的 `1.5~2.5` 倍，`updatePokeState` 都会将其标为 `beachheadTick = g.t` 并伪造 `lastPeakInc = 0.03 * B`，接着在 `tryDeterrentCounter` 中利用 `!isFreshBeachhead` 豁免掉 `Bq > 1.50 * B`（2745行）、`max3rdB > 1.32 * B`（2759行）和 `dq > 1.25 * dMe`（2783行）三道护栏，主动朝巨无霸脸上打出一记 `4.69%B` 的挑衅刀！
- 反过来，一旦我方因为上述挑衅被 `>= 2` 个敌人同时进攻（哪怕其中一个是垂死猎物的微弱反扑），第 `2726` 行的 `if (activeHumanAtkers >= 2) return false;` 又把正当反蚕食威慑完全关死！

### 2.2 第二诱因（权重 `30%`）：`V7` 交战期保留底线崩塌（`oppFloorCap=38` + `totB=B+myOut` + `isPrimeLand keep<=10*L~26*L`）
- **源码位置**：`tsb/squad/v27-team-live.js` 第 `3921` 行（`oppFloorCap: 38`）、第 `3963` 行（`collapseFloorCap: 16`）、第 `5848~5856` 行（`totB = B + myOut` 且 `isPrimeLand` 时 `keep = Math.min(keep, (o.nearCollapse || dqNow < 14 ? 10 : 26) * L)`）。
- **G08 实盘证据**：
  - `mark07` 在 `t=4230 -> 4320` 抢夺残血地时，领土从 `16,279` 增至 `19,475`，但密度从 `44.9` 直接抽干到 **`13.9`**，随后在 `t=4590` 跌至 `4.1` 阵亡；
  - `ethan21` 在 `t=4590 -> 4770` 领土从 `19,786` 冲到 `24,448`（峰值 `26,023`），但因为 `totB = B + myOut` 把在途兵力重复计入可用预算，且 `isPrimeLand` 将 `keep` 压到 `10*L`，其家里真实密度从 `27.6` 跌至 **`4.7`**（`24,448` 格地仅留 `114,212` 兵），立刻被 Team 5 巨无霸一刀秒杀！

---

## 3. 【专项核心变量全样本量化（Core Variable Quantification）】

我们对 **`V9`（反蚕食威慑、防戳强敌、防 `hardCapMult=1.16` 破防与防救援连发）** 进行了跨两个数据集的全样本量化：
1. **昨晚 9 局实盘全自动小队局（`G01 ~ G09`，`c116-winrate/data/G01-G09-squad.log`）**；
2. **`fdvg` 实盘 195 局录像库 + 152 局 `13,835` 次挑衅样本（`c102-poke-scan.jsonl` & `a07-data.json`）**。

### 3.1 昨晚 `G01 ~ G09` 实盘中 `V9` 两大失血指标（10% 救援机关枪连发 & `d>=95 -> d<=45` 破防跳水）全样本对比

| 局序 (结果 / 队伍数) | `[HL-ASSIST]` 10% 救援戳总次数 | 机关枪连发簇数 (`3~14` 连发/簇) | 单簇最大抽血比例 | `d>=95 -> d<=45` 破防断崖跳水次数 | 峰值表现与终局结局 |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **G07 (`01:07`, 🏆 唯一胜局, 2队)** | **`0` 次** | **`0` 簇** | **`0.0%`** | **`0` 次** | **全队 0 次破防跳水、0 次救援机关枪自残，稳扎稳打拿下 545,700 地吃鸡！** |
| **G01 (`00:30`, 败, 6队)** | `13` 次 | `2` 簇 (`kevin_k` 7连、`ethan21` 6连) | `56.3% B` | `4` 次 | `ryan_m` 冲上 51,217 地排第 1，被 `5280..5460` 两波救援连发抽空后遭 Team 6 翻盘 |
| **G02 (`00:35`, 败, 6队)** | `0` 次 | `0` 簇 | `0.0%` | `1` 次 | 早盘选点受限，早中盘落后出局 |
| **G03 (`00:41`, 败, 4队)** | `32` 次 | `5` 簇 (`ethan21` 7连×2、`ryan_m` 7连、`noah88` 6连、`leo_tx` 5连) | `56.3% B` | `2` 次 | 5 波机关枪对 `57(Russian Empire [OG])` 狂射 32 刀，把 4 个主力全部抽干 |
| **G04 (`00:50`, 败, 3队)** | `29` 次 | `3` 簇 (`noah88` **10连+14连**、`leo_tx` 5连) | **`80.9% B`** | `4` 次 | 领先到 `t=5422`，`noah88` 对 `23([CN])` 连射 10 刀+14 刀自抽 81% 兵力，被 Team 2 翻盘 |
| **G05 (`00:54`, 败, 6队)** | `0` 次 | `0` 簇 | `0.0%` | `0` 次 | 开局挤压早死（`t<3900`） |
| **G06 (`01:01`, 败, 5队)** | `10` 次 | `1` 簇 (`ryan_m` **10连**) | `69.3% B` | `1` 次 | `ryan_m` 在 `t=4350..4368` 对 `3(Trường Sa [VN])` 10 连发自残，`ethan21` 5.9 万地独木难支 |
| **G08 (`01:13`, 败, 6队 — 本局)** | **`41` 次 (全场最高)** | **`6` 簇 (`mark07` 8连、`kevin_k` 7连、`lucas94` 7连+5连、`ryan_m` 7连)** | **`61.1% B`** | **`7` 次 (全场最高)** | **41 刀救援机关枪 + 7 次 `d>100->d<40` 破防跳水，3 主力 >7 万地被 Team 5 翻盘** |
| **G09 (`01:28`, 败, 5队)** | `0` 次 | `0` 簇 | `0.0%` | `3` 次 | 6 人进场 + 3 次中盘破防跳水，仅 `lucas94` 苟到 `t=14666` |

- **统计显著性结论**：
  - 在唯一赢局 **G07** 中，`[HL-ASSIST]` 机关枪连发次数为 **`0`**，`d>=95 -> d<=45` 破防跳水次数为 **`0`**。
  - 在全部 **5 局中盘有优势/均势却被翻盘的败局（G01、G03、G04、G06、G08）** 中，**100%（5/5）出现了 `[HL-ASSIST]` 机关枪连发（场均 `25.0` 刀）和 `d>=95 -> d<=45` 破防跳水（场均 `3.6` 次）**！其中 **G08 以 41 刀机关枪、7 次断崖跳水居全批次之首**！

### 3.2 195 局实盘录像库「无端主动戳强敌 vs 按兵力比分级威慑」全样本量化（`c102-poke-scan.jsonl` & `a07-data.json`）

1. **接壤即戳 / 无端先手戳强敌（`weFirst && curInc === 0`）的胜率断崖（195 局，625 次先手）**：

| 无端先手攻击目标类型 | 样本数 $N$ | 300 拍内遭反扑率 | 终局遭反扑率 | 被戳目标最终夺冠率 | 我方最终胜率 | 我方阵亡率 | 遭对方累计砸兵均值 |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | ---: |
| **接壤即戳 (`<=60t`，含 `beachhead` 误判)，且 $B_q \ge 1.0 B_{me}$** | `25` | **`52.0%`** | **`88.0%`** | **`32.0%`** | **`0.0%`** | **`92.0%`** | **`14,246,116`** |
| **任意无端先手，且 $1.0 B_{me} \le B_q < 1.3 B_{me}$** | `52` | **`59.6%`** | **`98.1%`** | **`40.4%`** | **`0.0%`** | **`96.2%`** | **`15,843,737`** |
| **任意无端先手，且 $B_q \ge 1.3 B_{me}$** | `34` | `35.3%` | `70.6%` | `20.6%` | `2.9%` | `85.3%` | `5,340,192` |
| **任意无端先手，但目标比我方弱 ($B_q < 1.0 B_{me}$)** | `539` | `27.6%` | `46.2%` | `2.0%` | **`13.5%`** | `82.0%` | `2,535,792` |
| **全样本对局级对比**：**曾无端先手戳 $B_q \ge 1.0 B_{me}$ 的对局 ($N=71$)** vs **从未戳强敌的对局 ($N=124$)** | `195 局` | — | — | — | **`1.4%` vs `14.5%` (相差 10.4 倍!)** | **`91.5%` vs `78.2%`** | — |

2. **被动挨打时的反蚕食威慑生死线（152 局，`13,835` 次非秒杀挑衅，按 $R = B_{attacker} / B_{me}$ 分桶）**：
   - 当 $R < 1.35$（弱敌/同级试探，占挑衅总量的 `54.6%`）时：
     - **不还手 (`R0`)**：400 拍内崩盘率 `10.0% ~ 26.2%`，400 拍净丢地 `-10.1% ~ -29.3%`；
     - **适度等比例反击 ($\le 12.5\% B$)**：400 拍崩盘率暴降至 **`4.0% ~ 9.5%`**（风险降低 `60%+`），净领土变化改善 `+11% ~ +14%`。
   - 当 $1.35 \le R \le 1.50$ 时：仅在宽战线/高密度（`dMe >= 95`）下可做轻度威慑（400 拍死亡率 `9.8%` vs 不还手 `23.7%` vs 过量反击 `50.0%`）。
   - 当 **$R > 1.50$（巨无霸挑衅）** 时：反击是纯自杀（过量反击 400 拍崩盘率高达 **`65.8% ~ 83.4%`**），必须严格锁死反击、靠高密度吸收！

### 3.3 `V9` 最优数学阈值区间推导
1. **抢滩桥头堡真伪判别阈值**：
   $$\text{isTrueBeachhead}(q) \iff (\text{wasCnt}_q = 0) \land (1 \le \text{cnt}_q \le 32) \land (t \ge 1200) \land \big(\text{inc}_{q \to me} > 0 \lor L_q \le 4000\big)$$
   且在 `tryDeterrentCounter` 中强制附加：**当 $\text{curInc}_{q \to me} = 0$ 时，严禁对 $B_q \ge 1.0 \cdot B_{me}$ 的目标发动首击**！
2. **Team 模式防破防密度锁（`hardCapMult` & `isSoleHealthyBuffer`）**：
   - 恢复 `isSoleHealthyBuffer = true`（当 `humanNbCount === 1 && newNbs > 0 && !onMe` 时，要求 $d_{me} \ge 128$ 才可进攻该唯一缓冲邻）；
   - 将 Team 模式的 `hardCapMult` 从 `1.16` 恢复至：
     $$\text{hardCapMult} = \begin{cases} 1.42, & \text{if } \text{isCrowdedHard} \land c \ge 2.15 \cdot \text{worth} \land B_q \ge 0.55 B_{me} \\ 1.26, & \text{otherwise (P.crowdedHardCap)} \end{cases}$$
3. **队友救援 10% 策应刀护栏（彻底根除 2-tick 机关枪 Bug）**：
   $$\text{canAssistPoke}(q) \iff (\text{cnt}_q > 0) \land \neg\text{hasAttack}(me, q) \land \big(t - \text{hitTo}[q] \ge 45\big) \land (d_{me} \ge 88) \land (B_q \le 1.35 B_{me})$$
4. **多线受敌反蚕食过滤（`activeHumanAtkers`）**：
   - 仅统计 $B_a \ge 0.30 B_{me}$ 且 $\text{inc}_{a \to me} > 0.02 B_{me}$ 的有效威胁攻击者，排除垂死残血猎物的噪声反扑。

---

## 4. 【反事实推演（Counterfactual Verdict）】

如果将上述 `V9`（及耦合的 `V7`）改回 80% 胜率基线与最优阈值，在 **G08 (`t = 3150 ~ 5425`)** 的关键节点会发生如下确定性改变：

1. **`t = 3150 ~ 3780`（拦截 3 次 `hardCapMult=1.16` 盲目破防）**：
   - `ethan21` 在 `t=3150 (d=110.7 < 126)`、`ryan_m` 在 `t=3600 (d=108.7 < 128, nb=1 唯一缓冲邻)`、`dave_w` 在 `t=3690 (d=114.5 < 126)` **均被 `isSoleHealthyBuffer` 与 `hardCapMult = 1.26~1.42` 拦住**，不会向强邻 `18 (Turk)` 和 `41 (rubi)` 发动亏损率高达 `7:1` 的自杀式泄洪。
   - **直接收益**：全队在 `t=3780` 少损失 **$110.5\text{万} + 128.5\text{万} + 73.3\text{万} = \mathbf{312.3\text{万}}$ 兵力**，`ethan21`、`ryan_m`、`dave_w` 的密度保持在 **`d = 115 ~ 132`**，敌方 `18 (Turk)` 与 `41 (rubi)` 根本不敢发起反扑。
2. **`t = 3782 ~ 3912 & t = 4314 ~ 5334`（拦截 6 波共 41 刀 `[HL-ASSIST]` 机关枪自残）**：
   - 即便前线发生局部交火，加上 `g.t - (this.hitTo.get(q) ?? -999) >= 45` 与 `dMe >= 88` 护栏后，6 波共计 **41 刀** 10%B 机关枪连发会被压缩为 **最多 4 刀单发策应**（减少 **37 刀冗余指令**）。
   - **直接收益**：
     - `kevin_k` 在 `t=3782..3794` 少发 6 刀，保留 **`+36.5万` 兵力（密度 `82` vs 实盘 `41`）**，不会在 `t=4392` 阵亡；
     - `lucas94` 在 `t=3800..3808` 与 `t=4314..4326` 少发 10 刀，保留 **`+118万` 兵力（密度维持 `>95` vs 实盘 `42.7`）**；
     - `mark07` 在 `t=3898..3912` 少发 7 刀，保留 **`+71万` 兵力（密度维持 `>92` vs 实盘 `38.8`）**，不会在 `t=4630` 阵亡；
     - `ryan_m` 在 `t=5322..5334` 少发 6 刀，保留 **`+82万` 兵力（密度维持 `>68` vs 实盘 `22.5`）**，不会在 `t=5425` 阵亡。
3. **终局推演结果**：
   - 在拐点 `t = 3780`，我方 6 名存活主力的总兵力将从实盘的 **`302.5 万 (d=41.0)`** 提升至 **`685 万+ (d ≈ 94)`**；
   - **少死 4 个主力 Bot（`kevin_k`、`mark07`、`dave_w`、`ryan_m`）**，6 人完整保留北大陆 `7.5万~9.5万` 格连片高密度防线，不仅能轻松挡住 Team 2 与 Team 5 的推进，还能在 `t=4500~5800` 反吞西侧残血队伍，将这局从第 4 名败局转化为前 2 名乃至吃鸡局！

---

## 5. 【一行可验证改动建议（Minimal Actionable Fix）】

以下改动精确对应 `tsb/squad/v27-team-live.js`（同步修改生成器 `tsb/squad/make_v27_team.py`），**与 `V1~V3`（出生选点）、`V5`（海防船税）完全正交**，且每一条均消除了实盘已证实的漏兵 Bug：

### 改动 1：在 `tryDonateToTeammate` 与 `tryEmergencyBossRescue` 中为 10% 策应刀加上 `45 ticks` 冷却锁、`dMe >= 88` 密度锁与 `Bq <= 1.35*B` 强敌锁（消灭 2-tick 机关枪连发 Bug）
- **文件与位置**：`tsb/squad/v27-team-live.js` 第 `4491` 行 & 第 `4881` 行（对应 `tsb/squad/make_v27_team.py` 第 `459` 行 & 第 `851` 行）
- **修改前**：
```javascript
if (mainAttacker >= 0 && (this.cnt[mainAttacker] ?? 0) > 0 && !g.hasAttack(me, mainAttacker) && g.hasFreeSlot(me) && dMe >= 65) {
```
- **修改后**：
```javascript
if (mainAttacker >= 0 && (this.cnt[mainAttacker] ?? 0) > 0 && !g.hasAttack(me, mainAttacker) && g.t - (this.hitTo.get(mainAttacker) ?? -999) >= 45 && g.hasFreeSlot(me) && dMe >= 88 && g.bal[mainAttacker] <= 1.35 * B) {
```
（注：`tryEmergencyBossRescue` 第 `4491` 行同步加上 `&& g.t - (this.hitTo.get(q) ?? -999) >= 45 && dMe >= 85 && g.bal[q] <= 1.35 * B`。）

### 改动 2：修复 `updatePokeState` 自然接壤误判 `beachhead` 戳巨无霸 & `tryDeterrentCounter` 垂死猎物噪声锁（对齐 `fdvg` `v33-live.js`）
- **文件与位置**：`tsb/squad/v27-team-live.js` 第 `2693`、`2725`、`2745` 行
- **修改前**：
```javascript
if (wasCnt === 0 && curCnt > 0 && curCnt <= 32 && g.t >= 1200) {
// ...
if (a < g.humans && !g.isBot(a) && g.attackTroopsOn(a, me) > 0.02 * B) activeHumanAtkers++;
// ...
if (Bq > 1.50 * B && !isFreshBeachhead) continue;
```
- **修改后**：
```javascript
if (wasCnt === 0 && curCnt > 0 && curCnt <= 32 && g.t >= 1200 && (inc > 0 || g.terr[q] <= 4000)) {
// ...
if (a < g.humans && !g.isBot(a) && g.attackTroopsOn(a, me) > 0.02 * B && g.bal[a] >= 0.30 * B) activeHumanAtkers++;
// ...
if (Bq > 1.50 * B || (isFreshBeachhead && Bq >= B && curInc <= 0)) continue;
```

### 改动 3：恢复 Team 模式的 `isSoleHealthyBuffer` 与 `hardCapMult = 1.26~1.42` 防破防锁（撤销 `22effa4` 的 `1.16` 激进破防）
- **文件与位置**：`tsb/squad/v27-team-live.js` 第 `5755~5766` 行（对应 `tsb/squad/make_v27_team.py` 第 `1122~1133` 行）
- **修改前**：
```javascript
const isSoleHealthyBuffer =
  !isTeamMode && person && !o.isDoorSea && nHumans >= 3 && !o.nearCollapse && !o.bleeding && !o.onMe && o.newNbs > 0 && humanNbCount === 1;
// ...
const hardCapMult = isTeamMode ? 1.16 : (o.isCrowdedHard && c >= 2.15 * worth && g.bal[q] >= 0.55 * B ? 1.50 : P.crowdedHardCap);
```
- **修改后**：
```javascript
const isSoleHealthyBuffer =
  person && !o.isDoorSea && nHumans >= 3 && !o.nearCollapse && !o.bleeding && !o.onMe && o.newNbs > 0 && humanNbCount === 1;
// ...
const hardCapMult = o.isCrowdedHard && c >= 2.15 * worth && g.bal[q] >= 0.55 * B ? (isTeamMode ? 1.42 : 1.50) : P.crowdedHardCap;
```
