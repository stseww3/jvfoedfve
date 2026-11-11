# R01 进度与工作笔记（给自己接续用）

## 状态
- A057：复盘完成并通过本地机械检查（`python3 scripts/check_my_review.py A057`）。
- 其余 14 局：见下方「逐局进度」。

## 工具链（都在 scripts/）
- `resim_lib.mjs` + `resim.mjs <mid> [--replay 同局A包] [--log 包1,包2]`：整局逐拍重演（512 席位），与日志 [HL-TICK] 逐号核对。
  - 关键修正：团队局颜色初始化取 512 个随机数（否则 AI 出生点全错位）；队伍分配按引擎 `bj.ee()` 移植。
  - 核对结果（ok/bad，首个偏差拍）：A059 290/0；A055 539/0；A075 286/2(6480)；A054 652/0；A031 464/0；A019 505/0；
    A009 406/0；A023 515/1(5670)；A050 499/0；A003 339/0；B039(--replay A058 --log B039,A058) 743/0；
    B043(--replay A062 --log B043,A062) 860/2(6300)；A057(--log A057,B038) 963/361，t<=4130 全对。
  - A094：日志与录像不是同一盘（从 t=90 起全错）；A005：缺地图 `5_9294.bin.gz`，不能重演。
- `resim_report.py <mid> --section meta,timeline,bots,pairs,transfers,events,top,front`：把重演表整理成数字。
- 旧工具：`match_facts.py`、`lag_probe.py`、`cmd_audit.py`、`donation_ledger.py`、`econ_check.py`、`boat_landings.py`、
  `team_infer.py`、`dispatch_survey.py`、`replay_cmds.mjs`、`check_my_review.py`。

## 版本对应（总部 0002）
- Va（A003/A005/A009）：`v27-team-c116-va.js` + `spawn-coordinator-c116-va.mjs`
- Vb（其余 A 局）：`v27-team-c116-vb.js` + `spawn-coordinator-c116-vb.mjs`
- B039/B043：`v27-team-c110.js` + `spawn-coordinator-c110.mjs`

## 模式编号（提议，跨局复用）
SP01 密集阵压低人均中立地 | OP01 DP 开局一租期一令(对) | OP02 中立吃完后有邻居却零指令 | IO01 指令晚到/被丢 |
EX01 客户端落后后成批离场 | AT02 对零星中立像素重复下最小指令 | EC01 内陆封死满仓 | DN01 后排输血给唯一前线(对) |
DN02 受赠者快满仓时截断/作废 | DN04 给必死队友协防捐款 | DN06 低密度号给高密度号输血 | AT01 12% 脉冲持续推进(对) |
DF01 被余额高一个量级的对手陆攻 | EG01 本队领先时自退。
预留：DN03 上限作废、DN05 配额拒绝(t<4284)、EG02 标签与队伍结果不符、EX02 离场壳自动捐款、SE01 满仓不出海。

## 给总部的汇报要点（M1 报告里带上）
1. 重演工具与核对结果；A057 4140 起偏差原因未查到；A094 混盘；A005 缺地图。
2. 离场人类号自动捐款（kq）、船靠队友岸免税捐款、队数<8 时 AI 不入队、无边界进攻令入录像但不扣兵。
3. `likelyRejected` 不可靠，录像指令流才是真值。
4. 协议 `team-split` 与检查器 `external` 不一致；md 行数上限 160。
5. 捐款候选只认编队号/boss：被本队活人围死的后排无处输血（A057）。

## 逐局进度
- [x] A057
- [ ] A059
- [ ] A094
