## 11 脚本与产物

**跨局脚本（`scripts/`）**

| 脚本 | 做什么 | 产物 |
| :-- | :-- | :-- |
| `bundle_patterns.py` | 全量 123 局，日志 / 快照 / 对局卡侧的检测器（STACK70、CAP150、OVER100、FLAT600、SEALED、LAG180、SLOW、SHARE1530、SPAWNGAP、LEFT、SPLIT、REJ、COLLAPSE）；分版本、分结果、局间秩相关 | `out/bundle_patterns.txt`、`out/bundle_patterns.tsv` |
| `bundle_cmdstream.py` | 全量有录像的局，落地指令流的检测器（BATCH3、REPEAT、TINY、BOATLOW、SPAWN、DONLAND），同局其他真人做对照 | `out/bundle_cmdstream.txt`、`out/bundle_cmdstream.tsv`、`out/bundle_cmdstream_mine.txt` |
| `replay_stream.py` | 纯 Python 的录像解码（上面那个脚本用） | — |
| `bundle_humans.py` | 同一批 99 局录像：别的真人 / 我方 / 另一支本方编队的落地指令画像（目标、比例、间隔、捐款、船） | `out/bundle_humans.txt` |
| `bundle_join.py` | 把两张逐局表拼起来：时钟相差对成摞占比、成摞占比对占地比（含偏相关）、三等分 | `out/bundle_join.txt` |
| `m7_collect.py` | 把同一个单局脚本对 13 局各跑一遍，留汇总行 | `out/m7/<名字>.txt` |
| `m7_totals.py` | 把 13 局的汇总行排成 25 张表并求和 | `out/m7/TABLES.md` |
| `m7_version_table.py` | 把两份全量计数按版本、按结果摘成两张对比表 | `out/m7/VERSIONS.md` |
| `m7_funnel_bytype.py` | 把 13 局延迟账里「想发 → 落地」按陆攻 / 捐款 / 船拆开 | `out/m7/FUNNEL-BYTYPE.md` |
| `pattern_matrix.py` | 从 13 份复盘 JSON 数「模式 × 对局」 | `out/pattern_matrix.md`、`out/pattern_matrix.txt` |
| `pattern_evidence.py` | 每个模式的机制、代码位置和各局的原文证据 | `out/pattern_evidence.txt` |
| `spawn_geometry.py` | 出生阵型的几何和 630 / 1530 拍的领土、密度对比 | `out/spawn_geometry.txt` |
| `doomed_pocket.py`、`allin_strikes.py`、`seal_floor.py`、`neutral_pickup.py` | 四个跨局专项（弃子时段、全压、封死发船、捡无主地） | `out/*_all.txt` |
| `hub0007_table.py` | 延迟账 / 好地账的逐局大表 | `out/hub0007/m7_table.md` |
| `m7_report_build.py`、`m7_numcheck.py` | 拼这份报告；核对正文里手写的数 | `reports/CROSS-MATCH-SUMMARY.md` |

**重跑的顺序**（都在 `c136-review/agents/R04/` 下；前三条只读 `c136-data/bundles/`）：

```
python3 scripts/bundle_patterns.py --tsv out/bundle_patterns.tsv > out/bundle_patterns.txt
python3 scripts/bundle_cmdstream.py --tsv out/bundle_cmdstream.tsv > out/bundle_cmdstream.txt
python3 scripts/bundle_join.py > out/bundle_join.txt
python3 scripts/bundle_humans.py && python3 scripts/bundle_humans.py --report > out/bundle_humans.txt
python3 scripts/m7_totals.py > out/m7/TABLES.md
python3 scripts/m7_version_table.py > out/m7/VERSIONS.md
python3 scripts/m7_funnel_bytype.py > out/m7/FUNNEL-BYTYPE.md
python3 scripts/m7_report_build.py
python3 scripts/m7_numcheck.py
```

`m7_totals.py` 读的是 `out/m7/*.txt`、`out/hub0007/m7_table.md` 和四个 `out/*_all.txt`；这些要先有 13 局的真引擎事实表和影子表（`tmp/truth/`、`tmp/shadow/`，不进仓库，各局复盘里写了怎么重建）。

**假设卡**在 `cards/`（H01~H14），每张对应上面一组模式：可证伪的陈述、机制与代码位置、13 局的证据、全量上的检测器和读数、什么结果算证伪、边界。

## 附录　模式 × 对局

E = 判错，G = 判对，U = 不明；数字是这一局里这个模式的决策条数（1 条不写）。

{{MATRIX}}
