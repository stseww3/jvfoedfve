# R01 假设卡索引

每张卡的结构相同：假设、机制（源码函数和行号）、证据（15 局逐局 + 全量计数）、怎么数（可重跑的命令）、什么结果算证伪、没弄清的。全量的数只计“是同一场对局”的 108 个包（见 D01）；数字出处是 `reports/m6-data/` 里的表，`bash scripts/m6_run_all.sh` 一次重算全部。

卡里只有现象、机制和证据，没有补丁和参数建议。

| 卡 | 说的是什么 | 把握 | 全量怎么数 |
|---|---|---|---|
| [D01](D01-bundles-not-one-match.md) | 15 个包不是同一场对局（10 个平行两场，5 个先后两场或录像对不上） | 高 | `m6_match_split.py` |
| [H01](H01-channel-lag.md) | 指令通道：页面从本地 600 拍前后落后于服务器，令晚到、成批到或不到 | 现象和代价 高；原因 未知 | `m6_all_replay.py`、`m6_all_coload.py` |
| [H02](H02-stale-batches.md) | 过期的令成批落地，按落地时的余额连续扣，等于清仓 | 高 | `m6_all_replay.py`（batches） |
| [H03](H03-repeat-in-confirm-window.md) | 正常延迟内对同一目标重复下令，首击被叠成几倍 | 中 | `m6_all_replay.py`（repeats） |
| [H04](H04-spawn-layout-churn.md) | 出生落点表在出生阶段反复改写，收场的阵是几份表拼出来的 | 现象 高；对胜负 低 | `m6_all_replay.py`（solves、layouts、samePixelPairs） |
| [H05](H05-spawn-footprint.md) | 出生阵型太挤：名下的天然地盘只有人头占比的六成 | 高 | `m6_all_land.py` |
| [H06](H06-floor-lock-before-1500.md) | 1500 拍前对 AI 地的保底线取到了队友的余额 | 机制 高；值多少格 低 | 影子（`shadow.mjs`）；全量只有代用量 |
| [H07](H07-dispatch-over-quota.md) | 捐兵调度过不了反喂养配额：3213 拍前九成被拒 | 高 | `m6_all_traj.py`（q1–q3） |
| [H08](H08-boxed-rear-seats.md) | 1500–3000 拍四成的快照里这个号没有可打的对象 | 现象 高；和结果 低 | `m6_all_traj.py`（boxed） |
| [H09](H09-no-full-send-false-positive.md) | `isNoFullSend` 误置真，之后对人的令被自己的闸门扣下 | 机制 高；总代价 中 | 影子（`shadow.mjs --pin-no-full`） |
| [H10](H10-fee-on-whole-balance.md) | 手续费按下令方的全部余额收：小额捐兵和小船是净亏 | 规则 高；多亏多少 中 | `m6_donations.py`、`m6_boats.py`、`m6_all_traj.py`（smallPct） |
| [H11](H11-concentrated-strikes-and-sea.md) | 对手把兵集中到一两个号一波打穿；一半的登陆来自不接壤的对手 | 现象 高；保底线为什么挡不住 中 | `sea_landings.mjs`、`m6_all_traj.py`（drops） |
| [H12](H12-seats-removed-by-leave.md) | 席位被 leave 移出对局：集中在通道差的局，拍号落在 112 拍的格子上 | 现象 高；谁发的 未知 | `leave_grid.py` |
| [H13](H13-donations-to-husks-and-doomed.md) | 捐兵的对象不查守不守得住：必死的号、离场的壳、撞名的路人 | 高 | `m6_all_replay.py`（donToLeft）、`m6_all_traj.py`（doomed） |
| [H14](H14-idle-with-target.md) | 有对象而不出手：价格线、保底线、唯一真人邻居三道门 | 现象 高；该不该出手 低 | `m6_all_traj.py`（idleTgt）；影子探针 |
| [H15](H15-send-cap9-first-kept-last-run.md) | 通道的三条规则：每席位每拍 9 条；一串令里先发的 9 条留下、其余丢掉；同拍的令后发的先执行（出生指令也是） | 规则 高；闸在哪一层 未知 | `m6_channel_buffer.py` |

## 这些卡之间的关系

- 通道（H01）是最大的一项，它带出 H02（成批清仓）、H12（席位被移出），也让 H03（重复下令）在通道干净的局里才显出来。原因不在策略文件里，包里看不出来。
- H15 是 H01、H02、H04 共用的底层规则：掉队的页面停一段再连着算，这一串里只有最旧的 9 条令进对局、同拍倒序结算；出生指令同样倒序，所以同一步里留下的是旧表的点。模拟器的通道模型按它写（逐条轨迹 `reports/m6-data/channel_trace.csv`、`channel_bursts.csv`）。
- 落点（H04、H05）决定名下有多少地；H08（围死）是它在 AI 地分完以后的样子；H07（配额）让围死的号的兵送不出去。
- H06、H09、H14 是策略自己的闸门：各自有源码行，逐拍可在影子里复现，但值多少格都缺对照。
- H10、H13 是捐兵和船的两类净亏。H11 是对手的打法。

## 核对

```bash
python3 scripts/m6_build_report.py --check-file cards/*.md   # 卡里 ≥4 位的整数都能在数据文件、逐局报告、analysis 里找到
```
