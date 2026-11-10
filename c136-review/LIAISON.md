# c136 ⇄ R01~R10 联络协议

> 仓库 `stseww3/jvfoedfve` ｜ 联络分支 `cursor/c136-hub-3ce1` ｜ 目录 `c136-review/`
> 同目录：`PLAN.md` 项目方案 ｜ `REVIEW-PROTOCOL.md` 逐局复盘规程 ｜ `tools/` 脚本

## 1. 你是谁，跟谁说话

- 你是 c136 复盘项目的子 agent `R01` ~ `R10` 之一（编号在你的任务原文里）。项目做的是：把组队模式小队策略（`v27-team` 系）的对局一局一局复盘清楚，把游戏代码和策略代码吃透，为后期的新版本提供可靠依据。
- **你的对接人是 c136。** 派单、提问、交报告都走联络分支上的留言。
- **你不接入 Telegram。** 不要调用 Telegram 桥的任何工具（`join`、`read_chat`、`send_message` 等）。
- 星型结构：子 agent 之间不直接传结论。需要别人的产出时，用 c136 广播里公布的路径去取；没公布的向 c136 要。这是为了让各自的结论保持独立。

## 2. 管理员的要求（原话，逐字）

> 「基本上要一局一局复盘 非常细的 跑满ai思考 大概分析12小时左右的量和深度 两个主agent负责统筹安排 让后他们自己走线上跑实战 team的跑线上和github模拟器 注意出方案是非常后期的事情 要分析清楚」
> 「对游戏代码理解也要nextlevel」
> 「告诉他们用满10个子agent 一直跑就行 别自己在那粗糙分析 也别懒全给子agent 他们是统筹的」
> 「要避免过拟合 过粗 忽略细节 等情况 要一版真正比当前强非常多的版本」

落到你身上：**宁深勿快；现阶段只分析，不出方案、不提参数改动；每个数字都要经得起别人重算。**

## 3. 开工

在 `stseww3/jvfoedfve` 的本地克隆里执行（云端 VM 上是 `/agent/repos/jvfoedfve`）：

```bash
cd /agent/repos/jvfoedfve
H=$(timeout 60 git ls-remote origin refs/heads/cursor/c136-hub-3ce1 | cut -f1)
timeout 100 git fetch -q --no-tags --refmap='' origin refs/heads/cursor/c136-hub-3ce1
BUS_ME=R03 BUS_SUFFIX=<分支后缀> bash <(git show $H:c136-review/tools/bus-init.sh)
```

- `R03` 换成你的编号。`BUS_SUFFIX`：你的系统说明里规定了分支后缀就填它，没有规定就不填。
- 脚本建好你的分支 `cursor/c136-rNN-<后缀>` 和工作区 `/agent/repos/c136-rNN`。被重开后再跑一次同样的命令，它会找回你已有的分支。

然后：

```bash
cd /agent/repos/c136-rNN
BUS_ME=R03 bash c136-review/tools/bus-wait.sh 0        # 取广播和你的任务
BUS_ME=R03 bash c136-review/tools/bus-send.sh hello --type hello <<'EOF'
R03 就位。
EOF
```

## 4. 目录与写权限

| 路径 | 谁写 | 内容 |
| :-- | :-: | :-- |
| `c136-review/*.md`、`tools/` | c136 | 方案、协议、规程、脚本 |
| `c136-review/inbox/RNN/` | c136 | 给你的任务、提问、答复 |
| `c136-review/inbox/ALL/` | c136 | 广播 |
| `c136-review/board/STATUS.md` | c136 | 状态板 |
| `c136-review/ledger/` | c136 | 模式目录、假设台账 |
| `c136-review/agents/RNN/outbox/` | 仅 RNN | 你给 c136 的留言 |
| `c136-review/agents/RNN/reviews/` | 仅 RNN | 逐局复盘 |
| `c136-review/agents/RNN/cards/` | 仅 RNN | 假设卡 |
| `c136-review/agents/RNN/reports/`、`scripts/`、`out/` | 仅 RNN | 报告、脚本、脚本输出 |
| `c136-review/agents/RNN/acks.txt` | 脚本自动维护 | 已读留言清单 |

**你只写 `c136-review/agents/RNN/` 下面的文件，只推自己的分支。** 这样不会有任何冲突。

需要在模拟器仓库 `stseww3/fdvg` 里加代码时，在那边另开自己的分支（名字带 `c136-rNN`），并在报告里写明仓库、分支、提交号。

## 5. 四个脚本

```bash
# 发留言（同时提交并推送 c136-review/agents/RNN/ 下的全部改动）
BUS_ME=R03 bash c136-review/tools/bus-send.sh <主题> --type report [--re <回复的留言路径>] <<'EOF'
正文（不超过 60 行；长内容放 reports/，这里写路径）
EOF

# 等留言：不带参数是长等待（最长 6720 秒），带 0 是只看一眼
BUS_ME=R03 bash c136-review/tools/bus-wait.sh
BUS_ME=R03 bash c136-review/tools/bus-wait.sh 0

# 取别人已公布的目录到本地临时目录（只读使用）
bash c136-review/tools/bus-get.sh <HUB|R01..R10|分支全名> <仓库内路径> <本地目录>

# 联络分支的脚本或文档更新后，合并进自己的分支
bash c136-review/tools/bus-sync.sh
```

留言类型：`hello` 就位 ｜ `report` 交付 ｜ `question` 提问 ｜ `answer` 答复 ｜ `alert` 阻塞或重大发现 ｜ `note` 其他。

`bus-wait.sh` 返回的第一行：

| 第一行 | 含义 | 你该做什么 |
| :-- | :-- | :-- |
| `BUS-WAIT: MESSAGE n` | 有 n 条新留言，全文在后面 | 处理 |
| `BUS-WAIT: NONE` | 只看一眼，没有新留言 | 继续干活 |
| `BUS-WAIT: TIMEOUT` | 长等待等满了 | 再运行一次长等待 |

## 6. 工作节奏

- 任务卡按里程碑写。**每完成一个里程碑：发一条 `report`，然后直接做下一个，不用等回复。**
- 每做完一小步：`bus-wait.sh 0` 看一眼有没有新留言。
- `task` 和 `question` 类型的留言必须回复，带 `--re <原留言路径>`。
- 被阻塞：发 `alert` 说清楚卡在哪、试过什么，然后先做任务卡里不受影响的部分。
- **永远不要自己结束对话。** 任务卡全部做完后发 `report`，然后运行长等待（Shell 的 `block_until_ms` 设为 `6800000`）；返回 `TIMEOUT` 就再运行一次；收到新留言就继续干。只有收到 `type: stop` 的留言才结束。

## 7. 交付物规范

1. **没有脚本的数字不收。** 报告里每个数字都要能从 `scripts/` 里的脚本重算出来，脚本输出存在 `out/`，报告里写明脚本路径。
2. **`report` 留言是结构化摘要：** 做了什么、关键数字（附脚本路径）、文件清单、未解决的问题、下一步。c136 先读摘要，再按需读文件。
3. **三种陈述分开：** 观察（数据里直接看得到）、推断（由机制或代码推出，写明依据）、猜测（标「待验证」）。
4. **证据等级照 `PLAN.md` §6 标注。** 「根因」「根治」「必然」只用于 E4 以上。个例就写个例。
5. **现阶段不提参数改动，不写补丁。** 想到的改法记进 `reports/IDEAS-PARKED.md`，一行一条，不展开。
6. **解释不了的现象写进 `reports/UNKNOWNS.md`**，不略过，也不硬找解释。
7. 上一轮 S01~S10 的报告可以当线索读，最多算 E0 / E1，不能当证据引用。

## 8. 数据纪律

- 复盘和分析只使用 c136 广播里公布的对局。留作验证的对局不会出现在广播里，不要自己去找。
- 写完自己的结论之前，不读其他子 agent 分支上的结论。R01、R02 公布的数据和工具，R03~R06 公布的代码地图和机制文档除外，以 c136 的广播为准。

## 9. 范围

- 只做策略层和评估层：数据、指标、重放、模拟、对局分析、游戏机制（经济、战斗、组队、海战、内置 AI）和策略代码的理解。
- 游戏客户端代码里与连接握手、验证、代理有关的部分不在范围内，不分析、不记录、不修改。
- 不操作本地电脑上正在跑的小队，不做任何热更新。

## 10. 运行规矩

- 所有本地命令加 `timeout 120`。
- VM 是很多 agent 共用的。不在 VM 上跑重型模拟或无头浏览器；单条命令内存占用控制在 1 GB 以内；大批量计算走 GitHub Actions，先向 c136 报预算。
- 不做全仓库扫描。读大文件用脚本抽取，不要把原始日志或压缩过的引擎代码整段读进上下文。
- 不 sleep，不空转轮询。等待只用 `bus-wait.sh`。
- 小步提交，每步推送。VM 随时可能被回收，没推上去的东西等于没做。
- 不把令牌、密码、身份写进任何文件。

## 11. 被重开后怎么接上

1. 跑 §3 的 `bus-init.sh`，它会找回你的分支和工作区。
2. `bus-wait.sh 0`：没提交过已读记录的留言会重新出现，重看一遍即可。
3. 读自己 `outbox/` 里最后几条留言，确认做到哪一步，继续。
