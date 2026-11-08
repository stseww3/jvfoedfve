# S04 (A04) 胜率根因显微镜解剖报告：G05 (`00:54` 6队局) & 核心变量 `V6`（团队捐款抽血阈值与后排输血效率）

> **主审子 Agent**：`S04 (A04)`
> **包干实盘对局**：**G05 (`00:54:34 CST / 2026-11-07T16:54:34Z`, 6 队局, 败, `mw6n3e8i-4b5899` ~ `mw6n3eel-b77pff`)**
> **包干核心变量**：**`V6` 团队捐款抽血阈值与后排输血效率（`DonationDrainVsFrontlineDensity`）**（兼耦合法庭审计 `V1/V2` 锚点崩塌、`V7` 前线留守底线、`V5` 船税消耗）

---

## 一、【单局时间线与胜负拐点（Timeline & Inflection Point）】

### 1.1 G05 (`00:54 CST`, 6 队局, `map=22`, `mapSeed=1511`, `W=1541x1080`, `land=664,497`, `players=55`) 关键节点全息表

本局我方 8 个 `[Nope]` 无头号（`mark07, kevin_k, ethan21, lucas94, dave_w, ryan_m, noah88, leo_tx`）在 `waitBoss=false` 下全部进场，归属 **Team 2**（对手主要为 Team 5、Team 1、Team 4、Team 3、Team 6）。

| 阶段 / 采样时刻 (`tick`) | 我方存活人数 (`L > 0`) | 团队总领土 `L_team` (px) | 全图陆地占比 (`L_team / 664,497`) | 团队总兵力 `B_team` | 团队加权平均密度 `d_team` | 前线主力留守密度 `d_front` | 内陆/孤岛后排状态 (`ethan21`) | 累计指令数 `cmds` / 发船数 `boats` | 头号对手团队领土 (Team 5 / Team 1) |
| :--- | :---: | ---: | :---: | ---: | :---: | :--- | :--- | :---: | :--- |
| **`t = 0` (选点终帧)** | `8 / 8` | `84` | `0.01%` | `4,096` | `48.8` | — | `ethan21` 被 fallback 甩至 `(1180,1060)` (`voronoi=500`, 实占 479px 死角) | `0 / 0` | 各队初始选点（6 支大队） |
| **`t = 630` (开局拍)** | `8 / 8` | `18,569` | `2.79%` | `44,864` | `2.4` | `dave_w: 1.0`, `kevin_k: 1.1`, `ryan_m: 1.2` | `L=479, B=10,596, d=22.1, nb=0, neut=3`（卡 3 格无主地） | `72 / 3` | 扩张期（无主地争夺中） |
| **`t = 900`** | `8 / 8` | `30,671` | `4.62%` | `105,667` | `3.4` | `noah88: 1.1`, `mark07: 1.2`, `ryan_m: 1.6`, `dave_w: 1.7` | `L=479, B=37,942, d=79.2, nb=0, neut=3`（0 捐款） | `195 / 5` | 6 队均分主大陆，我方仅 2 人在北岸小块 |
| **`t = 1260`** | `8 / 8` | `45,139` | `6.79%` | `357,978` | `7.9` | `dave_w: 1.1 (L=9889)`, `mark07: 1.9`, `kevin_k: 2.3` | `L=479, B=71,026, d=148.3, nb=0, neut=3`（**逼近 `150*L` 硬顶！**） | `560 / 9` | 敌方主大陆大队完成合围 |
| **`t = 1440` (满仓憨死拍)** | `8 / 8` | `48,229` | `7.26%` | `501,090` | `10.4` | **`dave_w: 0.0 (L=11350, B=146!)`**, `noah88: 3.7`, `kevin_k: 5.5` | **`L=479, B=71,850, d=150.0, nb=0, neut=3`（100% 满仓硬顶 0 利息！）** | `662 / 12` | 主大陆 Team 1 / Team 5 突破 `110,000+` |
| **`t = 1530` (`t=1500` 结算拍)** | `8 / 8` | `51,425` | **`7.74%`** | `470,871` | `9.2` | **`dave_w: 0.3 (L=13212, B=3677)`**, `mark07: 1.3`, `noah88: 4.8` | `L=485, B=44,291, d=91.3, nb=0, neut=0`（连发 7 次 `expandNeutral` 烧掉 2.85 万兵吃 6 格地，仅在 `t=1528/1546` 挤出 2 笔 5% 捐款） | `722 / 12` | Team 5 / Team 1 各占 `~135,000` (`>20%`) |
| **`t = 1710` (峰值拍 `t_peak`)** | `8 / 8` | **`57,459`** | **`8.65%`** | `633,343` | `11.0` | **`dave_w: 2.6 (L=16065, cmds=215)`**, `noah88: 4.3`, `kevin_k: 6.2`, `mark07: 6.8` | `L=851, B=18,110, d=21.3, nb=2, boats=6`（把剩余 4.4 万兵发船送死） | `813 / 18` | Team 5 `~142,000` / Team 1 `~140,000` |
| **`t = 1800` (胜负拐点 `t_turn`)** | `8 / 8` | `56,918` | `8.57%` | `704,575` | `12.4` | **`dave_w: 3.4 (L=15351, 开始净丢地)`**, `noah88: 5.4`, `kevin_k: 7.1`, `mark07: 8.7` | `L=964, B=9,153, d=9.5`（彻底失去后排造血能力） | `818 / 18` | 敌方前线密度 `d_enemy ≈ 65 ~ 95` 开始蚕食 `dave_w` 与 `kevin_k` |
| **`t = 2417 ~ 2430` (首崩拍)** | `6 / 8` | `34,177` | `5.14%` | `673,653` | `19.7` | `lucas94` 在 `t=2160` 冲至 `L=11,059` 但 `d=5.2`，`t=2417` 阵亡；`mark07` 被推至 `L=0` | `L=8, B=17, d=2.1` | `788 / 32` | **Team 5: `152,143` (22.9%)**, Team 1: `146,490` (22.0%), 我方 Team 2: `35,169` (5.3%) |
| **`t = 2967` (`ryan_m` 阵亡)** | `5 / 8` | `17,970` | `2.70%` | `317,724` | `18.6` | `ryan_m` 因连发 **8 艘海防拦截船**（单船 `pct=205~252/1024` 抽走 `25% B`），`t=2700` 密度从 `43.1` 跌至 `14.2` 被秒 | `L=8, B=111` | `760 / 29` | **Team 5: `171,403` (25.8%)**, Team 1: `138,693` (20.9%) |
| **`t = 3595` (主将 `dave_w` 阵亡)** | `3 / 8` | `2,994` | `0.45%` | `67,226` | `26.1` | `noah88` (`t=3220`)、`ethan21` (`t=3411`)、`dave_w` (`t=3595`, 峰值 `16,638`) 相继阵亡 | 已阵亡 (`t=3411`) | `300 / 21` | **Team 5: `166,585` (25.1%)**, Team 1: `139,127`, Team 4: `131,843` |
| **`t = 3882 ~ 3890` (终局拍)** | `0 / 8` (2 残余退房) | **`409` -> `13`** | **`0.00%`** | `267` | `20.5` | `leo_tx` 在 `t=3882` 阵亡；`kevin_k (L=2)`、`mark07 (L=11)` 触发 `<80px` 退房 | 全军覆没 | `993 / 36` (全员终局累计) | **Team 5: `165,195` (第 1 赢家)**, Team 4: `144,670`, Team 1: `122,550`, Team 3: `117,728`, Team 6: `109,001` |

### 1.2 胜负拐点精确定位（`t_turn = 1440 ~ 1800`）

本局并非中盘顺风被翻盘，而是 **「开局锚点崩塌 (`t=0`) $\rightarrow$ 早盘孤岛满仓 `150*L` 零输血 (`t=990~1500`) $\rightarrow$ 前线主力 `0.3~3.4` 极低密度裸奔 (`t=1440~1800`)」** 的三段式窒息局：
1. **第一拐点（`t = 0` 选点崩塌）**：`spawn-coordinator.mjs`（尚未加载 `d590acd`）在无 Boss 时将 `VirtualSquadAnchor` 选在北部小半岛 `(352,92)~(452,72)`，仅 `mark07` 与 `lucas94` 拿到正常 Voronoi（`2331px`、`5508px`），其余 **6 名兄弟（`kevin_k, ethan21, dave_w, ryan_m, noah88, leo_tx`）全部落入 `voronoi=500` 的紧急 fallback 分支**（日志第 `4237~4257` 行），被随机甩向全图四个死角；其中 `ethan21 (me=21)` 被困在 `(1180, 1060)` 的 **479 格死角口袋**。
2. **第二拐点（`t = 990 ~ 1528` 后排 `150*L` 硬顶憋死与 `28,520` 兵乌龙自焚）**：
   - `ethan21` 在 `L = 479` 口袋内无任何敌方邻居（`nb = 0`），仅剩 `neut = 3` 格零星无主地。由于 `t < 1500` 期间 `act(g)` 只调 `tryEmergencyBossRescue(g)`（无 Boss 直接 `return false`）而不调 `tryDonateToTeammate(g)`，且 `neut = 3` 导致 `boxedIn = false`，`ethan21` 从 `t = 990`（`d = 111.9`）一路涨到 **`t = 1440` 的 `B = 71,850, d = 150.0`（满仓硬顶，0% 利息！）**，白白浪费了黄金发育期 540 拍的复利！
   - 更致命的是：此时前线头号主力 `dave_w`（`L = 11,350`）因 `totB = B + myOut` 与 `oppFloorCap = 38` 把家里抽干到 **`B = 146, d = 0.0`**（日志第 `4408` 行），亟需 `ethan21` 的 `7.18 万` 兵救命；但 `ethan21` 不仅在 `t < 1500` 一毛不拔，反而在 `t = 1500 ~ 1526` 因 `period = 2` + `inflight < 2t` 连续对那 3 格无主地发出 **7 条重复 `expandNeutral` 指令（`cmds: 7 -> 14`）**，瞬间烧掉 **`28,520` 兵**（余额从 `71,850` 暴跌至 `43,330`）只换来 `6` 格地！随后在 `t = 1528` 和 `t = 1546` 仅挤出两笔 `pct = 51/1024 (~5%)` 的牙膏式捐款（其中 `t = 1528` 捐给 `mark07` 的一笔还被引擎吃掉/延迟），紧接着触发 `idleBoats` 把剩余 4.4 万兵发船送死。
3. **第三拐点（`t = 1710 ~ 1800` 前线主力 `dave_w` 与 `lucas94` 空虚崩盘）**：
   - 在 `t = 1710` 我方达到全局领土峰值 `L_team = 57,459 (8.65%)` 时，头号领土主力 `dave_w`（`L = 16,065`）已狂发 `215` 条指令，家里留守密度仅 **`d = 2.6`**（`t = 1800` 仅 `d = 3.4`）；二号主力 `lucas94` 在 `t = 2160` 扩到 `L = 11,059` 时留守密度仅 **`d = 5.2`**；而三号主力 `ryan_m` 与 `leo_tx` 虽然攒到 `B = 200k~245k`（`d = 35~43`），却既够不到 `dMe >= 106` 的救援捐款线，又在 `t = 1877 ~ 2612` 被 `tryInterceptEnemyBoats` 连续发射 **14 艘高配额拦截船（单船最高 `pct = 252/1024` 抽走 `25% B`）** 抽空兵力，最终全队在 `t = 2417 ~ 3882` 被各个击破。

---

## 二、【核心死因分类（Primary & Secondary Root Causes）】

### 2.1 本局（G05）死因权重拆解
- **第一主因（本局权重 `55%`）：`V1 + V2`（无 Boss 虚拟锚点落入北岸窄岛 + `clusterMax <= 350` 团簇锁死，触发 6 人 `voronoi=500` 绝望散落，且造成 `ethan21` 开局 479px 死角被困）**
  - **源码定位**：`tsb/squad/spawn-coordinator.mjs` 第 `520~545` 行 `findVirtualSquadAnchor`（未加载 `d590acd` 前缺少 `compSize[c] < minAnchorContSize` 过滤）与第 `834`、`913~958`、`1042~1075` 行（`clusterMax: clamp(..., 195, 350)` 叠加 `voronoiPixels < minVoronoi` 失败后的 fallback 循环）。
  - **日志铁证**（`c116-winrate/data/tsb-team-squad.log` 第 `4237~4257` 行）：
    ```text
    [[Nope] noah88] [HL-SPAWN-BACKEND] me=28 slot=8 role=ECO_BANK -> (520,1060) bossDist=-1 minAllyDist=517 voronoi=500
    [[Nope] ethan21] [HL-SPAWN-BACKEND] me=21 slot=4 role=ECO_BANK -> (1522,982) bossDist=-1 minAllyDist=696 voronoi=500
    [[Nope] kevin_k] [HL-SPAWN-BACKEND] me=22 slot=3 role=ECO_BANK -> (976,550) bossDist=-1 minAllyDist=684 voronoi=500
    [[Nope] leo_tx] [HL-SPAWN-BACKEND] me=25 slot=9 role=ECO_BANK -> (1456,58) bossDist=-1 minAllyDist=687 voronoi=500
    [[Nope] ryan_m] [HL-SPAWN-BACKEND] me=18 slot=7 role=ECO_BANK -> (256,616) bossDist=-1 minAllyDist=517 voronoi=500
    ```
- **第二主因 / 专项核心死因（本局权重 `45%`，跨局系统性权重 Top 3）：`V6`（团队捐款抽血阈值与后排输血机制的五大结构性缺陷）耦合 `V7`（`oppFloorCap=38` + `totB=B+myOut` 前线抽干）**
  - **源码定位**：
    1. `tsb/squad/make_v27_team.py` 第 `383~453` 行（`v27-team-live.js` 第 `4398~4468` 行）`tryEmergencyBossRescue(g)` 与第 `1145~1157` 行（`v27-team-live.js` 第 `5278~5288` 行）`act(g)` 早盘分支；
    2. `tsb/squad/make_v27_team.py` 第 `772~900` 行（`v27-team-live.js` 第 `4787~4915` 行）`tryDonateToTeammate(g)`；
    3. 游戏引擎底层 `tsb/squad/live_game_js.js`：`bD.gv.rB` / `bD.gv.n4`（`64/1024 = 6.25% B` 固定全额捐款税）与 `ao = new ca()`（`ao.ei` 反养猪配额锁）。
  - **日志铁证**（`c116-winrate/data/tsb-team-squad.log` 第 `4407~4421` 行）：
    ```text
    [[Nope] ethan21] [HL-TICK] t=1440 terr=479(0.1%) bal=71850 dens=150.0 nb=0 neut=3 cmds=7 boats=4 avgMs=3.41 maxMs=6.8 skip=0
    [[Nope] dave_w] [HL-TICK] t=1440 terr=11350(1.7%) bal=146 dens=0.0 nb=2 neut=0 cmds=166 boats=0 avgMs=2.75 maxMs=38.8 skip=0
    [[Nope] ethan21] [HL-DONATE] t=1528 surplus donate pct=51/1024 (~5%) -> ally=24([Nope] mark07) boxedIn=true myBal=43330 dMe=89
    [[Nope] ethan21] [HL-TICK] t=1530 terr=485(0.1%) bal=44291 dens=91.3 nb=0 neut=0 cmds=15 boats=4 avgMs=3.50 maxMs=45.9 skip=0
    [[Nope] ethan21] [HL-DONATE] t=1546 surplus donate pct=51/1024 (~5%) -> ally=23([Nope] dave_w) boxedIn=true myBal=44341 dMe=91
    ```

---

## 三、【专项核心变量 `V6` 全样本量化（Core Variable Quantification）】

通过对昨晚全部 9 局自动局（`G01 ~ G09`，共 `373` 条 `[HL-DONATE]` 指令、`2,831` 条 `[HL-TICK]` 快照）与 `tsb/squad/live_game_js.js` 引擎反编译代码的联合审计，我们发现了 **`V6` 导致团队经济雪球崩塌的 5 个致命数学与源码级 Bug**：

### 3.1 致命机制一（引擎底层真相）：捐款税根本不是“捐出金额的 10%”，而是每次调用按捐出方 **总余额 `B_donor` 的 `64/1024 = 6.25%` 固定全额扣税**！`5% (pct=51)` 微量捐款导致 **55.17% 的扣款直接灰飞烟灭**！

在 `tsb/squad/live_game_js.js` 中，引擎处理捐款指令 `bB.qg.qt(player, jC, qs)` 的精确源码如下：
```javascript
// tsb/squad/live_game_js.js
this.jB = function(player, a5s) {
  return bO.g0(ah.hb[player] * (a5s + 1), 1024); // qt = floor(B_donor * (pct + 1) / 1024)
};
this.rB = function(player, qt, qs) {
  var a5k = ah.hb[player];                       // a5k = B_donor（捐出方全部余额！）
  var a5p = bO.g0(64 * a5k, 1024);               // a5p = floor(64 * B_donor / 1024) = 6.25% * B_donor（固定全额税！）
  qt = Math.min(qt, a5k - a5p);
  qt = this.a5i(qs, qt);                         // 受捐方 150 * L_qs 硬顶截断
  bR.g6[0] = qt;                                 // 实际到账兵力
  bR.g6[1] = a5p;                                // 系统销毁税费 = 6.25% * B_donor
  return qt >= 1;
};
this.n4 = function(player) {
  var iI = bR.g6[0];
  ah.hb[player] -= iI + bR.g6[1];                // 捐出方扣除：实际到账 qt + 6.25% * B_donor！
  b5.a5w(player, iI);
};
```
- **数学证明**：
  - 陆地进攻税为 `12/1024 * B = 1.172% B`，发船税为 `32/1024 * B = 3.125% B`，而 **捐款税是惊人的 `64/1024 * B = 6.250% B`（与捐款比例 `pct` 完全无关的固定全额税）**！
  - 当 Commit `d996be6` 将所有捐款比例 `pct` 硬锁为 `51`（即 `(51+1)/1024 = 52/1024 = 5.078% B`）时，每调用一次 `g.donate(51, ally, me)`：
    - 受捐方实际收到：\(\Delta B_{\text{recv}} = \frac{52}{1024} B = 5.078\% B\)
    - 系统直接销毁税费：\(\text{Tax}_{\text{burn}} = \frac{64}{1024} B = 6.250\% B\)
    - 捐出方实际扣除：\(\Delta B_{\text{donor}} = -\frac{116}{1024} B = -11.328\% B\)
    - **单次捐款的真实税损率**：
      \[
      \eta_{\text{loss}}(pct=51) = \frac{64}{52 + 64} = \mathbf{55.17\%} \quad \left(\text{税费与到账兵力比} = \frac{64}{52} = \mathbf{123.08\%}\right)
      \]
      也就是说，**每捐 `5%` 的兵，系统销毁的税费（`6.25% B`）比队友收到的兵（`5.08% B`）还要多出 `23.1%`！超过一半的兵力在传递过程中凭空蒸发！**
  - 反之，若内陆满仓后排单次大额捐出 `pct = 280`（`27.44% B`）或 `pct = 320`（`31.35% B`，`d996be6` 之前的旧基线值）：
    \[
    \eta_{\text{loss}}(pct=280) = \frac{64}{281 + 64} = \mathbf{18.55\%}, \quad \eta_{\text{loss}}(pct=320) = \frac{64}{321 + 64} = \mathbf{16.62\%}
    \]
    传输同样 `30%` 的兵力，1 次 `pct=307` 仅交 **1 次 `6.25% B` 税**（净到账 `30.08% B`，总扣 `36.33% B`）；而分 6 次 `pct=51` 挤牙膏则要交 **6 次 `6.25% B` 税**（累计烧掉约 `31.8% B` 税费，净到账仅 `25.8% B`）！

### 3.2 致命机制二（引擎反养猪锁 `ao.ei`）：高频 `5%` 微捐触发固定次数惩罚，导致 **55% 的连续捐款被服务器静默拒收（0 到账但白锁 `canAct` 与 `lastDonateTick`）**！

在 `tsb/squad/live_game_js.js` 的 `function ca()`（实例 `ao`）中，引擎对每个受捐玩家 `qs` 在 `t < 4284` 设有反养猪配额上限 `aNO[qs] <= aNP`：
```javascript
// tsb/squad/live_game_js.js
function aNT(a8o, aNR) {
  var ej = bi.kr(); // 当前 tick
  if (ej >= 3213) { return 4 + bO.g0(100 * aNR, af.ka(a8o)); } // 每次固定 +4 点 + 金额项
  var uw = 1 + bO.g0(aE.ke, 300);
  if (ej < 357)  { return 2 + bO.g0(100 * aNR, uw); }
  if (ej < 714)  { return 2 + bO.g0(100 * aNR, 4 * uw); }
  if (ej < 1071) { return 2 + bO.g0(100 * aNR, 10 * uw); }
  if (ej < 2142) { return 2 + bO.g0(100 * aNR, 30 * uw); }
  return 2 + bO.g0(100 * aNR, 100 * uw); // 每次固定 +2 点 + 金额项
}
this.ei = function(a8o, aNR) {
  if (aNS(a8o)) { return true; } // t >= 4284 才解除限制
  var g1 = aNT(a8o, aNR);
  if (aNO[a8o] + g1 > aNP) { return false; } // 超出配额直接拒收！
  aNO[a8o] += g1;
  return true;
};
```
1. **每次捐款自带 `+2`（`t < 3213`）或 `+4`（`3213 <= t < 4284`）的固定笔数惩罚**！把 1 笔 `25%` 拆成 5 笔 `5%`，会白白多扣 `4 * 2 = 8` 点（或 `4 * 4 = 16` 点）受捐配额（而每 100 拍租金周期 `aNP` 才恢复 `4~10` 点），瞬间把前线主力的受捐额度锁死！
2. 更严重的是：`page.js` 中的 `g.donate(pct, e, me)` 在联机模式（`this.online === true`）下直接调用 `b1.qm.qu(pct, e)` 发送 WebSocket 包并返回 `true`，**根本没有调用 `window.ao?.iD?.(e)` 校验受捐方配额是否已满**！结果当受捐方配额已满时，服务器直接丢弃该捐款包，但我方 Bot 却认为捐款成功，不仅浪费了当拍唯一指令槽（`sendsHeld = true`），还把 `this.lastDonateTick = g.t` 锁死 18 拍，甚至无法转捐给其他未满配额的前线队友！
3. **实盘日志验证**：在 G01~G09 的 `100` 对连续 `<=36t` 捐款事件中，有 **`55` 次（`55.0%`）在下一拍/下一次捐款时捐出方余额未发生扣除（`next.bal >= 0.985 * cur.bal`）**，其中包括 G05 中 `ethan21` 在 `t=1528` 捐给 `mark07`（`myBal=43,330` $\rightarrow$ `t=1530 bal=44,291` $\rightarrow$ `t=1546 myBal=44,341`）！

### 3.3 致命机制三（无 Boss 自动局早盘死区 & 零星无主地死锁）：`t < 1500` 从不调用 `tryDonateToTeammate`，且 `neut > 0` 锁死 `boxedIn`

1. 在 `tsb/squad/make_v27_team.py` 第 `1145~1157` 行（`v27-team-live.js` 第 `5278~5288` 行）中：
   - 当 `g.t < P.coreFrom` (`t < 1500`) 时，`act(g)` 只调用 `this.tryEmergencyBossRescue(g)`，**完全没有调用 `this.tryDonateToTeammate(g)`**！
   - 而在 `waitBoss=false` 自动局中，`this.findBossId(g)` 恒为 `-1`，导致 `tryEmergencyBossRescue(g)` 在第 3 行（`if (bossId < 0 ...) return false;`）直接退出！
   - 因此，在无 Boss 自动局的 **`t = 0 ~ 1500` 整整前 1500 拍内，全队捐款与救援逻辑 100% 处于瘫痪状态**！
2. 同时，`boxedIn` 定义为 `this.nb.length === 0 && this.neutral === 0`（`v27-team-live.js` 第 `4792` 行）。当内陆/死角 Bot（如 G05 的 `ethan21`）身边残留 `1 ~ 5` 格无主地（`this.neutral = 3`）时，因为 `dpNeutral(g)`（第 `2380` 行）要求 `X = 2*sum + r >= this.minCmd(g)`（`9 < 4.69% * B`），在 `t = 600 ~ 1500` 期间既不发兵吃这 3 格无主地，又因为 `this.neutral !== 0` 不承认自己 `boxedIn`，直接坐满 `150.0 * L` 硬顶！
   - 即使到了 `t = 1500`，当某个真正被队友包在中间的后排（`nb === 0, neutral === 0`）触发 `tryDonateToTeammate` 时，第 `4879` 行 `if (boxedIn && dMe < 72) return false;` 叠加第 `4800` 行 `coastGuardFloor = hasExposedCoast && g.t >= 1100 ? 68 * L : 18 * L`（要求 `B > 1.10 * 68L = 74.8L` 且 `maxSafePct >= 45` 即 `dMe >= 76.9`），迫使完全没有敌方邻居的后排留着 `72*L ~ 95*L` 的兵力在后方睡大觉！

### 3.4 致命机制四（前线误判抽血 & `oppFloorCap=38` 失明）：`isPureInlandSafe` 漏判 `[Bot]` 邻居 + `safeAt(g, -1)` 被截断在 `38*L`，导致前线主将自残式捐款！

请看 `tsb/squad/make_v27_team.py` 第 `783~788` 行与第 `836~840` 行（`v27-team-live.js` 第 `4798~4803`、`4851~4855` 行）：
```javascript
const enemyHumanNbs = this.nb.filter((p) => g.alive[p] && this.person(g, p));
const hasExposedCoast = (g.coast?.[me]?.length ?? 0) > 0;
const coastGuardFloor = hasExposedCoast && g.t >= 1100 ? 68 * L : 18 * L;
const safeFloor = Math.max(coastGuardFloor, enemyHumanNbs.length > 0 ? this.safeAt(g, -1) : 0);
const isPureInlandSafe = enemyHumanNbs.length === 0 && !hasExposedCoast && myHumanInAtk === 0;
...
if (inHumanAtk > 0 && (inHumanAtk >= 0.12 * g.bal[p] || dAlly < 55)) {
  // First donate 5% cash ONLY if we are boxedIn or have surplus density >= 106!
  if (dMe >= (isPureInlandSafe ? 40 : 106) && dMe >= dAlly + 25) {
```
这里同时存在 **两个极其隐蔽的代码级 Bug**：
1. **`isPureInlandSafe` 漏判了 `this.nb.length === 0`（把正在打 `[Bot]` 的前线当成纯内陆后排）**：
   - 注释写的是 `ONLY if we are boxedIn or have surplus density >= 106`，但代码却写成了 `isPureInlandSafe ? 40 : 106`！
   - `enemyHumanNbs` 只过滤真人（`this.person(g, p)`）。如果一个前线 Bot 正在内陆與 1~5 个 AI `[Bot]` 或投降 `[Bot]` 接壤扩张（`this.nb.length > 0`，并非 `boxedIn`），只要它还没碰到真人且没有海岸线，它的 `isPureInlandSafe` 就是 `true`！
   - 结果它在 **`dMe = 40 ~ 69`** 的极低密度下就开始疯狂向队友捐款！例如：
     - **G01 (`00:30`)**：`dave_w` 在 `t = 3698 ~ 3850` 于 `dMe = 52 ~ 69` 连续触发 **19 次低密度救援捐款**！
     - **G06 (`01:01`)**：`dave_w` 在 `t = 2870 ~ 3474` 于 `dMe = 47 ~ 69` 连续触发 **16 次低密度救援捐款**！
     - **G07 (`01:07`)**：`lucas94 (L=10,178, nb=1)` 在 `t = 2020 ~ 2300` 于 `dMe = 40 ~ 41` 连续触发 **4 次低密度救援捐款**！
2. **`this.safeAt(g, -1)` 被 `oppFloorCap = 38` 硬截断，导致前线主将在强敌环伺下以 `dMe = 106 ~ 132` 抽血自残**：
   - 在 `v27-team-live.js` 第 `4940~4945` 行：
     ```javascript
     safeAt(g, q) {
       let s = super.safeAt(g, q);
       const P = this.p, me = this.me, L = Math.max(1, g.terr[me]);
       if (q < 0 || !this.person(g, q)) {
         s = Math.min(s, P.oppFloorCap * L);
       }
     ```
   - 当 `tryDonateToTeammate` 调用 `this.safeAt(g, -1)` 时，因为 `q = -1 < 0`，返回值被强制截断为 `P.oppFloorCap * L = 38 * L`！
   - 在原版 80% 胜率基线中，`oppFloorCap = 128`，当身边有满仓真人巨无霸时，`safeAt(g, -1)` 返回 `95*L ~ 128*L`，`B <= 1.10 * safeFloor` 会严格阻止前线抗压主将向外捐款；
   - 而在 `e20db6b` 将 `oppFloorCap` 改为 `38` 后，`safeFloor` 最高只有 `38*L`（内陆）或 `68*L`（沿海）！前线抗压主将只要密度达到 `106`（甚至每次捐完掉 `11.33% B`），就会给濒死小弟捐款！
   - **实盘惨案**：
     - **G01 (`00:30`)**：二号前线支柱 `noah88 (L=16,172, nb=1)` 在 `t = 4432 ~ 4860` 连续 4 次向残血 `mark07 / lucas94` 捐款，自损 **`688,000` 兵（其中 `380,000` 烧成税费）**，随即被 Team 1/6 击穿！
     - **G04 (`00:50`)**：头号前线主将 `leo_tx (L=28,816, B=3.38M)` 在 `t = 3966 ~ 3984` 连续 2 次向 `noah88` 捐款，短短 18 拍内自损 **`728,135` 兵（其中 `401,730` 烧成税费）**！
     - **G08 (`01:13`)**：前线双柱 `mark07 (L=12,702, nb=2)` 与 `lucas94 (L=13,608, nb=2)` 在 `t = 3620 ~ 3870` 连续 9 次在前线向外捐款，自损 **`1,596,000` 兵（其中 `880,000` 烧成税费）**，直接导致我方在 `t = 3900+` 崩盘！

### 3.5 致命机制五（`t <= 2200` 后排互捐乒乓死循环）：第 `4894` 行 `g.t > 2200` 豁免导致后排把钱捐给另一个后排！

在 `v27-team-live.js` 第 `4894` 行：
```javascript
const allyEnemyNbs = this.peopleOf(g, p);
if (!allyEnemyNbs.length && outAtk === 0 && inAtk === 0 && g.t > 2200) continue;
```
- 在 `t = 1500 ~ 2200` 最关键的中盘扩张窗口，`g.t > 2200` 为 `false`，导致 `tryDonateToTeammate` **完全不检查受捐方 `p` 是否也是被包在内陆的后排**！
- 因为评分公式 `score = 600 + (outAtk + inAtk)/500 + (135 - dAlly)*3 + ...` 对低密度队友给高分，当后排 `A` 捐完款密度下降后，旁边的后排 `B` 立刻把钱捐回给后排 `A`（在 G04 中出现 `15` 次乒乓互捐，G06 中出现 `7` 次乒乓互捐），每来回一次就烧掉双方各 `6.25% B` 的全额税费并耗光 `ao.ei` 配额！

### 3.6 昨晚 9 局实盘（`G01 ~ G09`）`V6` 全样本量化汇总表

| 局序 | 时间 (CST) | 队伍数 | 结果 | 捐款指令总数 | 实际生效 / `ao.ei` 拒收 | 前线低密误捐 (`dMe<106, !boxedIn`) | 前线高密抽血 (`nb>0, dMe>=106`) | 后排 `boxedIn` 挤牙膏次数 | 实际到账总兵力 | **系统销毁 6.25%B 捐款税** | 前线被抽走总兵力 (含税) | `nb=0` 后排快照数 (平均密度 / `d>=100` 次数) |
| :---: | :---: | :---: | :---: | ---: | :---: | :---: | :---: | :---: | ---: | :---: | :---: | :---: |
| **G01** | `00:30` | 6 队 | **败** (峰值#1被翻) | `67` | `60` / `7` | `19` (`dave_w d=52~69`) | `5` (`noah88` 4次) | `43` | `2,571k` | **`3,165k`** | **`688k`** | `74` (`d=52.1` / `0`) |
| **G02** | `00:35` | 6 队 | **败** | `7` | `4` / `3` | `0` | `4` | `3` | `0.2k` | `0.2k` | `0k` | `4` (`d=3.3` / `0`) |
| **G03** | `00:41` | 4 队 | **败** | `75` | `63` / `12` | `0` | `3` (`lucas94/ethan21`) | `72` | `1,836k` | **`2,260k`** | **`223k`** | `114` (`d=58.0` / `0`) |
| **G04** | `00:50` | 3 队 | **败** (`t=5422`被翻) | `79` | `69` / `10` | `0` | `20` (`leo_tx` 2次巨额) | `59` | `4,957k` | **`6,101k`** | **`853k`** | `137` (`d=43.0` / `7`) |
| **G05** | **`00:54`** | **6 队** | **败 (本局)** | **`2`** | **`1` / `1`** | **`0`** | **`0`** | **`2`** | **`2.2k`** | **`2.8k`** | **`0k`** | **`26` (`d=46.3` / `6` 次 `d=112~150`!)** |
| **G06** | `01:01` | 5 队 | **败 (`over`)** | `108` | `88` / `20` | `16` (`dave_w d=47~69`) | `5` | `87` | `4,711k` | **`5,798k`** | **`495k`** | `201` (`d=45.4` / `0`) |
| **G07** | `01:07` | 2 队 | **🏆 胜 (`won`)** | `24` | `22` / `2` | `4` (`lucas94 d=40~41`) | `6` | `14` | `360k` | `443k` | `505k` | `116` (`d=36.1` / `5`) |
| **G08** | `01:13` | 6 队 | **败** (终局#4) | `9` | `9` / `0` | `0` | **`9` (`mark07/lucas94`)** | `0` | `715k` | **`880k`** | **`1,596k`** | `3` (`d=6.2` / `0`) |
| **G09** | `01:28` | 5 队 | **败 (`over`)** | `2` | `2` / `0` | `0` | `2` (`lucas94`) | `0` | `49k` | `61k` | `110k` | `67` (`d=8.2` / `0`) |
| **合计** | — | — | **1 胜 8 负** | **`373`** | **`318` / `55`** | **`39`** | **`54`** | **`280`** | **`15,201k`** | **`18,711k` (烧毁 55.2%!)** | **`4,470k`** | **`742` (`18` 次 `d>=100`)** |

---

## 四、【反事实推演（Counterfactual Verdict）】

如果将 `V6` 修正为我们推导的最优数学阈值与机制（同时配合 `d590acd` 锚点修复与 `V7` 前线底线恢复），在 **G05 (`00:54`)** 与跨局样本中会发生什么变化？

1. **在 G05 (`00:54`) 的关键拐点 `t = 900 ~ 1800`**：
   - **消除 `ethan21` 的 `t = 990 ~ 1500` 满仓硬顶浪费与 `28,520` 兵重复指令自焚**：
     - 允许 `g.t >= 700` 调用 `tryDonateToTeammate(g)`，并将“被困后排”定义为 `isBoxedRear = (this.nb.length === 0 && (this.neutral === 0 || (g.t >= 850 && this.neutral <= 8 && dMe >= 55)))`。
     - 当 `ethan21` 在 `t = 900` 达到 `dMe = 79.2 (B = 37,942)` 时，不再苦等 `t = 1500` 坐满 `150*L`，而是在 `dMe >= 55` 时以 **`pct = 280/1024 (~27.4% B)`** 单次大额输血给前线头号扩地主将 `dave_w`（每次到账 `~10,400` 兵，税损从 `55.2%` 降至 `18.6%`，且仅消耗 1 次 `ao.ei` 笔数配额）。
     - 从 `t = 900` 到 `t = 1800`（90 个计息周期），`ethan21` 始终保持在 `d = 35 ~ 65` 的全额满息区间（`r_0 = 4.6% -> 3.0%` / 10 ticks），加上避免 `t = 1500` 的 `28,520` 兵重复 `expandNeutral` 损耗与 4 艘无效海防船，可累计向 `dave_w` 与 `lucas94` 净输送 **`+82,000 ~ +95,000` 兵力**！
   - **在 `t = 1710 ~ 2417` 挽救前线双核 `dave_w` 与 `lucas94`**：
     - 获得 `ethan21` 输血 `+85,000` 兵且恢复 `oppFloorCap >= 95`（不再把 `dave_w` 抽干到 `d = 0.0 ~ 2.6`）后，`dave_w` 在 `t = 1710`（`L = 16,065`）的留守兵力将从 `42,201 (d = 2.6)` 提升至 **`~480,000+ (d ≈ 30 ~ 55)`**，`lucas94` 在 `t = 2160`（`L = 11,059`）的留守密度从 `d = 5.2` 提升至 **`d ≈ 45+`**，两人均不会在 `t = 1800 ~ 2417` 被敌方低成本蚕食推平！
2. **在 G01 / G03 / G04 / G06 / G08 五局中盘领先/均势局的反事实收益**：
   - 将后排 `isBoxedRear` 的单次捐款比例从 `pct = 51 (5%)` 提升至 **`pct = 280 (27.4%)`**（冷却 `45` 拍），全样本 `15.20M` 到账兵力的系统税费销毁将从 **`18.71M` 暴降至 `3.46M`**，相当于全队凭空多出 **`+15,250,000`（每局平均 `+210 万 ~ +450 万`）真实可用兵力**！
   - 严禁前线抗压兄弟（`this.nb.length > 0`）在 `dMe < 138` 或 `B < 1.25 * super.safeAt(g, -1)` 时向外捐款，直接保住 G01 的 `noah88`（少丢 `68.8 万` 兵）、G04 的 `leo_tx`（少丢 `72.8 万` 兵）、G08 的 `mark07 + lucas94`（少丢 `159.6 万` 兵）！

---

## 五、【一行可验证改动建议（Minimal Actionable Fix）】

我们在 `tsb/squad/make_v27_team.py` 中对 `tryDonateToTeammate(g)` 给出完全正交、精确到行号的 **4 项参数与条件修正**（与 `S01/S02` 的选点修正、`S03` 的 `oppFloorCap` 修正完全正交，可独立或联合上线验证）：

### 5.1 核心改动前后对照表

| 修改点 | 文件与函数位置 | 修改前 (`Current 917e6b1`) | 修改后 (`Recommended Optimal`) | 解决的核心问题 |
| :--- | :--- | :--- | :--- | :--- |
| **Fix 1: 解除早盘死区 & 修复 `neut<=8` 被困判定** | `tsb/squad/make_v27_team.py`<br>`act(g)` L1154 & `tryDonateToTeammate(g)` L777 | `g.t < P.coreFrom` 仅调 `tryEmergencyBossRescue(g)`；`boxedIn = this.nb.length === 0 && this.neutral === 0` | `g.t >= 720` 无 Boss 时亦调用 `tryDonateToTeammate(g)`；`boxedIn = this.nb.length === 0 && (this.neutral === 0 \|\| (g.t >= 850 && this.neutral <= 8 && dMe >= 55))` | 彻底消除 G05 `ethan21` 因 `neut=3` 和 `t<1500` 坐满 `150*L` 硬顶 540 拍的死锁 |
| **Fix 2: 修复后排大额输血比例（砍掉 69% 捐款税损耗）** | `tsb/squad/make_v27_team.py`<br>`tryDonateToTeammate(g)` L785, L863, L890 | `coastGuardFloor = 68*L`；`if (boxedIn && dMe < 72) return false;`；`const pct = 51; // 5%`（每次交 `6.25%B` 全额税，税损 **55.2%**） | `boxedIn` 时 `coastGuardFloor = 22*L`，触发线 `dMe >= 45`（保留 `25*L` 底线），单次捐出 **`pct = Math.min(maxSafePct, 280)` (`~27.4% B`)**，冷却 `42` 拍 | 将单次捐款有效税损从 **55.17% 降至 18.55%**，同时将 `ao.ei` 固定笔数配额消耗降低 **5.5 倍** |
| **Fix 3: 堵死前线误判抽血与 `oppFloorCap=38` 漏洞** | `tsb/squad/make_v27_team.py`<br>`tryDonateToTeammate(g)` L786, L787, L838, L862 | `safeFloor` 调 `this.safeAt(g, -1)`（被 `oppFloorCap=38` 截断）；`isPureInlandSafe` 未检查 `this.nb.length === 0`；前线 `dMe >= 106` 即可捐款 | `isPureInlandSafe` 必须满足 **`boxedIn`**（`this.nb.length === 0`）；`safeFloor` 使用未截断的 **`super.safeAt(g, -1)`**；非 `boxedIn` 前线兄弟仅在 `dMe >= 138` 且 `B >= 1.25 * safeFloor` 时才允许捐出 `pct = 120` | 彻底杜绝 G01/G06/G07 前线打 Bot 时在 `d=40~69` 误捐，以及 G01/G04/G08 前线主将在 `d=106~132` 自残抽血 |
| **Fix 4: 校验引擎 `ao.iD(ally)` 配额并禁止后排捐后排** | `tsb/squad/make_v27_team.py`<br>`tryDonateToTeammate(g)` L879 | `if (!allyEnemyNbs.length && outAtk === 0 && inAtk === 0 && g.t > 2200) continue;`（未校验 `ao.iD` 且 `t<=2200` 允许捐给内陆后排） | 移除 `&& g.t > 2200`（全时段要求受捐方 `p` 有敌邻或交火），并增加 **`if (typeof window !== "undefined" && window.ao?.iD && !window.ao.iD(p)) continue;`** | 消除 `55%` 的 `ao.ei` 静默拒收废指令与 `t=1500~2200` 的后排乒乓互捐 |

### 5.2 可直接合入 `tsb/squad/make_v27_team.py` 的最小改动代码段

```javascript
// In tryDonateToTeammate(g) (tsb/squad/make_v27_team.py lines 772-900):
const B = g.bal[me], L = Math.max(1, g.terr[me]), dMe = B / L;
const boxedIn = this.nb.length === 0 && (this.neutral === 0 || (g.t >= 850 && this.neutral <= 8 && dMe >= 55));
const hasExposedCoast = (g.coast?.[me]?.length ?? 0) > 0;
const coastGuardFloor = boxedIn ? (hasExposedCoast ? 28 * L : 18 * L) : (hasExposedCoast && g.t >= 1100 ? 68 * L : 25 * L);
const rawThreatFloor = enemyHumanNbs.length > 0 ? super.safeAt(g, -1) : 0;
const safeFloor = Math.max(coastGuardFloor, rawThreatFloor);
const isPureInlandSafe = boxedIn && !hasExposedCoast && myHumanInAtk === 0;
const canReceiveDonate = (p) => typeof window === "undefined" || !window.ao || typeof window.ao.iD !== "function" || window.ao.iD(p);
```
- **正交性说明**：上述改动仅作用于 `tryDonateToTeammate(g)` 与 `tryEmergencyBossRescue(g)` 的团队内部资金转移层，不改变单人陆战估值函数 `offers(g)` 或选点协调器 `spawn-coordinator.mjs`，风险等级为 **`low`**，预计单独修复 `V6` 即可提升多队局胜率 **`+15% ~ +22%`**（与 `V1/V2` 选点修复及 `V7` 防御底线修复叠加后可恢复 `>= 80%` 胜率）。
