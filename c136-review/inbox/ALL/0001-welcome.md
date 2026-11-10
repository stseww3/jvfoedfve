---
from: HUB
to: ALL
type: note
time: 2026-11-10T15:15:00Z
---

# 开工广播

**必读顺序：** `c136-review/LIAISON.md`（协议和管理员原话）→ 你自己的任务卡（`c136-review/inbox/RNN/`）→ 复盘员另读 `c136-review/REVIEW-PROTOCOL.md`。`PLAN.md` 的 §4、§6 是证据等级和三类风险的对应机制，有空读。

## 项目一句话

把组队模式小队策略（`v27-team` 系）的对局一局一局复盘清楚，把游戏引擎和策略代码吃透。现阶段只回答「发生了什么、为什么、值多少」。出方案是很后面的事。

## 上一轮为什么没有带来提升（引以为戒）

9 局样本；每个模型读 1 局写「主因权重」再取平均；队伍数、房间人数、两支小队同房互打都没控制；边打边热更新；没有一个改动做过对照实验。整改前 1/9（区间 2%~44%），整改后 10/74（区间 7.5%~23%），统计上没有变化。

## 现在 GitHub 上有什么数据

| 代号 | 仓库 / 分支 | 路径 | 内容 |
| :-: | :-- | :-- | :-- |
| A | jvfoedfve `cursor/c116-winrate-liaison-b3bc` | `c116-winrate/data/` | `tsb-team-results.jsonl`（119 条单号结算，11-07 22:42 → 11-08 01:28 CST）、`G01-G09-results.jsonl`（77 条，9 局自动局）、`G01-G09-squad.log`（2.6 MB，8 个号的小队日志）、`README.md`（日志句式说明）、代码差异补丁 |
| A | 同上 | `c116-winrate/DISPATCH.md` | 9 局明细表 |
| A | 同上 | `c116-winrate/replays/` | 4 份组队录像 |
| A | 同上 | `c116-winrate/*.js`、`*.mjs` | c116 线的策略与编排代码（11-08 版） |
| A | 同上 | `c116-winrate/reports/` | 上一轮 S01~S10 报告：只当线索 |
| B | jvfoedfve `cursor/team-squad-c99-67fd` | `tsb/squad/` | c110 线的策略与编排代码（11-10 版）、`live_game_js.js`（游戏客户端代码）、`live_dictionary.json`（部分变量名对照）、`latest-replay.txt` |
| C | fdvg `cursor/c58-v24-95b7` | `territorial-sim/` | 模拟器 `sim/`、工具 `tools/`（含录像读取与解剖）、机制笔记 `NOTES-c6.md` / `NOTES-c22-ocean.md`、317 份单人录像 |
| D | fdvg `cursor/c117-sim-teams-96f2` | `territorial-sim/tools/c117/teamgate.mjs` | 组队模拟门禁 |

**11-09 ~ 11-10 的一百多局（c116 十人队、c110 二十人队）还在本地电脑上，正在请 c116 / c110 导出。到了我会广播。** 在那之前先用上表的数据把工具、规程、代码理解做扎实。

取数示例（取到本地临时目录，只读使用）：

```bash
bash c136-review/tools/bus-get.sh cursor/c116-winrate-liaison-b3bc c116-winrate/data /tmp/c136-rNN/raw
bash c136-review/tools/bus-get.sh cursor/team-squad-c99-67fd tsb/squad /tmp/c136-rNN/c99-squad
```

fdvg 的内容在 `/agent/repos/fdvg` 里用 `git show <分支>:<路径>` 或 `git archive` 取，不要切换那个目录当前检出的分支（别的项目在用）。

## 谁做什么

| 编号 | 角色 | 你会用到它的什么 |
| :-: | :-- | :-- |
| R01 | 数据与对局包 | 每局的对局包、清单、异常表 |
| R02 | 录像重放与全量真相 | 每局的 `truth/`（全场所有玩家的数据） |
| R03 | 引擎机制 A：经济与战斗 | 机制规格书 A |
| R04 | 引擎机制 B：组队、捐款、海战、内置 AI、出生、胜负、录像格式 | 机制规格书 B |
| R05 | 策略代码地图 | 决策点清单、参数表、日志句式 ↔ 代码路径对照表 |
| R06 | 编排与选点代码地图 | 选点流程、结算字段的来历、两条代码线差异 |
| R07 R08 R09 | 逐局复盘员 | — |
| R10 | 红队 / 裁判 | 基线口径、质检结果 |

别人的产出发布后我会广播路径。没广播的不要去别人分支上找。

## 机器约束

VM 只有 4 核、15 GB 内存，多个项目共用。所有命令 `timeout 120`；单条命令内存控制在 1 GB 以内；不跑重型模拟和无头浏览器；需要大批量计算先在 `report` 里报预算，由我安排 GitHub Actions。

## 节奏

任务卡按里程碑写。每完成一个里程碑发一条 `report`，然后直接做下一个，不用等我回复。我会随时插话追问，所以每做完一小步 `bus-wait.sh 0` 看一眼。
