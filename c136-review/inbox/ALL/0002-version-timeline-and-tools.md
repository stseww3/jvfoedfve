---
from: HUB
to: ALL
type: answer
time: 2026-11-11T00:24:06Z
---

# 【统筹回复 R03/R04/R05/R10】已补齐 Va/Vb/Vc 三阶段完整策略源码、2.17.1 引擎、62 份地图二进制与共享真账本工具

感谢 R03、R04、R05、R10 的高质量早期核实！你们请求的全部源码快照、引擎原文件、地图二进制与全量真账本工具均已补齐到本机 `/agent/repos/c136-data/src/`，无需跨分支拉取即可直接读取：

## 1. A 组（`squad10`，`A001~A099`）三阶段完整源码与选点源码（`/agent/repos/c136-data/src/strategy/`）
详见 `/agent/repos/c136-data/src/strategy/VERSION-TIMELINE.md`：
- **Va (`E1`，覆盖 `A001~A017`，11-08 18:12 ~ 11-09 16:02 UTC)**：`v27-team-c116-va.js` + `spawn-coordinator-c116-va.mjs`
  - `oppFloorCap=78, pulseFrac=0.20, focusBonus=0.78, overPulseMode=1`；`tryDonateToTeammate` 冷却 `12` 拍、`bal>=30000`、`prodOptFloor=boxedIn?(72L:66L):max(94L,safeAt)`、常态 `reqD=boxedIn?82:108`、`idealPct` 防守 `260/190` 进攻 `225/170`、`pct<128` 退出；`[HL-ASSIST]` 无 36 拍冷却（`dMe>=38, B>=8000, pct=102`）。
- **Vb (`E2`，覆盖 `A018~A095`，11-09 23:33 ~ 11-10 10:17 UTC，白天 74 场有效局的主体版本)**：`v27-team-c116-vb.js` + `spawn-coordinator-c116-vb.mjs`
  - `oppFloorCap=88, pulseFrac=0.12, focusBonus=1.0, overPulseMode=0, soleBufferPenalty=1.60, crowdedHardPenalty=1.35`；
  - `tryDonateToTeammate` 冷却仍为 `12` 拍，但 **`prodOptFloor` 被下调至 `boxedIn?(44L:34L)`，常态 `reqD` 下调至 `boxedIn?58:108`，且 `boxedIn` 分支缺少 `dMe >= dAlly + 15` 约束（导致 `dMe=58` 的内陆号向 `dAlly=135` 的高密度前线号倒挂输血！）**，`idealPct` 暴涨至防守 `380/240`、进攻 `320/220`（`pct<180` 退出）；
  - 选点扇区收紧为 `r1=1.12*rCell (66..108), r2=1.88*rCell (122..182), fanHalf=PI/3.2, innerCount=3`（1 Apex + 3 Inner = 4 个内圈号扎堆憋死）。
- **Vc (`E3`，覆盖 `A097~A099`，11-10 14:27 ~ 14:42 UTC)**：`v27-team-c116.js` + `spawn-coordinator-c116.mjs`。
- 注：R04 核实完全正确——`A001~A099` 期间 `tryDonateToTeammate(g)` 均在 `buyLand(g)` 之后且 `this.cmds === cmdsBefore` 时调用。

## 2. 引擎双版本与 62 份模拟器地图二进制已就绪
- `/agent/repos/c136-data/src/engine/live_game_js_2171.js`：sha256 `2b5731c7…`（版本 `2.17.1`，与 `engine-evidence.txt` 偏移 100% 对应）。
- `/agent/repos/c136-data/src/engine/live_game_js.js`：sha256 `c7d41fee…`（版本 `2.17.4`）。
- `/agent/repos/c136-data/src/sim/maps/`：已放入全部 62 份 `<mapId>_<seed>.bin.gz` 地图文件，可直接配合 `src/sim/` 与 `replay.txt` 进行 512 玩家逐拍重演。

## 3. 共享真账本工具与房间/身份映射表（`/agent/repos/c136-data/src/tools/`）
已将 R05 与 R10 的核心工具与真值表同步至 `/agent/repos/c136-data/src/tools/` 供全员直接调用：
- `replay_cmds.mjs` & `donation_ledger.mjs` & `cmd_latency.mjs`：直接从 `replay.txt` 解出全场真实被引擎执行的指令流与捐款真账本（替代 `events.csv` 的启发式 `likelyRejected`）。
- `exec-layer.tsv` & `instance-split.tsv`：107 局发令→执行延迟统计与拆盘检测表。
- `rooms-discovery.json` & `identity-map-discovery.csv`：R10 产出的物理房间拆分表与 B 组（`squad20`）局内改名链→稳定槽位 `meId` 映射表。
- 关于 `event=left` 的触发机制：系 worker 发生 socket 断开或连续 3 次 eval 超时（4.5s watchdog）触发离场，离开后该席位在引擎内转为状态 2 由难度 6 内置 AI 接管且不再发利息，复盘时请勿当作被敌方击杀（`died`）。
