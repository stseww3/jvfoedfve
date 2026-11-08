# S09 单局显微镜解剖与核心变量量化报告

- **更新时间**: `2026-11-08T03:00:00Z`
- **包干对局**: `G01 (00:30, 6-team, Team 4 Peak #1 -> lost to Team 6), G02 (00:35, 6-team, Team 2 -> lost to Team 1), G03 (00:41, 4-team, Team 3 -> lost to Team 1), G04 (00:50, 3-team, Team 1 Peak #1 at t=5422 -> lost to Team 2), G05 (00:54, 6-team, Team 2 -> lost to Team 5), G06 (01:01, 5-team, Team 1 3-bot survival / 160.5k squad land -> over to Team 4), G07 (01:07, 2-team, Team 2 -> won 545,700 land), G08 (01:13, 6-team, Team 1 7-bot entry -> over to Team 5), G09 (01:28, 5-team, Team 2/3 split 6-bot entry -> over to Team 1 at t=14666), Historical Boss-Guard Batch (M05 & M11, 22:52~23:23 CST) + 100-game fdvg Live Corpus (mw5skhsn-40hbid, mw5tbhq8-coknnx, etc.)`
- **负责核心变量**: `V11, V12`

## 一、单局时间线、胜负拐点与核心死因解剖

### `G01` (`result=lost`, `6` 队局, 进场 `8` 号, 主陆 `8` 号)
- **`t=1500` 团队领土**: `104930` | **峰值领土**: `151096` (`@t=5139`) | **崩盘拐点**: `t=4950`
- **拐点前线密度 vs 敌方密度**: `d_front = 7.1` vs `d_enemy = 115.0`
- **第一主因**: `V11` | **第二诱因**: `V7`
- **逐拍取证摘要**: At t=1620..4230, 5 of 8 bots crashed on `TypeError: rnd is not a function` in `tryClaimNearTeamIslands`. At t=4230, `[HOT-IMPORT]` revived all 8 bots (squadL=121,611, squadB=11.22M, avgD=92.3, ryan_m d=107.5). Immediately, `oppFloorCap=38` + `totB=B+myOut` + `isPrimeLand keep<=10*L` caused `ryan_m` to dump 3.25M troops between t=4320..4500 (density crashed 107.5 -> 16.5 -> 14.6) and again at t=4950..5040 (13 commands in 90 ticks, density crashed 23.9 -> 7.1 while opening nb=1 -> 4 enemy fronts). Even as Team 4 held #1 (151,096 land vs Team 1 132,955 and Team 6 113,174 at t=5139), `kevin_k` (t=5280..5292, 7x 10%B pokes) and `ethan21` (t=5450..5460, 6x 10%B pokes) machine-gunned enemy #8 every 2 ticks due to missing cooldown in `tryDonateToTeammate`, hollowing the entire squad for Team 6's counter-sweep.

### `G02` (`result=lost`, `6` 队局, 进场 `8` 号, 主陆 `4` 号)
- **`t=1500` 团队领土**: `80132` | **峰值领土**: `84451` (`@t=2356`) | **崩盘拐点**: `t=1800`
- **拐点前线密度 vs 敌方密度**: `d_front = 5.0` vs `d_enemy = 88.0`
- **第一主因**: `V1` | **第二诱因**: `V12`
- **逐拍取证摘要**: In a 6-team 61-human lobby (Map 22, 664,497 land), pre-`d590acd` `findVirtualSquadAnchor` failed to anchor on a single main continent: 4 of 8 bots (`ryan_m`, `ethan21`, `mark07`, `noah88`) fell into the fallback loop (`voronoiPixels=500`, `minAllyDist=609..653px`) scattered across opposite map corners. Isolated frontline bot `ryan_m` fired 183 commands by t=1530 (`d=2.5`, `nb=4`) and died at t=2356 with Team 2 holding only 84,451 land (12.7%) against Team 1's 204,109.

### `G03` (`result=lost`, `4` 队局, 进场 `8` 号, 主陆 `8` 号)
- **`t=1500` 团队领土**: `60318` | **峰值领土**: `73102` (`@t=2024`) | **崩盘拐点**: `t=1980`
- **拐点前线密度 vs 敌方密度**: `d_front = 4.4` vs `d_enemy = 92.0`
- **第一主因**: `V2` | **第二诱因**: `V6`
- **逐拍取证摘要**: All 8 bots spawned in a tight cluster (`minSep=48..114px`) on Map 17 (292,727 land), boxing in 3 inner bots (`kevin_k`, `noah88`, `dave_w` with `nb=0`) while outer guards `leo_tx` (`d=4.4, nb=4`) and `mark07` (`d=4.6, nb=3`) over-expanded at t=1980. Furthermore, `ethan21`, `leo_tx`, `ryan_m`, and `noah88` triggered 32 unthrottled `[HL-ASSIST]` 10%B pokes (7 pokes in 12 ticks at t=2794..2806, 5 at t=3396..3404, 14 at t=4482..4550) against enemy #57 (`Russian Empire [OG]`), draining frontline balances while 3 boxed-in rear bots sat at `d=71.7..76.0` (below the `dMe >= 132` non-inland donation gate because they had coastline).

### `G04` (`result=lost`, `3` 队局, 进场 `8` 号, 主陆 `6` 号)
- **`t=1500` 团队领土**: `60868` | **峰值领土**: `248433` (`@t=5422`) | **崩盘拐点**: `t=6660`
- **拐点前线密度 vs 敌方密度**: `d_front = 27.8` vs `d_enemy = 118.0`
- **第一主因**: `V11` | **第二诱因**: `V5`
- **逐拍取证摘要**: Classic #1 lead throw in a 3-team game: Team 1 held #1 at t=5422 with 248,433 land (45.5% of map vs Team 2's 226,797 and Team 3's collapsing 66,931). Between t=1920..6640, `noah88` and `kevin_k` launched 61 `[HL-INTERCEPT]` chase boats (burning 90 total boats and >1.8M troops/tax, often double-chasing the exact same `boatId` on the same tick). Worse, `leo_tx` (27,199 land, boxed-in coastal rear with `nb=0` from t=2520 to t=6570) was bled every 18 ticks down to `d=70~76` by `tryDonateToTeammate` instead of compounding to `140*L`. At t=6570..6660, `noah88` (`20,018L`) and `lucas94` (`18,092L`) over-pulsed collapsing Team 3 remnants (`noah88` fired 18 commands in 90 ticks, crashing density `96.9 -> 33.8`; `lucas94` dropped `32.0 -> 27.8` with `nb=3`, plus `noah88` fired 14 unthrottled 10%B `[HL-ASSIST]` pokes at t=6594..6622). Team 2 counter-attacked their `d=27.8~33.8` frontline at t=6660 and swept `lucas94` (t=6988), `leo_tx` (t=7237), and `noah88` (t=7404).

### `G05` (`result=lost`, `6` 队局, 进场 `8` 号, 主陆 `4` 号)
- **`t=1500` 团队领土**: `51425` | **峰值领土**: `35169` (`@t=2417`) | **崩盘拐点**: `t=1620`
- **拐点前线密度 vs 敌方密度**: `d_front = 0.9` vs `d_enemy = 82.0`
- **第一主因**: `V1` | **第二诱因**: `V12`
- **逐拍取证摘要**: In a 6-team 55-human match on Map 22 (664,497 land), 4 of 8 bots (`ryan_m`, `leo_tx`, `ethan21`, `noah88`) hit the `voronoi=500` scattered fallback (`minAllyDist=573..594px`). Squad land at t=1530 was only 51,425 (7.7% of map), and by t=2417 Team 2 held just 35,169 land (5.3%, 6th of 6 teams) before being eliminated by t=3890.

### `G06` (`result=over`, `5` 队局, 进场 `8` 号, 主陆 `8` 号)
- **`t=1500` 团队领土**: `101273` | **峰值领土**: `160523` (`@t=4230`) | **崩盘拐点**: `t=4410`
- **拐点前线密度 vs 敌方密度**: `d_front = 16.6` vs `d_enemy = 122.0`
- **第一主因**: `V11` | **第二诱因**: `V6`
- **逐拍取证摘要**: All 8 bots spawned cohesively on Map 24 (`762,763` land, `voronoi=10,199..24,956`, `minSep=112px`), reaching `160,523` squad land (21.0% of map, `8.83M` troops) at t=4230..4320. However, 5 bots (`ryan_m`, `leo_tx`, `lucas94`, `mark07`, `dave_w`, holding 74,240 land = 46% of squad territory) were 100% boxed-in (`nb=0`), leaving ONLY `ethan21` (`47,231L`) and `noah88` (`9,273L`) on the frontline. Because the 5 rear bots had coastline (`hasExposedCoast=true`), `tryDonateToTeammate` treated them as `isPureInlandSafe=false` (`dMe >= 132` required for general surplus donate, or `dMe >= 106` only when an ally had `inHumanAtk >= 12%B`), so all 5 rear bots sat frozen at `d=70.8~77.7` while `ethan21` fought alone at `d=14.3~23.1` (`oppFloorCap=38` + `totB=B+myOut` + `keep<=10*L`). Simultaneously, `kevin_k` and `noah88` fired 63 `[HL-INTERCEPT]` boats (102 total boats), draining coastal balances. When Team 4 (377k->526k land) breached `ryan_m` at t=4410..4611, our 5 medium-density rear bots were eaten one by one in a domino cascade (`t=4611, 4935, 5219, 5383, 5464`).

### `G07` (`result=won`, `2` 队局, 进场 `8` 号, 主陆 `6` 号)
- **`t=1500` 团队领土**: `53877` | **峰值领土**: `545700` (`@t=5405`) | **崩盘拐点**: `t=3157`
- **拐点前线密度 vs 敌方密度**: `d_front = 22.6` vs `d_enemy = 45.0`
- **第一主因**: `V12` | **第二诱因**: `V6`
- **逐拍取证摘要**: Positive control (sole win, 2-team 59-human match on Map 10, 546,152 land): because `teamCount=2`, our Team 2 had ~29 players (8 `[Nope]` bots + ~21 human allies = 50% of lobby). Even when our frontline bot `ryan_m` over-expanded at `d=1.1~5.8` and died at t=3157 (`noah88` also disconnected `1006` at t=3437), Team 2 already held 304,624 land (55.8%) vs Team 1's 237,551. Surviving bots `lucas94` (17,077L, boxed-in `nb=0` compounding to `d=121.2`), `mark07` (6,977L), and `kevin_k` (1,412L) donated 24 times to frontline allies as Team 2 swept Team 1 to 545,700 land (99.9%) at t=5405.

### `G08` (`result=over`, `6` 队局, 进场 `7` 号, 主陆 `7` 号)
- **`t=1500` 团队领土**: `72068` | **峰值领土**: `85548` (`@t=2070`) | **崩盘拐点**: `t=3782`
- **拐点前线密度 vs 敌方密度**: `d_front = 10.7` vs `d_enemy = 112.0`
- **第一主因**: `V12` | **第二诱因**: `V7`
- **逐拍取证摘要**: Only 7 of 8 bots entered (`noah88` missed room entry due to `headlessInRoom0 >= 7` ready gate + proxy jitter). All 7 bots spawned on the north continent of Map 13 (`430,654` land) and reached `85,548` squad land (19.9% of map, #1 contender in a 6-team game) at t=2070, compounding to `6.07M` squad troops (`avgD=83.7`) at t=3510. At t=3510..3912, `ethan21` dropped to `d=10.7` (`oppFloorCap=38` + `totB`) and `kevin_k`, `lucas94`, `mark07`, `ryan_m` fired 41 unthrottled 10%B `[HL-ASSIST]` pokes across 3 different enemies (`#2 SGX union`, `#18 Turk`, `#41 rubi`), provoking a multi-team coalition from Team 2 and Team 5 that collapsed `kevin_k` (t=4392), `mark07` (t=4630), `dave_w` (t=4638), `ethan21` (t=4942), and `ryan_m` (t=5425).

### `G09` (`result=over`, `5` 队局, 进场 `6` 号, 主陆 `6` 号)
- **`t=1500` 团队领土**: `49636` | **峰值领土**: `59361` (`@t=2012`) | **崩盘拐点**: `t=2012`
- **拐点前线密度 vs 敌方密度**: `d_front = 0.7` vs `d_enemy = 95.0`
- **第一主因**: `V12` | **第二诱因**: `V10`
- **逐拍取证摘要**: Severe V12 lobby/network degradation: only 6 of 8 bots entered (`dave_w` and `noah88` missed entry due to `minStartsIn <= 14 && headlessInRoom0 >= 5` loose gate + proxy socket churn, with 19,956 `socket close` events logged during G09), AND the 6 bots were split by the game server across two opposing teams: Team 2 (`kevin_k`, `mark07`, `lucas94`, `leo_tx`) and Team 3 (`ethan21`, `ryan_m`)! Because `spawn-coordinator.mjs` placed all 6 bots in the exact same northern basin (`y=20..130`), our Team 2 and Team 3 bots fought each other in the opening (`kevin_k d=0.7`, `mark07 d=4.2`, both dying at t=2012..2085; `ethan21` and `ryan_m` dying at t=3609..3827; `leo_tx` disconnecting at t=6685), leaving `lucas94` stranded on an island until t=14666.

## 二、专项核心变量全样本量化与因果机制

### `V11` — MidgameLeadThrowMechanism (中盘领先/峰值第1收口失败与崩盘拐点机制) (预估胜率影响 `+38.5%`)
- **当前劣化值**: `No #1 lead-protection lock; oppFloorCap=38; collapseFloorCap=16; totB=B+myOut; isPrimeLand keep<=10*L..26*L; [HL-ASSIST] 10%B poke has 0 cooldown (fires every 2 ticks); boxed-in coastal rear bots locked at d=70~78 without feeding frontline.`
- **80% 胜率基线值**: `oppFloorCap=128; collapseFloorCap=85; avail=B-fee-keep (home B only); period=5 (280ms); Boss npl acted as centralized high-density frontline anchor receiving steady 5% surplus donations.`
- **推导最优阈值**: `Three Iron Laws of Lead Closing when L_team >= 0.22*L_map or Team Rank == 1: (1) Frontline Home Density Lock: keep_home >= max(68*L, 0.78*safeAt), strictly using B_home (never totB=B+myOut) when humanNbCount >= 1; (2) Rear-to-Frontline Conveyor: any bot with enemyHumanNbs.length === 0 && neutral === 0 (even with coast, if boatN_threat === 0) donates 8%B every 24t above dMe >= 45 directly to the largest/lowest-density frontline brother (nb >= 1); (3) Assist Cooldown & Single-Team Focus Lock: add 60-tick per-bot cooldown on [HL-ASSIST] (`this.lastAssistTick`) + `isBeingAssisted` check, and penalize attacking non-focus enemy teams by 1.35x when leading.`
- **源码级因果机制**: Across both the overnight Team batch (3/8 non-2-team games reached #1 or >140k squad land: G01 151k, G04 248k, G06 160.5k, yet 0/3 converted to a win = 100% throw rate) and the 100-game fdvg v33/v32 live corpus (28 games reached >=100k peak land, 23/28 = 82.1% threw; 16 games reached 150k..200k+ contested #1, 15/16 = 93.8% threw), every midgame throw follows a 3-stage cascade at t=4200..6660: Stage 1 (Frontline Self-Hollowing): `totB = B + myOut` + `oppFloorCap = 38` + `isPrimeLand keep <= 10*L` causes our leading frontline bot (`ryan_m` in G01, `noah88/lucas94` in G04, `ethan21` in G06) to chain-pulse collapsing enemies until actual home density `B_home/L` drops to `7.1 ~ 27.8`. Stage 2 (Rear Hoarding & Assist Bleed): 46%~62% of squad territory is held by boxed-in rear teammates (`nb=0`) sitting on coastlines at `d=70~78` that refuse to donate to the frontline (`!isPureInlandSafe` requires `dMe >= 132`), OR bordering teammates fire unthrottled 10%B `[HL-ASSIST]` pokes every 2 ticks (6~14 pokes in 12~28 ticks!) because `g.hasAttack(me, q)` is still false during the 2~4 tick WebSocket RTT window. Stage 3 (Perimeter Rupture): adjacent enemy mainstays (`d=105~130`) counter-punch the `d < 28` frontline bot, breaking into our low-density rear cluster and wiping 5~6 bots within 600 ticks.
- **源码定位**: `tsb/squad/v27-team-live.js:3921 (oppFloorCap:38), 3963 (collapseFloorCap:16), 4460 & 4851 ([HL-ASSIST] missing cooldown/RTT lock), 4795-4865 (tryDonateToTeammate isPureInlandSafe coastal rear lock), 5848-5856 (totB = B + myOut & isPrimeLand keep <= 10*L)`

### `V12` — LobbyTeamCountAndActiveBots (房间队伍数、有效在场人数、同队率与掉线/报错稳定性) (预估胜率影响 `+31.0%`)
- **当前劣化值**: `Team count K_teams in {2,3,4,5,6} (mean 4.89 teams in G01-G09); activeBots = 6..8 (G08=7, G09=6); G09 split across Team 2 (4 bots) + Team 3 (2 bots); G00 & G01 crippled by `TypeError: rnd is not a function` (499 errors); G00/G04/G07/G09 lost 1 bot mid-game (`left` on 1006/proxy jitter) and 19,956 `socket close` events in G09.`
- **80% 胜率基线值**: `8/8 Headless bots + 1 Human Boss (or 10/10 full squad) verified in Room 0, 100% on the same team, 0 runtime JS exceptions, predominantly 2~4 team lobbies or dominant 9-player squad share (>=20% of lobby).`
- **推导最优阈值**: `Require >= 7/8 (ideally 8/8) bots verified in Room 0 (`headlessInRoom0 >= 7`, remove `headlessInRoom0 >= 5 && minStartsIn <= 14` loose entry that caused G08 7-bot and G09 6-bot entries); in `chooseSpawn` & `isTeammate`, dynamically group by `g.teams[me]` so if server splits squad across 2 teams, minority-team bots do not cluster inside majority-team bots' basin; add socket-1 reconnect backoff to stop 19,956 close loops.`
- **源码级因果机制**: In Team mode with `H` total players (`H ≈ 48..61`) divided into `K_teams` teams, a team's average size is `H / K_teams`. With `N_my` active bots on the same team, our controlled share of our own team is `N_my / (H / K_teams) = (N_my * K_teams) / H`, while our team's baseline prior win probability is `1 / K_teams` (50.0% in 2-team, 33.3% in 3-team, 25.0% in 4-team, 20.0% in 5-team, 16.7% in 6-team). Last night's 9 games had a harsh lobby distribution: FOUR 6-team games (G01, G02, G05, G08), TWO 5-team games (G06, G09), ONE 4-team game (G03), ONE 3-team game (G04), and only ONE 2-team game (G07, which we won). Even more critically, effective bot count `N_eff` (bots alive on the same team without JS crash or mid-game 1006 disconnect) was < 8 in 6 of 10 matches: G00 (8 bots crashed at t=420 on `rnd is not a function`), G01 (5 bots crashed from t=1620 to t=4230), G04 (`ryan_m` crushed to 3px at t=1530), G07 (`noah88` disconnected `left` at t=3437), G08 (only 7 bots entered), and G09 (only 6 bots entered, split 4 vs 2 across Team 2 and Team 3, plus `leo_tx` disconnected at t=6685). When `N_eff = 8` on the same continent (G01 post-hot-import, G06), our squad achieved 136.8k~160.5k land (#1/#2 on map) even in 5~6 team lobbies; when `N_eff <= 6` or scattered (G00, G02, G05, G09), midgame land share collapsed to < 8%.
- **源码定位**: `tsb/squad/tsb-team-squad.mjs:1131 (headlessInRoom0 >= 5 loose ready gate), 1076-1117 (anyMeaningfulAlive / premature leave), tsb/squad/v27-team-live.js:4684 (seaSample Math.random fix in 917e6b1)`

## 三、核心变量权重排序

1. **`V7` (28.0%)**: `oppFloorCap=38` + `totB=B+myOut` + `isPrimeLand keep<=10*L` drained frontline home density to 7.1~27.8 at the exact inflection tick in G01, G04, G06, and G08.
2. **`V11` (24.0%)**: Zero lead-closing protocol when #1 (no frontline density lock, 46%~62% of squad land frozen in coastal rear bots at d=70~78, and unthrottled 2-tick [HL-ASSIST] spam).
3. **`V12` (18.0%)**: 5~6 team lobby prior (6/9 games had 5~6 teams) compounded by G01 `rnd` crash (t=1620..4230), G08/G09 6~7 bot partial entry, mid-game 1006 disconnects, and G09 Team 2/3 split.
4. **`V1` (14.0%)**: Pre-`d590acd` `findVirtualSquadAnchor` caused 4/8 bots in G02, G04, G05, G07 to hit the `voronoi=500` scattered corner fallback.
5. **`V6` (9.0%)**: Boxed-in coastal rear bots (`nb=0, hasExposedCoast=true`) were blocked from feeding the frontline above d=75 while `[HL-ASSIST]` lacked a cooldown and fired 6~14 times per RTT window.
6. **`V5` (7.0%)**: 61~63 `[HL-INTERCEPT]` chase boats in G04 and G06 (up to 35%B per boat, with duplicate same-tick chases before `bQ.mt.mu` RTT confirmation) burned >1.8M troops.

## 四、最小可验证修复清单 (Actionable Fixes)

- **文件**: `tsb/squad/v27-team-live.js` (`Policy.buyLand (totB & oppFloorCap & isPrimeLand keep lock)`, 风险: `low`)
  - 修改前: `oppFloorCap: 38, collapseFloorCap: 16; const myOut = this.myOutTroops(g); const totB = B + myOut; if (isPrimeLand && B >= 12 * L) keep = Math.min(keep, (o.nearCollapse || dqNow < 14 ? 10 : 26) * L); const avail = Math.min(B - fee, totB - fee - keep);`
  - 修改后: `oppFloorCap: 112, collapseFloorCap: 68; const avail = B - fee - keep; // Never count in-flight myOutTroops as home defense when humanNbCount >= 1, and when squad is #1 or L_team >= 0.20*g.land, lock frontline keep >= Math.max(68 * L, 0.78 * this.safeAt(g, q));`
- **文件**: `tsb/squad/v27-team-live.js` (`Policy.tryDonateToTeammate & Policy.tryEmergencyBossRescue ([HL-ASSIST] RTT Cooldown & Rear-to-Frontline Conveyor)`, 风险: `low`)
  - 修改前: `if (mainAttacker >= 0 && (this.cnt[mainAttacker] ?? 0) > 0 && !g.hasAttack(me, mainAttacker) && g.hasFreeSlot(me) && dMe >= 65) { if (g.attack(102, mainAttacker, me)) ... } // plus `if (!boxedIn && dMe < 132) return false;` where coastal boxed-in bots keep safeFloor = 68*L`
  - 修改后: `Add `if (g.t - (this.lastAssistTick ?? -999) < 60) continue;` and set `this.lastAssistTick = g.t;` before `g.attack(102, ...)` so 2-tick period + 4-tick RTT never machine-guns 7x 10%B pokes in 12 ticks! For boxed-in rear bots (`enemyHumanNbs.length === 0 && this.neutral === 0`), lower coastal reserve to `38 * L` when no enemy boat is within 95px and stream 6%B (`pct=62`) every 24 ticks to the lowest-density frontline squadmate (`nb.length > 0 && dAlly < 95`).`
- **文件**: `tsb/squad/tsb-team-squad.mjs` (`allReadyInRoom0 (Strict 8-Bot / 7-Bot Entry Gate)`, 风险: `low`)
  - 修改前: `headlessInRoom0 >= HEADLESS_BOTS.length - 1 || (headlessInRoom0 >= 5 && minStartsIn <= 14)`
  - 修改后: `headlessInRoom0 === HEADLESS_BOTS.length || (headlessInRoom0 >= HEADLESS_BOTS.length - 1 && minStartsIn <= 10) // Never launch with only 5~6 bots; ensures >= 7~8 bots enter every match!`
