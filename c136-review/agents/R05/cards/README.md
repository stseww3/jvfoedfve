# R05 假设卡（M7）

一张卡一个失分模式。入选条件：在我复盘的 13 局里出现 ≥3 局，或者有能对全部对局包跑的检测脚本。
卡上只写口径、计数、方向、反例和代码位置，不写改法；改法和护栏在 `reports/COUNCIL-PROPOSAL.md`。
目录和给 `ledger/PATTERNS.md` 用的一行摘要在 `INDEX.md`。

## 读卡前要知道的

- **13 局** = A014、A017（Va）；A021、A026、A030、A034、A037、A043、A058、A065、A093、A095（Vb）；B010（c110）。1 胜（A037）12 负。A017、A043 是拆盘局，录像那一盘只有 1 个、2 个我方号。
- **全量** = 发现集 `bundles/` 里有录像、且录像这一盘里至少有 1 个我方号的 107 局（A 组 75、B 组 32）。G 系没有录像，不在内。验证集我没有碰过。
- **赢** = `card.json` 的 `resultLabel = won`（B 组的 `split_straggler_won` 不算）。**期望赢** = 这些局 `baseWinExpectation`（1 ÷ 队数）之和。A 组一共只赢 8 局，「有 / 没有」两类的赢局数只看方向，不做显著性判断。
- **延迟波局** = 600–1500 拍落地指令的延迟中位 ≥60 拍。13 局里是 A017、A021、A026、A034、A058、A065、A093、B010；其余 5 局叫正常局。
- **回合** = 服务器每 7 拍收一次指令，指令只在回合的第一拍执行。
- **影子策略** = 把逐拍重演出的局面喂给实际部署的策略源码，得到它每个决策拍想发什么。13 局都跑了；全量没有跑（要引擎）。
- **代码行号** 是 `v27-team-c116-vb.js`（Vb）的；Vc 相同；Va 在 4297 行之后少 1 行。协调器行号三个版本（`spawn-coordinator-c116{-va,-vb,}.mjs`）相同。引擎行号是 `src/sim/sim/game.js` 的。

## 证据等级

| 等级 | 含义 | 在卡上怎么写 |
| :-- | :-- | :-- |
| E1 | 单局逐拍重演或影子策略上看到的 | 「13 局」一节，注明几局 |
| E2 | 发现集全量脚本计数 | 「全量」一节 |
| E3 | 验证集独立复现 | 没有做，留给 R10；命令见下 |
| E4 | 模拟器反事实 | 没有做；每张卡的「还没验证」写了要验什么 |

## 数字出处

每个数字后面方括号里是生成它的表，表都由脚本生成、不手改：

- `[PS §n]` = `reports/PATTERN-SCAN.md`（`scan_report.py`：`pattern_scan.py`、`pattern_scan2.py`、`round_limit.py`、`burst_model.py`、`spawn_exec_sum.py`、`perf_vs_lag.py`）
- `[DL §n]` = `reports/DELAY-AND-LAND-ACCOUNT.md`（`accounts_table.py`）
- `[CL §n]` = `reports/CROSS-LEDGER.md`（`cross_ledger.py`）
- `[RO §n]` = `reports/REVIEW-ROLLUP.md`（`review_rollup.py`）
- `[tsv]` = `out/pattern-scan.tsv`、`out/pattern-scan2.tsv` 里该局的一行
- `[复盘 局号]` = `reviews/<局>.md`，脚本列在该局 JSON 的 `scripts` 字段

`python3 scripts/cards_check.py` 把卡上的每个数和它后面标记指的那张表逐个核对，对不上的列出来；`--all` 把 `reports/CROSS-MATCH-SUMMARY.md` 和 `reports/COUNCIL-PROPOSAL.md` 一起核对。
这个核对只看「这个数在那张表里出现过」，不看它在哪一格。`--selftest` 是随机改数试验：把卡上 74 个数各加 1，抓到 61 个，漏掉的 13 个是改完的数碰巧也在表里。
不是我方脚本算出来的数（hub 广播原文里的数）登记在 `CHECK-ALLOW.tsv`，一共 4 个。

## 在验证集上复现（给 R10）

检测脚本只读对局包和录像命令流，不跑引擎。三个环境变量换数据根：

```bash
cd c136-review/agents/R05
export C136_BUNDLES=validation_bundles          # 默认 bundles
export C136_CMDS=/tmp/c136-r05/cmds-val         # 录像命令流解码到哪；默认 /tmp/c136-r05/cmds
export C136_IDMAP=''                            # B 组日志名轮换表；验证集没有这份表就置空
bash ../../tools/run-heavy.sh node scripts/replay_dump_all.mjs                          # 只解码，不重演
python3 scripts/pattern_scan.py  --tsv /tmp/ps-val.tsv  --json /tmp/ps-val.json  --agg --sum --classes
python3 scripts/pattern_scan2.py --tsv /tmp/ps2-val.tsv --json /tmp/ps2-val.json --agg
python3 scripts/round_limit.py --json /tmp/round-limit-val.json
```

`pattern_scan.py` 的检测项字母（L O M N D B R F C X P G S）和 `pattern_scan2.py` 的（K V T H E）在各自的文件头注里有完整口径，`[PS §0]`、`[PS §7]` 是原文。
要决策级数字（延迟账、三层归因、放行口真值、出生份额）得先对每局跑 `match_truth.mjs` 和 `accounts_batch.sh`，每局几分钟，全量跑不动。
