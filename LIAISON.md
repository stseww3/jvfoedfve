# GitHub Multi-Agent Liaison Index (`stseww3/fdvg` & `stseww3/jvfoedfve`)

如果你是管理员（`auouf`）新开启的协作 Agent，请先看这里对接：

1. **跨 Agent 实时联络主分支（在 `stseww3/fdvg` 仓库）**：`cursor/land-sea-liaison-337b`
   - 运行：`git -C /agent/repos/fdvg fetch origin cursor/land-sea-liaison-337b && git -C /agent/repos/fdvg checkout cursor/land-sea-liaison-337b`
   - **`liaison/land.txt`** — **主联络文件**（`c40` 已在文件最底部写好最新交接说明：含管理员 `#2457–#2602` 拍板的三大海陆核心机制、实盘 `LiveGame` 4 大底层修复、以及顾问 `c22` 对最近实盘局的诊断）
   - **`liaison/c39.txt`** — 架构与消融实验总表
   - **`liaison/sea.txt`** — 海洋机制与顾问 `c29` 的 40 局实盘统计报告

2. **最新策略代码分支（在 `stseww3/fdvg` 仓库）**：`cursor/territorial-c40-1745`（最新提交 `822e9141`，同步于 `cursor/c39-v21-8755`）
   - `territorial-sim/strategy/sea-core.js` — 三合一海洋闪电战模块（独立铺岛线 + 0 延迟桥头堡登陆 + 多点桥头堡扩接触面）
   - `territorial-sim/strategy/pool/v23.js` — 当前主策略源码
   - `territorial-sim/strategy/pool/v23-live.js` — 单文件自包含实盘包（由 `node tools/c22/freeze18.mjs v23` 生成）

3. **实盘录像与逐局战报分支（在 `stseww3/fdvg` 仓库）**：`cursor/territorial-c22-72c3`
   - `territorial-sim/results/tsb/games/*-report.txt` & `*-people.txt`

**如何与我们（`c40` / `c22` / `c29` / `c41`）在 GitHub 上交流**：
直接在 `stseww3/fdvg` 的 `cursor/land-sea-liaison-337b` 分支下 `liaison/land.txt` 末尾追加你的分析或代码提交 hash 并 push，`c40` 每隔几分钟会自动拉取并回复！
