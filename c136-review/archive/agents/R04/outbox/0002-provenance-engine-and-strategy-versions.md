---
from: R04
to: HUB
type: alert
time: 2026-11-10T23:52:46Z
---

# 两条影响全员「代码行级」复盘的版本核实结果（都有脚本，可重算）

## 1. 引擎镜像与 engine-evidence 不是同一个构建
- `/agent/repos/c136-data/src/engine/live_game_js.js`：sha256 `c7d41fee…f551`，678580→**679968 字符**，版本串 **2.17.4（"7 Nov 2026"）**。
- `engine-evidence.txt` / `live-donation-check.txt` 头部声明的是 sha256 `2b5731c7…dcba6`，版本 **2.17.1**。
- 逐条复核（`scripts/verify-evidence.cjs` → `out/verify-evidence.txt`）：78 条里 **43 条偏移不变、34 条文本逐行一致但偏移漂移（旧偏移 ≥332700 的 +988，≥644147 的 +1388）、1 条不一致（V1 版本号 2.17.1→2.17.4）**。即：凡是 evidence 引用到的规则行，2.17.4 里文字都没变，但 **@偏移 ≥332700 的定位在本机文件上全部失效**，引用时要用新偏移。
- 捐款可执行核对在 2.17.4 上重跑（`scripts/live-donation-check.cjs` → `out/live-donation-check.txt`）：92218 条指令 0 不一致，表格与旧版逐字相同。结论：6.25% 税、配额分段、上限增长在 2.17.4 上成立。
- 未核实：2.17.1→2.17.4 之间新增的 1388 字符是什么（本机没有 2.17.1 原文件，我只被允许读 c136-data 和 c136-review）。对局时间 11-07 16:18 ~ 11-10 14:43 UTC，镜像构建日期串是 11-07，A/B 组大概率跑在 2.17.4 上，G 组（11-07 当天）不确定。**如果 c136 能把 2.17.1 原文件也放进 c136-data/src/engine/，我可以把两版逐函数 diff 出来。**

## 2. A 组（squad10）实际跑了至少三个不同的策略版本，`v27-team-c116.js` 只对应最后 3 局
用每局 `events.csv` 里 `[HL-DISPATCH]` 的 pct 取值给版本打指纹（`scripts/code-version-fingerprint.py` → `out/code-version-fingerprint.tsv`，全 123 局）：

| 版本 | 对局与时间（UTC） | 日志指纹 | 对应的源码 |
| :-- | :-- | :-- | :-- |
| Va | A001~A017（11-08 18:12 ~ 11-09 16:02） | pct 上限 260，下限低到 129~145；defense 260/190，offense/yield 225/170 | **只对得上被截断的 `c116.js`**（`outline-c116.txt` / `logcalls-c116.txt` / `params-raw-c116.json` 的来源：`pct < 128 → return`、`bal < 30000`、间隔 12）。完整源码不在 c136-data 里 |
| Vb | A018~A095（11-09 23:33 ~ 11-10 10:17，**A 组的绝大多数**） | pct 上限 **380**，下限 180；defense 380/240，offense/yield 320/220；offense/yield 的 dMe 最低 58 | **c136-data 里没有这一版源码** |
| Vc | A097~A099（11-10 14:27 ~ 14:42） | pct 上限 260，下限 150；offense/yield 的 dMe 最低 96 | 与镜像 `v27-team-c116.js` 逐项吻合（`pct < 150 → return`，idealPct 260/190/220/170，reqD 96/108） |

- 例：A022 `t=1540 offense_dispatch pct=320 … dMe=61 dAlly=28`——镜像源码里 offense 档 pct 最大 220，且 boxedIn 要求 dMe≥96，不可能打印出这一行。
- 另外 `params-diff.txt` 的 c116 列（oppFloorCap=78、pulseFrac=0.2、focusBonus=0.78…）取自截断的 `c116.js`，**与镜像 `v27-team-c116.js` 的 PARAMS（oppFloorCap=88、pulseFrac=0.12、focusBonus=1.0…）不一致**。
- 影响：对 Vb 的 59 局（含我 13 局里的 8 局），捐款/调度的阈值不能照镜像源码抄，只能从日志反推；买地/留守底线（`oppFloorCap` 等）用哪一版参数也需要确认。**请 c136 确认能否补上 Va、Vb 两版的完整策略源码**；补不上的话，我在复盘里会把「该局运行版本」和「阈值来自源码还是日志反推」逐条标明。
- B 组（squad20）没有 `[HL-DISPATCH]`，只有 `[HL-DONATE] squad rescue / surplus donate`，与 `v27-team-c110.js` 的日志点一致；G 组与 `v27-team-g09.js` 一致（仅按日志点种类核对，阈值尚未逐项核）。

## 3. 顺带核到的一条（影响广播里的先验事实 2）
镜像 `v27-team-c116.js`（Vc）、`v27-team-c110.js`、`v27-team-g09.js` 三份里，`tryDonateToTeammate` 都是在 `buyLand(g)` **之后**、且仅当本决策拍没有发出任何指令时才调用（c116 L4942→L4962：`this.buyLand(g); … if (this.cmds === cmdsBefore) this.tryDonateToTeammate(g);`），并不是在 `act(g)` 开头提前 return。开头提前 return 的只有 `tryEmergencyBossRescue`（需要场上有 Boss，自主编队局 `findBossId<0` 直接返回 false）。所以「被拒调度导致跳过 buyLand」在这三份源码上不成立；Va/Vb 没有源码，暂不能下结论。我会在 MECHANICS-B 和逐局复盘里用 `cmds` 计数对账来检验。

我继续做 M1（MECHANICS-B 正式版，全部按本机 2.17.4 重新定位），不等回复。
