## 8 可对全量 `bundles/` 机械计数的脚本

三个脚本都只读对局包、不跑引擎、不跑影子策略，单线程一分钟以内跑完。检测器的定义写在各脚本开头的注释里；下表是检测器和 13 局复盘里的模式的对应关系，以及它在全量上的读数。

| 检测器 | 脚本 | 数据 | 对应的模式 | 全量读数（我方 / 对照） | 能不能区分赢和输（squad10） |
| :-- | :-- | :-- | :-- | :-- | :-- |
| BATCH3 | `bundle_cmdstream.py` | 录像 | `NEW-IO-STACK9`、`NEW-IO-DRAINBATCH` | 39% / 1% | 赢 26%，输 41% |
| REPEAT | `bundle_cmdstream.py` | 录像 | `NEW-IO-ACKREPEAT` | 53% / 20% | 不能（58% 对 59%） |
| SPAWN | `bundle_cmdstream.py` | 录像 | `NEW-SP-RESOLVE`、`NEW-SP-NOEXEC` | 中位 11 条 / 2 条 | 赢 11 条，输 18 条；和 1530 拍占地比的秩相关 +0.08 |
| DONLAND | `bundle_cmdstream.py` | 录像 + 日志 | `NEW-DN-QUOTABLIND` | 四档 1%、7%、25%、97% | 分档后差不多；合计赢 57%、输 22% |
| TINY | `bundle_cmdstream.py` | 录像 | `NEW-AT-TINYFEE` | 2% / 1%（上界） | 反向：赢 6%，输 2% |
| BOATLOW | `bundle_cmdstream.py` | 录像 | `NEW-SE-BOATWASTE` 的一部分 | 50% / 14%（各局中位 9% / 12%） | 反向：赢 88%，输 18% |
| LAG180、SLOW | `bundle_patterns.py` | 日志 | `NEW-IO-LAGLOSS` | 107 局里 51 局 | 赢 33%，输 39% |
| SHARE1530 | `bundle_patterns.py` | 快照 | 抢地期落后（§1.1 第 2 步） | 中位 0.60 | 赢 0.69，输 0.55 |
| SPAWNGAP | `bundle_patterns.py` | 日志 | `NEW-SP-DISC` | 中位 1.04 | 赢 1.08，输 1.03 |
| SEALED、FLAT600 | `bundle_patterns.py` | 快照 | `NEW-EC-LANDLOCK`、`NEW-AT-STANDOFF` | 39% 的快照 | 反向：赢 64%，输 43% |
| OVER100、CAP150 | `bundle_patterns.py` | 快照 | `NEW-EC-LANDLOCK`、`NEW-DN-CAPLOOP` | 24% 的快照；33 局 | 没有区分力（17% 对 17%） |
| STACK70 | `bundle_patterns.py` | 快照 | `NEW-AT-PARTALLIN`、`NEW-DF-THIN` | 其后出局 34% / 同局同拍对照 12% | 赢 8%，输 38% |
| REJ | `bundle_patterns.py` | 日志 | `NEW-DN-QUOTABLIND` | 64% 的调度行 | 赢 42%，输 76% |
| COLLAPSE | `bundle_patterns.py` | 快照 | `NEW-DN-HOLLOWREAR`、`NEW-DF-NORESCUE` 的结局 | 41 局 | 赢 0 局，输 37 局 |
| SPLIT、LEFT | `bundle_patterns.py` | 对局卡、结果表 | `NEW-EX-SPLITTEAMS`、`NEW-EX-LEAVER` | 36 局；47 局 | — |

`bundle_join.py` 把两张逐局表拼起来算局间的秩相关和偏相关（§3.1、§7.3 引的那几个数）。

**这些检测器数不到的。** 留兵底线、单价闸、出兵守卫的锁、弃子判定、一拍一条被挤掉的买地指令——这几类都要知道「策略当时想发什么」，只能靠影子策略在真引擎状态上重跑，全量上没有做（13 局的数在 §3.2、§3.4 的表里）。延迟的逐条数字也要影子，全量上只有成摞占比和时钟相差两个代理量。

**对照组怎么取的。** 同一局里既不是本编队的号、也不是另一支本方编队的号的真人位。另一支本方编队的号（A 组房间里的 c110、B 组房间里的 `[APEX]`）单独数、不进对照；名字撞进 c110 名池的真人也被划出去（宁可少算对照）。对照只说明「这不是同一局里人人都有的现象」：真人手点和程序发令本来就不同。

**数据缺口。** 123 局里 16 局没有录像（B001~B003、B005~B007 和 G 组的 10 局），8 局 c110 的录像只有开头；计入的 99 局里有 13 局 c110 的录像没录到终局。c110 的日志不打印选点坐标（SPAWNGAP 算不了）；`likelyRejected` 标记在 c110 上不准。`validation_bundles/` 的 37 局没有动，留给验证用。
