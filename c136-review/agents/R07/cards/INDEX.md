# R07 假设卡索引（M6）

来源：我逐局复盘过的 15 局（g09 4 局、Vb 10 局、Va 1 局）＋ 对全部对局包的机械计数（123 个对局包，其中 107 局带录像）。
配套报告：`reports/CROSS-MATCH-SUMMARY.md`。卡里的每个数都能在 `out/_cross/` 的脚本输出里找到（`scripts/49b_audit_report.py` 逐个核对）。

**这些卡只是分析和待验证的说法，不含补丁和参数。**「观测」= 数据里直接数出来的；「推断」= 从观测推出来、还没有直接证据的。

| 卡 | 说法 | 类型 | 环节 | 15 局里 | 全量 |
| :-- | :-- | :-- | :-- | :-- | :-- |
| [H01](H01-hold-and-rotate.md) | 指令被按住，各号按固定顺序轮流、成批放行 | 观测；位置未知 | 执行层 | IO-LAG-BATCH 10 局 45 例 | 1,657 段静默（72 局）；轮转顺序 154 / 173 对保持 |
| [H02](H02-nine-per-three-rounds.md) | 任何连续 3 个回合，一个席位最多落 9 条 | 观测；「丢掉」是推断 | 执行层 | — | 969 + 265 + 3,752 个席位，0 个超过 |
| [H03](H03-flood-and-inflight-repeat.md) | 没落地就每拍重发；发得越密落得越少；晚到的批一拍清仓 | 观测 | 策略 ↔ 执行层 | AT-INFLIGHT-REPEAT 11 局 41 例 | 一窗 15~24 条的窗口落地 ÷ 发出 0.19（1,307 窗）|
| [H04](H04-spawn-first-send-lost.md) | 出生阶段最早发的选点指令不进录像；结果不变的号落在默认格点 | 观测；原因未知 | 出生 | 11 局全部的号 | 675 / 686 个号次；8 局 40 个号一条没进 |
| [H05](H05-spawn-final-assignment-stale.md) | 出生阶段结束时没停在最后一次指派上 | 观测 | 出生 | SP-SWAP-CHURN 7 局 16 例 | 20 + 132 个号次；46 局 |
| [H06](H06-spawn-too-dense.md) | 站位过密，人均天然地盘 0.41~0.80 倍 | 观测 | 出生 | SP-CLUSTER 12 局 | 119 局 1,134 个号 |
| [H07](H07-ai-land-race-floor-lock.md) | 600~1500 抢内置 AI 的地：多数决策拍不出手，留底拿队友当参照 | 观测（3 局）＋ 代码 | 开局逻辑 | OP-WINFLOOR-MATE 10 局 31 例 | 要影子重演，日志数不出 |
| [H08](H08-donations-not-landing.md) | 调度的捐款多数没进录像；进了的常捐错人 | 观测 | 调度 | DN-QUOTA-OVERSIZE 8 局 24 例 | 日志 17,232 条 / 录像 5,395 条 |
| [H09](H09-midgame-hold.md) | 1500 之后接敌、有兵、不出手 | 观测 ＋ 代码 | 核心逻辑 | MT-PRE2400-HOLD 9 局 20 例 | 113 局，4,170 / 6,920 个接敌窗口零进攻 |
| [H10](H10-death-chain.md) | 阵亡链：带着兵死、没人捐；或刚打空就被反手 | 观测 | 防守 / 调度 | DF-PASSIVE-BLEED 12 局 37 例 | 115 局 3,792 个窗口 |
| [H11](H11-seats-left.md) | 席位被判离开 | 观测；原因未知 | 宿主 / 连接 | IO-SEAT-LOST 4 局 10 例 | 20 局 62 个号（t<3000）|
| [H12](H12-boxed-rich-softcap.md) | 围死的号满仓、过软上限 | 观测 | 经济 | EC-BOXED-RICH 7 局 18 例 | 105 局 11,092 个快照 |

## 卡和卡之间

- **执行层三张（H01、H02、H03）连成一条链**：指令被按住（H01）→ 本地局面不变、策略每拍重发（H03）→ 放行时一口气到、超过 9 条的不进录像（H02）→ 落地的几条按当时余额逐条扣、一拍清仓（H03）。这条链只在 600 拍之后明显；0~600 拍延迟正常。
- **出生两张（H04、H05）是同一个环节**：选点指令的发送。H06 是协调器方案本身。
- **H06 → H07 → H12**：扇形阵把多数号围在内圈（H06、H12），贴着内置 AI 的只有外圈，外圈的号又互相拿队友当留底的参照（H07）。
- **H08 → H10**：捐款不成，是「带着兵死、没人捐」的一半原因。
- **H11 要先分层**：有号被判离开的局，别的卡的数字都会被它带偏。

## 用这些卡之前要知道的口径

1. **三类席位**：我方 = 这个对局包日志里的号；同场的同一批号 = 同一个操作者、不在这个对局包里的号；其余才是其他真人。23 局同场有第二队，这些局里「其他真人」可能混进名字对不上的同一批号；说到其他真人时优先用「没有第二队的 84 局」。
2. **日志的第一列是序号，不是时间戳**；对局包里没有墙上时钟，所有的「晚」都是按拍数算的。
3. **发出 vs 落地**：「发出」是策略自己的 `cmds` 计数，「落地」是录像里的指令。能对账的是 89 局（录像比日志短的 17 局、计数回绕的 1 局不算）。
4. **日志判据（H06、H09、H10、H12 的全量数字）不看录像**：它们量的是策略「发没发」，不受执行层丢指令影响；但也分不出是哪一道闸挡的。
5. **赢的局里多数判据同样命中**。全量计数只说明「多常见」，不说明「因为它输」。

## 复现

```bash
cd /agent/repos/c136-r07
python3 c136-review/agents/R07/scripts/56_cross_match.py                    # 15 局对照 → out/_cross/cross_match.txt
timeout 118 bash c136-review/tools/run-heavy.sh node c136-review/agents/R07/scripts/57_exec_census.mjs   # 解码全部录像（约 21 秒）
python3 c136-review/agents/R07/scripts/57_exec_census.py                    # → exec_census.txt / .tsv
python3 c136-review/agents/R07/scripts/58_throughput.py                     # → throughput.txt
python3 c136-review/agents/R07/scripts/42_patterns.py --all && python3 c136-review/agents/R07/scripts/59_pattern_census.py   # → pattern_census.txt
python3 c136-review/agents/R07/scripts/60_three_layer.py                    # → three_layer.txt
python3 c136-review/agents/R07/scripts/49b_audit_report.py                  # 核对报告和卡里的数字
```
