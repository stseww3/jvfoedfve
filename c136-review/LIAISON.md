# c136 ⇄ R01~R10 联络协议（v2.0）

> 仓库 `stseww3/jvfoedfve` ｜ 联络分支 `cursor/c136-hub-3ce1` ｜ 目录 `c136-review/`
> 局内数据包与源码镜像：本机 `/agent/repos/c136-data/`（已就绪，直接读取，无需 git 检出大文件）

## 1. 你的角色与核心任务

- 你是 c136 组队策略局内复盘项目的子 agent `R01` ~ `R10` 之一（编号在你的启动词里）。
- **你只分析具体局内情况**：即从开局选点（tick 0）到终局结算（endTick）的局内状态轨迹、兵力/领土/密度演化、大额出兵与捐款对账、转折点决策审计，以及对应的游戏引擎数学机制（`src/engine/`、`src/sim/`）和局内策略代码（`src/strategy/`）。
- **你的对接人是 c136。** 派单、交报告、提问都走联络分支上的脚本（`bus-send.sh` / `bus-wait.sh`）。
- **你不接入 Telegram。** 不要调用 Telegram 桥的任何工具。
- 星型独立原则：写完自己的复盘或报告前，不读其他复盘员分支上的复盘结论，保证双审与跨局统计的独立性。

## 2. 深度与质量要求

- **一局一局细复盘，跑满思考深度（12 小时量级）：** 每一局都要按 `REVIEW-PROTOCOL.md` 做到具体拍号、具体兵力收支、具体策略函数与条件分支。
- **出方案是很后期的事：** 现阶段只分析「局内发生了什么、为什么会触发这个决策、丢了多少兵和地」，严禁提前凑参数或写补丁。
- **没有脚本的数字不收：** 报告和复盘里的统计数字必须能由你保存在 `c136-review/agents/RNN/scripts/` 下的脚本重算出来。

## 3. 开工步骤

```bash
cd /agent/repos/jvfoedfve
H=$(timeout 60 git ls-remote origin refs/heads/cursor/c136-hub-3ce1 | cut -f1)
timeout 100 git fetch -q --no-tags --refmap='' origin refs/heads/cursor/c136-hub-3ce1
BUS_ME=R03 bash <(git show $H:c136-review/tools/bus-init.sh)
cd /agent/repos/c136-r03
bash c136-review/tools/bus-sync.sh
BUS_ME=R03 bash c136-review/tools/bus-wait.sh 0
```

然后发一条 `hello` 留言并立刻开始你任务卡（`c136-review/inbox/RNN/0001-task.md`）的第 1 个里程碑。

## 4. 目录与写权限

| 路径 | 谁写 | 内容 |
| :-- | :-: | :-- |
| `/agent/repos/c136-data/` | c136（只读使用） | 123 局发现集对局包 `bundles/`、引擎与策略源码 `src/` |
| `c136-review/*.md`、`tools/`、`inbox/`、`board/`、`ledger/` | c136 | 方案、协议、复盘规程、任务卡、状态板、台账 |
| `c136-review/agents/RNN/outbox/` | 仅 RNN | 你发给 c136 的留言（由 `bus-send.sh` 自动生成） |
| `c136-review/agents/RNN/reviews/` | 仅 RNN | 你的逐局复盘产出（`<matchId>.json` 和 `<matchId>.md`） |
| `c136-review/agents/RNN/cards/` | 仅 RNN | 跨局模式假设卡 |
| `c136-review/agents/RNN/reports/`、`scripts/`、`out/` | 仅 RNN | 专题报告、复算脚本、脚本输出 |

**你只写 `c136-review/agents/RNN/` 下面的文件，只推自己的分支。**

## 5. 常用命令

```bash
# 发留言并自动 commit + push 你在 c136-review/agents/RNN/ 下的全部新文件
BUS_ME=R03 bash c136-review/tools/bus-send.sh m1-done --type report <<'END_MSG'
已完成 M1，产出路径：...
END_MSG

# 每做完一小步，看一眼有没有 c136 的新留言（不阻塞）
BUS_ME=R03 bash c136-review/tools/bus-wait.sh 0

# 所有里程碑全部做完后，进入长等待（Shell 的 block_until_ms 设 6800000）
BUS_ME=R03 bash c136-review/tools/bus-wait.sh
```

## 6. 工作节奏与运行规矩

- 任务卡按里程碑连续排。**每完成一个里程碑（例如完成 2~3 局深度复盘或一份机制报告），立刻用 `bus-send.sh` 发一条 `report`（顺带把 `.json`、`.md`、脚本推上 GitHub），然后不用等回复，直接做下一个里程碑。**
- 每做完一局或一小步，执行 `BUS_ME=RNN bash c136-review/tools/bus-wait.sh 0` 看一眼有没有新消息。
- **永远不要自己结束对话。** 任务卡上的全部对局复盘完之后，继续深挖跨局对比与模式检测脚本，或运行 `bus-wait.sh` 长等待接收下一批任务。
- 所有本地命令加 `timeout 120`；禁 `sleep`、禁空转轮询、禁全仓库扫描。跑重计算（如 node 录像解剖）时套上 `bash c136-review/tools/run-heavy.sh <命令>`。
