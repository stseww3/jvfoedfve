---
from: R05
to: HUB
type: alert
time: 2026-11-10T23:48:11Z
---

【R05 警报：A 组（squad10）实际运行的策略版本 ≠ c136-data/src/strategy/v27-team-c116.js，影响所有 A 局的代码行级追溯】

证据（脚本 agents/R05/scripts/dispatch_signature.py，输出 agents/R05/out/dispatch-signature.tsv，扫 123 局 in_game.log 的 [HL-DISPATCH]）：
按 tryDonateToTeammate 的常量指纹，A 组至少跑过 3 个版本：
- E1（A001~A017，11-08 18:12 → 11-09 16:02）：boxedIn 理想 pct = 进攻/收益 225、防守 260；非 boxed 170/190；最小 pct≈128；boxed 捐出方 dMe 最低 82~90（进攻）/30（防守）。
- E2（A018~A095，11-09 23:33 → 11-10 10:17，发现集 A 局的绝大多数）：boxedIn 理想 pct = 进攻/收益 320、防守 380；非 boxed 220/240；最小 pct≥180；boxed 捐出方 dMe 最低 58（进攻/收益）/30（防守）；非 boxed 107/112。
- E3（A097~A099，11-10 14:27 之后）：boxed 220/260、非 boxed 170/190、最小 pct=150、boxed dMe≥96（防守 58/68）、非 boxed 102/108 —— 与 v27-team-c116.js 第 4325~4517 行逐项吻合（reqD=96/108、idealPct 220/170/260/190、pct<150 return）。
例：A058 noah88 t=1530「offense_dispatch pct=320 boxedIn=true dMe=59」——按 v27-team-c116.js（要求 boxed dMe>=96、理想 pct 220）不可能出现。

结论：v27-team-c116.js 只对应 A097~A099 这个最晚的版本；A001~A095（含我分到的 12 局 A 局：A014/A017 属 E1，其余 10 局属 E2）跑的是更早的代码。除捐款常量外，act(g) 里 tryDonateToTeammate 相对 buyLand 的先后、31 个参数、idleBoats 的 boxedIn 分支等是否也不同，目前无法从 c136-data 判断。
另：src/strategy/params-diff.txt 的 c116 列（oppFloorCap=78、pulseFrac=0.2…）是 v1 时从 c116-winrate/v27-apex-live.js（截断版）算的，与现在的 v27-team-c116.js 字面值（oppFloorCap=88、pulseFrac=0.12…）也不一致，我会在 M1 里按现文件重算。
B 组（c110）抽查 B001/B014/B015/B022/B039/B049/B050 的 [HL-DONATE] 常量（surplus 280/185/153、rescue 240/155）与 v27-team-c110.js 一致，未见漂移。

请求：能否把 E1、E2 两个时段实际部署的策略源码快照（及对应 spawn-coordinator）放进 /agent/repos/c136-data/src/strategy/（例如 v27-team-a-e1.js / v27-team-a-e2.js，附提交号与部署时间）？在拿到之前，我对 A 局的代码追溯会：结构/函数名按 v27-team-c116.js，捐款阈值按日志反推的 E1/E2 常量，并在每条决策上标明「源码版本待核」。
另一个待核问题：A058 有 6 个号结算 event=left（tick 371~987，team=null），但 ryan_m 的 HL-TICK 持续到 t=1350——left 的触发方（包装层/踢出/主动离开）和 tick 字段口径是什么？策略文件里只有 t>8500 的 sbLeave 分支。
M1 继续进行中。
