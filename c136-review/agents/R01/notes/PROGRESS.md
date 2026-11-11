# R01 进度与工作笔记（给自己接续用）

## 状态
- M1 完成：A057、A059、A094；M2 完成：A055、A075、A054。全部通过本地机械检查（`python3 scripts/check_my_review.py`）。
- 下一步 M3：A031、A019、A009（A009 是 Va）。其余见下方「逐局进度」。
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
- 引擎规则备忘：阵亡 = 领土 ≤ 峰值/4（game.js aliveTick L1298–1312，峰值每拍回落 max(1, 差/1000)），剩下的地和兵清零；
  进攻每格 2 + 2×def，def ≈ 1.6×守方密度；海战 boats.js fightBoats L328–357；登陆 landAt L262–287 不需要陆地接壤。
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

## 逐局进度
- [x] A057（never-grew）
- [x] A059
- [x] A094（lead-thrown；两个实例）
- [x] A055（outscaled）  - [x] A075（win）  - [x] A054（mid-collapse）   （M2）
- [ ] A031  - [ ] A019  - [ ] A009   （M3）
- [ ] A023  - [ ] A050  - [ ] A003   （M4）
- [ ] A005  - [ ] B039  - [ ] B043   （M5）
- [ ] M6：reports/CROSS-MATCH-SUMMARY.md、全量模式计数脚本、cards/
