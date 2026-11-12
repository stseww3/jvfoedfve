# R05 假设卡目录（24 张失分模式 + 1 张有效做法）

口径、出处标记、证据等级见 `README.md`。「全量」= 发现集里录像盘有我方号的 107 局（A 组 75、B 组 32）；「13 局」= 我复盘的 13 局。
「方向」一栏写的是 A 组「有 / 没有」两类的赢局数对期望赢局数；A 组一共只赢 8 局，只看方向。

## 1. 给 `ledger/PATTERNS.md` 的一行摘要

| 编号（建议） | 名称 | 可检测的定义 | 提出者 / 首见对局 | 检测脚本 | 全量计数 | 证据 |
| :-- | :-- | :-- | :-- | :-- | :-- | :-- |
| `IO-LAG-STALE` | 客户端延迟波 | 600–1500 拍有新指令的 `[HL-TICK]` 采样里「迟到 ≥90 拍或永远没到」的占比 ≥25% | R05 / A017 | `pattern_scan.py` L、N | A 41/73 局，B 12/17 局；A 组没落地 20,048/61,864 条（32%） | E2 + E1×13 |
| `IO-BATCH9` | 连续 3 个回合最多执行 9 条 | 录像里一个玩家任意连续 3 个回合（21 拍）执行的指令合计；满 9 条的回合之后两个回合为空 | R05 / A014 | `round_limit.py`；`pattern_scan.py` B、P | 107 份录像 0 反例；满回合 本编队 1,007 个、其他真人 156 个 | E2 + E1×13 |
| `AT-NEUTRAL-CROWD` | 每个决策拍只收一条 | `results.csv` 的 sent − accepted ÷ sent ≥5% | R05 / A030 | `pattern_scan2.py` E | A 6/75 局；没收 1,943/94,609 条（2.1%） | E2 + E1×13 |
| `EC-NOFULLSEND-LOCK` | `isNoFullSend` 误置位 | 影子策略里该标志置位，而录像头的引擎规则没有开禁全兵 | R05 / A014 | `quota_guard.py`、`unlock_diff.py`（要影子） | 没有全量；13/13 局置位 | E1×13 |
| `SP-EXEC-MISS` | 出生指令没落地 | 一个号最后一条执行了的出生指令的坐标 ≠ 协调器给它的最终坐标；或一条出生指令都没执行 | R05 / A017 | `spawn_exec.py` → `spawn_exec_sum.py` | A 682 个号：落地 72%、停在旧坐标 20%、0 条 6% | E2 + E1×13 |
| `SP-OVERLAP` | 两个号落在同一个出生点 | 两个我方号最终出生点相距 ≤2 格 | R05 / A021 | `pattern_scan2.py` H.stack | A 20/75 局（27 对），B 15/30 局 | E2 + E1×2 |
| `SP-SHARE-SHORT` | 出生份额不足 | 按最近出生点分地，编队名下陆地占比 ÷ 人数占比 <1 | R05 / A017 | `land_account.mjs`（要地图）；代理 `pattern_scan2.py` H.nnMed | 没有全量；13/13 局 <1，中位 0.61 | E1×13 |
| `SP-ENEMY-INSIDE` | 别的真人站在阵里 | 其他真人最终出生点落在我方号凸包内，或任一我方号 40 格内 | R05 / A021 | `pattern_scan2.py` H.inHull、H.in40 | A 凸包内有人 31/70 局，≥3 人 5 局 | E2 + E1×6 |
| `OP-MID-STALL` | 600–1500 拍被反超 | 编队人均地 ÷ 其余真人人均地：600 拍 ≥1 而 1500 拍 <1 | R05 / A017 | `cross_ledger.py` §7（要重演）；代理 `pattern_scan.py` G | 没有全量真值；13 局里 12 局 1500 拍 <1 | E1×13 |
| `AT-BOTLOCK` | 机器人锁 | 600–1500 拍一个号贴着可打的机器人、没有在途进攻，留底 ≥ 可用兵，这一拍没发 | R05 / A014 | `tick_attrib.py`（要影子）；上界 `pattern_scan.py` F | 没有全量；13 局占决策拍 2.3–36.4% | E1×13 |
| `AT-PULSE-REPEAT` | 上一条还在路上就再下一条 | 同号同目标、相邻两条间隔 ≤21 拍、≥3 条一串 | R05 / A014 | `pattern_scan.py` R | A 600–1500 拍 1,466 串 5,725 条，73/73 局 | E2 + E1×13 |
| `AT-HOLD-1500` | 1500 拍后贴着真人不出手 | 影子策略 `buyLand` 返回在 L5359（价格门）、L5447（留底）、L5452 / L5616（不够一个 chunk） | R05 / A017 | `shadow.mjs` 出口行计数；上界 `pattern_scan.py` F2 | 没有全量；1500–3000 拍没出手窗口 A 输局中位 78%、赢局 80% | E1×13 |
| `AT-OVER-RELEASE` | 过 100×地 不看价格出手 | 打真人的一轮，第一条执行前存兵 > 100×地；按目标存兵 ≥ 自己、≥2 倍分 | R05 / A014 | `cross_ledger.py` §4（要重演）；弱代理 `pattern_scan2.py` V | 没有全量真值；13 局打真人的兵 76% 由此放出，47% 打向更强的目标 | E1×13 |
| `EC-BANK-IDLE` | 自围的号只攒兵 | `[HL-TICK]` 采样 `nb = 0` 且 `neut = 0`；1500–3000 拍这样的采样 ≥30% | R05 / A014 | `pattern_scan.py` F（selfBoxed） | A 41/73 局；各局中位 34% | E2 + E1×13 |
| `DN-QUOTA-BLIND` | 调度不看配额 | 录像里执行的捐兵条数 ÷ 捐兵日志条数 <50% | R05 / A014 | `pattern_scan.py` D；`match_extra.py --sec quota` | A 42/64 局；17,636 条里执行 4,638 条（26%） | E2 + E1×13 |
| `DN-DONOR-GATE` | 捐出方门槛 | 调度探针里正被真人打的（候选 × 拍）没有任何队友列为可捐对象 | R05 / A026 | `donprobe_why.py`（要影子） | 没有全量；13 局里 5 局 | E1×5 |
| `DN-BURST-DRAIN` | 配额一松就连发 | 录像里 [3213, 3513) 拍 ≥5 笔，或 [4284, 4884) 拍 ≥10 笔我方号捐兵 | R05 / A030 | `pattern_scan2.py` K.burst | A 36 局 / 28 局 | E2 + E1×5 |
| `DN-SINK-FEED` | 往守不住的号里送 | 受赠方到账后 300 拍内地 ≤ 到账前的 80% 或阵亡；一局这样的笔数 ≥30% | R05 / A030 | `pattern_scan2.py` K.recipLost | A 17/63 局；682/4,704 笔（14%） | E2 + E1×2 |
| `DN-PINGPONG` | 互捐与转手 | 同一对号 300 拍内两个方向各有 ≥1 笔；收到后 100 拍内转给第三个号 | R05 / A014 | `pattern_scan2.py` K.pingpong、K.relay | A 来回 948 笔（20%），≥10 笔的 13 局；转手 654 笔 | E2 + E1×5 |
| `DF-DOOMED-POCKET` | 挨打的号被判弃子 | 调度探针里候选在 L4455–4456 被跳过，按（候选 × 拍）计，分两个分支 | R05 / A014 | `donprobe_tally.py`（要影子） | 没有全量；13 局里 7 局 | E1×7 |
| `SE-FEW-BOATS` | 几乎不出船 | 录像到 3000 拍，我方号全程出船 ≤5 条 | R05 / A030 | `pattern_scan2.py` T.n | A 26/71 局 | E2 + E1×13 |
| `SE-BOAT-WASTE` | 落在队友地上 / 海上耗光 / 探路船船费 | 船到岸时落点归队友；≥10k 的船到岸 <60%；pct=0 的船 | R05 / A014 | `boat_fate.mjs`（要重演）；`pattern_scan2.py` T.scout | 全量只有探路船：A 1,257 条，其中 1,224 条在赢的 8 局 | E1×8 |
| `EX-CLIENT-DROP` | 客户端中途离场 | 录像里我方号有离场指令且早于阵亡；一局 3000 拍前 ≥1 个 | R05 / A026 | `pattern_scan.py` X | A 18/71 局；全程 25 局 62 个号 | E2 + E1×7 |
| `EX-SPLIT-ROOM` | 拆盘 | 日志里的我方号数 − 这一盘录像里配得上的号数 ≥2 | R05 / A017 | `pattern_scan.py` S | A 6/75 局，B 7/32 局 | E2 + E1×2 |

有效做法（`OP-DP-PAR`、`AT-THIN-KILL`、`AT-PULSE-BLEED`、`AT-FOCUS-KILL`、`DN-FRONT-FEED`、`AT-BOT-HARVEST`、`DN-DEFENSE-FEED`、`SE-BEACHHEAD-OPEN`）合在 `OK-PATTERNS.md` 一张卡里，没有全量检测器。

## 2. 按「全量上有没有方向」分组

**有方向（有的那一类赢得比期望少得多）**

| 卡 | 有：局数 / 赢 / 期望赢 | 没有：局数 / 赢 / 期望赢 | 主要混杂 |
| :-- | :-- | :-- | :-- |
| `SP-OVERLAP` | 20 / 0 / 7.5 | 55 / 8 / 20.1 | B 组没有方向（15 / 2 / 4.1 对 15 / 3 / 4.0） |
| `DN-SINK-FEED` | 17 / 0 / 6.1 | 46 / 7 / 16.5 | 受赠方丢地本身就是在输 |
| `SE-FEW-BOATS` | 26 / 1 / 8.9 | 45 / 7 / 17.0 | 活得久的局船多 |
| `IO-LAG-STALE` | 41 / 3 / 15.0 | 32 / 5 / 11.6 | 外因；与 `IO-BATCH9`、`AT-PULSE-REPEAT` 分不开 |
| `EC-BANK-IDLE` | 41 / 3 / 15.6 | 32 / 5 / 11.1 | 与出生份额、地图形状相关 |
| `AT-NEUTRAL-CROWD` | 6 / 0 / 2.6 | 69 / 8 / 25.1 | 6 局太少；与延迟波重合 |

**全量普遍存在，分不出类**：`IO-BATCH9`（有满回合的局 76/107）、`AT-PULSE-REPEAT`（73/73）、`DN-QUOTA-BLIND`（42/64）、`SP-EXEC-MISS`（输赢两类比例相同）、`DN-BURST-DRAIN`（28 / 4 / 10.1 对 34 / 4 / 11.9）、`EX-CLIENT-DROP`（18 / 2 / 6.5 对 53 / 6 / 19.5）、`EX-SPLIT-ROOM`（6 / 2 / 2.5 对 69 / 6 / 25.2）。

**方向相反，不能当失分标记**：`DN-PINGPONG` 的来回（13 / 6 / 5.7 对 49 / 2 / 16.3）、`SE-BOAT-WASTE` 的探路船（3 / 3 / 1.3）、`AT-BOTLOCK` 的全量上界 F（28 / 5 / 9.7 对 47 / 3 / 17.9）。这三项都是「活得久 / 没有延迟波的局里更多」。

**只有 13 局的证据（要影子策略或逐拍重演，全量没跑）**：`AT-BOTLOCK`、`AT-HOLD-1500`、`AT-OVER-RELEASE`、`OP-MID-STALL`、`SP-SHARE-SHORT`、`DN-DONOR-GATE`、`DF-DOOMED-POCKET`、`EC-NOFULLSEND-LOCK`、`SE-BOAT-WASTE`（除探路船）。

## 3. 按时段排

| 时段 | 卡 |
| :-- | :-- |
| 选点期 | `SP-EXEC-MISS`、`SP-OVERLAP`、`SP-SHARE-SHORT`、`SP-ENEMY-INSIDE`、`EX-SPLIT-ROOM` |
| 0–600 拍 | 没有失分卡（`OP-DP-PAR` 13/13 局有效） |
| 600–1500 拍 | `IO-LAG-STALE`、`IO-BATCH9`、`AT-PULSE-REPEAT`、`AT-NEUTRAL-CROWD`、`AT-BOTLOCK`、`OP-MID-STALL`、`EC-NOFULLSEND-LOCK`、`EX-CLIENT-DROP` |
| 1500–3213 拍 | `EC-BANK-IDLE`、`AT-HOLD-1500`、`DN-QUOTA-BLIND`、`SE-FEW-BOATS`、`AT-OVER-RELEASE` |
| 3213–4284 拍 | `DN-BURST-DRAIN`、`DN-DONOR-GATE`、`DN-SINK-FEED`、`AT-OVER-RELEASE` |
| 4284 拍以后 | `DN-PINGPONG`、`DN-BURST-DRAIN`、`DF-DOOMED-POCKET`、`AT-OVER-RELEASE`、`SE-BOAT-WASTE` |

## 4. 合并掉的模式键

13 局复盘里登记过的模式键：出现在 ≥3 局的 36 个，另有 52 个只出现在 2 局以内 [RO §6]。同一段代码、同一个量的合成了一张卡，卡头的「并入的模式键」列出了来源。没有进卡的键：只在 1–2 局出现、又没有全量检测器的（例如 `EC-PEAK-RATCHET`、`EC-RETURN-CLIP`、`DF-COAST-PINGPONG`、`AT-COUNTER-CARCASS`、`IO-SAMPLER-GAP`），定义留在各局的复盘 JSON 里。
