# machines/switchboard-boiler 配电板和锅炉

**目标**：方案 §7.2「配电板和锅炉」、§5.3 发电房；细化稿 §2.6。大理石配电板（表盘/闸刀）、铁锅炉炉门透红光。**V6 发电房外（红热窗）+ 发电房内室**。
**优先级**：P2（配电板面用 A1 面板方块，依赖 A1；外壳依赖 A4；可占位先做立体大件）。

**约束**
- 坐标：`S.POWER_HOUSE` 内，配电板靠墙、锅炉落地。
- 色板：配电板底 `slate`（大理石）+母排 `brass`；大闸刀 `brass` 刀+`porcelain` 座；大表盘 `brass`圈+`cream`面+`phosphor` 夜光刻度；锅炉 `iron` 铆接+铁箍；炉膛火光 `glow`；安全阀点 `signal`。
- 16 像素一格，`px=scale`：配电板分段 scale2、锅炉 ⌀3→scale2、小件 scale1。
- 发光：**炉门口一圈暖光**（`glow`，emit 收小），透发电房拱窗成 V6 红热窗；表盘微亮。摆放函数返回 light（炉门二级、表盘三级）。亮区<1/3。
- 实体预算：本件 ≈40；`build()` 返回实体数。

**件清单**：`mach_board_panel` 大理石配电板框 3×0.5×3（**板面表盘/闸刀/电铃主要用 A1 面板方块码墙**，A5 只做立体件）；`mach_board_switch` 大闸刀排（`brass` 刀+`porcelain` 座，可扳）；`mach_board_meter` 大圆表盘 ⌀1（指针动画）；`mach_boiler_body` 锅炉本体 ⌀3×4（铆接+铁箍）；`mach_boiler_door` 炉门+火光（**emit 炉膛**，透窗红热）；`mach_boiler_gauge` 压力表/安全阀（大号自做）。
**交付物**：`build/scenes/obs/machines/board.py`、`boiler.py`（+ `_kit.py` 的 `dial/grad_circle/riveted_tube`）；测试场景 `build/scenes/obs_mach_switchboard_boiler/`（盒子发电房 + A1 面板方块占位；`shots.json` 配电板墙、炉门红光、透窗 V6）。
**验收**：五项，重点「明暗光色」（炉门红热透窗是 V6 关键暖点、亮区<1/3）、「风格逻辑」（大理石配电板+黄铜闸刀是电气时代、锅炉看得懂）、「质感像素」（闸刀/表盘/铆钉近看）。视角：配电板墙、炉门红光近景、透拱窗（V6）。
**版本**：1 版。
**依赖**：skeleton、palette；**A1** 面板方块（仪表墙/配电板面）、**A4** 发电房外壳/拱窗；`engine-dynamo`（同房，出线接配电板）；A8 指针/闸刀（供料）。**被依赖**：interiors `powerhouse`、看板 V6。
**记录**：A5 领（牵头）。默认：配电板靠内墙、锅炉在炉门朝拱窗一侧、炉门暖光收成膛口一圈。退回改法逐条记此。
