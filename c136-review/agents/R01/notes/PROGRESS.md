# R01 进度与工作笔记（给自己接续用）

## 状态
- M1 完成：A057、A059、A094；M2 完成：A055、A075、A054。全部通过本地机械检查（`python3 scripts/check_my_review.py`）。
- M3 进行中：A031（never-grew）、A019（mid-collapse）完成；下一步 A009（Va），做完发 m3-reviews 报告。其余见下方「逐局进度」。
- M2 报告 `outbox/0006-m2-reviews.md` 里 A075 的判定数写错了（写成 11/4/5），实际是 错 10 / 不清 5 / 对 5，M3 报告里要更正。
- 总部 0006：所有 node 重演/影子命令必须 `bash ../../tools/run-heavy.sh node scripts/...`（在 agents/R01 下），串行、一次一局，结果缓存在 out/。

## 每局流水线
1. `bash c136-review/tools/run-heavy.sh node scripts/resim.mjs <mid> [--replay 同局A包] [--log 包1,包2] [--bots a,b]`：整局重演，和日志 [HL-TICK] 逐号核对。
2. `run-heavy.sh node scripts/shadow.mjs <mid> [--bots ..] [--pin-no-full --tag nf0] [--probe bot:t0:t1 --tag x]`：把重演的每拍状态喂给部署的策略原文。
   默认 isNoFullSend 检查窗口 = 发令拍 +2..+7（`--pc-shift 1 --pc-end keep`），三局全对。
3. `resim_report.py --section meta,timeline,percap,bots,events,pairs,transfers,front,spawn,drops`；
   `shadow_report.py --section check,lagcurve,chunks,bursts,paths,repeat,donate,idle`（idle 里有价格线细分）；`shadow_diff.py <mid> nf0`。
4. `burst_audit.mjs`、`dispatch_audit.mjs`、`tick_cost.py`、`q.py <mid> <表> --where .. --show ..`。
5. 手写 `analysis/<mid>.json` → `build_review.py <mid>` → `check_my_review.py <mid>`（md ≤150 行）。
- 没有录像的实例（A094 的 X、A005）：`log_only.py`（spawn/squad/idle/dispatch/results/drops/share/late/chain）、`log_sync.py`；
  build_review 的 `timelineLog` 从日志填时间线，`timelineSpecB` 给第二个实例另填一张表。
- 总部共享工具：`/agent/repos/c136-data/src/tools/engine_replay.cjs`（真引擎）、`engine_vs_resim.py` 对比。
- `match_facts.py`（M1 的旧底稿脚本，读 bundle）的按席位对账在混了两个实例的包上不能用（A094）。
- M2 新增（都读 out/<mid>/）：`recon_facts.py --section dispatch,husk,slot,safe,ainb,doomed,peak [--siege bot:t0:t1]`（对账一节的汇总数）、
  `probe_view.py`（探针按决策拍一行）、`death_ledger.py`（阵亡号的最后一围）、`exchange_price.py`/`target_price.py`（换地与公式价）、
  `boat_fight.mjs`（海战）、`sea_landings.mjs` + `landing_math.py`（敌方登陆）、`map_ascii.mjs`（字符地图）。
- M3 新增/改动：`probe_view.py <mid> --tag x --gate <席位>`（把 buyLand 的闸门链整条复算：预算、价格 keep、safeAt 封顶、avail、20% 线、最小出兵量；
  nearCollapse 的 85 倍封顶和 isSoleHealthyBuffer 没算）、`recon_facts.py --section drops,leave`（results.csv 的离场拍 vs 录像 leave 拍）、
  `resim_report.py --section percap`（带密度）、`afk_gap.py`（leave 前的静默拍数；没有 leave 的席位的最大指令间隔）。
- A019 新增：`cmd_gaps.py <mid> [--min 60] [--bots]`（全队指令断档：连续 N 拍没有任何本队指令落地的窗口，对照窗口内受理条数、其他玩家落地条数、断档后 70 拍的批次）、
  `decay_check.py <mid> --cases bot:t0:t1 --kill 席位:拍`（挨打时余额按领土的 1.6 次方掉；吃到阵亡线的算式价 ≈ 1.8×对方余额，与策略的 need 对得上）；
  `shadow_report.py --section check` 多一行“差异是否只在船计数”；`resim_report.py --section ledger` 不再把离场壳的船算进出海两项（boat_trace 对壳的 balBefore 不可靠）。
- 影子对 boatTo 的受理比真实客户端宽（A019：影子 42 条、日志 10 条），**船指令的“受理”不能引用**；进攻、捐兵两类与日志 cmds 计数一致。cmd_gaps、lagcurve、flow 都不含船。
- 批次落地的兵不都是净损失：打无主地（目标已死改打无主地、pct=47 中立令成批）的兵在进攻结束后流回余额；写“实扣”时要分开打真人和打无主地
  （`q.py <mid> shadow_match --where "... n>=3" --agg sum:spent --by targetName`）。
- 引擎规则备忘：阵亡 = 领土 ≤ 峰值/4（game.js aliveTick L1298–1312，峰值每拍回落 max(1, 差/1000)），剩下的地和兵清零；
  进攻每格 2 + 2×def，def ≈ 1.6×守方密度；海战 boats.js fightBoats L328–357；登陆 landAt L262–287 不需要陆地接壤。
  守方每丢一格同时被打掉 def 的兵（damage L1062–1074）→ 余额 ∝ 领土^1.6；吃到阵亡线总价 = 2×(L0−峰值/4) + 2×B0×(1−(峰值/4/L0)^1.6) ≈ 1.8×B0。
  海上有船时 collapse 不清号（L1316–1330）：地、余额、峰值清零，船靠岸后重来（A019 sora_w）。捐款手续费 = 捐出方余额×64/1024，与捐多少无关（donate L404–416）。
  expandNeutral：t < dpEnd(1500) 只走 dpNeutral；之后走 General.expandNeutral L944–953，线上兵不够就每个决策拍补一条 pct=47。
- Vb buyLand 非真人目标：safe = min(safeAt, 88×L)（L5414–5418）→ keep = max(keep, safe)（L5444）→ avail ≤ 0 continue（L5446–5447）→ x < want 且 x < chunk(0.2)×B 不发（L5449–5453）。

## 重演核对（ok/bad）
A057 1324/0（含 B038）；A059 290/0；A094-Y 86/0（--bots ryan_m,zexos1,noah88）。
旧结果（船落点修正前，开工时重跑）：A055 539/0；A075 286/2；A054 652/0；A031 464/0；A019 505/0；A009 406/0；A023 515/1；A050 499/0；
A003 339/0；B039(--replay A058 --log B039,A058) 743/0；B043(--replay A062 --log B043,A062) 860/2。A005 缺地图，只能 engine_replay 或 log_only。

## 版本对应（总部 0002）
- Va（A003/A005/A009）：`v27-team-c116-va.js` + `spawn-coordinator-c116-va.mjs`
- Vb（其余 A 局）：`v27-team-c116-vb.js` + `spawn-coordinator-c116-vb.mjs`
- B039/B043：`v27-team-c110.js` + `spawn-coordinator-c110.mjs`

## Vb 代码地图（行号）
General.act L752–810（L796 打 AI）；Style.pickTarget L1144–1177；V13.dpNeutral L2383/L2406；V13.floorFor0 L2233；V13.safeFinite L2500–2510；
Policy.updateShadowQuota L3800–3835；Policy.send L3838–3925（L3844 闸门）；tryDonateToTeammate L4325–4517（L4331 每 25 拍、L4343 被打不捐、
L4355 boxedIn、L4382–4388 两条底线、L4418 受赠者密度上限 142/115、L4455 doomed、L4463–4473 协防、L4479–4481 收益调度、L4500–4506 pct）；
Policy.winFloor L4562；Policy.act L4801…（L4941 expandNeutral、L4942 buyLand、L4962 捐款只在本拍没发令时）；Policy.offers L5072–5340；
Policy.buyLand L5342–5619（L5358 价格线、L5361–5365 唯一健康缓冲、L5440–5443 over 留兵、L5449–5453 打 AI、L5611–5616 满预算）。
参数：maxW 0.5，winT→2500 拍后 1.8（m=0.9），hold 0.9，marketFloor 0.85，overHumanCap 1.28，pulseFrac 0.12，quotaGuardMode 1。

## 模式编号（提议，跨局复用）
SP01 密集阵/被队友围住 | SP02 出生名单跨实例 | OP01 DP 开局(对) | OP02 保底线死锁 | IO01 掉队期间照常下令 | IO02 过期指令成批落地 |
IO03 isNoFullSend 误置真 | AT01 12% 脉冲(对) | AT02 零星中立令占名额 | AT04 开战首击 | AT05 价格线空等 | AT06 中期吃 AI 地(对) |
EC01 内陆围死满仓 | EC02 小邻居卡住后排大号 | DN01 后排输血(对) | DN02 截断捐款 | DN04 给必死队友捐 | DN05 配额拒单 | DN06 低密度给高密度 |
DN07 互捐 | DF01 被大号陆攻 | DF02 挨打不出手 | EG01 领先时自退。
M2 新增：SP03 出生方案反复改写/同像素 | OP03 1500 拍前对真人的保底线 | IO04 正常延迟内重复下令 | IO05 过期捐款/船令成批落地 |
AT07 最小出兵量闸门 | AT08 过 100 倍后不看价格 | AT09 离场壳的 88 倍保底线 | DF03 safeAt 高于余额 | DF04 不接壤对手海上登陆 |
DN08 后排捐空后被打 | DN09 幽灵前线 | DN10 为利息而捐净负 | SE01 远程船耗光占船位 | SE02 短程船重开前线(对) | SE03 船落在队友岸上 |
SE04 装兵比手续费少的小船 | SE05 远程船被拦截船打沉。
M3 新增：AT10 身边的离场壳按预算吃掉(对) | DN11 两波进攻之间把兵捐走 | EG02 8500 拍前被 leave 指令移出对局（不出自策略）；IO01 在 A031 补了定义；
AT11 单价过了价格线但预算不到余额 20%（buyLand L5611–5616），对真人不出手（A019 riku_x）。AT08 在 A019 有一处判“对”（延迟正常时吃 Player 917）、一处判“错”（断档时清仓）。

## 逐局进度
- [x] A057（never-grew）
- [x] A059
- [x] A094（lead-thrown；两个实例）
- [x] A055（outscaled）  - [x] A075（win）  - [x] A054（mid-collapse）   （M2）
- [x] A031（never-grew）  - [x] A019（mid-collapse）  - [ ] A009   （M3）
- [ ] A023  - [ ] A050  - [ ] A003   （M4）
- [ ] A005  - [ ] B039  - [ ] B043   （M5）
- [ ] M6：reports/CROSS-MATCH-SUMMARY.md、全量模式计数脚本、cards/
