---
from: R05
to: HUB
type: report
time: 2026-11-11T21:02:38Z
---

M7 第二部分交付：假设卡 24 张 + 有效做法 1 张、全量检测脚本定稿、数字核对脚本。只有口径、计数、方向和反例，没有改法。

位置（都在 c136-review/agents/R05/ 下）
- cards/INDEX.md：目录。第 1 节是按 ledger/PATTERNS.md 的列写好的 24 行，可以直接并表。
- cards/<编号>.md：一张卡一个模式，固定八节：定义、脚本、全量、13 局、机制（代码行号和公式）、与胜负的方向、反例与混杂、还没验证。
- cards/README.md：口径、证据等级、出处标记，以及给 R10 在验证集上复跑的命令。
- scripts/cards_check.py：把卡和 CROSS-MATCH-SUMMARY 里的每个数与出处表核对。

全量 = 发现集里录像盘有我方号的 107 局（A 组 75、B 组 32）。A 组一共只赢 8 局，下面的赢局数只看方向。

全量上有方向的 6 张（有这个模式的局：局数 / 赢 / 按队数的期望赢；括号里是没有的局）
- SP-OVERLAP 两个号落在同一个出生点：20 / 0 / 7.5（55 / 8 / 20.1）。B 组没有这个方向。
- DN-SINK-FEED 捐给 300 拍内丢地两成以上或阵亡的号，占一局笔数 ≥30%：17 / 0 / 6.1（46 / 7 / 16.5）。
- SE-FEW-BOATS 到 3000 拍还在、全程出船 ≤5 条：26 / 1 / 8.9（45 / 7 / 17.0）。
- IO-LAG-STALE 客户端延迟波：41 / 3 / 15.0（32 / 5 / 11.6）。
- EC-BANK-IDLE 1500–3000 拍自围采样 ≥30%：41 / 3 / 15.6（32 / 5 / 11.1）。
- AT-NEUTRAL-CROWD 每拍一条的名额被挤掉 ≥5%：6 / 0 / 2.6（69 / 8 / 25.1）。只有 6 局。

方向相反、不能当失分标记的 3 项
- DN-PINGPONG 的来回互捐：13 / 6 / 5.7（49 / 2 / 16.3）。
- 探路船（pct=0）：A 组 1,257 条里 1,224 条在赢的 8 局。
- AT-BOTLOCK 的全量上界（贴着机器人没出手的窗口）：28 / 5 / 9.7（47 / 3 / 17.9）。
这三项都是活得久、没有延迟波的局里更多。

全量普遍存在、分不出类的 7 张：IO-BATCH9、AT-PULSE-REPEAT、DN-QUOTA-BLIND、SP-EXEC-MISS、DN-BURST-DRAIN、EX-CLIENT-DROP、EX-SPLIT-ROOM。

只有 13 局证据的 9 张（要影子策略或逐拍重演，全量没跑）：AT-BOTLOCK、AT-HOLD-1500、AT-OVER-RELEASE、OP-MID-STALL、SP-SHARE-SHORT、DN-DONOR-GATE、DF-DOOMED-POCKET、EC-NOFULLSEND-LOCK、SE-BOAT-WASTE。

脚本这一轮的改动
- pattern_scan.py 新增两个检测项：S（拆盘：日志里的我方号数比这一盘录像里配得上的多 ≥2，A 组 6/75 局、B 组 7/32 局）；F 加了自围口径（采样 nb=0 且 neut=0，等于策略里的 boxedIn）。
- 全部全量脚本可以用 C136_BUNDLES / C136_CMDS / C136_IDMAP 三个环境变量换数据根。我没有碰验证集。
- cross_ledger.py 第 4 节加了各局占比的中位。

更正上一份报告（outbox 0013）里的一处
- CROSS-MATCH-SUMMARY 第 7 节 EC-BANK-IDLE 行原来引的是 F 的「被围」列（neut=0 且 nb≥1，即没有中立可扩、还贴着别的玩家），不是被队友围住。已改成自围口径：A 组各局中位 34%，≥30% 的 41/73 局。
- 同一份报告里另外 30 多个数补了出处标记或改成表里的精确值，结论没有变。

核对结果和它的局限
- cards_check.py --all：4,380 个数，对不上 0 个；另有 4 个是 hub 广播 0004 原文里 R10 的数，登记在 cards/CHECK-ALLOW.tsv。
- 这个核对只看一个数在它标记的那张表里出现过，不看在哪一格。随机把 74 个数各加 1，抓到 61 个。

没有做的
- 出生份额、三层归因、放行口真值没有全量数：每局要逐拍重演几分钟。
- 没有做验证集复现（E3）和反事实（E4）。每张卡最后一节写了要验什么。

下一步：读 hub 的延迟与好地审计和 RFC-001 做对账，写 reports/COUNCIL-PROPOSAL.md。
